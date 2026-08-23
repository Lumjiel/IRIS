"""
IRIS Researcher 节点
- 本地文档检索（RAG）+ 文档相关性审计（Grader）
- 文档模式提前终止（should_stop）
- Validation Node（工具状态校验）
- 网络搜索已迁移至 search_agent（Function Calling）
"""
from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.rag.engine import get_retriever
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger
from app.error_types import ErrorCode, tool_execution_failed

log = get_logger("researcher")


def _validate_tool_status(state: AgentState, results: list) -> AgentState:
    """
    Validation Node：检查工具调用状态
    - 失败时设置 error_code = DEGRADED_SEARCH
    - 标记 degraded = True
    - 不往 search_results 里写原始错误
    """
    tool_status = state.get("tool_status", {})
    failed_tools = [
        name for name, status in tool_status.items()
        if isinstance(status, dict) and status.get("success") is False
    ]
    
    if failed_tools:
        state["error_code"] = ErrorCode.DEGRADED_SEARCH
        state["degraded"] = True
        state["failed_tools"] = failed_tools
        log.warning(f"[Validation Node] 工具调用失败: {failed_tools}，标记降级")
        
        # 不往 search_results 写原始错误，而是写降级提示
        if not results:
            results.append(
                f"[系统提示] 搜索服务暂时不可用（{', '.join(failed_tools)}），"
                f"以下基于已有知识回答。"
            )
    
    return state


def _record_tool_status(state: AgentState, tool_name: str, success: bool, error: str = None):
    """记录工具调用状态到 state"""
    tool_status = state.get("tool_status", {})
    tool_status[tool_name] = {
        "success": success,
        "error": error,
    }
    state["tool_status"] = tool_status


def research_node(state: AgentState):
    """执行研究节点（本地 RAG + 文档审计，网络搜索由 search_agent 处理）"""
    mode = state.get("search_mode", "hybrid")
    query = state["query"]
    plans = state.get("plan", [])
    results = []

    # 初始化 tool_status
    state["tool_status"] = {}

    # 每轮研究从干净状态开始：清空上一轮残留的降级标志，
    # 否则 error_code 一旦设置会经 checkpoint 持久化，导致 should_continue 永远强制打回 planner 重写
    state["error_code"] = ""
    state["degraded"] = False
    state["failed_tools"] = []
    
    log.info(f"开始搜索 | 模式: {mode}")
    
    try:
        retriever = get_retriever()
    except Exception as e:
        log.error(f"get_retriever 调用失败: {e}")
        _record_tool_status(state, "retriever", False, str(e))
        retriever = None

    rag_content = ""
    is_doc_relevant = False

    # === 本地文档检索 ===
    if retriever:
        log.info("正在检索本地知识库...")
        try:
            docs = retriever.invoke(query)
            if docs:
                raw_context = "\n\n".join([f"[文档片段]: {doc.page_content}" for doc in docs])
                log.info("正在进行文档相关性审计...")
                
                # Grader LLM 调用（带状态记录）
                grader_prompt = f"""
                你是一个严格的文档相关性评估员。

                用户问题: {query}
                检索到的文档片段:
                {raw_context[:2000]} (截取部分)

                请判断：这些文档片段是否包含回答用户问题所需的信息？
                - 如果文档完全不相关（例如问'吃什么'但文档是'深度学习'），请回答 "NO"。
                - 如果文档相关或部分相关，请回答 "YES"。

                只输出 "YES" 或 "NO"，不要输出其他内容。
                """
                
                try:
                    grade = llm_invoke(
                        [HumanMessage(content=grader_prompt)],
                        model_type="smart",
                        node="researcher"
                    ).content.strip().upper()
                    _record_tool_status(state, "grader", True)
                except Exception as e:
                    log.warning(f"Grader LLM 调用失败: {e}，默认文档相关")
                    _record_tool_status(state, "grader", False, str(e))
                    grade = "YES"  # grader 超时时保守地认为文档相关
                
                if "YES" in grade:
                    is_doc_relevant = True
                    rag_content = "\n\n".join([f"[文档片段]: {doc.page_content}" for doc in docs])
                    results.append(f"### 📂 本地文档资料 (已核实相关)\n{rag_content}\n")
                    log.info("文档通过相关性审计")
                else:
                    log.warning(f"文档内容与问题 '{query}' 不相关，已自动忽略")
                    results.append("[系统提示]: 检索了本地文档，但发现内容与问题不相关，已自动忽略。")
            else:
                log.info("未找到相关内容")
        except Exception as e:
            log.error(f"检索出错: {e}")
            _record_tool_status(state, "retriever", False, str(e))
    else:
        log.info("知识库为空，跳过")
    
    # === 文档模式：提前终止 ===
    if mode == "document":
        if is_doc_relevant:
            log.info("文档相关，按计划仅使用文档")
        else:
            log.warning("文档不相关，但 Document Only 模式")
            log.warning("文档内容与问题不匹配，无法生成有效回答")
            results.append("【严重警告】：用户选择了 Document Only 模式，但上传的文档与问题完全无关。请直接在报告中诚实地告诉用户：'您上传的文档中没有关于此问题的说明'，不要编造答案。")
            return {
                "search_results": results,
                "should_stop": True,
                "error_code": ErrorCode.VALIDATION_FAILED,
                "degraded": True,
            }

    # === 网络搜索已迁移至 search_agent（Function Calling） ===
    # researcher 只负责本地 RAG 检索 + 文档相关性审计
    # 网络搜索由 search_agent 节点通过 LLM 驱动的工具调用完成

    # === Validation Node：统一检查工具状态 ===
    state = _validate_tool_status(state, results)

    # 如果所有检索都失败，给 writer 一个提示而非空内容
    if not results:
        results.append(f"[系统提示] 未能检索到关于「{query}」的本地资料。网络搜索将由后续搜索代理完成。")

    return {"search_results": results, **{
        k: v for k, v in state.items()
        if k in ("tool_status", "error_code", "degraded", "failed_tools")
    }}

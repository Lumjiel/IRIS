from langchain_core.messages import HumanMessage
from app.tools.registry import ToolRegistry
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger
from app.tools.search import search_tavily_structured

log = get_logger("researcher")


def research_node(state: AgentState):

    mode = state.get("search_mode", "hybrid")
    query = state["query"]
    plans = state["plan"]
    results = []
    sources = []

    log.info(f"开始搜索 | 模式: {mode}")

    # --- resolve which tools to use ---
    # If the active Skill declares required_tools, restrict to those;
    # otherwise use all registered tools.
    active_skill = state.get("active_skill", "")
    if active_skill:
        from app.skills.registry import SkillRegistry as _SR
        # import skills registry singleton (imported lazily to avoid circular)
        from app.config import SKILLS_BUILTIN_DIR, SKILLS_USER_DIR
        _sr = _SR(SKILLS_BUILTIN_DIR, SKILLS_USER_DIR)
        skill_obj = _sr.get(active_skill)
        if skill_obj and skill_obj.required_tools:
            tools = [ToolRegistry.get(t) for t in skill_obj.required_tools if ToolRegistry.get(t)]
        else:
            tools = ToolRegistry.list_all()
    else:
        tools = ToolRegistry.list_all()

    # Separate doc_search from the rest
    doc_tool = next((t for t in tools if t.name == "doc_search"), None)
    web_tools = [t for t in tools if t.name != "doc_search"]

    # --- document retrieval ---
    rag_content = ""
    is_doc_relevant = False

    if doc_tool:
        log.info("正在检索本地知识库...")
        try:
            rag_content = doc_tool.func(query=query)
            if rag_content and not rag_content.startswith("[系统提示]"):
                log.info("正在进行文档相关性审计...")
                grader_prompt = f"""
                你是一个严格的文档相关性评估员。

                用户问题: {query}
                检索到的文档片段:
                {rag_content[:2000]} (截取部分)

                请判断：这些文档片段是否包含回答用户问题所需的信息？
                - 如果文档完全不相关（例如问'吃什么'但文档是'深度学习'），请回答 "NO"。
                - 如果文档相关或部分相关，请回答 "YES"。

                只输出 "YES" 或 "NO"，不要输出其他内容。
                """
                try:
                    grade = llm_invoke([HumanMessage(content=grader_prompt)], model_type="smart", node="researcher").content.strip().upper()
                except Exception as e:
                    log.warning(f"Grader LLM 调用失败: {e}，默认文档相关")
                    grade = "YES"
                if "YES" in grade:
                    is_doc_relevant = True
                    results.append(f"### \U0001f4c2 本地文档资料 (已核实相关)\n{rag_content}\n")
                    log.info("文档通过相关性审计")
                else:
                    log.warning(f"文档内容与问题 '{query}' 不相关，已自动忽略")
                    results.append("[系统提示]: 检索了本地文档，但发现内容与问题不相关，已自动忽略。")
            else:
                log.info("未找到相关内容")
        except Exception as e:
            log.error(f"检索出错: {e}")
    else:
        log.info("知识库为空，跳过")

    if mode == "document":
        if is_doc_relevant:
            log.info("文档相关，按计划仅使用文档")
        else:
            log.warning("文档不相关，但 Document Only 模式")
            log.warning("文档内容与问题不匹配，无法生成有效回答")
            results.append("【严重警告】：用户选择了 Document Only 模式，但上传的文档与问题完全无关。请直接在报告中诚实地告诉用户：\u201c您上传的文档中没有关于此问题的说明\u201d，不要编造答案。")
            return {
                "search_results": results,
                "search_sources": [],
                "should_stop": True
            }
    else:
        log.info("正在执行互联网搜索...")
        from app.tools.search import search_tavily_structured
        for q in plans:
            try:
                structured_results = search_tavily_structured(q)
                for item in structured_results:
                    url = item.get("url", "")
                    title = item.get("title", "")
                    content_text = item.get("content", "")
                    if url:
                        sources.append({"url": url, "title": title})
                    results.append(f"### 🌐 网络搜索结果 ({q})\n**{title}**\n{content_text}\n")
            except Exception as e:
                log.error(f"搜索 {q} 失败: {e}")

    # If all retrieval failed, give writer a hint
    if not results:
        results.append(f"[系统提示] 未能检索到关于「{query}」的外部资料。请基于你的知识直接回答，并在报告开头说明信息来源有限。")

    return {"search_results": results, "search_sources": sources}

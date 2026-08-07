import asyncio
from langchain_core.messages import HumanMessage
from app.tools.registry import ToolRegistry
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger
from app.utils.credibility import CredibilityScorer

log = get_logger("researcher")


async def _search_one(query: str):
    """在后台线程执行一次 Tavily 搜索。返回 (results, failed)。
    failed=True 表示基础设施/网络/API key 原因导致的失败，区别于正常无结果。"""
    try:
        from app.tools.search import search_tavily_structured
        results = await asyncio.to_thread(search_tavily_structured, query)
        return results, False
    except Exception as e:
        log.error(f"搜索 {query} 失败: {e}")
        return [], True


async def research_node(state: AgentState):
    mode = state.get("search_mode", "hybrid")
    query = state["query"]
    plan_structure = state.get("plan_structure") or []
    # 兼容：plan_structure 为空时用拍平 plan 兜底
    if not plan_structure:
        flat = state.get("plan", [])
        plan_structure = [{"subtask": f"方向{i+1}", "queries": [q]} for i, q in enumerate(flat)]

    results = []
    sources = []
    findings = []
    search_error = False

    log.info(f"开始搜索 | 模式: {mode} | 子任务数: {len(plan_structure)}")

    # --- resolve which tools to use ---
    # Skill 的 required_tools 真正约束可用工具；缺失的工具记告警但不阻塞
    active_skill = state.get("active_skill", "")
    if active_skill:
        from app.skills.router import get_skill
        skill_obj = get_skill(active_skill)
        if skill_obj and skill_obj.required_tools:
            tools = []
            for tname in skill_obj.required_tools:
                t = ToolRegistry.get(tname)
                if t:
                    tools.append(t)
                else:
                    log.warning(f"Skill '{active_skill}' 声明的工具 '{tname}' 未注册，已跳过")
            if not tools:
                log.warning(f"Skill '{active_skill}' 的 required_tools 均不可用，回退到全部工具")
                tools = ToolRegistry.list_all()
        else:
            tools = ToolRegistry.list_all()
    else:
        tools = ToolRegistry.list_all()

    doc_tool = next((t for t in tools if t.name == "doc_search"), None)
    web_tools = [t for t in tools if t.name != "doc_search"]

    # --- document retrieval ---
    rag_content = ""
    is_doc_relevant = False
    if doc_tool:
        log.info("正在检索本地知识库...")
        try:
            rag_content = await asyncio.to_thread(doc_tool.func, query=query)
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
                    results.append(f"### 📂 本地文档资料 (已核实相关)\n{rag_content}\n")
                    log.info("文档通过相关性审计")
                    try:
                        from app.rag.engine import get_retriever
                        retriever = get_retriever()
                        if retriever:
                            docs = retriever.invoke(query)
                            seen_sources = set()
                            for doc in docs:
                                source_name = doc.metadata.get("source", doc.metadata.get("filename", "本地文档"))
                                if source_name not in seen_sources:
                                    seen_sources.add(source_name)
                                    sources.append({"url": "", "title": source_name, "snippet": doc.page_content[:200]})
                    except Exception as e:
                        log.warning(f"提取文档来源元数据失败: {e}")
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
            results.append("【严重警告】：用户选择了 Document Only 模式，但上传的文档与问题完全无关。请直接在报告中诚实地告诉用户：\u201c您上传的文档中没有关于此问题的说明\u201d，不要编造答案。")
            return {
                "search_results": results,
                "search_sources": [],
                "should_stop": True,
            }
    else:
        log.info("正在并行执行互联网搜索...")
        total_queries = 0
        failed_queries = 0
        for item in plan_structure:
            subtask = item.get("subtask", "")
            queries = item.get("queries", [])
            # 并行执行该子任务下所有查询
            per_query = await asyncio.gather(*[_search_one(q) for q in queries])
            total_queries += len(queries)
            subtask_findings = []
            for q, (structured, failed) in zip(queries, per_query):
                if failed:
                    failed_queries += 1
                for s in structured:
                    url = s.get("url", "")
                    title = s.get("title", "")
                    content_text = s.get("content", "")
                    if url and title:
                        sources.append({"url": url, "title": title})
                    results.append(f"### 🌐 网络搜索结果 ({q})\n**{title}**\n{content_text}\n")
                    subtask_findings.append({"query": q, "url": url, "title": title, "content": content_text})
            findings.append({"subtask": subtask, "items": subtask_findings})
        # 全部搜索因基础设施原因失败（API key 失效/网络/配额）=> 标记搜索服务不可用
        search_error = total_queries > 0 and failed_queries >= total_queries
        if search_error:
            log.warning("所有网络搜索均失败，判定搜索服务不可用")

    # If all retrieval failed, give writer a hint
    if not results:
        results.append(f"[系统提示] 未能检索到关于「{query}」的外部资料。请基于你的知识直接回答，并在报告开头说明信息来源有限。")

    # 可信度过滤：移除低质量来源
    if sources:
        scorer = CredibilityScorer()
        sources = scorer.filter_results(sources)

    return {
        "search_results": results,
        "search_sources": sources,
        "research_findings": findings,
        "search_error": search_error,
    }
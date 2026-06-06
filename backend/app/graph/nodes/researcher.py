from langchain_core.messages import HumanMessage
from app.tools.search import search_tavily
from app.graph.state import AgentState
from app.rag.engine import get_retriever
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("researcher")
def research_node(state: AgentState):

    mode = state.get("search_mode", "hybrid")
    query = state["query"]
    plans = state["plan"]
    results = []

    log.info(f"开始搜索 | 模式: {mode}")
    
    retriever = get_retriever()
    rag_content = ""
    is_doc_relevant = False
    
    if retriever:
        log.info("正在检索本地知识库...")
        try:
            docs = retriever.invoke(query)
            if docs:
                raw_context = "\n\n".join([f"[文档片段]: {doc.page_content}" for doc in docs])
                log.info("正在进行文档相关性审计...")
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
                    grade = llm_invoke([HumanMessage(content=grader_prompt)], model_type="smart").content.strip().upper()
                except Exception as e:
                    log.warning(f"Grader LLM 调用失败: {e}，默认文档相关")
                    grade = "YES"  # grader 超时时保守地认为文档相关
                if "YES" in grade:
                    is_doc_relevant = True
                    rag_content = "\n\n".join([f"[文档片段]: {doc.page_content}" for doc in docs])
                    results.append(f"### 📂 本地文档资料 (已核实相关)\n{rag_content}\n")
                    log.info("文档通过相关性审计")
                else:
                    log.warning(f"文档内容与问题 '{query}' 不相关，已自动忽略")

                    results.append(f"[系统提示]: 检索了本地文档，但发现内容与问题不相关，已自动忽略。")
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
            results.append("【严重警告】：用户选择了 Document Only 模式，但上传的文档与问题完全无关。请直接在报告中诚实地告诉用户：“您上传的文档中没有关于此问题的说明”，不要编造答案。")
            return {
                "search_results": results,
                "should_stop": True 
            }


    else: 
        should_web_search = True
        
        if is_doc_relevant:

            log.info("文档相关，启用混合增强模式 (Doc + Web)")
        else:

            log.info("文档不相关，自动切换为全网搜索模式")
            log.info("本地文档与问题无关，系统已自动切换为全网搜索")

        if should_web_search:
            log.info("正在执行互联网搜索...")
            for q in plans:
                try:
                    content = search_tavily(q)
                    results.append(f"### 🌐 网络搜索结果 ({q})\n{content}\n")
                except Exception as e:
                    log.error(f"搜索 {q} 失败: {e}")
            
    return {"search_results": results}
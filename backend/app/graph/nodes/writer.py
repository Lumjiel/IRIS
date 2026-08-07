from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.utils.memory import build_conversation_context
from app.graph.state import AgentState
from app.utils.logger import get_logger
from app.memory.extractor import extract_memories
from app.utils.citations import CitationFormatter

log = get_logger("writer")

# 写作风格映射
STYLE_MODIFIERS = {
    "detailed": "请写一份结构清晰、有深度的调研报告，内容详尽全面。",
    "concise": "请写一份简洁精炼的调研报告，突出核心结论，避免冗余。",
    "formal": "请用正式的学术/商业文风撰写调研报告，用词严谨专业。",
    "casual": "请用通俗易懂的语言撰写调研报告，让非技术读者也能理解。",
}

LANGUAGE_MODIFIERS = {
    "zh": "使用 Markdown 格式，全文中文。",
    "en": "Use Markdown format. Write the entire report in English.",
}

WRITE_PROMPT = ChatPromptTemplate.from_template(
    """你是一个专业的技术撰稿人。
    基于以下的调研资料，回答用户的问题：{query}

    调研资料：
    {content}

    {conversation_context}

    审查意见（如果有）：
    {critique_section}
    不能捏造事实，每个结论都要对应资料里的证据点。
    {style_instruction}
    {language_instruction}
    """
)

async def write_node(state: AgentState):
    log.info("正在撰写报告")
    query = state["query"]
    # 优先使用 Synthesize 节点汇总后的结构化发现，避免被原始片段淹没
    synthesis = state.get("synthesis", "")
    raw_results = "\n\n".join(state.get("search_results", []))
    content = synthesis if synthesis.strip() else raw_results

    critique = state.get("critique", "")
    critique_section = ""
    if critique:
        critique_section = f"""
        【重要提示】上一版本的报告未通过审查。
        审查意见如下："{critique}"
        请务必在本次写作中修正上述问题。
        """

    # 组装对话上下文（摘要 + 最近对话 + 已搜方向避让）
    conversation_context = build_conversation_context(state)

    # 根据用户偏好调整写作风格
    prefs = state.get("preferences", {})
    style = prefs.get("style", "detailed")
    language = prefs.get("language", "zh")
    style_instruction = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS["detailed"])
    language_instruction = LANGUAGE_MODIFIERS.get(language, LANGUAGE_MODIFIERS["zh"])

    prompt_text = WRITE_PROMPT.format(
        query=query,
        content=content,
        conversation_context=conversation_context,
        critique_section=critique_section,
        style_instruction=style_instruction,
        language_instruction=language_instruction,
    )

    if get_token_queue() is not None:
        report = await llm_stream_tokens(
            [HumanMessage(content=prompt_text)],
            model_type="fast",
            node_name="writer",
            node="writer",
        )
    else:
        response = llm_invoke([HumanMessage(content=prompt_text)], node="writer")
        report = response.content or ""

    if not report.strip():
        log.warning("LLM 返回空报告，生成兜底内容")
        report = f"## {query}\n\n基于现有信息，关于「{query}」的研究报告暂时无法完整生成。建议稍后重试或调整研究方向。"

    # 追加引用标注和参考文献列表（跨轮持久化）
    citation_fmt = CitationFormatter()
    existing_refs = state.get("citation_refs", "")
    if existing_refs:
        for line in existing_refs.split("\n"):
            line = line.strip()
            if line and line.startswith("[") and "]" in line:
                idx_end = line.index("]")
                title_part = line[idx_end+1:].strip()
                citation_fmt.add_source(url="", title=title_part, snippet="")
    for src in state.get("search_sources", []):
        citation_fmt.add_source_from_search_result(src)
    references = citation_fmt.format_references()
    if references:
        report = report + references

    thread_id = state.get("thread_id") or state.get("preferences", {}).get("thread_id")
    try:
        extract_memories(
            query=query,
            plan=state.get("plan", []),
            report=report,
            thread_id=thread_id,
            preferences=state.get("preferences"),
        )
    except Exception as e:
        log.warning(f"记忆提取失败（不影响主流程）: {e}")

    return {"final_report": report, "citation_refs": references}

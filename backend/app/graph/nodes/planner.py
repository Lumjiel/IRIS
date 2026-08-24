from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.utils.memory import build_conversation_context
from app.graph.state import AgentState
from app.utils.logger import get_logger

log = get_logger("planner")


PLAN_PROMPT = ChatPromptTemplate.from_template(
    """你是一个专业的调研助手。
    {conversation_context}
    请生成 3-5 个简短的搜索子问题，用于在 Google 上查找相关信息。

    重要规则：
    - 如果存在「已搜索方向」列表，**严禁重复**这些方向，必须从全新的角度切入
    - 如果存在审查意见，请针对意见中提到的缺失信息生成搜索方向
    - 结合对话历史和当前问题，确保每次搜索都有增量价值
    - 只返回关键词，用逗号分隔，不要有其他废话
    例如：子问题1, 子问题2, 子问题3
    """
)

async def plan_node(state: AgentState):
    log.info("正在规划搜索路径")

    # 组装对话上下文（含历史摘要、已搜方向避让、当前问题）
    conversation_context = build_conversation_context(state)

    # 长期记忆注入（有记忆才拼，空则不加）——影响"怎么搜"，不参与路由
    from app.graph.nodes.load_memories import build_memory_block
    conversation_context = build_memory_block(state) + conversation_context

    prompt_text = PLAN_PROMPT.format(
        conversation_context=conversation_context,
    )

    if get_token_queue() is not None:
        response_text = await llm_stream_tokens(
            [HumanMessage(content=prompt_text)],
            model_type="fast",
            node_name="planner",
            node="planner",
        )
    else:
        response = llm_invoke([HumanMessage(content=prompt_text)], node="planner")
        response_text = response.content

    # LLM 在中文语境下常输出全角逗号/顿号/换行，统一按多种分隔符切分并过滤空项，
    # 否则整段文本会退化成单元素计划传给 search_agent
    import re as _re
    plans = [p.strip() for p in _re.split(r"[,，、;；\n]", response_text) if p.strip()]
    if not plans:
        # 空计划守卫：LLM 输出异常时至少保留原始查询作为搜索方向
        log.warning("planner 输出解析为空计划，回退为原始 query")
        plans = [state.get("query", "")]

    # 首次进入 planner（NEW_TOPIC）时清理旧报告状态
    # revision_number > 0 表示是审查失败后的重试，不清
    result = {"plan": plans}
    if state.get("revision_number", 0) == 0:
        if state.get("final_report", "").strip():
            log.info("新主题：清理旧报告，防止污染新主题的搜索方向")
            result["final_report"] = ""
            result["conversation_summary"] = ""
    return result

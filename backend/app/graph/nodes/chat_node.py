"""
IRIS Chat Node — 通用对话（不调 graph）
用于打招呼、一般知识问答、非研究类问题
"""
from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.utils.memory import update_conversation_summary
from app.utils.logger import get_logger

log = get_logger("chat")


async def chat_node(state: AgentState):
    """通用对话节点：流式输出纯文本，不调研究 graph"""
    query = state["query"]
    summary = state.get("conversation_summary", "")

    log.info(f"通用对话: '{query}'")

    prompt = f"""你是一个专业的投研助手 IRIS，擅长分析 A 股市场和个股投资价值。
请友好、简洁地回答用户的问题。回答控制在 2-4 句话。

如果用户询问与股票/投资无关的问题，先简短回答，然后引导用户使用研究功能。
"""
    if summary:
        prompt += f"\n【对话上下文摘要】\n{summary[:1000]}\n"

    prompt += f"\n【用户问题】\n{query}\n\n请直接回答："

    if get_token_queue() is not None:
        response_text = await llm_stream_tokens(
            [HumanMessage(content=prompt)],
            model_type="fast",
            node_name="chat",
            node="chat",
        )
    else:
        response = llm_invoke([HumanMessage(content=prompt)], node="chat")
        response_text = response.content

    # 更新对话摘要（轻量）
    new_summary = update_conversation_summary(
        old_summary=summary,
        query=query,
        report="",
    )

    return {
        "chat_response": response_text,
        "conversation_summary": new_summary,
        "review_status": "PASS",
    }

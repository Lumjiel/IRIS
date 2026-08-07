from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.graph.state import AgentState
from app.utils.logger import get_logger

log = get_logger("chat")

CHAT_PROMPT = """\
你是一个友好的 AI 助手。请用简洁友好的方式回答用户的问题。
不要过度展开，保持对话的自然性。
如果用户问的是关于你自己的问题，你可以介绍自己是一个 AI 调研助手。
如果用户的问题超出你的能力范围，诚实地说出来。"""


async def chat_node(state: AgentState):
    """闲聊/问答节点：直接用 LLM 回复，不走调研流程"""
    query = state["query"]
    log.info(f"闲聊模式: {query[:50]}...")

    messages = [SystemMessage(content=CHAT_PROMPT), HumanMessage(content=query)]

    if get_token_queue() is not None:
        response = await llm_stream_tokens(
            messages, model_type="fast", node_name="chat", node="chat"
        )
    else:
        response = llm_invoke(messages, node="chat").content

    return {"final_report": response}

"""
Clarify 节点 — 意图不明时的反问澄清路径。

Router 判为 CLARIFY（低置信度/语义含糊）时，本节点向用户抛出澄清问题，
而不是默认硬塞给 RESEARCH。问题通过 SSE 流式输出，并写入 state.clarify_question。
"""
from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.logger import get_logger
from app.utils.streaming import llm_stream_tokens, get_token_queue

log = get_logger("clarify")

_DEFAULT_QUESTION = (
    "我还不太确定您的具体需求。请问您是想让我做一项深度调研并生成报告，"
    "还是修改/补充已有的内容？也可以直接告诉我您想调研的主题或想完成的任务。"
)

CLARIFY_PROMPT = """用户说：「{query}」

这句话语义不够明确，无法判断是「深度调研」还是「修改已有报告」还是「其他需求」。
请用一句话、口语化地反问用户，引导 TA 说明具体意图。不要解释，只输出问题本身。
"""


async def clarify_node(state: AgentState) -> dict:
    query = (state.get("query") or "").strip()
    log.info(f"意图不明，进入澄清: '{query}'")

    queue = get_token_queue()
    question = _DEFAULT_QUESTION

    if queue is not None:
        try:
            question = await llm_stream_tokens(
                [HumanMessage(content=CLARIFY_PROMPT.format(query=query or "前一句话"))],
                model_type="fast",
                node_name="clarify",
                node="clarify",
            )
        except Exception as e:
            log.warning(f"澄清问题生成失败，使用默认问题: {e}")
            for token in question:
                await queue.put({"step": "clarify_token", "data": {"token": token}})
            await queue.put({"step": "clarify_token", "data": {"token": "", "final": True}})
    else:
        log.debug("无流式队列，clarify 仅写入 state")

    if not (question or "").strip():
        question = _DEFAULT_QUESTION

    return {
        "clarify_question": question,
        "should_stop": True,
    }
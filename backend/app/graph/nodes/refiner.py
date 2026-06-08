from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.utils.memory import update_conversation_summary
from app.utils.logger import get_logger

log = get_logger("refiner")

# 模糊后续的典型模式：短句、无具体修改意图
_VAGUE_PATTERNS = ["你觉得", "你认为", "怎么看", "然后呢", "接着", "继续",
                    "还有呢", "再说说", "评价", "点评", "分析一下"]


def _is_vague(query: str) -> bool:
    q = query.strip()
    return len(q) < 20 and any(p in q for p in _VAGUE_PATTERNS)


async def refine_node(state: AgentState):
    query = state["query"]
    old_report = state.get("final_report", "")

    # 模糊后续（如"你觉得呢？"）：轻量处理，不全文重写
    if _is_vague(query):
        log.info(f"模糊后续，轻量处理: {query}")
        summary = old_report[:2000]
        prompt = f"""你是一个专业的技术分析师。用户刚才看了一份调研报告，现在想听听你的看法。

【报告摘要（前 2000 字）】
{summary}

【用户提问】
{query}

请基于报告内容简要回答用户的问题（2-4 段）。不要重复报告的完整内容，给出你的专业分析和建议。"""
    else:
        log.info(f"明确修改指令，全文修订: {query}")
        prompt = f"""
    你是一个专业的报告编辑。

    【原始报告】
    {old_report}

    【用户修改指令】
    {query}

    请根据用户的指令，对原始报告进行修改。
    注意：
    1. 保持原有的 Markdown 结构。
    2. 只修改用户要求的部分，其余部分尽量保持原汁原味。
    3. 直接输出修改后的完整报告，不要有任何前言后语。
    """

    if get_token_queue() is not None:
        new_report = await llm_stream_tokens(
            [HumanMessage(content=prompt)],
            model_type="fast",
            node_name="refiner",
        )
    else:
        response = llm_invoke([HumanMessage(content=prompt)])
        new_report = response.content

    # 模糊后续不修改原报告，在末尾追加分析
    if _is_vague(query):
        new_report = old_report + "\n\n---\n\n## 💬 AI 分析\n\n" + new_report

    # 更新对话摘要，记录用户的修改指令
    new_summary = update_conversation_summary(
        old_summary=state.get("conversation_summary", ""),
        query=query,
        report=new_report,
    )

    return {
        "final_report": new_report,
        "conversation_summary": new_summary,
        "review_status": "PASS"
    }
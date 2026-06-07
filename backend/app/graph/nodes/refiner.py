from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.memory import update_conversation_summary
from app.utils.logger import get_logger

log = get_logger("refiner")


def refine_node(state: AgentState):
    query = state["query"]
    old_report = state.get("final_report", "")

    log.info(f"正在根据指令修改报告: {query}")

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

    response = llm_invoke([HumanMessage(content=prompt)])
    new_report = response.content

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
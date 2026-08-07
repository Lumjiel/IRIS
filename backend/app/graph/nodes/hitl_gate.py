"""
Human-in-the-loop 门禁节点。

Reviewer 首次 FAIL 时，本节点暂停自动重规划，把审查意见 + 可选项抛给用户，
让用户决定下一步方向（重试搜索 / 用当前内容定稿 / 换方向），而不是黑盒自动重跑。
"""
from app.graph.state import AgentState
from app.utils.logger import get_logger
from app.utils.streaming import get_token_queue

log = get_logger("hitl_gate")

HITL_CHOICES = ["retry", "use_existing", "redirect"]


def _build_question(state: AgentState) -> str:
    critique = state.get("critique", "") or ""
    return (
        "报告未通过质量审查，需要你的决定：\n\n"
        f"审查意见：{critique[:200]}\n\n"
        "请选择下一步：\n"
        "1. 重试搜索 — 根据审查意见换个方向重新调研\n"
        "2. 就用当前内容定稿 — 保留现有报告\n"
        "3. 换个方向 — 告诉我新方向\n"
    )


def hitl_gate_node(state: AgentState) -> dict:
    log.info("Reviewer FAIL，进入 Human-in-the-loop，等待用户决策")
    question = _build_question(state)

    queue = get_token_queue()
    if queue is not None:
        for token in question:
            queue.put_nowait({"step": "hitl_token", "data": {"token": token}})
        queue.put_nowait({"step": "hitl_token", "data": {"token": "", "final": True}})

    return {
        "pending_hitl": True,
        "hitl_question": question,
        "hitl_mode": "waiting",
        "should_stop": True,
    }
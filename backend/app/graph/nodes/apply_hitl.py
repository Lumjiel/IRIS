"""
Human-in-the-loop 决策节点。

用户在 reviewer FAIL 后选择的方向在这里落地：
- retry: 清空 pending_hitl，按原审查意见重新规划搜索（回 planner）
- redirect: 用用户新给的方向重新规划（回 planner）
- use_existing: 保留当前报告定稿（review_status=PASS，结束）

通过 hitl_mode 通知条件边跳到 planner 还是 END。
"""
from app.graph.state import AgentState
from app.utils.logger import get_logger

log = get_logger("apply_hitl")


def apply_hitl_node(state: AgentState) -> dict:
    choice = (state.get("hitl_choice") or "").strip().lower()
    log.info(f"应用 HITL 决策: {choice!r}")

    # 兜底：把用户自然语言映射到枚举（子串匹配，兼容"换个方向：XXX"）
    if any(k in choice for k in ("use_existing", "就用", "保留", "定稿", "用现有", "就用当前")):
        mode, final = "end", True
    elif any(k in choice for k in ("换方向", "redirect", "重新", "重试", "再搜", "换个角度")):
        mode, final = "planner", False
    else:
        # 未知选择：默认重试
        mode, final = "planner", False

    result = {
        "pending_hitl": False,
        "hitl_choice": "",
        "hitl_mode": mode,
    }
    if final:
        result["review_status"] = "PASS"
        # 把已有报告发回给前端展示（本次 run 不产生新报告）
        result["final_report"] = state.get("final_report", "")
        result["grounded"] = state.get("grounded", True)
        log.info("用户选择定稿，保留当前报告")
    else:
        log.info("用户选择重规划，回 planner 重新调研")
    return result
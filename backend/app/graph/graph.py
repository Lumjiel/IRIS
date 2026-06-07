from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes.planner import plan_node
from app.graph.nodes.researcher import research_node
from app.graph.nodes.writer import write_node
from app.graph.nodes.reviewer import review_node
import json
from app.graph.nodes.router import route_query
from app.graph.nodes.refiner import refine_node
from app.utils.logger import get_logger
from app.config import MAX_REVISIONS

log = get_logger("graph")

def route_after_research(state: AgentState):
    """
    Researcher 结束后的交通指挥员。
    检查 state['should_stop'] 是否为 True。
    """

    if state.get("should_stop", False):
        log.info("[路由] 检测到停止信号 (should_stop=True) -> 提前结束任务")
        return END
    else:

        return "writer"

def should_continue(state: AgentState):
    """
    决定下一步去哪里的函数。
    返回下一个节点的名称 (字符串) 或 END。
    """

    current_revision = state.get("revision_number", 0)
    if current_revision >= MAX_REVISIONS:
        log.info(f"已达到最大重试次数 {MAX_REVISIONS}，强制结束")
        return END

    review_status = state.get("review_status", "PASS")
    critique = state.get("critique", "")

    if review_status == "FAIL":
        log.info(f"[路由] 审查未通过 (意见: {critique}) -> 返回规划节点")
        return "planner"
    else:
        log.info("[路由] 审查通过 -> 结束")
        return END


# 模块级构建一次拓扑（不含编译）
_workflow = StateGraph(AgentState)

_workflow.add_node("planner", plan_node)
_workflow.add_node("researcher", research_node)
_workflow.add_node("writer", write_node)
_workflow.add_node("reviewer", review_node)
_workflow.add_node("refiner", refine_node)

# START -> planner -> researcher -> writer -> reviewer -> END/planner
_workflow.set_conditional_entry_point(
    route_query,
    {
        "planner": "planner",
        "refiner": "refiner"
    }
)
_workflow.add_edge("planner", "researcher")
_workflow.add_conditional_edges(
    "researcher",
    route_after_research,
    {
        "writer": "writer",
        END: END
    }
)
_workflow.add_edge("writer", "reviewer")

_workflow.add_conditional_edges(
    "reviewer",
    should_continue,
    {
        "planner": "planner",
        END: END
    }
)
_workflow.add_edge("refiner", END)


def create_graph(memory=None, store=None):
    """编译图（仅执行 compile，不重建拓扑）"""
    return _workflow.compile(checkpointer=memory, store=store)
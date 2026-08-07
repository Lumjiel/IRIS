from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes.planner import plan_node
from app.graph.nodes.researcher import research_node
from app.graph.nodes.synthesize import synthesize_node
from app.graph.nodes.writer import write_node
from app.graph.nodes.reviewer import review_node
from app.graph.nodes.router import route_node, route_intent
from app.graph.nodes.refiner import refine_node
from app.graph.nodes.chat import chat_node
from app.graph.nodes.sql import sql_node
from app.graph.nodes.tool_call import tool_call_node
from app.graph.nodes.tool_execute import tool_execute_node
from app.graph.nodes.clarify import clarify_node
from app.utils.logger import get_logger
from app.config import MAX_REVISIONS

log = get_logger("graph")


def after_tool_call(state: AgentState):
    """ReAct：tool_call 决策后有工具请求则执行，否则直接结束。"""
    if state.get("tool_call_request"):
        return "tool_execute"
    return END


def route_after_research(state: AgentState):
    """Researcher 结束后的路由：should_stop 提前结束，否则进入 Synthesize 汇总。"""
    if state.get("should_stop", False):
        log.info("[路由] 检测到停止信号 (should_stop=True) -> 提前结束任务")
        return END
    else:
        return "synthesize"


def should_continue(state: AgentState):
    """Reviewer 审查后的路由：FAIL 回跳 planner，PASS 结束"""
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

# === 添加所有节点 ===
# router 是真正的意图识别节点（写回 state），后续由 route_intent 条件边路由
_workflow.add_node("router", route_node)
_workflow.add_node("planner", plan_node)
_workflow.add_node("researcher", research_node)
_workflow.add_node("synthesize", synthesize_node)
_workflow.add_node("writer", write_node)
_workflow.add_node("reviewer", review_node)
_workflow.add_node("refiner", refine_node)
_workflow.add_node("chat", chat_node)
_workflow.add_node("sql", sql_node)
_workflow.add_node("tool_call", tool_call_node)
_workflow.add_node("tool_execute", tool_execute_node)
_workflow.add_node("clarify", clarify_node)

# === 入口：router 节点 -> 按意图条件路由 ===
_workflow.set_entry_point("router")
_workflow.add_conditional_edges(
    "router",
    route_intent,
    {
        "research": "planner",      # RESEARCH -> planner -> researcher(并行) -> synthesize -> writer -> reviewer
        "chat": "chat",             # CHAT -> chat_node -> END
        "sql": "sql",               # SQL -> sql_node -> END
        "tool_call": "tool_call",   # TOOL_CALL -> ReAct 循环(tool_call⇄tool_execute)
        "refine": "refiner",        # REFINE -> refiner -> END
        "clarify": "clarify",       # CLARIFY -> clarify -> END
    }
)

# === RESEARCH 链路 ===
_workflow.add_edge("planner", "researcher")
_workflow.add_conditional_edges(
    "researcher",
    route_after_research,
    {
        "synthesize": "synthesize",
        END: END
    }
)
_workflow.add_edge("synthesize", "writer")
_workflow.add_edge("writer", "reviewer")
_workflow.add_conditional_edges(
    "reviewer",
    should_continue,
    {
        "planner": "planner",
        END: END
    }
)

# === ReAct 工具循环 ===
# tool_call 决策：有工具请求 -> tool_execute；否则 -> END（after_tool_call 决定）
_workflow.add_conditional_edges(
    "tool_call",
    after_tool_call,
    {"tool_execute": "tool_execute", END: END}
)
# tool_execute 执行完回到 tool_call 继续决策（循环靠 after_tool_call 的 END 出口打断）
_workflow.add_edge("tool_execute", "tool_call")

# === 其他链路直接到 END ===
_workflow.add_edge("chat", END)
_workflow.add_edge("sql", END)
_workflow.add_edge("refiner", END)
_workflow.add_edge("clarify", END)


def create_graph(memory=None, store=None):
    """编译图（仅执行 compile，不重建拓扑）"""
    return _workflow.compile(checkpointer=memory, store=store)
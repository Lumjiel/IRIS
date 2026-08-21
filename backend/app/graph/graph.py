"""
IRIS LangGraph 状态机拓扑
- LangSmith Traceable 包装
- RetryPolicy/TimeoutPolicy
- 条件边循环终止（cosine 早停 + MAX_ITERATIONS）
"""
from langgraph.graph import StateGraph, END
from langsmith import traceable
import httpx

from app.graph.state import AgentState
from app.graph.nodes.router import route_query
from app.graph.nodes.planner import plan_node
from app.graph.nodes.researcher import research_node
from app.graph.nodes.writer import write_node
from app.graph.nodes.reviewer import review_node
from app.graph.nodes.refiner import refine_node
from app.graph.nodes.data_collector import data_collector_node
from app.error_types import ErrorCode
from app.utils.logger import get_logger
from app.config import MAX_REVISIONS, LANGSMITH_API_KEY

log = get_logger("graph")

# === 循环终止配置 ===
MAX_ITERATIONS = 5  # 最大循环次数（reviewer → planner 回跳）
COSINE_SIMILARITY_THRESHOLD = 0.95  # cosine 相似度早停阈值

# === 重试策略 ===
retry_policy = {
    "max_attempts": 3,
    "initial_interval": 1.0,
    "backoff_factor": 2.0,
    "max_interval": 10.0,
    "jitter": True,
    "retry_on": (
        httpx.TimeoutException,
        httpx.HTTPStatusError,
        ConnectionError,
    )
}

# === Traceable 包装节点 ===
@traceable(run_type="chain", name="router")
def traced_router(state: AgentState):
    return route_query(state)

@traceable(run_type="chain", name="planner")
def traced_planner(state: AgentState):
    return plan_node(state)

@traceable(run_type="chain", name="researcher")
def traced_researcher(state: AgentState):
    return research_node(state)

@traceable(run_type="chain", name="writer")
def traced_writer(state: AgentState):
    return write_node(state)

@traceable(run_type="chain", name="reviewer")
def traced_reviewer(state: AgentState):
    return review_node(state)

@traceable(run_type="chain", name="refiner")
def traced_refiner(state: AgentState):
    return refine_node(state)


@traceable(run_type="chain", name="data_collector")
def traced_data_collector(state: AgentState):
    return data_collector_node(state)


def route_after_research(state: AgentState):
    """Researcher 结束后的交通指挥员"""
    if state.get("should_stop", False):
        log.info("[路由] 检测到停止信号 (should_stop=True) -> 提前结束任务")
        return END
    else:
        return "writer"


def should_continue(state: AgentState) -> str:
    """
    条件路由决策（4 层终止逻辑）：
    1. 降级错误（DEGRADED_SEARCH / FALLBACK_LLM）→ 继续但标记 degraded
    2. 其他严重错误 → 终止
    3. reviewer 设置 early_stop 或 should_continue=False → 终止
    4. 达到最大迭代次数 → 终止
    5. 默认继续
    """
    # 1. 检查错误码
    error_code = state.get("error_code")
    if error_code:
        if error_code in (ErrorCode.DEGRADED_SEARCH.value, ErrorCode.FALLBACK_LLM.value):
            state["degraded"] = True
            log.warning(f"[路由] 降级错误 {error_code}，继续执行但标记 degraded")
            return "planner"
        else:
            log.warning(f"[路由] 严重错误 {error_code}，终止循环")
            return END

    # 2. 早停检查（由 reviewer 设置）
    if state.get("early_stop") is True or state.get("should_continue") is False:
        log.info("[路由] reviewer 设置 early_stop/should_continue=False，终止循环")
        return END

    # 3. 迭代次数限制
    current_revision = state.get("revision_number", 0)
    if current_revision >= MAX_ITERATIONS:
        log.warning(f"[路由] 达到最大迭代次数 {MAX_ITERATIONS}，强制终止")
        return END

    # 4. 原有逻辑：reviewer FAIL → planner
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

_workflow.add_node("router", traced_router)
_workflow.add_node("planner", traced_planner)
_workflow.add_node("researcher", traced_researcher)
_workflow.add_node("writer", traced_writer)
_workflow.add_node("reviewer", traced_reviewer)
_workflow.add_node("refiner", traced_refiner)
_workflow.add_node("data_collector", traced_data_collector)

# START -> planner -> Researcher -> Writer -> Reviewer -> END/Planner
_workflow.set_conditional_entry_point(
    route_query,
    {
        "planner": "planner",
        "refiner": "refiner"
    }
)
_workflow.add_edge("planner", "researcher")
_workflow.add_edge("researcher", "data_collector")
_workflow.add_edge("data_collector", "writer")
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

"""
IRIS LangGraph 状态机拓扑
- LangSmith Traceable 包装
- RetryPolicy/TimeoutPolicy
- 条件边循环终止（cosine 早停 + MAX_ITERATIONS）
- 节点级状态事件（start/done + elapsed）→ 前端时间线真实进度
"""
import time as _time
from langgraph.graph import StateGraph, END
from langsmith import traceable
import httpx

from app.graph.state import AgentState
from app.graph.nodes.router import route_query
from app.graph.nodes.planner import plan_node
from app.graph.nodes.researcher import research_node
from app.graph.nodes.search_agent import search_agent_node, search_tool_node, route_after_tools
from app.graph.nodes.writer import write_node
from app.graph.nodes.reviewer import review_node
from app.graph.nodes.refiner import refine_node
from app.graph.nodes.chat_node import chat_node
from app.graph.nodes.data_collector import data_collector_node
from app.error_types import ErrorCode
from app.utils.logger import get_logger
from app.utils.streaming import emit_node_event

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
    emit_node_event("router", "start")
    t0 = _time.time()
    try:
        return route_query(state)
    finally:
        emit_node_event("router", "done", elapsed=_time.time() - t0)

@traceable(run_type="chain", name="planner")
async def traced_planner(state: AgentState):
    emit_node_event("planner", "start")
    t0 = _time.time()
    try:
        return await plan_node(state)
    finally:
        emit_node_event("planner", "done", elapsed=_time.time() - t0)

@traceable(run_type="chain", name="researcher")
def traced_researcher(state: AgentState):
    emit_node_event("researcher", "start")
    t0 = _time.time()
    try:
        return research_node(state)
    finally:
        emit_node_event("researcher", "done", elapsed=_time.time() - t0)

@traceable(run_type="chain", name="writer")
async def traced_writer(state: AgentState):
    emit_node_event("writer", "start")
    t0 = _time.time()
    try:
        return await write_node(state)
    finally:
        emit_node_event("writer", "done", elapsed=_time.time() - t0)
@traceable(run_type="chain", name="reviewer")
def traced_reviewer(state: AgentState):
    emit_node_event("reviewer", "start")
    t0 = _time.time()
    try:
        return review_node(state)
    finally:
        emit_node_event("reviewer", "done", elapsed=_time.time() - t0)

@traceable(run_type="chain", name="refiner")
async def traced_refiner(state: AgentState):
    emit_node_event("refiner", "start")
    t0 = _time.time()
    try:
        return await refine_node(state)
    finally:
        emit_node_event("refiner", "done", elapsed=_time.time() - t0)

@traceable(run_type="chain", name="chat")
async def traced_chat(state: AgentState):
    emit_node_event("chat", "start")
    t0 = _time.time()
    try:
        return await chat_node(state)
    finally:
        emit_node_event("chat", "done", elapsed=_time.time() - t0)

from app.graph.nodes.load_memories import load_memories_node


@traceable(run_type="chain", name="load_memories")
async def traced_load_memories(state: AgentState, *, store=None):
    emit_node_event("load_memories", "start")
    t0 = _time.time()
    mem_data = None  # 异常时 done 事件不带记忆数据，行为与旧版一致
    try:
        result = await load_memories_node(state, store=store)
        # 记忆条数随 done 事件透传前端（"已结合 N 条记忆"提示）
        mem_data = {"memories": list((result or {}).get("user_memories") or [])[:5],
                    "count": len((result or {}).get("user_memories") or [])}
    finally:
        emit_node_event("load_memories", "done", elapsed=_time.time() - t0,
                        data=mem_data)

@traceable(run_type="chain", name="search_agent")
def traced_search_agent(state: AgentState):
    emit_node_event("search_agent", "start")
    t0 = _time.time()
    try:
        return search_agent_node(state)
    finally:
        emit_node_event("search_agent", "done", elapsed=_time.time() - t0)

def traced_search_tools(state: AgentState):
    emit_node_event("search_tools", "start")
    t0 = _time.time()
    try:
        return search_tool_node(state)
    finally:
        emit_node_event("search_tools", "done", elapsed=_time.time() - t0)

@traceable(run_type="chain", name="data_collector")
def traced_data_collector(state: AgentState):
    emit_node_event("data_collector", "start")
    t0 = _time.time()
    try:
        return data_collector_node(state)
    finally:
        emit_node_event("data_collector", "done", elapsed=_time.time() - t0)

def _route_search_agent(state: AgentState) -> str:
    """Function Calling 路由：agent 决定调工具还是结束"""
    # 循环终止：超过最大轮次时强制结束
    if state.get("search_iteration", 0) >= 5:
        log.info("[FC路由] 搜索轮次已达上限 -> 提取结果 -> data_collector")
        return "route_after_tools"

    messages = state.get("messages", [])
    if not messages:
        log.warning("[FC路由] 无消息，跳过搜索")
        return "route_after_tools"

    last_msg = messages[-1]
    # 检查最后一条消息是否有工具调用
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        log.info(f"[FC路由] agent 请求 {len(last_msg.tool_calls)} 个工具调用 -> search_tools")
        return "search_tools"

    # 无工具调用 = agent 结束，提取结果
    log.info("[FC路由] agent 无工具调用 -> 提取结果 -> data_collector")
    return "route_after_tools"


def route_after_research(state: AgentState):
    """Researcher 结束后的交通指挥员：正常→search_agent，should_stop→END"""
    if state.get("should_stop", False):
        log.info("[路由] 检测到停止信号 (should_stop=True) -> 提前结束任务")
        return END
    else:
        return "search_agent"
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
_workflow.add_node("search_agent", traced_search_agent)
_workflow.add_node("search_tools", traced_search_tools)
_workflow.add_node("route_after_tools", route_after_tools)
_workflow.add_node("writer", traced_writer)
_workflow.add_node("reviewer", traced_reviewer)
_workflow.add_node("refiner", traced_refiner)
_workflow.add_node("data_collector", traced_data_collector)
_workflow.add_node("chat", traced_chat)

# START -> load_memories（长期记忆注入首节点，只读不路由）-> 条件路由 -> ...
_workflow.add_node("load_memories", traced_load_memories)
_workflow.set_entry_point("load_memories")
_workflow.add_conditional_edges(
    "load_memories",
    route_query,
    {
        "planner": "planner",
        "refiner": "refiner",
        "chat": "chat",
    }
)
_workflow.add_edge("planner", "researcher")
_workflow.add_conditional_edges(
    "researcher",
    route_after_research,
    {"search_agent": "search_agent", END: END}
)
_workflow.add_edge("chat", END)
_workflow.add_conditional_edges(
    "search_agent",
    _route_search_agent,
    {
        "search_tools": "search_tools",
        "route_after_tools": "route_after_tools"
    }
)
_workflow.add_edge("search_tools", "search_agent")
_workflow.add_edge("route_after_tools", "data_collector")
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

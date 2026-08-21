# IRIS 面试优化方案 — DeepSeek 设计讨论总结

> 讨论时间: 2026-08-17
> 讨论轮次: 3 轮（问题诊断 → 代码实现 → 补齐剩余）
> 讨论方式: browser-agent → DeepSeek 网页版

---

## 一、核心设计风险（面试官会猛攻的地方）

DeepSeek 在讨论中识别了 4 个系统级隐患，这是原方案没覆盖的：

### 1. 状态污染与幻觉级联（最致命）
- **问题**: 6 节点共享全局 State（LangGraph reducer 合并）。如果 researcher 误将 Tavily 返回的错误信息（403、空列表）写入 `research_results`，writer 会基于污染状态"一本正经地编造"
- **现有覆盖不足**: 熔断只覆盖"搜索是否相关"，不覆盖"工具返回内容的语义有效性"
- **修复**: 在 researcher 输出端加 **Validation Node**，检查 `tool_status`，失败时写入 `tool_status: 'unavailable'` 标记而非原始错误

### 2. 条件边死锁的经济性风险
- **问题**: reviewer → refiner → reviewer 循环。若 reviewer 连续 FAIL 且 refiner 每次只做微小改动，循环耗尽 Token 预算
- **现有覆盖不足**: 只有 `MAX_REVISIONS` 硬限制，缺少"改进幅度阈值"早停
- **修复**: 双重刹车——绝对步数上限（3 轮）+ **cosine 相似度早停**（相似度 > 0.95 强制跳出）

### 3. 硬截断破坏指令完整性
- **问题**: 记忆压缩的"硬截断"按字符长度暴力切分。若用户核心约束（如"必须引用 2026 年数据"）恰好在截断点之后，planner 丢失约束
- **修复**: 升级压缩策略——先用正则提取用户指令中的强制动词（"必须"、"禁止"），给这些句子打上高优先级标签，截断时优先保留高优先级片段

### 4. 可观测性盲区导致"盲修"
- **问题**: 没有 Trace 时，无法区分是 router 选错分支、researcher 超时、还是 reviewer 阈值过严
- **修复**: LangSmith 全链路追踪

---

## 二、架构选型决策

DeepSeek 给出 3 套方案对比：

| 方案 | 核心思路 | 优点 | 缺点 | 适配性 |
|------|---------|------|------|--------|
| **A: LangGraph 原生深度绑定（推荐）** | RetryPolicy/TimeoutPolicy + LangSmith + LangSmith Dataset + LLM-as-Judge | 零耦合，面试展示"懂官方最佳实践"；LangSmith 可从 Trace 一键生成 Eval 数据集 | 依赖 SaaS（有免费额度） | ⭐⭐⭐⭐⭐ |
| B: 自建轻量中间件 | tenacity + logging + ELK + 自定义评分脚本 | 无外部依赖 | 重复造轮子，缺少可视化，面试暴露"没接触过生产级工具链" | ⭐⭐ |
| C: 混合双写 | Trace 同时写 LangSmith + 本地文件 | 兼顾 Demo 和离线备灾 | 开发量翻倍，ROI 极低 | ⭐ |

**决策：闭眼选 A。** LangGraph 与 LangSmith 集成是"官方锁死"的，面试官一听就默认掌握了现代 Agent 工程标准。

---

## 三、优先级重新排序

DeepSeek 对原 P0/P1/P2 排序提出异议：

> "面试官的第一反应是'你的 Agent 敢上线吗？'。敢不敢上线取决于可观测性和容错，而不是 Eval（Eval 是上线后持续迭代的）。"

### 新优先级

| 优先级 | 模块 | 面试关键词 | 预计工时 | 理由 |
|--------|------|-----------|---------|------|
| **P0** | Observability (Trace) + 基础容错 (Retry/Timeout) | "生产可观测" + "弹性工程" | 1.5 天 | LangSmith 配置仅需 3 个环境变量，1 小时可见炫酷 Trace 界面；RetryPolicy 是 LangGraph 内置，10 行代码搞定。即时视觉冲击 |
| **P0** | Eval 数据集 + 2 个核心指标 | "效果闭环" | 2 天 | 不做全四支柱，只做有效性（LLM-as-Judge）+ 效率（步数/工具调用次数）。构建 20 个黄金用例即可 |
| **P1** | 结构化错误处理（降级语义） | "故障隔离" | 1 天 | error_handler 返回结构化错误码（DEGRADED_SEARCH / FALLBACK_LLM），前端展示不同 UI 状态；加入循环终止条件 |
| **P1** | 核心链路集成测试 | "变更安全" | 1.5 天 | 只测 happy path（研究→写作→评审→通过）+ 异常 path（搜索超时走降级） |
| **P2** | 前端 E2E 测试 + 其他 Eval 维度 | "锦上添花" | 2 天 | 面试前有余力再做 |

---

## 四、关键代码改动（IRIS 项目具体文件）

### 4.1 `backend/app/config.py` — LangSmith 环境变量

```python
# backend/app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# === LangSmith 可观测性 ===
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "iris-dev")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")  # 必须为 true
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

# 启动时自动设置环境变量（LangSmith SDK 自动读取）
if LANGSMITH_API_KEY:
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
```

### 4.2 `backend/app/error_types.py` — 新增结构化错误码

```python
# backend/app/error_types.py
from enum import Enum
from typing import Optional, Any

class ErrorCode(str, Enum):
    """IRIS 结构化错误码"""
    DEGRADED_SEARCH = "DEGRADED_SEARCH"          # 搜索降级（Tavily 不可用）
    FALLBACK_LLM = "FALLBACK_LLM"              # LLM 降级（主模型→备模型）
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"  # 工具执行失败
    VALIDATION_FAILED = "VALIDATION_FAILED"        # 输出校验失败
    RATE_LIMIT = "RATE_LIMIT"                      # 限流
    TIMEOUT = "TIMEOUT"                          # 超时
    UNKNOWN = "UNKNOWN"                        # 未知错误

class IrisError(Exception):
    """IRIS 结构化异常"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")

# 工厂函数
def degrade_search(reason: str, details: Optional[dict] = None) -> IrisError:
    return IrisError(ErrorCode.DEGRADED_SEARCH, reason, details)

def fallback_llm(reason: str, details: Optional[dict] = None) -> IrisError:
    return IrisError(ErrorCode.FALLBACK_LLM, reason, details)

def tool_execution_failed(tool_name: str, reason: str, details: Optional[dict] = None) -> IrisError:
    return IrisError(ErrorCode.TOOL_EXECUTION_FAILED, f"Tool {tool_name} failed: {reason}", details)

def validation_failed(field: str, reason: str, details: Optional[dict] = None) -> IrisError:
    return IrisError(ErrorCode.VALIDATION_FAILED, f"Validation failed for {field}: {reason}", details)
```

### 4.3 `backend/app/graph/graph.py` — Traceable + RetryPolicy + 条件边

```python
# backend/app/graph/graph.py
from langgraph.graph import StateGraph, END
from langgraph.types import RetryPolicy, TimeoutPolicy
from langsmith import traceable
import httpx

from app.graph.state import AgentState
from app.graph.nodes.router import route_query
from app.graph.nodes.planner import plan_node
from app.graph.nodes.researcher import research_node
from app.graph.nodes.writer import write_node
from app.graph.nodes.reviewer import review_node
from app.graph.nodes.refiner import refine_node
from app.error_types import ErrorCode

# === 重试策略 ===
retry_policy = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=10.0,
    jitter=True,
    retry_on=(
        httpx.TimeoutException,
        httpx.HTTPStatusError,
        ConnectionError,
        # 注意：不重试 4xx（权限错误、参数错误等）
    )
)

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

# === 条件边：循环终止逻辑 ===
MAX_ITERATIONS = 5

def should_continue(state: AgentState) -> str:
    """
    条件路由决策：
    1. 降级错误（DEGRADED_SEARCH / FALLBACK_LLM）→ 继续但标记 degraded
    2. 其他严重错误 → 终止
    3. reviewer 设置 early_stop 或 should_continue=False → 终止
    4. 达到最大迭代次数 → 终止
    5. 默认继续
    """
    # 1. 检查错误码
    error_code = state.get("error_code")
    if error_code:
        if error_code in (ErrorCode.DEGRADED_SEARCH, ErrorCode.FALLBACK_LLM):
            state["degraded"] = True
            return "continue"
        else:
            return "end"

    # 2. 早停检查（由 reviewer 设置）
    if state.get("early_stop") is True or state.get("should_continue") is False:
        return "end"

    # 3. 迭代次数限制
    iteration = state.get("revision_number", 0)
    if iteration >= MAX_ITERATIONS:
        return "end"

    return "continue"

# === 构建图 ===
_workflow = StateGraph(AgentState)

_workflow.add_node("router", traced_router)
_workflow.add_node("planner", traced_planner)
_workflow.add_node("researcher", traced_researcher, retry_policy=retry_policy)
_workflow.add_node("writer", traced_writer, retry_policy=retry_policy)
_workflow.add_node("reviewer", traced_reviewer)
_workflow.add_node("refiner", traced_refiner)

_workflow.set_conditional_entry_point(
    route_query,
    {"planner": "planner", "refiner": "refiner"}
)

_workflow.add_edge("planner", "researcher")
_workflow.add_edge("writer", "reviewer")
_workflow.add_edge("refiner", "END")

_workflow.add_conditional_edges(
    "reviewer",
    should_continue,
    {"planner": "planner", END: END}
)

def create_graph(memory=None, store=None):
    return _workflow.compile(checkpointer=memory, store=store)
```

### 4.4 `backend/app/graph/nodes/researcher.py` — Validation Node

```python
# backend/app/graph/nodes/researcher.py（新增 Validation Node）
from app.error_types import tool_execution_failed, ErrorCode

def research_node(state: AgentState):
    # ... 原有搜索逻辑 ...
    
    # === Validation Node：检查工具调用状态 ===
    tool_status = state.get("tool_status", {})
    failed_tools = [
        name for name, status in tool_status.items()
        if isinstance(status, dict) and status.get("success") is False
    ]
    
    if failed_tools:
        # 标记降级状态，供 writer 检测
        state["error_code"] = ErrorCode.DEGRADED_SEARCH
        state["degraded"] = True
        state["failed_tools"] = failed_tools
        # 不往 search_results 里写原始错误，而是写降级标记
        state["search_results"] = [
            f"[系统提示] 搜索服务暂时不可用（{', '.join(failed_tools)}），以下基于已有知识回答"
        ]
    else:
        state["error_code"] = None
        state["degraded"] = False
    
    return state
```

### 4.5 `backend/app/graph/nodes/reviewer.py` — Cosine 相似度早停

```python
# backend/app/graph/nodes/reviewer.py（新增 cosine 早停）
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def review_node(state: AgentState):
    current_report = state.get("final_report", "")
    report_history = state.get("report_history", [])
    
    # 空报告直接 FAIL
    if not current_report or len(current_report.strip()) < 50:
        return {
            "critique": "报告内容不完整或为空，请重新生成。",
            "revision_number": state.get("revision_number", 0) + 1,
            "review_status": "FAIL"
        }
    
    # 第一次审查，保留历史
    if not report_history:
        state["report_history"] = [current_report]
        state["should_continue"] = True
        return {
            "critique": "",
            "revision_number": state.get("revision_number", 0),
            "review_status": "PASS"
        }
    
    # === Cosine 相似度早停 ===
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([current_report, report_history[-1]])
    sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    
    state["report_history"].append(current_report)
    
    if sim > 0.95:
        # 相似度过高，说明 refiner 改不动了，早停
        state["early_stop"] = True
        state["should_continue"] = False
        return {
            "critique": f"连续两版报告相似度 {sim:.2f} > 0.95，判定为无法进一步改进，强制结束循环。",
            "revision_number": state.get("revision_number", 0) + 1,
            "review_status": "PASS"
        }
    
    # 原有审查逻辑
    # ... 调用 LLM 审查 ...
```

### 4.6 `backend/app/api/routes.py` — SSE 透传 Trace Context

```python
# backend/app/api/routes.py（SSE 端点改动）
from langsmith import get_current_run_tree
import uuid

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, req: Request):
    # ... 限流检查 ...
    
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # === LangSmith Trace Context ===
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "user_id": request.user_id or "anonymous",
            "session_id": thread_id,
        },
        "tags": ["production", "sse-stream"]
    }
    
    async def event_generator():
        # 获取当前 trace run_id，通过 SSE 第一条消息发送
        current_run = get_current_run_tree()
        run_id = str(current_run.id) if current_run else None
        yield f"data: {json.dumps({'type': 'trace', 'run_id': run_id})}\n\n"
        
        # 执行图，透传 config
        async for chunk in graph.astream(
            {"messages": [{"role": "user", "content": request.query}]},
            config=config,
            stream_mode="values"
        ):
            yield f"data: {json.dumps(chunk, default=str)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 4.7 `backend/tests/integration/test_router_fallback.py` — 新增集成测试

```python
# backend/tests/integration/test_router_fallback.py
import pytest
from unittest.mock import patch, MagicMock
from app.graph import create_graph
from app.graph.state import AgentState
from app.error_types import ErrorCode

@pytest.fixture
def graph():
    from app.graph.checkpoint import get_memory
    return create_graph(memory=get_memory())

def test_researcher_degraded_continues(graph):
    """测试 researcher 降级后，条件边继续但标记 degraded"""
    state = AgentState(
        query="test",
        error_code=ErrorCode.DEGRADED_SEARCH,
        degraded=True,
        revision_number=0,
    )
    # 验证降级错误不会终止循环
    from app.graph.graph import should_continue
    decision = should_continue(state)
    assert decision == "continue"
    assert state.get("degraded") is True

def test_tool_failure_ends_loop(graph):
    """测试工具执行失败（非降级错误）终止循环"""
    state = AgentState(
        query="test",
        error_code=ErrorCode.TOOL_EXECUTION_FAILED,
        degraded=False,
        revision_number=1,
    )
    from app.graph.graph import should_continue
    decision = should_continue(state)
    assert decision == "end"

def test_reviewer_early_stop(graph):
    """测试 reviewer cosine 相似度早停"""
    state = AgentState(
        query="test",
        early_stop=True,
        should_continue=False,
        revision_number=2,
    )
    from app.graph.graph import should_continue
    decision = should_continue(state)
    assert decision == "end"

def test_max_iterations_ends(graph):
    """测试达到最大迭代次数终止"""
    state = AgentState(
        query="test",
        revision_number=5,  # MAX_ITERATIONS = 5
    )
    from app.graph.graph import should_continue
    decision = should_continue(state)
    assert decision == "end"
```

---

## 五、面试话术弹药

### 对抗状态污染
> "我会在 researcher 输出端加一个校验节点（Validation Node），如果 Tavily 返回空或报错，不往 State 里写原始错误，而是写一个 `tool_status: 'unavailable'` 标记，writer 检测到该标记自动切换到'基于内部知识回答'模式。这比单纯重试更进一步。"

### 对抗循环死锁
> "我为 review-refine 循环设置了双重刹车：绝对步数上限（3 轮）和 cosine 相似度早停——如果 refiner 改动前后相似度 > 0.95，说明改不动了，强行跳出循环。"

### 对抗硬截断丢指令
> "我升级了压缩策略：不是无脑硬截，而是先用正则提取用户指令中的强制动词（'必须'、'禁止'），给这些句子打上高优先级标签，截断时优先保留高优先级片段。"

### 面试最高级叙事
> "我的熔断和压缩是'稳定性的左膀'，Trace 和 Eval 是'可观测性的右臂'，而 Retry 和结构化错误是'韧性的血管'。三套系统协同，才构成完整的 Agent 生命体征监测。"

---

## 六、2 周冲刺时间线

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | LangSmith 集成 + RetryPolicy | Trace 界面截图录屏 |
| Day 3-4 | 20 个 Golden Case + Eval Runner | 评测综合分 |
| Day 5-6 | 结构化错误码 + 循环终止条件 | `error_types.py` + `should_continue` 重构 |
| Day 7-8 | 集成测试（happy path + 降级 path） | CI 绿标 |
| Day 9-10 | Cheatsheet 整理 | 1 页面试速查表 |

---

## 七、关键决策记录

| # | 决策 | 选择 | 理由 | 权衡 |
|---|------|------|------|------|
| 1 | 架构方案 | A: LangGraph 原生深度绑定 | 面试官认可工业标准，零耦合 | 依赖 LangSmith SaaS（有免费额度） |
| 2 | P0 排序 | Observability + 容错 > Eval | 面试第一印象是"敢不敢上线" | Eval 是上线后迭代 |
| 3 | 循环终止 | 步数上限 + cosine 早停 | 双重保险，避免 Token 爆炸 | cosine 计算增加少量延迟 |
| 4 | 状态污染 | Validation Node 而非重试 | 防止错误信息污染 State | 增加一个节点，图拓扑更复杂 |
| 5 | 错误码 | 结构化 Enum + 工厂函数 | 前端可展示不同 UI 状态 | 需要改条件边逻辑 |

---

## 八、开放问题

- [ ] LangSmith 免费额度是否够用？（个人项目应该够）
- [ ] 是否需要同时集成 AgentOps 作为备选？
- [ ] 前端测试是否用 Playwright 而非 Vitest？
- [ ] 是否需要支持离线评测（CI 无网络时）？

---

## 九、讨论产出文件

| 文件 | 内容 |
|------|------|
| `deepseek_round1_strategy.md` | 第 1 轮：问题诊断 + 架构选型 + 优先级重排 |
| `deepseek_round2_code.md` | 第 2 轮：P0 Observability + Function Calling 容错代码 |
| `deepseek_round3_full.md` | 第 3 轮：error_types.py + 条件边 + 集成测试代码 |
| `design-discussion-summary.md` | 本文档：完整讨论总结 |

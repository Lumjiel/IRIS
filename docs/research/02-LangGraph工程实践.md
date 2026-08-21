# LangGraph 多 Agent 工程实践调研（真实项目验证）

> 调研目标：四个技术点在真实项目中被验证过的做法 —— 每个点给出「项目名 + 做法 + 可复现的代码/步骤 + 来源 URL」。
> 主要一手来源：LangGraph/LangChain 官方文档与仓库、langchain-ai 官方博客、真实开源项目源码、AWS/Microsoft/OWASP/Anthropic 工程博客。

---

## 1. Function Calling 正确姿势：ToolNode + bind_tools

### 1.1 官方标准模式（三节点 ReAct 环）

LangGraph 官方 Quickstart 与官方 tool-calling 教程中，标准模式是固定的三个节点 + 一个条件边：

```
agent(model 节点, 带 bind_tools 的 model) → conditional edge(检查最后一条消息是否有 tool_calls)
  ├─ 有 tool_calls → tools 节点(ToolNode) → 回到 agent
  └─ 无 tool_calls → END
```

可复现代码（官方 Quickstart / `libs/cli/examples/graphs/agent.py` 同款）：

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END, MessagesState
from langchain.chat_models import init_chat_model

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

tools = [add]
model_with_tools = init_chat_model("...").bind_tools(tools)  # ① 关键一步
tool_node = ToolNode(tools)                                   # ② prebuilt 工具执行节点

def call_model(state: MessagesState):
    return {"messages": [model_with_tools.invoke(state["messages"])]}

def should_continue(state: MessagesState):                    # ③ 条件边 = 循环终止逻辑
    last_message = state["messages"][-1]
    return "tools" if last_message.tool_calls else END

builder = StateGraph(MessagesState)
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)
builder.set_entry_point("agent")
builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "tools": "agent"})
# 实际写法：builder.add_edge("tools", "agent")
```

要点（官方文档/源码确认）：
- **`model.bind_tools(tools)` 是唯一把工具暴露给 LLM 的正确姿势**；ToolNode 执行 `last AIMessage` 里的 tool_call，**支持并行执行多个 tool call**，已在 `libs/prebuilt/langgraph/prebuilt/tool_node.py` 实现 [Source](https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/langgraph/prebuilt/tool_node.py)。
- **错误处理是默认内置的**：ToolNode 默认 `handle_tool_errors=True`，工具抛异常会被包装成 `ToolMessage(status="error")` 送回 LLM 让它自纠错，而不是让整个图崩溃；PR #1667 还允许只针对特定异常处理 [Source](https://github.com/langchain-ai/langgraph/pull/1667)。
- 循环必须靠条件边路由到 END，否则触发 `recursion_limit`（默认 25）报 `GraphRecursionError`。

### 1.2 真实项目：JoshuaC215/agent-service-toolkit（LangGraph 社区最流行的生产模板）

**做法**：`src/agents/research_assistant.py` 完整复刻标准模式，并加了三个生产级细节：

```python
# ① 用 RunnableLambda 前置 SystemMessage + bind_tools —— 系统提示与工具绑定合成为一个 runnable
def wrap_model(model: BaseChatModel) -> RunnableSerializable[AgentState, AIMessage]:
    bound_model = model.bind_tools(tools)
    preprocessor = RunnableLambda(
        lambda state: [SystemMessage(content=instructions)] + state["messages"],
        name="StateModifier",
    )
    return preprocessor | bound_model

# ② 用 LangGraph managed value 做步数看门狗，防止工具循环烧钱
class AgentState(MessagesState, total=False):
    safety: SafeguardOutput
    remaining_steps: RemainingSteps   # managed: 每步自动递减

async def acall_model(state, config):
    response = await model_runnable.ainvoke(state, config)
    if state["remaining_steps"] < 2 and response.tool_calls:   # 步数不足时截断并礼貌拒绝
        return {"messages": [AIMessage(id=response.id,
                content="Sorry, need more steps to process this request.")]}
    return {"messages": [response]}

# ③ 条件边路由：有 tool_calls → tools；否则 END
def pending_tool_calls(state) -> Literal["tools", "done"]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "done"

agent.add_conditional_edges("model", pending_tool_calls, {"tools": "tools", "done": END})
```

- 结构：`guard_input → model ↔ tools（循环）→ END`，中间插了 Safeguard 安全审查节点；入口与条件边分开建（`set_entry_point` + `add_conditional_edges`）[Source](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/src/agents/research_assistant.py)
- **效果**：项目 1k+ stars，被大量拷贝为生产模板；工具循环有 `RemainingSteps` 兜底、有安全审查、模型可热切换（`config["configurable"]["model"]`），实测不会再出现"工具把自己卡死"类事故。
- GitHub MCP agent 走的是更高层的 `create_agent(model, tools=...)` prebuilt 路径 [Source](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/src/agents/github_mcp_agent/github_mcp_agent.py)

**其他官方资料**：LangGraph 官方「Add tools」教程 [Source](https://langchain-ai.github.io/langgraph/tutorials/get-started/2-add-tools/)；Quickstart [Source](https://docs.langchain.com/oss/python/langgraph/quickstart)；`libs/cli/examples/graphs/agent.py` [Source](https://github.com/langchain-ai/langgraph/blob/main/libs/cli/examples/graphs/agent.py)。

---

## 2. 记忆系统设计：短期(thread) vs 长期(store) 的混用

### 2.1 官方定义的两种记忆（必须分开，不能混为一谈）

- **短期记忆** = thread 维度：消息历史 + 图状态，靠 **checkpointer** 持久化，thread 内可恢复/续聊。
- **长期记忆** = 跨 thread：任意 namespace 下的 KV 文档，靠 **store**（`BaseStore`：`InMemoryStore` / `PostgresStore` / `AsyncPostgresStore`），任何 thread 都能读写 [Source](https://docs.langchain.com/oss/python/langgraph/add-memory) [Source](https://docs.langchain.com/oss/python/langgraph/stores)。

官方明确区分两类记忆"fail in different ways，多数记忆 bug 源于把它们当一件事处理"（社区实践文章也反复印证这点）[Source](https://folarin.dev/blog/agent-memory-short-term-vs-long-term)。

长期记忆官方推荐写入方式有两种（LangMem）：
1. **Hot path**：agent 主动用 `manage_memory` 工具在对话中显式保存笔记；
2. **Background**：后台自动从对话抽取记忆（LangMem background 模式）[Source](https://langchain-ai.github.io/langmem/hot_path_quickstart/) [Source](https://github.com/langchain-ai/langmem)。

### 2.2 真实项目混用：agent-service-toolkit（Postgres 双通道）

`src/memory/postgres.py` 同时初始化 **checkpointer（短期）** 和 **store（长期）**，共享同一个 psycopg 连接池，关键约束都写死了：`autocommit=True`、`row_factory=dict_row`（LangGraph 强要求）[Source](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/src/memory/postgres.py)：

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore

# 短期记忆通道：AsyncPostgresSaver(pool)，服务层逐 thread 读写（/threads 列出历史会话）
checkpointer = AsyncPostgresSaver(pool)
await checkpointer.setup()

# 长期记忆通道：AsyncPostgresStore(pool)，跨会话/按 namespace 存取
store = AsyncPostgresStore(pool)
await store.setup()

# 编译时两个都挂上 → graph 同时获得 thread 续聊 + 跨 session 记忆
graph = agent.compile(checkpointer=checkpointer, store=store)
```

- **做法**：`/threads` 端点列出每个 agent 的历史会话（短期记忆的人工可见面），README 明确把 "human in the loop、long-term memory with Store" 列为特性；store 不塞进每个 agent，而是按需在服务层注入。
- **效果**：短期记忆支持多轮对话/断点续聊，长期记忆支持跨会话；两套通道生命周期、作用域、数据库表都隔离，出问题（比如该跨会话的没跨）能一眼定位是哪个通道。

### 2.3 官方可复现代码（混用最小骨架）

```python
from langgraph.store.memory import InMemoryStore
from langgraph.graph import MessagesState

store = InMemoryStore()          # 生产换成 PostgresStore/AsyncPostgresStore
builder = StateGraph(MessagesState)
graph = builder.compile(store=store)   # store 自动注入到节点签名 Runtime

# 节点内主动写入长期记忆：
def remember(state):
    runtime = get_runtime()      # store 通过 Runtime 注入
    runtime.store.put(
        ("users", user_id),      # namespace 决定作用域，跨 thread 共享
        "preferences",
        {"theme": "dark", "lang": "zh"},
    )
    return {}

# 唤起（官方 memory 教程模式）：先 retrieve 再放进 system prompt
```

### 2.4 混用要点/坑（实测教训）

- **坑 1：把 checkpointer 当长期记忆** —— thread 过期/换 ID 就失忆，跨会话检索只能靠 store。官方语义检索发布也是基于 store（PostgresStore/InMemoryStore 支持语义搜索）[Source](https://www.langchain.com/blog/semantic-search-for-langgraph-memory)。
- **坑 2：store 不设置 namespace 隔离** —— 多租户串数据（官方文档明确 namespace 是隔离手段）。
- **坑 3：每次对话都全量载入长记忆** —— 爆 context；正确姿势是 retrieve 后按相关性放 system prompt，只取最相关若干条 [Source](https://docs.langchain.com/oss/python/langgraph/add-memory)。

---

## 3. 评审/反馈循环（Reviewer）在真实项目里的形态与防死循环

### 3.1 官方参考实现

- **langchain-ai/langgraph-reflection**（官方 prebuilt）：main agent + critique agent 两个子代理；critique 有意见就返回一条 **user 消息**继续循环，无意见返回 **None** 即终止；提供 LLM-as-judge 与 Pyright 校验两个例子 [Source](https://github.com/langchain-ai/langgraph-reflection)。
- 官方 Reflection 博客给出基础版（`MessageGraph`，用 **消息条数** 当循环上限：`if len(state) > 6: return END`）和 Reflexion（**显式 `MAX_ITERATIONS = 5`** 计数）[Source](https://www.langchain.com/blog/reflection-agents)。
- 官方 Reflection 教程（内置完整可运行代码）[Source](https://langchain-ai.github.io/langgraph/tutorials/reflection/reflection/)。

### 3.2 真实项目形态（按如何"判定合格"分三类）

**(A) 评分阈值式（最常见）—— tathadn/multi-agent-codegen**
- 流水线：Orchestrator → Planner → Coder → **Reviewer（打分 0–10）** → Tester（Docker 沙箱跑 pytest）→ 条件边回 Coder。
- 判合格：`Review 通过 且 测试全绿` → COMPLETED；否则回 Coder 带上 reviewer 意见 + 测试失败上下文修订。
- **防死循环是核心卖点**：state 里显式放 `iteration` 和 `max_iterations`（默认 3、UI 可调），并用 `utils/budget.py` 做硬性 token 费用上限防"跑飞"（超预算直接抛 `BudgetExceeded`）[Source](https://github.com/tathadn/multi-agent-codegen)。

```python
class AgentState(BaseModel):
    user_request: str
    plan: Optional[Plan]
    artifacts: list[CodeArtifact]
    review: Optional[ReviewFeedback]
    test_result: Optional[TestResult]
    status: TaskStatus
    iteration: int                # 防死循环核心：计数器放 state
    max_iterations: int

def should_continue(state):
    if state.review.approved and state.test_result.passed:
        return "end"              # → COMPLETED
    if state.iteration >= state.max_iterations:
        return "end"              # 达到上限也强制结束（宁可交差不可死循环）
    return "coder"
```

**(B) 确定性外部检验式 —— 官方 coding.py（Pyright）与 smart-pr-review-agent**
- langgraph-reflection 的 `examples/coding.py`：生成代码 → **Pyright 静态检查**，错误原文送回 main agent 修正，直到通过 [Source](https://github.com/langchain-ai/langgraph-reflection)。
- kushalsai-01/smart-pr-review-agent：Indexer → Reviewer → Bug Hunter → Issue Raiser → Fix Drafter，reviewer 产出结构化 review、交给 `approval` 判断；提供 **Review Only / Human-in-Loop / Auto Pilot** 三模式，HITL 模式靠 LangGraph checkpoint 暂停等人工审批，天然免疫死循环 [Source](https://github.com/kushalsai-01/smart-pr-review-agent)。

**(C) 多人/多模型投票式 —— magi-ai/opencode-magi**
- 多个模型各自独立审查同一 PR，**奇数个模型过半数才批准/打回**，降低单模型误判导致的无效循环 [Source](https://github.com/magi-ai/opencode-magi)。

另见：planner→executor→reviewer 参考实现（明确 "bounded retries"）[Source](https://github.com/kanaparthikiran/multi-agent-langgraph-demo)；Reviewer/Fixer/Evaluator 三代理 + SSE 流式（评估者可以打回 Fixer，触发第二轮修复）[Source](https://github.com/eholt723/agentmesh)。

### 3.3 防死循环手段汇总（在真实项目/官方均被验证）

| 手段 | 出处 |
|---|---|
| `iteration` 计数器放 state + `max_iterations`（默认 3~5），超限强制 END | multi-agent-codegen；官方 Reflexion `MAX_ITERATIONS=5` |
| 用消息条数/步数当硬上限（`len(state) > 6`；`RemainingSteps` managed value） | 官方 Reflection 博客；agent-service-toolkit |
| Reviewer 输出**结构化评分 + approved 布尔值**而不是开放意见，低于阈值才修订 | multi-agent-codegen reviewer |
| 用**可验证的外部裁判**（Pyright、Docker 沙箱测试、真实 web 搜索引用）让"合格"客观可判，避免纯 LLM 主观循环 | langgraph-reflection/coding.py；官方 Reflexion（强制引用） |
| HITL：关键步骤 interrupt 等人工确认 | smart-pr-review-agent；LangGraph interrupt 机制 |
| `recursion_limit`（默认 25）作为最后兜底 + 合理调大 | [GraphRecursionError 教程](https://www.agentnotebook.dev/tutorials/langgraph-recursion-limit)；官方正计划出生产可靠性 RFC：[langgraph#6617](https://github.com/langchain-ai/langgraph/issues/6617)（无限循环是真实项目常见事故，见 [langgraph#6731](https://github.com/langchain-ai/langgraph/issues/6731)） |

---

## 4. MCP 集成：核心还是锦上添花？教训案例

### 4.1 真实项目里的定位

**结论：MCP 是"锦上添花"式的集成层，不是 agent 的默认核心** —— 两个真实项目正好形成对照：

- **agent-service-toolkit（github-mcp-agent）**：MCP 是**可选能力**。`GITHUB_PAT` 未配置时 agent 照样加载运行（`self._mcp_tools = []`），配置了才连 `MultiServerMCPClient` + `StreamableHttpConnection` 拉工具；错误处理里 **MCP 初始化失败也只是打日志降级，绝不拖垮整个 agent**。且与全体 agent 解耦（按需懒加载 `LazyLoadingAgent`）[Source](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/src/agents/github_mcp_agent/github_mcp_agent.py)
- **smart-pr-review-agent（GitHub MCP 为核心之一）**：MCP 是其架构组成（GitHub API 全靠 `https://api.githubcopilot.com/mcp/` over Streamable HTTP），但其价值核心是 RAG + tree-sitter + LangGraph 编排，MCP 只是"接入 GitHub 的传输层"，且全程 LangSmith 追踪 **每个 MCP tool call** 以便审计 [Source](https://github.com/kushalsai-01/smart-pr-review-agent)

官方接入代码（langchain-mcp-adapters，Python/JS 双版本）[Source](https://github.com/langchain-ai/langchain-mcp-adapters)：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({
    "github": {
        "transport": "streamable_http",
        "url": settings.MCP_GITHUB_SERVER_URL,
        "headers": {"Authorization": f"Bearer {github_pat}"},   # 运行时 header 鉴权
    }
})
tools = await client.get_tools()        # MCP 工具 → 标准 LangChain 工具
agent = create_agent(model, tools)      # 再走标准 ToolNode/bind_tools 路径
# 默认 handle_tool_errors=True：MCP 执行错误(isError)送回模型自纠错，不崩溃
```

### 4.2 过度集成的教训案例（有量化数据的经验帖）

1. **MCP Context Tax（工具定义吃掉 context）**：Anthropic 官方工程博客确认 "tool results and definitions can sometimes consume **50,000+ tokens** before an agent reads a request"；GitHub Copilot 的官方 MCP server 单个就暴露 **96 个工具** [Source](https://www.anthropic.com/engineering/advanced-tool-use) [Source](https://tetrate.io/learn/ai/mcp/tool-filtering-performance)。Pipeworx 托管 605 工具包 ≈ 2,761 个工具，实测体会是"在读到用户问题前已经付了数万 token 的工具定义税" [Source](https://pipeworx.io/blog/mcp-context-tax-tool-routing/)。
2. **工具数量越大，选择准确率崩得越狠**：Writer 团队 RAG-MCP benchmark 实测——完整工具集下工具选择准确率仅 **13.62%**，检索只暴露相关子集后升至 **43%**（模型没换、工具没换）[Source](https://tianpan.co/blog/2026-04-19-over-tooled-agent-problem)；综合多来源结论：**约 50 个工具开始明显下滑、超过 ~120 个接近崩坏** [Source](https://getunblocked.com/blog/mcp-tool-overload/)。
3. **Tool-space interference（工具相互干扰）**——微软研究院基于 MCP server 生态调研：工具/agent 共存时可能出现更长的行动序列、更高 token 成本、脆弱恢复甚至任务失败；且 "MCP servers do not know which clients or models" 调它，设计时完全不可见 [Source](https://www.microsoft.com/en-us/research/blog/tool-space-interference-in-the-mcp-era-designing-for-agent-compatibility-at-scale/)。
4. **安全是硬伤**：OWASP 出官方 MCP Security Cheat Sheet 与 "MCP Tool Poisoning"（间接提示注入——恶意 server 的返回内容伪装成可信指令）[Source](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) [Source](https://owasp.org/www-community/attacks/MCP_Tool_Poisoning)；arXiv 有研究指出协议级缺陷（双向 sampling 无来源认证等）[Source](https://arxiv.org/html/2601.17549)。
5. **生产部署翻车实录**：SSE 传输被弃用、HTTP+SSE 要求常驻长连接；"requests die silently"（既不返回结果也不报错）；auth/scopes 逐个授权很痛苦 [Source](https://ibanforge.com/en/blog/2026-07-03-mcp-server-in-production-what-breaks) [Source](https://tianpan.co/blog/2025-10-27-mcp-in-production) [Source](https://mrdib.com/blog/articles/mcp-servers-production-lessons-learned.html)。

### 4.3 被验证的缓解姿势

- **把 MCP 当基础设施，不塞进每个 agent**：MCP 位于 LangGraph state 与数据源之间（"不是图的一部分，而是图用的基础设施"）；本地工具（calculator 等）仍走原生 bind_tools [Source](https://ranjankumar.in/implementing-mcp-with-langgraph-a-practical-walkthrough)
- **工具接入前重新设计，不裸贴上游 API**：AWS 明确"为 LLM 设计工具"——工具数量要"恰到好处"，接口、schema、说明都为 agent 使用重写（瘦身聚合、分层）[Source](https://aws.amazon.com/blogs/machine-learning/mcp-tool-design-practical-approaches-and-tradeoffs/) [Source](https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/mcp-tool-strategy.html)
- **按需/延迟加载工具**：Anthropic 推出 Tool Search + deferred loading（按任务只暴露相关子集，几千个工具不占 context）[Source](https://www.anthropic.com/engineering/advanced-tool-use)
- **agent-service-toolkit 式降级设计**：MCP 不可用 → 工具列表清空、agent 继续跑；每个 MCP tool call 进 LangSmith 审计 [Source](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/src/agents/github_mcp_agent/github_mcp_agent.py)

---

## 来源汇总

### Kept（一手/高价值）
1. LangGraph Quickstart — https://docs.langchain.com/oss/python/langgraph/quickstart（官方标准三节点 agent 代码）
2. LangGraph Add tools 教程 — https://langchain-ai.github.io/langgraph/tutorials/get-started/2-add-tools/（bind_tools + ToolNode 官方示范）
3. langgraph 仓库 `libs/prebuilt/.../tool_node.py` — https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/langgraph/prebuilt/tool_node.py（ToolNode 实现，含 handle_tool_errors）
4. langgraph PR #1667 — https://github.com/langchain-ai/langgraph/pull/1667（ToolNode 错误处理演进）
5. JoshuaC215/agent-service-toolkit — https://github.com/JoshuaC215/agent-service-toolkit（源码：src/agents/research_assistant.py、src/memory/postgres.py、src/agents/github_mcp_agent/github_mcp_agent.py）
6. LangGraph Memory 文档 — https://docs.langchain.com/oss/python/langgraph/add-memory（短/长期记忆官方定义与推荐代码）
7. LangGraph Stores 文档 — https://docs.langchain.com/oss/python/langgraph/stores（跨 thread store 语义）
8. LangChain 官方博客：Long-Term Memory Launch — https://www.langchain.com/blog/launching-long-term-memory-support-in-langgraph；Semantic Search for Store — https://www.langchain.com/blog/semantic-search-for-langgraph-memory
9. LangMem — https://github.com/langchain-ai/langmem；Hot Path Quickstart — https://langchain-ai.github.io/langmem/hot_path_quickstart/
10. folarin.dev 短/长期记忆辨析 — https://folarin.dev/blog/agent-memory-short-term-vs-long-term（"多数记忆 bug 源于二者混用"经验贴）
11. langchain-ai/langgraph-reflection — https://github.com/langchain-ai/langgraph-reflection（官方 review loop prebuilt + Pyright 样例）
12. Reflection Agents 博客 — https://www.langchain.com/blog/reflection-agents（基础/Reflexion/LATS 三种循环 + MAX_ITERATIONS 代码）
13. tathadn/multi-agent-codegen — https://github.com/tathadn/multi-agent-codegen（评分阈值 + max_iterations + budget 防死循环实例）
14. kushalsai-01/smart-pr-review-agent — https://github.com/kushalsai-01/smart-pr-review-agent（LangGraph+RAG+GitHub MCP 的 PR review 循环，三模式）
15. magi-ai/opencode-magi — https://github.com/magi-ai/opencode-magi（多模型多数决）
16. kanaparthikiran/multi-agent-langgraph-demo — https://github.com/kanaparthikiran/multi-agent-langgraph-demo（planner/executor/reviewer + bounded retries）
17. langchain-ai/langchain-mcp-adapters — https://github.com/langchain-ai/langchain-mcp-adapters（官方 MCP→LangGraph 集成代码）
18. Anthropic Advanced tool use — https://www.anthropic.com/engineering/advanced-tool-use（50k token 工具开销 + tool search 缓解）
19. Microsoft Research Tool-space interference — https://www.microsoft.com/en-us/research/blog/tool-space-interference-in-the-mcp-era-designing-for-agent-compatibility-at-scale/
20. AWS MCP tool design（含 tool 数量权衡图）— https://aws.amazon.com/blogs/machine-learning/mcp-tool-design-practical-approaches-and-tradeoffs/ 与 https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/mcp-tool-strategy.html
21. The Over-Tooled Agent Problem — https://tianpan.co/blog/2026-04-19-over-tooled-agent-problem（13.62%→43% 实测数据）
22. MCP Tool Overload — https://getunblocked.com/blog/mcp-tool-overload/（50/120 工具阈值汇总）
23. OWASP MCP Security Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html；MCP Tool Poisoning — https://owasp.org/www-community/attacks/MCP_Tool_Poisoning
24. MCP 协议安全分析 — https://arxiv.org/html/2601.17549
25. IBANforge MCP in production — https://ibanforge.com/en/blog/2026-07-03-mcp-server-in-production-what-breaks；tianpan 生产复盘 — https://tianpan.co/blog/2025-10-27-mcp-in-production

### Dropped（相关性/质量不足）
- 多个"入门教程型"第三方博客（crewship/algomart/medium 等）——内容与官方文档重复且无新证据
- LangModule/langgraph-postgres-memory、aayushmaanhooda/LongTermMemoryLangGraph——小型封装/教学项目，证据价值低于 agent-service-toolkit
- madtank/agent-service-toolkit fork——加 MCP 的派生项目，无法代表原项目实践
- 部分厂商软文（barndoor/tetrate/pipeworx）——只取其中的量化事实与行业公认数据，不采信其产品方案

---

## Gaps（未能完全回答/存疑处）

1. 「MCP 在真实项目里核心 vs 锦上添花」缺少大规模生产系统的一手调研（本文依赖两个有代表性的开源项目 + 企业博客的数据点；GitHub Copilot/Cursor 内部如何使用 MCP 没有公开代码）。
2. Review 循环的"防死循环"缺乏公开的失败基准数据（哪些阈值/轮次在哪些任务上最优）——各项目都是启发式设置（2~6 轮），无对比实验。
3. agent-service-toolkit 的 store 具体写入逻辑（哪个节点、什么 namespace、写什么）未逐行核实（README 声明了该特性并有 postgres store 基建，但 store 的调用点分布在 service 层）。

**建议下一步**：若需要更硬的证据，可以 (a) 拉取 agent-service-toolkit 仓库搜索 `store.` 调用点；(b) 在 LangSmith / GitHub 搜 langgraph 项目跑分评测；(c) 直接向 langchain 社群要 MCP 生产事故案例。
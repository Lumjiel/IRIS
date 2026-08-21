# Research: LangGraph 两条落地路径的实现细节（到可抄代码的程度）

## Summary

两条路径都已被 langchain 官方项目验证：(1) 工具调用迁移的权威样板是官方 Quickstart（Calculator Agent）与仓库内 `examples/tool-calling.ipynb`，核心只有 4 步：`@tool` 声明 → `model.bind_tools(tools)` → 挂 `ToolNode` → 用 `tools_condition` 替换手写 if/else 路由；time travel（replay/fork）由 `libs/langgraph/tests/test_time_travel.py` 覆盖验证。(2) 记忆系统官方教程即 `docs.langchain.com/oss/python/langgraph/add-memory`（短期=checkpointer，长期=store），一个 resume 项目做到"checkpointer 多轮 + store 单 namespace 读写 + 注入上下文"即算完整，实体图谱/记忆衰减/语义索引等都是可选项、不做得"过度"。

注意：旧的 `langchain-ai.github.io/langgraph` 教程大部分已 404/下线，权威源现在是 `docs.langchain.com/oss/python/langgraph/*`；GitHub Pages 内容在 mintlify.wiki 有镜像（内容与官方一致，仅用于抄代码）。

---

## Findings（含代码骨架与来源）

### 路径 1：从硬编码调工具 → Function Calling + ToolNode 的最小迁移

**迁移前（要删掉的模式）**：在节点里用 if/else 判断意图再调函数，比如 `if "天气" in query: return weather(q)`，LLM 不参与决策、输出靠硬解析。

**迁移后（官方 Quickstart 模式，4 件事）**：

```python
# ---- ① 工具声明：@tool 自动生成 JSON schema（bind_tools / ToolNode 都消费它）----
from langchain.tools import tool

@tool
def add(a: int, b: int) -> int:
    """相加 a 和 b。"""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """相乘 a 和 b。"""
    return a * b

tools = [add, multiply]
tools_by_name = {t.name: t for t in tools}   # 官方教程的做法：按名字查工具

# ---- ② Function Calling：把工具声明绑给模型（模型只"说要调"，不执行）----
from langchain.chat_models import init_chat_model

model = init_chat_model("claude-sonnet-4-6", temperature=0)  # 官方 quickstart 用的模型
model_with_tools = model.bind_tools(tools)

# ---- ③ 图骨架：add_node / add_edge / add_conditional_edges 全在这里 ----
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

builder = StateGraph(MessagesState)
builder.add_node("chatbot", model_with_tools)                   # 模型节点：产出 AI message + tool_calls
builder.add_node("tools", ToolNode(tools))                      # 官方执行器替代手写 if/else
builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", tools_condition)       # 有 tool_calls → "tools"，否则 → END
builder.add_edge("tools", "chatbot")                            # 工具结果回喂模型 → 形成循环
graph = builder.compile()
```

- `tools_condition` 的等价手写函数（官方 add-tools 教程原文逻辑）：

```python
def should_continue(state) -> str:
    if state["messages"][-1].tool_calls:
        return "tools"
    return END
```

- 想不依赖 `ToolNode`、展示机制细节时，官方教程给的手写 node（**必须回传 `tool_call_id`**，否则 OpenAI/Anthropic 方报 message 校验错误）：

```python
import json
from langchain_core.messages import ToolMessage

def tool_node(state: dict) -> dict:
    outputs = []
    for tool_call in state["messages"][-1].tool_calls:
        result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        outputs.append(ToolMessage(
            content=json.dumps(result),
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        ))
    return {"messages": outputs}
```

**迁移核对清单（照着改就行）**：
1. 工具函数加 `@tool`（docstring 写清楚参数语义，这就是 schema）。
2. 节点里删掉意图 if/else；只保留 `model.bind_tools(tools)` 后的模型调用。
3. `builder.add_node("tools", ToolNode(tools))` + `add_conditional_edges("chatbot", tools_condition)`。
4. 原"工具结果拼接"逻辑如果测试里依赖，改成断言 `messages[-1].tool_calls` / ToolMessage 内容。

**时间旅行（调试/演示必备，官方 how-to + 仓库测试验证的 API 形状）**：

```python
from langgraph.checkpoint.memory import InMemorySaver

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "1"}}
graph.invoke(initial_input, config)

# ① 列出该 thread 全部 checkpoint（按时间倒序，含 metadata.step）
for snapshot in graph.get_state_history(config):
    print(snapshot.metadata.get("source"), snapshot.config["configurable"]["checkpoint_id"])

# ② Replay：拿某个 checkpoint 的 config 重新跑，只重执行该点之后的节点
replay_config = {"configurable": {"thread_id": "1",
                                  "checkpoint_id": target.config["configurable"]["checkpoint_id"]}}
for event in graph.stream(None, replay_config, stream_mode="values"):
    ...

# ③ Fork：在旧 checkpoint 上 update_state 改状态，再继续执行（探索另一条路）
fork_config = {"configurable": {"thread_id": "1",
                                "checkpoint_id": target.config["configurable"]["checkpoint_id"]}}
graph.update_state(fork_config, {"messages": [{"role": "user", "content": "改过的输入"}]})
for event in graph.stream(None, fork_config, stream_mode="values"):
    ...
```

官方文档原文验证了这三个 API 的语义："Invoke the graph with a prior checkpoint's config to replay"、“Call `update_state` on a prior checkpoint to create the fork, then `invoke` with `None`”。注意：fork 后不要给原 checkpoint 传 `pending_writes`，节点会以无缓存的干净状态重跑；子图默认只有一个父级超步 checkpoint（要穿过子图内部只能给子图自己配 checkpointer）。

**验证状态（哪些被官方项目验证过）**：
- `ToolNode` / `tools_condition` / `bind_tools` 模式：官方 Quickstart Calculator Agent + 仓库内 `examples/tool-calling.ipynb`；prebuilt 库自带完整单测 `libs/prebuilt/tests/test_tool_node.py`（涵盖 InjectedState/InjectedStore 注入、ValidationError 过滤、拦截器等）。
- time travel 三个动作（replay / fork / interrupt / subgraph 组合）：`libs/langgraph/tests/test_time_travel.py` 全覆盖；教学仓库 langchain-academy module-3 `time-travel.ipynb` 与文档 how-to 一致。
- 手写 tool_node 版本：官方 add-tools 教程（旧 GitHub Pages 版仍被搜索索引，代码片段与上述一致）。

---

### 路径 2：记忆系统（短期 + 长期 store）官方教程骨架

官方"memory 教程"= `docs.langchain.com/oss/python/langgraph/add-memory` 一页讲完两种记忆：短期=thread 级 checkpointer（对话内），长期=store（跨 thread 共享）。

**① 短期记忆（多轮对话）——最小代码**：

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState

builder = StateGraph(MessagesState)          # MessagesState 自带 add_messages reducer，消息自动累积
graph = builder.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "user-123"}}
graph.invoke({"messages": [{"role": "user", "content": "我叫小明"}]}, config)
graph.invoke({"messages": [{"role": "user", "content": "我叫什么？"}]}, config)  # 记住了
```

- 要点：换 `thread_id` = 新会话；不传 config 则每次全新。生产用 `langgraph-checkpoint-postgres` 的 `PostgresSaver`，`InMemorySaver` 官方注明仅供调试/测试。

**② 长期记忆（store）——最小代码**：

```python
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import InMemorySaver

# 可选：配上 embedding 索引后 store.search 支持语义检索
store = InMemoryStore(index={"dims": 1536, "embed": "openai:text-embedding-3-small"})
graph = builder.compile(checkpointer=InMemorySaver(), store=store)

def remember(state, *, store: BaseStore):            # store 由 LangGraph 自动注入节点
    user_id = state["user_id"]
    store.put(
        namespace=(user_id, "memories"),             # namespace 惯例：(<user_id>, "memories")
        key="preference_language",
        value={"lang": "python"},                    # value 必须是 JSON 可序列化 dict
    )
    return {}

def recall(state, *, store: BaseStore):
    user_id = state["user_id"]
    items = store.search(
        (user_id, "memories"),
        query=state["messages"][-1].content,          # 不给 query 则按插入/updated_at 排序枚举
        limit=5,
    )
    facts = [it.value for it in items]
    return {"context": f"已知信息：{facts}"}           # 注入 system/消息上下文
```

- 新官方推荐写法（2025 后文档）：节点签名用 `Runtime` 对象，等价访问 `runtime.context.user_id`、`await runtime.store.asearch(namespace, query=...)`；经典 `*, store: BaseStore` 注入仍被支持（绝大多数教程/notebook 用它，两者都算"官方验证过"）。
- store API 面：`put / get / delete / search(namespace_prefix, *, query, limit, offset) / list_namespaces`；`namespace` 按前缀匹配，`("alice",)` 会包含 `("alice","memories")`；Postgres 后端的 `search` 按 updated_at 倒序、InMemory 按插入序——顺序敏感就自己 sort。换 `user_id` 就用同一套 store 访问其他命名空间，天然隔离。

**③ 控制对话长度（short-term 的配套，官方 how-to）**：

```python
from langchain_core.messages import trim_messages

def trim_node(state):
    return {"messages": trim_messages(
        state["messages"], max_tokens=4000, strategy="last",
        token_counter=len, start_on="human", include_system=True)}
# 或 summarize + SystemMessage 替换旧消息的经典摘要法
```

---

### "完整且不过度"的记忆验收清单（resume 项目）

**完整（必做，做到这 4 条即可在简历写"实现了两级记忆"）**：
1. `MessagesState` + checkpointer（`thread_id` 路由）→ 多轮对话记忆。
2. store 挂上编译（`compile(checkpointer=..., store=...)`）。
3. 一个"记忆写入"节点（如 LLM 抽取偏好/事实 → `store.put`）+ 回答前 `store.search` 读回并注入上下文的"记忆读取"节点。
4. 可演示的验证：同 thread 多轮记得 → 换 user_id 不串号 →（可选）重启进程后 PostgresSaver 数据仍在。

**加分项（做了才算"深入"，不做不算缺陷）**：
- `trim_messages` 控制上下文长度；摘要记忆；语义索引（上面 `index=...` 那行）；LangGraph 官方子项目 langmem 的记忆工具（`create_manage_memory_tool` / `create_search_memory_tool`，直接接 store）。
- 短时 + 长时两层联合的页面级演示（官方 add-memory 就是一层 checkpointer + 一层 store）。

**过度（resume 项目没必要时别做）**：
- 实体记忆图谱、知识图谱、记忆衰减/合并/遗忘策略、自定义 `BaseStore` 子类、多级复杂 namespace 设计、同时接多个 embedding 后端。官方文档明确"记忆写/取"两件事用 store 三层 API 就能表达完；这些高级模式没有官方教程背书，放进简历反而问不住。

---

## Sources

- Kept: Docs by LangChain (docs.langchain.com) — 当前唯一权威教程源
  - Quickstart（Calculator Agent 全代码，工具迁移样板）— https://docs.langchain.com/oss/python/langgraph/quickstart
  - Add memory（两种记忆官方教程，Runtime API 原文）— https://docs.langchain.com/oss/python/langgraph/add-memory
  - Stores（BaseStore/InMemoryStore/namespace 语义）— https://docs.langchain.com/oss/python/langgraph/stores
  - Use time-travel（replay/fork 官方说明）— https://docs.langchain.com/oss/python/langgraph/use-time-travel
  - Checkpointers（thread/checkpoint 模型）— https://docs.langchain.com/oss/python/langgraph/checkpointers
  - Memory overview（概念层）— https://docs.langchain.com/oss/python/concepts/memory
- Kept: langchain-ai/langgraph 仓库（实现与单测 = "被官方验证"的最硬证据）
  - examples/tool-calling.ipynb — https://github.com/langchain-ai/langgraph/tree/main/examples
  - libs/prebuilt/tests/test_tool_node.py — https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/tests/test_tool_node.py
  - libs/langgraph/tests/test_time_travel.py — https://github.com/langchain-ai/langgraph/blob/b674dd46/libs/langgraph/tests/test_time_travel.py
- Kept: langchain-ai/langchain-academy module-3/time-travel.ipynb — 官方教学 notebook，代码与文档一致 — https://github.com/langchain-ai/langchain-academy/blob/26377bf6/module-3/time-travel.ipynb
- Kept: langchain-ai.github.io/langgraph/tutorials/get-started/2-add-tools/ — 旧版官方教程（手写 tool_node 版代码出处，搜索索引仍引用，页面本体可能 404）
- Kept: langchain-ai.github.io/langmem/guides/memory_tools/ — langmem 记忆工具（long-term 提质选择）— https://langchain-ai.github.io/langmem/guides/memory_tools/
- Kept: mintlify.wiki/langchain-ai/langgraph/guides/memory — 官方旧 memory 指南的代码完整镜像（抄代码用，非权威）
- Dropped: deepwiki.com langchain-academy 页面 — 提取不完整；可直接用上面的原始 notebook
- Dropped: markaicode / crewship / cleancodestack / scrolltest / getautonoma / dragonforest / machinelearningplus / supermemory / pythonfriday — 二手解读，仅用于交叉印证 API 名，无独立证据价值
- Dropped: luochang212/dive-into-langgraph、i-flow/strands 等第三方测试 — 非官方项目，不能用来说明"官方验证"

## Gaps

- `use-time-travel` 官方页的完整代码块在抓取时被 Mintlify 剥离，无法逐字核对 replay/fork 字面代码；已用仓库 `test_time_travel.py` 的描述 + 文档 prose + academy notebook 三方交叉验证 API 形状（confidence: 高，但建议抄代码后跑一次 `graph.update_state` + `invoke(None)` 烟测）。
- 旧 GitHub Pages 教程（manage-conversation-history / manage-long-term-memory / function_calling tutorial）均已 404，无法确认其与 docs.langchain.com 新版的代码是否 1:1；本 brief 一律采用新版 API。
- langmem 工具库（create_manage_memory_tool 等）的当前版本参数未逐行核对，若采用请直接看其官方 guide。
- InMemoryStore 语义索引的模型名/维度（openai:text-embedding-3-small, dims=1536）来自官方 langmem 文档示例，接入自己的 key 前需验证。

## 下一步建议（给父代理）

1. 若要在真实本地环境验证，把本文两份骨架跑一遍最小烟测：① tool 循环（故意触发 tool 再改输入验证 fork）；② 多轮 + store 读写 + 换 user_id 隔离。
2. resume 项目定型：工具侧用"绑定前 if/else → 绑定后 ToolNode"两版对比截图；记忆侧按"必做 4 条 + 1 个加分项"组合即可。
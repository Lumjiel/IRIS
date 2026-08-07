# IRIS 意图识别 + 图拓扑重构方案

> 参考项目：LangGraph Multi-Agent Router + Agent Squad

---

## 一、当前问题

### 1.1 意图识别

| 问题 | 影响 |
|------|------|
| 只有 NEW_TOPIC / REFINE 二元分类 | 无法识别闲聊、SQL生成、工具调用 |
| Skill 匹配结果不进入路由 | Skill 只是 prompt 注入，不改变执行路径 |
| `_skill_cache` 是进程级 dict | 多 worker 部署时 cache 互相污染 |

### 1.2 图拓扑

| 问题 | 影响 |
|------|------|
| 固定 5 节点单链路 | 所有输入走同一条路 |
| 无独立"闲聊"节点 | 用户问"你好"也走完整调研流程 |
| refiner 直接 END | 修订后不经过 reviewer 审查 |

---

## 二、目标架构

### 2.1 新图拓扑

```
                            ┌─────────────────────────────────────┐
                            │           router (多意图分类)         │
                            └──────┬──────┬──────┬──────┬─────────┘
                                   │      │      │      │
                             RESEARCH  CHAT   SQL   TOOL_CALL  REFINE
                                   │      │      │      │       │
                                   ▼      ▼      ▼      ▼       ▼
                               planner  chat   sql   tool    refiner
                                   │    node   node  executor   │
                                   ▼      │      │      │       ▼
                               researcher │      │      │      END
                                   │      │      │      │
                                   ▼      │      │      │
                                writer    │      │      │
                                   │      │      │      │
                                   ▼      │      │      │
                                reviewer  │      │      │
                                   │      │      │      │
                                   ▼      ▼      ▼      ▼
                                  END ← ← ← ← ← ← ← ←
```

### 2.2 意图类型

| 意图 | 说明 | 路由到 | 示例 |
|------|------|--------|------|
| `RESEARCH` | 调研任务 | planner → researcher → writer → reviewer | "帮我调研 AI Agent 发展趋势" |
| `CHAT` | 闲聊/问答 | chat_node → END | "你好"、"今天天气怎么样" |
| `SQL` | SQL 生成/查询 | sql_node → END | "帮我写一个查询用户表的 SQL" |
| `TOOL_CALL` | 工具调用 | tool_executor → END | "帮我搜索最新的论文" |
| `REFINE` | 修改报告 | refiner → END | "把第三段改详细"、"你觉得呢" |

---

## 三、详细设计

### 3.1 Router 重构

**文件**: `backend/app/graph/nodes/router.py`

#### 3.1.1 分类 Prompt

```python
ROUTER_SYSTEM_PROMPT = """\
你是一个意图分类器，分析用户输入并选择以下意图之一：

RESEARCH: 需要深度调研的任务，如"帮我调研XXX"、"分析XXX的发展趋势"、"写一份关于XXX的报告"
CHAT: 闲聊、问候、简单问答，如"你好"、"你是谁"、"今天天气怎么样"
SQL: SQL 相关操作，如"帮我写一个查询"、"查询用户表"、"执行SQL"
TOOL_CALL: 需要调用工具的任务，如"帮我搜索XXX"、"查找论文"、"翻译这段话"
REFINE: 对已有报告的修改、补充、讨论，如"把第三段改详细"、"你觉得呢"、"继续"

重要规则：
- 如果用户明确提出了一个调研任务，归类为 RESEARCH
- 如果是简单对话或问答，归类为 CHAT
- 如果涉及数据库操作，归类为 SQL
- 如果需要调用外部工具（搜索、翻译等），归类为 TOOL_CALL
- 如果是对已有报告的修改或讨论，归类为 REFINE

只输出一个词：RESEARCH, CHAT, SQL, TOOL_CALL, 或 REFINE。"""
```

#### 3.1.2 分类逻辑

```python
def route_query(state: AgentState):
    query = state["query"]
    has_report = bool(state.get("final_report", "").strip())

    # 无报告时，排除 REFINE
    if not has_report:
        prompt = f"""用户输入: "{query}"
        
        注意：当前没有已生成的报告，所以 REFINE 不是一个有效选项。
        
        请选择意图：RESEARCH, CHAT, SQL, 或 TOOL_CALL。"""
    else:
        prompt = f"""用户输入: "{query}"
        
        当前已有一份报告（片段）："{state['final_report'][:300]}"
        
        请选择意图：RESEARCH, CHAT, SQL, TOOL_CALL, 或 REFINE。"""

    # 调用 LLM 分类
    result = llm_invoke(
        [SystemMessage(content=ROUTER_SYSTEM_PROMPT), HumanMessage(content=prompt)],
        node="router"
    ).content.strip().upper()

    # 兜底：如果 LLM 输出非法
    if result not in ["RESEARCH", "CHAT", "SQL", "TOOL_CALL", "REFINE"]:
        result = looks_like_refine(query) and has_report ? "REFINE" : "RESEARCH"

    return result.lower()  # 返回小写，对应 graph 的节点名
```

### 3.2 新增节点

#### 3.2.1 chat_node.py — 闲聊/问答

```python
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.graph.state import AgentState

CHAT_PROMPT = """你是一个友好的 AI 助手。请用简洁友好的方式回答用户的问题。
不要过度展开，保持对话的自然性。"""

async def chat_node(state: AgentState):
    query = state["query"]
    
    messages = [SystemMessage(content=CHAT_PROMPT), HumanMessage(content=query)]
    
    if get_token_queue() is not None:
        response = await llm_stream_tokens(messages, model_type="fast", node_name="chat", node="chat")
    else:
        response = llm_invoke(messages, node="chat").content
    
    return {"final_report": response}
```

#### 3.2.2 sql_node.py — SQL 生成

```python
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.graph.state import AgentState

SQL_PROMPT = """你是一个 SQL 专家。根据用户的描述，生成对应的 SQL 查询语句。

规则：
1. 只输出 SQL 语句，不要有其他解释
2. 使用标准 SQL 语法
3. 如果用户没有指定数据库，默认使用通用语法
4. 如果用户的描述不清晰，生成最合理的 SQL 并加注释说明"""

async def sql_node(state: AgentState):
    query = state["query"]
    
    messages = [SystemMessage(content=SQL_PROMPT), HumanMessage(content=query)]
    
    if get_token_queue() is not None:
        response = await llm_stream_tokens(messages, model_type="fast", node_name="sql", node="sql")
    else:
        response = llm_invoke(messages, node="sql").content
    
    return {"final_report": f"```sql\n{response}\n```"}
```

#### 3.2.3 tool_executor_node.py — 工具调用

```python
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm import llm_invoke
from app.tools.registry import ToolRegistry
from app.graph.state import AgentState

TOOL_SELECT_PROMPT = """你是一个工具选择器。根据用户的请求，选择最合适的工具。

可用工具：
{tools_description}

用户请求: "{query}"

只输出工具名称，不要有其他内容。如果没有合适的工具，输出 "NONE"。"""

async def tool_executor_node(state: AgentState):
    query = state["query"]
    
    # 获取所有可用工具
    tools = ToolRegistry.list_all()
    tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools)
    
    # 让 LLM 选择工具
    select_prompt = TOOL_SELECT_PROMPT.format(tools_description=tools_desc, query=query)
    selected_tool = llm_invoke([HumanMessage(content=select_prompt)], node="tool_executor").content.strip()
    
    if selected_tool == "NONE" or selected_tool not in [t.name for t in tools]:
        return {"final_report": f"抱歉，没有找到合适的工具来处理您的请求：{query}"}
    
    # 执行工具
    tool = ToolRegistry.get(selected_tool)
    try:
        result = tool.func(query=query)
        return {"final_report": f"**工具: {selected_tool}**\n\n{result}"}
    except Exception as e:
        return {"final_report": f"工具执行失败: {e}"}
```

### 3.3 图拓扑重构

**文件**: `backend/app/graph/graph.py`

```python
from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes.planner import plan_node
from app.graph.nodes.researcher import research_node
from app.graph.nodes.writer import write_node
from app.graph.nodes.reviewer import review_node
from app.graph.nodes.refiner import refine_node
from app.graph.nodes.router import route_query
from app.graph.nodes.chat import chat_node
from app.graph.nodes.sql import sql_node
from app.graph.nodes.tool_executor import tool_executor_node

def create_graph(memory=None, store=None):
    workflow = StateGraph(AgentState)
    
    # 添加所有节点
    workflow.add_node("planner", plan_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("writer", write_node)
    workflow.add_node("reviewer", review_node)
    workflow.add_node("refiner", refine_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("sql", sql_node)
    workflow.add_node("tool_executor", tool_executor_node)
    
    # 条件入口：根据 router 返回值路由
    workflow.set_conditional_entry_point(
        route_query,
        {
            "research": "planner",
            "chat": "chat",
            "sql": "sql",
            "tool_call": "tool_executor",
            "refine": "refiner",
        }
    )
    
    # RESEARCH 链路
    workflow.add_edge("planner", "researcher")
    workflow.add_conditional_edges(
        "researcher",
        lambda state: END if state.get("should_stop", False) else "writer",
        {"writer": "writer", END: END}
    )
    workflow.add_edge("writer", "reviewer")
    workflow.add_conditional_edges(
        "reviewer",
        lambda state: END if state.get("revision_number", 0) >= 3 or state.get("review_status") == "PASS" else "planner",
        {"planner": "planner", END: END}
    )
    
    # 其他链路直接到 END
    workflow.add_edge("chat", END)
    workflow.add_edge("sql", END)
    workflow.add_edge("tool_executor", END)
    workflow.add_edge("refiner", END)
    
    return workflow.compile(checkpointer=memory, store=store)
```

### 3.4 AgentState 扩展

**文件**: `backend/app/graph/state.py`

```python
from typing import TypedDict, List

class AgentState(TypedDict):
    # === 核心字段 ===
    query: str
    plan: List[str]
    search_results: List[str]
    final_report: str
    critique: str
    revision_number: int
    review_status: str
    search_mode: str
    should_stop: bool
    
    # === 意图分类 ===
    intent: str  # 新增：router 分类结果 (research/chat/sql/tool_call/refine)
    
    # === 记忆系统 ===
    conversation_summary: str
    
    # === 用户偏好 ===
    preferences: dict
    
    # === Skill 系统 ===
    active_skill: str
    
    # === 引用系统 ===
    search_sources: List[dict]
    citation_refs: str
```

---

## 四、前端适配

### 4.1 意图类型展示

在 SSE 事件流中，前端可以根据 `step: "router"` 的 `data` 判断意图类型，展示不同的 UI：

```javascript
// 前端根据 intent 展示不同 UI
if (intent === "research") {
  // 显示调研进度条
} else if (intent === "chat") {
  // 直接显示对话气泡
} else if (intent === "sql") {
  // 显示 SQL 代码块 + 执行按钮
} else if (intent === "tool_call") {
  // 显示工具调用状态
}
```

### 4.2 Skill 卡片位置（后续优化）

当前方案不涉及前端改动，后续再优化 Skill 卡片位置。

---

## 五、实施步骤

### Phase 1: 核心骨架（本次完成）

1. [ ] 重构 `router.py` — 多意图分类
2. [ ] 新增 `chat_node.py` — 闲聊节点
3. [ ] 新增 `sql_node.py` — SQL 节点
4. [ ] 新增 `tool_executor_node.py` — 工具调用节点
5. [ ] 重构 `graph.py` — 多分支路由
6. [ ] 更新 `state.py` — 添加 intent 字段

### Phase 2: 前端适配（后续）

1. [ ] 前端根据 intent 展示不同 UI
2. [ ] SQL 结果展示优化
3. [ ] 工具调用状态展示

### Phase 3: 高级功能（后续）

1. [ ] SupervisorAgent 模式（多 agent 并行）
2. [ ] ChainAgent 模式（多步管道）
3. [ ] Agent 独立对话历史

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 分类延迟 | 增加一次 LLM 调用 | 用 fast 模型 + 缓存 |
| 分类准确率 | 错误分类导致功能异常 | 兜底规则 + confidence 阈值 |
| 向后兼容 | 现有调研功能受影响 | RESEARCH 走原有链路 |

---

## 七、参考资源

- [LangGraph Multi-Agent Router](https://github.com/mkassaf/langgraph-complete-guide)
- [Agent Squad](https://github.com/awslabs/agent-squad)
- [AnRouter](https://github.com/anrouter/router)

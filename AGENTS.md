# Repository Guidelines

## Project Overview

**IRIS** (Intelligent Research Insight System) — an A-share investment research aggregation platform built on a LangGraph multi-agent state machine.

**Purpose**: Accept a stock code or research topic → plan search directions → multi-source retrieval (local docs + web + AKShare financial data) → write Chinese 6-section research report → quality review → output. Supports multi-turn follow-up refinement.

**Tech Stack**:

- **Backend**: Python 3.11+ / FastAPI / LangGraph / AKShare / ChromaDB / Tavily / DeepSeek / SQLite
- **Frontend**: Vue 3 (Composition API) / Tailwind CSS / markdown-it + KaTeX / SSE streaming

---

## Architecture & Data Flow

### 8-Node State Machine + Function Calling

The core workflow is a LangGraph `StateGraph` defined in `backend/app/graph/graph.py`. The topology is built **once at module import** — adding/removing nodes requires a server restart.

```
router (conditional entry, NOT a node)
  ├── NEW_TOPIC → planner → researcher → search_agent ⇄ search_tools → data_collector → writer → reviewer
  │                                                              └── FAIL → planner (up to MAX_REVISIONS=5)
  └── REFINE → refiner → END
```

**Node sync/async split**:

- `async def` nodes (SSE-aware): `planner`, `writer`, `refiner` — call `get_token_queue()` to detect streaming mode
- `sync def` nodes: `router`, `researcher`, `data_collector`, `reviewer`, `search_agent`, `search_tools`

**Key insight**: `router` is registered via `set_conditional_entry_point()` — it's a dispatch function, not a graph node.

**Function Calling loop**: `search_agent` and `search_tools` form a loop — LLM decides when to call tools, executes them, and loops back until satisfied.
**Key insight**: `router` is registered via `set_conditional_entry_point()` — it's a dispatch function, not a graph node.

### AgentState (20+ fields)

Defined in `backend/app/graph/state.py` as a `TypedDict`:

| Field | Type | Written By | Purpose |
| ------- | ------ | ----------- | --------- |
| `query` | str | all | User's original question |
| `plan` | List[str] | planner/writer | 3-5 search sub-directions |
| `search_results` | List[str] | researcher/writer | Retrieved content chunks |
| `final_report` | str | writer/reviewer/refiner | Generated report |
| `critique` | str | reviewer/planner | Review feedback |
| `revision_number` | int | reviewer | Current revision count (loop guard) |
| `review_status` | str | reviewer | "PASS" or "FAIL" |
| `search_mode` | str | router | "document" or "hybrid" |
| `should_stop` | bool | researcher | Circuit-breaker flag |
| `conversation_summary` | str | writer/refiner | Running summary, persisted via checkpoint |
| `preferences` | dict | writer | `{style, language}` from frontend |
| `error_code` | str | various | Structured error code (ErrorCode enum) |
| `degraded` | bool | various | Degradation flag |
| `failed_tools` | list | various | Failed tool list |
| `early_stop` | bool | reviewer | Reviewer early-stop flag |
| `should_continue` | bool | reviewer | Conditional edge control |
| `report_history` | list | reviewer | Report history (cosine similarity) |
| `tool_status` | dict | researcher | Tool call status |
| `financial_data` | dict | data_collector | AKShare financial data (stock_info, indicators, quote) |
| `data_sources` | list | data_collector | Data source tags |
| `pending_stock_code` | str | router/planner | Stock code to analyze |
| `messages` | List | search_agent/tools | Function Calling 消息历史（`add_messages` reducer 自动累加） |
### SSE Streaming Architecture

`backend/app/utils/streaming.py` — producer/consumer pattern:

- `ContextVar` holds per-request `asyncio.Queue`
- **Producer thread**: sync `llm.stream()` → `asyncio.Queue`
- **Consumer**: async loop reads from queue → pushes to SSE response
- No queue present → degrades to sync `llm_invoke()`
- **Heartbeat**: `routes.py` sends `: heartbeat\n\n` every 15s to prevent proxy timeout

### RAG Engine

`backend/app/rag/engine.py`:

- Embedding: DashScope `text-embedding-v4` → ChromaDB vector store
- Optional CrossEncoder reranker (`ENABLE_RERANKER=true`): fetch_k=20 → rerank → top_k=5
- Document pipeline: PyPDFLoader → RecursiveCharacterTextSplitter (chunk_size=500, overlap=50)
- **2GB servers**: keep `ENABLE_RERANKER=false` (+400MB if enabled)

### LLM Factory

`backend/app/utils/llm.py`:

- Per-node model routing: `LLM_MODEL_{NODE}` env vars (router/planner/researcher/writer/reviewer/refiner)
- `model_type="fast"` (temp 0.7): router, planner, writer, refiner
- `model_type="smart"` (temp 0): researcher grader, reviewer
- Global primary→fallback downgrade with **5-minute TTL auto-recovery**
- Downgrade trigger keywords: quota/limit/insufficient/balance/429/rate

### AKShare Financial Data Layer

`backend/app/tools/akshare_tools.py`:

- **4 tools**: `query_stock_info`, `query_financial_indicators`, `query_stock_quote`, `query_stock_news`
- **3-tier fallback**: East Money → Snowball/Sina → Mock data
- **Module-level proxy cleanup**: clears `HTTP_PROXY/HTTPS_PROXY` on import
- **Never throws exceptions**: returns structured JSON error on failure
- **LangChain `@tool` decorator**: Function Calling ready
- **Source attribution**: every value tagged with `[来源: AKShare 东方财富]`

### Function Calling Architecture

`backend/app/tools/search_tools.py` + `backend/app/graph/nodes/search_agent.py`:

- **`@tool` 声明**: `search_web` 使用 LangChain `@tool` 装饰器
- **`bind_tools`**: LLM 通过 `get_llm().bind_tools([search_web])` 绑定工具
- **LLM 自主决策**: LLM 决定是否调用工具、调用什么参数
- **自定义 ToolNode**: `search_tool_node` 执行 LLM 决定的工具调用（不依赖 `langgraph.prebuilt`，避免版本兼容问题）
- **消息累加**: 工具结果通过 `add_messages` reducer 自动累加到 `state["messages"]`
- **结果提取**: `route_after_tools` 从 ToolMessage 提取搜索结果到 `search_results`

### Report RAG (PDF Ingestion)

`backend/app/rag/report_ingest.py`:

- **PyMuPDF 抽取**: `import fitz` 抽取 PDF 全文
- **实体抽取**: 正则抽取公司名/代码/评级/目标价/日期
- **元数据入库**: ChromaDB metadata 存 `{source, stock_code, rating, report_date}`
- **按标的检索**: `search_reports(query, stock_code="600196")` 可按股票代码过滤
### Chinese Report Format

`backend/app/agents/prompts.py`:

- **6-section template**: 核心结论 → 公司概况 → 财务分析 → 行业观点 → 风险提示 → 投资建议
- **Data-opinion separation**: tables generated directly from `financial_data` JSON (not LLM-rewritten)
- **Source attribution**: all values tagged with `[来源: ...]`
- **Mandatory disclaimer**: auto-appended if missing
- **Honest reporting**: missing data marked as `⚠️ 数据不足，暂不评价`

### Session Memory

`backend/app/utils/memory.py`:

- `conversation_summary`: running summary, persisted via checkpoint
- Incremental update: appends each round's query + report excerpt
- Compression: truncates at `summary_max` (default 2000 chars)
- Search direction dedup: prevents repeating search directions

---

## Project Structure

```
IRIS/
├── backend/
│   ├── main.py                      # FastAPI 入口，CORS、路由挂载、启动依赖检查
│   ├── app/
│   │   ├── agents/
│   │   │   └── prompts.py           # 中文研报提示词模板 + 数据表格生成器
│   │   ├── api/
│   │   │   └── routes.py            # 全部 API 端点（SSE 流式聊天、上传、素材、记忆、TTS、股票查询）
│   │   ├── graph/
│   │   │   ├── state.py             # AgentState TypedDict（20+ 字段，含 messages）
│   │   │   ├── graph.py             # StateGraph 拓扑（8 节点 + Function Calling 循环）
│   │   │   └── nodes/
│   │   │       ├── router.py        # 意图路由（NEW_TOPIC / REFINE）
│   │   │       ├── planner.py       # 搜索规划（async）
│   │   │       ├── researcher.py    # RAG 检索 + Grader 审计
│   │   │       ├── search_agent.py  # Function Calling agent（LLM 驱动工具调用）
│   │   │       ├── data_collector.py # AKShare 数据拉取（扇出并行 + 三层降级）
│   │   │       ├── writer.py        # 中文研报撰写（async）
│   │   │       ├── reviewer.py      # 质量审查 + cosine 相似度早停
│   │   │       └── refiner.py       # 双模式修订（async）
│   │   ├── rag/
│   │   │   └── engine.py            # ChromaDB + DashScope embedding + 可选 CrossEncoder
│   │   │   └── report_ingest.py     # 研报 PDF 入库 + 实体抽取
│   │   ├── tools/
│   │   │   ├── akshare_tools.py     # AKShare 4 工具（含新闻）+ 三层降级 + @tool 装饰器
│   │   │   ├── search_tools.py      # Function Calling @tool 声明
│   │   │   └── search.py            # Tavily 搜索封装
│   │       ├── llm.py               # LLM 工厂 + 自动降级
│   │       ├── streaming.py         # ContextVar + asyncio.Queue 流式架构
│   │       ├── memory.py            # 会话摘要
│   │       └── logger.py            # 结构化日志
│   ├── eval/                        # 评测框架（12 个 Golden Case）
│   ├── tests/                       # 127 个测试（全量通过）
│   │   ├── test_akshare_tools.py    # 13 个测试（AKShare 工具层 + mock）
│   │   ├── test_data_collector.py   # 9 个测试（DataCollector 节点 + mock）
│   │   ├── test_chinese_report.py   # 11 个测试（中文报告格式 + 表格生成）
│   │   ├── test_router.py           # 18 个测试
│   │   ├── test_reviewer.py         # 12 个测试
│   │   ├── test_researcher.py       # 5 个测试
│   │   ├── test_search_agent.py     # 8 个测试（Function Calling 节点）
│   │   ├── test_report_ingest.py    # 13 个测试（研报入库 + 检索）
│   │   ├── test_llm.py              # 9 个测试
│   │   ├── test_graph.py            # 6 个测试
│   │   └── integration/             # 23 个集成测试
│   ├── conftest.py                  # Mock 外部依赖 + sample_state fixture
│   ├── pytest.ini                   # asyncio_mode = auto
│   ├── requirements.txt             # 依赖清单（含 akshare + pymupdf）
---

## Key Design Decisions

1. **Module-level graph singleton**: `_workflow` is built once at import. Adding nodes requires restart.
2. **AKShare proxy cleanup**: Module-level `os.environ.pop()` clears proxy vars to prevent `Connection aborted`.
3. **Data-opinion separation**: Financial tables generated from JSON (not LLM) to prevent hallucination.
4. **3-tier data fallback**: East Money → Snowball/Sina → Mock data ensures system never crashes.
5. **Function Calling**: LLM autonomously decides when/what to search via `@tool` + `bind_tools` + custom `ToolNode`.
6. **Custom ToolNode**: Instead of `langgraph.prebuilt.ToolNode` (which has version compatibility issues), we implement our own.
7. **Report RAG**: PyMuPDF + regex entity extraction + ChromaDB metadata filtering.
---

## Environment Variables

| Variable | Description | Default |
| ---------- | ------------- | --------- |
| `OPENAI_API_KEY` | DeepSeek API key | - |
| `OPENAI_API_BASE` | API base URL | `https://api.deepseek.com/v1` |
| `LLM_MODEL_PRIMARY` | Primary model | `qwen3.7-plus` |
| `LLM_MODEL_FALLBACK` | Fallback model | `deepseek-v4-flash` |
| `TAVILY_API_KEY` | Tavily search API key | - |
| `LANGSMITH_API_KEY` | LangSmith observability (optional) | - |
| `DEEPSEEK_API_KEY` | DeepSeek key (legacy compat) | - |

---

## Common Workflows

### Adding a new graph node

1. Create `backend/app/graph/nodes/my_node.py` with `def my_node_node(state: AgentState) -> dict`
2. Add `@traceable(run_type="chain", name="my_node")` wrapper in `graph.py`
3. Register: `_workflow.add_node("my_node", traced_my_node)`
4. Wire edges: `_workflow.add_edge("from_node", "my_node")`
5. Add tests in `tests/test_my_node.py`

### Adding a new AKShare tool

1. Add `@tool` function in `backend/app/tools/akshare_tools.py`
2. Implement 3-tier fallback: East Money → Snowball/Sina → Mock
3. Add to `AKSHARE_TOOLS` list
4. Add mock tests in `tests/test_akshare_tools.py`

### Adding a new API endpoint

1. Add route in `backend/app/api/routes.py`
2. For SSE: use `StreamingResponse` with async generator
3. For stock data: use `query_stock_info.invoke(code)` etc.

---

## Interview Talking Points

- **Why LangGraph?** Explicit state + conditional routing + Checkpoint, ideal for auditable deterministic workflows
- **How to prevent infinite loops?** MAX_REVISIONS(5) + cosine similarity early-stop(0.95)
- **How to prevent hallucination?** Data-opinion separation + source attribution + honest reporting
- **How to handle degradation?** 3-tier data sources + LLM primary/fallback + tool-level never-throw
- **Multi-agent architecture?** 8-node collaboration with Function Calling loop (search_agent ⇄ search_tools)
- **Function Calling?** `@tool` declaration + `bind_tools` + custom `ToolNode` + LLM autonomous decision (not hardcoded)
- **Memory system?** conversation_summary incremental + checkpoint cross-session persistence
- **Report RAG?** PyMuPDF extraction + regex entity extraction + ChromaDB metadata filtering

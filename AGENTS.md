# Repository Guidelines

## Project Overview

**IRIS** (Intelligent Research Insight System) — an automated deep research and report generation system built on a LangGraph state machine.

**Purpose**: Accept a research topic → plan search directions → multi-source retrieval (local docs + web) → write structured report → quality review → output. Supports multi-turn follow-up refinement.

**Tech Stack**:
- **Backend**: Python 3.11+ / FastAPI / LangGraph / ChromaDB / Tavily / DashScope LLM / SQLite
- **Frontend**: Vue 3 (Composition API) / Tailwind CSS / markdown-it + KaTeX / SSE streaming

---

## Architecture & Data Flow

### 6-Node State Machine

The core workflow is a LangGraph `StateGraph` defined in `backend/app/graph/graph.py`. The topology is built **once at module import** — adding/removing nodes requires a server restart.

```
router (conditional entry, NOT a node)
  ├── NEW_TOPIC → planner → researcher → (should_stop? → END : writer) → reviewer
  │                                      └── FAIL → planner (up to MAX_REVISIONS=3)
  └── REFINE → refiner → END
```

**Node sync/async split**:
- `async def` nodes (SSE-aware): `planner`, `writer`, `refiner` — call `get_token_queue()` to detect streaming mode
- `sync def` nodes: `router`, `researcher`, `reviewer`

**Key insight**: `router` is registered via `set_conditional_entry_point()` — it's a dispatch function, not a graph node. The conditional edge after `researcher` checks `should_stop` to short-circuit in document-only mode.

### AgentState (11 fields)

Defined in `backend/app/graph/state.py` as a `TypedDict`:

| Field | Type | Written By | Purpose |
|-------|------|-----------|---------|
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

### Session Memory

`backend/app/utils/memory.py`:
- `update_conversation_summary()`: incremental append of query/report/search directions; LLM compression when >2000 chars
- `build_conversation_context()`: regex-extracts searched directions from summary → generates avoidance list for planner
- `_truncate_at_sentence()`: 3-level degradation — split by `。` → `,` → hard cut; **never blocks main flow**

### Checkpoint Serialization

LangGraph `AsyncSqliteSaver` uses **msgpack** (NOT JSON). `channel_values` at top level (not nested under `data`). Custom checkpoint reads in `routes.py` (`_read_checkpoint_state`, `_reset_checkpoint_summary`) use `msgpack.packb/unpackb`.

---

## Key Directories

```
IRIS/
├── backend/
│   ├── main.py                    # FastAPI entry: CORS, router mount, startup dep check
│   ├── conftest.py                # Mock external deps + sample_state fixture
│   ├── pytest.ini                 # asyncio_mode = auto
│   ├── requirements.txt           # 19 production deps
│   ├── requirements-dev.txt       # pytest + pytest-asyncio
│   ├── app/
│   │   ├── config.py              # Centralized config from env vars
│   │   ├── api/
│   │   │   └── routes.py          # All API endpoints (SSE chat, upload, materials, memory, TTS)
│   │   ├── graph/
│   │   │   ├── state.py          # AgentState TypedDict
│   │   │   ├── graph.py          # StateGraph topology (module-level singleton)
│   │   │   └── nodes/
│   │   │       ├── router.py     # Intent routing (NEW_TOPIC / REFINE) + keyword fallback
│   │   │       ├── planner.py    # Search planning, 3-5 sub-directions
│   │   │       ├── researcher.py # Multi-source retrieval + Relevance Grader + circuit-breaker
│   │   │       ├── writer.py     # Report writing, style/language preferences
│   │   │       ├── reviewer.py   # Quality review, JSON output + retry + fail-closed
│   │   │       └── refiner.py    # Dual-mode: vague follow-up / explicit edit
│   │   ├── rag/
│   │   │   └── engine.py         # ChromaDB + DashScope embedding + optional CrossEncoder
│   │   ├── tools/
│   │   │   └── search.py         # Tavily search wrapper with retry
│   │   └── utils/
│   │       ├── llm.py            # LLM factory + auto-downgrade
│   │       ├── streaming.py      # ContextVar + asyncio.Queue streaming
│   │       ├── memory.py         # Session summary: incremental + compression + avoidance
│   │       └── logger.py         # Structured logging
│   └── tests/
│       ├── test_router.py        # 18 tests
│       ├── test_reviewer.py      # 12 tests
│       ├── test_researcher.py    # 6 tests
│       ├── test_llm.py           # 9 tests
│       └── test_graph.py         # 6 tests
├── frontend/
│   ├── src/
│   │   ├── App.vue               # Root component, all UI state (201 lines)
│   │   ├── main.js               # Vue entry
│   │   ├── style.css             # Tailwind entry
│   │   ├── components/
│   │   │   ├── ChatHeader.vue    # Top bar: memory status + summary capacity bar
│   │   │   ├── ChatMessages.vue  # Message flow: research trajectory timeline + Markdown report
│   │   │   ├── ChatInput.vue     # Input: search mode toggle
│   │   │   └── ChatSidebar.vue   # Sidebar: knowledge base/materials/history/settings + memory management
│   │   ├── composables/
│   │   │   └── useChat.js       # Chat core: SSE streaming + session persistence (377 lines)
│   │   ├── services/
│   │   │   ├── api.js            # API client (211 lines)
│   │   │   └── history.js       # localStorage session persistence
│   │   └── utils/
│   │       └── markdown.js       # markdown-it + KaTeX rendering
│   ├── vite.config.js            # /api proxy to localhost:8000
│   └── package.json              # Vue 3 + Tailwind + markdown-it
├── deploy/
│   └── nginx.conf                # Nginx reverse proxy config
├── docker-compose.yml            # Full stack orchestration (backend + frontend)
└── docs/
    └── flowchart.md              # Architecture diagrams
```

---

## Development Commands

### Backend

```bash
cd backend

# Setup (Windows)
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env    # Fill in API keys

# Run (development)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run (production single-worker)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Frontend

```bash
cd frontend
npm install && npm run dev      # http://localhost:5173, /api proxies to :8000
npm run build                   # Production build to dist/
```

### Tests

```bash
cd backend

# Full suite
pytest

# Single file
pytest tests/test_router.py

# Single test by name
pytest -k "test_looks_like_refine"

# With verbose output
pytest -v
```

**Pytest config** (`backend/pytest.ini`):
- `asyncio_mode = auto` — async tests run without `@pytest.mark.asyncio`
- `testpaths = tests`

### Docker (Full Stack)

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f

# Rebuild after code changes
docker compose up -d --build

# Stop
docker compose down

# Debug backend container
docker compose exec backend bash
```

---

## Code Conventions & Common Patterns

### Async/Sync Split

- **Async nodes** (`planner`, `writer`, `refiner`): Use `await llm_stream_tokens()` when SSE queue is present, else fall back to `llm_invoke()`
- **Sync nodes** (`router`, `researcher`, `reviewer`): Always use `llm_invoke()` directly

### Error Handling Patterns

1. **Graceful degradation** (never crash the workflow):
   - LLM downgrade: primary → fallback model with 5-min TTL
   - Router fallback: `looks_like_refine()` keyword match if LLM returns invalid routing
   - Reviewer fail-closed: JSON parse failure → FAIL status (forces rewrite)
   - Memory compression: LLM failure → `_truncate_at_sentence()` → hard cut

2. **Circuit-breaker** (researcher):
   - Document-only mode + irrelevant docs → `should_stop=True` → skip writer
   - Hybrid mode + irrelevant docs → auto-degrade to web-only search

3. **Validation at boundaries**:
   - File upload: type/size/count validation
   - Material endpoints: `os.path.realpath()` before prefix check (path traversal defense)
   - Query length limit: 2000 chars

### Logging

`backend/app/utils/logger.py` — structured logging with per-module loggers:
```python
from app.utils.logger import get_logger
log = get_logger("module_name")
log.info("message")
```

Format: `HH:MM:SS [module] LEVEL: message`

### Configuration

All config in `backend/app/config.py` reads from env vars with defaults:
```python
from app.config import HOST, PORT, WORKERS, CORS_ORIGINS, LOG_LEVEL
```

**Required env vars**: `OPENAI_API_KEY`, `OPENAI_API_BASE`, `DASHSCOPE_API_KEY`, `TAVILY_API_KEY`

### Rate Limiting

`routes.py` — SQLite-backed sliding window rate limiter (process-safe across workers):
- 5 research requests per IP per minute
- **Warning**: `WORKERS > 1` breaks in-memory rate limiter; use SQLite-backed limiter for multi-worker

### Streaming Pattern

Producer/consumer with `asyncio.Queue`:
```python
# In async node:
if get_token_queue() is not None:
    text = await llm_stream_tokens(messages, model_type="fast", node_name="writer", node="writer")
else:
    response = llm_invoke(messages, node="writer")
    text = response.content
```

### Frontend State Management

- **Single component**: `App.vue` holds all UI state (201 lines)
- **Composable**: `useChat.js` encapsulates chat logic, SSE handling, session persistence
- **Session persistence**: `history.js` — localStorage, max 50 sessions, truncate reports >50KB
- **Vue Proxy gotcha**: `getMsgById()` returns Vue Proxy reference — mutate plain object directly to avoid reactivity overhead

---

## Important Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI entry point, CORS, startup dependency check |
| `backend/app/config.py` | Centralized configuration from env |
| `backend/app/graph/graph.py` | StateGraph topology (module-level singleton) |
| `backend/app/graph/state.py` | AgentState TypedDict definition |
| `backend/app/api/routes.py` | All API endpoints (534 lines) |
| `backend/app/utils/llm.py` | LLM factory with auto-downgrade |
| `backend/app/utils/streaming.py` | SSE streaming architecture |
| `backend/app/utils/memory.py` | Session summary management |
| `backend/app/rag/engine.py` | RAG engine (ChromaDB + optional reranker) |
| `backend/conftest.py` | Test fixtures, mock external deps |
| `frontend/src/composables/useChat.js` | Frontend chat logic (377 lines) |
| `frontend/src/services/api.js` | API client (211 lines) |
| `docker-compose.yml` | Full stack orchestration |
| `deploy/nginx.conf` | Nginx reverse proxy config |

---

## Runtime/Tooling Preferences

### Required Runtime

- **Python 3.11+** (backend)
- **Node.js 18+** (frontend development)
- **Docker** (deployment)

### Package Manager

- **Backend**: `pip` with `venv` (or `uv` per global CLAUDE.md policy)
- **Frontend**: `npm` (lockfile present)

### Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi==0.129.0` | Web framework |
| `langgraph==1.0.8` | State machine orchestration |
| `langchain_openai==1.1.9` | LLM client (DashScope-compatible) |
| `langgraph-checkpoint-sqlite` | Session persistence |
| `chromadb` | Vector store |
| `tavily==1.1.0` | Web search |
| `dashscope` | Embedding + TTS |
| `pydantic==2.12.5` | Request validation |
| `uvicorn[standard]==0.40.0` | ASGI server |

### Tooling Constraints

- **No linter/formatter configured** — run tests as the gate
- **No type checking** — no mypy/pyright in CI
- **No integration/e2e tests** — all backend tests are unit tests with mocked external deps
- **No frontend tests** — no vitest/jest configured

---

## Testing & QA

### Test Framework

- **pytest** + **pytest-asyncio** (`asyncio_mode = auto`)
- 5 test files, ~51 test cases total
- All unit tests — mock all external dependencies (LLM, Tavily, ChromaDB)

### Test Fixtures (`backend/conftest.py`)

```python
@pytest.fixture(autouse=True)
def _mock_env_vars(monkeypatch):
    # Sets OPENAI_API_KEY, OPENAI_API_BASE, DASHSCOPE_API_KEY, TAVILY_API_KEY

@pytest.fixture
def mock_llm_invoke():
    # Patches app.utils.llm.llm_invoke

@pytest.fixture
def sample_state():
    # Returns standard AgentState dict
```

### Mocking Pattern

External deps are mocked at **module import time** in `conftest.py`:
```python
sys.modules.setdefault("dashscope", MagicMock())
sys.modules.setdefault("tavily", MagicMock())
sys.modules.setdefault("sentence_transformers", MagicMock())
```

### Running Tests

```bash
cd backend
pytest                           # All tests
pytest tests/test_router.py       # Single file
pytest -k "test_name"            # By test name
pytest -v                        # Verbose
```

### Coverage

- No coverage tool configured
- Focus areas: router logic, reviewer JSON parsing, LLM factory downgrade, researcher circuit-breaker

---

## Key Constraints & Gotchas

1. **Graph topology is a module-level singleton** — adding/removing nodes requires server restart
2. **Checkpoint uses msgpack** — not JSON; `channel_values` at top level
3. **Rate limiter is process-scoped memory** — `WORKERS > 1` breaks it (use SQLite-backed limiter)
4. **2GB servers**: disable reranker (`ENABLE_RERANKER=false`) — saves ~400MB
5. **`CREATION_DIR` defaults to Windows path** — set explicitly for Docker/Linux
6. **WAL mode for checkpoint cleanup** — `timeout=5`, silent skip on locked DB
7. **Path traversal defense** on material endpoints — `os.path.realpath()` before prefix check
8. **Startup dep check** — `main.py` checks `langgraph.checkpoint.sqlite` etc. at import; missing → `SystemExit(1)`
9. **Memory compression degrades** — LLM summarization failure → `_truncate_at_sentence()` → hard cut, never blocks main flow
10. **Frontend `getMsgById()`** returns Vue Proxy — mutate plain object directly to avoid reactivity overhead

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | DashScope API Key |
| `OPENAI_API_BASE` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `DASHSCOPE_API_KEY` | Embedding API Key |
| `TAVILY_API_KEY` | Tavily search Key |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL_PRIMARY` | `qwen3.7plus` | Primary model |
| `LLM_MODEL_FALLBACK` | `deepseek-v4-flash` | Fallback model |
| `LLM_MODEL_{NODE}` | PRIMARY | Per-node model override |
| `ENABLE_RERANKER` | `false` | CrossEncoder reranker (2GB: don't enable) |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `CREATION_DIR` | Windows path | Report save directory |
| `CHECKPOINT_DB` | `checkpoints.db` | SQLite checkpoint path |
| `MAX_REVISIONS` | `3` | Max review retry loop |
| `WORKERS` | `1` | uvicorn workers (>1 breaks rate limiter) |
| `LOG_LEVEL` | `info` | Logging level |

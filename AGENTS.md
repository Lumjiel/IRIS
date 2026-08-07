# AGENTS.md

IRIS — LangGraph-based multi-agent deep research & report system. FastAPI backend + Vue 3 frontend. LLM via DashScope (qwen3.7-plus primary / deepseek-v4-flash fallback), Embedding DashScope, search Tavily, RAG ChromaDB, checkpoint SQLite.

> **Docs are stale.** `CLAUDE.md` and `README.md` describe an older topology (6 nodes, `conversation_summary` active). The current code has 8 nodes and a deprecated summary field. Trust the code, not the prose.

## Layout

```
backend/
  main.py                 # FastAPI entry; dep-check at import; SPA mount
  app/config.py           # all env config
  app/api/routes.py       # all endpoints + raw checkpoint access
  app/graph/              # StateGraph topology + 11 nodes
    graph.py              # module-level singleton topology (built at import)
    state.py              # AgentState TypedDict
    nodes/                # router/planner/researcher/synthesize/writer/reviewer/refiner/chat/sql/tool_call/tool_execute/clarify
  app/skills/ app/memory/ app/tools/   # skill, 4-layer memory, tool registries
  app/rag/engine.py       # ChromaDB + DashScope embedding (+ optional CrossEncoder)
  app/utils/              # llm factory, streaming, memory, credibility, citations, logger
  tests/                  # pytest (see Testing gotcha)
frontend/
  src/App.vue             # root component; all UI state
  src/composables/useChat.js  # SSE chat + session persistence
  vite.config.js          # /api proxy -> localhost:8000
```

## Commands

```bash
# backend (run from backend/)
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# frontend (run from frontend/)
npm install && npm run dev     # localhost:5173, /api proxies to :8000

# tests
pip install -r requirements-dev.txt
pytest                           # see Testing gotcha — most tests are SKIPPED
pytest -k "test_looks_like_refine"   # single case

# full-stack Docker
docker compose up -d --build    # backend:8000 + frontend nginx:80
```

No lint config. No typecheck.

## Testing gotcha (important)

`backend/conftest.py` **mocks `pydantic` with a fake BaseModel** and auto-skips every test module that imports real pydantic: `test_graph`, `test_planner`, `test_researcher`, `test_reviewer`, `test_writer` are all `@skip`-marked. Only `test_router`, `test_memory`, `test_llm` actually execute. A green/full `pytest` run does **not** validate graph/planner/researcher/writer/reviewer logic — do not treat it as proof those work.

Conftest also mocks `dashscope`, `tavily`, `sentence_transformers`, `langchain_openai`, `langchain_community`, `langchain_text_splitters`, `langgraph_checkpoint_sqlite` at module level (before any app import) to avoid module-level side effects.

## Graph topology (current, differs from CLAUDE.md)

`router` is a **real node** (writes intent/confidence/entities/active_skill back to state); a following `route_intent` conditional edge dispatches on **6 routes**: `research`→planner, `chat`→chat, `sql`→sql, `tool_call`→tool_call, `refine`→refiner, `clarify`→clarify. `tool_call` is a **ReAct loop** (`tool_call` decision node ⇄ `tool_execute` execution node; `after_tool_call` conditional edge exits to END when no tool request). Tools carry JSON-schema `parameters`; `tool_execute` falls back to a `query` retry on kwarg mismatch. `MAX_TOOL_ITERATIONS` (env) caps the loop.

- RESEARCH chain (Orchestrator-Worker): planner → researcher(parallel) → synthesize → writer → reviewer → (FAIL & revision<MAX_REVISIONS ? planner : END). Planner emits structured `plan_structure:[{subtask,queries}]` (+ flat `plan` for compat); researcher runs queries concurrently via `asyncio.gather`+`to_thread`; synthesize summarizes findings into `synthesis` for writer.
- `StateGraph` is built **once at import time** (module-level `_workflow`). `create_graph(memory, store)` only calls `.compile()`. Adding/removing nodes/edges requires a server restart.
- Async nodes: `planner`, `researcher`, `synthesize`, `writer`, `refiner`, `clarify` (`async def`). Others are sync. Async nodes detect SSE streaming via `get_token_queue()`; with no queue they fall back to sync `llm_invoke()`.
- `conversation_summary` is **deprecated** in `state.py` — kept only for checkpoint compatibility. The four-layer memory system (`app/memory/`) replaced it. Don't rely on `utils/memory.py` session-summary updates.
- `MAX_REVISIONS` (env) caps reviewer→planner retries.
- Four-layer memory (`app/memory/store.py`) does **hybrid retrieval**: keyword (LIKE) + cosine over DashScope embeddings stored in an `embedding` column; falls back to pure keyword if embedding unavailable. Empty query returns recent records. Planners injected with memory per active skill's `memory_policy` (`read_episodic` → reads historical episodic memories to avoid re-research).
- `researcher` scopes tools to the active skill's `required_tools` (warns on unregistered, falls back to all if none usable). Uses the skill-registry singleton, not a fresh `SkillRegistry` per call.

## Streaming & checkpoint quirks

- SSE: `ContextVar` token queue + `asyncio.Queue`; producer thread pushes token → endpoint consumes. Emit `: heartbeat\n\n` every 15s of silence to keep Nginx/proxy alive.
- Checkpoints use **msgpack** (not JSON) via `AsyncSqliteSaver`; `channel_values` sits at the top level. Raw read/write in `routes.py` (`_read_checkpoint_state`, `_reset_checkpoint_summary`) must use `msgpack.packb/unpackb`. `msgpack` is a hard requirement.
- Checkpoint cleanup uses `sqlite3.connect(timeout=5)` + `PRAGMA journal_mode=WAL`; locked DBs are silently skipped.

## Env & ops

- Config in `backend/.env` (copy from `.env.example`). Required: `OPENAI_API_KEY`, `OPENAI_API_BASE`, `TAVILY_API_KEY`, `DASHSCOPE_API_KEY`.
- Per-node model override env vars exist: `LLM_MODEL_ROUTER/PLANNER/RESEARCHER/WRITER/REVIEWER/REFINER` (fall back to `LLM_MODEL_PRIMARY`).
- `CORS_ORIGINS` must be explicit (not `*`) in production; `allow_credentials` is off for `*`.
- `CREATION_DIR` default is a **Windows path** — must be set explicitly for Docker/Linux (compose sets `/data/creation`).
- `ENABLE_RERANKER=true` adds ~400MB RAM — keep off on 2GB servers.
- Rate limiter is **process-local memory**: `WORKERS > 1` silently disables it. Compose pins `WORKERS=1`.
- `main.py` runs a startup dependency check and `SystemExit(1)`s if `langgraph.checkpoint.sqlite.aio` etc. are missing.
- `main.py` serves `frontend/dist` as SPA if it exists; otherwise `GET /` is a JSON health check. Building the frontend + running backend alone serves the whole app.
- `/api/upload` validates: PDF only, ≤20MB, ≤5 files. `/api/materials/{filename}` uses `os.path.realpath()` prefix checks to block `../` traversal.

## Failing soft first

Backend venv (`backend/venv`) is a broken/bespoke environment (pydantic-core stub). Prefer creating a fresh venv with the pinned `requirements.txt` (`pydantic==2.12.5`) rather than trusting the committed venv.
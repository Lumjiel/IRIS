# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

IRIS (Intelligent Research Insight System) — 基于 LangGraph 状态机的自动化深度调研与报告生成系统。支持多轮对话、会话持久化、素材库管理。

## 技术栈

- **后端**: FastAPI + LangGraph 1.0.8 + ChromaDB (RAG) + Tavily (搜索) + SQLite Checkpoint (WAL 模式)
- **前端**: Vue 3 (单组件 App.vue) + Tailwind CSS + markdown-it + KaTeX
- **LLM**: DashScope API (qwen3.7-plus 主 / deepseek-v4-flash 备)
- **Embedding**: DashScope text-embedding-v4

## 项目结构

```
backend/
  main.py                     # FastAPI 入口，CORS、路由挂载、启动依赖检查
  app/config.py               # 集中配置，从 env 读取所有参数
  app/api/routes.py           # 全部 API 端点（~360 行，最大后端文件）
  app/graph/graph.py          # LangGraph StateGraph 拓扑（模块级单例）
  app/graph/state.py          # AgentState TypedDict（9 字段）
  app/graph/nodes/            # 6 个节点：router/planner/researcher/writer/reviewer/refiner
  app/rag/engine.py           # RAG 引擎：ChromaDB + DashScope embedding + 可选 CrossEncoder
  app/tools/search.py         # Tavily 搜索封装（带重试）
  app/utils/llm.py            # LLM 工厂 + 自动降级
  app/utils/streaming.py      # ContextVar + asyncio.Queue 流式架构

frontend/
  src/App.vue                 # 唯一组件（~710 行），包含全部 UI 和状态
  src/services/api.js         # API 客户端：上传、SSE 流式聊天、素材 CRUD
  src/services/history.js     # localStorage 会话持久化
  vite.config.js              # Vite 配置，/api 代理到 localhost:8000
```

## 常用命令

```bash
# 后端
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # 生产构建

# Docker
cd backend
docker build -t iris-backend .
docker run -d --name iris -p 8000:8000 --memory=1g -v .env:/app/.env iris-backend
```

**无测试、无 lint 配置。**

## ⚠️ 开发 Gotcha

### 混合同步/异步节点

`planner` 和 `writer` 是 `async def`，其余节点（router/researcher/reviewer/refiner）是同步 `def`。异步节点通过 `get_token_queue()` 判断是否处于 SSE 流式模式，有 queue 则流式输出，否则降级为同步 `llm_invoke()`。

### Graph 拓扑是模块级单例

`graph.py` 中 `StateGraph` 在 import 时构建一次（line 51），每次请求只调用 `compile(memory)` 挂载 checkpointer。增删节点需重启服务。

### 其他注意事项

- **`StatusFlow.vue` 未使用**: 该组件未被 App.vue 导入，工作流步骤通过 SSE 事件流在消息系统中渲染
- **限流器是进程级内存**: `WORKERS > 1` 时限流失效（每个 worker 独立内存）
- **`CREATION_DIR` 默认值是 Windows 路径**: Docker/Linux 部署必须显式设置
- **检查点清理用 WAL + timeout**: `cleanup_old_checkpoints` 使用 `sqlite3.connect(timeout=5)` + `PRAGMA journal_mode=WAL`，locked 时静默跳过
- **启动依赖检查**: `main.py` 启动时检查 `langgraph.checkpoint.sqlite` 等关键模块，缺包直接报错退出
- **Researcher 熔断仅在 document 模式生效**: hybrid 模式下 `should_stop` 永远为 False

## 架构要点

### 状态机工作流

```
入口 → router
  ├── NEW_TOPIC → planner → researcher → (should_stop? → END : writer) → reviewer → (FAIL? → planner : END)
  └── REFINE → refiner → END
```

多轮对话：第 1 次输入走 NEW_TOPIC，后续输入（同 thread_id 且已有报告）走 REFINE。

### AgentState（`graph/state.py`）

TypedDict，9 个字段：`query`, `plan`, `search_results`, `final_report`, `critique`, `revision_number`, `review_status`, `search_mode`, `should_stop`。每个节点读写特定子集。

### 流式架构

- `contextvars.ContextVar` 存储每请求的 token queue（`utils/streaming.py`）
- 生产者-消费者模式：同步 `llm.stream()` 在线程中生产 token → `asyncio.Queue` → SSE 端点消费推送
- `routes.py` 中 `app.astream()` 作为独立 task 运行图，主循环同时轮询图事件和 token queue
- 前端 token 即时渲染：SSE 回调直接修改 Vue 响应式对象，不经过队列/rAF 延迟

### 前端消息系统

- 单条流式消息累积所有阶段状态：`{ statuses: [...], streamText: '...' }`
- 状态时间线带详情展开（搜索方向列表、审查意见）
- 完成后 `stream` → `report`，Markdown 渲染
- `getMsgById(id)` 通过响应式数组获取 Proxy 引用，直接改 plain object 不触发 Vue 重绘

### 会话持久化

- `thread_id` 存 `localStorage`，刷新后自动恢复
- 历史记录保存完整 `messages[]`（含 statuses、streamText）
- `onDone` 和 `onError` 回调都保存会话，防止出错丢数据
- 点击「新建调研」生成新 `thread_id`

### LLM 工厂（`utils/llm.py`）

- `model_type="fast"`（temperature 0.7）: router/planner/writer/refiner
- `model_type="smart"`（temperature 0）: researcher grader/reviewer
- 全局降级状态 + 5 分钟 TTL 自动恢复

### RAG 引擎（`rag/engine.py`）

- DashScope embedding → ChromaDB 向量存储
- 可选 CrossEncoder 精排（`ENABLE_RERANKER=true`）: fetch_k=20 → rerank → top_k=5
- **2GB 服务器必须关闭 reranker**（增加 ~400MB 内存）

## 环境变量

在 `backend/.env` 中配置（参考 `.env.example`）：

| 变量 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | DashScope API Key | ✅ | - |
| `OPENAI_API_BASE` | API 端点 | ✅ | - |
| `DASHSCOPE_API_KEY` | Embedding API Key | ✅ | - |
| `TAVILY_API_KEY` | Tavily 搜索 Key | ✅ | - |
| `LLM_MODEL_PRIMARY` | 主模型 | ❌ | `qwen3.7-plus` |
| `LLM_MODEL_FALLBACK` | 备用模型 | ❌ | `deepseek-v4-flash` |
| `CORS_ORIGINS` | 允许的域名 | 生产必填 | `*` |
| `ENABLE_RERANKER` | CrossEncoder 精排 | ❌ | `false` |
| `CREATION_DIR` | 报告保存目录 | ❌ | 本地路径（仅 Windows） |
| `CHECKPOINT_DB` | SQLite 路径 | ❌ | `data/checkpoints.db` |

## API 端点

| 端点 | 说明 |
|------|------|
| `POST /api/upload` | 上传 PDF，构建向量知识库 |
| `POST /api/chat` | SSE 流式聊天（支持多轮） |
| `POST /api/clear` | 重置知识库 |
| `GET /api/aihot/news` | AI HOT 新闻代理 |
| `POST /api/save-report` | 保存报告到素材库 |
| `GET /api/materials` | 列出所有素材 |
| `GET /api/materials/{filename}` | 读取素材内容 |
| `DELETE /api/materials/{filename}` | 删除素材 |
| `GET /` | 健康检查 |

## 容错机制

- **模型降级**: 主模型失败 → 备用模型，5 分钟 TTL 自动恢复
- **Router 兜底**: LLM 输出非法 → `looks_like_refine()` 关键词匹配
- **Reviewer 兜底**: JSON 解析失败 → 重试 → fail-closed
- **搜索重试**: Tavily 调用失败 → 2 次重试
- **上传校验**: 文件类型（PDF）+ 大小（20MB）+ 数量（5 个）
- **SQLite WAL**: 检查点清理使用 WAL 模式 + timeout，避免 locked 错误
- **启动检查**: 缺少 `langgraph-checkpoint-sqlite` 等关键依赖时启动直接报错

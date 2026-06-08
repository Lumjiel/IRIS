# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

IRIS (Intelligent Research Insight System) — 基于 LangGraph 状态机的自动化深度调研与报告生成系统。支持多轮对话、会话记忆、素材库管理。

## 技术栈

- **后端**: FastAPI + LangGraph 1.0.8 + ChromaDB (RAG) + Tavily (搜索) + SQLite Checkpoint (WAL + msgpack)
- **前端**: Vue 3 (单组件 App.vue) + Tailwind CSS + markdown-it + KaTeX
- **LLM**: DashScope API (qwen3.7-plus 主 / deepseek-v4-flash 备)
- **Embedding**: DashScope text-embedding-v4

## 项目结构

```
backend/
  main.py                     # FastAPI 入口，CORS、路由挂载、启动依赖检查
  app/config.py               # 集中配置，从 env 读取所有参数
  app/api/routes.py           # 全部 API 端点 + checkpoint 读写（msgpack）
  app/graph/graph.py          # LangGraph StateGraph 拓扑（模块级单例）
  app/graph/state.py          # AgentState TypedDict（11 字段）
  app/graph/nodes/            # 6 个节点：router/planner/researcher/writer/reviewer/refiner
  app/rag/engine.py           # RAG 引擎：ChromaDB + DashScope embedding + 可选 CrossEncoder
  app/tools/search.py         # Tavily 搜索封装（带重试）
  app/utils/llm.py            # LLM 工厂 + 自动降级
  app/utils/streaming.py      # ContextVar + asyncio.Queue 流式架构
  app/utils/memory.py         # 会话记忆：摘要增量更新 + 压缩 + 搜索方向去重

frontend/
  src/App.vue                 # 根组件，包含全部 UI 状态和记忆管理
  src/components/ChatHeader.vue    # 顶栏：记忆状态指示器 + 摘要容量进度条
  src/components/ChatMessages.vue  # 消息流：研究轨迹时间线 + Markdown 报告
  src/components/ChatInput.vue     # 输入框：搜索模式切换
  src/components/ChatSidebar.vue   # 侧栏：知识库/素材/历史/设置 + 记忆管理
  src/composables/useChat.js       # 聊天逻辑：流式 SSE + 会话持久化 + 轮次跟踪
  src/services/api.js         # API 客户端：上传、SSE 流式聊天、素材 CRUD、记忆管理
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
npm run dev      # http://localhost:5173，/api 代理到 localhost:8000
npm run build    # 生产构建
npm run preview  # 预览生产构建

# 测试（backend）
pip install -r requirements-dev.txt   # 首次运行需安装
pytest                                # 全量运行
pytest tests/test_router.py           # 单文件
pytest -k "test_looks_like_refine"    # 单用例

# Docker（全栈）
docker compose up -d --build          # 构建并启动 backend + frontend(Nginx)

# Docker（仅后端）
cd backend
docker build -t iris-backend .
docker run -d --name iris -p 8000:8000 --memory=1g -v .env:/app/.env iris-backend
```

**无 lint 配置。**

## ⚠️ 开发 Gotcha

### 混合同步/异步节点

`planner`、`writer`、`refiner` 是 `async def`，其余节点（router/researcher/reviewer）是同步 `def`。异步节点通过 `get_token_queue()` 判断是否处于 SSE 流式模式，有 queue 则流式输出，否则降级为同步 `llm_invoke()`。

### Graph 拓扑是模块级单例

`graph.py` 中 `StateGraph` 在 import 时构建一次（line 51），每次请求只调用 `compile(memory)` 挂载 checkpointer。增删节点需重启服务。

### 其他注意事项

- **`StatusFlow.vue` 未使用**: 该组件未被 App.vue 导入，工作流步骤通过 SSE 事件流在消息系统中渲染
- **限流器是进程级内存**: `WORKERS > 1` 时限流失效（每个 worker 独立内存）
- **`CREATION_DIR` 默认值是 Windows 路径**: Docker/Linux 部署必须显式设置
- **检查点清理用 WAL + timeout**: `cleanup_old_checkpoints` 使用 `sqlite3.connect(timeout=5)` + `PRAGMA journal_mode=WAL`，locked 时静默跳过
- **启动依赖检查**: `main.py` 启动时检查 `langgraph.checkpoint.sqlite` 等关键模块，缺包直接报错退出
- **Researcher 熔断仅在 document 模式生效**: hybrid 模式下 `should_stop` 永远为 False
- **Checkpoint 序列化是 msgpack**: LangGraph `AsyncSqliteSaver` 使用 msgpack（非 JSON/zlib），`channel_values` 在顶层（非 `data.channel_values`）。读写 checkpoint 必须用 `msgpack.packb/unpackb`，`requirements.txt` 需包含 `msgpack`
- **素材接口路径穿越防御**: `get_material`/`delete_material` 使用 `os.path.realpath()` 解析路径后再校验前缀，防止 `../` 绕过
- **SSE 心跳保活**: `routes.py` 事件循环中，超过 15 秒无数据时发送 `: heartbeat\n\n` 注释，防止 Nginx 等代理因空闲断开连接

## 架构要点

### 状态机工作流

```
入口 → router
  ├── NEW_TOPIC → planner → researcher → (should_stop? → END : writer) → reviewer → (FAIL? → planner : END)
  └── REFINE → refiner → END
```

多轮对话：第 1 次输入走 NEW_TOPIC，后续输入（同 thread_id 且已有报告）走 REFINE。

**REFINE 路径双模式**：
- **模糊后续**（如"你觉得呢？"）：`_is_vague()` 检测 → 轻量 prompt（只传报告前 2000 字摘要）→ 输出追加到报告末尾作为"AI 分析"
- **明确修改**（如"把第三段改详细"）：全文报告 + 修改指令 → LLM 输出完整修订版

### AgentState（`graph/state.py`）

TypedDict，11 个字段：

| 字段 | 类型 | 读写节点 | 说明 |
|------|------|---------|------|
| `query` | str | 全部 | 用户原始问题 |
| `plan` | List[str] | planner/writer | 规划的搜索步骤 |
| `search_results` | List[str] | researcher/writer | 搜索到的具体内容 |
| `final_report` | str | writer/reviewer/refiner | 最终生成的报告 |
| `critique` | str | reviewer/planner | 审查意见 |
| `revision_number` | int | reviewer | 当前修改到了第几版 |
| `review_status` | str | reviewer | "PASS" 或 "FAIL" |
| `search_mode` | str | router | "document" 或 "hybrid" |
| `should_stop` | bool | researcher | 控制位 |
| `conversation_summary` | str | writer/refiner | 运行摘要，通过 checkpoint 持久化 |
| `preferences` | dict | writer | 用户偏好 {style, language} |

### 流式架构

- `contextvars.ContextVar` 存储每请求的 token queue（`utils/streaming.py`）
- 生产者-消费者模式：同步 `llm.stream()` 在线程中生产 token → `asyncio.Queue` → SSE 端点消费推送
- `routes.py` 中 `app.astream()` 作为独立 task 运行图，主循环同时轮询图事件和 token queue
- **SSE 心跳**: 15 秒无数据时发送 `: heartbeat\n\n` 注释，防止代理/负载均衡器断开空闲连接
- 前端 token 即时渲染：SSE 回调直接修改 Vue 响应式对象，不经过队列/rAF 延迟

### 前端消息系统

- 单条流式消息累积所有阶段状态：`{ statuses: [...], streamText: '', rounds: [...] }`
- `rounds` 数组记录每轮搜索方向：`{ number, directions[] }`，用于渲染研究轨迹时间线
- 状态时间线带详情展开（搜索方向列表、审查意见）
- 完成后 `stream` → `report`，报告卡片内可折叠研究轨迹
- `getMsgById(id)` 通过响应式数组获取 Proxy 引用，直接改 plain object 不触发 Vue 重绘

### 会话持久化

- `thread_id` 存 `localStorage`，刷新后自动恢复
- 历史记录保存完整 `messages[]`（含 statuses、streamText、rounds）
- `onDone` 和 `onError` 回调都保存会话，防止出错丢数据
- `stopResearch` 终止时也保存会话（abort 后 `onDone` 不会被调用）
- 点击「新建调研」生成新 `thread_id`，同时调用 `clearContext()` 清空向量知识库
- 追问时**不**调用 `clearContext()`，保留知识库上下文供 RAG 检索

### 会话记忆系统（`utils/memory.py`）

多轮对话时，系统通过 `conversation_summary` 维护跨轮上下文：

```
用户输入 → router(NEW_TOPIC/REFINE)
  → planner 读取摘要 + 已搜方向避让 → 生成不重复的搜索计划
  → writer 撰写报告 → 增量更新摘要（含搜索方向）
  → 通过 SQLite checkpoint 持久化（msgpack 格式）
```

**新主题状态清理**：`planner` 在 `revision_number == 0`（首次进入，非审查重试）且 `final_report` 非空时，清空 `final_report` 和 `conversation_summary`，防止旧主题的搜索方向污染新主题。

**核心函数**：
- `update_conversation_summary()` — 增量追加本轮 query/报告/搜索方向，超过 2000 字符阈值时 LLM 压缩
- `build_conversation_context()` — 从摘要中正则提取已搜索方向，生成 `[已搜索方向（请勿重复）]` 避让列表
- `_truncate_at_sentence()` — 降级截断：按句号→逗号→硬切三级退让，避免截出乱码

**前端集成**：
- `ChatHeader` 显示记忆状态指示器（`🧠 N 轮上下文`），展开可查看摘要全文和容量进度条
- `ChatSidebar` 顶部显示记忆状态，旁边有清空按钮
- `ChatMessages` 报告卡片内显示研究轨迹时间线（多轮时可折叠展开）

**Checkpoint 格式**：LangGraph 使用 **msgpack** 序列化（非 JSON），`channel_values` 在顶层。读写需用 `msgpack.packb/unpackb`。`routes.py` 中 `_read_checkpoint_state` 和 `_reset_checkpoint_summary` 直接操作 SQLite 绕过 LangGraph saver 上下文。

### 用户偏好系统

前端侧栏设置 → localStorage → API 请求 → AgentState.preferences → writer prompt 动态注入：

| 偏好 | 选项 | Writer 效果 |
|------|------|------------|
| 写作风格 | detailed / concise / formal / casual | 详尽全面 / 简洁精炼 / 学术正式 / 通俗易懂 |
| 报告语言 | zh / en | 全中文 / 全英文 |

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
| `POST /api/chat` | SSE 流式聊天（支持多轮，接收 style/language 偏好） |
| `POST /api/clear` | 重置知识库 |
| `GET /api/memory/{thread_id}` | 获取会话记忆：摘要、轮次、已搜方向、容量 |
| `POST /api/memory/{thread_id}/reset` | 清空会话摘要（保留报告） |
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
- **记忆压缩降级**: LLM 压缩失败 → 按句号→逗号→硬切三级退让截断，不阻塞主流程
- **Checkpoint 读写容错**: msgpack 解析失败 → 返回空状态，不影响新请求

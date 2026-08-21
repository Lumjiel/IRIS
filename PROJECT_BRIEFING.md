# IRIS 项目完整概况 — 供优化 Agent 参考

## 项目简介

IRIS (Intelligent Research Insight System) — 基于 LangGraph 状态机的自动化深度调研与报告生成系统。

**技术栈**：FastAPI + LangGraph + ChromaDB + Tavily + DashScope LLM + Vue 3 + Tailwind CSS

**核心流程**：用户输入研究主题 → 意图路由 → 规划搜索方向 → 多源检索（文档+网络）→ 撰写报告 → 质量审查 → 输出。支持多轮对话追问修改。

---

## 项目结构

```
IRIS/
├── backend/
│   ├── main.py                      # FastAPI 入口，CORS、路由挂载、启动依赖检查
│   ├── app/
│   │   ├── config.py                # 集中配置，从 env 读取所有参数
│   │   ├── api/
│   │   │   └── routes.py            # 全部 API 端点（SSE 流式聊天、上传、素材、记忆、TTS）534 行
│   │   ├── graph/
│   │   │   ├── state.py             # AgentState TypedDict（11 字段）
│   │   │   ├── graph.py             # LangGraph StateGraph 拓扑（模块级单例，91 行）
│   │   │   └── nodes/
│   │   │       ├── router.py        # 意图路由（NEW_TOPIC / REFINE），含 looks_like_refine 兜底
│   │   │       ├── planner.py       # 搜索规划，生成 3-5 个子方向
│   │   │       ├── researcher.py    # 多源检索 + Relevance Grader + 熔断
│   │   │       ├── writer.py        # 报告撰写，支持风格/语言偏好
│   │   │       ├── reviewer.py      # 质量审查，JSON 输出 + 重试 + fail-closed
│   │   │       └── refiner.py       # 双模式修订（模糊追加 / 明确修改全文重写）
│   │   ├── rag/
│   │   │   └── engine.py            # ChromaDB + DashScope embedding + 可选 CrossEncoder 精排
│   │   ├── tools/
│   │   │   └── search.py            # Tavily 搜索封装（带重试）
│   │   └── utils/
│   │       ├── llm.py               # LLM 工厂 + 自动降级（5 分钟 TTL）
│   │       ├── streaming.py         # ContextVar + asyncio.Queue 流式架构
│   │       ├── memory.py            # 会话摘要：增量更新 + 压缩 + 搜索方向避让
│   │       └── logger.py            # 结构化日志
│   ├── tests/
│   │   ├── test_router.py           # 18 个测试
│   │   ├── test_reviewer.py         # 12 个测试
│   │   ├── test_researcher.py       # 6 个测试
│   │   ├── test_llm.py              # 9 个测试
│   │   └── test_graph.py            # 6 个测试
│   ├── conftest.py                  # Mock 外部依赖 + sample_state fixture
│   ├── pytest.ini                   # asyncio_mode = auto
│   ├── requirements.txt             # 19 个生产依赖
│   ├── requirements-dev.txt         # dev 依赖（pytest + pytest-asyncio）
│   ├── Dockerfile                   # Python 3.11-slim + build-essential
│   ├── .env.example                 # 环境变量模板
│   └── DEPLOY.md                    # 部署指南
├── frontend/
│   ├── src/
│   │   ├── App.vue                  # 根组件，包含全部 UI 状态（201 行）
│   │   ├── main.js                  # Vue 入口
│   │   ├── style.css                # Tailwind 入口
│   │   ├── components/
│   │   │   ├── ChatHeader.vue       # 顶栏：记忆状态指示器 + 摘要容量进度条
│   │   │   ├── ChatMessages.vue     # 消息流：研究轨迹时间线 + Markdown 报告
│   │   │   ├── ChatInput.vue        # 输入框：搜索模式切换
│   │   │   └── ChatSidebar.vue      # 侧栏：知识库/素材/历史/设置 + 记忆管理
│   │   ├── composables/
│   │   │   └── useChat.js           # 聊天核心逻辑：SSE 流式 + 会话持久化（377 行）
│   │   ├── services/
│   │   │   ├── api.js               # API 客户端（211 行）
│   │   │   └── history.js           # localStorage 会话持久化
│   │   └── utils/
│   │       └── markdown.js          # markdown-it + KaTeX 渲染
│   ├── index.html
│   ├── vite.config.js               # /api 代理到 localhost:8000
│   ├── package.json                 # Vue 3 + Tailwind + markdown-it
│   └── Dockerfile                   # 多阶段构建（node → nginx）
├── deploy/
│   └── nginx.conf                   # Nginx 反向代理配置
├── docker-compose.yml               # 全栈编排（backend + frontend）
├── AGENTS.md                        # OpenCode Agent 开发指南
├── CLAUDE.md                        # Claude Code 指南
└── README.md                        # 项目说明
```

---

## AgentState（11 字段）

定义在 `app/graph/state.py`：

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

---

## 图拓扑（Graph Topology）

定义在 `app/graph/graph.py`，模块级构建一次拓扑，每次请求只调用 `compile(memory)` 挂载 checkpointer。

```
router（条件入口，非节点）
  ├── NEW_TOPIC → planner → researcher → (should_stop? → END : writer) → reviewer → (FAIL → planner, 最多 MAX_REVISIONS=3)
  └── REFINE → refiner → END
```

**节点同步/异步拆分**：
- `async def`：planner, writer, refiner — 通过 `get_token_queue()` 检测 SSE 模式
- `sync def`：router, researcher, reviewer

**关键约束**：增删节点需要重启服务。

---

## 各节点详细逻辑

### Router（`nodes/router.py`）
- 无报告时直接 → planner
- 有报告时调用 LLM 判断 NEW_TOPIC / REFINE
- LLM 输出非法时 `looks_like_refine()` 关键词匹配兜底
- 关键词列表：改/润色/优化/补充/扩写/你觉得/然后呢/继续 等

### Planner（`nodes/planner.py`）
- 调用 `build_conversation_context()` 组装对话上下文（含历史摘要 + 已搜方向避让）
- 生成 3-5 个搜索子方向，逗号分隔
- 首次进入（`revision_number == 0`）且有旧报告时，清理 `final_report` 和 `conversation_summary`

### Researcher（`nodes/researcher.py`）
- 两种模式：`document`（仅文档）/ `hybrid`（文档+网络）
- 本地文档检索 → Relevance Grader（LLM 二分类 YES/NO）
- **document 模式**：文档不相关 → `should_stop=True` → 提前结束
- **hybrid 模式**：文档不相关 → 自动降级为全网搜索；文档相关 → 文档+网络混合
- Grader 超时时保守地认为文档相关
- 所有搜索失败时给 writer 一个系统提示而非空内容

### Writer（`nodes/writer.py`）
- 支持 4 种写作风格：detailed / concise / formal / casual
- 支持 2 种语言：zh / en
- 接收 critique 时在 prompt 中注入修正指令
- 流式输出时通过 `llm_stream_tokens()` 推送 token

### Reviewer（`nodes/reviewer.py`）
- 空报告/短报告（<50 字）直接 FAIL
- LLM 输出 JSON：`{"status": "PASS/FAIL", "feedback": "..."}`
- JSON 解析失败 → 重试一次 → 仍失败则 fail-closed（返回 FAIL + 格式异常提示）
- `_clean_json_text()` 处理 markdown 代码块包裹、多余文本等情况
- `revision_number` 每次 +1，达到 `MAX_REVISIONS` 强制结束

### Refiner（`nodes/refiner.py`）
- **模糊后续**（`_is_vague()`：短句 + 特定关键词）：只传报告前 2000 字摘要，输出追加到报告末尾作为"AI 分析"
- **明确修改**：全文报告 + 修改指令 → LLM 输出完整修订版
- 调用 `update_conversation_summary()` 更新对话摘要

---

## 核心模块详解

### LLM 工厂（`utils/llm.py`）
- 按节点分配模型：`LLM_MODEL_{NODE}` 环境变量
- `model_type="fast"`（temperature 0.7）：router/planner/writer/refiner
- `model_type="smart"`（temperature 0）：researcher grader/reviewer
- 全局降级状态 + 5 分钟 TTL 自动恢复
- 降级触发关键词：quota/limit/insufficient/balance/429/rate

### 流式架构（`utils/streaming.py`）
- `ContextVar` 存储每请求的 token queue
- 生产者（线程）→ 同步 `llm.stream()` → `asyncio.Queue` → async 消费者 → SSE
- 无 queue 时降级为同步 `llm_invoke()`

### 会话记忆（`utils/memory.py`）
- `update_conversation_summary()`：增量追加本轮 query/报告/搜索方向，超过 2000 字符阈值时 LLM 压缩
- `build_conversation_context()`：从摘要中正则提取已搜索方向，生成避让列表
- `_truncate_at_sentence()`：降级截断，按句号→逗号→硬切三级退让
- **记忆压缩失败时降级为截断，不阻塞主流程**

### RAG 引擎（`rag/engine.py`）
- DashScope `text-embedding-v4` → ChromaDB 向量存储
- 可选 CrossEncoder 精排（`ENABLE_RERANKER=true`）：fetch_k=20 → rerank → top_k=5
- 文档处理：PyPDFLoader → RecursiveCharacterTextSplitter（chunk_size=500, overlap=50）
- 重置知识库时 delete_collection + 清理上传目录

### 搜索模块（`tools/search.py`）
- Tavily 搜索，支持重试（默认 2 次），每次间隔 2 秒
- 搜索结果：提取 content 字段，换行拼接

### API 路由（`api/routes.py`）
- `POST /api/chat` — SSE 流式聊天，含心跳保活（15s 无数据发送 `: heartbeat\n\n`）
- `POST /api/upload` — 批量上传 PDF，校验文件类型/大小/数量
- `POST /api/clear` — 重置知识库
- `GET /api/memory/{thread_id}` — 获取会话记忆
- `POST /api/memory/{thread_id}/reset` — 清空会话摘要
- `GET /api/aihot/news` — AI 资讯代理
- `POST /api/save-report` — 保存报告到素材库
- `GET/DELETE /api/materials/{filename}` — 素材 CRUD（含路径穿越防御）
- `POST /api/tts` — CosyVoice 语音合成
- SQLite 滑动窗口限流：每 IP 每分钟 5 次
- 10% 概率触发检查点清理

### Checkpoint 序列化
- LangGraph `AsyncSqliteSaver` 使用 **msgpack**（非 JSON）
- `channel_values` 在顶层（非 `data.channel_values`）
- `_read_checkpoint_state()` 和 `_reset_checkpoint_summary()` 直接操作 SQLite 绕过 LangGraph saver

---

## 前端架构

### 单组件 App.vue（201 行）
- 包含全部 UI 状态管理
- 管理 AI 新闻、素材库、记忆状态
- Toast 通知系统

### useChat composable（377 行）
- SSE 流式聊天：`streamChat()` 逐步接收事件
- 事件类型处理：planner_token / writer_token / refiner_token / planner / researcher / writer / reviewer / refiner / error
- 研究轨迹：`rounds` 数组记录每轮搜索方向
- 会话持久化：`saveSession()` 保存到 localStorage（含消息列表）
- 停止研究：`stopResearch()` 终止 AbortController + 保存会话
- `getMsgById()` 返回 Vue Proxy 引用 — 直接改 plain object 避免触发重绘

### 会话持久化（`services/history.js`）
- localStorage 存储，最多 50 个会话
- 报告超过 50KB 时截断
- 同 thread_id 的会话会更新而非新增

### Markdown 渲染（`utils/markdown.js`）
- markdown-it + KaTeX
- 标题自动生成 id（用于 TOC）
- LaTeX 分隔符兼容：`\\[` → `$$$`，`\\(` → `$`

---

## 测试现状

- 测试框架：pytest + pytest-asyncio（`asyncio_mode = auto`）
- 共 5 个测试文件，约 51 个测试用例
- 全部为单元测试，mock 了所有外部依赖（LLM、Tavily、ChromaDB）
- **无集成测试、无端到端测试、无前端测试**
- conftest.py mock 了 `dashscope`、`tavily`、`sentence_transformers` 模块级实例

---

## 环境变量

### 必填
- `OPENAI_API_KEY` — DashScope API Key
- `OPENAI_API_BASE` — `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `DASHSCOPE_API_KEY` — Embedding API Key
- `TAVILY_API_KEY` — Tavily 搜索 Key

### 可选
- `LLM_MODEL_PRIMARY` / `LLM_MODEL_FALLBACK` — 主/备模型
- `LLM_MODEL_{NODE}` — 按节点分配模型
- `ENABLE_RERANKER` — CrossEncoder 精排（2G 服务器不要开，+400MB）
- `CORS_ORIGINS` — 允许的域名
- `CREATION_DIR` — 报告保存目录（默认 Windows 路径，Docker 需显式设置）
- `CHECKPOINT_DB` — SQLite 路径
- `MAX_REVISIONS` — 最大审查重试次数（默认 3）
- `WORKERS` — uvicorn worker 数（>1 时限流失效）

---

## 已有的工程化能力

1. **容错降级**：LLM 自动降级、Router 关键词兜底、Reviewer JSON 重试+fail-closed、搜索重试、记忆压缩降级
2. **安全防护**：素材接口路径穿越防御、文件上传校验（类型/大小/数量）、查询长度限制（2000 字）
3. **可观测性**：结构化日志（每个节点独立 logger）、SSE 心跳保活
4. **数据管理**：SQLite WAL + timeout 防锁死、检查点自动清理、上传文件过期清理
5. **部署能力**：Docker Compose 全栈、Nginx 反向代理、健康检查
6. **会话持久化**：localStorage 历史 + SQLite checkpoint 双重持久化

---

## 当前短板（需要优化的方向）

### P0 — 面试必做

1. **无 Eval 评测体系**
   - 没有 Golden Case 数据集
   - 没有自动化评测指标（Tool Call 准确率、任务完成率、报告质量评分）
   - 无法量化证明系统效果

2. **Function Calling / 工具调用无容错**
   - Tavily 搜索只有简单重试，无指数退避
   - 无参数校验层（Pydantic/JSON Schema）
   - 无工具调用耗时/Token 消耗记录
   - 无结构化 ToolError 返回给 LLM

3. **无可观测性平台**
   - 只有本地日志，无 Trace 追踪
   - 无 AgentOps / LangSmith 集成
   - 无法回溯单次请求的完整执行链路

### P1 — 强烈推荐

4. **记忆系统可增强**
   - 当前只有摘要压缩，无向量化的长期记忆
   - 无记忆反思/更新机制（Generative Memory）
   - 无"何时写入"和"如何检索"的策略设计

5. **无动态重规划**
   - 当前 planner 只在审查失败后重新规划
   - 执行中发现计划错误无法自动修正
   - 无死循环检测（靠 MAX_REVISIONS 硬限制）

6. **前端无测试**
   - 零前端测试覆盖
   - 无组件快照测试
   - 无 E2E 测试

### P2 — 锦上添花

7. **无 MCP 协议支持**
8. **无 Token 预算控制**
9. **无 Prompt Injection 防护**
10. **无 A/B 测试框架**

---

## 开发命令速查

```bash
# 后端启动
cd backend && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端启动
cd frontend && npm install && npm run dev  # http://localhost:5173

# 测试
cd backend
pytest                            # 全量
pytest tests/test_router.py       # 单文件
pytest -k "test_looks_like_refine" # 单用例

# Docker
docker compose up -d --build

# 无 lint/typecheck/formatter，测试是唯一门控
```

---

## 关键设计决策（面试可讲）

1. **图拓扑纠错 > 代码 if-else**：用 LangGraph 条件边把"审查不通过就回跳 Planner"变成图的拓扑结构，天然支持循环
2. **模块级单例拓扑 + 请求级 checkpointer**：拓扑构建一次，每次请求只挂载 checkpointer，平衡性能和隔离性
3. **msgpack 而非 JSON**：LangGraph checkpoint 用 msgpack 序列化，`channel_values` 在顶层，自定义读写必须用 `msgpack.packb/unpackb`
4. **模糊后续 vs 明确修改双模式**：`_is_vague()` 区分用户意图，避免把"你觉得呢"这种追问当全文重写处理
5. **熔断机制**：文档模式下 Relevance Grader 判断文档不相关时直接终止，hybrid 模式下降级为全网搜索，不编造信息
6. **记忆压缩三级降级**：LLM 压缩失败 → 按句子边界截断 → 硬截断，永不阻塞主流程

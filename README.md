# IRIS — AI Research Agent

> 基于有向图编排的多步骤 AI 研究智能体。支持文档解析 + 联网检索，可自动规划搜索策略、多源采集信息并输出结构化研究报告，报告质量不达标时基于评审反馈自动迭代重写。

### 系统界面

主界面分为三个区域：
- **左侧输入区**：文本框输入研究主题（如"2026 年 AI Agent 技术框架对比"），PDF 上传按钮支持批量上传参考文档（最多 5 个）
- **模式切换**：Document Only（仅本地文档）/ Hybrid（本地+联网搜索）
- **右侧展示区**：Agent 执行状态实时显示（Planner → Researcher → Writer → Reviewer），报告以打字机效果逐行渲染，支持 Markdown 格式与数学公式（KaTeX）

---

## 解决了什么问题

深度调研是一个重复性高、容易遗漏的流程。传统方式：手动搜资料 → 整理笔记 → 写报告。三个痛点：

1. **信息渠道分散** — 官网、技术博客、行业报告、内部文档，跨来源整合费时
2. **质量没法保证** — 人工搜容易漏，写报告时可能凭印象写错
3. **修改成本高** — 写完发现缺了某方面，要重新搜重新写

IRIS 把这个流程自动化了：输入一个研究主题，上传参考文档（可选），Agent 自动完成全流程。

---

## 核心特性

### 🧠 6 节点 Agent 状态机（LangGraph）

不同于传统线性 RAG，IRIS 用 LangGraph StateGraph 定义了 6 个专有节点，通过条件边实现路径分支、熔断短路、质量环路三种执行模式：

- **Router** — 意图识别，判断用户是要"开新研究"还是"修改报告某章节"
- **Planner** — 任务规划，把研究主题拆成 3-5 个子问题
- **Researcher** — 多源检索（本地文档 + 网络搜索），Relevance Grader 评估文档相关性
- **Writer** — 基于检索结果撰写结构化报告
- **Reviewer** — 质量审查，FAIL 时回跳 Planner 重新检索（最多 3 轮）
- **Refiner** — 局部修改，"把第三章写详细点"只改对应部分，不重写全文

### 🛡️ 防幻觉熔断机制

当用户上传的文档与研究主题无关时，Grader LLM 判断相关性，不相关时触发熔断——系统不编造信息，而是提示用户补充资料或切换到混合搜索模式。

### 🔄 质量审查闭环

Writer 写完报告后，Reviewer 做 JSON 格式审查，内容深度、结构完整度、格式规范任一项不达标就回跳 Planner 重新规划搜索策略，实现"查→写→审→重查→重写"自动迭代，最多 3 轮，无需人工介入。

### ⚡ SSE 流式响应

后端 FastAPI 异步框架，LangGraph 的 `astream()` 逐节点推送执行状态，前端打字机效果实时渲染报告片段，解决多节点执行耗时带来的等待焦虑。

### 🔁 会话级记忆

基于 `AsyncSqliteSaver` 的 SQLite Checkpoint 实现会话持久化，配合 Intent Router 精准区分"开新研究"和"修改已有报告"，支持"把第一章扩写得更详细"等跨轮次局部修订指令。

---

## 系统架构

```
用户输入研究主题
    ↓
Intent Router → 判断 NEW_TOPIC / REFINE
    ├── NEW_TOPIC → Planner → Researcher → Relevance Grader
    │                          ├── 不相关 → 熔断终止（纯文档模式）
    │                          │         → 自动降级（混合模式）
    │                          └── 相关   → Writer → Reviewer
    │                                         ├── FAIL → 回跳 Planner（最多3轮）
    │                                         └── PASS → 输出报告
    └── REFINE → Refiner → 直接修改已有报告（快通道，不进审查循环）
```

---

## 技术栈

### 后端
- **Python 3.10+** / **FastAPI** — 全异步架构
- **LangGraph** — 有向图状态机编排
- **ChromaDB** — 本地文档向量检索
- **CrossEncoder (ms-marco-MiniLM-L-6-v2)** — 两段式精排（可选，通过 `ENABLE_RERANKER` 环境变量控制）
- **Tavily** — 网络搜索
- **aiosqlite** — 异步 SQLite Checkpoint

### 前端
- **Vue 3** (Composition API) / **Tailwind CSS**
- **markdown-it** + **markdown-it-katex** — 报告渲染
- **SSE** — 流式推送 + 打字机效果

### 双模型架构
- **快模型（qwen3-max）**：意图分类、策略规划、内容生成、报告修订 — 追求低延迟
- **慢模型（deepseek-r1）**：文档相关性判定、质量评审 — 追求判断准确性

---

## 快速开始

```bash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
# 配置 .env: OPENAI_API_KEY, OPENAI_API_BASE, TAVILY_API_KEY
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd ../frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

---

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `OPENAI_API_KEY` | DashScope / OpenAI API Key | ✅ |
| `OPENAI_API_BASE` | API 端点（如 DashScope: `https://dashscope.aliyuncs.com/compatible-mode/v1`） | ✅ |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | ✅ |
| `ENABLE_RERANKER` | 启用 CrossEncoder 精排（`true`/`false`，默认 `false`，开启需额外 ~400MB 内存） | ❌ |
| `CORS_ORIGINS` | 允许的跨域来源（逗号分隔，默认 `*`） | ❌ |

---

## 核心文件

| 文件 | 内容 |
|------|------|
| `backend/app/graph/graph.py` | 状态机拓扑定义（6节点 + 条件边） |
| `backend/app/graph/nodes/` | 各节点实现（router/planner/researcher/writer/reviewer/refiner） |
| `backend/app/rag/engine.py` | 两段式 RAG 引擎（Chroma 粗召回 + 可选 CrossEncoder 精排） |
| `backend/app/api/routes.py` | FastAPI 路由 + SSE 流式响应 |
| `backend/app/utils/llm.py` | LLM 工厂（fast/smart 双模型策略） |
| `frontend/src/App.vue` | 前端主页面（SSE 消费 + 打字机渲染） |

---

## 研发心得

IRIS 最核心的设计决策是把"纠错"表达成图的拓扑，而不是代码里的 if-else。

传统 RAG 是链式的：检索→生成，一次过，没有回头路。IRIS 用 LangGraph 的条件边把"审查不通过就回跳 Planner"变成了图拓扑里的一条回边——这不是 hack，是图的拓扑结构天然支持循环。

这带来了三个工程上的挑战：
1. **退出条件** — 没有退出条件会死循环，所以加了 `revision_number` 上限 3 次
2. **LLM 输出不稳定** — Reviewer 要求 JSON 输出，但模型经常带 Markdown 代码块，加了 `_clean_json_text` 后处理 + fail-closed 兜底
3. **内存控制** — CrossEncoder 模型文件约 400MB，多进程部署时每个进程都加载一份，通过 `ENABLE_RERANKER` 环境变量控制是否启用

这个项目是对 Agentic System 底层运行机制的一次深度工程实践。
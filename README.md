# IRIS — AI Research Agent

> 基于 LangGraph 状态机的智能调研系统。支持文档解析 + 联网检索 + AI 灵感发现，自动规划搜索策略、多源采集信息并输出结构化研究报告。

### 系统界面

主界面采用 Tab 切换布局：
- **输入区（常驻）**：文本框输入研究主题，Ctrl+Enter 快速开始
- **左侧面板（Tab 切换）**：知识库管理 / AI 灵感发现 / 研究历史
- **右侧展示区**：报告以打字机效果渲染，支持 TOC 目录导航 + 多格式导出

---

## 解决了什么问题

深度调研是一个重复性高、容易遗漏的流程。IRIS 把这个流程自动化了：

1. **信息渠道分散** — 官网、技术博客、行业报告、内部文档，跨来源整合费时
2. **质量没法保证** — 人工搜容易漏，写报告时可能凭印象写错
3. **修改成本高** — 写完发现缺了某方面，要重新搜重新写

输入一个研究主题，上传参考文档（可选），Agent 自动完成全流程。

---

## 核心特性

### 🧠 6 节点 Agent 状态机（LangGraph）

- **Router** — 意图识别，判断"开新研究"还是"修改报告"
- **Planner** — 任务规划，把研究主题拆成 3-5 个子问题
- **Researcher** — 多源检索（本地文档 + 网络搜索），Relevance Grader 评估相关性
- **Writer** — 基于检索结果撰写结构化报告
- **Reviewer** — 质量审查，FAIL 时回跳 Planner 重新检索
- **Refiner** — 局部修改，只改用户要求的部分

### 🛡️ 防幻觉熔断机制

文档与问题不相关时，Grader LLM 触发熔断——系统不编造信息，纯文档模式终止，混合模式自动降级为全网搜索。

### 🔄 质量审查闭环

Writer 写完 → Reviewer 审查 → FAIL 回跳 Planner → 重新搜索重写，自动迭代，无需人工介入。

### 🤖 模型自动降级

主模型（qwen3.7-plus）额度耗尽 → 自动切换备用模型（deepseek-v4-flash），5 分钟后自动恢复尝试。

### 🔍 AI 灵感发现

集成 AI HOT 资讯平台，实时获取 AI 行业动态，支持 5 分类筛选（模型/产品/行业/论文/技巧），点击即可作为调研主题。

### 📚 寻阶行工作流集成

调研报告可一键保存到公众号素材库，自动追加寻阶行水印，历史记录支持标记"已用于文章"。

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
    │                                         ├── FAIL → 回跳 Planner
    │                                         └── PASS → 输出报告
    └── REFINE → Refiner → 直接修改已有报告
```

---

## 技术栈

### 后端
- **Python 3.11+** / **FastAPI** — 全异步架构
- **LangGraph** — 有向图状态机编排
- **ChromaDB** — 本地文档向量检索
- **Tavily** — 网络搜索
- **SQLite** — 会话持久化 + 自动清理

### 前端
- **Vue 3** (Composition API) / **Tailwind CSS**
- **markdown-it** + **markdown-it-katex** — 报告渲染
- **SSE** — 流式推送 + 打字机效果

### LLM
- **主模型**: qwen3.7-plus (DashScope)
- **备用模型**: deepseek-v4-flash (DashScope)
- **Embedding**: text-embedding-v4 (DashScope)

---

## 快速开始

```bash
# 后端
cd backend
python -m venv venv && venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env  # 填入 API Key
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd ../frontend
npm install && npm run dev
# 访问 http://localhost:5173
```

---

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `OPENAI_API_KEY` | DashScope API Key | ✅ |
| `OPENAI_API_BASE` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | ✅ |
| `DASHSCOPE_API_KEY` | Embedding API Key | ✅ |
| `TAVILY_API_KEY` | Tavily 搜索 Key | ✅ |
| `LLM_MODEL_PRIMARY` | 主模型（默认 qwen3.7-plus） | ❌ |
| `LLM_MODEL_FALLBACK` | 备用模型（默认 deepseek-v4-flash） | ❌ |
| `CORS_ORIGINS` | 允许的域名（生产必填） | ❌ |
| `ENABLE_RERANKER` | CrossEncoder 精排（2G 服务器不要开） | ❌ |
| `CREATION_DIR` | 报告保存目录 | ❌ |
| `CHECKPOINT_DB` | SQLite 路径 | ❌ |

---

## 部署

支持 Docker 部署，详见 `backend/DEPLOY.md`。

```bash
cd backend
docker build -t iris-backend .
docker run -d --name iris -p 8000:8000 --memory=1g -v .env:/app/.env iris-backend
```

---

## 核心文件

| 文件 | 内容 |
|------|------|
| `backend/app/graph/graph.py` | 状态机拓扑定义 |
| `backend/app/graph/nodes/` | 6 个智能体节点 |
| `backend/app/rag/engine.py` | RAG 引擎（Chroma + 可选精排） |
| `backend/app/api/routes.py` | API 路由（SSE + 限流 + 代理） |
| `backend/app/utils/llm.py` | 模型工厂（带自动降级） |
| `backend/app/config.py` | 集中配置 |
| `frontend/src/App.vue` | 前端主页面 |
| `frontend/src/services/history.js` | 历史管理 |

---

## 研发心得

IRIS 最核心的设计决策是把"纠错"表达成图的拓扑，而不是代码里的 if-else。

传统 RAG 是链式的：检索→生成，一次过，没有回头路。IRIS 用 LangGraph 的条件边把"审查不通过就回跳 Planner"变成了图拓扑里的一条回边——这不是 hack，是图的拓扑结构天然支持循环。

这个项目是对 Agentic System 底层运行机制的一次深度工程实践。

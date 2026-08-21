# IRIS 投研信息聚合平台

> **基于 LangGraph 多智能体协同的 A 股投资研究系统**
>
> `Python 3.11+` `FastAPI` `LangGraph 1.0+` `Vue 3` `AKShare` `DeepSeek` `ChromaDB`

**七节点多智能体协同 + AKShare 真实 A 股数据 + 中文六章节投研报告 + Gradio 演示**

---

## 项目简介

### 痛点

传统金融研报分析高度依赖人工：研究员手动翻阅 PDF 提取信息、反复切换平台查询市场数据、再凭经验撰写报告。整个过程**数据检索分散、流程割裂**，一份深度研报平均耗时 3-5 小时。通用 Chatbot 无法自动完成"解析→检索→分析→撰写"的闭环，且容易产生幻觉。

### 方案

IRIS 基于 **LangGraph StateGraph** 搭建 **七节点多智能体协同架构**，将投研分析拆解为 7 个独立子任务，分别交给 7 个专业 Agent 执行。系统接入 AKShare 真实 A 股数据（行情/财务/研报），输出符合券商规范的中文六章节研报。

### 适用场景

- 📄 **个股研报分析**：输入股票代码/名称，自动拉取行情+财务+新闻 → 生成深度分析
- 🏭 **行业数据整理**：输入行业关键词，检索板块行情与财务指标
- ✍️ **自动化研报撰写**：全自动生成券商风格的 Markdown 投资分析报告

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3 + Tailwind)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ 智能问答 Tab  │  │ 投研分析 Tab  │  │ 实时行情 + 报告渲染   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ SSE / REST
┌─────────────────────────────▼───────────────────────────────────┐
│                  API Gateway (FastAPI)                            │
│   限流 · 认证 · 文件上传 · 报告管理 · TTS · LangSmith             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│              LangGraph StateGraph (7 节点协同)                    │
│                                                                  │
│  router → planner → researcher → data_collector → writer          │
│                                   │                              │
│                              reviewer ──FAIL──→ planner (循环)    │
│                                   │                              │
│                              refiner (多轮追问/修改)              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      数据层 (Data Layer)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ AKShare      │  │ Tavily       │  │ ChromaDB RAG         │  │
│  │ (A股行情/财务)│  │ (网络搜索)   │  │ (本地文档检索)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心特性

### 1. 七节点多智能体协同

| 节点 | 职责 | 关键技术 |
| ------ | ------ | --------- |
| 🧠 **Router** | 意图识别：新话题 / 修改报告 | LLM 分类 + 关键词兜底 |
| 📋 **Planner** | 搜索规划：生成 3-5 个子方向 | 对话上下文 + 搜索方向去重 |
| 🔍 **Researcher** | 多源检索：本地文档 + 网络搜索 | ChromaDB RAG + Tavily + Grader 审计 |
| 📊 **DataCollector** | 金融数据拉取：AKShare 并行调用 | ThreadPoolExecutor 扇出 + 三层降级 |
| ✍️ **Writer** | 中文研报撰写：六章节格式 | 数据与观点分离 + 来源标注 |
| 🔍 **Reviewer** | 质量审查：PASS/FAIL + 修复循环 | JSON 输出 + cosine 相似度早停 |
| 🔧 **Refiner** | 多轮修改：模糊追加 / 明确重写 | 双模式修订策略 |

### 2. AKShare 真实 A 股数据接入

- **三层降级**：东方财富 → 雪球/新浪 → 内置模拟数据
- **数据模块**：`query_stock_info` / `query_financial_indicators` / `query_stock_quote`
- **永不抛异常**：工具级故障隔离，单工具失败不影响整体流程
- **来源标注**：所有数值标注 `[来源: AKShare 东方财富]`

### 3. 中文六章节投研报告

```markdown
# {公司名}（{代码}）投资分析报告

## 一、核心结论与投资摘要
## 二、公司概况（表格：指标|数值|来源）
## 三、财务分析（营收/盈利/偿债/现金流）
## 四、行业观点与竞争格局
## 五：风险提示（⚠️ 数据不足时标注）
## 六、投资建议（仅供参考）+ 免责声明
```

**数据与观点分离**：表格数值直接来自 `financial_data` JSON（不经 LLM 改写），LLM 只写评述——从机制上防幻觉。

### 4. 工程鲁棒性

| 机制 | 实现 |
| ------ | ------ |
| **死循环防护** | MAX_REVISIONS(5) + cosine 相似度早停(0.95) |
| **LLM 降级** | 主模型 → 备用模型（5min TTL 自动恢复） |
| **数据降级** | 三层数据源 + 模拟数据兜底 |
| **工具容错** | 永不抛异常，结构化错误 JSON |
| **限流** | SQLite 滑动窗口（每 IP 5次/分钟） |
| **可观测性** | LangSmith traceable 全链路 |

---

## 快速开始

### 环境要求

- **Python**：3.11+
- **Node.js**：v22.22.2 || v24.15.0 || >=26.0.0
- **网络**：需能访问 AKShare / DeepSeek API

### 一键启动

```bash
# 1. 克隆仓库
git clone https://github.com/your-repo/iris-project.git
cd iris-project

# 2. 启动后端
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
# 配置 .env（填入 DeepSeek API Key）
cp .env.example .env
python main.py
# 后端运行于 http://localhost:8000

# 3. 启动前端
cd ../frontend
npm install
npm run dev
# 前端运行于 http://localhost:5173
```

### 两种使用方式

```bash
# 方式一：Web 界面（推荐）
# 浏览器访问 http://localhost:5173
# "投研分析" Tab → 输入股票代码 → 开始分析

# 方式二：API 调用
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "分析复星医药 600196 的投资价值", "thread_id": "demo"}'
```

---

## 项目结构

```
IRIS/
├── backend/                          # FastAPI + LangGraph 核心
│   ├── app/
│   │   ├── agents/
│   │   │   └── prompts.py            # 中文研报提示词模板 + 数据表格生成器
│   │   ├── api/
│   │   │   └── routes.py             # REST + SSE 路由（含股票查询 API）
│   │   ├── graph/
│   │   │   ├── state.py              # AgentState（18 字段，含 financial_data）
│   │   │   ├── graph.py              # StateGraph 拓扑（7 节点）
│   │   │   └── nodes/                # 7 个 Agent 节点
│   │   │       ├── router.py         # 意图路由
│   │   │       ├── planner.py        # 搜索规划
│   │   │       ├── researcher.py     # 多源检索 + Grader
│   │   │       ├── data_collector.py # AKShare 数据拉取（扇出并行）
│   │   │       ├── writer.py         # 中文研报撰写
│   │   │       ├── reviewer.py       # 质量审查 + cosine 早停
│   │   │       └── refiner.py        # 多轮修改
│   │   ├── rag/
│   │   │   └── engine.py             # ChromaDB RAG + 文档审计
│   │   ├── tools/
│   │   │   ├── akshare_tools.py      # AKShare 3 工具 + 三层降级
│   │   │   └── search.py             # Tavily 搜索
│   │   └── utils/
│   │       ├── llm.py                # 多模型 + 自动降级
│   │       ├── streaming.py          # SSE 流式架构
│   │       ├── memory.py             # 会话记忆
│   │       └── logger.py             # 结构化日志
│   ├── eval/                         # 评测框架
│   ├── tests/                        # 106 个测试（全量通过）
│   ├── main.py                       # FastAPI 入口
│   └── requirements.txt              # 依赖清单
│
├── frontend/                         # Vue 3 + Vite + Tailwind
│   ├── src/
│   │   ├── views/
│   │   │   └── InvestmentResearch.vue # 投研分析页面
│   │   ├── components/               # 聊天组件
│   │   ├── composables/
│   │   │   └── useChat.js             # 聊天逻辑（SSE 流式）
│   │   ├── services/
│   │   │   ├── api.js                # API 客户端
│   │   │   └── finance.js            # 投研分析 API 服务
│   │   └── App.vue                   # 根组件（Tab 导航）
│   └── package.json
│
├── docs/research/                    # 调研报告（6 份）
├── REFACTOR_PLAN.md                  # 分阶段重构计划（含面试验证）
├── AGENTS.md                         # 项目指南
├── PROJECT_BRIEFING.md               # 项目简报
└── CLAUDE.md                         # Claude Code 配置
```

---

## 配置说明

| 环境变量 | 说明 | 默认值 |
| --------- | ------ | -------- |
| `OPENAI_API_KEY` | DeepSeek API 密钥 | - |
| `OPENAI_API_BASE` | API 基础地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL_PRIMARY` | 主模型 | `qwen3.7-plus` |
| `LLM_MODEL_FALLBACK` | 备用模型 | `deepseek-v4-flash` |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | - |
| `LANGSMITH_API_KEY` | LangSmith 可观测性（可选） | - |
| `DEEPSEEK_API_KEY` | DeepSeek 密钥（旧版兼容） | - |

---

## 测试覆盖

```
106 tests in 38.03s

├── test_akshare_tools.py     13 passed  (AKShare 工具层 + mock)
├── test_data_collector.py     9 passed  (DataCollector 节点 + mock)
├── test_chinese_report.py    11 passed  (中文报告格式 + 表格生成)
├── test_router.py            18 passed  (意图路由)
├── test_reviewer.py          12 passed  (质量审查)
├── test_researcher.py         6 passed  (多源检索)
├── test_llm.py                9 passed  (LLM 工厂)
└── test_graph.py              6 passed  (图拓扑)
```

---

## 开发路线图

### ✅ 已完成（v1.0）

- [x] 基于 LangGraph StateGraph 的七节点多智能体协同架构
- [x] AKShare 真实 A 股数据接入（三层降级）
- [x] 中文六章节投研报告格式（数据与观点分离）
- [x] 多模型 LLM 降级 + SSE 流式输出
- [x] ChromaDB RAG + 文档相关性审计
- [x] 会话记忆系统（增量摘要 + checkpoint）
- [x] LangSmith 全链路可观测性
- [x] 限流器 + 生产级 FastAPI 后端
- [x] Vue 3 前端（智能问答 + 投研分析 Tab）
- [x] 106 个测试，零回归

### 🚧 规划中（v1.1）

- [ ] 多股票对比分析
- [ ] 行业数据聚合
- [ ] 定时研报生成任务
- [ ] 报告导出（PDF / Word）
- [ ] 前端 Gradio 演示入口

### 🔮 远期规划（v2.0）

- [ ] MCP 协议集成（eastmoney MCP）
- [ ] 研报 PDF 入库 RAG
- [ ] 新闻/公告实时聚合
- [ ] 人工审核节点（HITL）
- [ ] 多用户权限管理

---

## 面试技术亮点

| 面试问题 | 回答要点 |
| --------- | --------- |
| 为什么选 LangGraph？ | 显式状态 + 条件路由 + Checkpoint，适合可审计的确定性流程 |
| 如何防死循环？ | MAX_REVISIONS(5) + cosine 相似度早停(0.95) |
| 如何防幻觉？ | 数据与观点分离 + 来源标注 + 诚实告知原则 |
| 如何降级？ | 三层数据源 + LLM 主备切换 + 工具级不抛异常 |
| 多 Agent 架构？ | 7 节点协同，每节点独立解耦，可单独测试替换 |
| Function Calling？ | `@tool` 声明 + `bind_tools` + `ToolNode` + `tools_condition` |
| 记忆系统？ | conversation_summary 增量摘要 + checkpoint 跨会话持久化 |

---

## 开源协议

MIT License

---

<p align="center">
  <sub>Built with ❤️ using LangGraph + DeepSeek + AKShare | IRIS v1.0</sub>
</p>

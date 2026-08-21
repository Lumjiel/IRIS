# IRIS 项目完整概况 — 供优化 Agent 参考

## 项目简介

IRIS (Intelligent Research Insight System) — 基于 LangGraph 状态机的 A 股投研信息聚合平台。

**技术栈**：FastAPI + LangGraph 1.0.8 + AKShare + ChromaDB + Tavily + DeepSeek + Vue 3 + Tailwind CSS

**核心流程**：用户输入股票代码/名称 → 意图路由 → 规划搜索方向 → 多源检索（文档+网络+AKShare）→ 撰写中文六章节研报 → 质量审查 → 输出。支持多轮对话追问修改。

---

## 项目结构

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
│   │   │       ├── search_agent.py  # Function Calling agent
│   │   │       ├── data_collector.py # AKShare 数据拉取
│   │   │       ├── writer.py        # 中文研报撰写（async）
│   │   │       ├── reviewer.py      # 质量审查 + cosine 早停
│   │   │       └── refiner.py       # 双模式修订（async）
│   │   ├── rag/
│   │   │   ├── engine.py            # ChromaDB + DashScope embedding
│   │   │   └── report_ingest.py     # 研报 PDF 入库 + 实体抽取
│   │   ├── tools/
│   │   │   ├── akshare_tools.py     # AKShare 4 工具（含新闻）+ 三层降级
│   │   │   ├── search_tools.py      # Function Calling @tool 声明
│   │   │   └── search.py            # Tavily 搜索封装
│   │       ├── llm.py               # LLM 工厂 + 自动降级（5 分钟 TTL）
│   │       ├── streaming.py         # ContextVar + asyncio.Queue 流式架构
│   │       ├── memory.py            # 会话摘要：增量更新 + 压缩 + 搜索方向避让
│   │       └── logger.py            # 结构化日志
│   ├── eval/                        # 评测框架
│   ├── tests/                       # 106 个测试（全量通过）
│   ├── conftest.py                  # Mock 外部依赖 + sample_state fixture
│   ├── pytest.ini                   # asyncio_mode = auto
│   ├── requirements.txt             # 依赖清单（含 akshare）
│   └── DEPLOY.md                    # 部署指南
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   └── InvestmentResearch.vue # 投研分析页面（股票输入 + 流式报告）
│   │   ├── components/              # 聊天组件（ChatHeader/ChatMessages/ChatInput/ChatSidebar）
│   │   ├── composables/
│   │   │   └── useChat.js            # 聊天逻辑（SSE 流式）
│   │   ├── services/
│   │   │   ├── api.js               # API 客户端
│   │   │   └── finance.js           # 投研分析 API 服务
│   │   └── App.vue                  # 根组件（Tab 导航：智能问答 + 投研分析）
│   └── package.json
├── docs/research/                   # 调研报告（6 份）
├── REFACTOR_PLAN.md                 # 分阶段重构计划（含面试验证）
├── AGENTS.md                        # 项目指南
├── PROJECT_BRIEFING.md              # 本文件
└── CLAUDE.md                        # Claude Code 配置
```

---

## 核心架构

### 八节点状态机 + Function Calling

```
router (conditional entry)
  ├── NEW_TOPIC → planner → researcher → search_agent ⇄ search_tools → data_collector → writer → reviewer
  │                                                              └── FAIL → planner (循环)
  └── REFINE → refiner → END
```

| 节点 | 职责 | 关键技术 |
| ------ | ------ | --------- |
| 🧠 Router | 意图识别：新话题 / 修改报告 | LLM 分类 + 关键词兜底 |
| 📋 Planner | 搜索规划：生成 3-5 个子方向 | 对话上下文 + 搜索方向去重 |
| 🔍 Researcher | 本地文档检索 + 文档审计 | ChromaDB RAG + Grader |
| 🤖 SearchAgent | LLM 驱动的网络搜索 | Function Calling: `@tool` + `bind_tools` |
| 🔧 SearchTools | 执行 LLM 决定的工具调用 | 自定义 ToolNode |
| 📊 DataCollector | 金融数据拉取：AKShare 并行调用 | ThreadPoolExecutor 扇出 + 三层降级 |
| ✍️ Writer | 中文研报撰写：六章节格式 | 数据与观点分离 + 来源标注 |
| 🔍 Reviewer | 质量审查：PASS/FAIL + 修复循环 | JSON 输出 + cosine 相似度早停 |
| 🔧 Refiner | 多轮修改：模糊追加 / 明确重写 | 双模式修订策略 |
### AgentState（20+ 字段）

核心字段：`query`, `plan`, `search_results`, `final_report`, `critique`, `revision_number`, `review_status`, `search_mode`, `should_stop`, `conversation_summary`, `preferences`, `error_code`, `degraded`, `failed_tools`, `early_stop`, `should_continue`, `report_history`, `tool_status`, **`financial_data`**, **`data_sources`**, **`pending_stock_code`**, **`messages`**

### AKShare 数据层

- **4 个工具**：`query_stock_info`, `query_financial_indicators`, `query_stock_quote`, `query_stock_news`
- **三层降级**：东方财富 → 雪球/新浪 → 内置模拟数据
- **永不抛异常**：工具级故障隔离
- **来源标注**：所有数值标注 `[来源: AKShare 东方财富]`

### Function Calling 架构

- **`@tool` 声明**：`search_web` 使用 LangChain `@tool` 装饰器
- **LLM 自主决策**：通过 `bind_tools([search_web])` 绑定工具，LLM 决定何时调用
- **自定义 ToolNode**：`search_tool_node` 执行工具调用（避免 `langgraph.prebuilt` 版本兼容问题）
- **消息累加**：`add_messages` reducer 自动累加到 `state["messages"]`

### 研报 RAG

- **PyMuPDF 抽取**：`import fitz` 抽取 PDF 全文
- **实体抽取**：正则抽取公司名/代码/评级/目标价/日期
- **元数据入库**：ChromaDB metadata 存 `{source, stock_code, rating, report_date}`
### 中文六章节研报格式

```markdown
# {公司名}（{代码}）投资分析报告
## 一、核心结论与投资摘要
## 二、公司概况（表格：指标|数值|来源）
## 三、财务分析（营收/盈利/偿债/现金流）
## 四、行业观点与竞争格局
## 五、风险提示（⚠️ 数据不足时标注）
## 六、投资建议（仅供参考）+ 免责声明
```

**数据与观点分离**：表格数值直接来自 `financial_data` JSON（不经 LLM 改写），LLM 只写评述。

---

## 测试覆盖

```
127 tests in 38.16s

├── test_akshare_tools.py     13 passed  (AKShare 工具层 + mock)
├── test_data_collector.py     9 passed  (DataCollector 节点 + mock)
├── test_chinese_report.py    11 passed  (中文报告格式 + 表格生成)
├── test_router.py            18 passed  (意图路由)
├── test_reviewer.py          12 passed  (质量审查)
├── test_researcher.py         5 passed  (RAG 检索 + 审计)
├── test_search_agent.py       8 passed  (Function Calling 节点)
├── test_report_ingest.py     13 passed  (研报入库 + 检索)
├── test_llm.py                9 passed  (LLM 工厂)
├── test_graph.py              6 passed  (图拓扑)
└── integration/              23 passed  (集成测试)
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
| ------ | ------ | -------- |
| `OPENAI_API_KEY` | DeepSeek API 密钥 | - |
| `OPENAI_API_BASE` | API 基础地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL_PRIMARY` | 主模型 | `qwen3.7-plus` |
| `LLM_MODEL_FALLBACK` | 备用模型 | `deepseek-v4-flash` |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | - |
| `LANGSMITH_API_KEY` | LangSmith 可观测性（可选） | - |

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

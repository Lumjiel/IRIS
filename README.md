# IRIS 投研信息聚合平台

> **基于 LangGraph 多智能体协同的 A 股投资研究系统**
>
> `Python 3.11+` `FastAPI` `LangGraph 1.0+` `Vue 3` `AKShare` `DeepSeek` `ChromaDB` `PyMuPDF`

**LangGraph 多智能体协同（15 个注册节点）+ Function Calling + 同花顺/东财真实 A 股数据 + 中文六章节投研报告 + 研报 RAG + Vue 前端**

---

## 项目简介

### 痛点

传统金融研报分析高度依赖人工：研究员手动翻阅 PDF 提取信息、反复切换平台查询市场数据、再凭经验撰写报告。整个过程**数据检索分散、流程割裂**，一份深度研报平均耗时 3-5 小时。通用 Chatbot 无法自动完成"解析→检索→分析→撰写"的闭环，且容易产生幻觉。

### 方案

IRIS 基于 **LangGraph StateGraph** 搭建 **多智能体协同架构**（`backend/app/graph/graph.py` 实际注册 15 个节点：核心 Agent 链 + load_memories 长期记忆注入 + 分章写作等支撑节点）。系统接入 AKShare 真实 A 股数据（行情/财务/新闻）+ 研报 PDF 入库检索，输出符合券商规范的中文六章节研报。

### 适用场景

- 📄 **个股研报分析**：输入股票代码/名称，自动拉取行情+财务+新闻 → 生成深度分析
- 🏭 **行业数据整理**：输入行业关键词，检索板块行情与财务指标
- ✍️ **自动化研报撰写**：全自动生成券商风格的 Markdown 投资分析报告
- 📊 **研报 PDF 管理**：上传研报 PDF → 自动入库 → 检索命中

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
│              LangGraph StateGraph (多节点协同)                    │
│                                                                  │
│  load_memories（长期记忆注入）                                    │
│      → router → planner → researcher → search_agent ⇄ tools     │
│                                        ↓                         │
│  route_after_tools → data_collector → writer → reviewer ─FAIL─→ planner │
│                                        │                        │
│                                   refiner (多轮追问/修改)         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      数据层 (Data Layer)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ AKShare      │  │ Tavily       │  │ ChromaDB RAG         │  │
│  │ (行情/财务/  │  │ (网络搜索)   │  │ (本地文档 + 研报)    │  │
│  │  新闻)       │  │              │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心特性

### 1. 多智能体协同 + Function Calling + 长期记忆

| 节点 | 职责 | 关键技术 |
| ------ | ------ | --------- |
| 🧠 **Router** | 意图识别：新话题 / 修改报告 | LLM 分类 + 关键词兜底 |
| 📋 **Planner** | 搜索规划：生成 3-5 个子方向 | 对话上下文 + 搜索方向去重 |
| 🔍 **Researcher** | 本地文档检索 + 文档相关性审计 | ChromaDB RAG + Grader |
| 🤖 **SearchAgent** | LLM 驱动的网络搜索 | Function Calling: `@tool` + `bind_tools` + 自定义 ToolNode |
| 🔧 **SearchTools** | 执行 LLM 决定的工具调用 | Tavily 搜索 + 新闻 API |
| 📊 **DataCollector** | 金融数据拉取：AKShare 并行调用 | ThreadPoolExecutor 扇出 + 四层降级 + 60s 缓存 |
| ✍️ **Writer** | 中文研报撰写：六章节格式 | 数据与观点分离 + 来源标注 |
| 🔍 **Reviewer** | 质量审查：PASS/FAIL + 修复循环 | JSON 输出 + cosine 相似度早停 |
| ✍️ **Refiner** | 双模式修订（多轮追问/修改） | 对话摘要上下文 |

**Function Calling 改造亮点**：

- 传统方式：Python 直接调用 `search_tavily(q)`（硬编码搜索关键词）
- IRIS 方式：LLM 通过 `bind_tools(tools)` 自主决定**何时搜索、搜索什么**
- LLM 返回 `tool_calls` → `ToolNode` 执行 → 结果自动累加到 `state["messages"]`
- 支持多轮迭代：agent → tools → agent → tools → ... → 结束（≤5 轮自动终止）

### 2. AKShare 真实 A 股数据接入 + 行情 K 线

- **四层降级**：同花顺官方 API（L0）→ 东方财富 → 雪球/新浪 → 内置 Mock 数据（服务器环境东财被封，实际走同花顺 L0 单链，fail-open）
- **4 个数据工具**：`query_stock_info` / `query_financial_indicators` / `query_stock_quote` / `query_stock_news`
- **60s 缓存**：全市场数据 TTL 缓存，消灭 30s 全量拉取
- **行情 K 线 API**：`/api/stock/{code}/kline`（个股日 K，多源降级：东财 → 新浪 → 腾讯）+ `/api/index/{code}/kline`（指数 K 线）
- **来源标注**：所有数值标注 `[来源: AKShare 东方财富]` 或 `[来源: 同花顺官方API·腾讯行情补充]`
### 3. 中文六章节投研报告

```markdown
# {公司名}（{代码}）投资分析报告

## 一、核心结论与投资摘要
## 二、公司概况（表格：指标|数值|来源）
## 三、财务分析（营收/盈利/偿债/现金流）
## 四、行业观点与竞争格局
## 五、风险提示（⚠️ 数据不足时标注）
## 六、投资建议（仅供参考）+ 免责声明
```

**数据与观点分离**：表格数值直接来自 `financial_data` JSON（不经 LLM 改写），LLM 只写评述——从机制上防幻觉。

### 4. 研报 PDF 入库 RAG

- **PyMuPDF 抽取**（`import fitz`）：全文提取 + 页级处理
- **实体抽取**：正则抽取公司名/代码/评级/目标价/日期
- **元数据入库**：ChromaDB metadata 存 `{source, stock_code, rating, report_date}`
- **按标的检索**：`search_reports(query, stock_code="600196")`

### 5. MCP 工具暴露

- 5 个只读金融工具以 **stdio MCP server** 暴露（`mcp_server.py`）：公司概况 / 财务指标 / 实时行情 / 个股新闻 / 研报 RAG 检索
- `readOnlyHint` 注解 + 口径字段透传（`data_source` / `degraded`，模拟数据明确标记）
- 仓库根 `.mcp.json` 即插即用；工具层与 Web 前端解耦，任意 MCP 客户端可复用（**N×M → N+M**）

### 6. 工程鲁棒性

| 机制 | 实现 |
| ------ | ------ |
| **死循环防护** | MAX_REVISIONS(3) + cosine 相似度早停(0.95) |
| **LLM 降级** | 主模型 → 备用模型（5min TTL 自动恢复） |
| **数据降级** | 四层数据源 + 模拟数据兜底 |
| **工具容错** | 永不抛异常，结构化错误 JSON |
| **限流** | SQLite 滑动窗口（每 IP 5次/分钟） |
| **可观测性** | LangSmith traceable 全链路 |

---

## 快速开始

### 环境要求

- **Python**：3.11+
- **Node.js**：v22+ || v24+
- **网络**：需能访问 AKShare / DeepSeek API

### 一键启动

```bash
# 1. 克隆仓库
git clone https://github.com/your-repo/iris-project.git
cd iris-project

# 2. 启动后端
cd backend
python -m venv venv && source venv/bin/activate
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

### Docker 部署

```bash
docker compose up -d
# 前端: http://localhost:8080（80/443 常被已有 nginx 占用，映射见 docker-compose.yml）
# 后端: 容器内 8000，仅经前端 /api 反代访问
```

### 生产部署（裸机 · 推荐用于云服务器）

已在 `49.234.178.53`（OpenCloudOS 9）验证，非 Docker 方式：

```bash
# 1. 拉取最新代码（服务器 /var/www/IRIS）
cd /var/www/IRIS && git fetch origin && git reset --hard origin/main

# 2. 后端：venv 重建依赖 + uvicorn 8081
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8081 --workers 1

# 3. 前端：构建并上传 dist
cd ../frontend && npm install && npm run build
# 将 dist/ 上传至服务器 /var/www/IRIS/frontend/dist

# 4. Nginx（已有容器）反代：/api → 172.17.0.1:8081，静态 → dist
```

- 公网地址：`https://iris-jie.duckdns.org`
- 后端实际端口：`8081`（非 Docker 文档里的 8000）
- 服务器东财接口被封，AKShare 走同花顺 L0 单链（fail-open），`/api/status` 的 `data_online` 为 false 属正常
- 详细步骤见 `backend/DEPLOY.md`

### 两种使用方式

```bash
# 方式一：Web 界面（推荐）
# 浏览器访问 http://localhost:5173
# "投研分析" Tab → 输入股票代码 → 开始分析

# 方式二：API 调用
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "分析复星医药 600196 的投资价值", "thread_id": "demo"}'

# 方式三：股票数据查询
curl http://localhost:8000/api/stock/600196/info
curl http://localhost:8000/api/stock/600196/financial
curl http://localhost:8000/api/stock/600196/quote
curl http://localhost:8000/api/stock/600196/news
curl "http://localhost:8000/api/stock/600196/kline?period=daily&start=2026-01-01"
curl "http://localhost:8000/api/index/sh000001/kline"
curl http://localhost:8000/api/market/hot
curl http://localhost:8000/api/market/snapshot
# 长期记忆管理（按 X-User-Id 隔离）
curl "http://localhost:8000/api/memory-items" -H "X-User-Id: default"
curl -X POST http://localhost:8000/api/memory-items -H "X-User-Id: default" \
  -H "Content-Type: application/json" -d '{"kind":"preference","content":"偏好简洁结论先行"}'
curl -X PUT "http://localhost:8000/api/memory-items/{key}" -H "X-User-Id: default" \
  -H "Content-Type: application/json" -d '{"kind":"preference","content":"已更新"}'

# 方式四：MCP 客户端复用数据工具（stdio，只读）
# 仓库根已注册 .mcp.json（iris-findata），Claude Code 打开即用；或手动：
#   claude mcp add iris-findata -- backend/.venv/bin/python backend/mcp_server.py
# 工具：query_stock_info / query_financial_indicators / query_stock_quote / query_stock_news / search_reports

# 方式五：研报 RAG
curl -X POST http://localhost:8000/api/reports/upload \
  -F "file=@report.pdf"
curl "http://localhost:8000/api/reports/search?q=复星医药&stock_code=600196"
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
│   │   │   └── routes.py             # REST + SSE 路由（含股票查询/研报 API）
│   │   ├── graph/
│   │   │   ├── state.py              # AgentState（含 financial_data, messages）
│   │   │   ├── graph.py              # StateGraph 拓扑（15 节点 + Function Calling 循环 + 长期记忆入口）
│   │   │   └── nodes/                # 9 个 Agent 节点（含 load_memories）
│   │   │       ├── router.py         # 意图路由
│   │   │       ├── planner.py        # 搜索规划
│   │   │       ├── researcher.py     # RAG 检索 + Grader 审计
│   │   │       ├── search_agent.py   # Function Calling agent
│   │   │       ├── data_collector.py # AKShare 数据拉取
│   │   │       ├── writer.py         # 中文研报撰写
│   │   │       ├── reviewer.py       # 质量审查 + cosine 早停
│   │   │       └── refiner.py        # 多轮修改
│   │   ├── rag/
│   │   │   ├── engine.py             # ChromaDB RAG + 可选 CrossEncoder
│   │   │   └── report_ingest.py      # 研报 PDF 入库 + 实体抽取
│   │   ├── tools/
│   │   │   ├── akshare_tools.py      # AKShare 4 工具（含新闻）+ 四层降级 + 同花顺 L0
│   │   │   ├── search_tools.py       # Function Calling @tool 声明
│   │   │   └── search.py             # Tavily 搜索封装
│   │   └── utils/
│   │       ├── llm.py                # 多模型 + 自动降级
│   │       ├── streaming.py          # SSE 流式架构
│   │       ├── memory.py             # 会话记忆
│   │       └── logger.py             # 结构化日志
│   ├── eval/                         # 评测框架（12 个 Golden Case）
│   ├── tests/                        # 299 个测试（全量通过，覆盖率 69.22%）
│   ├── mcp_server.py                 # MCP stdio server（只读金融工具暴露，任意 MCP 客户端复用）
│   ├── main.py                       # FastAPI 入口
│   └── requirements.txt              # 依赖清单
├── .mcp.json                         # MCP 注册（iris-findata，指向 backend/.venv/bin/python）
├── frontend-next/                    # 新前端壳：React 19 + assistant-ui（重构中，未接入生产部署）
├── frontend/                         # Vue 3 + Vite（当前生产使用的前端，docker-compose 与服务器部署均指向它）
│   ├── src/
│   │   ├── views/
│   │   │   ├── ChatView.vue          # 聊天页（功能引导 + 消息流 + 侧边栏布局 + 附件上传）
│   │   │   ├── MarketView.vue        # 行情页（指数卡 + 自选股 + Sparkline 走势）
│   │   │   ├── SettingsView.vue      # 设置页（API/搜索模式/短期记忆/长期记忆增删改/系统状态）
│   │   │   └── HistoryView.vue       # 历史记录页（真实会话加载）
│   │   ├── components/
│   │   │   ├── chat/                 # ChatHeader / EmptyState / MessageBubble / ChatInput
│   │   │   ├── ChatSidebar.vue        # 侧边栏（自选股名称补全/会话历史/系统状态）
│   │   │   ├── ReportViewer.vue       # 报告渲染（TOC + ScrollSpy）
│   │   │   ├── ResearchTimeline.vue   # 研究进程时间线（节点进度置顶）
│   │   │   ├── MarketDataCard.vue     # 实时行情卡
│   │   │   ├── Sparkline.vue          # K 线/走势迷你图
│   │   │   ├── ProcessBar.vue         # 研究进度条（消息顶部）
│   │   │   ├── NewsTicker.vue         # 滚动资讯条
│   │   │   ├── FollowUpInput.vue       # 多轮追问输入
│   │   │   ├── TermTip.vue            # 术语提示
│   │   │   ├── ActionBar.vue          # 操作栏（复制/下载/保存）
│   │   │   └── Toast.vue              # 全局提示
│   │   ├── composables/               # useChat / useToast / useWatchlist / useThrottledRender
│   │   ├── router/                    # vue-router 配置（懒加载）
│   │   ├── stores/                    # pinia 全局 store
│   │   ├── services/                  # api / finance / history / config（统一 API base）
│   │   ├── App.vue                    # 路由壳
│   │   ├── style.css                  # 毛玻璃全局样式
│   │   └── main.js
│   └── package.json
├── deploy/                           # Nginx 配置 + 演示前自检脚本
├── docker-compose.yml                # Docker 部署（backend + frontend）
├── eval/                             # LLM 裁判（llm_judge.py）+ 真实报告首评结果
├── docs/research/                    # 调研报告（7 份）
├── docs/interview/                   # 面试文档（6 份，细到能照着讲）
├── docs/archive/                     # 历史文档（REFACTOR_PLAN / PROJECT_BRIEFING / blueprint）
├── AGENTS.md                         # 项目指南
└── CLAUDE.md                         # Claude Code 入口（指向 AGENTS.md）
```

---

## 配置说明

| 环境变量 | 说明 | 默认值 |
| --------- | ------ | -------- |
| `OPENAI_API_KEY` | DashScope API 密钥 | - |
| `OPENAI_API_BASE` | API 基础地址（DashScope 兼容端点） | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL_PRIMARY` | 默认主模型 | `qwen3.7-plus`（`llm.py:48` 代码默认） |
| `LLM_MODEL_FALLBACK` | 全局备用模型（额度/异常降级） | `deepseek-v4-flash`（`llm.py:49`） |
| `LLM_MODEL_ROUTER` / `_PLANNER` / `_RESEARCHER` / `_WRITER` / `_REVIEWER` / `_REFINER` | 逐节点模型路由（可选） | 未配置时回退 `LLM_MODEL_PRIMARY`（`llm.py:53-58`） |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | - |
| `LANGSMITH_API_KEY` | LangSmith 可观测性（可选） | - |

---

## 测试覆盖

```
299 passed, 4 warnings in ~47s（覆盖率 69.22%，2026-11-11 实测）

├── test_akshare_tools.py       # AKShare/同花顺工具层 + mock + 降级链
├── test_data_collector.py      # DataCollector 节点 + mock
├── test_chinese_report.py      # 中文报告格式 + 表格生成
├── test_router.py              # 意图路由
├── test_reviewer.py            # 质量审查 + cosine 早停
├── test_researcher.py          # RAG 检索 + 审计
├── test_search_agent.py        # Function Calling 节点
├── test_report_ingest.py       # 研报入库 + 检索
├── test_hithink_tools.py       # 同花顺 L0 客户端（fail-open）
├── test_api_routes.py          # API 端点
├── test_fault_injection.py     # 故障注入
└── integration/                # 集成测试
```

复现：`cd backend && .venv/bin/python -m pytest -q --cov=app --cov-fail-under=62`

---

## 评测（Benchmark）

> 详见 `docs/benchmark.md`

**评测方法**：20 只样本池（`backend/eval/benchmark_run.py`），其中 5 只已实测（600196/000001/600519/000333/601318，2026-08-24 / 2026-11-08 / v2.1 三轮），15 只待低峰时段分夜实测。**数字一律实测填入，不编造**，详见 `docs/benchmark.md`。

**LLM 裁判**（2026-11-11 起）：`eval/llm_judge.py` 以 5 维度 + 引文作证 + temp 0 对报告质量打分；对 600519 真实报告首评 7/10，抓到 3 条人工复核属实的缺陷（详见 `docs/interview/03-评测与可观测.md` 第 4 节）。

---

## 开发路线图

### ✅ 已完成（v1.0）

- [x] 基于 LangGraph StateGraph 的多智能体协同架构（+ Rerank 重排 / 长期记忆 Store）
- [x] Function Calling 改造（LLM 驱动工具调用 + ≤5 轮循环终止）
- [x] AKShare 真实 A 股数据接入（4 个工具 + 四层降级 + 60s 缓存）
- [x] 中文六章节投研报告格式（数据与观点分离）
- [x] 研报 PDF 入库 RAG（PyMuPDF + 实体抽取）
- [x] 个股新闻/公告聚合
- [x] 多模型 LLM 降级 + SSE 流式输出
- [x] ChromaDB RAG + 文档相关性审计
- [x] 会话记忆系统（增量摘要 + checkpoint）
- [x] LangSmith 全链路可观测性
- [x] 限流器 + 生产级 FastAPI 后端
- [x] Vue 3 前端（智能问答 + 投研分析 Tab）
- [x] Docker Compose 部署
- [x] 299 个测试，零回归（覆盖率 69.22%）
- [x] 图拓扑修复（researcher→search_agent 断链）
- [x] 节点状态事件（start/done + elapsed 真实进度）
- [x] search_iteration 循环终止（≤5 轮自动停止）
- [x] Router REFINE 误判收紧
- [x] 前端工程化（composables + vue-router + pinia + 侧边栏）
- [x] 功能引导页 + 真实进度时间线

### ✅ 已完成（v1.3 · 前端体验 + 生产部署）

- [x] 前端毛玻璃 UI 重构（backdrop-blur 半透明卡片 + 渐变光斑背景）
- [x] 聊天附件上传（PDF 自动分析）+ 多轮追问输入（FollowUpInput）
- [x] 行情走势 Sparkline + 自选股名称补全
- [x] 研究节点进度置顶（ProcessBar）
- [x] 设置页扩展：短期记忆摘要 + 长期记忆增删改 + 系统状态
- [x] 后端新增端点：`/api/stock/{code}/kline`、`/api/index/{code}/kline`、`/api/market/hot`、`/api/memory-items` 增删改查
- [x] 生产部署：裸机 venv + uvicorn 8081 + Nginx 反代，公网 https://iris-jie.duckdns.org

### 🚧 规划中（v1.2）

- [ ] 多股票对比分析
- [ ] 行业数据聚合
- [ ] 定时研报生成任务
- [ ] 报告导出（PDF / Word）
- [ ] 前端 Gradio 演示入口
### 🔮 远期规划（v2.0）

- [ ] MCP 协议集成（eastmoney MCP）
- [ ] 人工审核节点（HITL）
- [ ] 多用户权限管理

---

## 面试技术亮点

| 面试问题 | 回答要点 |
| --------- | --------- |
| 为什么选 LangGraph？ | 显式状态 + 条件路由 + Checkpoint，适合可审计的确定性流程 |
| 如何防死循环？ | MAX_REVISIONS(3) + cosine 相似度早停(0.95) |
| 如何防幻觉？ | 数据与观点分离 + 来源标注 + 诚实告知原则 |
| 如何降级？ | 四层数据源 + LLM 主备切换 + 工具级不抛异常 |
| Function Calling？ | `@tool` 声明 + `bind_tools` + 自定义 `ToolNode` + LLM 自主决策 |
| 多 Agent 架构？ | 15 节点协同（核心 Agent 链 + 支撑节点），每节点独立解耦，可单独测试替换 |
| 记忆系统？ | 双层：conversation_summary 增量摘要（会话内，checkpoint 持久化）+ 长期记忆 AsyncSqliteStore（跨会话） |
| 为什么长期记忆「只注入不路由」？ | 记忆影响"怎么答"不影响"走哪条边"——错误记忆误导路由会造成 refine/research 误判；注入只改变 prompt 上下文，风险可控且用户可删 |
| 为什么 watch_stock 用规则抽取而不是每轮 LLM？ | 省成本、行为可预期：严格正则识别股票代码零成本零幻觉；LLM 只兜底"记住我喜欢…"这类无结构化信号的显式请求 |
| 为什么 rerank 选 DashScope gte-rerank 而不是本地 CrossEncoder？ | 同供应商同 Key 零额外依赖；本地模型 +400MB 内存且 Windows/容器安装易翻车；API 失败 fail-open 降级纯向量序，可用性优先于精排收益 |
| rerank 怎么证明有效？ | score 契约用 `reranked` 字段区分语义（relevance_score vs Chroma distance），可观测可回归；20 query 手工标注小评测待补（诚实边界） |
| 研报 RAG？ | PyMuPDF(fitz) 抽取 + 正则实体抽取 + ChromaDB 按标的检索 + gte-rerank 精排 |
---

## 开源协议

MIT License

---

<p align="center">
  <sub>Built with ❤️ using LangGraph + DeepSeek + AKShare | IRIS v1.0</sub>
</p>

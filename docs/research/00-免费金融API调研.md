# Research: Investment Research Aggregation Project (LangGraph + FastAPI + Gradio)

> 调研日期: 2026-05-18  
> 项目目标: 构建 A 股投资研究聚合平台，使用 LangGraph 多智能体 + FastAPI 后端 + Gradio 前端

---

## 1. Free Financial APIs for A-share Stocks

### Summary

对于 A 股数据，**本土数据源全面胜出**——AKShare、BaoStock、Tushare Pro 覆盖 A 股且免费/低成本；国际 API（Alpha Vantage、Finnhub、Polygon.io）在免费层**不支持 A 股**或覆盖极弱。推荐以 AKShare 为主、BaoStock 为备、East Money MCP 为补充。

### Findings

#### 1.1 AKShare（首选）

- **开源 Python 库**，基于公开数据源（新浪财经、东方财富、巨潮资讯等），无需 API Key
- **A 股覆盖极全**：历史 K 线（日线/周线/月线/分钟线）、实时行情、财务数据（三大表+财务指标）、资金流向、龙虎榜、融资融券、公告、研报、行业分类
- **无调用次数限制**，但单次返回数据量有上限（如实时行情单次返回所有深 A 股/沪 A 股）
- **Python SDK**：`pip install akshare`，返回 pandas DataFrame，Python 3.11+
- **无需注册**，完全免费
- **注意**：数据来自公开网页抓取，接口可能随上游网站变化而调整；稳定性依赖上游源
- **GitHub**: <https://github.com/akfamily/akshare> (25k+ stars)
- **PyPI**: <https://pypi.org/project/akshare/>

#### 1.2 BaoStock（备选）

- **免费开源** A 股数据平台，无需注册、无需 API Key
- **覆盖**：历史 K 线（日/周/月/5分钟）、财务数据（三大表+财务指标）、宏观经济指标、行业分类
- **Python SDK**：`pip install baostock`，返回 pandas DataFrame
- **限制**：每次 session 需 `bs.login()`，数据有滞后（日线数据 T+1 更新）；不支持实时行情
- **优势**：数据由自有服务器提供，比网页抓取更稳定
- **官网**: <http://www.baostock.com/>
- **PyPI**: <https://pypi.org/project/baostock/>

#### 1.3 Tushare Pro（积分制）

- **积分门槛制**：注册新用户获 100 分，基础日线数据需 120 分（免费），财务数据需 2000-5000 分
- **A 股覆盖全**：行情、财务、参考数据、分钟数据、新闻舆情、公告
- **免费额度**：120 积分可调用非复权日线数据，50 次/分钟，8000 次/天
- **获取积分**：推荐注册(+50)、修改资料(+20)、贡献代码(+100~500)、发表文章(+100~1000)
- **Python SDK**：`pip install tushare`
- **注意**：高质量数据（分钟级、新闻、研报）需要高积分或付费（200 元/年起）
- **官网**: <https://tushare.pro/>

#### 1.4 东方财富 API（East Money）

- **公开延时接口**（push2delay.eastmoney.com），无需 API Key
- **MCP 服务器项目**：`mcp-eastmoney` 提供 5 个核心 Tool（实时行情、股票搜索、主力资金排名、板块资金流、历史 K 线）
- **覆盖**：全 A 股（沪深京），返回结构化中文字段
- **完全免费**，标准 MCP 协议，兼容 Claude/Cursor/Cline 等
- **GitHub**: <https://github.com/27dream/mcp-eastmoney>

#### 1.5 新浪财经 / 腾讯财经 API

- **公开接口**，无需 Key，可通过 `finshare` 等第三方库统一封装
- **覆盖**：港股实时报价、A 股行情（有限）
- **稳定性**：公开接口可能变更，建议通过多源库（如 finshare）使用
- **finshare 库**：<https://github.com/finvfamily/finshare> — 多源自动切换，统一格式

#### 1.6 Yahoo Finance（yfinance）

- **A 股覆盖差**：代码格式为 `600519.SS`（沪）/ `000001.SZ`（深），数据不完整
- **国内网络不稳定**：TradingAgents 项目已将 A 股数据源从 yfinance 切换到 akshare
- **免费无限制**，但 A 股数据质量和时效性不可靠
- **建议**：仅作美股/港股补充数据源，不用于 A 股主力
- **PyPI**: <https://pypi.org/project/yfinance/>

#### 1.7 Alpha Vantage

- **免费层**：25 请求/天（旧数据说 500/天，已收紧），5 次/分钟
- **A 股覆盖极弱**：主要覆盖美股和全球主要交易所，A 股基本不可用
- **Python SDK**：`pip install alpha-vantage`
- **建议**：不适合 A 股项目，仅作美股参考
- **官网**: <https://www.alphavantage.co/>

#### 1.8 Polygon.io（已更名为 Massive）

- **免费层**：5 次/分钟，2 年历史日线数据，仅美股
- **A 股不支持**：仅覆盖美股、美股期权、外汇、加密、全球指数
- **付费起步**：$199/月
- **建议**：不适合 A 股项目
- **官网**: <https://massive.com/pricing>

#### 1.9 Finnhub

- **免费层**：60 次/分钟，仅美股
- **A 股不支持**：免费账户仅限美股市场，国际股市需付费许可
- **Python SDK**：`pip install finnhub-python`
- **建议**：不适合 A 股项目
- **官网**: <https://finnhub.io/>

### API 对比总结

| API | A 股覆盖 | 免费额度 | 需要注册 | Python SDK | 推荐度 |
| ----- | --------- | --------- | --------- | ----------- | -------- |
| **AKShare** | ★★★★★ | 无限 | 否 | ✅ | ⭐⭐⭐⭐⭐ |
| **BaoStock** | ★★★★ | 无限 | 否 | ✅ | ⭐⭐⭐⭐ |
| **Tushare Pro** | ★★★★★ | 120 分免费 | 是 | ✅ | ⭐⭐⭐ |
| **East Money MCP** | ★★★★ | 无限 | 否 | ✅ | ⭐⭐⭐⭐ |
| **finshare** | ★★★★ | 无限 | 否 | ✅ | ⭐⭐⭐⭐ |
| **Yahoo Finance** | ★★ | 无限 | 否 | ✅ | ⭐⭐ |
| **Alpha Vantage** | ★ | 25/天 | 是 | ✅ | ⭐ |
| **Polygon.io** | ✗ | 5/分钟 | 是 | ✅ | ✗ |
| **Finnhub** | ✗ | 60/分钟 | 是 | ✅ | ✗ |

### 推荐策略

1. **主力数据源**：AKShare（覆盖最广、无需 Key、社区活跃）
2. **备用数据源**：BaoStock（自有服务器更稳定）+ finshare（多源自动切换）
3. **实时资金流**：East Money MCP（主力资金、板块资金）
4. **付费升级路径**：如需分钟级数据/新闻舆情 → Tushare Pro 积分或付费

---

## 2. Open-Source Investment Research Projects

### Summary

GitHub 上 AI 金融分析项目已形成完整生态：**TradingAgents**（~98k stars）是最热门的多智能体交易框架；**FinanceAgent-LangGraph** 展示了 LangGraph + FastAPI + React 的完整生产级架构；**stock-picker-agent** 则示范了 CrewAI + LangGraph 的混合模式。这些项目提供了可直接参考的架构模式和代码实现。

### Findings

#### 2.1 TradingAgents（TauricResearch）— 最热门

- **Stars**: ~98,272 | **License**: Apache 2.0
- **架构**: 多智能体交易框架，模拟真实投行团队
  - **分析师团队**：Fundamentals Analyst、Sentiment Analyst、News Analyst、Technical Analyst、Social Media Analyst
  - **研究员团队**：Bull Researcher + Bear Researcher（结构化辩论）
  - **交易员**：综合分析报告生成交易决策
  - **风险管理 + 投资组合经理**：风险评估、交易审批
- **技术栈**: LangGraph + LangChain + OpenAI/Gemini/Claude/Grok + yfinance + Alpha Vantage + Reddit + StockTwits + FRED
- **特点**:
  - 支持多 LLM 提供商（含 DeepSeek、Qwen、GLM 国产模型）
  - 有 CLI 和 Python API 两种使用方式
  - 支持 LangGraph checkpoint resume
  - 有 CI 测试套件
- **局限**: 数据源以美股为主，A 股需替换数据层
- **GitHub**: <https://github.com/TauricResearch/TradingAgents>

#### 2.2 FinanceAgent-LangGraph（aakarsh31）— 最贴合你的需求

- **架构**: 10 个专业 Agent 并行运行
  - DataFetchAgent → MacroRegimeAgent → [Fundamentals, Technical, Sentiment, Risk, OnChain] → [Bull, Bear, Valuation] → SupervisorAgent → trade_gate (HITL)
- **技术栈**: LangGraph (StateGraph, SqliteSaver) + GPT-4.1-nano (分析) + GPT-4.1-mini (Supervisor) + yfinance + CoinGecko + FRED + FastAPI + React + Vite
- **关键设计**:
  - 分层 LLM 策略：分析用 nano（快+便宜），Supervisor 用 mini（聪明）
  - 平均端到端延迟 17.6s，p50 成本 $0.0018/run
  - Human-in-the-loop 交易审批门
  - 资产类别自动检测（股票/加密货币）
  - LangSmith 可观测性
- **GitHub**: <https://github.com/aakarsh31/FinanceAgent-LangGraph>

#### 2.3 Stock Picker Agent（Crazy-Horse）— CrewAI + LangGraph 混合

- **架构**: CrewAI 负责 Agent 角色和工具使用，LangGraph 负责确定性工作流
  - News Scout → Retriever (RAG) → Fundamentals Analyst → Risk Analyst → Portfolio PM/Ranker
- **技术栈**: CrewAI + LangGraph + LangChain + Chroma/Pinecone + OpenAI/Anthropic/Gemini
- **特点**:
  - RAG 向量搜索实现有引用的分析
  - 投资风格筛选（value/growth/momentum/dividend）
  - 输出 markdown 报告 + 结构化 JSON
- **GitHub**: <https://github.com/Crazy-Horse/stock-picker-agent>

#### 2.4 AI Hedge Fund（harshshri07）

- **架构**: 5 个专业 Agent（Fundamentals, Sentiment, Technical, Risk, Portfolio）
- **技术栈**: LangGraph + LangChain + Google Gemini + FastAPI + Next.js
- **GitHub**: <https://github.com/harshshri07/ai-hedge-fund>

#### 2.5 LangAlpha（ginlix-ai）— 34,435 stars

- **特点**: Programmatic Tool Calling (PTC)——Agent 编写 Python 代码处理金融数据，而非将原始数据灌入 LLM 上下文，大幅减少 token 浪费
- **多层级金融数据提供商体系**
- **GitHub**: <https://github.com/ginlix-ai/langalpha>

#### 2.6 Financial Research Analyst Agent（gsaini）

- **架构**: 层级式多智能体，11 个专门 Agent + 20+ 分析工具 + RAG 知识管道
- **访问方式**: Streamlit Web App + REST API + CLI
- **GitHub**: <https://github.com/gsaini/financial-research-analyst-agent>

#### 2.7 其他值得关注的项目

| 项目 | Stars | 特点 | URL |
| ------ | ------- | ------ | ----- |
| anthropics/financial-services | 34,435 | Claude 金融参考 Agent，IB/PE/财富管理 | <https://github.com/anthropics/financial-services> |
| adam-eques/finsight-crew | - | CrewAI 金融研究，Provider-agnostic | <https://github.com/adam-eques/finsight-crew> |
| BullBearPK | - | 巴基斯坦股市，LangGraph+CrewAI+React | <https://github.com/noumanic/bullbearpk> |
| Crazy-Horse/multi-agent-research | - | LangGraph 确定性多 Agent 研究管道 | <https://github.com/Crazy-Horse/multi-agent-research> |
| Crazy-Horse/ai-deep-rag-agent-research | - | LangGraph + DeepAgents + Hybrid RAG，SEC 文件分析 | <https://github.com/crazy-horse/ai-deep-rag-agent-research> |

### 架构模式总结

从这些项目中可提取的**通用架构模式**：

1. **分层 LLM 策略**：快模型做数据提取/分析，强模型做综合决策
2. **并行 Agent 执行**：多个专业 Agent 同时运行，减少端到端延迟
3. **HITL 审批门**：关键决策（如交易执行）需人工确认
4. **RAG 引用**：分析结果需有文档引用/来源追溯
5. **资产类别路由**：根据输入自动检测资产类型，走不同分析路径

---

## 3. Resume Project Complexity vs Over-Engineering

### Summary

招聘者看重的是**工程判断力**而非堆砌技术。一个"恰到好处"的项目应当展示：你能做出合理的技术权衡、有清晰的文档、能讨论失败案例。多智能体架构在以下情况才被认可为"合理"：有明确的角色分工理由、每个 Agent 解决不同子问题、有对比实验证明比单 Agent 更好。

### Findings

#### 3.1 招聘者真正看重的

- **GitHub 项目不是教程克隆**：招聘者一眼能看出哪些是跟着教程做的（"chat with PDF"、"wrapper around chat API"、"fine-tune on public dataset"、"agent that browses" 是四大俗套）[Source](https://multigrid.ai/learn/ai-portfolio)
- **可验证的工程决策**：README 中的架构图、技术选型理由、失败案例讨论比 demo 链接更重要 [Source](https://www.samuelfaj.com/en/blog/ai-software-engineer-portfolio-what-to-prove/)
- **文档质量**：清晰的 technical writing（博客文章、README）是区分因素 [Source](https://www.linkedin.com/posts/pranay-mahendrakar-84bb3b197)
- **量化影响**：性能数据、成本分析、延迟指标——展示你能衡量和优化

#### 3.2 过度工程的代价

- **真实案例**：有候选人在设计简单通知系统时引入 Kafka、流处理引擎、多区域数据库复制——结果因此失去了 offer [Source](https://dev.to/emilywoodsnyc/i-over-engineered-the-system-design-and-it-cost-me-the-offer-1khk)
- **核心原则**："A project demonstrates judgement only where judgement was required. Following a tutorial removes precisely the decisions that would have shown yours."
- **信号 vs 噪音**：招聘者 30 秒内决定你的项目是否值得关注，大多数项目在这 30 秒内就输了 [Source](https://www.learnist.org/ai-portfolio-project-pitfalls-recruiters/)

#### 3.3 多智能体架构何时合理

**合理的情况**：

- 每个 Agent 有明确的角色分工且解决不同子问题
- 有对比实验（如多 Agent vs 单 Agent 的准确率/延迟/成本对比）
- 有 HITL 审批门或安全护栏
- 有可观测性（LangSmith 追踪、日志）
- 有失败案例讨论（什么情况下 Agent 会出错）

**过度工程的情况**：

- 仅为"看起来高级"而拆分 Agent
- 所有 Agent 用同一个 LLM 做类似的事
- 没有对比基线（如何证明比单 prompt 更好？）
- 没有错误处理或降级策略

#### 3.4 不同级别的项目期望

| 级别 | 期望 | 关键信号 |
| ------ | ------ | --------- |
| **初级** | 能完成原创工作 | 项目能跑、有文档、不是教程复制 |
| **中级** | 生产判断力 | 部署故事、监控证据、失败文档 |
| **高级** | 业务影响 | 用非技术语言描述影响、范围声明 |

[Source](https://mentorcruise.com/blog/career-roadmap-how-to-build-an-ai-portfolio-that-gets-you-hired/)

#### 3.5 对项目的具体建议

1. **展示工程权衡**：为什么选 LangGraph 而非纯 LangChain？为什么用 GPT-4.1-nano 而非全用 mini？
2. **有对比基线**：单 Agent vs 多 Agent 的延迟/成本/质量对比
3. **讨论失败**：Agent 在什么情况下会判断错误？如何降级？
4. **可观测性**：集成 LangSmith 或自建追踪
5. **不要堆砌**：如果 Gradio 够用就上 Gradio，不必为"看起来专业"换 Next.js

---

## 4. Gradio + Multi-Agent / LangGraph Integration

### Summary

Gradio 已原生支持多智能体 UI 开发：`gr.Chatbot` 支持可折叠的思考块/工具调用展示，有官方 LangGraph 模板项目，支持 SSE 流式输出。对于金融仪表盘，Gradio 的 `gr.DataFrame`、`gr.Plot` 和 `gr.ChatInterface` 足以覆盖大多数场景。

### Findings

#### 4.1 Gradio 原生 Agent UI 支持

- **`gr.Chatbot` metadata 功能**：每个消息可附带 `metadata={"title": "Thinking...", "log": "..."}`，在聊天消息旁显示可折叠的手风琴，完美展示 Agent 思考过程和工具调用 [Source](https://gradio.app/guides/agents-and-tool-usage)
- **`reasoning_tags` 参数**：支持保留 `<thinking>` 等非标准 HTML 标签
- **`gr.ChatInterface`**：原生支持显示中间思考和工具使用，返回 `gr.ChatMessage` 对象即可
- **官方示例**: `demo/chatbot_thoughts/run.py` — 模拟思考过程的完整实现

#### 4.2 LangGraph + Gradio 模板项目

- **brycepg/gradio-langgraph-template**:
  - 功能：历史记录、工具调用、流式输出、Tabs、持久化、后续问题按钮
  - 安装：`pip install uv` + `uv run app.py`
  - GitHub: <https://github.com/brycepg/gradio-langgraph-template>
- **ssgrummons/langgraph-gradio**:
  - 使用 Ollama 本地运行 LangGraph
  - 展示 LangGraph 与 Gradio 的 wiring
  - GitHub: <https://github.com/ssgrummons/langgraph-gradio>

#### 4.3 Gradio 流式输出（SSE）

- **架构**：Python 后端 → HTTP + SSE → JavaScript 前端
- **实现方式**：后端使用 `async generator`（yield 流式数据），Gradio 自动通过 SSE 推送到前端
- **已知问题**：`@gradio/client` submit iterator 在 `process_completed` 后可能不解析（GitHub issue #13402），需注意错误处理
- **PR #6069**：Gradio 已将 websockets 替换为 SSE，所有 demo 应能正常工作
- **DeepWiki 架构文档**: <https://deepwiki.com/gradio-app/gradio>

#### 4.4 Gradio 金融仪表盘

- **gr.DataFrame**：实时数据表格展示
- **gr.Plot**：matplotlib/plotly 图表
- **gr.ChatInterface**：对话式交互
- **BigQuery 实时仪表盘教程**：7 行 Python 代码创建实时更新仪表盘 [Source](https://gradio.app/guides/creating-a-dashboard-from-bigquery-data)
- **印度股票可视化器**：从 Streamlit 迁移到 Gradio 的完整案例 [Source](https://www.lionbloggertech.com/how-to-build-an-indian-stock-visualizer-using-gradio/)

#### 4.5 多智能体 Gradio 项目参考

- **Multi-Agent-LLM-Collaboration-Sandbox** (dakshjain-1616):
  - 定义 Agent 角色/模型/人格，实时观察协作
  - 基于 OpenRouter（200+ LLM）
  - 6 个预设场景 + 自定义配置
  - GitHub: <https://github.com/dakshjain-1616/-Multi-Agent-LLM-Collaboration-Sandbox>

#### 4.6 推荐实现方案

```
用户输入 (ticker/问题)
    ↓
Gradio ChatInterface (messages type)
    ↓
FastAPI endpoint (async generator)
    ↓
LangGraph StateGraph (多 Agent 编排)
    ↓
Agent 并行执行 → yield 中间状态
    ↓
Gradio Chatbot metadata 展示思考过程
    ↓
最终报告 (结构化 markdown)
```

**关键实现点**：

- 使用 `gr.Chatbot(type="messages")` + `metadata` 展示 Agent 思考
- 后端 `async generator` yield 流式更新
- 每个 Agent 完成时 yield 中间结果（思考块折叠展示）
- 最终输出结构化投资报告

---

## 5. Multi-Agent Financial Analysis Patterns

### Summary

多智能体金融分析已形成成熟模式：**CrewAI** 适合角色分工明确的团队协作，**AutoGen** 适合对话式渐进分析，**LangGraph** 适合需要精确控制流和状态管理的复杂工作流。最佳实践包括：分层 LLM 策略、HITL 审批门、RAG 引用、可观测性、以及对比实验证明多 Agent 优于单 Agent。

### Findings

#### 5.1 CrewAI 金融分析模式

- **官方示例**：`crewAI-examples/crews/stock_analysis` — 输入 ticker，多 Agent 协作生成完整股票分析和投资建议 [Source](https://github.com/crewAIInc/crewAI-examples/tree/main/crews/stock_analysis)
- **典型 Agent 角色**：
  - Financial Analyst Agent：数据收集和分析
  - Research Analyst Agent：深度研究
  - Investment Recommendation Agent：最终建议
- **特点**：角色驱动、工具使用、自然语言任务描述
- **优势**：上手快、社区示例多、适合模拟"分析师团队"
- **GitHub 项目**：
  - devjothish/Financial-Analyst-CrewAI — yfinance 实时数据
  - MukulGupta121190/CrewAi-Gemini-Stock-Analyser — Gemini + DuckDuckGo

#### 5.2 AutoGen 金融分析模式

- **官方示例**：Company Research — 顺序式 Agent 团队（Search Agent → Research Writer → Quality Reviewer）[Source](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/examples/company-research.html)
- **Gradio 集成项目**：
  - amitlals/Stock-Analysis-AutoGen-Multi-Agent-Azure-AI-Foundry — AutoGen + Gradio UI + Azure AI
  - shaadclt/Multi-Agent-Stock-Analysis — AutoGen + Groq LLaMA-3
- **特点**：对话式、渐进式、Agent 间自然语言交互
- **优势**：灵活、适合探索性分析
- **局限**：确定性不如 LangGraph，调试较难

#### 5.3 LangGraph 金融分析模式

- **AWS 官方博客**：LangGraph + Strands Agents + MCP 构建智能金融分析 Agent [Source](https://aws.amazon.com/blogs/machine-learning/build-an-intelligent-financial-analysis-agent-with-langgraph-and-strands-agents/)
  - LangGraph 处理动态分析工作流
  - Strands Agents 提供结构化推理
  - MCP 协议集成工具
- **Nous Ergon Crucible Research**：
  - 6 个行业团队 + CIO + 宏观经济学家
  - 滚动投资论点、S&P 900 扫描、复合信号评分
  - GitHub: <https://github.com/nousergon/crucible-research>
- **关键设计模式**：
  - StateGraph 定义明确的状态机
  - 条件路由（根据资产类别走不同路径）
  - Checkpoint 持久化和恢复
  - SqliteSaver/PostgresSaver 跨会话持久化

#### 5.4 Agentic AI 投资研究最佳实践（行业观点）

**来自 CFA Institute、Schroders、Amazon Bedrock、Amundi 的共识**：

1. **多 Agent 协作优于单 Agent**：
   - 单一 Agent 难以处理复杂的多步骤投资研究工作流
   - 专业化子 Agent 在特定任务上表现更好 [Source](https://aws.amazon.com/blogs/machine-learning/part-3-building-an-ai-powered-assistant-for-investment-research-with-multi-agent-collaboration-in-amazon-bedrock-and-amazon-bedrock-data-automation/)

2. **数据架构决定成败**：
   - "模型架构本身不再是决定性因素，底层数据架构才是" [Source](https://www.integrity-research.com/the-hidden-infrastructure-of-agentic-ai-why-data-architecture-determines-success-in-investment-research/)
   - 需要多源数据融合、数据验证、缓存策略

3. **人机协作**：
   - Schroders 的 multi-agent 系统让分析师专注于高价值判断 [Source](https://cloud.google.com/blog/topics/customers/how-schroders-built-its-multi-agent-financial-analysis-research-assistant)
   - AI 自动化常规数据收集和处理

4. **可观测性和审计**：
   - 每个 Agent 的决策需可追溯
   - 结构化输出 + 引用来源

5. **2025 趋势**：
   - Agentic AI 在投资领域从实验走向生产
   - YC 等 VC 对 Agentic AI 初创的投资大幅增加 [Source](https://rpc.cfainstitute.org/research/the-automation-ahead-content-series/agentic-ai-for-finance)

#### 5.5 推荐的多 Agent 架构（针对本项目）

```
┌─────────────────────────────────────────────┐
│                用户输入 (ticker)              │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│          Data Collection Agent               │
│    (AKShare + BaoStock + East Money MCP)     │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│           Parallel Analysis Agents           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │Fundament.│ │Technical │ │ Sentiment │    │
│  │ Analyst  │ │ Analyst  │ │ Analyst   │    │
│  └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────┐ ┌──────────┐                  │
│  │  Risk    │ │  Macro   │                  │
│  │ Analyst  │ │ Analyst  │                  │
│  └──────────┘ └──────────┘                  │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│          Supervisor Agent (强 LLM)           │
│      综合所有分析 → 结构化投资报告            │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│         HITL Gate (可选人工审批)             │
└─────────────────────────────────────────────┘
```

**Agent 分工原则**：

- 每个 Agent 有**明确、不重叠**的职责
- 分析型 Agent 用快模型（如 GPT-4.1-nano / Qwen / DeepSeek）
- 综合型 Agent 用强模型（如 GPT-4.1-mini / Claude）
- 所有输出为**结构化 Pydantic 模型**（非自由文本）
- 中间状态**可观测**（LangSmith 或自建日志）

---

## Sources

### Kept（保留来源）

| 来源 | URL | 保留原因 |
| ------ | ----- | --------- |
| AKShare GitHub | <https://github.com/akfamily/akshare> | 主力数据源，25k+ stars |
| BaoStock 官网 | <http://www.baostock.com/> | 免费 A 股数据备选 |
| Tushare Pro 文档 | <https://tushare.pro/document/2?doc_id=290> | 积分制 API 权威文档 |
| East Money MCP | <https://github.com/27dream/mcp-eastmoney> | 免费 A 股 MCP 服务器 |
| TradingAgents GitHub | <https://github.com/TauricResearch/TradingAgents> | 最热门多 Agent 金融框架 |
| FinanceAgent-LangGraph | <https://github.com/aakarsh31/FinanceAgent-LangGraph> | 最贴合需求的参考实现 |
| Stock Picker Agent | <https://github.com/Crazy-Horse/stock-picker-agent> | CrewAI+LangGraph 混合模式 |
| Finnhub 定价页 | <https://finnhub.io/pricing> | 确认免费层不支持 A 股 |
| Massive (Polygon) 定价 | <https://massive.com/pricing> | 确认免费层仅美股 |
| Gradio Agent UI 指南 | <https://gradio.app/guides/agents-and-tool-usage> | 官方 Agent UI 实现 |
| Gradio LangGraph 模板 | <https://github.com/brycepg/gradio-langgraph-template> | 官方集成模板 |
| CrewAI Stock Analysis | <https://github.com/crewAIInc/crewAI-examples/tree/main/crews/stock_analysis> | 官方金融分析示例 |
| AutoGen Company Research | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/examples/company-research.html> | 官方多 Agent 研究示例 |
| AWS LangGraph 金融博客 | <https://aws.amazon.com/blogs/machine-learning/build-an-intelligent-financial-analysis-agent-with-langgraph-and-strands-agents/> | 官方架构模式 |
| CFA Institute Agentic AI | <https://rpc.cfainstitute.org/research/the-automation-ahead-content-series/agentic-ai-for-finance> | 行业权威观点 |
| Schroders Multi-Agent | <https://cloud.google.com/blog/topics/customers/how-schroders-built-its-multi-agent-financial-analysis-research-assistant> | 真实生产案例 |
| AI Portfolio 招聘视角 | <https://www.learnist.org/ai-portfolio-project-pitfalls-recruiters/> | 招聘者视角 |
| Over-Engineering 教训 | <https://dev.to/emilywoodsnyc/i-over-engineered-the-system-design-and-it-cost-me-the-offer-1khk> | 真实面试教训 |
| 100K AI Portfolio | <https://zenvanriel.nl/ai-engineer-blog/100k-ai-engineering-portfolio-projects/> | 成功案例分析 |

### Dropped（排除来源）

| 来源 | 排除原因 |
| ------ | --------- |
| Alpha Vantage vs Polygon 对比 (TradingDataCompare) | SEO 聚合站，数据可能过时 |
| cn-a-stock-data (PyPI) | 新项目，社区验证不足 |
| finshare 文档 | 与 AKShare 功能重叠，优先推荐 AKShare |
| 印度股票可视化器教程 | 与 A 股场景关联弱 |
| Crypto Portfolio Tracker | 加密货币场景，非本项目重点 |
| 部分 LinkedIn 招聘观点 | 泛泛而谈，缺乏具体指导 |

---

## Gaps

1. **AKShare 在高频调用下的稳定性**：公开文档未明确说明并发限制，实际生产需自行测试和添加重试/缓存
2. **A 股研报/公告数据质量**：AKShare 有研报接口但覆盖率和时效性需验证
3. **Gradio 大规模部署性能**：Gradio 默认单线程，生产部署需考虑 `queue()` + 多 worker
4. **国产 LLM（Qwen/DeepSeek/GLM）在金融分析上的表现对比**：缺乏权威 benchmark
5. **A 股多 Agent 系统的延迟基准**：现有项目多为美股，A 股数据获取延迟可能不同

### 建议下一步

1. **搭建数据层原型**：用 AKShare + BaoStock 获取 A 股数据，测试稳定性和延迟
2. **实现最小可行 Agent**：先做 1 个 Agent（如 Fundamentals Analyst），验证 LangGraph + Gradio 流式输出
3. **逐步扩展 Agent**：在单 Agent 基础上添加 Technical、Sentiment 等 Agent，每加一个都做对比实验
4. **集成 LangSmith**：从第一天就加入可观测性，展示工程成熟度
5. **写博客/文档**：记录架构决策和失败案例，这本身就是加分项

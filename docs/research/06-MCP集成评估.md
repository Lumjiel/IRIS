# Research: 简历项目集成 MCP（以 mcp-eastmoney 为例）是否值得 + 怎么做最有效

## Summary

MCP 已经进入真实面试循环：不止一家求职社区和招聘分析确认"简历里写 MCP 会被面试官顺着深挖"，而且从 2025Q4 到 2026 年中，MCP 特定岗位从近乎为零涨到 agentic 工程岗位的约 4%，"在 GitHub 发布 2-3 个 MCP server"被明确列为 MCP 工程师方向最有说服力的作品集动作。但对投研方向简历项目来说，**接不接不是关键，能不能讲清工程决策才是关键**——多位面试官视角的内容指出 MCP 关键词已从"亮点"变成"入场券"，只接线不深挖会被当成堆砌。

结论：**值得接，且有明确的最优做法**——用 LangGraph agent 承载投研主链路（数据→分析→报告），数据层通过 `langchain-mcp-adapters` 的 `MultiServerMCPClient`（stdio transport）接 mcp-eastmoney（或用数据面更全的 akshare-one-mcp），同时把同一个 server 配进 Claude Desktop 演示"一 server 多客户端"。这样做比直接调 akshare/东财 HTTP 接口多了一层协议知识展示面，正好是投研（domain）+ AI 工程（protocol）双卖点；代价是 ~15 分钟延时、非官方接口稳定性、以及"单一 agent 固定小工具集时 MCP 属多余抽象"的过度设计风险。

---

## Findings

### 一、真实案例：MCP 写进简历/作品集确实是加分点，但有分层

1. **岗位数据：MCP 工程师已成为真实职业，作品集动作明确。** AgenticCareers 统计：MCP 特定岗位从 2025Q4 近于零增长到 2026 年中约占其追踪的 agentic 工程岗位的 4%；IC3 总包 $180K–240K、IC5 $330K–450K。且明确写道："The portfolio-credibility move for this role is unambiguous: publish two or three MCP servers on GitHub that expose something non-trivial… with clean typed schemas, good tool descriptions, and a short README that shows you understand the failure modes. A working server beats a certification every time."——**即"GitHub 上 2-3 个非玩具 MCP server + 能讲失败模式"是官方背书级的加分动作**。[Source](https://agenticcareers.co/blog/what-is-mcp-engineer)

2. **简历写 MCP 会被面试官主动深挖（真实面试对话）。**
   - 腾讯云开发者社区面试向文章标题即"面试官：你项目里接了 MCP，对吧？"，列举实际追问：MCP vs Function Calling 有什么区别、为什么不用自己写工具注册中心、上生产后权限/稳定性/调试/版本兼容怎么处理。[Source](https://cloud.tencent.com/developer/article/2664521)
   - 掘金实录：实习生面试后反问"就面个实习至于这么高强度吗"，面试官答"你对 RAG、Agent、MCP、Skill 理解得很到位，所以要求高一点"，其中 MCP 作为独立问题单列。[Source](https://juejin.cn/post/7653108100300242987)
   - 牛客 27 届 Agent 方向简历模板把"协议理解加分：对 MCP 等协议的理解比单纯会用某个框架更有含金量"列为该方向简历的特殊性之一，并把"MCP 协议"放进第二梯队强推技能。[Source](https://www.nowcoder.com/discuss/912309942026002432?sourceSSR=post)
   - DataCamp 面试题库亦确认："Now it shows up in interviews for AI engineering, developer relations, and backend roles."（MCP 出现在 AI 工程/开发者关系/后端岗位面试中）[Source](https://www.datacamp.com/blog/mcp-interview-questions)

3. **反面证据（关键警示）：MCP 关键词已从"亮点"变"入场券"，只列名词=减分。**
   - 一位筛简历的面试官复盘："Agent/LangGraph/MCP/多智能体这些词，从少数人的亮点，变成了几乎人人都在写的标配……两年前是亮点，现在只是入场券。" 追问集中在"为什么"和决策细节。[Source](https://www.nowcoder.com/discuss/903739745971302400)
   - 招聘视角文章直指 6 类 resume padding 信号，第一条就是"只列 OpenAI/LangChain/MCP 等关键词、讲不出业务影响"；Signal #3 是"描述工具而不是工程决策"。反推：**简历里出现 MCP 的前提是能答出 why this architecture / 被否掉的备选 / 评测方式**。[Source](https://www.uplers.com/article/signals-ai-engineer-isnt-ai-native-resume-padding/)

4. **第一手作品集案例：有人真把 MCP server 做成求职材料。**
   - ayush-s-tomar 把自己的 9 个项目封装成 FastMCP stdio server，5 个工具（list_projects / get_project_details / search_projects_by_stack / get_flagship_project / get_resume_summary），对 Claude Desktop 直接可聊，工具调用弹出权限弹窗就是"活证据"；文中记录了 4 个真实踩坑（MCP Inspector 默认 uv、Windows Store 版 Claude 配置路径不同、配错配置文件、模型有时不主动调工具需在 prompt 点名）。[Source](https://dev.to/ayushsinghtomar/i-got-tired-of-my-portfolio-looking-like-a-list-of-links-so-i-built-an-mcp-server-for-it-440o) [Repo](https://github.com/ayush-s-tomar/portfolio-mcp-server)
   - 另一开发者把"简历 MCP server"发布到 npm，宣称任何人可让 AI 直接查他的项目/技能。[Source](https://dev.to/akincskn/i-published-my-own-mcp-server-on-npm-heres-why-every-developer-should-1ek5)

### 二、mcp-eastmoney 实际用法与 LangGraph 集成

5. **mcp-eastmoney 是什么、怎么跑。** 27dream/mcp-eastmoney：基于东方财富公开**延时**接口（push2delay.eastmoney.com，约 15 分钟延迟）的 A 股 MCP server，免费、免 API Key、Python 3.10+、MIT。[Source](https://github.com/27dream/mcp-eastmoney)
   - 暴露 **5 个工具**：`get_stock_quote`（实时行情：价格/涨跌/成交量/PE/换手率）、`search_stock`（关键词/拼音/代码搜股）、`main_fund_rank`（主力资金净流入排名，大中小单拆解）、`sector_fund_flow`（行业/概念板块资金流+领涨股）、`get_kline`（日/周/月线，前复权）。
   - 本地跑起来（Windows PowerShell 装 uv）：`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`，然后 `uvx mcp-eastmoney` 一键运行；pip 方式 `pip install mcp-eastmoney` + `mcp-eastmoney`。本地开发版：`"command": "python", "args": ["-m", "mcp_eastmoney"], "cwd": "/path/to/mcp-eastmoney"`。
   - 接 Claude Desktop（Windows）：`%APPDATA%\Claude\claude_desktop_config.json` 加 `{"mcpServers": {"eastmoney": {"command": "uvx", "args": ["mcp-eastmoney"]}}}`，重启后在工具面板看到 5 个工具；FAQs 含 `uvx --version` 校验、日志路径 `~/Library/Logs/Claude/mcp-server-eastmoney.log`、绝对路径替代 command、"Connection closed"（东财接口抽风）处理。[Source](https://github.com/27dream/mcp-eastmoney/blob/main/examples/CLAUDE_DESKTOP.md)
   - **投研注意**：README 路线图明确"财务报表数据 / 龙虎榜 / 北向资金"尚未实现——基本面分析类投研项目，仅 eastmoney 5 个工具不够；数据面更全的中文金融 MCP 备选：zwldarren/akshare-one-mcp（历史行情/实时/新闻/财务报表，双模式 stdio+HTTP）[Source](https://github.com/zwldarren/akshare-one-mcp)、shazhuya/china-stock-mcp（含技术指标、缓存、Docker）[Source](https://github.com/shazhuya/china-stock-mcp)。

6. **LangGraph 里调 MCP 的标准姿势：langchain-mcp-adapters。** 官方库 langchain-ai/langchain-mcp-adapters（LangChain 官方出品）把 MCP 工具转成 LangChain/LangGraph 可用的工具。[Source](https://github.com/langchain-ai/langchain-mcp-adapters)

   ```bash
   pip install langchain-mcp-adapters langgraph "langchain[openai]"
   ```

   ```python
   from langchain_mcp_adapters.client import MultiServerMCPClient
   from langchain.agents import create_agent        # 或 langgraph.prebuilt.create_react_agent

   client = MultiServerMCPClient({
       "eastmoney": {
           "command": "uvx",
           "args": ["mcp-eastmoney"],
           "transport": "stdio",
       }
   })
   tools = await client.get_tools()                  # 运行时自动发现工具 schema
   agent = create_agent("openai:gpt-4.1", tools)
   resp = await agent.ainvoke({"messages": "分析贵州茅台最近 60 天 K 线趋势，给出资金面结论"})
   ```

   - 多 server/混合 transport：同例可加 `{"weather": {"url": "http://localhost:8000/mcp", "transport": "http"}}`；与 LangGraph 自定义图（StateGraph + ToolNode + tools_condition）配合的官方示例见 Azure-Samples 的 `examples/langgraph_mcp.py`。[Source](https://github.com/Azure-Samples/python-ai-agent-frameworks-demos/blob/main/examples/langgraph_mcp.py)
   - 需要注意的语义：`MultiServerMCPClient` 默认**无状态**——每次工具调用新建 `ClientSession`；工具执行错误（isError=True）默认以 `ToolMessage(status="error")` 回给模型让其自纠，而不是崩掉 run（`handle_tool_errors=False` 可改回抛异常）；协议/传输层失败始终抛异常。[Source](https://docs.langchain.com/oss/python/langchain/mcp) [Reference](https://reference.langchain.com/python/langchain-mcp-adapters/client/MultiServerMCPClient)
   - 官方 LangChain 真实项目参考：langchain-ai/deep_research_from_scratch 的 `research_agent_mcp.py` 即用 MultiServerMCPClient + StateGraph 做研究 agent——与"投研 agent"结构同构，可直接当模板。[Source](https://github.com/langchain-ai/deep_research_from_scratch/blob/main/src/deep_research_from_scratch/research_agent_mcp.py)

### 三、评估：投研简历项目 接 vs 不接 MCP(eastmoney)

7. **接 MCP 的增量价值（有依据）**：
   - 面试面：MCP 已成为高频追问点（见 Finding 2），"配置过一次 MCP"就能答两层，但"能讲清 client/server 边界、什么时候直接调 API 更简单"层级的候选人明显更少——这正是作品级 MCP 集成的差异化位置。[Source](https://interviewaibox.co/zh/blog/mcp-interview-questions-guide-2026)
   - 岗位面：投研/量化/AI 应用方向，MCP 工程能力明确对应 2026 年的真实岗位类别与薪酬段（Finding 1）。
   - 技术面：同一数据层同时被 Claude Desktop 和 LangGraph agent 消费，体现"协议而非硬编码工具列表"的架构认知；运行时 schema 发现、换数据服务商不改 client 代码，是可直接写进简历 bullet、"为什么不用直接 function calling"的可答点。
8. **接 MCP 的代价与风险（同样有依据）**：
   - 数据质量硬伤：eastmoney 免费接口 ~15 分钟延时 + 非官方（"偶尔抽风"、README 自述数据仅供研究）；严谨投研结论存在数据时效性风险。若项目主打基本面/财务分析，mcp-eastmoney 5 个工具不够，需换 akshare-one-mcp 等（Finding 5）。
   - 过度设计风险：单一 agent、固定小工具集场景下 MCP 是多余抽象——"MCP 在多客户端消费、运行时发现、可替换实现时才值回开销"。投研主链路若只是"一个 LangGraph agent 内嵌几个函数"，直连 akshare 更简单。[Source](https://www.compoundlearn.ai/topics/mcp-model-context-protocol)
   - 简历风险：只"接线"= tutoring 克隆信号（Finding 3），面试官顺着"为什么 MCP""错误怎么处理""怎么评测"往下问，答不上来是负分。
9. **结论（可落地的平衡点）**：**接，但把 MCP 定位为"数据接入层 + 协议展示层"，而不是项目卖点本身**。
   - 主链路：LangGraph agent 做"数据获取 → 资金面/技术面分析 → 研究报告"；数据层经 mcp-eastmoney（行情/资金流/K线）或 akshare-one-mcp（如需财报/新闻）。
   - 配套动作（决定加分与否的三个工程决策，务必提前写好答案）：① 为什么选 MCP 而不是把东财接口函数直接写进 agent（答：多客户端复用 + 运行时工具发现 + 可替换数据源）；② 错误处理与重试策略（答：ToolMessage 错误回流让模型自纠、eastmoney 接口熔断/退避）；③ 评测方式（答：给定 >100 条投研问题的工具调用正确率/回答准确率评测集）。
   - 演示面：同一个 server 配进 Claude Desktop，"让招聘方现场用自然语言查行情/资金流"是可录屏的差异化 demo（参考 Finding 4 的 portfolio MCP server 模式）。

---

## Sources

**Kept：**
- AgenticCareers "What Is an MCP Engineer?"（https://agenticcareers.co/blog/what-is-mcp-engineer）— MCP 岗位占比、薪酬、作品集动作的一手行业数据（博客级，方向性可信）。
- langchain-ai/langchain-mcp-adapters（https://github.com/langchain-ai/langchain-mcp-adapters）— LangChain 官方集成库，含完整 stdio/http 示例代码。**权威实现依据。**
- LangChain MCP 官方文档（https://docs.langchain.com/oss/python/langchain/mcp）— MultiServerMCPClient 无状态语义、错误处理默认值。**权威。**
- 27dream/mcp-eastmoney（https://github.com/27dream/mcp-eastmoney）+ examples/CLAUDE_DESKTOP.md — 5 工具清单、Windows 配置路径、FAQs、数据延迟声明。**一手来源。**
- Azure-Samples python-ai-agent-frameworks-demos langgraph_mcp.py — LangGraph StateGraph + MCP 官方示例。**权威。**
- langchain-ai/deep_research_from_scratch research_agent_mcp.py — 与研究 agent 同构的官方实战代码。
- 腾讯云开发者社区"面试官：你项目里接了 MCP，对吧？"（https://cloud.tencent.com/developer/article/2664521）— 真实追问列表。
- 掘金 7653108100300242987 — 面试官原话："你对 RAG、Agent、MCP、Skill 理解得很到位"。
- 牛客 912309942026002432（Agent 简历模板）— "协议理解加分"原话；牛客 903739745971302400 — "MCP 已从亮点变入场券"的反面警示。
- Uplers "6 Signals an AI Engineer Isn't AI-Native"（https://www.uplers.com/article/signals-ai-engineer-isnt-ai-native-resume-padding/）— MCP 关键词 padding 信号与正确写法的对照。
- dev.to ayushsinghtomar portfolio-mcp-server 文章 — "作品集做成 MCP server"的第一手案例 + 4 个真实踩坑。
- DataCamp MCP 面试题综述（https://www.datacamp.com/blog/mcp-interview-questions）— MCP 出现在 AI 工程/后端/开发者关系岗位面试的独立佐证。
- CompoundLearn MCP 架构案例课（https://www.compoundlearn.ai/topics/mcp-model-context-protocol）— "何时 MCP 值回开销"的成本对照。
- zwldarren/akshare-one-mcp（https://github.com/zwldarren/akshare-one-mcp）— 数据面更全（含财报/新闻）的中文金融 MCP 备选。

**Dropped：**
- weste.net "你用 MCP 当普通 API 调？"（https://www.weste.net/2026/06-10/mcp-tool-call.html）— 疑似 SEO 生成、叙事不可验证，仅当轶事佐证，未采信。
- TechMeetups Raleigh MCP 薪酬文 — 单一地区、无原始数据，仅方向性且与我结论不冲突，未引用。
- Interview AiBox MCP 指南 — 泛泛内容，仅采其中"连过本地 server vs 讲清边界"的观点（已在 Finding 7 标注）。
- resumeportfolio.in "Day 10" — 教程性内容，无增量证据。
- jsonresume/mcp、mr-martinsosa/resume-tailor-mcp 等简历工具类 MCP — 与"把 MCP 写进简历"主题无关，已排除。

## Gaps

- **无对照实验数据**：找不到"同一份简历+项目，接 MCP vs 不接 → 面试/offer 差异"的一手统计；现有证据全部是"面试会问 / 岗位存在 / 社区共识"，属于强方向性而非定量因果。
- **eastmoney 免费接口可靠性无长期观测**：15 分钟延时与偶发不可用是 README 自述，实际稳定性需本地压测确认。
- **薪酬数字（$180K–450K）为博客口径**，无一手 JD 数据库可核验，仅用于说明"岗位类别真实存在"。
- 建议下一步：若决定接，先做 10 行级冒烟测试（uvx mcp-eastmoney 起服务 → get_stock_quote 调通），再决定数据源最终选型（eastmoney vs akshare-one-mcp）。
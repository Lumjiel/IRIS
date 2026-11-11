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
│   ├── tests/                       # 127 个测试（全量通过）
│   ├── conftest.py                  # Mock 外部依赖 + sample_state fixture
│   ├── pytest.ini                   # asyncio_mode = auto
│   ├── requirements.txt             # 依赖清单（含 akshare）
│   └── DEPLOY.md                    # 部署指南
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── ChatView.vue          # 聊天页（功能引导 + 消息流 + 侧边栏 + 附件上传）
│   │   │   ├── MarketView.vue        # 行情页（指数卡 + 自选股 + Sparkline 走势）
│   │   │   ├── SettingsView.vue      # 设置页（API/搜索模式/短期记忆/长期记忆增删改/系统状态）
│   │   │   └── HistoryView.vue       # 历史记录页（真实会话加载）
│   │   ├── components/
│   │   │   ├── chat/                 # ChatHeader / EmptyState / MessageBubble / ChatInput（附件）
│   │   │   ├── ChatSidebar.vue        # 侧边栏（自选股名称补全/会话历史/系统状态）
│   │   │   ├── ReportViewer.vue       # 报告渲染（TOC + ScrollSpy + 节流）
│   │   │   ├── ResearchTimeline.vue   # 研究进程时间线（节点进度置顶）
│   │   │   ├── MarketDataCard.vue     # 实时行情卡
│   │   │   ├── FinancialCard.vue      # 财务指标卡
│   │   │   ├── Sparkline.vue          # K 线/走势迷你图
│   │   │   ├── ProcessBar.vue         # 研究进度条（消息顶部）
│   │   │   ├── NewsTicker.vue         # 滚动资讯条
│   │   │   ├── FollowUpInput.vue       # 多轮追问输入
│   │   │   ├── TermTip.vue            # 术语提示
│   │   │   ├── ActionBar.vue          # 操作栏（复制/下载/保存）
│   │   │   └── Toast.vue              # 全局提示
│   │   ├── composables/
│   │   │   ├── useChat.js             # 聊天状态 + SSE 解析
│   │   │   ├── useToast.js            # Toast 全局提示
│   │   │   ├── useWatchlist.js        # 自选股管理
│   │   │   └── useThrottledRender.js  # 节流渲染 + 批量累积
│   │   ├── router/
│   │   │   └── index.js               # vue-router 配置（懒加载）
│   │   ├── stores/
│   │   │   └── app.js                 # pinia 全局 store（深色/偏好/会话）
│   │   ├── services/
│   │   │   ├── api.js                 # API 客户端
│   │   │   ├── finance.js             # 投研分析 API 服务（含 K线/指数/热门/行情）
│   │   │   ├── history.js             # 历史记录管理（tombstone 删除）
│   │   │   └── config.js             # 统一 API base 解析（env > 设置 > 同源）
│   │   ├── App.vue                    # 路由壳
│   │   ├── style.css                  # 毛玻璃全局样式
│   │   └── main.js                    # 入口（router + pinia 初始化）
│   └── package.json
├── docs/research/                   # 调研报告（6 份）
├── REFACTOR_PLAN.md                 # 分阶段重构计划（含面试验证）
├── AGENTS.md                        # 项目指南
├── PROJECT_BRIEFING.md              # 本文件
└── CLAUDE.md                        # Claude Code 配置
```

---

## 核心架构

### 九节点状态机 + Function Calling（含长期记忆注入）

> `router` 为条件入口（`set_conditional_entry_point`，非图节点）；`load_memories` 为长期记忆注入节点（仅注入 prompt 上下文，不参与路由决策）。

```
router (conditional entry)
  └── NEW_TOPIC → load_memories → planner → researcher → search_agent ⇄ search_tools → route_after_tools → data_collector → writer → reviewer
                                                                                                        │ FAIL → planner (循环，≤5 次)
                                                                                                        └ REFINE → refiner → END
```

| 节点 | 职责 | 关键技术 |
| ------ | ------ | --------- |
| 🧠 Router | 意图识别：新话题 / 修改报告 | LLM 分类 + 关键词兜底（收紧闲聊误判） |
| 📋 Planner | 搜索规划：生成 3-5 个子方向 | 对话上下文 + 搜索方向去重 |
| 🔍 Researcher | 本地文档检索 + 文档审计 | ChromaDB RAG + Grader |
| 🤖 SearchAgent | LLM 驱动的网络搜索 | Function Calling: `@tool` + `bind_tools`（≤5 轮自动终止） |
| 🔧 SearchTools | 执行 LLM 决定的工具调用 | 自定义 ToolNode |
| 📊 DataCollector | 金融数据拉取：AKShare 并行调用 | ThreadPoolExecutor 扇出 + 三层降级 + 60s 缓存 |
| ✍️ Writer | 中文研报撰写：六章节格式 | 数据与观点分离 + 来源标注 |
| 🔍 Reviewer | 质量审查：PASS/FAIL + 修复循环 | JSON 输出 + cosine 相似度早停 |
| 🔧 Refiner | 多轮修改：模糊追加 / 明确重写 | 双模式修订策略 |

### 节点状态事件（v1.1 新增）

每个 traced 节点发射 `start`/`done` + 真实 elapsed 时间 → 前端时间线实时进度：
- `emit_node_event()` 写入 ContextVar 队列 → routes.py 合并到 SSE 流
- 前端 `ResearchTimeline` 消费真实 status/elapsed，不再假动画
- 格式：`planner:done 5.21s`、`search_tools:done 23.44s`
### AKShare 数据层

- **4 个工具**：`query_stock_info`, `query_financial_indicators`, `query_stock_quote`, `query_stock_news`
- **四层降级**：同花顺官方 API（L0）→ 东方财富 → 雪球/新浪 → 内置模拟数据（服务器东财被封，实际走同花顺 L0 单链）
- **60s 缓存**：`stock_zh_a_spot_em` 全市场数据 TTL 缓存（消灭 30s 全量拉取）
- **永不抛异常**：工具级故障隔离
- **来源标注**：所有数值标注 `[来源: AKShare 东方财富]`

### Function Calling 架构

- **`@tool` 声明**：`search_web` 使用 LangChain `@tool` 装饰器
- **LLM 自主决策**：通过 `bind_tools([search_web])` 绑定工具，LLM 决定何时调用
- **自定义 ToolNode**：`search_tool_node` 执行工具调用（避免 `langgraph.prebuilt` 版本兼容问题）
- **消息累加**：`add_messages` reducer 自动累加到 `state["messages"]`
- **循环终止**：`search_iteration` 计数 + 上限 5 轮（防 LLM 无限循环）

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

### ✅ 已完成（v1.0 — 核心引擎）

- [x] 基于 LangGraph StateGraph 的九节点多智能体协同架构（含 load_memories 长期记忆注入）
- [x] AKShare 真实 A 股数据接入（四层降级：同花顺 L0 → 东财 → 雪球/新浪 → Mock）
- [x] 中文六章节投研报告格式（数据与观点分离 + 来源标注）
- [x] Function Calling 改造（LLM 驱动工具调用 + ≤5 轮循环终止）
- [x] 多模型 LLM 降级 + SSE 流式输出
- [x] ChromaDB RAG + 文档相关性审计 + 研报 PDF 入库
- [x] 会话记忆系统（增量摘要 + checkpoint）+ 长期记忆 Store
- [x] LangSmith 全链路可观测性 + 限流器 + 生产级 FastAPI 后端
- [x] Vue 3 前端（智能问答 + 投研分析 + 行情 + 设置 + 历史）
- [x] 127 个测试，零回归

### ✅ 已完成（v1.1 — 稳定性与工程化）

- [x] 图拓扑修复（researcher→search_agent 断链）
- [x] search_iteration 循环终止（≤5 轮自动停止）
- [x] 节点状态事件（start/done + elapsed 真实进度）
- [x] AKShare 全市场数据 60s 缓存
- [x] Router REFINE 误判收紧
- [x] 前端工程化（composables + vue-router + pinia）+ 侧边栏 + 功能引导页 + 真实进度时间线

### ✅ 已完成（v1.3 — 前端体验 + 生产部署）

- [x] 前端毛玻璃 UI 重构（backdrop-blur 半透明卡片 + 渐变光斑背景）
- [x] 聊天附件上传（PDF 自动分析）+ 多轮追问输入
- [x] 行情走势 Sparkline + 自选股名称补全 + 研究节点进度置顶
- [x] 设置页扩展：短期记忆摘要 + 长期记忆增删改 + 系统状态
- [x] 后端新增端点：K 线 / 指数 K 线 / 市场热门 / 记忆 CRUD
- [x] 生产部署：裸机 venv + uvicorn 8081 + Nginx 反代，公网 https://iris-jie.duckdns.org

### 🚧 规划中（v1.2）

- [ ] 多股票对比分析
- [ ] 行业数据聚合
- [ ] 定时研报生成任务
- [ ] 报告导出（PDF / Word）
- [ ] 前端 Gradio 演示入口

### 🔮 远期规划（v2.0）

- [ ] MCP 协议集成（eastmoney MCP 数据接入层）
- [ ] 人工审核节点（HITL）
- [ ] 多用户权限管理

---

## 面试技术亮点

| 面试问题 | 回答要点 |
| --------- | --------- |
| 为什么选 LangGraph？ | 显式状态 + 条件路由 + Checkpoint，适合可审计的确定性流程 |
| 如何防死循环？ | MAX_REVISIONS(5) + cosine 相似度早停(0.95) + search_iteration 上限(5 轮) |
| 如何防幻觉？ | 数据与观点分离 + 来源标注 + 诚实告知原则 |
| 如何降级？ | 三层数据源 + LLM 主备切换 + 工具级不抛异常 + AKShare 60s 缓存 |
| 多 Agent 架构？ | 10 节点协同（含 Function Calling 循环），每节点独立解耦，可单独测试替换 |
| Function Calling？ | `@tool` 声明 + `bind_tools` + `ToolNode` + search_iteration 循环终止 |
| 节点状态事件？ | `emit_node_event()` ContextVar 队列 → SSE 流 → 前端时间线真实进度 |
| 记忆系统？ | conversation_summary 增量摘要 + checkpoint 跨会话持久化 |

---

## 部署

生产环境已在 `49.234.178.53`（OpenCloudOS 9）以**裸机**方式部署（非 Docker Compose）：

- 代码目录：`/var/www/IRIS`，升级时 `git fetch origin && git reset --hard origin/main`
- 后端：`backend/venv` 虚拟环境，`uvicorn main:app --host 0.0.0.0 --port 8081 --workers 1`
- 前端：`frontend/dist` 由已有 Nginx 容器托管，构建命令 `npm install && npm run build`
- 反代：Nginx 容器将 `/api` 反代到宿主机网桥 `172.17.0.1:8081`
- 公网域名：`https://iris-jie.duckdns.org`
- 已知常态：服务器东财接口被封，AKShare 走同花顺 L0 单链，`/api/status` 的 `data_online` 为 false，属正常非故障
- 详细步骤见 `backend/DEPLOY.md`

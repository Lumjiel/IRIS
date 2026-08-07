# IRIS — Intelligent Research Insight System

> 通用深度调研引擎 · 基于 LangGraph 状态机的多 Agent 协作系统

---

## 一、项目定位

### 核心理念

IRIS 是一个**通用深度调研引擎**，不是一个单一功能的工具。它的设计哲学是：

> **任何需要"多源信息采集 → 交叉验证 → 结构化输出"的场景，都应该能通过配置快速适配，而不是重写一套系统。**

### 典型场景

| 场景 | 说明 | 预设 Skill |
|------|------|-----------|
| 公众号内容创作 | 选题调研、素材搜集、竞品文章分析 | `content_research` |
| 技术选型评估 | 框架对比、社区健康度、性能基准 | `tech_evaluation` |
| 行业研究 | 市场规模、竞争格局、趋势研判 | `industry_analysis` |
| 学术文献综述 | 论文检索、观点梳理、引用网络 | `literature_review` |

**第一个落地场景是公众号内容创作**——我自己运营公众号（寻阶行），IRIS 是我日常使用的调研工具。但架构设计保持通用性，通过 Skill 体系适配不同领域。

---

## 二、架构设计

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3 + Tailwind)                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ 输入区域  │  │ 研究进度指示  │  │ 报告渲染   │  │ 素材库/历史    │  │
│  └──────────┘  └──────────────┘  └───────────┘  └────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Skill 管理 │ 记忆搜索 │ 工具浏览 │ 使用统计 │ 示例建议       │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ SSE 流式推送
┌──────────────────────────────▼──────────────────────────────────────┐
│                     API 层 (FastAPI)                                 │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ 聊天端点 │  │ 文件上传  │  │ 素材管理  │  │ 会话记忆管理         │  │
│  └─────────┘  └──────────┘  └──────────┘  └──────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Skill API │  │ 记忆 API  │  │ 工具 API  │  │ 导出/统计 API       │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                   Agent 编排层 (LangGraph)                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    StateGraph 状态机                          │   │
│  │                                                             │   │
│  │   ┌────────┐    ┌──────────┐    ┌───────────┐              │   │
│  │   │ Router │───▶│ Planner  │───▶│ Researcher │              │   │
│  │   └────────┘    └──────────┘    └─────┬─────┘              │   │
│  │       │                               │                     │   │
│  │       │ REFINE                        │ should_stop?        │   │
│  │       ▼                               ▼                     │   │
│  │  ┌─────────┐    ┌────────┐    ┌───────────┐              │   │
│  │  │ Refiner  │    │ Writer │───▶│ Reviewer  │──┐           │   │
│  │  └─────────┘    └────────┘    └───────────┘  │           │   │
│  │                              FAIL ◄──────────┘           │   │
│  │                              │                            │   │
│  │                              ▼                            │   │
│  │                         回跳 Planner                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   AgentState (TypedDict)                     │   │
│  │  query, plan, search_results, final_report, critique,        │   │
│  │  revision_number, review_status, search_mode, should_stop,   │   │
│  │  conversation_summary, preferences, active_skill,            │   │
│  │  search_sources                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                       基础设施层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ LLM 工厂     │  │ RAG 引擎     │  │ 会话持久化               │  │
│  │ (主/备降级)   │  │ (ChromaDB)   │  │ (SQLite Checkpoint)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Skill 注册   │  │ 记忆存储     │  │ 工具注册                 │  │
│  │ (SKILL.md)   │  │ (SQLite)     │  │ (动态注册)               │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ 引用格式化   │  │ 可信度评分   │  │ Token 追踪               │  │
│  │ (Citation)   │  │ (域名权威)   │  │ (用量统计)               │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计决策

#### 决策 1：用图的拓扑表达"纠错"

传统 RAG 是链式的：检索 → 生成，一次过，没有回头路。IRIS 用 LangGraph 的条件边把"审查不通过就回跳 Planner"变成了图拓扑里的一条回边。

```
Reviewer(FAIL) ──▶ Planner ──▶ Researcher ──▶ Writer ──▶ Reviewer
                                                          │
                                                    PASS  ▼
                                                        END
```

**为什么这样设计？**
- 审查不是简单的"重试"——回跳 Planner 意味着**搜索方向会根据审查意见重新规划**
- 对比固定 prompt 重试：如果 Writer 没写好，重试大概率还是写不好——因为信息本身就不完整
- 回跳让系统能从"信息收集"层面解决问题，而不是在"文字修饰"层面死循环

#### 决策 2：Skill 体系 — 场景化策略可插拔

不同调研场景需要不同的策略。IRIS 通过 Skill 体系实现场景化适配：

- 每个 Skill 是一个 `SKILL.md` 文件（YAML frontmatter + Prompt 模板）
- 系统根据用户查询自动匹配最相关的 Skill
- 新增场景只需加一个 SKILL.md，零代码改动
- 内置 Skill：`content_research`（公众号内容创作）

#### 决策 3：四层记忆架构

| 记忆层 | 存储内容 | 生命周期 | 存储介质 |
|--------|---------|---------|---------|
| Working | 当前会话上下文 | 单次会话 | LangGraph Checkpointer |
| Episodic | 每次研究的完整记录 | 永久 | SQLite |
| Semantic | 用户偏好和领域知识 | 永久 | SQLite |
| Procedural | 成功的研究模式 | 永久 | SQLite |

#### 决策 4：文档相关性熔断

当用户上传文档但文档与问题无关时，系统不会编造信息：
- **纯文档模式**：文档不相关 → 熔断终止，诚实告知用户
- **混合模式**：文档不相关 → 自动降级为全网搜索

#### 决策 5：可信度评分

每个来源按域名权威打分（0.0-1.0），低于阈值（0.4）的直接丢弃：

| 域名类型 | 可信度 | 示例 |
|---------|--------|------|
| 学术机构 | 1.0 | .edu, .ac.uk |
| 政府 | 1.0 | .gov, .europa.eu |
| 权威媒体 | 0.9 | BBC, Reuters, NYT |
| 科技媒体 | 0.8 | TechCrunch, TheVerge |
| 其他 | 0.5 | 未知域名 |

---

## 三、Agent 节点详解

### 3.1 Router — 意图识别器

**职责**：判断用户输入属于哪类意图，并匹配最相关的 Skill

**设计要点**：
- 作为 LangGraph 节点运行，分类结果（intent/confidence/entities/active_skill）**写回 state**
- **结构化 LLM 输出**：`{intent, confidence, is_followup, entities, skill}`，带置信度
- 6 类意图：`research / chat / sql / tool_call / refine / clarify`
- **CLARIFY 意图**：低置信度/语义含糊时反问澄清，而不是默认硬塞给 RESEARCH
- **follow-up 识别**：注入对话摘要 + 是否有报告，短回复/代词续聊继承上一意图
- **Skill 进路由**：意图为 research 时，由 LLM 根据各 Skill 的 `description` 选 Skill（agent-squad 风格），失败回退 bigram 匹配器
- 无报告时强制排除 REFINE；LLM 输出非法时启用关键词兜底

### 3.2 Planner — 任务规划器

**职责**：把研究主题拆解为 3-5 个搜索子问题

**设计要点**：
- 读取对话摘要，获取已搜索方向避让列表
- 读取 Semantic 记忆（用户偏好）
- 如果存在 active_skill，注入 Skill 的 Prompt 模板
- 如果存在审查意见，针对意见中提到的缺失信息生成搜索方向
- 新主题时自动清理旧报告状态
- **结构化计划输出**：拆解为 `plan_structure: [{subtask, queries}]`（Orchestrator-Worker 的任务分解阶段），并派生拍平 `plan` 兼容下游

### 3.3 Researcher — 多源检索器

**职责**：从本地文档和网络两个渠道采集信息

**设计要点**：
- 本地文档检索：ChromaDB 向量搜索 + LLM 相关性评估
- 网络搜索：Tavily API，带重试机制
- **并行执行**：对 `plan_structure` 的每个子任务，用 `asyncio.gather` + `asyncio.to_thread` 并发执行其查询，单轮耗时从串行累计降到 ≈ 最慢一条
- 三种模式：document（纯文档）、hybrid（混合）、全网搜索
- 熔断机制：纯文档模式下文档不相关则终止
- **Skill 工具选择**：根据 Skill 的 required_tools 决定使用哪些工具
- **可信度过滤**：搜索结果按域名权威评分，过滤低质量来源
- **来源追踪**：保留 URL 和标题，供引用标注使用

### 3.4 Synthesize — 结果汇总结

**职责**：把并行检索的分散结果按子任务汇总成结构化发现摘要，供 Writer 直接引用（Orchestrator-Worker 的「结果合成」阶段）。

**设计要点**：
- 接收 Researcher 输出的 `research_findings`（按子任务分组）
- 每个子任务提炼 2-4 条关键发现，去重、保留来源出处
- 输出 `synthesis` 写入 state，Writer 优先使用该摘要而非原始片段

### 3.5 Writer — 报告撰写器

**职责**：基于检索结果撰写结构化研究报告

**设计要点**：
- 接收搜索内容 + 对话上下文 + 审查意见 + 用户偏好
- 用户偏好支持：写作风格（detailed/concise/formal/casual）+ 报告语言（zh/en）
- 流式输出：SSE 逐 token 推送，打字机效果
- 每轮增量更新对话摘要（含搜索方向，供 Planner 避让）
- **引用标注**：自动追加参考文献列表
- **记忆提取**：研究完成后自动写入 Episodic 记忆

### 3.6 Reviewer — 质量审查器

**职责**：评估报告是否充分回答了用户问题

**设计要点**：
- 输出严格 JSON：`{status: "PASS"|"FAIL", feedback: "..."}`
- 空报告直接 FAIL
- JSON 解析失败时重试一次，仍失败则 fail-closed（判 FAIL）
- 使用 smart 模型（temperature 0），确保审查一致性
- 最大重试次数由 `MAX_REVISIONS` 控制

### 3.7 Refiner — 报告精修器

**职责**：处理用户的后续交互（模糊评价 or 明确修改）

**设计要点**：
- 模糊后续检测：`_is_vague()` 函数，长度 < 20 字 + 包含特定模式词
- 模糊后续 → 轻量分析，追加到报告末尾（不破坏原报告）
- 明确修改 → 全文修订，保持 Markdown 结构

---

## 四、Skill 体系

### 4.1 Skill 定义

每个 Skill 是一个 `SKILL.md` 文件：

```markdown
---
name: content_research
description: 公众号内容创作调研
tools: [web_search, doc_search]
memory_policy: read_episodic
---

你是一个资深公众号内容编辑。用户给你一个选题，你要：

1. 搜公众号文章（site:mp.weixin.qq.com）
2. 搜技术资料（官方文档、技术博客）
3. 对比不同观点，客观呈现
4. 带引用标注 [1][2]
5. 结尾给出写作角度建议
```

### 4.2 Skill 生命周期

| 操作 | API | 说明 |
|------|-----|------|
| 列出 | `GET /api/skills` | 列出所有 Skill |
| 创建 | `POST /api/skills` | 创建新 Skill |
| 查看 | `GET /api/skills/{name}` | 获取详情 |
| 更新 | `PUT /api/skills/{name}` | 更新 Skill |
| 删除 | `DELETE /api/skills/{name}` | 删除 Skill（内置 Skill 返回 403） |

### 4.3 Skill 匹配

系统根据用户查询自动匹配最相关的 Skill：
- 使用 bigram（双字符）匹配算法，支持中文
- 匹配失败时使用默认策略，行为与不加 Skill 时完全一致

---

## 五、记忆系统

### 5.1 四层记忆架构

| 记忆层 | 读时机 | 写时机 | 存储 |
|--------|--------|--------|------|
| Working | 每个节点执行前 | 每个节点执行后 | LangGraph Checkpointer |
| Episodic | 用户发起新研究时 | 研究完成后 | SQLite |
| Semantic | Planner 规划时 | 研究完成后异步提炼 | SQLite |
| Procedural | 路由决策时 | 成功任务完成后 | SQLite |

**混合检索**：`MemoryStore` 写入时用 DashScope 嵌入存向量，搜索时「关键词 + 余弦相似度」混合打分；嵌入不可用时无损回退关键词。Skill 的 `memory_policy`（如 `read_episodic`）驱动 planner 读取对应记忆层，避免重复调研。

### 5.2 Memory API

| 端点 | 说明 |
|------|------|
| `GET /api/memory/search?q={query}&kind={kind}` | 搜索记忆 |
| `GET /api/memory/{memory_id}` | 获取单条记忆 |
| `DELETE /api/memory/{memory_id}` | 删除记忆 |

---

## 六、工具系统

### 6.1 Tool Registry

所有工具动态注册到 ToolRegistry：

| 工具 | 说明 |
|------|------|
| `web_search` | 互联网搜索（Tavily） |
| `doc_search` | 本地文档检索（ChromaDB） |
| `citation_search` | 带引用标注的搜索 |

### 6.2 Tool API

| 端点 | 说明 |
|------|------|
| `GET /api/tools` | 列出所有工具 |
| `GET /api/tools/{name}` | 获取工具详情 |
| `POST /api/tools/{name}/execute` | 执行工具（调试） |

---

## 七、引用系统

### 7.1 引用标注

报告中引用的地方标注 `[1]`，末尾自动追加：

```markdown
---

**参考文献**

[1] 文章标题 — https://example.com/article
[2] 另一篇文章 — https://example.com/other
```

### 7.2 可信度评分

每个来源按域名权威打分，低于 0.4 的直接丢弃。

---

## 八、导出与统计

### 8.1 报告导出

| 端点 | 说明 |
|------|------|
| `POST /api/export/pdf` | 导出 PDF |
| `POST /api/export/html` | 导出 HTML |

### 8.2 Token 追踪

LLM 调用自动统计 token 用量，存储在内存中。

---

## 九、技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python 3.11+) |
| Agent 编排 | LangGraph 1.0.8 |
| 向量数据库 | ChromaDB |
| 搜索 | Tavily API |
| 会话持久化 | SQLite (WAL + msgpack) |
| LLM | DashScope (qwen3.7-plus / deepseek-v4-flash) |
| Embedding | DashScope text-embedding-v4 |
| 前端 | Vue 3 (Composition API) + Tailwind CSS |
| 报告渲染 | markdown-it + KaTeX |
| 流式推送 | SSE (Server-Sent Events) |
| 部署 | Docker Compose |

---

## 十、快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- DashScope API Key
- Tavily API Key

### 本地开发

```bash
# 后端
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填入 API Key
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd ../frontend
npm install
npm run dev  # http://localhost:5173
```

### Docker 部署

```bash
docker compose up -d --build
```

---

## 十一、项目结构

```
IRIS/
├── backend/
│   ├── main.py                     # FastAPI 入口
│   ├── app/
│   │   ├── config.py               # 集中配置
│   │   ├── api/routes.py           # API 端点（22 个）
│   │   ├── graph/
│   │   │   ├── graph.py            # StateGraph 拓扑
│   │   │   ├── state.py            # AgentState 定义
│   │   │   └── nodes/              # 11 个节点：router/planner/researcher/synthesize/writer/reviewer/refiner/chat/sql/tool_executor/clarify
│   │   ├── skills/                 # Skill 体系
│   │   │   ├── registry.py         # SkillRegistry
│   │   │   ├── lifecycle.py        # CRUD 操作
│   │   │   ├── models.py           # Skill 数据类
│   │   │   ├── router.py           # Skill 路由
│   │   │   └── builtin/            # 内置 Skill
│   │   │       └── content_research/SKILL.md
│   │   ├── memory/                 # 记忆系统
│   │   │   ├── store.py            # MemoryStore
│   │   │   ├── models.py           # MemoryRecord
│   │   │   └── extractor.py        # 记忆提取
│   │   ├── tools/                  # 工具系统
│   │   │   ├── registry.py         # ToolRegistry
│   │   │   ├── builtin/            # 内置工具
│   │   │   │   ├── search.py       # web_search
│   │   │   │   ├── doc_search.py   # doc_search
│   │   │   │   └── citation.py     # citation_search
│   │   │   └── search.py           # Tavily 封装
│   │   ├── rag/engine.py           # RAG 引擎
│   │   └── utils/
│   │       ├── llm.py              # LLM 工厂 + 降级 + Token 追踪
│   │       ├── memory.py           # 会话记忆（原有）
│   │       ├── credibility.py      # 可信度评分
│   │       ├── citations.py        # 引用格式化
│   │       ├── streaming.py        # 流式输出
│   │       └── logger.py           # 日志
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.vue                 # 根组件
│       ├── components/             # UI 组件
│       │   ├── ChatHeader.vue      # 顶栏 + Skill 指示器
│       │   ├── ChatMessages.vue    # 消息流 + 进度指示器
│       │   ├── ChatInput.vue       # 输入框 + 示例建议
│       │   └── ChatSidebar.vue     # 侧栏 + 统计面板
│       ├── composables/
│       │   ├── useChat.js          # 聊天逻辑
│       │   └── useStats.js         # 统计逻辑
│       └── services/
│           └── api.js              # API 客户端
├── docker-compose.yml
└── docs/                           # 文档
```

---

## 十二、API 端点

### 聊天与调研

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式聊天 |
| `/api/upload` | POST | 上传 PDF |
| `/api/clear` | POST | 重置知识库 |

### Skill 管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/skills` | GET | 列出所有 Skill |
| `/api/skills` | POST | 创建 Skill |
| `/api/skills/{name}` | GET | 获取详情 |
| `/api/skills/{name}` | PUT | 更新 |
| `/api/skills/{name}` | DELETE | 删除 |

### 记忆管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/memory/search` | GET | 搜索记忆 |
| `/api/memory/{memory_id}` | GET | 获取详情 |
| `/api/memory/{memory_id}` | DELETE | 删除 |

### 工具管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tools` | GET | 列出所有工具 |
| `/api/tools/{name}` | GET | 获取详情 |
| `/api/tools/{name}/execute` | POST | 执行工具 |

### 导出

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/export/pdf` | POST | 导出 PDF |
| `/api/export/html` | POST | 导出 HTML |

---

## 十三、研发心得

### 为什么选择 LangGraph 而不是 CrewAI/AutoGen？

| 框架 | 优势 | 局限 |
|------|------|------|
| **LangGraph** | 图拓扑精确控制，状态可持久化，生产级 | 学习曲线陡 |
| CrewAI | 上手简单，角色定义直观 | 控制力弱，调试困难 |
| AutoGen | 对话式交互自然 | 不适合确定性流程 |

IRIS 的核心需求是**"审查不通过就回跳"这种精确的拓扑控制**，LangGraph 的条件边天然支持这种需求。

### 状态机的模块级单例模式

`graph.py` 中 StateGraph 在 import 时构建一次，每次请求只调用 `compile(memory)` 挂载 checkpointer。好处：
- 避免每次请求重建拓扑的开销
- 拓扑定义与运行时解耦

代价：增删节点需重启服务。这是可接受的 trade-off。

### 中文 Skill 匹配的 bigram 方案

最初用 substring 匹配，"公众号内容创作调研" 无法匹配 "公众号如何写爆款文章"。改用 bigram（双字符）交集评分后解决：

```
description bigrams: {"众号", "号内", "内容", "容创", "创作", "作调", "调研"}
query bigrams:       {"众号", "号如", "何写", "写爆", "爆款", "款文", "文章"}
交集: {"众号"} → score=1，匹配成功
```

### 真实使用数据

- 单篇产出时间：从 6 小时 → 2 小时
- 已撰写文章：5 篇
- 平均调研耗时：12 分钟

---

## License

MIT

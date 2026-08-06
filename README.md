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
│  ┌──────────┐  ┌──────────────┐  �───────────┐  ┌────────────────┐  │
│  │ 输入区域  │  │ 研究轨迹时间线 │  │ 报告渲染   │  │ 素材库/历史    │  │
│  └──────────┘  └──────────────┘  └───────────┘  └────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ SSE 流式推送
┌──────────────────────────────▼──────────────────────────────────────┐
│                     API 层 (FastAPI)                                 │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ 聊天端点 │  │ 文件上传  │  │ 素材管理  │  │ 会话记忆管理         │  │
│  └─────────┘  └──────────┘  └──────────┘  └──────────────────────┘  │
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
│  │  conversation_summary, preferences                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                       基础设施层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ LLM 工厂     │  │ RAG 引擎     │  │ 会话持久化               │  │
│  │ (主/备降级)   │  │ (ChromaDB)   │  │ (SQLite Checkpoint)      │  │
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

#### 决策 2：模糊后续 vs 明确修改的双模式

用户说"你觉得呢？"和"把第三段改详细"是两种完全不同的意图：

| 类型 | 处理方式 | 原因 |
|------|---------|------|
| 模糊后续 | 轻量分析，追加到报告末尾 | 用户只是想要一个观点补充，没必要全文重写 |
| 明确修改 | 全文修订，保持 Markdown 结构 | 用户有具体的修改意图 |

#### 决策 3：文档相关性熔断

当用户上传文档但文档与问题无关时，系统不会编造信息：
- **纯文档模式**：文档不相关 → 熔断终止，诚实告知用户
- **混合模式**：文档不相关 → 自动降级为全网搜索

---

## 三、Agent 节点详解

### 3.1 Router — 意图识别器

**职责**：判断用户输入是"新研究课题"还是"修改现有报告"

**设计要点**：
- 首先检查是否有已有报告（无报告 → 强制 NEW_TOPIC）
- 用 LLM 判断意图，输出 NEW_TOPIC 或 REFINE
- LLM 输出非法时，启用关键词兜底规则
- 模糊后续（"你觉得呢"、"然后呢"）默认走 REFINE

**状态读写**：无（纯路由判断）

### 3.2 Planner — 任务规划器

**职责**：把研究主题拆解为 3-5 个搜索子问题

**设计要点**：
- 读取对话摘要，获取已搜索方向避让列表
- 如果存在审查意见，针对意见中提到的缺失信息生成搜索方向
- 新主题（revision_number == 0）时自动清理旧报告状态
- 输出格式：逗号分隔的关键词

**状态读写**：
- 读：`conversation_summary`, `query`, `critique`
- 写：`plan`, `final_report` (清理), `conversation_summary` (清理)

### 3.3 Researcher — 多源检索器

**职责**：从本地文档和网络两个渠道采集信息

**设计要点**：
- 本地文档检索：ChromaDB 向量搜索 + LLM 相关性评估
- 网络搜索：Tavily API，带重试机制
- 三种模式：document（纯文档）、hybrid（混合）、全网搜索
- 熔断机制：纯文档模式下文档不相关则终止

**状态读写**：
- 读：`query`, `plan`, `search_mode`
- 写：`search_results`, `should_stop`

### 3.4 Writer — 报告撰写器

**职责**：基于检索结果撰写结构化研究报告

**设计要点**：
- 接收搜索内容 + 对话上下文 + 审查意见 + 用户偏好
- 用户偏好支持：写作风格（detailed/concise/formal/causal）+ 报告语言（zh/en）
- 流式输出：SSE 逐 token 推送，打字机效果
- 每轮增量更新对话摘要（含搜索方向，供 Planner 避让）

**状态读写**：
- 读：`search_results`, `query`, `critique`, `conversation_summary`, `preferences`, `plan`
- 写：`final_report`, `conversation_summary`

### 3.5 Reviewer — 质量审查器

**职责**：评估报告是否充分回答了用户问题

**设计要点**：
- 输出严格 JSON：`{status: "PASS"|"FAIL", feedback: "..."}`
- 空报告直接 FAIL
- JSON 解析失败时重试一次，仍失败则 fail-closed（判 FAIL）
- 使用 smart 模型（temperature 0），确保审查一致性
- 最大重试次数由 `MAX_REVISIONS` 控制

**状态读写**：
- 读：`query`, `final_report`, `revision_number`
- 写：`critique`, `revision_number`, `review_status`

### 3.6 Refiner — 报告精修器

**职责**：处理用户的后续交互（模糊评价 or 明确修改）

**设计要点**：
- 模糊后续检测：`_is_vague()` 函数，长度 < 20 字 + 包含特定模式词
- 模糊后续 → 轻量分析，追加到报告末尾（不破坏原报告）
- 明确修改 → 全文修订，保持 Markdown 结构

**状态读写**：
- 读：`query`, `final_report`
- 写：`final_report`, `conversation_summary`, `review_status`

---

## 四、记忆系统

### 4.1 当前实现：运行摘要

```
conversation_summary (字符串，最大 2000 字符)
```

**结构**：
```
用户: [本轮问题]
搜索方向: [方向1]、[方向2]、[方向3]
报告要点: [前 300 字摘要]
审查意见: [如有]
```

**更新策略**：
- 每轮增量追加
- 超过 2000 字符时 LLM 压缩
- 压缩失败时按句子边界截断（句号→逗号→硬切）

**应用场景**：
- Planner 读取摘要，提取已搜索方向，避免重复搜索
- Writer 读取摘要，保持上下文连贯性

### 4.2 持久化：SQLite Checkpoint

- 使用 LangGraph `AsyncSqliteSaver`
- 序列化格式：msgpack（非 JSON）
- WAL 模式 + timeout，避免 locked 错误
- 自动清理：7 天过期，低概率触发（10%）

---

## 五、工具系统

### 5.1 内置工具

| 工具 | 实现 | 作用 |
|------|------|------|
| `search_tavily` | Tavily API 封装 | 网络搜索，支持重试 |
| `get_retriever` | ChromaDB + DashScope Embedding | 本地文档向量检索 |
| `RerankRetriever` | CrossEncoder 精排 | 可选，增加 ~400MB 内存 |

### 5.2 LLM 工厂

**模型分配策略**：
- `fast` 模式（temperature 0.7）：router, planner, writer, refiner
- `smart` 模式（temperature 0）：researcher grader, reviewer

**降级机制**：
- 主模型（qwen3.7-plus）额度耗尽 → 自动切换备用（deepseek-v4-flash）
- 5 分钟后自动恢复尝试主模型
- 节点级模型配置：每个节点可独立指定模型

---

## 六、流式架构

```
LLM.stream() ──▶ 线程内生产 token ──▶ asyncio.Queue ──▶ SSE 端点消费
                                          ▲
                                          │
                                    ContextVar 存储
                                    每请求独立的 token_queue
```

**关键设计**：
- `ContextVar` 存储每请求的 token queue，实现请求级隔离
- 生产者（线程）写入 channel，消费者（async）读取并推入 queue
- SSE 心跳：15 秒无数据时发送 `: heartbeat\n\n`，防止代理断开
- 前端 token 即时渲染：SSE 回调直接修改 Vue 响应式对象

---

## 七、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式聊天（核心端点） |
| `/api/upload` | POST | 上传 PDF，构建向量知识库 |
| `/api/clear` | POST | 重置知识库 |
| `/api/memory/{thread_id}` | GET | 获取会话记忆 |
| `/api/memory/{thread_id}/reset` | POST | 清空会话摘要 |
| `/api/save-report` | POST | 保存报告到素材库 |
| `/api/materials` | GET | 列出素材 |
| `/api/materials/{filename}` | GET | 读取素材内容 |
| `/api/materials/{filename}` | DELETE | 删除素材 |
| `/api/aihot/news` | GET | AI HOT 新闻代理 |
| `/api/tts` | POST | 语音合成（CosyVoice） |

---

## 八、技术栈

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

## 九、快速开始

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
# 全栈
docker compose up -d --build

# 仅后端
cd backend
docker build -t iris-backend .
docker run -d --name iris -p 8000:8000 --memory=1g -v .env:/app/.env iris-backend
```

---

## 十、项目结构

```
IRIS/
├── backend/
│   ├── main.py                     # FastAPI 入口
│   ├── app/
│   │   ├── config.py               # 集中配置
│   │   ├── api/routes.py           # API 端点
│   │   ├── graph/
│   │   │   ├── graph.py            # StateGraph 拓扑
│   │   │   ├── state.py            # AgentState 定义
│   │   │   └── nodes/              # 6 个 Agent 节点
│   │   ├── rag/engine.py           # RAG 引擎
│   │   ├── tools/search.py         # Tavily 搜索封装
│   │   └── utils/
│   │       ├── llm.py              # LLM 工厂 + 降级
│   │       ├── memory.py           # 会话记忆
│   │       ├── streaming.py        # 流式输出
│   │       └── logger.py           # 日志
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.vue                 # 根组件
│       ├── components/             # UI 组件
│       ├── composables/            # 组合式函数
│       └── services/              # API 客户端
├── docker-compose.yml
└── docs/                           # 文档
```

---

## 十一、当前局限 & 演进方向

### 11.1 已知局限

| 局限 | 影响 | 优先级 |
|------|------|--------|
| 记忆系统是单一字符串，非结构化 | 长期会话信息丢失，无法支持复杂上下文 | 🔴 高 |
| 工具系统硬编码，无注册扩展机制 | 新增工具需改代码，无法动态适配不同场景 | 🔴 高 |
| 无 Skill 体系 | 不同场景用同一套 prompt，无法做场景化优化 | 🟡 中 |
| Agent 是函数调用，非独立实例 | 无法单独升级某个 Agent，无法做 Agent 间解耦 | 🟡 中 |
| 无评估/可观测性 | 无法量化质量，调试困难 | 🟢 低 |

### 11.2 演进路线图

```
V1.0 (当前)
  └─ 6 节点状态机 + 基础记忆 + 单一工具 + SSE 流式
       │
       ▼
V1.5 (记忆系统升级)
  └─ 四层记忆架构：Working / Episodic / Semantic / Procedural
       │
       ▼
V2.0 (工具 + Skill 体系)
  └─ Tool Registry 动态注册
  └─ Skill = Prompt + Tools + Memory Policy 的可插拔打包
  └─ Skill Router 自动匹配场景
       │
       ▼
V2.5 (多 Agent 重构)
  └─ 独立 Agent 实例 + MessageBus 通信
  └─ Agent 可独立升级/替换
       │
       ▼
V3.0 (可观测性 + 评估)
  └─ LangSmith / LangFuse 集成
  └─ 自动化评估 Pipeline
```

---

## 十二、研发心得

### 为什么选择 LangGraph 而不是 CrewAI/AutoGen？

| 框架 | 优势 | 局限 |
|------|------|------|
| **LangGraph** | 图拓扑精确控制，状态可持久化，生产级 | 学习曲线陡 |
| CrewAI | 上手简单，角色定义直观 | 控制力弱，调试困难 |
| AutoGen | 对话式交互自然 | 不适合确定性流程 |

IRIS 的核心需求是**"审查不通过就回跳"这种精确的拓扑控制**，LangGraph 的条件边天然支持这种需求。

### 状态机的模块级单例模式

`graph.py` 中 StateGraph 在 import 时构建一次，每次请求只调用 `compile(memory)` 挂载 checkpointer。这样做的好处：
- 避免每次请求重建拓扑的开销
- 拓扑定义与运行时解耦

代价：增删节点需重启服务。这是可接受的 trade-off。

---

## License

MIT

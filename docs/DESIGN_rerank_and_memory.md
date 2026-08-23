# 设计文档：RAG 重排（Rerank）+ 长期记忆（Memory）

> 状态：设计评审中 ｜ 日期：2026-08-23 ｜ 分支：main
> 关联代码：`backend/app/rag/engine.py`、`backend/app/rag/report_ingest.py`、`backend/app/graph/`、`backend/app/api/routes.py`

---

## 0. 现状审计（设计基线）

### 0.1 RAG 检索链路现状

```
PDF 上传 → PyPDFLoader 提取 → RecursiveCharacterTextSplitter 切片
        → DashScope text-embedding-v4 → Chroma 持久化
检索有两条互不相通的路径：
  A. get_retriever()（engine.py）   → 可选两阶段检索（默认关闭）
  B. search_reports()（report_ingest.py）→ 纯向量 similarity_search_with_score，无 rerank
```

**关键发现：rerank 代码已存在但处于三重休眠状态：**

| 问题 | 证据 |
| ------ | ------ |
| ① 默认关闭 | `ENABLE_RERANKER` 环境变量默认 `"false"` |
| ② 依赖过重 | 本地 `CrossEncoder(ms-marco-MiniLM-L-6-v2)`，需 sentence-transformers + torch，约 400MB 内存；Windows/容器环境安装易翻车（测试环境 conftest 已被迫 mock 该库） |
| ③ 覆盖不全 | 只挂在路径 A；研报检索 API（路径 B `/api/reports/search`）完全没接 |

### 0.2 记忆系统现状

| 层 | 现状 |
| ---- | ------ |
| 短期记忆 | ✅ AsyncSqliteSaver 按 thread_id 持久化全量 state（消息、报告、迭代历史），支持多轮/断线恢复/refine 复用 |
| 长期记忆 | ❌ 无。跨 thread 的用户偏好、关注标的、历史结论全部丢失 |
| 可用组件 | ✅ langgraph 1.0.8 自带 `AsyncSqliteStore`（已验证可导入），原生支持 namespace/key/value；**注意**：不配 embedding index 时 `store.search` 只是前缀扫描取最近 N 条，与查询内容无关（语义检索需额外配 `index={"embed": ...}`，本期不接） |

---

## 1. 目标与非目标

### 目标

- **G1（Rerank）**：两条检索路径统一接入轻量 rerank，形成完整的「切片 → 嵌入 → 召回 → **重排** → 生成」链路；rerank 失败自动降级纯向量，不阻断服务
- **G2（Memory）**：跨会话记住用户关注标的与偏好，在 router/planner 阶段注入上下文，实现"换个会话还记得我"
- **G3**：两者均有开关与降级路径，默认配置下行为可预测

### 非目标

- 不做用户账号体系（user_id 用前端生成的设备 ID，够 demo 也够单机部署）
- 不做记忆的自动遗忘/衰减策略（记一条删一条，手动管理）
- 不引入向量库以外的检索源（BMQ25 混合检索不在本期）

---

## 2. 方案 A：Rerank 重排

### 2.1 技术选型

| 方案 | 优点 | 缺点 | 结论 |
| ------ | ------ | ------ | ------ |
| 本地 CrossEncoder（现状） | 零 API 成本、无网络依赖 | 400MB 内存 + torch 依赖重、Windows 安装易翻车 | 弃用 |
| **DashScope `gte-rerank-v2`** | 与现有 embedding 同供应商同 Key、毫秒级、零本地依赖 | API 调用成本（千次几分钱级别）、多一跳网络 | **采用** |
| Cohere Rerank | 效果好 | 又一个供应商、又一个 Key | 弃用 |

### 2.2 架构

```
                    ┌──────────────────────────────┐
 query ──► Chroma ──►│ fetch_k=20 候选（向量召回）    │
                    └──────────────┬───────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │ DashScopeReranker（新增）      │ ── 失败 ──► 降级：按向量距离序直接取 top_k
                    │ gte-rerank-v2 精排            │
                    └──────────────┬───────────────┘
                                   ▼
                              top_k=5 返回
```

### 2.3 代码改动点

**新增 `backend/app/rag/reranker.py`：**

```python
class DashScopeReranker:
    """gte-rerank-v2 精排器。接口签名对齐 CrossEncoder.predict，便于替换。"""

    def __init__(self, model: str = "gte-rerank-v2"):
        self.model = model

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        # 1. 调 dashscope.TextReRank：documents + query → relevance_score
        # 2. 按 score 降序取 top_k
        # 3. 任何异常抛出 RerankError，由上层捕获降级（fail-open，不 fail-closed）
        ...
```

**改造 `engine.py`：**

- `get_reranker()` 改为返回 `DashScopeReranker`；删除 CrossEncoder 懒加载（保留 git 历史即可）
- `ENABLE_RERANKER` 默认值改 `"true"`（依赖已轻量化，无内存顾虑）
- `RerankRetriever._get_relevant_documents` 中 rerank 调用包 try/except → 异常时 `log.warning` + 返回向量序 top_k（**注意：当前代码无此 try/except，降级发生在上一层 `researcher.py:101-107`；此次需新增**）

**改造 `report_ingest.py::search_reports`：**

- `similarity_search_with_score(query, k=FETCH_K)` → rerank → 截断 top_k
- 返回结构增加 `"reranked": true/false` 字段，前端/调用方可感知是否精排
- **评分契约（I1）**：rerank 启用后，`relevance_score`（越大越相关，0-1 归一化）替换原有的 Chroma distance（越小越相关）；通过 `reranked` 布尔字段区分语义，消费方按字段选择解读方式
- **同步调用改为 async I/O（I2）**：`/api/reports/search` 是 `async def`，rerank 走网络会阻塞事件循环；复用 `/status` 端点已有的 `asyncio.to_thread` 范式，将 rerank 调用丢进线程池

**配置新增（config.py）：**
沿用现有 `ENABLE_RERANKER` 布尔项（`config.py:19`），仅新增模型名：

```python
RERANK_MODEL = os.getenv("RERANK_MODEL", "gte-rerank-v2")
```

### 2.4 降级矩阵

| 场景 | 行为 |
| ------ | ------ |
| gte-rerank API 超时/限流 | 单次降级纯向量序 + warning 日志，不重试（rerank 是锦上添花，不值得阻塞）；超时阈值显式设 `timeout=2-3s`（默认不适合检索热路径） |
| 返回候选数 < top_k | 全量返回，不调 rerank API（省一次调用） |
| rerank 同步调用阻塞事件循环 | 用 `asyncio.to_thread` 丢线程池（`/status` 端点已有范式）；实施时验证事件循环无阻塞 |
### 2.5 测试计划

- 单测：DashScopeReranker mock dashscope SDK，验证排序/截断/异常降级三条路径
- 单测：`search_reports` 带/不带 rerank 的返回结构（`reranked` 字段）
- 集成：`ENABLE_RERANKER=true` 时 `/api/reports/search` 端到端（mock API）
- 单测（I3）：rerank 开启态下 `get_retriever` 分支——显式 mock `DashScopeReranker.rerank` 返回固定分值，验证排序正确（conftest 把 dashscope mock 成 MagicMock 时此项必补，否则 MagicMock 返回垃圾对象导致 `sorted(key=float)` 随机序或报错）
- 现有 conftest 对 sentence_transformers 的 mock 可移除对应部分

**工作量：约 0.5-1 天（含测试 + DEPLOY.md 修订）**

---

## 3. 方案 B：长期记忆（Long-term Memory）

### 3.1 存储选型

**采用 langgraph 原生 `AsyncSqliteStore`**，理由：

- 与 checkpoint 同一套 SQLite 生态，部署零新增组件
- 原生 namespace 层级（`("memories", user_id)`），天然按用户隔离
- 1.0.8 版本已验证可导入，API 稳定

### 3.2 数据模型

```
namespace: ("memories", user_id)          # 用户隔离
key:       <memory_id>（watch_stock 用确定性 key `watch:{stock_code}` 幂等；preference/fact 用 uuid）
value:     {
  "kind": "watch_stock" | "preference" | "fact",
  "content": "用户长期关注复星医药(600196)",
  "stock_code": "600196",        # kind=watch_stock 时存在
  "source": "auto" | "explicit",   # 自动抽取 or 用户显式要求
  "thread_id": "xxx",              # 来源会话，便于溯源
  "created_at": "...", "updated_at": "..."
}

三类记忆（刻意保持最小集，避免过度设计）：

| kind | 示例 | 写入时机 |
| ------ | ------ | --------- |
| `watch_stock` | "关注 600196" | 研究完成时自动记录本次分析的股票 |
| `preference` | "偏好简洁结论" | 用户显式说"记住我喜欢…"时 |
| `fact` | "我是医药行业研究员" | 同上，LLM 抽取确认后写入 |

### 3.3 读写时机（关键设计）

```
写入（研究/闲聊结束时，异步、不阻塞响应）：
  research/chat 流结束
    → 后台任务：规则抽取（正则识别股票代码 + "记住/关注"关键词）
    → 命中 watch_stock 类 → upsert 到 Store（确定性 key `watch:{stock_code}` 幂等去重）
    → 命中显式记忆请求 → LLM 一次轻量调用抽取结构化记忆 → 写入

读取（新增首节点注入）：
  START → load_memories（新增节点）→ 条件路由（planner/refiner/chat）
    → load_memories 内：store.search(("memories", user_id), limit=5)  # 前缀扫描取最近 N 条，非语义检索
    → 拼装为 system prompt 前缀：「用户背景：长期关注 600196…」
    → 注入 state 字段 user_memories，planner/writer/chat 的提示词因此天然感知用户历史
```

（S3 正则一致性：memory_writer 的股票代码抽取复用 `report_ingest` 的严格正则 `[68]\d{5}|[03]\d{5}`，不用 router 的宽松 `\b\d{6}\b`，避免把日期段号、基金代码误记为 watch_stock）
**设计取舍：**

- 写入用**规则优先 + LLM 兜底**而非每轮 LLM 抽取——省成本、行为可预期
- 读取**只注入不参与路由决策**——记忆影响"怎么答"，不影响"走哪条边"（避免记忆错误导致 refine/research 误判，这是今天 pre-run 路由修复的同款教训）
- 注入点选在**新增首节点 `load_memories`**而非 traced_router：后者在当前拓扑中是死代码（`graph.py` 入口 `set_conditional_entry_point` 直达 planner/refiner/chat，不经过 router 节点），且条件入口函数的返回值只是边名字符串，LangGraph 不会把副作用合并进 state
- 注入覆盖 planner/writer/**chat** 三条路径——演示场景"换个会话还记得我关注什么"大概率走 chat，不能漏
- 记忆上限每用户 50 条，超出淘汰最旧（SQLite 查询天然支持）
### 3.4 生命周期管理

**Store 采用独立 DB 文件**（`config.py:45` 已预定义 `STORE_DB = store.db`），与 `CHECKPOINT_DB` 物理隔离。理由：checkpoint 已承载 checkpoint 写入 + RateLimiter（`routes.py chat_limiter`）两个写入方，三写方挤同一 SQLite 在 WAL 下仍可能 `database is locked`；分库后各管各的，备份/清理策略各自独立。

**连接生命周期（关键）**：
后台异步写入必须在连接存活期间完成。采用方案 **(b)：memory_writer 用独立的短命 `AsyncSqliteStore` 上下文**——每次写入在 `async with AsyncSqliteStore.from_conn_string(STORE_DB) as store` 内完成，随写随关，不依赖请求级 SSE 上下文中已被关闭的连接。
（方案 a 同步尾步会增加 [DONE] 延迟；方案 c 模块级长连在多 worker 下会串，均不取。）

**初始化**：首次启动调用 `await AsyncSqliteStore.from_conn_string(STORE_DB).setup()` 建表，放在 `main.py` 的 app 创建阶段（与 `_preheat_data_cache` 同级），不放在请求路径上。

**新增 API**：
  - `GET  /api/memory?user_id=` → 列出该用户全部记忆
  - `DELETE /api/memory/{memory_id}?user_id=` → 删除单条（红线操作走前端确认）

**user_id 来源**：前端 `localStorage` 生成的 UUID，随每次请求携带（header `X-User-Id`）
### 3.5 代码改动点

| 文件 | 改动 |
| ------ | ------ |
| `app/graph/graph.py` | 新增首节点 `load_memories`（START → load_memories → 条件路由）；编译图时注入独立短命的 `AsyncSqliteStore` 上下文（非连接池，每次写入独立 `from_conn_string(STORE_DB)`） |
| 新增 `app/graph/nodes/load_memories.py` | 从 Store 读取 user_memories → 注入 state |
| 新增 `app/graph/nodes/memory_writer.py`（或并入 chat/research 收尾） | 异步规则+LLM 抽取写入（watch_stock 用确定性 key `watch:{stock_code}` 幂等去重） |
| `app/agents/prompts.py` | planner/writer/**chat** prompt 增加用户背景段（有记忆才拼，空则不加） |
| `app/api/routes.py` | 3 个记忆管理端点 + `X-User-Id` 透传 |
| `frontend/src/services/api.js` | 请求头带 user_id；设置页新增"记忆管理"入口（可选，二期） |

### 3.6 测试计划

- 单测：规则抽取器（股票代码识别、"记住"关键词、去重 upsert）
- 单测：Store 读写隔离（user A 的记忆不出现在 user B）
- 单测：记忆注入 prompt 的拼装（有记忆/无记忆两态）
- 单测：Store 不可用时全链路降级（记忆缺失不影响研究主流程）
- 单测：`watch:{stock_code}` 确定性 key 幂等性（重复写入不产生重复记录）
- E2E：会话 1 研究 600196 → 新会话 2 问"我关注的股票怎么样" → 验证 load_memories 节点日志出现记忆注入

**工作量：约 2-3 天（含测试）**

---

## 4. 实施顺序与里程碑

| 阶段 | 内容 | 产出 |
| ------ | ------ | ------ |
| P1 | Rerank（方案 A） | 两条检索路径统一精排 + 降级，`reranked` 字段可见 |
| P2 | 长期记忆（方案 B） | 跨会话记忆 + 注入 + 管理 API |
| P3 | 文档收口 | README 架构图更新 + DEPLOY.md OOM 警告修订 + INTERVIEW_QA 补"为什么这样设计记忆/rerank" |

P1、P2 相互独立，可并行；合计约 **3-4 天**（rerank 0.5-1 天 + memory 2-3 天）。

## 5. 风险与对策

| 风险 | 对策 |
| ------ | ------ |
| gte-rerank API 变更/收费策略变化 | 抽象 Reranker 接口，可换 Cohere/本地模型；fail-open 降级保证主流程 |
| 记忆注入污染 prompt（错误记忆误导生成） | 只注入不路由 + 用户可删 + 上限 50 条 |
| AsyncSqliteStore 与 AsyncSqliteSaver 连接竞争 | 独立 DB 文件（STORE_DB）物理隔离，无竞争 |
| 演示时记忆为空显得功能"没做" | 预置 2-3 条演示记忆（如关注 600196），与 mock 快照同策略 |
| `ENABLE_RERANKER` 默认翻 true 使 `DEPLOY.md` OOM 警告失效 | P3 文档收口必须同步修订 DEPLOY.md |
| 面试官问"怎么证明 rerank 有效" | 补 20 query 手工标注的小评测脚本（哪怕粗略），否则零评测只有工程降级 |

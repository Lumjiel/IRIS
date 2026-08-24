# 优化方案：接入同花顺官方 Financial-API 作为一级数据源

> 目标仓库：<https://github.com/HiThink-Tech/Financial-API>（MIT，同花顺官方 A 股数据服务）
> 关联文档：`docs/DESIGN_rerank_and_memory.md`（同系列）、`docs/benchmark.md`（暴露的缺口）

## 0. 一句话结论

把**同花顺官方 API 插为数据降级链的最上层**（同花顺 → AKShare → 内置快照），
用半天工作量修复 benchmark 暴露的最大诚实缺口——"行情数据是离线模拟快照"，
同时为面试补上"为什么选商业 API 而不是免费 AKShare"的真实工程决策叙事。

---

## 1. 现状审计（为什么需要它）

### 1.1 benchmark 实测暴露的问题（2026-08-24）

| 问题 | 证据 | 影响 |
|------|------|------|
| 数据层是假的 | AKShare 未装/网络不可用 → 全部走内置模拟快照，5 只样本股报告的行情数字均为离线兜底 | 面试官现场验数即穿帮；"数据来源标注率 100%"标注的是 mock |
| AKShare 安装脆弱 | Windows/容器安装易翻车；无 SLA、无限流保障，高峰期限流 | 生产可用性存疑 |

### 1.2 现有降级链（akshare_tools.py）

```text
L1: AKShare/东方财富（在线）
L2: 备用源
L3: 内置模拟快照（离线兜底）
```

工具签名（data_collector 并行调用）：`query_stock_quote / query_stock_info /
query_financial_indicators / query_stock_news`，返回 JSON 字符串，带 `data_source` 字段。

### 1.3 Financial-API 能力对照

| IRIS 需要 | Financial-API 覆盖 | 结论 |
| ----------- | ------------------- | ------ |
| 实时行情 quote | ✅ 最新行情、集合竞价 | 直接替换 L1 |
| 公司概况 info | ✅ 标的目录、公司行动、估值 | 直接替换 L1 |
| 财务指标 financials | ✅ 财务报表与指标 | 直接替换 L1 |
| 个股新闻 news | ❌ 不覆盖 | 保持 Tavily/AKShare 现状 |
| 加分项 | 板块/涨跌停/龙虎榜/热榜/MCP Server | 可选扩展 |

## 2. 技术选型

| 方案 | 优点 | 缺点 | 结论 |
| ------ | ------ | ------ | ------ |
| **REST API 直连（httpx）** | 最轻量；对齐现有 retry_policy/超时模式；契约文档齐全（docs/api/endpoints-*.md） | 要自己处理鉴权头 | ✅ 采用 |
| 托管 MCP 端点 | 21+4+2 工具现成；无需本地跑 server | 引入 MCP client 依赖，改 data_collector 架构 | P3 演示项再做 |
| marketdb Python SDK（DuckDB 本地库） | 全量 Parquet 本地化 | 重；面向量化研究场景，IRIS 用不到 | 弃用 |

鉴权：统一环境变量 `HITHINK_FINANCE_API_KEY`（fuyao.aicubes.cn/admin 获取）。
**红线**：Key 只进 `.env`，不进 git/prompt/日志。

## 3. 设计要点

### 3.1 新降级链（四层）

```text
L1: 同花顺官方 API（新增，ENABLE_HITHINK=true 默认开）
L2: AKShare/东方财富（原 L1 降级）
L3: 备用源（原 L2）
L4: 内置模拟快照（原 L3，最终兜底不变）
```

fail-open 语义不变：任何一层失败静默落到下一层，`data_source` 字段如实标注
（如 `同花顺官方API` / `AKShare/东方财富` / `内置模拟快照`），前端与 benchmark 口径自动跟随。

### 3.2 配置新增（config.py）

```python
HITHINK_API_KEY = os.getenv("HITHINK_FINANCE_API_KEY", "")
ENABLE_HITHINK = os.getenv("ENABLE_HITHINK", "true").lower() == "true"
HITHINK_TIMEOUT_S = float(os.getenv("HITHINK_TIMEOUT_S", "5"))
```

Key 缺失或开关关闭时整层跳过（等价于现状三链），零破坏性。

### 3.3 代码改动点

| 文件 | 改动 |
| ------ | ------ |
| **新增** `app/tools/hithink_tools.py` | 对齐 akshare_tools 的 4 个函数签名（quote/info/financials；news 不做）；httpx 同步调用 + `asyncio.to_thread` 包装（复用 `/status` 端点范式）；超时 5s、失败抛异常交由降级链 |
| `app/tools/data_collector.py`（或并行调用处） | 每个 tool 内部先试 hithink 再落 akshare——**在工具函数内降级而非 collector 层**，保持 collector 无感知 |
| `app/config.py` | 上述 3 个配置项 |
| `.env.example` | `HITHINK_FINANCE_API_KEY=` 注释说明获取渠道 |
| `backend/tests/test_hithink_tools.py` | 见 §4 |
| `docs/benchmark.md` | 数据口径更新（重跑后） |

### 3.4 明确不做

- 不替换 query_stock_news（对方不覆盖新闻）
- 不引入 marketdb/DuckDB（场景不符）
- 不在本期接 MCP（见 §6 P3）

## 4. 测试计划

- 单测（mock httpx）：正常返回 / 非 200 / 超时 / Key 缺失四条路径，均正确落到下一层
- 契约测试：按官方 docs/api/endpoints-financials.md 等契约文件断言响应字段映射
- 降级链集成：hithink 失败 → akshare 兜底成功，`data_source` 如实变化
- E2E：真实 Key 下跑 600196 单只研究，确认 `data_source=同花顺官方API`
- 回归：全量 pytest（当前基线 187 passed）

## 5. 实施阶段

| 阶段 | 内容 | 工作量 |
| ------ | ------ | -------- |
| P1 | hithink_tools.py 三工具 + 降级链接入 + 单测 | ~0.5 天 |
| P2 | 注册真实 Key → 重跑 benchmark_run → 更新 docs/benchmark.md 数据口径 | ~1 小时 |
| P3（可选加分） | 用 LangChain MCP adapter 接托管端点做演示，兑现重构计划 P2 的"MCP 数据接入层" | ~0.5 天 |

前置条件：**注册 fuyao.aicubes.cn 获取 API Key**（免费额度/定价注册后确认；
若定价不可接受，本方案仅损失 L1 层，其余照旧）。

## 6. 风险与对策

| 风险 | 对策 |
| ------ | ------ |
| Key 收费/额度超限 | 四层降级天然兜底；`ENABLE_HITHINK` 一键关闭；用量可观测（后续可挂 /api/usage 同款统计） |
| 第三方服务不稳定 | 超时 5s 显式设置 + fail-open；SLA 由 AKShare 层续命 |
| Key 泄露 | 仅存 `.env`（已 gitignore）；日志脱敏；不进 prompt |
| 响应字段变更 | 契约测试锁定关键字段映射；解析失败按层降级不炸主流程 |

## 7. 面试叙事（数字实测后填入）

> "数据源我做过一次真实的可靠性升级：最初用免费的 AKShare，benchmark 实测发现
> 它在 Windows/容器环境安装脆弱且无限流保障，一旦不可用整个数据层就退化到离线快照。
> 我接入了同花顺官方金融数据服务作为一级数据源——选型时对比了它的 REST、Python SDK
> 和托管 MCP 三种接入方式，选了最轻的 REST 直连，并把原有的三层降级链扩成四层：
> 同花顺 → AKShare → 备用源 → 离线快照，每层的 data_source 字段如实透传到前端和
> 评测报告。切换后 benchmark 里 5 只样本股的数据全部来自真实行情，且主数据源故障时
> 系统行为与之前完全一致。"

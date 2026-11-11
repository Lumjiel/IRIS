# 04 · 证据映射（Evidence Map）

> 规则：每个「简历声称的能力」映射到可复核证据。证据分级：
> **A** = 命令输出可直接复现 · **B** = 代码 文件:行 · **C** = 文档/commit 记录 · **D** = 外部调研（不足以单独证明）。
> 数字以「命令实际输出」为准，重跑可能变化。

## 1. 工程质量

| 声称 | 证据 | 级 |
|------|------|----|
| 299 tests 全绿，覆盖率 69.37%，门禁 ≥62% | `cd backend && .venv/bin/python -m pytest tests/ -q --timeout=120 --cov=app --cov-fail-under=62` → `299 passed, Required test coverage of 62% reached. Total coverage: 69.37%`（2026-11-10） | A |
| 覆盖率提升不靠改实现 | 本次 56.46%→69.37% 仅新增测试文件：`tests/test_memory.py`（16 用例）、`tests/test_streaming.py`（11）、`tests/test_api_routes.py`（29）、`tests/test_fault_injection.py`（16）；`app/` 零改动（用例数来源：`pytest --collect-only -q`，2026-11-10） | A/B |
| Lint 门禁零错 | `ruff check app/ --select E9,F63,F7,F82` → `All checks passed!` rc=0（2026-11-10） | A |
| CI 三件套（ruff+cov+前端构建） | `.github/workflows/test.yml:21-33`（ruff 步骤 + `--cov-fail-under=62`）+ `:34-50`（frontend build） | B |

## 2. 数据工具稳定性

| 声称 | 证据 | 级 |
|------|------|----|
| 4 个数据工具 × 4 层降级（同花顺 L0→东财→新浪/雪球→mock） | `app/tools/akshare_tools.py:423-560`（quote 链）、`:138-241`（info 链） | B |
| 重试封装（网络错误重试、退避、不可重试直返） | `app/tools/akshare_tools.py:40-69` `_safe_request`；测试 `tests/test_fault_injection.py::TestSafeRequest`（6 用例） | B/A |
| 工具永不抛异常 + 降级可识别 | 全链故障注入 `test_fault_injection.py::test_full_chain_down_never_raises` → `degraded=true`；mock 兜底带「内置模拟数据」来源标注 | A |
| 超时控制 | 腾讯补充接口 `timeout=3`（`akshare_tools.py:387`）；同花顺层 `_timeout_s()`（`hithink_tools.py:34`） | B |
| fail-open（个股失败不炸批量响应） | `test_api_routes.py::test_snapshot_fail_open_with_error` / `test_snapshot_quote_raises_still_fail_open`（2026-11-10 绿） | A |

## 3. 可观测 / Trace

| 声称 | 证据 | 级 |
|------|------|----|
| 节点级 trace（全节点） | `app/graph/graph.py:48-116` 每节点 `@traceable` 包装 | B |
| 前端实时时间线（start/done+耗时） | `emit_node_event`（`app/utils/streaming.py:29-41`）→ SSE 事件 | B |
| Token 用量 real/est 分开累计 | `app/utils/llm.py:21-28`；查询口 `GET /api/usage`（`routes.py:1150`），测试 `test_api_routes.py::test_usage_stats` | B/A |
| 数据源/LLM 状态探测端点 | `GET /api/status`（`routes.py:1161-1194`），测试 `test_status_endpoint` | B/A |
| SSE 心跳防断连 | `routes.py:425`（`HEARTBEAT_INTERVAL=15`，空闲超时发 `: heartbeat`） | B |

## 4. 评测体系

| 声称 | 证据 | 级 |
|------|------|----|
| 端到端 benchmark（五指标，SSE 实测） | `backend/eval/benchmark_run.py`；结果 `docs/benchmark.md`（2026-08-24 / 11-08 两轮） | C |
| 修订快速通道效果 | v2.1：中位延迟 598.2s→436.4s（-27.1%），600196 2508.8s→543.7s（`docs/benchmark.md`，2026-11-08） | C |
| 20 只样本池已注册 | `benchmark_run.py` `STOCKS` 20 项（2026-11-10）；其中 15 只真实数字**待实测**（`BLOCKED.md`，dummy key 环境跑不出真实数字，不预填） | B/C |
| Badcase 复盘 ×3（含反例） | `docs/badcase-review.md`（Case1 流式额度降级缺失 P0 / Case2 测试依赖真实环境 / Case3 性能回归 +362%） | C |

## 5. LLM 工程与记忆

| 声称 | 证据 | 级 |
|------|------|----|
| 逐节点模型路由 + fast/smart 双档 | `app/utils/llm.py:48-58,102-` | B |
| 主模型额度熔断（TTL 5min 自动恢复） | `llm.py:64-87`（`_EXHAUSTED_TTL=300`、`is_quota_error`、`mark_primary_exhausted`） | B |
| 流式路径降级与 invoke 对齐 + 回归测试 | `streaming.py:87-115`；`tests/test_streaming.py::test_quota_error_triggers_fallback_stream`（2026-11-10 绿） | B/A |
| 会话摘要增量更新 + 压缩降级 | `app/utils/memory.py:39-104`；测试 `test_memory.py` 16 用例（100% 覆盖） | B/A |
| 长期记忆三类（watch_stock/fact/preference）+ 淘汰 | `app/utils/memory_store.py:34-36,178`；API 测试 `test_memory_store.py::TestMemoryAPI` | B/A |
| 检索方向去重避让 | `memory.py:107-131`（`build_conversation_context`），测试断言去重保序 | B/A |

## 6. RAG

| 声称 | 证据 | 级 |
|------|------|----|
| DashScope text-embedding-v4 + ChromaDB | `app/rag/engine.py` | B |
| 可选 CrossEncoder/DashScope 重排，失败降级纯向量序 | `app/rag/reranker.py`（95% 覆盖）；2G 机器 `ENABLE_RERANKER=false` 的资源决策在 `AGENTS.md` | B/C |
| 研报入库与检索 API | `app/rag/report_ingest.py`（77% 覆盖）；`POST /api/reports/upload`、`GET /api/reports/search`（`routes.py:1102-1138`） | B |

## 7. 部署

| 声称 | 证据 | 级 |
|------|------|----|
| 轻量服务器部署（systemd + Nginx 反代，uvicorn RSS ~200MB） | commit `1c7538e`（2026-11）`backend/DEPLOY.md` | C |

## 8. 边界（如实）

| 事项 | 现状 |
|------|------|
| 15 只扩容样本真实数字 | 待真实 API 环境跑 `python -m eval.benchmark_run`（`BLOCKED.md`） |
| 在线 eval（生产流量采样评分） | 未建设，属下一阶段 |
| 东财数据源 | 生产服务器被封，实际可达层 = 同花顺 L0（`AGENTS.md` 记录） |

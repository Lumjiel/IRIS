# BLOCKED — IRIS#E1（2026-11-10 夜间）

## B1: 15 只扩容样本的真实 benchmark 数字无法本夜产出

- **要什么**：GOAL 验收清单 #4 要求 `docs/benchmark.md` 有 20 只样本的真实数字
  （六章节完整率/标注率/延迟/token）。
- **为什么堵**：本夜执行环境 (a) 无外网访问，(b) 注入的是 dummy key
  （OPENAI/DASHSCOPE/TAVILY/HITHINK 全部 `ci-dummy-key`），LLM 调用与同花顺/
  Tavily 数据链全部不可达，端到端 benchmark（`python -m eval.benchmark_run`）
  必然全失败。红线「不许编造指标」优先于「把表填满」。
- **已做的替代**（不编数字，把路铺好）：
  1. `backend/eval/benchmark_run.py` `STOCKS` 池 5 → 20 只（代码-名称与仓库内
     `HOT_FALLBACK_CODES` 交叉验证过 10 只）；
  2. `docs/benchmark.md` 样本表扩到 20 只并标注 实测/待实测 状态；
  3. 已有 5 只的真实数字（2026-08-24 / 2026-11-08 / v2.1 三轮）原样保留。
- **解锁条件**：一台有真实 `OPENAI_API_KEY` + 数据源网络的机器，跑
  `python -m eval.benchmark_run`（约 20 × 7-13 min），把输出回填待实测行。

## B2: 可选项「研报库 ≥26 份 / 图表 / PDF 导出 / 多股对比」本夜不可做

- **为什么堵**：
  1. 研报库扩容依赖 DashScope embedding（`rag/report_ingest.py` 真实向量化），
     dummy key 下无法入库；
  2. PDF 导出/图表需要引入新依赖（reportlab/matplotlib 等），红线「不新增依赖」
     且本夜无网络装不了包。
- **现状**：研报入库/检索链路已有测试覆盖（`tests/test_report_ingest.py`，
  report_ingest.py 覆盖率 77%），API 端点 `POST /api/reports/upload` /
  `GET /api/reports/search` 已在 `tests/test_api_routes.py` 覆盖参数校验分支。

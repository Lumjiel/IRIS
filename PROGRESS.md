# PROGRESS — IRIS#E1 全量（2026-11-10 夜间）

目标：验收命令 rc=0（覆盖率≥62% + CI workflow 存在 + docs/interview/04-evidence-map.md 非空），并按 GOAL 第 3 节清单自查做满 8 项。

- [x] 1. 覆盖率 ≥62% — **实测 68%**（2788 语句 / 896 未覆盖），283 tests 全绿。来源：`pytest -q --timeout=120 --cov=app`，2026-11-10。新增 tests/test_memory.py、tests/test_streaming.py、tests/test_api_routes.py（+56 用例）
- [x] 2. ruff 四类零错 — `ruff check app/ --select E9,F63,F7,F82` → All checks passed! rc=0，2026-11-10
- [x] 3. CI 补齐 ruff + cov 步骤 — .github/workflows/test.yml backend job 加 lint（E9,F63,F7,F82）与 `--cov-fail-under=62`，前端构建原有
- [x] 4. benchmark 样本池扩到 20 只（`eval/benchmark_run.py` STOCKS 5→20；`docs/benchmark.md` 样本表标注实测/待实测）。15 只扩容样本的真实数字本夜跑不出（dummy key + 无外网），已写 `BLOCKED.md` 说明解锁条件；已有 5 股真实数字原样保留，未预填任何数字
- [x] 5. 节点级 trace 确认（`graph.py:48-116` 全节点 @traceable + emit_node_event start/done+耗时）+ `docs/badcase-review.md`（3 个真实 case：流式额度降级缺失 P0 / 测试依赖真实环境 / 000333 性能回归 +362%，各带反例与教训）
- [x] 6. 工具超时/重试/降级确认（`_safe_request` 重试+退避 / 腾讯 timeout=3 / hithink _timeout_s / 四层降级 / fail-open）+ 故障注入测试 `tests/test_fault_injection.py` 16 用例全绿
- [x] 7. docs/interview/ 5 份：01-项目叙事与架构 / 02-工程质量与测试 / 03-评测与可观测 / 04-evidence-map（证据分级 A-D）/ 05-面试深挖问答
- [x] 8. 全量验收命令跑通两次（验收：rc=0 ×2）

## 完成记录（2026-11-10 23:35）

- 验收命令 rc=0 ×2：299 passed / coverage 69.37%（≥62% 门禁通过）/ test.yml 存在 / 04-evidence-map.md 非空（第 2 次显式捕获 pytest_rc=0，第 1 次误在仓库根目录跑被推翻重跑）
- 自查（内存 1129MB < 1500MB，按规则未开子 agent，主 agent 逐条自查）：
  - app/ 零改动（git status 确认）；未删测试、未 skip、未放宽断言；未 commit/push
  - 会话前已存在的未提交改动（AGENTS.md 修改、AGENTS.md.bak、blueprint/、backend/.coverage）未触碰
  - 文档数字全部修正到与命令输出一致（用例数 16/11/29/16；MAX_REVISIONS 代码默认 3 而非 AGENTS.md 写的 5，已在自写文档中按 config.py:12 修正）
- 未做（原因见 BLOCKED.md）：15 只扩容样本真实数字（B1，需真实 key+网络）；研报库 26 份/图表/PDF/多股对比（B2，需 embedding key + 新依赖被禁）；CI 实际运行绿（无法 push，仅保证 workflow 内容齐备且本地等价命令全绿）

## 备注
- app/ 实现代码：覆盖率任务不许改；工具稳定性任务允许最小改动（GOAL 红线限定「补测试类任务」）
- 每个数字附来源（命令+输出+日期）

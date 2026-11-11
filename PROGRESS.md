# PROGRESS — IRIS#M1 收尾（2026-11-12）

上一轮（2026-11-11）已把 GOAL 三条终局全部跑通并标记 `STATUS: done`；本轮为收尾轮：**只整理，不加新功能**。产物见 `docs/FINAL.md`。

## 本轮做完

1. **结构盘点**（`tree -L 2`）：活的（backend/frontend/eval/deploy/docs）归位良好；历史规划文档沉底归档。
   - `REFACTOR_PLAN.md` / `PROJECT_BRIEFING.md` / `blueprint/` → `git mv` 进 `docs/archive/`（历史记录，保留不删）
   - `docs/demo{1,2}.jpeg`、`docs/diagrams/whiteboard_*.png`（全仓库零引用）→ `/root/trash/2026-11-12/IRIS/docs/...`，索引已写 `/root/trash/INDEX.tsv` 三行
2. **文档同步（过期断言逐条改掉）**：
   - `README.md`：测试数 127/218 → **299 passed / 69.22%（2026-11-11 实测）**，补复现命令；节点数「九节点」→ 以 `backend/app/graph/graph.py:240-257` 实际注册的 **15 节点** 为准（节点表补 Refiner 行）；「三层降级」→ **四层降级**（同花顺 L0→东财→雪球/新浪→Mock，共 4 处口径统一）；frontend/ 状态从「已被 frontend-next 替代待下线」改为实情「**当前生产使用**（docker-compose 与服务器部署均指向它），frontend-next 重构中未接入」；benchmark 节改为「5 只已实测 + 15 只待实测，数字不编造」并补 LLM 裁判一段；快速开始修掉 Windows 路径 `venv\Scripts\activate`；结构树对齐归档后的实况
   - `AGENTS.md`：「8-Node State Machine」→ **15-Node**（附 graph.py 行号证据）；tests 注记同步 299/69.22%；结构树补 frontend-next / 根 eval / deploy / docs/interview / docs/archive / mcp_server.py
   - `CLAUDE.md`：原为 AGENTS.md 的独立副本且断言过期（qwen3.7-plus 等）→ 收敛为指向 AGENTS.md 的入口页（不删文件，工具入口保留）
3. **docs/FINAL.md**：是什么/为谁做、三条命令跑起来、三条演示路径（对齐 `docs/interview/06-live-demo.md`）、已知缺陷与不做的事（口径矛盾/指数区空/benchmark 15 只待测/frontend-next）、待清理（两处 eval 并存、双 pyrightconfig 属有意设计）
4. **依赖记账**：本轮零安装，`docs/env.md` 无需补记

## 验收

```
python3 /root/night/tools/check_regress.py --test "cd backend && python3 -m pytest -q --cov=app --cov-fail-under=62"
→ [regress] ✓ 测试绿 / 完成度 18/21（基线 18/21）/ ✓ 通过，rc=0
```

未动 `app/` 实现代码、未删测试、未改 features.json（desc 冻结条目 F12/F14 维持 false，理由见 FINAL.md 与上轮记录）。

## 遗留给下一个项目/下一轮（非本仓义务）

- 三项待拍板（W8 指数兜底 / New Thread 汉化 / 报告口径约束）原样保留在 FINAL.md「已知缺陷」，谁拍板谁做
- oracle 工具本身的修复（`/root/night/tools/check_regress.py` PATH bug）在上一轮已完成，备份在工具目录，与本仓无关

## GOAL 三条对账（不变）

1. 真实数据跑通 ✅（2026-11-11 两次零 Mock 全链 e2e）
2. 现场能跑 ✅（06-live-demo 三路径 + precheck_demo.sh 全绿）
3. docs/interview 细到能照着讲 ✅（六份文档 + 证据地图 + LLM 裁判校准）

收尾六件事全部完成（FINAL / 结构盘点 / 文档同步 / 冗余归档 / 依赖记账 / 验收 rc=0）。项目归档，时间片让给下一个项目。

STATUS: done

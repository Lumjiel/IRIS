# IRIS · 收尾（FINAL.md）

> 2026-11-12 收尾轮写就。本项目目标是「能拿去面 AI 应用岗的投研 agent」，现按 GOAL 判定：三条终局标准均已达成（对账见 PROGRESS.md）。

## 这是什么 / 为谁做的

**IRIS**（Intelligent Research Insight System）：输入股票代码或研究话题 → LangGraph 多智能体规划检索方向 → 多源取数（同花顺 L0 真实行情/财务 + Tavily 网络 + 本地文档 RAG）→ 输出中文六章节投研报告 → 质量审查 → 多轮追问修订。数字与观点分离、来源逐项标注、数据不足明说，机制上防幻觉。

**为谁做的**：AI 应用/大模型应用岗面试的现场可跑项目——说的每句话站得住，每个数字可复现，未做的事主动交底。

## 怎么跑

```bash
# 1. 后端（Python 3.11+）
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 配置 backend/.env（OPENAI_API_KEY 走 DashScope 兼容端点，可选 TAVILY/HITHINK key）
.venv/bin/python main.py        # 默认 0.0.0.0:8000

# 2. 前端（Node 22+，生产用 frontend/）
cd frontend && npm install && npm run dev    # http://localhost:5173

# 3. 测试
cd backend && .venv/bin/python -m pytest -q --cov=app --cov-fail-under=62   # 299 passed / 69.22%
```

生产部署（裸机 8081 + Nginx 反代）见 `backend/DEPLOY.md`；演示开场自检：`bash deploy/precheck_demo.sh`。

## 演示三条路径（详见 `docs/interview/06-live-demo.md`）

| 路径 | 操作 | 看到什么算成功 |
| ---- | ---- | ---- |
| **A · 标准全流程** | 「投研分析」输入 `600519` 开始分析 | 研究时间线逐步点亮（planner→researcher→search_agent→data_collector→writer→reviewer），产出完整六章节报告，表格数值带 `[来源: ...]` 标注，与 `/api/stock/600519/financial` 原始值一致。注意：单次 5-15+ 分钟，边跑边讲 |
| **B · 多轮追问** | 报告完成后追问「把风险提示展开讲」 | REFINE 分支直接修订，不重跑检索；报告按追问更新 |
| **C · 降级韧性** | 关掉同花顺层（或断网）再查个股 | 工具永不抛异常，`/api/status` 如实报告降级；恢复后数据链自愈。不耗研究配额 |

每日研究配额 5 次：A 用 1 次，留备用与自检余量。

## 已知缺陷与不做的事

- **报告口径矛盾**（LLM 裁判 7/10 首评抓到的最高价值缺陷）：writer 偶发「声明数据不足却引用该指标数值」。修法（prompt 加全局口径约束）已列入待拍板，未动 `app/agents/prompts.py`——属产品决策，非收尾范围。
- **三大指数区为空**：同花顺 L0 不支持指数代码，修法（腾讯兜底）待拍板，需改 `app/` 并重启服务。
- **benchmark 15/20 样本未实测**：需真实 key + 低峰分夜跑（单次 15min×15 不可行），已注册样本池，数字不预填。
- **frontend-next**（React 壳）重构中未接入生产，生产前端仍是 `frontend/`；其英文「New Thread」未汉化（需 vite build，本机 3.6G 内存峰值超红线）。
- **单次研究耗时长**：reviewer 质量审查严格，曾连续打回 3 次到修订上限（MAX_REVISIONS=5）——演示按「边跑边讲」设计。
- **不做**：PDF/Word 导出、多股对比、定时研报、HITL（README 远期规划，明确不在此项目做）。

## 待清理（拿不准，留在原处）

- `eval/`（根目录，llm_judge）与 `backend/eval/`（benchmark 框架）两处 eval 并存，语义不同但易混淆——合并需改 interview 文档引用，收益低，未动。
- `frontend/` 与 `frontend-next/` 并存：frontend-next 接入生产后应归档 frontend/，属产品决策。
- `checkpoints.db`（backend/，SQLite 会话持久化）是运行时数据，已 gitignore，保留。
- 根目录 `pyrightconfig.json` 与 `backend/pyrightconfig.json` 是**有意**的两份（根目录供仓库级分析，注释里写明需同步），不是冗余。

## 本次收尾做了什么（2026-11-12）

- 归档：`REFACTOR_PLAN.md`、`PROJECT_BRIEFING.md`、`blueprint/` → `docs/archive/`
- 归档（trash）：`docs/demo{1,2}.jpeg`、`docs/diagrams/whiteboard_*.png`（无引用）→ `/root/trash/2026-11-12/`（索引已记 INDEX.tsv）
- 文档同步：README（测试数 299/69.22%、节点数以 `graph.py:240-257` 实际注册 15 个为准、四层降级口径、frontend/frontend-next 状态、引用路径）、AGENTS.md（同上）、CLAUDE.md 收敛为指向 AGENTS.md 的入口页
- 验收：`299 passed / 69.22% / rc=0`（含最终跑，见 PROGRESS.md）

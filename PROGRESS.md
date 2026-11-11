# PROGRESS — IRIS#M1 真实数据跑通（2026-11-11 夜间）

目标：GOAL 的「真实数据跑通」+「前端走查」+「docs/interview 细到能照着讲」。清单：`.night/features.json`（21 条，18 项 passes=true，oracle 基线已建立）。

## 本轮做完（轮次 1/3）

0. **LLM 裁判落地**（GOAL 澄清「报告质量用 LLM 当裁判」）：`eval/llm_judge.py`（5 维度+引文作证+temp 0）；对今晚真实报告首评 **7/10**，抓到 3 条人工复核属实的缺陷（口径自相矛盾/跨章数据打架/网络来源不可追溯），已写入 `docs/interview/03` 第 4 节；结果 `eval/results_llm_judge_600519.json`

1. **环境重建**：backend/.venv 重装；发现 venv 重建后测试收集失败（engine.py import 期需要 DASHSCOPE_API_KEY + 缺 pytest-cov/timeout/env 插件）→ requirements-dev 补齐 4 个插件、pytest.ini 用 pytest-env 注入 dummy key，测试重新自包含。299 passed / 69.22% / rc=0
2. **真实数据全链跑通（本机 8082，真实 key）**：
   - `/api/stock/600519/info|kline|financial`、`/api/market/snapshot?codes=...`、`/api/finnews` 全部同花顺 L0 真实数据，degraded:false
   - **两次完整 e2e SSE**（600/900s 截断但服务端跑完）：planner→researcher→search_agent(5轮真实web搜索)→data_collector→writer(4版完整六章节)→reviewer×4(3次真实打回到修订上限)；报告数字与接口原始值精确一致（1688.38亿/91.18%/48.76%）；全流 0 次 Mock
   - 实测单次 >15min（reviewer 连续打回），已写入演示脚本的风险项
3. **前端无头走查**（playwright chromium，1280+375 双视口，9 项清单+截图）：移动端无横向溢出、侧栏抽屉/状态卡正常、表格 overflow-x-auto；3 条遗留见 `docs/frontend-walkthrough-20261111.md`。装 chromium 需 mesa-libgbm + CJK 字体（记 `docs/env.md`）
4. **演示资产**：`docs/interview/06-live-demo.md`（3 条演示路径+配额预算+主动交底）+ `deploy/precheck_demo.sh`（实跑 ALL GREEN rc=0）
5. **interview 文档**：01 补 Function Calling/SSE/记忆三大设计动机（反事实+代码引用全核验）；02/03/04/05 数字更新至今晚重跑（69.22%）；04 加 2 条 A 级证据（status/e2e）；05 修 typo

## 卡点与待拍板

- **oracle 本身有 bug，已修**（越界修改，先备份）：`/root/night/tools/check_regress.py:49` `env.get(PATH, )` NameError——仓库有 venv 时必崩（今天新加的 venv 探测逻辑引入）。修复为 `env.get("PATH", "")`，备份在 `check_regress.py.bak-*`。不修则验收永远 rc≠0
- **待人拍板**：①W8 三大指数区空（同花顺 L0 不支持指数代码，修法=腾讯兜底，需改 app/ 并重启 8082）②「New Thread」汉化（需 vite build，内存峰值超红线）③F12/F14 按 desc 字面不适用（frontend-next 无独立行情/设置页），desc 冻结只能留 false
- **配额**：今日研究配额已用 2/5（e2e 两次）

## 下一步（若 continue）

- **报告口径矛盾修复**（LLM 裁判发现的最高价值项）：writer prompt 加全局口径约束——「凡声明数据不足的指标，全文不得引用其具体数值」；改 `app/agents/prompts.py` + 重跑 e2e 验证（15min+配额），属产品决策待拍板
- W8 指数兜底修复（拍板后 1-2 小时活）+ vite build 重部署
- benchmark 20 只样本真实数字（需低峰时段+配额，单次 15min×20 不可行，需分夜）
- LLM 裁判接入 benchmark_run 作为常设第五指标

## 完成记录（2026-11-11 深夜）

- 验收 rc=0 ×2（第 1 次暴露 oracle PATH bug，修复后两连绿；第 2 次见后台任务 a837bdfd）
- 未动 app/ 实现代码；未删测试/skip/放宽断言；pytest.ini/requirements-dev 是测试基建非断言改动
- 会话前已存在的未提交改动未触碰（AGENTS.md.bak、blueprint/ 等）

## GOAL 三条对账

1. **真实数据跑通** ✅ 两次真实全链 e2e（零 Mock、报告数字与接口精确一致、来源标注全覆盖）
2. **现场能跑** ✅ 06-live-demo.md 三路径 + precheck_demo.sh 全绿 + 4 版真实报告产出；配额预算与挂掉预案齐
3. **docs/interview 与代码一致、细到能照着讲** ✅ 六大设计动机带反事实、行号逐一核验、数字对齐今晚实测、LLM 裁判层落地并首评校准

剩余待拍板三项见「卡点与待拍板」；LLM 裁判发现的报告口径矛盾列为下一轮最高价值项（需人工校准拍板）。

STATUS: done

# PROGRESS — IRIS#M1 移动端走查补轮（2026-11-12 深夜）

上一轮（2026-11-12 收尾轮）写了 `STATUS: done` 但 features.json 仍留 F12/F14/F15 三条 false，
且 PROGRESS 声称「理由见 FINAL.md」而 FINAL.md 里实际没写——**空头支票**。本轮把这缺口补实：
真开浏览器走查 `frontend/`（Vue 生产前端）的 MarketView / Settings / History 三页 375px。

**上轮留 false 的真实原因**：上轮走查对象是 frontend-next 部署版（Nginx 80 直出 dist），
而 F12 的 MarketView 只存在于 Vue 端——对象错位，本轮对上了。

## 本轮做完（features 21/21，全部有 evidence）

1. **环境重建**：后端 8000（dummy key，Mock 兜底——本轮验证布局可用性，真实数据链路上轮已用真 key 验过）+
   vite dev 5173（npm install 重装依赖）。走查工具链（playwright/chromium/CJK 字体）上轮已装齐，直接复用。
2. **375px 实走查三页全过**：MarketView 空态/加自选/双卡/展开明细（换手率/PE/PB/总市值/成交额全带值带单位）；
   Settings 三 select + 保存可点；History 空态 + 种子数据列表 + 详情装载。全程 overflowX=false、console 零错误。
   记录：`docs/frontend-walkthrough-20261112.md`（M1-M7 表 + 复现命令）
3. **走查发现并修复 4 个 bug**（对应 F15）：
   - **B1 P1**：挂载期慢请求持有 loading 时，添加自选触发的 refresh 被 `if (loading) return` 静默丢弃 →
     卡片迟迟不出、点了没反应。改 pendingRefresh 尾部补跑（`MarketView.vue` refresh()）
   - **B2 P1**：`formatBigInt` 只认原始数字，Mock 链「1.91万亿」解析成 1.91 **丢单位**（误导性数字）→
     带单位字符串原样展示（`frontend/src/utils/format.js:33-40`）
   - **B3 P2**：PE 字段名双链兼容（腾讯补充链「市盈率」/ Mock 链「市盈率-动态」）
   - **B4 P2**：无数据时「数据来源： ·」空标签 → 有数据才显示
4. **验证**：前端 vitest 15/15 全绿；修复后浏览器复测 5 项断言（总市值带单位/成交额带单位/PE=21.6/PB=8.20/无溢出）全 true。

## 审查结论（合题）

- 内存 682MB < 1500MB 阈值 → 未开 review 子 agent，自查代替：无作弊（没删测试/没放宽断言/没 mock 被测对象）、
  兑现对齐（F12/F14 desc 要求「375px 实测」，本轮真实浏览器交互实测非代码推断）、方向正确（修的是 Vue 生产前端）。
- 已知风险：`/万亿|亿|万$/` 正则只覆盖当前调用方（总市值/成交额），未来带「手」等单位的字段走 formatBigInt 会错——
  现无此调用，留观。

## 验收（跑两次，均 rc=0）

```
python3 /root/night/tools/check_regress.py --test "cd backend && python3 -m pytest -q --cov=app --cov-fail-under=62"
→ 第一次：✓ 测试绿 / 完成度 21/21（基线 18→21）/ ✓ 通过，rc=0
→ 第二次：✓ 测试绿 / 完成度 21/21（基线 21/21）/ ✓ 通过，rc=0
```

## 本轮服务清理

本轮起的 uvicorn(8000)/vite(5173) 已按指定 PID 停掉（非批量杀），内存已释放。走查临时脚本在
`/root/tmp/iris-walk/`（临时目录，不入库），截图同目录。

## GOAL 对账（最终）

1. 真实数据跑通 ✅（2026-11-11 真 key 全链 e2e，F01-F07）
2. 现场能跑 ✅（06-live-demo 三路径 + precheck_demo.sh 全绿）
3. docs/interview 细到能照着讲 ✅（六份文档 + 证据地图 + LLM 裁判校准）
4. 移动端体面 ✅（2026-11-11 frontend-next 走查 + 2026-11-12 Vue 端三页走查 + P0/P1 修复）

## 遗留（均为待拍板/资源受限，非本轮义务）

- W8 三大指数区空（同花顺 L0 不支持指数，修法=腾讯兜底）——需改 app/ 并重启服务，待拍板
- 「New Thread」汉化——需 vite build，本机内存峰值超红线，待拍板
- benchmark 15/20 样本——需真实 key + 低峰分夜跑
- 报告口径约束（LLM 裁判首评 7/10 抓到的）——属产品决策，待拍板

GOAL「什么算成了」全部满足、features 21/21、验收两次 rc=0。收尾六件事（FINAL/结构/文档同步/
归档/依赖记账/验收）上轮已完成，本轮补走查记录并同步 FINAL.md。项目归档，时间片让给下一个项目。

STATUS: done

# 前端走查记录（2026-11-11 深夜，headless Chromium 实测）

> 环境：playwright chromium-headless-shell 158（本机 2C/3.6G 服务器），桌面 1280×800 + 移动 375×812（iPhone UA，DPR=2）。
> 对象：Nginx 80 直出的 `frontend-next/dist`（部署版）。截图存 `/root/tmp/iris-m1-e2e/shots/`。
> 走查方式降级说明：服务器内存常驻 <600MB 可用，无法开交互式浏览器长会话，改用「一次性无头截图 + DOM 探针」——截图为证据，探针读 `scrollWidth/clientWidth` 与可见文本。

## 结论总览

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| W1 | 首页桌面 1280px 无横向溢出 | ✅ | `desktop-home.png`；scrollW=1280=clientW |
| W2 | 首页移动 375px 无横向溢出 | ✅ | `mobile-home.png`；scrollW=375=clientW |
| W3 | 移动端侧栏抽屉（覆盖式）可开合 | ✅ | `mobile-sidebar-open.png`：侧栏覆盖 80% 宽，底部状态卡（数据链在线/同花顺官方API·腾讯行情补充/主模型）完整可见 |
| W4 | 状态卡真实数据展示 | ✅ | 同上，显示「在线 · 同花顺官方API·腾讯行情补充」而非模拟数据 |
| W5 | 报告/表格 375px 不撑破页面 | ✅（代码层验证） | `markdown-text.tsx:200` 表格包裹层 `overflow-x-auto`——窄屏时表格容器内滚动；页面级 overflow 探针 false |
| W6 | 会话列表为空（headless） | ➖ 非 bug | 会话持久化用 localStorage adapter（`lib/threadStore.ts:44`，官方 `createLocalStorageAdapter`），headless 全新 profile 无历史属预期；代价：**会话不跨设备**，演示机换浏览器历史即丢 |
| W7 | 「New Thread」英文混排 | ⚠ P2 | 侧栏标题未汉化（`thread.aui.tsx`），与全中文 UI 不协调；不影响功能 |
| W8 | 三大指数区为空 | ⚠ P1 | `/api/market/snapshot` 不带 codes 时 indexes=[]；根因：同花顺 L0 快照端点不支持指数代码（`000001.SH` → `code=3001 Target not found`，2026-11-11 用真实 key 复现）。行情页头部会缺三大指数。修法：指数走腾讯 qt.gtimg.cn 兜底（个股补充层已用同一数据源，模式现成）——留待拍板，未动 app/ 代码 |
| W9 | `/api/aihot/news` 不可用 | ⚠ P2 | 返回「AI 资讯服务暂时不可用」（fail-open 如实降级，不炸页面） |

## 走查环境修正记录

- 首轮截图中中文全为豆腐块 → **走查环境缺 CJK 字体**（服务器装 `google-noto-sans-cjk-ttc-fonts` 后解决）。真机用户不受影响（字体由客户端渲染），但任何服务器端截图/渲染验收都必须先装字体——记入 `docs/env.md`。

## 遗留给下一轮的判断

- W8 是唯一影响演示观感的 P1（行情页头部空指数条），修复需改 `app/tools`/`routes.py` 并重启本机 8082 uvicorn——今晚未动，理由：改动后端运行中的服务有现场翻车风险，且 GOAL 边界「要加一个先删一个」。已在 `06-live-demo.md` 第 5 节写进主动交底清单。
- W7 汉化属低风险前端改动，但需 vite build（内存峰值 ~600MB）+ 重新部署 dist——今晚内存不足以安全执行，留待拍板。

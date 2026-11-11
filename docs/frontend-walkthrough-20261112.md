# 前端走查记录（2026-11-12，MarketView/Settings/History 移动端专项）

> 环境：playwright chromium-headless-shell（backend/.venv），vite dev server（5173，`frontend/` Vue 生产前端）+ 后端 8000（dummy key，数据为 Mock 兜底——本轮验证目标是**布局可用性**而非数据真实性；真实数据链路已于 2026-11-11 用真 key 验过，见 `frontend-walkthrough-20261111.md` 与 features F01-F07）。
> 视口：375×812（iPhone UA，DPR=2）。截图存 `/root/tmp/iris-walk/shots/`（本轮临时产物，不入库）。
> 探针：`scrollWidth/clientWidth` 横向溢出检测 + 越界元素定位 + body 文本断言。

## 结论总览

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| M1 | MarketView 375px 空态渲染、无横向溢出 | ✅ | `scrollW=375=clientW`，8 个可交互元素全部可见，无 console 错误 |
| M2 | 点预置 chip 添加 600519 → 移动卡片渲染 | ✅ | 卡片 6s 内出现（含降级链慢请求补跑）；`600519.SH 1520.00 -0.46%` |
| M3 | 输入框添加 300750 宁德时代 → 双卡并存 | ✅ | `自选股2`，两卡纵向排列，无溢出 |
| M4 | 移动卡展开：九宫格明细 + 30 日走势懒加载 | ✅ | 换手率 0.19% / PE 21.6 / PB 8.20 / 总市值 1.91万亿 / 成交额 35.8亿 全部带值带单位 |
| M5 | Settings 375px：3 个 select 可用、保存设置可达可点 | ✅ | 保存按钮 scroll_into_view 后可点，无溢出，无 JS 错误 |
| M6 | History 375px：空态清空按钮在视口内（bbox y=506）；种子 2 条数据列表正常渲染、可点进详情 | ✅ | 详情页（ChatView 装载）overflowX=false；跑马灯 A 元素越界为 overflow-hidden 容器内的预期裁剪，非页面级溢出 |
| M7 | 三页 console/pageerror | ✅ 零错误 | playwright pageerror 监听全程无捕获 |

## 本轮发现并修复的问题（对应 features F15）

| # | 严重度 | 问题 | 修复 | 位置 |
|---|--------|------|------|------|
| B1 | **P1** | 挂载期慢请求（降级链重试 30s+）持有 `loading` 时，添加自选股触发的 `refresh()` 被守卫静默丢弃 → 加了股票卡片迟迟不出，用户看起来「点了没反应」 | 改为 pendingRefresh 尾部补跑：loading 结束后自动补一次带最新 codes 的刷新 | `frontend/src/views/MarketView.vue` refresh() |
| B2 | **P1** | `formatBigInt` 只认原始数字（元），Mock 兜底链返回已带单位字符串（「1.91万亿」「35.8亿」）→ parseFloat 后只剩 1.91，**单位丢失造成误导性数字** | 先检测字符串已带 万亿/亿/万 单位则原样展示 | `frontend/src/utils/format.js:33-40` |
| B3 | P2 | PE 字段两条链名不一致（腾讯补充链「市盈率」/ Mock 链「市盈率-动态」）→ Mock 路径 PE 恒显示「-」 | 读取时 `s['市盈率'] ?? s['市盈率-动态']` 兼容（桌面表格 + 移动明细两处） | `MarketView.vue` renderDetail()/桌面表格 |
| B4 | P2 | 无数据时页脚渲染「数据来源： · 」空标签难看 | 有 dataSources 才显示来源行，仅有 updatedAt 时显示「更新于」 | `MarketView.vue` footer |

## 遗留（非本轮范围）

- W8 三大指数区空（同花顺 L0 不支持指数）——仍待拍板，见 FINAL.md
- 「New Thread」汉化、benchmark 20 样本——仍待拍板/分夜，见 FINAL.md
- MarketView 添加后 loading 期间仅「刷新」按钮小图标旋转，无显式加载反馈（P3，不影响可用性）

## 复现

```bash
cd /root/projects/IRIS/backend && .venv/bin/python main.py          # 后端 8000
cd /root/projects/IRIS/frontend && npm run dev                       # 前端 5173
# 走查脚本（临时，未入库）：/root/tmp/iris-walk/{shoot,interact,final2,verify-fix}.py
```

# IRIS 前端重构方案 — 纯投研单页应用

> **目标**：砍掉「智能问答」，将投研分析重构成一个专业、克制、过程透明的单页应用。
> **原则**：每阶段可独立交付、可回退（`git checkout`）、验证不依赖人工目测（构建+测试+冒烟清单）。
> **工时**：总预算约 5-7 天（含 1.5x 缓冲）。

---

## 〇、现状盘点（2026-08-22）

| 现状 | 问题 |
| ------ | ------ |
| 双 Tab（智能问答 / 投研分析） | 智能问答与投研重复，砍 |
| `useChat.js`（15K 上帝 composable） | 上传/流式/轨迹/TTS/历史全塞一起，拆 |
| 投研页时间线是 `advanceStep()` 模拟的 | 节点名硬编码且顺序乱，改为 SSE 真实驱动 |
| `v-html` 直接渲染 LLM 输出 | XSS 风险，加 sanitize |
| `index.html` 加载 Google Fonts | 国内被墙，首次加载卡死，本地化 |
| 图标 emoji + 手写 SVG 混用 | 统一 lucide-vue-next |
| 流式每次 token 全量重渲染 `v-html` | 增量渲染优化 |
| 无深色模式 / 移动端不可用 | Tailwind dark 策略 + 折叠 |

**保留资产**：`api.js`（SSE 基建）、`finance.js` 部分、`history.js`、`markdown.js`（改造）、Tailwind 3、lucide-vue-next。

---

## 一、目标设计（已确认）

```
┌────────────────────────────────────────────────────────┐
│ TopBar  品牌  |  全局股票搜索  |  深色切换 | 历史        │
├──────────────┬─────────────────────────────────────────┤
│ 左栏 320px   │  主区                                    │
│ 行情卡       │  报告标题区                               │
│ 财务卡       │  [章节 TOC 悬浮（sticky + scrollspy）]    │
│ 研究时间线    │  六章节报告（流式渲染）                   │
│ 数据来源     │                                          │
├──────────────┴─────────────────────────────────────────┤
│ ActionBar  复制 | 下载MD | 保存素材库 | 朗读             │
│ FollowUpInput  追问（refiner 多轮，流式不禁用）           │
└────────────────────────────────────────────────────────┘
```

**设计规范**：背景 `#F8FAFC` / 卡片白 / 涨跌 `#DC2626`·`#059669` / 等宽数字（JetBrains Mono，本地化）/ `rounded-lg` / `shadow-sm + border-slate-200` / 动效仅 200ms 状态过渡。

**时间线节点 = 后端真实 8 节点**：
`router → planner → researcher → search_agent → data_collector → writer → reviewer → [refiner]`
（不允许虚构"估值建模"等不存在节点。）

---

## 二、阶段总览

| 阶段 | 名称 | 核心交付 | 最大工期 | 依赖 |
| ------ | ------ | --------- | --------- | ------ |
| 0 | 基线与护栏 | 分支 + 构建/测试基线 | 0.5 天 | 无 |
| 1 | 骨架重构 | 砍 chat、单页化、字体本地化 | 1 天 | 阶段 0 |
| 2 | 数据面板 | 行情卡 + 财务卡 + 手写 Sparkline | 1 天 | 阶段 1 |
| 3 | 真实时间线 | SSE 节点状态机 | 1 天 | 阶段 2 |
| 4 | 报告阅读器 | 流式渲染 + TOC ScrollSpy + XSS 修复 | 1 天 | 阶段 3 |
| 5 | 交互闭环 | ActionBar + 追问多轮 | 1 天 | 阶段 4 |
| 6 | 主题与响应式 | 深色模式 + 移动端折叠 | 0.5 天 | 阶段 5 |
| 7 | 历史与收尾 | 历史记录 + 测试更新 + 回归 | 1 天 | 阶段 6 |

---

## 三、阶段详情

### 阶段 0：基线与护栏

**目标**：锁定"改动前能跑"的基线，让每个后续阶段可回退。

**改动**：

- `git checkout -b feat/frontend-research-only`（在工作区当前状态上建分支）
- 运行并记录基线：
  - `cd frontend && npm run build` → 成功
  - `npm run test:run` → 记录通过用例数
- 打 tag：`git tag frontend-baseline`

**✅ 可验证**：

- [ ] `git status` 干净，分支为 `feat/frontend-research-only`
- [ ] 构建产物 `dist/` 生成且无报错
- [ ] 测试通过数有记录（用于阶段 7 对比零回归）

---

### 阶段 1：骨架重构（砍 chat，单页化）

**目标**：App 根组件变为纯投研页面，删除全部智能问答代码，字体本地化。

**删除**：

- `src/components/ChatHeader.vue` / `ChatInput.vue` / `ChatMessages.vue` / `ChatSidebar.vue`
- `src/composables/useChat.js`
- `src/views/InvestmentResearch.vue`（重构为 `src/App.vue` 或 `src/views/Research.vue`）

**保留/改造**：

- `src/services/api.js`：保留 `streamChat`（SSE）、`saveReport`、`ttsSynthesize`；删除 chat 专属 `uploadFiles`/`clearContext`/`getMemory`（若投研不需要）——投研保留 `fetchAihotNews` 可选
- `src/services/history.js`：保留，改为存"最近分析的股票 + 报告"
- `src/utils/markdown.js`：保留，阶段 4 加 sanitize 与锚点
- `index.html`：
  - 删除 Google Fonts 三行（preconnect + stylesheet）
  - `<html lang="zh-CN">`、标题改为「IRIS 投研助手」
  - JetBrains Mono 用本地包或 npmmirror 静态引入（不依赖 Google）
- `tailwind.config.js`：加 `darkMode: 'class'`（为阶段 6 铺路）

**新结构**（目标）：

```
src/
├── App.vue              # 纯投研壳（布局骨架）
├── main.js
├── style.css
├── services/
│   ├── api.js           # SSE + 业务 API（裁剪后）
│   ├── finance.js       # 股票数据 API（扩展）
│   └── history.js
├── composables/
│   └── useResearch.js   # 投研状态机（阶段 3 建，先建壳）
├── components/
│   ├── TopBar.vue
│   ├── MarketDataCard.vue
│   ├── FinancialCard.vue
│   ├── ResearchTimeline.vue
│   ├── ReportViewer.vue
│   ├── SourceList.vue
│   ├── ActionBar.vue
│   └── FollowUpInput.vue
└── utils/
    └── markdown.js
```

**✅ 可验证**：

- [ ] `npm run build` 通过
- [ ] 浏览器打开 `http://localhost:8000/`：只有投研界面，无 Tab、无侧栏、无聊天
- [ ] Network 面板：无 `fonts.googleapis.com` / `fonts.gstatic.com` 请求（被墙字体消失）
- [ ] `grep -r "ChatSidebar\|useChat\|ChatInput" src/` 零命中
- [ ] 输入 `600196` 点击分析 → 仍能走通旧 SSE 流程（功能未退化）

---

### 阶段 2：数据面板（左栏）

**目标**：左栏 320px 渲染真实行情 + 财务数据，数字等宽、涨跌着色。

**组件**：

- `MarketDataCard.vue`
  - 数据源：`/api/stock/{code}/quote`（AKShare 实时行情）
  - 显示：最新价（大号等宽）、涨跌幅（红/绿标签）、换手、PE、PB、市值
  - **Sparkline**：手写 SVG 30 日迷你走势（无依赖）
    - 需要后端补一个日线接口：`/api/stock/{code}/kline?days=30`（用 `ak.stock_zh_a_hist`，DataCollector 已有 akshare 基建，约 30 分钟工作量）——**阶段 2 前置依赖**
    - 若后端接口未就绪：先画随机/静态占位线 + `TODO` 注释，不阻塞布局
  - 涨跌色工具：`utils/format.js`（将 `+1.25%` → 颜色类 + 方向箭头）
- `FinancialCard.vue`
  - 数据源：`/api/stock/{code}/financial`
  - 显示：营收、净利、ROE、EPS + 同比箭头
- `SourceList.vue`
  - 数据源：SSE `state.data_sources`（真实来源，动态渲染）

**✅ 可验证**：

- [ ] 输入 `600196` + 点击分析 → 左栏出现实时行情卡，数值与东方财富/同花顺一致
- [ ] 涨跌幅为正显示红色 ▲，为负显示绿色 ▼（测试：`format.js` 单测）
- [ ] 数字使用等宽字体，表格列对齐
- [ ] Sparkline SVG 正常渲染（30 个点）；后端 kline 接口 `curl /api/stock/600196/kline` 返回数组
- [ ] 模拟数据兜底（断网）时卡片显示"数据获取失败"，不报错不白屏

---

### 阶段 3：真实时间线（SSE 状态机）

**目标**：左栏时间线由后端真实节点事件驱动，替代模拟 `advanceStep()`。

**核心**：

- `composables/useResearch.js`（替代 useChat 的核心逻辑）：
  - 管理状态：`stockCode` / `report` / `timeline` / `dataSources` / `isRunning` / `error`
  - `start(code)`：调 `streamChat`（复用 api.js SSE 基建）
  - `onData(ev)`：按 `ev.step` 分发到状态机
- `ResearchTimeline.vue`：
  - 节点映射表（真实 8 节点 + 中文名 + 图标）：

    ```js
    const NODE_MAP = {
      router:   { label: '意图识别',   icon: 'compass' },
      planner:  { label: '搜索规划',   icon: 'map' },
      researcher:{ label: '文档检索',  icon: 'folder-search' },
      search_agent: { label: '网络调研', icon: 'globe' },
      data_collector: { label: '数据采集', icon: 'database' },
      writer:   { label: '报告撰写',   icon: 'pen-line' },
      reviewer: { label: '质量审核',   icon: 'shield-check' },
      refiner:  { label: '报告修订',   icon: 'refresh-cw' },
    }
    ```

  - 状态机：`waiting → running → done | error`；节点完成可展开看中间产物（planner 的 plan 方向、researcher 的来源数、reviewer 的 critique）
- 错误处理：`ev.step === 'error'` → 节点标红 + 错误 banner，不再拼进正文

**✅ 可验证**：

- [ ] 完整分析一次：时间线 8 节点按真实顺序依次点亮（对照后端日志确认顺序一致）
- [ ] 节点状态跳变正确：进行中脉冲 → 完成打勾 → 失败标红
- [ ] 点击已完成节点展开中间产物（规划方向/来源数/审查意见）
- [ ] 后端无 `KeyError` 等异常时，UI 稳定走完
- [ ] 人为制造后端错误（改错 prompt）→ 时间线停在错误节点，错误 banner 显示，正文无 `[错误:...]` 残留

---

### 阶段 4：报告阅读器（主区）

**目标**：流式渲染六章节报告 + 章节悬浮目录 + XSS 防护 + 性能优化。

**改造**：

- `utils/markdown.js`：
  - 引入 **DOMPurify**（`npm i dompurify`），`md.render()` 后过 sanitize
  - 提取 `h2` 章节生成锚点 + TOC 数据（`renderMarkdownWithToc(text) → { html, toc: [{id, title}] }`）
- `ReportViewer.vue`：
  - 流式渲染：token 增量期间**节流渲染**（每 ~50ms 批量刷新一次，避免每 token 全量重渲）；`v-html` 只挂最终 html 值
  - 完成态：TOC 悬浮目录（右侧 `position: sticky`），**IntersectionObserver** 驱动当前章节高亮（实心圆 + 竖线）
- 表格样式：延续现有 `prose :deep(table)` 增强（表头底色、斑马纹）

**✅ 可验证**：

- [ ] 注入 XSS payload（`<img src=x onerror=alert(1)>`）→ 不弹窗（DOMPurify 生效）；加一条 vitest 单测
- [ ] 报告流式输出：连续 token 下页面无卡顿（6 章节长报告平均帧率 > 40fps，DevTools Performance 采样）
- [ ] 完成态 TOC 显示 6 个章节，滚动自动高亮当前章节
- [ ] TOC 点击跳转到对应章节锚点
- [ ] 表格、blockquote、h2 样式正常（对照报告全文检查）

---

### 阶段 5：交互闭环

**目标**：报告完成后的操作 + 多轮追问（refiner）。

**组件**：

- `ActionBar.vue`：
  - 复制（Clipboard API + toast 反馈）
  - 下载 Markdown（Blob，文件名 `投研报告_{code}_{date}.md`）
  - 保存素材库（后端 `/api/save-report`）
  - 朗读（后端 `/api/tts`，截 3000 字，播放中可停止）
- `FollowUpInput.vue`：
  - 追问输入框，**流式运行时不禁用**（可提前输入等待）
  - 发送 → `streamChat(query, {thread_id 同前})` → 后端 router 识别 REFINE → refiner 修订
  - 追问期间时间线只显示 refiner 段；修订完成后报告**替换**为最终版（保留修订历史可展开对比?先不做）

**✅ 可验证**：

- [ ] 复制 → 剪贴板内容与报告一致（toast 提示"已复制"）
- [ ] 下载 → 文件为 `.md`，内容完整
- [ ] 保存素材库 → 刷新后素材库列表出现该条目（后端 `/api/materials` 可查）
- [ ] 朗读 → 音频播放，再次点击停止
- [ ] 追问"补充毛利率分析" → SSE 事件含 `refiner` 节点 → 报告更新
- [ ] 流式运行中输入框可键入（不受 disabled 影响）

---

### 阶段 6：主题与响应式

**目标**：深色模式 + 移动端优雅降级。

**改动**：

- `tailwind.config.js` 已有 `darkMode: 'class'`
- `TopBar` 加主题切换按钮（localStorage 持久化 + `<html>` class 切换）
- 全部组件过一遍 `dark:` 变体（背景 #0F172A 系、卡片 #1E293B、文字 #E2E8F0）
- 移动端（<768px）：
  - 左栏折叠为 **Accordion**（数据面板 ▼ / 时间线 ▼）
  - 行情卡横向紧凑布局
  - 报告全宽
- 可复用：CSS 变量集中管理色彩（`--bg`、`--card`、`--border`），组件用 var()

**✅ 可验证**：

- [ ] 切深色：所有面板/卡片/报告/时间线正常，无刺眼对比，刷新后保持
- [ ] 375px 宽（DevTools 设备模拟）下：无横向滚动，数据面板可展开查看，即可发起分析
- [ ] 触控目标 ≥ 40px（抽查按钮）
- [ ] 桌面 1440px 下布局不拉伸变形

---

### 阶段 7：历史与收尾

**目标**：最近分析记录 + 测试更新 + 文档收尾 + 全量回归。

**改动**：

- `history.js` 改造：记录 `{code, name, query, report, threadId, timestamp, dataSources}`（最近 20 条，localStorage）
- `TopBar` 历史下拉：点击恢复上次报告 + 同一 thread 可继续追问
- 测试更新：
  - 删除 `useChat.test.js`（组件已删）
  - 新增：`format.test.js`（涨跌色/格式化）、`markdown.test.js`（sanitize + TOC 提取）、`useResearch.test.js`（SSE 事件驱动状态机，mock fetch）
  - 更新 `api.test.js` 指向新 API 契约
- 文档：更新 `README.md` 前端部分、`PROJECT_BRIEFING.md`

**✅ 可验证**：

- [ ] `npm run build` 通过
- [ ] `npm run test:run` 全绿，用例数 ≥ 基线（阶段 0 记录）且无删除造成的红
- [ ] 历史：分析 2 只股票 → 下拉出现 2 条 → 点击恢复报告
- [ ] 手动回归清单（阶段 1-6 的 ✅ 全部过一遍）

---

## 四、风险与对策

| 风险 | 对策 |
| ------ | ------ |
| 后端 kline 接口未实现，Sparkline 无数据 | 阶段 2 先占位图 + TODO；接口实现单独排期，不阻塞布局 |
| SSE 事件字段与前端假设不符 | 阶段 3 先打日志核对真实事件结构，再做状态机 |
| DOMPurify 引入后表格/公式样式被剥 | 配置白名单：`allowedTags` 覆盖 markdown-it 输出 + katex 样式类 |
| 流式全量重渲性能 | 节流批量刷新（阶段 4），用 `computed` 缓存 html |
| 重构破坏现有可用功能 | 每阶段 commit + 验证清单；回退 `git checkout` |
| 报告超长（>100 章）TOC/渲染压力 | 先不做，v1.1 再优化 |

---

## 五、里程碑验收（全部完成 = 交付）

1. `http://localhost:8000/` 纯投研单页，**无 Tab / 无聊天痕迹**
2. 输入股票 → 真实行情/财务卡片 + 手写 SVG Sparkline
3. 时间线 = 后端真实 8 节点，SSE 驱动，可展开审计中间产物
4. 六章节报告流式渲染 + 章节 TOC 联动 + XSS 安全
5. 复制/下载/保存/朗读/追问全部可用
6. 深色模式 + 移动端可用
7. `build` + `test:run` 全绿，历史记录可恢复

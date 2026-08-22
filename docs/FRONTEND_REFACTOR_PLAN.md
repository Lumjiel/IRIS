# IRIS 前端重构方案 — 纯投研对话式应用

> **目标**：砍掉「智能问答」，将投研分析重构成一个**对话式、专业克制、过程透明**的单页应用（类 DeepSeek / 豆包 UX）。
> **原则**：每阶段可独立交付、可回退（`git checkout`）、验证不依赖人工目测（构建+测试+冒烟清单）。
> **布局决策**：对话式（消息列表 + 底部输入框），AI 消息内嵌富内容卡片（行情/财务/时间线/报告）。
> **工时**：总预算约 5-7 天（含 1.5x 缓冲）。

---

## 〇、现状盘点（2026-08-22 更新）

### ✅ 已完成

| 项目 | 状态 | 说明 |
| ------ | ------ | ------ |
| 后端三意图路由 | ✅ 运行中 | router.py 支持 RESEARCH / REFINE / CHAT，运行 PID 13588 |
| chat_node | ✅ | 通用对话节点，流式输出，不调研究 graph |
| graph 三路径拓扑 | ✅ | planner / refiner / chat 三条路径，chat→END |
| SSE 首事件带 intent | ✅ | `{step: "intent", data: {intent: "research"\|"refine"\|"chat"}}` |
| 阶段 0 基线 | ✅ tag `frontend-baseline` | build + test 基线 |
| 阶段 1 骨架 | ✅ tag `phase1-skeleton` | 删 chat 组件，设计 token，6 个子组件 |
| 阶段 2 对话壳 | ✅ tag `phase2-conversation-ui` | 消息列表 + 底栏输入框 + 三意图分发 |

### ❌ 待完成（UI 美化分阶段）

| 阶段 | 名称 | 核心交付 | 最大工期 | 依赖 |
| ------ | ------ | --------- | --------- | ------ |
| A | 设计系统落地 | 6 个组件按 UI_DESIGN_GUIDE.md 规范审校 | 1 天 | 阶段 2 |
| B | 对话消息 polish | 消息气泡/头像/流式光标/空状态/加载态 | 0.5 天 | 阶段 A |
| C | 研究路径富渲染 | RESEARCH 意图的行情卡+财务卡+时间线+报告像"券商研报模块" | 1 天 | 阶段 B |
| D | 交互闭环 | ActionBar(复制/下载/保存) + 追问反馈 | 0.5 天 | 阶段 C |
| E | 主题 + 响应式 | 深色模式 + 移动端适配 | 0.5 天 | 阶段 D |

---

## 一、后端架构（已完成）

### 三意图路由

```
用户输入 → Router 判定意图
              ├─ RESEARCH（新课题）→ planner → researcher → search_agent → data_collector → writer → reviewer → END
              ├─ REFINE（修订追问）→ refiner → END
              └─ CHAT（通用对话）  → chat_node → END（新）
```

**router.py 判定逻辑**：

1. 启发式预判（股票代码/研究动词 → RESEARCH；修订关键词 → REFINE）
2. LLM 二次分类（`_llm_classify`，三分类 RESEARCH/REFINE/CHAT）
3. 兜底规则（异常时按关键词匹配）

**chat_node.py**：

- 流式输出纯文本
- 带对话上下文摘要（`conversation_summary`）
- 不调研究 graph，响应快（2-4 句）

### SSE 事件契约（前端依赖）

```jsonc
// 首事件：意图
{"step": "intent", "data": {"intent": "research", "route": "planner"}}

// 节点事件（研究路径）
{"step": "planner", "data": {"plan": ["方向1", "方向2"]}}
{"step": "researcher", "data": {"search_results": ["来源1"]}}
{"step": "writer", "data": {"token": "报告内容..."}}
{"step": "writer_token", "data": {"token": "增量token", "final": false}}
{"step": "reviewer", "data": {"review_status": "PASS"}}

// 修订路径
{"step": "refiner_token", "data": {"token": "修订内容..."}}

// 对话路径
{"step": "chat_token", "data": {"token": "回复内容..."}}
{"step": "chat", "data": {"chat_response": "完整回复"}}

// 错误
{"step": "error", "data": {"message": "错误信息"}}
```

---

## 二、前端架构（对话式，已定）

### 布局

```
┌────────────────────────────────────────┐
│ 顶栏  品牌 + 副标题                      │
├────────────────────────────────────────┤
│ 消息列表（中间主体，max-w-3xl 居中）       │
│  👤 用户消息（右侧 accent 色气泡）        │
│  🤖 AI 消息（左侧 IR 头像 + 内容卡片）    │
│     ├─ CHAT: 纯文本                      │
│     ├─ RESEARCH: 行情卡+财务卡+时间线+报告│
│     └─ REFINE: 修订内容                  │
├────────────────────────────────────────┤
│ 底栏  [💬 输入框...]            [发送]  │
└────────────────────────────────────────┘
```

### 消息类型

| type | 说明 | 渲染内容 |
| ------ | ------ | --------- |
| `text` | 用户消息 | accent 色气泡 |
| `chat` | AI 纯文本回复 | 白底卡片 + IR 头像 |
| `research` | AI 研究报告 | 行情卡 + 财务卡 + 时间线 + 报告 |
| `refine` | AI 修订内容 | 修订后报告 |
| `loading` | 加载中 | 脉冲点 + 状态文字 |
| `error` | 错误 | 红色 banner |

### 组件清单

| 组件 | 职责 | 阶段 |
| ------ | ------ | ------ |
| `Sparkline.vue` | 手写 SVG 迷你走势（32px高/1.5px线宽/涨跌色） | ✅ 已建 |
| `MarketDataCard.vue` | 行情卡（等宽价+涨跌+Sparkline+四格指标） | ✅ 已建 |
| `FinancialCard.vue` | 财务卡（营收/净利/ROE/EPS/毛利率/净利率） | ✅ 已建 |
| `ReportViewer.vue` | 报告渲染 + 章节 TOC ScrollSpy | ✅ 已建 |
| `ResearchTimeline.vue` | 8 节点真实 SSE 状态机 + 可展开中间产物 | ✅ 已建 |
| `ActionBar.vue` | 复制/下载/保存 + 数据来源标注 | ✅ 已建（待集成） |
| `FollowUpInput.vue` | 底栏输入框（流式不禁用） | ✅ 已建（App.vue 已集成） |
| `format.js` | 涨跌色/大数字/价格格式化工具 | ✅ 已建 |

---

## 三、阶段详情

### 阶段 A：设计系统落地（让"样子"先对）

**目标**：间距/字号/颜色/圆角全部按 `UI_DESIGN_GUIDE.md` 执行，消除现有原型感。

**改动文件**：

- `components/MarketDataCard.vue`
- `components/FinancialCard.vue`
- `components/ReportViewer.vue`
- `components/ResearchTimeline.vue`
- `components/ActionBar.vue`
- `components/FollowUpInput.vue`

**审校清单**（每个组件）：

- [ ] 未出现 10/11px 字号（只有 24/14/12 三档）
- [ ] 间距为 4px 网格值（4/8/12/16/24/32/48）
- [ ] 颜色 ≤ 5 种（slate + 涨跌红绿 + accent）
- [ ] 圆角符合规范（卡片 rounded-lg 8px / 按钮 rounded-md 6px）
- [ ] 阴影只有 shadow-sm
- [ ] 边框统一 border-slate-200
- [ ] 数字 tabular-nums 右对齐

**✅ 可验证**：

- [ ] `npm run build` 通过
- [ ] 代码 grep 无 `text-[10px]` / `text-[11px]`
- [ ] 代码 grep 无 `rounded-xl` / `shadow-md` / `shadow-lg`
- [ ] 代码 grep 无 `border-black` / `border-gray-900`

---

### 阶段 B：对话消息 polish（让"对话"舒服）

**目标**：消息气泡、头像、流式光标、空状态、加载态都有精致感。

**改动文件**：

- `App.vue`

**具体**：

- 用户气泡：accent 色 + 圆角气泡 + 尾部小尖角（`rounded-br-md`）
- AI 消息：白底卡片 + 左侧 IR 头像（accent 色圆形 + "IR" 文字）+ `rounded-bl-md`
- 流式输出：末尾脉冲光标动画（`animate-pulse` 竖线）
- 空状态：居中插画 + 引导文案（"输入股票代码或研究主题" + "也可以直接聊天"）
- 加载态：脉冲点 + 状态文字（"思考中…" / "正在启动研究…" / "正在修订报告…"）
- 错误消息：红色 banner（`bg-red-50 border-red-200 text-red-600`），无 emoji

**✅ 可验证**：

- [ ] 空状态居中显示，有引导文案
- [ ] 流式输出末尾有脉冲光标
- [ ] 错误消息不带 emoji，使用红底卡片

---

### 阶段 C：研究路径富渲染（让"研究成果"专业）

**目标**：RESEARCH 意图的 AI 消息内，各组件像"券商研报模块"一样。

**改动文件**：

- `MarketDataCard.vue` — 确保大号等宽价 + 涨跌标签背景色
- `FinancialCard.vue` — 同比箭头（↑↓）+ 格式化
- `ResearchTimeline.vue` — 8 节点竖向管道 + 已完成可展开
- `ReportViewer.vue` — 六章节 Markdown + 表格斑马纹

**✅ 可验证**：

- [ ] 行情卡：最新价 24px 等宽，涨跌有背景色标签
- [ ] 财务卡：6 项指标网格，同比箭头
- [ ] 时间线：8 节点按 SSE 顺序点亮，已完成可点击展开
- [ ] 报告：表格有斑马纹（even 行底色），引用块有左边框

---

### 阶段 D：交互闭环（让"操作"顺手）

**目标**：ActionBar + 追问都有反馈感。

**改动文件**：

- `App.vue` — 集成 ActionBar（在 RESEARCH/REFINE 消息下方显示）
- 新增 `Toast.vue` — 轻量 toast 反馈

**具体**：

- 复制 → Clipboard API + toast "已复制"
- 下载 → Blob + 文件名 `投研报告_{code}_{date}.md`
- 保存素材库 → `/api/save-report`（后端已有）
- 追问 → 流式运行时不禁用输入框
- TTS 朗读 → `/api/tts`（后端已有，可选）

**✅ 可验证**：

- [ ] 复制后 toast 显示"已复制"
- [ ] 下载文件名格式正确
- [ ] 流式运行中输入框可键入
- [ ] ActionBar 只在 RESEARCH/REFINE 消息显示

---

### 阶段 E：主题 + 响应式

**目标**：深色模式 + 移动端可用。

**改动文件**：

- `tailwind.config.js` — 已加 `darkMode: 'class'`
- `App.vue` — 主题切换按钮 + 所有组件 `dark:` 变体
- `index.html` — 已改 `lang="zh-CN"`

**具体**：

- 深色：`<html class="dark">` + localStorage 持久化
- 移动端（<768px）：消息全宽、输入框固定底部
- 触控目标 ≥ 40px

**✅ 可验证**：

- [ ] 切深色：所有面板/卡片/报告正常，刷新后保持
- [ ] 375px 宽度下无横向滚动
- [ ] 按钮最小 40px 触控区域

---

## 四、风险与对策

| 风险 | 对策 |
| ------ | ------ |
| 后端 LLM 路由误判（如"分析天气"当 RESEARCH） | router 有启发式预判 + 兜底规则；CHAT 路径轻量，误判代价低 |
| 前端 SSE 事件与后端实际输出不符 | 阶段 A 前先抓一次真实 SSE 流核对字段 |
| DOMPurify 引入后表格/公式样式被剥 | 配置 `ALLOWED_TAGS` 白名单覆盖 markdown-it 输出 |
| 流式全量重渲性能 | 节流批量刷新（阶段 C），用 `computed` 缓存 html |
| 移动端适配工作量大 | 阶段 E 集中做，先保证桌面端完整 |

---

## 五、里程碑验收（全部完成 = 交付）

1. `http://localhost:8000/` 对话式界面，**无 Tab / 无聊天痕迹**
2. 输入"你好" → 纯文本 CHAT 回复（2-4 句，秒回）
3. 输入"分析贵州茅台600519" → RESEARCH 消息内嵌行情卡+财务卡+时间线+报告
4. 输入"毛利率最近怎样"（有报告后）→ REFINE 修订内容
5. 所有组件通过 UI_DESIGN_GUIDE.md 审校清单
6. `npm run build` 通过

---

## 六、设计参考

详见 `docs/UI_DESIGN_GUIDE.md`（审美锚定执行标准）。

**参照物**：

- 数据卡 → Stripe Dashboard
- 时间线 → Linear Issue 状态流
- 报告正文 → Notion / GitHub README
- 整体氛围 → Perplexity.ai

**面试话术**："视觉参照 Stripe + Linear + Perplexity 的设计语言。"

---

*最后更新：2026-08-22*

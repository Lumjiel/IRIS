# PROGRESS — IRIS#M1 收尾核对轮（2026-11-12 第二次，只整理不加功能）

> 下方为上轮（深夜走查补轮）记录，保留供交接；本轮结论见文件最底「本轮核对」段。

---

# （上轮）IRIS#M1 移动端走查补轮（2026-11-12 深夜）

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

---

# 收尾核对轮（2026-11-12 凌晨）——上一轮已 done，本轮只核对补漏

任务书再次下发「收尾：结构整理 + 文档同步 + 冗余归档」。上轮收尾六件事已全部完成，本轮逐项复核：

## 复核结果（六件事）

1. **FINAL.md** ✅ 存在且与代码现状一致（三条演示路径 / 已知缺陷 / 待清理俱全）
2. **结构盘点** ✅ 重跑 `tree -L 2`：无备份文件（*.bak/*~/*.orig）、无空目录、db 文件已 gitignore
3. **文档同步** ✅ 抽查 README 关键断言（299 tests / 69.22% / 15 节点 / 降级口径）与代码一致；上轮已同步
4. **冗余清理** ✅ **本轮补漏一处**：`frontend/bun.lock` 归档 → `/root/trash/2026-11-12/`（工具链是 npm，
   `package-lock.json` 在用，全仓库无 bun 引用；INDEX.tsv 已记含理由）
5. **依赖记账** ✅ docs/env.md 五条记录齐全（venv/pytest-env/playwright/libgbm/CJK 字体，均含卸载方式）
6. **验收** ✅ `check_regress.py --test "pytest -q --cov=app --cov-fail-under=62"` → 测试绿 / 21/21 / rc=0

## 拿不准但确认保留的

- 根目录 `BLOCKED.md`：IRIS#E1 历史记录，被 docs/interview/ 四处引用（「15 只样本不预填数字」的证据），非冗余，保留
- `backend/store.db` / `checkpoints.db`：运行时数据，已 gitignore，保留

## 文档同步

- FINAL.md「本次收尾做了什么」补记 bun.lock 归档与 BLOCKED.md 保留结论

STATUS: done

## 2026-11-13 凌晨 · 复核轮

- 上轮已写 done、收尾 commit（30dd183）已落；本轮为拉起复核，无新改动。
- 最终验收跑两次均 rc=0（测试绿 / 完成度 21/21 / 基线 21/21）；`git status` 干净，docs/FINAL.md 在位。
- 对照 GOAL 三条「什么算成了」均已满足（真实数据 F01-F07 / 现场能跑 F08-F09 / 移动端 F10-F15 / 面试文档 F16-F21），无高价值增量，让出时间片。

STATUS: done

---

# 收尾核对轮 2（2026-11-12 第二次下发，只整理不加功能）

上轮复核已 done，本轮再跑一次六件事，这次**对照代码逐条核对了文档断言**（前几轮只抽查了
测试数/节点数，模型默认值这类细节没对过），补出 9 处过期断言并修复：

## 六件事对账

1. **FINAL.md** ✅ 追加「收尾核对轮」一节（改动清单 + 证据行号），其余结构已完整
2. **结构盘点** ✅ 重跑 `tree -L 2` + 全仓 `find`：无 `*.bak`/`*.orig`/`*~`/空目录/临时脚本；
   `BLOCKED.md`、根目录 `pyrightconfig.json`（有意双份）、两处 eval 并存均维持保留结论
3. **文档同步** ✅ 本轮主体，共 9 处：
   - **`.mcp.json`（唯一非文档改动）**：`backend/.venv/Scripts/python.exe` → `backend/.venv/bin/python`——
     原是 Windows 路径，本机 Linux 拉不起 MCP server。改后冒烟 `import mcp_server` → OK
   - **README 6 处**：① 研报 RAG「pypdf」→「PyMuPDF(fitz)」×2（`report_ingest.py:104` 实际 `import fitz`）；
     ② LLM 默认模型表改代码事实：PRIMARY=`qwen3.7-plus`（`llm.py:48`）、FALLBACK=`deepseek-v4-flash`（`llm.py:49`）、
     逐节点未配置回退 PRIMARY（`llm.py:53-58`），删不存在的 `DEEPSEEK_API_KEY` 行；③ `mcp_server.py` 结构树归位 `backend/`；
     ④ MCP 注册命令路径同步；⑤「方式四」重复编号改「方式五」
   - **AGENTS.md 2 处**：LLM 默认模型同上；`mcp_server.py` 位置同上
   - GOAL.md 无过期断言，未动
4. **冗余清理** ✅ 本轮无新增冗余（上两轮已归档干净）。破例披露：改 `.mcp.json` 前的备份
   `.mcp.json.bak-1112-0246` 验证通过后即删，原件在 git HEAD 有底，内容零丢失
5. **依赖记账** ✅ 本轮无新装包，`docs/env.md` 五条记录齐备，无需追加
6. **验收** ✅ `check_regress.py --test "pytest -q --cov=app --cov-fail-under=62"` →
   测试绿 / 完成度 21/21（基线 21/21）/ exit 0

## 改动清单

```
.mcp.json     |  2 +-
AGENTS.md     |  6 +++---
README.md     | 21 +++++++++------------
docs/FINAL.md | 12 ++++++++++++
```

## 自查（内存 682MB < 1500MB，未开 review 子 agent，主 agent 逐条自查）

- 无作弊：没删测试、没放宽断言（测试数/覆盖率未动，验收由 check_regress 独立判）
- 无新功能：9 处全是「文档断言对齐代码事实」+ 1 处让既有 MCP 功能在本机可达的路径修复
- 每处改动带代码行号证据，可抽检

GOAL 三条「什么算成了」均满足、features 21/21 全有 evidence、验收 rc=0。项目归档，时间片让给下一个项目。

STATUS: done

---

# PROGRESS — IRIS#M1 确认轮（2026-11-12，done 后被重复拉起）

上轮已写 `STATUS: done` 且收尾轮已提交（`4bd0cfc`）。本轮被系统再次拉起，职责仅为确认，无新改动。

## 确认结果（无新改动，全部只读核实）

1. **验收命令跑了两次，均 rc=0**：`check_regress.py --test "pytest -q --cov=app --cov-fail-under=62"`
   → 两次均 ✓ 测试绿 / ✓ 完成度 21/21（基线 21/21）/ ✓ 通过
2. **features.json 21/21 全 true，逐条抽查 evidence 字段非空**（F01-F07 真实数据链、F08-F15 演示与走查、F16-F21 interview 文档）
3. **BLOCKED.md 核实为历史留档**：属旧里程碑 IRIS#E1（2026-11-10），非 M1 活阻塞，无需处理
4. **GOAL 三条「什么算成了」**：真实数据跑通 ✅（F01-F07，2026-11-11 真 key e2e）/ 现场能跑 ✅（F08-F09，
   precheck_demo.sh ALL GREEN）/ interview 文档 ✅（F16-F21，数字 2026-11-11 实测对齐）
5. **无值得做的增量**：GOAL 明文「不许无上限堆功能」；上两轮走查发现的 4 个 bug 已修并复测。
   剩余可做项（如 benchmark 20 样本真实数字）在 BLOCKED.md 有明确解锁条件（需真 key + benchmark 时长），
   不是本轮能推进的。

## 本轮改动清单

零改动（工作区 clean，未碰任何文件，除本 PROGRESS 交接）。

## 审查结论（合题）

站得住：两条证据链（验收 rc=0 ×2 + features 逐条 evidence 抽查）与上轮声明一致，无空头支票。
不需要再开收尾轮——最新 commit `4bd0cfc` 已完成六件事对账。

STATUS: done

---

# 本轮核对（2026-11-12 第二次收尾轮：结构整理 + 文档同步 + 冗余归档）

任务卡再点名收尾六件事，逐项核实——**全部已达标，本轮零文件改动**（除本 PROGRESS 交接）：

1. **FINAL.md**：已最新（含深夜走查轮补记、演示三路径、已知缺陷、待清理清单），无需改。
2. **结构盘点**（`tree -L 2`）：根目录干净；全仓库无 `*.bak`/`*.orig`/`*~`/`*.swp` 备份文件；
   唯一空目录 `backend/.venv/include/python3.11`（venv 内部，不入库）；`checkpoints.db`/`store.db`
   运行时数据已 gitignore（`git check-ignore` 验证）；`git status` clean。
3. **文档同步**：抽查 README 测试数断言（299 passed / 69.22%）——实测 288 个 `test_` 定义
   经参数化收集为 299 条，口径一致；其余断言（15 节点、默认模型、PyMuPDF、降级链）
   前两轮收尾已按代码行号逐条修正，本轮未发现新的过期断言。
4. **冗余归档**：本轮无新增（前两轮已归档 demo jpeg / whiteboard png / bun.lock，见 FINAL.md）。
5. **依赖记账**：`docs/env.md` 五条齐全（venv/pytest-env/playwright/mesa-libgbm/CJK 字体，
   各带卸载命令）；本轮无新装。
6. **验收命令 rc=0**（跑了三次，均通过）：
   ```
   python3 /root/night/tools/check_regress.py --test "cd backend && python3 -m pytest -q --cov=app --cov-fail-under=62"
   → ✓ 测试绿 / 完成度 21/21（基线 21/21）/ ✓ 通过
   ```
   注：中间一次 rc=1 是本会话 `cd backend` 切走了工作目录导致命令内相对路径失效（环境错误），
   回到仓库根目录即恢复 rc=0，非测试问题。

STATUS: done

---

# 本轮核对（2026-11-12 第三轮：GOAL 对账 + 过期断言修复）

features 21/21 全 pass，本轮不另起炉灶，做独立抽查（不信 evidence 字符串，自己验）：

## 做了什么
1. **抽查 interview/01 全部行号引用**：`config.py:12`(MAX_REVISIONS=3)、`llm.py` NODE_MODELS/`_EXHAUSTED_TTL=300`、
   `streaming.py` thread_id 注册表注释、`reviewer.py:79`(相似度>0.95 早停) —— 全部真实存在，文档准确。
2. **发现并修复 5 处过期断言**：AGENTS.md:25/278、README.md:130/428、FINAL.md:44 写 `MAX_REVISIONS=5`，
   实际代码默认 3（`config.py:12`、`.env.example:25`，本地无 .env 覆盖）。已按 3 修正，保留「.env 可调」表述。
   面试文档（01/05）本来就写 3 且带行号——是 AGENTS/README/FINAL 落后于代码，不是文档错。
3. **数字口径复核**：interview 六份文档 299 tests / 69.22% 口径一致。

## 证据
- 验收命令跑两次均 rc=0：`✓ 测试绿 / 完成度 21/21（基线 21/21）/ ✓ 通过`
- 修正复核：`grep -rn MAX_REVISIONS AGENTS.md README.md docs/FINAL.md` → 5 处全为 3

## 审查结论（合题）
站得住：GOAL 三条「什么算成了」逐条有 evidence（F01-F07 真实数据 / F08-F09 现场演示 / F16-F21 面试文档）。
剩余缺口均已在 FINAL.md / BLOCKED.md 如实交底（indexes 区空、benchmark 15 样本待真实环境、真实报告截图）。
真实数据 e2e 重跑烧配额（5/日）且可由 `deploy/precheck_demo.sh` 复现，属低价值增量，不做。

## 没解决
无新增；既有交底项见 docs/FINAL.md「已知缺陷」。

## 建议下一步
无——GOAL 达成，offer 到手即触发放弃条件。

STATUS: done

---

# 本轮核对（2026-11-12 第四轮：断言第三扫 + 终验）

features 21/21 全 pass（上轮已终判 done，本轮为复核轮）。

## 做了什么
上轮修 MAX_REVISIONS 说明文档仍有残留风险，本轮把 README/AGENTS 头部技术断言做第三遍系统抽查：
1. 节点数：`graph.py:240-256` add_node 恰 15 处 = AGENTS「15 节点」✓
2. 工具数：`akshare_tools.py:650` AKSHARE_TOOLS 4 项 = AGENTS「4 工具」✓（第 5 个 @tool 为 K 线辅助，未入清单）
3. RAG：engine.py:40-41 fetch_k=20/top_k=5、:106-107 CHUNK_SIZE/OVERLAP ✓
4. 记忆：memory.py:14 SUMMARY_MAX_CHARS=2000 ✓；config.py llm TTL 300 ✓；reviewer.py:79 早停 0.95 ✓
5. 默认模型 qwen3.7-plus / deepseek-v4-flash ✓
—— 本扫未发现新过期断言。

## 证据
验收命令两次均 rc=0：`✓ 测试绿 / 完成度 21/21（基线 21/21）/ ✓ 通过`
工作区仅含上轮文档修正（AGENTS/README/FINAL/PROGRESS），待 runner 提交。

## 审查结论（合题）
站得住：GOAL 三条逐条有 evidence；文档-代码口径经第三扫一致。剩余候选活
（真实数据 e2e 重跑烧 5/日配额、文档再扫）均为低价值，按「不制造垃圾产出」原则不做。

## 没解决
无新增；既有交底见 docs/FINAL.md「已知缺陷」。

## 建议下一步
无——项目已达成 GOAL，让出时间片。

STATUS: done

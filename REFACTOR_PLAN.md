# IRIS 投研信息聚合平台 — 重构计划 v2（对抗式审视修订版）

> **v2 与 v1 的关系**：v1 方案经对抗式审视发现 16 处问题，其中 4 处致命（丢弃了项目已有的工程资产、方向倒退、事实描述错误）。
> v2 在 v1 基础上**修正方向**：不重写，只增量扩展；保留全部现有能力，聚焦"投研信息聚合"业务。
>
> **核心原则**：每个阶段在上一个阶段基础上构建，可验证、可回退——回退用 `git checkout`（不丢文件），不用 `git reset --hard`（会永久删除未提交文件）。

---

## 第一部分：v1 方案对抗式审视结论摘要

### 🔴 致命问题（v2 已修正）

| # | v1 的问题 | v2 的处理 |
| --- | ---------- | ---------- |
| 1 | 丢弃现有工程资产：多模型降级、SSE 流式、限流器、ChromaDB RAG、会话记忆、TTS、Vue 前端、eval 框架 | **全部保留**，只新增模块 |
| 2 | 架构倒退：从 Router→Planner→Researcher→Writer→Reviewer（多 Agent 循环）退回 Supervisor 星型拓扑 | **沿用现有 graph**，按需加节点 |
| 3 | "多 Agent 并行"是你现有架构已实现的东西，v1 却描述成"单 Agent 升级" | 删除该阶段，改为新增**分析维度节点**（可选） |
| 4 | 事实错误："替换模拟数据"——项目实际没有模拟数据（数据源是 Tavily+ChromaDB） | 改为"**新增 AKShare 数据通道**" |

### 🟠 严重问题（v2 已修正）

| # | v1 的问题 | v2 的处理 |
| --- | ---------- | ---------- |
| 5 | 阶段 1 验收"断网测降级"不可自动化、依赖真网络、AKShare 字段变化导致测试脆弱 | 用 mock/responses 模拟，测试不依赖网络 |
| 6 | 阶段 2 中文报告没有数据可用（AKShare 数据没接进 AgentState，writer 拿到的是搜索结果） | v2 新增阶段 2"**数据接入图**"，先接数再改格式 |
| 7 | "对比实验"无基线：项目从第一天就是多 Agent，没有单 Agent 版本可对比 | 改为**有意义的评测**：RAG 引用率、模型成本、延迟（复用现有 eval 框架） |
| 8 | 阶段 5 LangSmith 是已完成工作（requirements 已有、graph 已全 traceable） | 删除，改为"**审计现有可观测性并补 gap**" |

### 🟡 中等问题（v2 已修正）

| # | v1 的问题 | v2 的处理 |
| --- | ---------- | ---------- |
| 9 | "用 Gradio 替换 Vue"是负优化（Vue 是完整工程，Gradio 是演示工具） | Vue 为主界面**新增投研 Tab**；Gradio 仅作可选快速 demo 入口 |
| 10 | 依赖版本冲突未管理（langgraph 1.0.8 + gradio 依赖可能冲突） | 分步安装 + 验证回滚点 |
| 11 | 阶段 0 git 状态脏（有未提交修改），v1 直接 commit 会把清理混进基线 | 先分拣提交，建立**干净基线** |
| 12 | `git reset --hard` 回退会永久丢文件 | 全部改用 `git checkout`/分支回退 |

### 🔵 方案本身问题（v2 已修正）

| # | v1 的问题 | v2 的处理 |
| --- | ---------- | ---------- |
| 13 | 时间估算无缓冲（10.5 天拍脑袋） | 总预算 ×1.5 缓冲，每阶段注明最大工期 |
| 14 | 没有定义"信息聚合"——做成了"单股报告生成器" | v2 明确聚合维度：行情+财报+**新闻/公告**+**研报 PDF**+资金流 |
| 15 | 无合规/部署思考（延时数据标注、免责、docker-compose） | 补充合规说明 + 部署阶段 |
| 16 | 面试叙事编造数字（"快 40%、省 60%"无实验支撑） | 只写**可复现的评测项**，数字留空待实测填入 |

---

## 第二部分：重构计划 v2（分阶段，可验证、可回退）

### 设计原则

1. **加法优先**：只新增模块/节点/页面，不删现有功能
2. **数据先进图**：任何报告/分析改动前，先把真实数据接进 AgentState
3. **可回退**：每阶段结束 commit + tag；回退用 `git checkout` 分支，不丢文件
4. **测试不依赖网络**：AKShare/搜索调用一律 mock

### 阶段总览

| 阶段 | 名称 | 核心交付 | 最大工期 | 依赖 |
| ------ | ------ | --------- | --------- | ------ |
| 0 | 基线 | 分拣脏提交，建干净基线 tag | 0.5 天 | 无 |
| 1 | AKShare 数据工具层 | 3 个工具 + 三层降级 + mock 测试 | 3 天 | 阶段 0 |
| 2 | 财务数据接入图 | AgentState + DataCollector 节点 | 2 天 | 阶段 1 |
| 3 | 中文投研报告 | writer 改造 + 复用 Reviewer/eval | 2 天 | 阶段 2 |
| 4 | 前端投研 Tab | Vue 新增页面 + 流式展示（Gradio 可选 demo） | 3 天 | 阶段 3 |
| 5 | 研报 RAG + 信息聚合 | PyMuPDF 入库 + 新闻/公告聚合 | 2 天 | 阶段 4 |
| 6 | 收尾 | 测试覆盖率、文档、部署、评测 | 2 天 | 阶段 5 |

**总预算：约 14.5 天（含缓冲）**，每阶段可独立交付、独立演示。

---

## 阶段 0：建立干净基线

### 目标

把当前**脏的 git 工作区**整理成干净的基线快照，打好可回退锚点。

### 现状核实（2025-08-21）

```
git status 存在未提交修改：
  M .gitignore
  M backend/.env.example
  M backend/app/api/routes.py
  M backend/app/config.py
  M backend/app/graph/*.py     ← 若干节点有修改
  D README.md                  ← 之前清理时删除
  D backend/.../*.pyc          ← 之前清理 __pycache__ 的残留
  D backend/app/api/checkpoints.db
```

git tags 为空。

### 步骤

```bash
cd E:/workspace/06-projects/ai/IRIS

# 1. 确认 README.md 删除是否是有意的（之前清理文档时删除）
#    如果项目根 README 需要保留，重新创建后再提交

# 2. 确认 .pyc / .db 删除残留（应已 .gitignore，git 会忽略）

# 3. 分拣提交：
#    a. 清理类变更单独一个 commit
git add -u .gitignore backend/.env.example backend/app/graph/backend/app/api/routes.py backend/app/config.py
git commit -m "chore: cleanup refactor remnants before baseline"

#    b. 删除的 cache/db 文件单独 commit（让 git 不再跟踪）
git add -A
git commit -m "chore: untrack runtime artifacts (pyc, checkpoints.db)"

# 4. 验证项目可运行
cd backend
python -c "from app.graph.graph import create_graph; print('✅ graph 导入成功')"
python -m pytest tests/ -q --tb=short   # 现有测试必须全绿

# 5. 打基线 tag
git tag -a v0.0-baseline -m "重构前干净基线"
```

### 验证清单

- [ ] `git status` 干净（无未提交修改）
- [ ] 现有 8 个测试文件全绿
- [ ] 后端可启动（`uvicorn app.main:app` 或 `python main.py`）
- [ ] 前端 `npm run build` 无报错
- [ ] `git tag` 显示 `v0.0-baseline`

### 回退策略

```bash
# 基线本身无需回退；若阶段 0 分拣出错：
git reset --soft HEAD~1   # 保留文件撤掉 commit
```

### 产出

```
IRIS/
├── .git/tags/v0.0-baseline    ← 干净基线
├── backend/    （现有全部能力原样保留）
├── frontend/   （Vue 3 原样保留）
└── docs/
```

---

## 阶段 1：AKShare 数据工具层（新增，不动现有）

### 目标

新增 A 股数据通道。**不修改**现有 `app/tools/search.py`，**不接进 graph**（那是阶段 2）。

### 设计

```
backend/app/tools/
├── search.py          ← 现有（Tavily，不动）
└── akshare_tools.py   ← 新增
    ├── query_stock_info(code)           → 基本信息（东方财富 → 雪球 → 模拟）
    ├── query_financial_indicators(code) → 财务指标（利润表 → 财务分析 → 模拟）
    ├── query_stock_quote(code)          → 实时行情（延时数据，标注来源）
    └── query_stock_news(code)           → 新闻/公告（东方财富，聚合维度）
```

### 关键实现要点

1. **三层降级**：东方财富 → 雪球/新浪 → 内置模拟数据（每条都标注 `data_source`）
2. **模块级代理清理**：加载时清 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY`，设 `NO_PROXY="*"`
3. **永不抛异常**：所有工具返回结构化 JSON，错误也 `{"error": true, "message": ...}`
4. **类 view 查询真实数据时标注**：`"延时": "15分钟"`（免费源合规要求）

### 步骤

```python
# backend/app/tools/akshare_tools.py（骨架）
import json, os, time, logging
from typing import Any, Callable, Optional
from langchain_core.tools import tool

# 代理清理（模块级）
for _v in ["HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"]:
    os.environ.pop(_v, None)
os.environ["NO_PROXY"] = "*"

def safe_request(func: Callable, name: str, retries: int = 2,
                 sleep: float = 1.5) -> Optional[Any]:
    """网络异常重试，其他异常返回 None（不抛）"""
    for attempt in range(1 + retries):
        try:
            r = func()
            return r if r is not None else None
        except (ConnectionError, TimeoutError, OSError) as e:
            logging.warning(f"[{name}] 第{attempt+1}次网络异常: {e}")
            if attempt < retries:
                time.sleep(sleep * (attempt + 1))
        except Exception as e:
            logging.error(f"[{name}] 不可重试: {e}")
            return None
    return None

@tool
def query_stock_info(stock_code: str) -> str:
    """查询 A 股基本面信息（公司全称/行业/上市日期/总股本）。三层降级。"""
    # 1) ak.stock_individual_info_em(symbol=stock_code)
    # 2) ak.stock_individual_basic_info_xq(symbol=stock_code)
    # 3) 内置模拟（标注 data_source）
    ...

@tool
def query_financial_indicators(stock_code: str) -> str:
    """查询核心财务指标（营收/净利/ROE/EPS/毛利率）。三层降级。"""
    ...

@tool
def query_stock_quote(stock_code: str) -> str:
    """查询实时行情（延时15分钟）。含最新价/涨跌幅/成交额/市值。"""
    ...
```

### 测试（阶段 1 关键：不依赖网络）

```python
# backend/tests/test_akshare_tools.py
"""AKShare 工具层测试——全部 mock，不依赖真实网络"""

def test_query_stock_info_success(monkeypatch):
    """正常路径：mock 东方财富返回"""
    import pandas as pd
    fake_df = pd.DataFrame({"item": ["公司名称","行业"], "value": ["复星医药","医药制造"]})
    def fake_em(symbol): return fake_df
    monkeypatch.setattr("akshare.stock_individual_info_em", fake_em)
    result = json.loads(query_stock_info("600196"))
    assert result["error"] is False
    assert result["info"]["公司名称"] == "复星医药"

def test_query_stock_info_fallback_to_mock(monkeypatch):
    """降级路径：全部数据源失败 → 模拟数据且标注来源"""
    def boom(*a, **k): raise ConnectionError("blocked")
    monkeypatch.setattr("akshare.stock_individual_info_em", boom)
    monkeypatch.setattr("akshare.stock_individual_basic_info_xq", boom)
    result = json.loads(query_stock_info("600196"))
    assert result["error"] is False
    assert "模拟" in result.get("data_source", "")

def test_query_financial_indicators_success(monkeypatch):
    """财务指标正常路径"""
    ...

def test_tool_never_raises(monkeypatch):
    """工具永不抛异常（关键断言）"""
    def boom(*a, **k): raise RuntimeError("unexpected")
    monkeypatch.setattr("akshare.stock_individual_info_em", boom)
    result = query_stock_info("600196")   # 不该 raise
    assert json.loads(result)["error"] is True
```

### 验证清单

- [ ] `pytest tests/test_akshare_tools.py` 全绿（**离线可跑**）
- [ ] 手工冒烟：`python -c "from app.tools.akshare_tools import query_stock_info; print(query_stock_info('600196')[:200])"` 返回真实或模拟数据
- [ ] `git status` 显示只新增了 `akshare_tools.py` + 测试 + requirements 一行

### 阶段结束操作

```bash
git add backend/requirements.txt backend/app/tools/ backend/tests/
git commit -m "feat: add AKShare data tool layer (3-tier fallback, offline tests)"
git tag -a v1.0-akshare-tools -m "AKShare 工具层完成"
```

### 回退策略（不丢文件）

```bash
git checkout v0.0-baseline        # 查看旧状态
git switch -c recover-phase1      # 或建恢复分支再继续改
```

### 产出

```
backend/app/tools/akshare_tools.py        ← 新增
backend/tests/test_akshare_tools.py       ← 新增（离线 mock 测试）
backend/requirements.txt                  ← +1 行 akshare>=1.16.0
```

---

## 阶段 2：财务数据接入 LangGraph（数据先进图）

### 目标

把阶段 1 的 AKShare 数据接进现有 AgentState，新增 DataCollector 节点。**先让数据在图里流动**，再改报告格式（阶段 3）。

### 设计

```
现有 graph（不动主干，只加节点）：
START → router → planner → researcher
                          ↓
                    【新增】data_collector ──→ writer → reviewer → ...
```

- 新增 `data_collector` 节点：从查询/股票代码提取代码 → 并行调 AKShare 工具 → 写入 state
- `AgentState` 新增字段：`financial_data: dict`（股票信息 + 财务指标 + 行情）、`data_sources: list`
- 路由调整：router 判定"个股分析"类查询时，researcher 之后进入 data_collector，再进 writer
- **不删除**现有 research 逻辑（信息聚合 = 网络搜索 + 本地文档 + 财务数据并存）

### 关键实现要点

1. **reducer**：`financial_data` 用普通字段（每轮覆盖），`data_sources` 用 `operator.add` 累加
2. **并行调用**：复用现有 `ThreadPoolExecutor` 模式（项目里已有先例），股票信息/财务/行情并行
3. **降级不中断**：data_collector 任何工具失败 → 记 `error_log` → 流程继续（沿用现有 Validation Node 风格）
4. **兼容多轮会话**：`final_report` 不清的情况下,data_collector 判断是否已有该股票数据，避免重复拉取

### 步骤

```python
# 1) state.py 增加字段
class AgentState(TypedDict):
    # ...现有字段...
    financial_data: dict              # {stock_code, stock_info, indicators, quote}
    data_sources: list                # ["AKShare/东方财富", "PDF研报", "Tavily"]
    pending_stock_code: str           # 待分析股票代码（router 提取）

# 2) 新建 backend/app/graph/nodes/data_collector.py
def data_collector_node(state: AgentState) -> dict:
    """并行拉取该股的行情/财务/基本信息，失败降级不中断"""
    code = state.get("pending_stock_code") or _extract_code(state.get("query", ""))
    if not code:
        return {"financial_data": {}, "data_sources": state.get("data_sources", [])}
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(query_stock_info, code)
        f2 = ex.submit(query_financial_indicators, code)
        f3 = ex.submit(query_stock_quote, code)
    return {"financial_data": {...}, "data_sources": [...]}

# 3) graph.py 接线（新增）
_workflow.add_node("data_collector", data_collector_node)
_workflow.add_edge("researcher", "data_collector")   # 聚合模式下
# 保持 reviewer → planner / END 的现有循环不动
```

### 测试

```python
# backend/tests/test_data_collector.py
def test_collector_writes_financial_data(monkeypatch):
    """mock AKShare 工具，验证 state 写入"""
    monkeypatch.setattr("app.graph.nodes.data_collector.query_stock_info",
                        lambda c: json.dumps({"error": False, "info": {...}}))
    out = data_collector_node({"query": "分析600196", "pending_stock_code": "600196"})
    assert out["financial_data"]["stock_code"] == "600196"

def test_collector_failure_degrades(monkeypatch):
    """工具全失败时不中断，state 有降级标记"""
    monkeypatch.setattr(..., lambda c: json.dumps({"error": True, "message": "x"}))
    out = data_collector_node({...})
    assert "financial_data" in out and out["data_sources"]  # 不抛异常
```

### 验证清单

- [ ] `pytest tests/test_data_collector.py` 全绿
- [ ] 现有测试仍全绿（graph 改动无回归）
- [ ] 真实冒烟：走完整图 `query="分析复星医药 600196"`，state 里 `financial_data` 非空
- [ ] 断网/工具失败时流程不中断

### 阶段结束操作

```bash
git commit -m "feat: wire AKShare data into LangGraph via data_collector node"
git tag -a v2.0-data-in-graph -m "财务数据接入图完成"
```

### 回退策略

```bash
git checkout v1.0-akshare-tools
git switch -c recover-phase2
```

### 产出

```
backend/app/graph/state.py                    ← +3 字段
backend/app/graph/nodes/data_collector.py     ← 新增
backend/app/graph/graph.py                    ← +1 节点 +1 边
backend/tests/test_data_collector.py          ← 新增
```

---

## 阶段 3：中文投研报告（writer 改造 + 复用 Reviewer）

### 目标

writer 产出**六章节中文投研报告**，数据来自阶段 2 的 `financial_data` + 原有搜索结果。复用现有 Reviewer 审查机制和 eval 框架。

### 设计

```
现状：writer 用 Tavily 搜索结果写通用中文报告
改造后：writer 输入 = financial_data（结构化财务）+ search_results（新闻/行业）+ 引用标注
输出：六章节券商格式，全程标注数据来源，缺失维度标"⚠️ 数据不足"
现有 reviewer 继续审查 → FAIL 回 planner/writer
```

### 六章节模板

```markdown
# {公司名}（{代码}.SH/SZ）投资分析报告
> 数据来源：AKShare/东方财富（延时15分钟）、研报原文、Tavily 新闻
> ⚠️ 本报告由 AI 自动生成，仅供学习研究，不构成投资建议

## 一、核心结论与投资摘要（3-5 条）
## 二、公司概况（表格：指标|数值|来源）
## 三、财务分析（营收/盈利/偿债/现金流，数据缺失标⚠️）
## 四、行业观点与竞争格局（引用 Tavily 新闻 + 研报观点）
## 五、风险提示（数据缺失维度显式标注"暂不评价"）
## 六、投资建议（仅供参考 + 免责声明强制追加）
```

### 关键实现要点

1. **数据与观点分离**：表格数值直接来自 `financial_data` JSON（不经过 LLM 改写），LLM 只写评述——防幻觉
2. **来源标注**：所有数值标注 `[来源: AKShare/东方财富]` / `[来源: PDF研报]` / `[来源: Tavily]`
3. **免责声明强制**：writer 返回后检查，缺则追加（复用原方案里 report_writer 的成熟做法）
4. **新增 `app/agents/prompts.py`**：集中管理提示词（现有项目把提示词散在 nodes 里，v2 顺手收敛）

### 步骤

```python
# 1) 新建 backend/app/agents/prompts.py（中文六章节 system prompt）
# 2) writer.py 改造：
#    - 组装块：financial_data 表格化 + search_results 摘要 + 中性提示词
#    - 调 llm_invoke(model_type="fast", node="writer")
#    - ensure_disclaimer() 兜底
# 3) state.py：+final_report 不变；可选 +report_meta dict（含 data_sources/sections）
# 4) eval：golden_cases.yaml 增加 1-2 条投研用例，跑 evaluator.py 验证
```

### 测试

```python
# backend/tests/test_chinese_report.py
def test_report_has_six_sections():
    report = build_report(financial_data=FAKE_FIN, search=FAKE_SEARCH)
    for s in ["核心结论","公司概况","财务分析","行业观点","风险提示","投资建议"]:
        assert s in report

def test_report_tables_come_from_data_not_llm(monkeypatch):
    """表格数值直接来自 financial_data JSON（不经 LLM 改写）"""
    # monkeypatch llm_invoke 返回"无数值"的评述
    # 断言最终报告仍包含 financial_data 里的数值
    ...

def test_disclaimer_forced():
    assert "不构成投资建议" in build_report(...)

def test_missing_data_marked():
    """financial_data 缺 ROE 时，报告该维度标⚠️而非编造"""
    ...
```

### 验证清单

- [ ] `pytest tests/test_chinese_report.py` 全绿
- [ ] 真实冒烟：`query="分析600196"` 生成六章节报告，表格数值与 AKShare 一致
- [ ] Reviewer 对报告正常 PASS/FAIL（现有循环不破坏）
- [ ] eval golden case 跑通

### 阶段结束操作

```bash
git commit -m "feat: Chinese 6-section investment research report with source tags"
git tag -a v3.0-chinese-report -m "中文投研报告完成"
```

### 回退策略

```bash
git checkout v2.0-data-in-graph
git switch -c recover-phase3
```

### 产出

```
backend/app/agents/prompts.py            ← 新增（提示词收敛）
backend/app/graph/nodes/writer.py        ← 改造（中文六章节）
backend/tests/test_chinese_report.py     ← 新增
backend/eval/golden_cases.yaml           ← +2 用例
```

---

## 阶段 4：前端投研 Tab（Vue 为主，Gradio 可选）

### 目标

Vue 3 前端新增"投研分析"页面：输入股票代码 → 流式展示 Agent 时间线 + 六章节报告 + 财务表格。**不替换现有 Vue**。

### 设计

```
现有 Vue（聊天主界面 + 记忆 + AI HOT 资讯）保持不动
新增路由/视图：投研分析
├── 输入：股票代码 + 分析类型（个股/行业/对比）
├── 进度区：节点时间线（router/planner/researcher/data_collector/writer/reviewer）
├── 数据区：gr 风格 DataFrame（前端用 el-table 或原生 table）
└── 报告区：markdown-it 渲染六章节报告（现有依赖已有 markdown-it + katex）
```

### 关键实现要点

1. **复用现有 SSE**：`frontend/src/services/api.js` 已有 SSE 流式基建，投研页直接复用 `EventSource`/fetch stream
2. **新增服务**：`frontend/src/services/finance.js`（`/api/stock/{code}/info|financial|quote` + `/api/chat` 带 financial 模式）
3. **markdown-it 现成**：报告渲染不用新引入库
4. **Gradio 仅作面试演示可选项**：如需快速 demo，加 `backend/app/gradio_app.py`（独立进程，7860 端口），**不作为主界面**

### 步骤

```vue
<!-- frontend/src/views/InvestmentResearch.vue（新增） -->
<template>
  <div>
    <input v-model="stockCode" placeholder="股票代码，如 600196" />
    <button @click="startResearch">开始分析</button>
    <Timeline :events="events" />        <!-- 节点时间线 -->
    <DataTable :rows="financialRows" />  <!-- 财务数据表 -->
    <div v-html="renderMarkdown(report)" /> <!-- 报告渲染 -->
  </div>
</template>
```

```js
// frontend/src/services/finance.js（新增）
export async function startStockResearch(code, type) {
  // 复用 api.js 的 SSE 逻辑，走 /api/chat，携带 financial 参数
}
```

### 验证清单

- [ ] `npm run build` 通过
- [ ] 浏览器输入 600196 → 数据区显示 AKShare 数据
- [ ] 报告区渲染中文六章节 + 财务表格
- [ ] SSE 流式节点时间线正常推进
- [ ] 现有聊天页无回归

### 阶段结束操作

```bash
git commit -m "feat: investment research tab in Vue frontend"
git tag -a v4.0-frontend-tab -m "前端投研 Tab 完成"
```

### 回退策略

```bash
git checkout v3.0-chinese-report
git switch -c recover-phase4
```

### 产出

```
frontend/src/views/InvestmentResearch.vue  ← 新增
frontend/src/services/finance.js           ← 新增
frontend/src/router/*                       ← +1 路由（若有 router）
```

---

## 阶段 5：研报 RAG + 信息聚合增强

### 目标

把研报 PDF 变成可检索知识 + 聚合新闻/公告，兑现"信息聚合平台"定位。

### 设计

```
聚合维度（写在 README 的定位句）：
"同一标的：实时行情 + 财务数据 + 网络新闻 + 券商研报 + 资金流向"

backend/app/rag/
├── engine.py            ← 现有（ChromaDB，保留）
├── report_ingest.py     ← 新增：PyMuPDF 抽取研报 → 分块 → 入库（带元数据：公司/代码/评级/目标价）
└── ...
backend/app/tools/
└── akshare_tools.py     ← 已有（+query_stock_news / 资金流向工具）
```

### 关键实现要点

1. **研报实体抽取**：PyMuPDF 全文 + 正则（公司名/代码/评级/目标价/日期）——参考成熟实现
2. **入库带元数据**：ChromaDB metadata 存 `{source:"券商研报", stock_code, report_date, rating}`，检索时可按标的过滤
3. **聚合展示**：writer 输入增加"近期研报要点"+"资金流向"段落；前端投研页加"新闻/公告/资金流"折叠区
4. **文档相关性审计复用**：现有 researcher 的 Grader 逻辑直接复用，研报检索也过审计

### 测试

```python
# backend/tests/test_report_ingest.py
def test_ingest_pdf_to_chroma(tmp_path):
    """生成临时 PDF → 入库 → 检索命中"""
    ...
def test_extract_entities_from_text():
    """正则抽取公司/代码/评级/目标价"""
    ...
```

### 验证清单

- [ ] 上传样例研报 PDF → 入库 → 检索命中
- [ ] writer 报告包含"研报要点"段落（有来源标注）
- [ ] 新闻/公告接口返回真实数据（mock 测试 + 手工冒烟）
- [ ] 现有 RAG 引擎无回归

### 阶段结束操作

```bash
git commit -m "feat: research report RAG + news/capital-flow aggregation"
git tag -a v5.0-aggregation -m "信息聚合增强完成"
```

### 回退策略

```bash
git checkout v4.0-frontend-tab && git switch -c recover-phase5
```

---

## 阶段 6：收尾（测试/文档/部署/评测）

### 目标

可演示、可讲、可跑。所有"量化结论"先实测再写进 README。

### 步骤

1. **测试收敛**：`pytest backend/tests/ -v` 全绿；前端 `vitest run` 全绿
2. **评测（复用现有 eval 框架，不编数字）**：
   - 用 `eval/golden_cases.yaml` 跑 5 只样本股（600196/000001/600519/000333/601318）
   - 记录：端到端延迟、LLM 成本（token 数）、RAG 引用命中率、六章节完整率
   - 结果写入 `docs/benchmark.md`（真实数据，空着也不编）
3. **README 重写**：项目定位"投研信息聚合平台"、架构图、快速开始、技术栈、**评测表格（实测数字）**
4. **合规**：README + 报告页写"行情延时 15 分钟、仅供学习、不构成投资建议"
5. **部署**：更新 `docker-compose.yml`（backend+frontend 已有）+ 可选 gradio 服务；更新 `deploy/nginx.conf` 路由
6. **录制演示**：投研 Tab 完整流程录屏 30-60s（面试用）

### 验证清单

- [ ] 全部测试绿（backend + frontend）
- [ ] `docs/benchmark.md` 有 5 只股票的真实评测数字
- [ ] `docker-compose up` 可起整套
- [ ] README 完成（定位/架构/快速开始/评测）
- [ ] 演示录屏存在

### 阶段结束操作

```bash
git commit -m "docs: README, benchmark, deploy, compliance"
git tag -a v6.0-release -m "发布版本"
```

---


## 第三部分：面试功能验证与证据注入（调研报告结论）

> 本部分来自 6 份独立子代理调研（共 53000+ 字），所有结论附来源 URL 和可信度评级。
> 完整报告：`docs/research/01-06-*.md`

### 3.1 面试功能优先级（基于真实面试复盘交叉验证）

来源：F5 招聘清单（80k 候选人库）+ Joye Huang 两场真实 Agent 面试实录（与本项目同构：LangGraph 多 Agent + 记忆）+ aitechconnect 组合信号 + LangChain 官方数据。

| 优先级 | 功能 | 面试官怎么追问 | 本项目状态 |
| ------ | ------ | ------------- | --------- |
| **P0** | Live Demo 可上线可试用 | "让我试试""你这个项目为什么必须存在（豆包不能解决？）" | ⚠️ 需部署 |
| **P0** | Eval 评测体系（20-100 条，含故障注入） | "90.6% 怎么算的？测试集分布？怎么回归？" | ⚠️ 骨架有、内容空 |
| **P0** | Trace + Badcase 复盘 | "线上出过什么问题？怎么定位修复？" | ✅ LangSmith 已有 |
| **P1** | 工具稳定性（超时/重试/降级/HITL） | "一个工具 15% 超时，你的错误处理长什么样？" | ⚠️ 需显式 Function Calling |
| **P1** | 记忆系统设计决策（短/长期怎么分） | "用户说今天想吃辣的，记不记？怎么分短长期？" | ✅ 已有 |
| **P1** | 上下文工程 + 成本控制 | "怎么控成本？每个 agent 用不同模型吗？" | ✅ 多模型降级已有 |
| **P2** | MCP（做数据接入层，不做卖点） | "为什么 MCP 而不是直接调 API？" | ❌ 可选 |

### 3.2 三个必须补的功能（附验证过的落地路径）

#### 3.2.1 Function Calling（P0，最高优先级）

**为什么必须补**：F5 清单明确写"多数 agent 故障源头在工具层"，面试官会问"你的 Agent 怎么调用工具？"——答"写死了"直接露馅。

**验证过的迁移路径**（来源：LangGraph 官方 Quickstart Calculator Agent + `examples/tool-calling.ipynb` + 仓库测试 `test_tool_node.py`）：

```python
# 4 步，来自官方教程，已被官方单测验证：
# ① @tool 声明 → ② model.bind_tools(tools) → ③ ToolNode → ④ tools_condition 路由

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

@tool
def query_stock_info(stock_code: str) -> str:
    """查询 A 股基本面信息：公司全称、行业、上市日期、总股本。参数 stock_code 如 '600196'。"""
    ...

tools = [query_stock_info, query_financial_indicators, search_tavily]
model_with_tools = model.bind_tools(tools)

builder = StateGraph(AgentState)
builder.add_node("agent", model_with_tools)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)  # 替代手写 if/else
builder.add_edge("tools", "agent")
```

**注入位置**：阶段 1 的 `akshare_tools.py` 工具声明 + 阶段 2 的 `data_collector` 节点改为 LLM 驱动的工具调用。

#### 3.2.2 MCP 集成（P2，定位为"数据接入层 + 协议展示"）

**为什么值得接**：2026 MCP 占 agentic 工程岗 4%，"面试官：你项目里接了 MCP 对吧？"已成真实面试题。

**验证过的最优做法**（来源：LangChain 官方 langchain-mcp-adapters + Azure-Samples langgraph_mcp.py + mcp-eastmoney README）：

```python
# 数据层通过 MCP 接入，主链路仍是 LangGraph agent
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "eastmoney": {"command": "uvx", "args": ["mcp-eastmoney"], "transport": "stdio"}
})
tools = await client.get_tools()  # 运行时自动发现 schema
# 然后 bind_tools → ToolNode 接入你现有 graph
```

**mcp-eastmoney 5 个工具**（已验证可跑）：实时行情、股票搜索、主力资金排名、板块资金流、K 线。但**不够基本面分析**——如需要财报/新闻，换 `akshare-one-mcp`（含财务报表+新闻，双模式 stdio+HTTP）。

**配套必须写进 README 的 3 个工程决策**（答不出来 = 负分）：
- 为什么选 MCP 而不是把函数写进 agent：多客户端复用 + 运行时工具发现 + 可替换数据源
- 错误处理：ToolMessage 错误回流让模型自纠 + 东财接口熔断退避
- 评测方式：给定 >100 条投研问题的工具调用正确率评测集

**注入位置**：作为阶段 5 的可选子任务（研报 RAG 之后）。

#### 3.2.3 Eval 评测体系（P0，用现有框架扩充）

**为什么必须做**："没有 evals 常常足以丢 offer"（aitechconnect 统计）。LangChain 官方数据：89% 组织有 observability，但只有 52% 跑离线 eval——eval 是稀缺差异点。

你已有 `eval/evaluator.py` + `golden_cases.yaml`，只需要：
- 用 5 只样本股（600196/000001/600519/000333/601318）跑评测
- 指标：端到端延迟、单次 token 成本、六章节完整率、RAG 引用命中率
- 结果写入 `docs/benchmark.md`（实测数字，**空着也不编**）

**注入位置**：阶段 6 收尾。

### 3.3 明确不要做的事（来自真实扣分案例）

| 反模式 | 来源 |
| ------ | ------ |
| ⛔ Redis 存记忆 + TTL 过期删除（"记忆是最珍贵资产，不能当缓存删"——Joye Huang 面试实录） | 真实扣分 |
| ⛔ 无理由微调（尤其培训班标配 Qwen3-8B——"看到就 PTSD"） | 真实扣分 |
| ⛔ 无通信的"多 Agent"（= Workflow 冒充 Multi-Agent，你项目**不是**这个，因为 reviewer→planner 有回流） | 概念陷阱 |
| ⛔ "多 Agent + GraphRAG + 微调 + 图数据库"全家桶但答不上任何一个"为什么" | 真实扣分 |
| ⛔ 简历每个技术点都是洞——"你写了就要能答透" | Joye Huang 实录 |

### 3.4 面试叙事模板（数字实测后填入，不编造）

> "IRIS 是一个 A 股投研信息聚合平台。基础是一个多 Agent 研究助手（Router/Planner/Researcher/Writer/Reviewer 循环 + RAG + SSE 流式 + 多模型降级），
> 我在此基础上新增了 AKShare 数据通道和投研业务能力：财务数据进 LangGraph 状态、中文六章节研报、研报 PDF 入库检索。
> 关键工程决策：① 数据与观点分离——表格数值直接来自数据源 JSON，LLM 只写评述，从机制上防幻觉；
> ② 三层数据降级 + 离线 mock 测试，系统在任何环境下不崩溃；
> ③ 复用现有 Reviewer 审查循环做质量把关，不重复造轮子。
> 评测：5 只样本股实测端到端延迟 Xs、单次成本 ¥Y、六章节完整率 Z%（数字来自 docs/benchmark.md）。"


 第三部分：附录

### A. 安全 Git 工作流（v2 修正：不用 reset --hard）

```bash
# 每阶段结束：
git add -A && git commit -m "..."

# 回退（保留所有文件，不丢工作）：
git checkout <上一阶段tag>            # 暂看旧状态
git switch -c recover-<阶段名>        # 建恢复分支，可继续改

# 查看阶段：
git tag -l
```

**为什么不用 `git reset --hard`**：它会永久删掉工作区未提交文件，阶段中途的新代码会丢失。`checkout`+分支是安全的。

### B. 阶段完成检查表

| 阶段 | Commit 主题 | Tag | 验证通过 |
| ------ | ------------ | ----- | --------- |
| 0 | 基线 | `v0.0-baseline` | ☐ |
| 1 | AKShare 工具层 | `v1.0-akshare-tools` | ☐ |
| 2 | 数据接入图 | `v2.0-data-in-graph` | ☐ |
| 3 | 中文报告 | `v3.0-chinese-report` | ☐ |
| 4 | 前端 Tab | `v4.0-frontend-tab` | ☐ |
| 5 | 聚合增强 | `v5.0-aggregation` | ☐ |
| 6 | 收尾 | `v6.0-release` | ☐ |

### C. 保留的现有资产清单（v2 不动的部分）

| 模块 | 位置 | 价值 |
| ------ | ------ | ------ |
| 多模型降级 + TTL | `app/utils/llm.py` | 生产级 LLM 容错 |
| SSE 流式 + 心跳 + 限流 | `app/api/routes.py` | 生产级 API |
| ChromaDB RAG + Grader | `app/rag/engine.py` + researcher | 引用可追溯 |
| 会话记忆 | `app/utils/memory.py` | 多轮对话 |
| LangSmith 全链路 | `app/graph/graph.py`（已 traceable） | 可观测性 |
| Vue 3 前端 + markdown-it + katex | `frontend/` | 工程化前端 |
| eval 框架 | `eval/evaluator.py` + golden_cases | 评测闭环 |
| Docker + Nginx 部署 | `docker-compose.yml` + `deploy/` | 可部署 |

### D. 风险管理

| 风险 | 影响 | 缓解 |
| ------ | ------ | ------ |
| AKShare 接口/字段名变更 | 数据获取失败 | 三层降级 + 离线 mock 测试 |
| langgraph 1.0.8 与 akshare/gradio 依赖冲突 | 环境破坏 | 阶段内分步 `pip install`，每步验证；冲突则先装 akshare（工具层不依赖 graph 新特性） |
| 延时行情被误当实时 | 合规问题 | 所有行情标注"延时15分钟" |
| 征信:mock 数据出现在演示里被问 | 面试穿帮 | 演示用真实网络；mock 仅在断网降级时有明确"模拟数据"标记 |
| 阶段超时 | 进度延迟 | 每阶段有最小可交付物（工具可单独演示、数据可单独展示） |

### E. 面试叙事模板（数字实测后填入，不编造）

> "IRIS 是一个 A 股投研信息聚合平台。基础是一个多 Agent 研究助手（Router/Planner/Researcher/Writer/Reviewer 循环 + RAG + SSE 流式 + 多模型降级），
> 我在此基础上新增了 AKShare 数据通道和投研业务能力：财务数据进 LangGraph 状态、中文六章节研报、研报 PDF 入库检索。
> 关键工程决策：① 数据与观点分离——表格数值直接来自数据源 JSON，LLM 只写评述，从机制上防幻觉；
> ② 三层数据降级 + 离线 mock 测试，系统在任何环境下不崩溃；
> ③ 复用现有 Reviewer 审查循环做质量把关，不重复造轮子。
> 评测：5 只样本股实测端到端延迟 Xs、单次成本 ¥Y、六章节完整率 Z%（数字来自 docs/benchmark.md）。"

---

## 附：v1 中被删除/修正内容的对照（留痕）

| v1 阶段 | v2 去向 |
| --------- | -------- |
| 阶段 0 基线 | 保留（修正分拣脏提交） |
| 阶段 1 AKShare 数据层 | 保留（修正"替换模拟数据"→"新增数据通道"；测试改离线 mock） |
| 阶段 2 中文报告 | 拆成 v2 阶段 2（数据进图）+ 阶段 3（改格式）——先接数再改格式 |
| 阶段 3 Gradio 前端 | 改为 Vue 新增 Tab；Gradio 降级为可选 demo |
| 阶段 4 多 Agent 并行 | **删除**（现有架构已是多 Agent；如需加分析维度，作为 v2 阶段 5 的可选项） |
| 阶段 5 LangSmith | **删除**（项目已有） |
| 阶段 6 打磨导出 | 保留为 v2 阶段 6（去掉编造的对比实验，改为评测 + benchmark 实测） |
| 附录 D 面试叙事 "快40%/省60%" | 修正：数字留空待实测 |

## 第四部分：附录

### A. 安全 Git 工作流（v2 修正：不用 reset --hard）

```bash
# 每阶段结束：
git add -A && git commit -m "..."

# 回退（保留所有文件，不丢工作）：
git checkout <上一阶段tag>            # 暂看旧状态
git switch -c recover-<阶段名>        # 建恢复分支，可继续改

# 查看阶段：
git tag -l
```

**为什么不用 `git reset --hard`**：它会永久删掉工作区未提交文件，阶段中途的新代码会丢失。`checkout`+分支是安全的。

### B. 阶段完成检查表

| 阶段 | Commit 主题 | Tag | 验证通过 |
| ------ | ------------ | ----- | --------- |
| 0 | 基线 | `v0.0-baseline` | ☐ |
| 1 | AKShare 工具层 | `v1.0-akshare-tools` | ☐ |
| 2 | 数据接入图 | `v2.0-data-in-graph` | ☐ |
| 3 | 中文报告 | `v3.0-chinese-report` | ☐ |
| 4 | 前端 Tab | `v4.0-frontend-tab` | ☐ |
| 5 | 聚合增强 | `v5.0-aggregation` | ☐ |
| 6 | 收尾 | `v6.0-release` | ☐ |

### C. 保留的现有资产清单（v2 不动的部分）

| 模块 | 位置 | 价值 |
| ------ | ------ | ------ |
| 多模型降级 + TTL | `app/utils/llm.py` | 生产级 LLM 容错 |
| SSE 流式 + 心跳 + 限流 | `app/api/routes.py` | 生产级 API |
| ChromaDB RAG + Grader | `app/rag/engine.py` + researcher | 引用可追溯 |
| 会话记忆 | `app/utils/memory.py` | 多轮对话 |
| LangSmith 全链路 | `app/graph/graph.py`（已 traceable） | 可观测性 |
| Vue 3 前端 + markdown-it + katex | `frontend/` | 工程化前端 |
| eval 框架 | `eval/evaluator.py` + golden_cases | 评测闭环 |
| Docker + Nginx 部署 | `docker-compose.yml` + `deploy/` | 可部署 |

### D. 风险管理

| 风险 | 影响 | 缓解 |
| ------ | ------ | ------ |
| AKShare 接口/字段名变更 | 数据获取失败 | 三层降级 + 离线 mock 测试 |
| langgraph 1.0.8 与 akshare/gradio 依赖冲突 | 环境破坏 | 阶段内分步 `pip install`，每步验证；冲突则先装 akshare（工具层不依赖 graph 新特性） |
| 延时行情被误当实时 | 合规问题 | 所有行情标注"延时15分钟" |
| 征信:mock 数据出现在演示里被问 | 面试穿帮 | 演示用真实网络；mock 仅在断网降级时有明确"模拟数据"标记 |
| 阶段超时 | 进度延迟 | 每阶段有最小可交付物（工具可单独演示、数据可单独展示） |

### E. 面试叙事模板（数字实测后填入，不编造）

> "IRIS 是一个 A 股投研信息聚合平台。基础是一个多 Agent 研究助手（Router/Planner/Researcher/Writer/Reviewer 循环 + RAG + SSE 流式 + 多模型降级），
> 我在此基础上新增了 AKShare 数据通道和投研业务能力：财务数据进 LangGraph 状态、中文六章节研报、研报 PDF 入库检索。
> 关键工程决策：① 数据与观点分离——表格数值直接来自数据源 JSON，LLM 只写评述，从机制上防幻觉；
> ② 三层数据降级 + 离线 mock 测试，系统在任何环境下不崩溃；
> ③ 复用现有 Reviewer 审查循环做质量把关，不重复造轮子。
> 评测：5 只样本股实测端到端延迟 Xs、单次成本 ¥Y、六章节完整率 Z%（数字来自 docs/benchmark.md）。"

---

## 附：v1 中被删除/修正内容的对照（留痕）

| v1 阶段 | v2 去向 |
| --------- | -------- |
| 阶段 0 基线 | 保留（修正分拣脏提交） |
| 阶段 1 AKShare 数据层 | 保留（修正"替换模拟数据"→"新增数据通道"；测试改离线 mock） |
| 阶段 2 中文报告 | 拆成 v2 阶段 2（数据进图）+ 阶段 3（改格式）——先接数再改格式 |
| 阶段 3 Gradio 前端 | 改为 Vue 新增 Tab；Gradio 降级为可选 demo |
| 阶段 4 多 Agent 并行 | **删除**（现有架构已是多 Agent；如需加分析维度，作为 v2 阶段 5 的可选项） |
| 阶段 5 LangSmith | **删除**（项目已有） |
| 阶段 6 打磨导出 | 保留为 v2 阶段 6（去掉编造的对比实验，改为评测 + benchmark 实测） |
| 附录 D 面试叙事 "快40%/省60%" | 修正：数字留空待实测 |

---

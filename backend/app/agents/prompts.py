"""
中文投研报告提示词模板

六章节券商研报格式：
一、核心结论与投资摘要
二、公司概况（表格：指标|数值|来源）
三、财务分析（营收/盈利/偿债/现金流）
四、行业观点与竞争格局
五、风险提示（⚠️ 数据不足时标注）
六、投资建议（仅供参考）+ 免责声明

设计原则：
- 数据与观点分离：表格数值直接来自 financial_data JSON（不经 LLM 改写）
- 来源标注：所有数值标注 [来源: AKShare/东方财富]
- 诚实告知：数据缺失维度标注「⚠️ 数据不足，暂不评价」
- 免责声明：强制追加，不可省略
"""

# ============================================================
# 六章节中文研报 System Prompt
# ============================================================
CHINESE_REPORT_SYSTEM_PROMPT = """你是国内顶级券商研究所的首席分析师，专精于撰写A股投资分析报告。

## 你的任务
基于以下全部信息，撰写一份专业、结构完整的投资分析报告。

## 报告结构（必须严格遵循）

### 一、核心结论与投资摘要
- 提炼最关键的投资观点（3-5条）
- 用一两句话总结整体判断

### 二、公司概况
- 主营业务、行业定位、竞争优势
- 使用表格展示关键信息（指标 | 数值 | 来源）
- 标注信息来源：[来源: AKShare/东方财富]

### 三、财务分析
- 营收趋势、盈利质量、偿债能力
- 关键财务指标同比/环比变化
- 数据不足的指标明确标注「⚠️ 数据不足，暂不评价」
- 严禁编造具体数值

### 四、行业观点与竞争格局
- 行业趋势判断
- 公司行业地位评估
- 引用网络搜索结果中的行业数据

### 五、风险提示
- 按重要性排序，列出3-5条核心风险
- 区分系统性风险与个股风险
- ⚠️ 数据不足的维度必须标注「数据不足，暂不评价」

### 六、投资建议（仅供参考）
- 综合以上分析给出参考观点
- **必须包含免责声明**：「本报告仅供参考，不构成投资建议」

## 风格要求
- 专业严谨，符合国内券商研报表述规范
- 数据引用时标注来源（[来源: AKShare 东方财富] / [来源: 网络搜索]）
- 不确定性使用「可能」「预计」「或」等措辞
- 严禁编造数据、指标具体数值
- 使用 Markdown 格式，全文中文
"""

# ============================================================
# 免责声明（强制追加）
# ============================================================
DISCLAIMER = """
---

> ⚠️ **免责声明**: 本报告由 IRIS 智能投研系统自动生成，
> 仅供学习研究参考，不构成任何投资建议。
> 股市有风险，投资需谨慎。
"""

# ============================================================
# 数据与观点分离：从 financial_data 生成表格
# ============================================================
def build_financial_tables(financial_data: dict) -> str:
    """
    从 financial_data JSON 生成 Markdown 表格（不经 LLM 改写，防幻觉）。

    返回包含公司概况表、财务指标表的 Markdown 字符串。
    """
    if not financial_data or not financial_data.get("stock_code"):
        return ""

    sections = []
    stock_code = financial_data.get("stock_code", "")

    # ---- 公司概况表 ----
    info = financial_data.get("stock_info", {})
    if info:
        rows = []
        # 关键字段映射（中文显示名 -> info 中的 key）
        key_mapping = {
            "公司名称": "公司名称",
            "公司全称": "公司全称",
            "所属行业": "所属行业",
            "上市日期": "上市日期",
            "总股本": "总股本",
            "流通股本": "流通股本",
            "主营业务": "主营业务",
            "员工人数": "员工人数",
        }
        for display_name, info_key in key_mapping.items():
            value = info.get(info_key, "")
            if value and value.lower() not in ("none", "nan", "n/a", ""):
                source = info.get("data_source", "AKShare")
                rows.append(f"| {display_name} | {value} | [来源: {source}] |")

        if rows:
            header = "| 指标 | 数值 | 来源 |\n|------|------|------|"
            sections.append(f"### 公司概况\n{header}\n" + "\n".join(rows))

    # ---- 财务指标表 ----
    indicators = financial_data.get("indicators", {})
    if indicators:
        rows = []
        key_mapping = {
            "报告期": "report_period",
            "营业总收入": "total_revenue",
            "营收同比增长": "revenue_yoy_growth",
            "归母净利润": "net_profit",
            "净利润同比增长": "net_profit_yoy_growth",
            "毛利率": "gross_margin",
            "净利率": "net_margin",
            "ROE": "roe",
            "EPS": "eps",
        }
        for display_name, ind_key in key_mapping.items():
            value = indicators.get(ind_key, "")
            if value and value.lower() not in ("none", "nan", "n/a", ""):
                source = indicators.get("data_source", "AKShare")
                rows.append(f"| {display_name} | {value} | [来源: {source}] |")

        if rows:
            header = "| 指标 | 数值 | 来源 |\n|------|------|------|"
            sections.append(f"### 财务指标\n{header}\n" + "\n".join(rows))

    # ---- 行情快照表 ----
    quote = financial_data.get("quote", {})
    if quote:
        rows = []
        key_mapping = {
            "最新价": "最新价",
            "涨跌幅": "涨跌幅",
            "涨跌额": "涨跌额",
            "成交量": "成交量",
            "成交额": "成交额",
            "换手率": "换手率",
            "市盈率": "市盈率-动态",
            "市净率": "市净率",
            "总市值": "总市值",
            "流通市值": "流通市值",
        }
        for display_name, q_key in key_mapping.items():
            value = quote.get(q_key, "")
            if value and value.lower() not in ("none", "nan", "n/a", ""):
                source = quote.get("data_source", "AKShare")
                rows.append(f"| {display_name} | {value} | [来源: {source}] |")

        if rows:
            header = "| 指标 | 数值 | 来源 |\n|------|------|------|"
            delay = quote.get("延时", "15分钟")
            sections.append(f"### 行情快照（延时 {delay}）\n{header}\n" + "\n".join(rows))

    return "\n\n".join(sections)


# ============================================================
# 数据源标注生成
# ============================================================
def build_data_source_tags(data_sources: list) -> str:
    """根据 data_sources 列表生成来源标注说明"""
    if not data_sources:
        return ""

    tags = []
    for source in data_sources:
        if "东方财富" in source:
            tags.append(f"- [来源: {source}]")
        elif "雪球" in source or "新浪" in source:
            tags.append(f"- [来源: {source}]（备用数据源）")
        elif "模拟" in source:
            tags.append(f"- [来源: {source}]")
        else:
            tags.append(f"- [来源: {source}]")

    return "\n".join(tags)

"""
测试中文投研报告格式

验证:
1. build_financial_tables 从 financial_data JSON 生成 Markdown 表格
2. 免责声明强制追加
3. 报告包含六个章节
"""
import pytest

from app.agents.prompts import (
    build_financial_tables,
    build_data_source_tags,
    DISCLAIMER,
    CHINESE_REPORT_SYSTEM_PROMPT,
)
from app.graph.state import AgentState


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def sample_financial_data():
    """样本 financial_data"""
    return {
        "stock_code": "600196",
        "stock_info": {
            "公司名称": "复星医药",
            "所属行业": "医药制造业",
            "上市日期": "1998-08-07",
            "总股本": "25.6亿股",
            "data_source": "AKShare (东方财富)",
        },
        "indicators": {
            "stock_code": "600196",
            "report_period": "2024-09-30",
            "total_revenue": "309.21亿",
            "revenue_yoy_growth": "+5.73%",
            "net_profit": "31.85亿",
            "roe": "7.82%",
            "eps": "1.24元",
            "data_source": "AKShare (东方财富利润表)",
        },
        "quote": {
            "stock_code": "600196",
            "最新价": "25.30",
            "涨跌幅": "+1.2%",
            "换手率": "1.5%",
            "总市值": "648亿",
            "延时": "15分钟",
            "data_source": "AKShare (东方财富)",
        },
    }


@pytest.fixture
def base_state():
    """基础 AgentState"""
    return AgentState(
        query="分析复星医药 600196 的投资价值",
        plan=["搜索医药行业数据"],
        search_results=["### 网络搜索结果\n医药行业稳步增长\n"],
        final_report="",
        critique="",
        revision_number=0,
        review_status="PASS",
        search_mode="hybrid",
        should_stop=False,
        conversation_summary="",
        error_code="",
        degraded=False,
        failed_tools=[],
        early_stop=False,
        should_continue=True,
        report_history=[],
        tool_status={},
        preferences={"style": "detailed", "language": "zh"},
        financial_data={},
        data_sources=[],
        pending_stock_code="",
        error_log=[],
    )


# ============================================================
# 测试: build_financial_tables
# ============================================================
class TestBuildFinancialTables:
    def test_generates_company_info_table(self, sample_financial_data):
        """验证生成公司概况表"""
        tables = build_financial_tables(sample_financial_data)
        assert "公司概况" in tables
        assert "复星医药" in tables
        assert "医药制造业" in tables
        assert "[来源:" in tables

    def test_generates_financial_indicators_table(self, sample_financial_data):
        """验证生成财务指标表"""
        tables = build_financial_tables(sample_financial_data)
        assert "财务指标" in tables
        assert "309.21亿" in tables
        assert "7.82%" in tables

    def test_generates_quote_table(self, sample_financial_data):
        """验证生成行情快照表"""
        tables = build_financial_tables(sample_financial_data)
        assert "行情快照" in tables
        assert "25.30" in tables
        assert "15分钟" in tables

    def test_empty_data_returns_empty_string(self):
        """空数据返回空字符串"""
        assert build_financial_tables({}) == ""
        assert build_financial_tables({"stock_code": ""}) == ""

    def test_source_attribution(self, sample_financial_data):
        """验证来源标注"""
        tables = build_financial_tables(sample_financial_data)
        assert "AKShare (东方财富)" in tables


# ============================================================
# 测试: build_data_source_tags
# ============================================================
class TestBuildDataSourceTags:
    def test_generates_tags(self):
        """验证生成来源标注"""
        sources = ["AKShare (东方财富)", "AKShare (雪球备用)"]
        tags = build_data_source_tags(sources)
        assert "AKShare (东方财富)" in tags
        assert "备用数据源" in tags

    def test_empty_sources(self):
        """空列表返回空字符串"""
        assert build_data_source_tags([]) == ""


# ============================================================
# 测试: DISCLAIMER
# ============================================================
class TestDisclaimer:
    def test_disclaimer_present(self):
        """验证免责声明存在"""
        assert "免责声明" in DISCLAIMER
        assert "不构成" in DISCLAIMER

# ============================================================
# 测试: CHINESE_REPORT_SYSTEM_PROMPT
# ============================================================
class TestChineseReportPrompt:
    def test_contains_six_sections(self):
        """验证包含六个章节"""
        sections = ["核心结论", "公司概况", "财务分析", "行业观点", "风险提示", "投资建议"]
        for section in sections:
            assert section in CHINESE_REPORT_SYSTEM_PROMPT

    def test_contains_source_attribution_requirement(self):
        """验证包含来源标注要求"""
        assert "来源" in CHINESE_REPORT_SYSTEM_PROMPT

    def test_contains_data_shortage_instruction(self):
        """验证包含数据不足标注要求"""
        assert "数据不足" in CHINESE_REPORT_SYSTEM_PROMPT

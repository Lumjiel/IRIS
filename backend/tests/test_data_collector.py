"""
DataCollector 节点单元测试 — 全部 mock，不依赖真实网络

使用 unittest.mock 模拟 AKShare 工具返回，确保测试离线可跑。
"""
import json
import pytest
from unittest.mock import patch

from app.graph.state import AgentState
from app.graph.nodes.data_collector import data_collector_node, _extract_stock_code


# ============================================================
# Fixtures
# ============================================================
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


def _make_success_result(data_type: str, payload: dict) -> str:
    """构造工具成功返回的 JSON"""
    if data_type == "info":
        return json.dumps({"error": False, "info": payload, "data_source": "AKShare (东方财富)"})
    elif data_type == "financial":
        return json.dumps({"error": False, "indicators": payload})
    elif data_type == "quote":
        return json.dumps({"error": False, "quote": payload})
    return "{}"


# ============================================================
# 测试: _extract_stock_code
# ============================================================
class TestExtractStockCode:
    def test_extract_from_pending_code(self, base_state):
        """优先使用 pending_stock_code"""
        base_state["pending_stock_code"] = "600196"
        assert _extract_stock_code(base_state) == "600196"

    def test_extract_from_query(self, base_state):
        """从 query 中正则匹配"""
        base_state["query"] = "分析复星医药 600196"
        assert _extract_stock_code(base_state) == "600196"

    def test_extract_none(self, base_state):
        """无股票代码时返回空"""
        base_state["query"] = "今天天气怎么样"
        assert _extract_stock_code(base_state) == ""

    def test_extract_shenzhen_code(self, base_state):
        """深市代码 00xxxx"""
        base_state["query"] = "分析 000001"
        assert _extract_stock_code(base_state) == "000001"


# ============================================================
# 测试: data_collector_node
# ============================================================
class TestDataCollectorNode:
    def test_writes_financial_data(self, base_state):
        """验证写入 financial_data 和 data_sources"""
        base_state["query"] = "分析 600196"

        # Mock AKShare 工具返回
        mock_info = {"公司名称": "复星医药", "行业": "医药制造"}
        mock_fin = {"stock_code": "600196", "roe": "7.82%", "data_source": "AKShare (东方财富)"}
        mock_quote = {"最新价": "25.30", "涨跌幅": "+1.2%", "data_source": "AKShare (东方财富)"}

        with patch("app.graph.nodes.data_collector.query_stock_info") as mock_info_fn, \
             patch("app.graph.nodes.data_collector.query_financial_indicators") as mock_fin_fn, \
             patch("app.graph.nodes.data_collector.query_stock_quote") as mock_quote_fn:

            mock_info_fn.invoke.return_value = _make_success_result("info", mock_info)
            mock_fin_fn.invoke.return_value = _make_success_result("financial", mock_fin)
            mock_quote_fn.invoke.return_value = _make_success_result("quote", mock_quote)

            result = data_collector_node(base_state)

        assert result["financial_data"]["stock_code"] == "600196"
        assert result["financial_data"]["stock_info"]["公司名称"] == "复星医药"
        assert result["financial_data"]["indicators"]["roe"] == "7.82%"
        assert result["financial_data"]["quote"]["最新价"] == "25.30"
        assert len(result["data_sources"]) > 0

    def test_skips_when_no_stock_code(self, base_state):
        """无股票代码时跳过"""
        base_state["query"] = "今天天气怎么样"
        result = data_collector_node(base_state)
        assert result["financial_data"] == {}
        assert result["data_sources"] == []

    def test_skips_when_already_has_data(self, base_state):
        """已有数据时跳过重复拉取"""
        base_state["financial_data"] = {"stock_code": "600196", "stock_info": {"公司名称": "复星医药"}}
        base_state["data_sources"] = ["AKShare"]

        result = data_collector_node(base_state)
        # 应该返回已有数据，不重新拉取
        assert result["financial_data"]["stock_code"] == "600196"
        assert result["financial_data"]["stock_info"]["公司名称"] == "复星医药"
    def test_failure_degrades_gracefully(self, base_state):
        """工具失败时降级不中断"""
        base_state["query"] = "分析 600196"

        with patch("app.graph.nodes.data_collector.query_stock_info") as mock_info_fn, \
             patch("app.graph.nodes.data_collector.query_financial_indicators") as mock_fin_fn, \
             patch("app.graph.nodes.data_collector.query_stock_quote") as mock_quote_fn:

            # 所有工具都失败
            mock_info_fn.invoke.return_value = json.dumps({"error": True, "message": "网络错误"})
            mock_fin_fn.invoke.return_value = json.dumps({"error": True, "message": "网络错误"})
            mock_quote_fn.invoke.return_value = json.dumps({"error": True, "message": "网络错误"})

            result = data_collector_node(base_state)

        # 不应该抛异常，而是记录 error_log
        assert "financial_data" in result
        assert "error_log" in result
        assert len(result["error_log"]) > 0  # 记录了错误

    def test_degraded_mock_data_recorded(self, base_state):
        """mock 降级数据（degraded=True）应被接受，但必须写入 error_log 提示非真实数据"""
        base_state["query"] = "分析 600196"

        with patch("app.graph.nodes.data_collector.query_stock_info") as mock_info_fn, \
             patch("app.graph.nodes.data_collector.query_financial_indicators") as mock_fin_fn, \
             patch("app.graph.nodes.data_collector.query_stock_quote") as mock_quote_fn:

            mock_info_fn.invoke.return_value = json.dumps({"error": False, "degraded": True, "info": {"公司名称": "示例公司"}, "data_source": "内置模拟数据"})
            mock_fin_fn.invoke.return_value = json.dumps({"error": False, "degraded": True, "indicators": {"stock_code": "600196", "roe": "模拟数据"}})
            mock_quote_fn.invoke.return_value = json.dumps({"error": False, "degraded": True, "quote": {"最新价": "模拟", "data_source": "内置模拟数据"}})

            result = data_collector_node(base_state)

        # 数据被接受（演示模式可用）
        assert result["financial_data"]["stock_info"]["公司名称"] == "示例公司"
        # 但降级必须被记录，不能静默流入报告
        assert len(result["error_log"]) == 3
        assert all("模拟数据" in entry for entry in result["error_log"])

    def test_partial_success(self, base_state):
        """部分成功：一个工具失败不影响其他"""
        base_state["query"] = "分析 600196"

        mock_info = {"公司名称": "复星医药"}

        with patch("app.graph.nodes.data_collector.query_stock_info") as mock_info_fn, \
             patch("app.graph.nodes.data_collector.query_financial_indicators") as mock_fin_fn, \
             patch("app.graph.nodes.data_collector.query_stock_quote") as mock_quote_fn:

            mock_info_fn.invoke.return_value = _make_success_result("info", mock_info)
            mock_fin_fn.invoke.return_value = json.dumps({"error": True, "message": "失败"})
            mock_quote_fn.invoke.return_value = json.dumps({"error": True, "message": "失败"})

            result = data_collector_node(base_state)

        # 成功的工具数据应该被保留
        assert result["financial_data"]["stock_info"]["公司名称"] == "复星医药"
        # 失败的工具有 error_log
        assert len(result["error_log"]) == 2

"""
AKShare 工具层单元测试 — 全部 mock，不依赖真实网络

使用直接属性赋值模拟 AKShare 返回，确保测试离线可跑、CI 稳定。
注意：@tool 装饰器将函数转为 StructuredTool，需用 .invoke() 调用。
"""
import json
import pytest

# 模拟 akshare 模块（避免真实网络调用）
import sys
import types

# 创建 mock akshare 模块
mock_ak = types.ModuleType("akshare")
sys.modules["akshare"] = mock_ak

from app.tools.akshare_tools import (
    query_stock_info,
    query_financial_indicators,
    query_stock_quote,
    _get_mock_info,
    _get_mock_financial,
    _get_mock_quote,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture(autouse=True)
def reset_mock_ak():
    """每个测试前重置 mock_ak 的属性"""
    # 清除所有可能存在的属性
    for attr in list(vars(mock_ak).keys()):
        if not attr.startswith("_"):
            delattr(mock_ak, attr)
    yield


@pytest.fixture
def mock_akshare_em_success():
    """模拟东方财富接口成功返回（不依赖真实 pandas）"""
    # 创建 mock DataFrame，模拟 pandas DataFrame 的最小接口
    class MockDataFrame:
        def __init__(self, data):
            self._data = data
            self.empty = False
        def iterrows(self):
            for i, row in enumerate(zip(*self._data.values())):
                yield i, dict(zip(self._data.keys(), row))
    
    def fake_em(symbol):
        return MockDataFrame({
            "item": ["公司名称", "行业", "上市日期"],
            "value": ["复星医药", "医药制造业", "1998-08-07"],
        })
    
    mock_ak.stock_individual_info_em = fake_em

@pytest.fixture
def mock_akshare_all_fail():
    """模拟所有数据源失败（网络不可用）"""
    def boom(*args, **kwargs):
        raise ConnectionError("网络不可用")

    mock_ak.stock_individual_info_em = boom
    mock_ak.stock_individual_basic_info_xq = boom
    mock_ak.stock_profit_sheet_by_report_em = boom
    mock_ak.stock_financial_analysis_indicator = boom
    mock_ak.stock_zh_a_spot_em = boom
    mock_ak.stock_zh_a_spot_sina = boom


# ============================================================
# 测试: query_stock_info
# ============================================================
class TestQueryStockInfo:
    def test_returns_valid_json(self):
        """验证返回格式正确（JSON 可解析）"""
        result = query_stock_info.invoke("600196")
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "error" in data
        assert "stock_code" in data
        assert "info" in data
        assert "data_source" in data

    def test_em_success_path(self, mock_akshare_em_success):
        """正常路径：东方财富接口成功"""
        result = query_stock_info.invoke("600196")
        data = json.loads(result)
        assert data["error"] is False
        assert data["stock_code"] == "600196"
        assert data["info"]["公司名称"] == "复星医药"
        assert data["info"]["行业"] == "医药制造业"
        assert "东方财富" in data["data_source"]

    def test_fallback_to_mock(self, mock_akshare_all_fail):
        """降级路径：全部数据源失败 → 模拟数据且标注来源"""
        result = query_stock_info.invoke("600196")
        data = json.loads(result)
        assert data["error"] is False
        assert data["stock_code"] == "600196"
        assert "模拟" in data["data_source"]
        assert "公司名称" in data["info"]

    def test_never_raises(self, mock_akshare_all_fail):
        """工具永不抛异常（关键断言）"""
        # 即使所有数据源爆炸，也不该 raise
        result = query_stock_info.invoke("600196")
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["error"] is False


# ============================================================
# 测试: query_financial_indicators
# ============================================================
class TestQueryFinancialIndicators:
    def test_returns_valid_json(self):
        """验证返回格式正确"""
        result = query_financial_indicators.invoke("600196")
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "error" in data
        assert "indicators" in data

    def test_fallback_to_mock(self, mock_akshare_all_fail):
        """降级路径：全部数据源失败 → 模拟数据"""
        result = query_financial_indicators.invoke("600196")
        data = json.loads(result)
        assert data["error"] is False
        assert "模拟" in data["indicators"].get("data_source", "")

    def test_never_raises(self, mock_akshare_all_fail):
        """工具永不抛异常"""
        result = query_financial_indicators.invoke("600196")
        assert isinstance(result, str)


# ============================================================
# 测试: query_stock_quote
# ============================================================
class TestQueryStockQuote:
    def test_returns_valid_json(self):
        """验证返回格式正确"""
        result = query_stock_quote.invoke("600196")
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "error" in data
        assert "quote" in data

    def test_fallback_to_mock(self, mock_akshare_all_fail):
        """降级路径：全部数据源失败 → 模拟数据"""
        result = query_stock_quote.invoke("600196")
        data = json.loads(result)
        assert data["error"] is False
        assert "模拟" in data["quote"].get("data_source", "")

    def test_never_raises(self, mock_akshare_all_fail):
        """工具永不抛异常"""
        result = query_stock_quote.invoke("600196")
        assert isinstance(result, str)


# ============================================================
# 测试: 模拟数据兜底
# ============================================================
class TestMockFallback:
    def test_mock_info_contains_stock_code(self):
        """模拟数据包含股票代码"""
        info = _get_mock_info("600196")
        assert info["股票代码"] == "600196"
        assert "公司名称" in info

    def test_mock_financial_contains_stock_code(self):
        """模拟财务数据包含股票代码"""
        fin = _get_mock_financial("000001")
        assert fin["stock_code"] == "000001"
        assert "data_source" in fin

    def test_mock_quote_contains_delay_flag(self):
        """模拟行情标注延时"""
        quote = _get_mock_quote("600196")
        assert "延时" in quote
        assert "模拟" in quote["data_source"]

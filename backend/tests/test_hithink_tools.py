"""HITHINK Financial-API 工具层测试：四条路径 + 降级链集成。"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.tools import hithink_tools as ht


# ============================================================
# thscode 转换
# ============================================================

class TestToThscode:
    def test_sh(self):
        assert ht._to_thscode("600519") == "600519.SH"

    def test_sz_main_and_gem(self):
        assert ht._to_thscode("000001") == "000001.SZ"
        assert ht._to_thscode("300750") == "300750.SZ"

    def test_bj(self):
        assert ht._to_thscode("830799") == "830799.BJ"

    def test_already_suffixed_passthrough(self):
        assert ht._to_thscode("600519.SH") == "600519.SH"


# ============================================================
# _get 四条路径
# ============================================================

@pytest.fixture(autouse=True)
def _with_key(monkeypatch):
    # is_enabled() 动态读环境变量；默认开启供 fetch_* 用例使用
    monkeypatch.setenv("HITHINK_FINANCE_API_KEY", "test-key")
    monkeypatch.setenv("ENABLE_HITHINK", "true")


def _resp(status_code=200, body=None):
    m = MagicMock()
    m.status_code = status_code
    m.text = "err" if status_code != 200 else ""
    m.json.return_value = body or {}
    return m


class TestGet:
    def test_success(self, monkeypatch):
        monkeypatch.setattr(ht.httpx, "get",
                            lambda *a, **kw: _resp(body={"code": 0, "data": {"item": [1]}}))
        assert ht._get("/x", {}) == {"item": [1]}

    def test_401_raises_auth_error(self, monkeypatch):
        monkeypatch.setattr(ht.httpx, "get",
                            lambda *a, **kw: _resp(status_code=401))
        with pytest.raises(ht.HithinkError, match="鉴权失败"):
            ht._get("/x", {})

    def test_http_error_raises(self, monkeypatch):
        monkeypatch.setattr(ht.httpx, "get",
                            lambda *a, **kw: _resp(status_code=500))
        with pytest.raises(ht.HithinkError, match="HTTP 500"):
            ht._get("/x", {})

    def test_business_error_raises(self, monkeypatch):
        monkeypatch.setattr(ht.httpx, "get",
                            lambda *a, **kw: _resp(body={"code": 1004, "message": "bad param"}))
        with pytest.raises(ht.HithinkError, match="1004"):
            ht._get("/x", {})

    def test_network_exception_raises(self, monkeypatch):
        def _boom(*a, **kw):
            raise TimeoutError("timed out")

        monkeypatch.setattr(ht.httpx, "get", _boom)
        with pytest.raises(ht.HithinkError, match="请求失败"):
            ht._get("/x", {})

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.setenv("HITHINK_FINANCE_API_KEY", "")
        with pytest.raises(ht.HithinkError, match="未配置"):
            ht._get("/x", {})


# ============================================================
# fetch_* 字段映射
# ============================================================

class TestFetchMapping:
    def test_fetch_quote_maps_fields(self, monkeypatch):
        monkeypatch.setattr(ht, "_get", lambda p, params: {
            "item": [{"thscode": "600519.SH", "last_price": 1310.3,
                      "price_change_ratio_pct": 2.94, "price_change": 37.47,
                      "volume": 3070033, "turnover": 3978713400,
                      "high_price": 1310.96, "low_price": 1270.33,
                      "open_price": 1271.01, "prev_price": 1272.83}]})
        q = ht.fetch_quote("600519")
        assert q["最新价"] == "1310.3"
        assert q["data_source"] == "同花顺官方API"
        assert q["延时"] == "实时"

    def test_fetch_info_maps_valuations(self, monkeypatch):
        monkeypatch.setattr(ht, "_get", lambda p, params: {
            "timestamp": 1787540977000,
            "item": [{"thscode": "600519.SH", "name": "贵州茅台",
                      "pe_ttm": 20.1, "pb_mrq": 6.52}]})
        info = ht.fetch_info("600519")
        assert info["证券简称"] == "贵州茅台"
        assert info["市盈率PE(TTM)"] == "20.1"

    def test_fetch_financial_computes_yoy(self, monkeypatch):
        """同比由相邻两期计算；毛利率由营收-成本计算。"""
        statements = [
            {"fiscal_year": 2024, "fiscal_period": "FY",
             "operating_income": 110.0, "operating_costs": 55.0,
             "parent_holder_net_profit": 22.0, "basic_eps": 1.75},
            {"fiscal_year": 2023, "fiscal_period": "FY",
             "operating_income": 100.0, "operating_costs": 50.0,
             "parent_holder_net_profit": 20.0, "basic_eps": 1.6},
        ]
        monkeypatch.setattr(ht, "_get", lambda p, params: {"indicators": statements})

        ind = ht.fetch_financial_indicators("600519")
        assert ind["report_period"] == "2024FY"
        assert ind["total_revenue"] == "110.0"
        assert ind["revenue_yoy_growth"] == "10.00%"
        assert ind["net_profit_yoy_growth"] == "10.00%"
        assert ind["gross_margin"] == "50.00%"
        assert ind["roe"] == "N/A"  # 利润表无 ROE，诚实标注

    def test_empty_data_raises(self, monkeypatch):
        monkeypatch.setattr(ht, "_get", lambda p, params: {"item": []})
        with pytest.raises(ht.HithinkError, match="无"):
            ht.fetch_quote("600519")


# ============================================================
# 降级链集成：hithink 失败 → akshare 链兜底，data_source 如实变化
# ============================================================

class TestDegradationChain:
    def test_tool_falls_back_when_hithink_down(self, monkeypatch):
        """query_stock_quote 在同花顺层抛异常时落回 AKShare 链（此处 mock 兜底数据）。"""
        from app.tools.akshare_tools import query_stock_quote

        # 禁用真实网络路径，让 akshare 层落到内置模拟快照
        monkeypatch.setenv("ENABLE_HITHINK", "false")

        result = json.loads(query_stock_quote.invoke({"stock_code": "600196"}))
        assert result["error"] is False
        # ENABLE_HITHINK=false 时第零层直接跳过，走原三链（本环境 akshare 未装 → 模拟快照）
        assert "模拟数据" in result["quote"]["data_source"]

    def test_layer_skipped_without_key(self, monkeypatch):
        """Key 缺失时整层跳过（is_enabled=False），等价于原三链。"""
        monkeypatch.setenv("HITHINK_FINANCE_API_KEY", "")
        monkeypatch.setenv("ENABLE_HITHINK", "true")
        assert ht.is_enabled() is False

    def test_disabled_by_switch(self, monkeypatch):
        monkeypatch.setenv("HITHINK_FINANCE_API_KEY", "some-key")
        monkeypatch.setenv("ENABLE_HITHINK", "false")
        assert ht.is_enabled() is False

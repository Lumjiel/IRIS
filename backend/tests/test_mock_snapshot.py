"""mock_snapshot.py 快照兜底数据测试。"""


class TestMockSnapshot:
    """快照数据完整性与降级标记测试。"""

    def test_known_stock_returns_snapshot(self):
        from app.tools.mock_snapshot import get_snapshot
        snap = get_snapshot("600196")
        assert snap["info"]["公司名称"] == "复星医药"
        assert len(snap["news"]) > 0

    def test_unknown_code_falls_back_to_generic(self):
        from app.tools.mock_snapshot import get_snapshot
        snap = get_snapshot("999999")
        assert snap["info"]["公司名称"] == "样本公司"

    def test_mock_info_has_degradation_marker(self):
        """data_source 必须含「模拟」，否则 degraded 检测被绕过。"""
        from app.tools.mock_snapshot import get_mock_info
        data = get_mock_info("600196")
        assert "模拟" in data["data_source"]
        assert data["公司名称"] == "复星医药"

    def test_mock_financial_schema_matches_real_path(self):
        """financial 字段需与真实接口 schema 一致（下游按这些 key 取数）。"""
        from app.tools.mock_snapshot import get_mock_financial
        data = get_mock_financial("600519")
        for key in ("stock_code", "report_period", "total_revenue",
                    "net_profit", "gross_margin", "roe", "eps"):
            assert key in data, f"缺少字段: {key}"
        assert data["stock_code"] == "600519"

    def test_mock_quote_schema_matches_real_path(self):
        """quote 字段需与东财/新浪路径 schema 一致。"""
        from app.tools.mock_snapshot import get_mock_quote
        data = get_mock_quote("000001")
        for key in ("最新价", "涨跌幅", "换手率", "市盈率-动态", "市净率",
                    "总市值", "流通市值", "延时"):
            assert key in data, f"缺少字段: {key}"

    def test_mock_news_returns_copies(self):
        """返回副本而非内部引用，避免调用方修改污染全局快照。"""
        from app.tools.mock_snapshot import get_mock_news
        a = get_mock_news("600196")
        b = get_mock_news("600196")
        assert a == b
        assert a is not b

    def test_akshare_tools_mock_delegates(self):
        """akshare_tools._get_mock_* 应委托到快照模块。"""
        from app.tools.akshare_tools import _get_mock_info, _get_mock_quote, _get_mock_news
        assert "模拟" in _get_mock_info("600196")["data_source"]
        assert _get_mock_quote("600196")["最新价"] == "26.85"
        assert len(_get_mock_news("600196")) >= 3

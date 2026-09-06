"""/api/status 数据源在线判定回归测试。

背景（2026-09 修复）：数据链升级为「同花顺 L0 + 腾讯补充」后，
旧判定 `"AKShare" in source or "雪球" in source` 永远为 False，
侧栏误显示「内置模拟数据」。新语义：探到非 Mock/异常的真实数据源即在线。
"""
from unittest.mock import MagicMock, patch

from app.api import routes


def _tool_return(source: str):
    """query_stock_quote 是 pydantic 冻结的 StructuredTool，整体替换而非改其属性。"""
    import json

    return MagicMock(invoke=lambda _code: json.dumps({"quote": {"data_source": source}}))


class TestSystemStatus:
    def setup_method(self):
        routes._status_cache["data"] = None
        routes._status_cache["ts"] = 0

    async def test_hithink_source_is_online(self):
        """同花顺 L0（含腾讯补充）必须判定为在线——服务器实际链路。"""
        with patch.object(routes, "query_stock_quote", _tool_return("同花顺官方API·腾讯行情补充")):
            payload = await routes.system_status()
        assert payload["data_online"] is True
        assert payload["data_source"] == "同花顺官方API·腾讯行情补充"

    async def test_akshare_source_is_online(self):
        with patch.object(routes, "query_stock_quote", _tool_return("AKShare(东方财富)")):
            payload = await routes.system_status()
        assert payload["data_online"] is True

    async def test_mock_source_is_offline(self):
        with patch.object(routes, "query_stock_quote", _tool_return("内置模拟数据")):
            payload = await routes.system_status()
        assert payload["data_online"] is False

    async def test_probe_exception_is_offline(self):
        tool = MagicMock(invoke=MagicMock(side_effect=RuntimeError("boom")))
        with patch.object(routes, "query_stock_quote", tool):
            payload = await routes.system_status()
        assert payload["data_online"] is False

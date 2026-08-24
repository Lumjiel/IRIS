"""行情页批量快照：fetch_quotes_batch 工具层 + /market/snapshot 路由层。

覆盖：字段映射、上限保护、批量命中、逐股降级兜底、单股失败隔离（fail-open）。
"""
import json
from unittest.mock import patch

import pytest

from app.tools import hithink_tools as ht


def _hithink_quote(code, price="10.0", pct="1.5"):
    return {
        "stock_code": code,
        "最新价": price,
        "涨跌幅": pct,
        "data_source": "同花顺官方API",
    }


@pytest.fixture(autouse=True)
def _enable_hithink(monkeypatch):
    monkeypatch.setenv("ENABLE_HITHINK", "true")
    monkeypatch.setenv("HITHINK_FINANCE_API_KEY", "test-key")


# ============================================================
# 工具层：fetch_quotes_batch
# ============================================================

class TestFetchQuotesBatch:
    def test_maps_fields_and_reverse_lookup(self, monkeypatch):
        """返回按原始入参代码（6 位）索引，中文字段形态与 fetch_quote 一致。"""
        monkeypatch.setattr(ht, "_get", lambda p, params: {"item": [
            {"thscode": "600519.SH", "last_price": 1311.21,
             "price_change_ratio_pct": 3.02, "price_change": 38.38}]})
        result = ht.fetch_quotes_batch(["600519"])
        assert set(result.keys()) == {"600519"}
        q = result["600519"]
        assert q["最新价"] == "1311.21"
        assert q["涨跌幅"] == "3.02"
        assert q["data_source"] == "同花顺官方API"

    def test_suffixed_code_passthrough(self, monkeypatch):
        """带后缀的代码（指数）原样透传，不二次加后缀。"""
        captured = {}

        def fake_get(p, params):
            captured["thscodes"] = params["thscodes"]
            return {"item": [{"thscode": "000001.SH", "last_price": 3877.3}]}

        monkeypatch.setattr(ht, "_get", fake_get)
        result = ht.fetch_quotes_batch(["000001.SH"])
        assert captured["thscodes"] == "000001.SH"
        assert result["000001.SH"]["最新价"] == "3877.3"

    def test_empty_input_returns_empty(self):
        assert ht.fetch_quotes_batch([]) == {}

    def test_unrequested_code_ignored(self, monkeypatch):
        """服务端多返回的代码不在结果里（只信任请求过的）。"""
        monkeypatch.setattr(ht, "_get", lambda p, params: {
            "item": [{"thscode": "999999.XX", "last_price": 1}]})
        assert ht.fetch_quotes_batch(["600519"]) == {}

    def test_cap_thirty_codes(self, monkeypatch):
        """单次请求最多 30 只（配额保护）。"""
        captured = {}

        def fake_get(p, params):
            captured["thscodes"] = params["thscodes"]
            return {"item": []}

        monkeypatch.setattr(ht, "_get", fake_get)
        ht.fetch_quotes_batch([f"60{i:04d}" for i in range(40)])
        assert len(captured["thscodes"].split(",")) == 30


# ============================================================
# 路由层：market_snapshot
# ============================================================

class TestMarketSnapshot:
    async def test_batch_hit_no_errors(self, monkeypatch):
        """批量全命中：stocks 来自同花顺层，errors 为空。"""
        from app.api.routes import market_snapshot

        def fake_batch(codes):
            if codes[0].endswith(".SH") and codes[0] == "000001.SH":
                return {c: _hithink_quote(c) for c in codes}  # 指数调用
            return {c: _hithink_quote(c) for c in codes}

        monkeypatch.setattr(ht, "fetch_quotes_batch", fake_batch)
        resp = await market_snapshot(codes="600519,600196")
        assert len(resp["indexes"]) == 3
        assert len(resp["stocks"]) == 2
        assert resp["errors"] == []
        assert all(s["data_source"] == "同花顺官方API" for s in resp["stocks"])

    async def test_per_stock_fallback_when_hithink_down(self, monkeypatch):
        """同花顺整层失败 → 逐股落完整降级链（此处 mock 到模拟快照）。"""
        from app.api import routes as routes_mod
        from app.api.routes import market_snapshot

        def boom(codes):
            raise ht.HithinkError("网络不可用")

        monkeypatch.setattr(ht, "fetch_quotes_batch", boom)
        def fake_func(stock_code):
            return json.dumps(
                {"error": False,
                 "quote": {"stock_code": stock_code, "最新价": "22.93",
                           "涨跌幅": "-2.67", "data_source": "内置模拟快照"}})

        # StructuredTool 是 pydantic 模型，patch 其底层 func 字段（invoke 会转发到它）
        monkeypatch.setattr(routes_mod.query_stock_quote, "func", fake_func)

        resp = await market_snapshot(codes="600196")
        assert len(resp["stocks"]) == 1
        assert resp["stocks"][0]["data_source"] == "内置模拟快照"
        assert resp["errors"] == []

    async def test_single_failure_isolated(self, monkeypatch):
        """一只股票彻底失败：只进 errors，其余正常返回，整体不 500。"""
        from app.api import routes as routes_mod
        from app.api.routes import market_snapshot
        monkeypatch.setattr(ht, "fetch_quotes_batch",
                            lambda codes: {} if codes[0] != "000001.SH"
                            else {c: _hithink_quote(c) for c in codes})

        def flaky_func(stock_code):
            if stock_code == "300999":
                raise RuntimeError("超时")
            return json.dumps({"error": False,
                               "quote": _hithink_quote(stock_code)})

        monkeypatch.setattr(routes_mod.query_stock_quote, "func", flaky_func)

        resp = await market_snapshot(codes="600519,300999")
        assert [s["stock_code"] for s in resp["stocks"]] == ["600519"]
        assert len(resp["errors"]) == 1
        assert resp["errors"][0]["code"] == "300999"

    async def test_empty_codes_only_indexes(self, monkeypatch):
        """无自选码：仅返回指数区，不报错。"""
        from app.api.routes import market_snapshot

        monkeypatch.setattr(
            ht, "fetch_quotes_batch",
            lambda codes: {c: _hithink_quote(c) for c in codes})
        resp = await market_snapshot(codes="")
        assert len(resp["indexes"]) == 3
        assert resp["stocks"] == []

    async def test_index_failure_tolerated(self, monkeypatch):
        """指数失败但个股正常：指数区为空，个股照常（fail-open）。"""
        from app.api.routes import market_snapshot

        calls = []
        def fake_batch(codes):
            calls.append(list(codes))
            if codes[0] == "000001.SH":
                raise ht.HithinkError("指数接口挂了")
            return {c: _hithink_quote(c) for c in codes}

        monkeypatch.setattr(ht, "fetch_quotes_batch", fake_batch)
        resp = await market_snapshot(codes="600519")
        assert resp["indexes"] == []
        assert len(resp["stocks"]) == 1
        assert len(calls) == 2  # 指数一次失败后仍继续拉个股

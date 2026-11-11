"""routes.py API 单测：数据端点 / K线降级链 / 行情快照 / 素材管理 / TTS 校验。

外部依赖（akshare、requests、query_* 工具、dashscope TTS）全部 mock，
覆盖多源降级与 fail-open 分支。
"""
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app.api.routes as routes_mod


def _akshare_stub(monkeypatch, **funcs):
    """安装临时 akshare stub（test_akshare_tools 模块级污染了 sys.modules["akshare"]，
    这里用 setitem 每用例自装自拆，互不影响）。"""
    stub = types.ModuleType("akshare")
    for name, fn in funcs.items():
        setattr(stub, name, fn)
    monkeypatch.setitem(sys.modules, "akshare", stub)
    return stub


@pytest.fixture(scope="module")
def client():
    import main as main_module
    return TestClient(main_module.app)


def _quote_result(pct="2.5", source="同花顺官方API", error=None):
    if error:
        return json.dumps({"error": True, "message": error})
    return json.dumps({"error": False, "quote": {
        "stock_code": "600519", "name": "贵州茅台", "price": 1500.0,
        "涨跌幅": pct, "data_source": source,
    }})


# ============================================================
# 股票查询端点
# ============================================================

class TestStockEndpoints:
    def test_stock_info(self, client):
        with patch("app.api.routes.query_stock_info") as mock_q:
            mock_q.invoke.return_value = json.dumps({"code": "600519", "name": "贵州茅台"})
            resp = client.get("/api/stock/600519/info")
        assert resp.status_code == 200
        assert resp.json()["name"] == "贵州茅台"

    def test_stock_financial(self, client):
        with patch("app.api.routes.query_financial_indicators") as mock_q:
            mock_q.invoke.return_value = json.dumps({"roe": "25%"})
            resp = client.get("/api/stock/600519/financial")
        assert resp.status_code == 200
        assert resp.json()["roe"] == "25%"

    def test_stock_quote(self, client):
        with patch("app.api.routes.query_stock_quote") as mock_q:
            mock_q.invoke.return_value = _quote_result()
            resp = client.get("/api/stock/600519/quote")
        assert resp.status_code == 200
        assert resp.json()["quote"]["name"] == "贵州茅台"

    def test_stock_news(self, client):
        with patch("app.api.routes.query_stock_news") as mock_q:
            mock_q.invoke.return_value = json.dumps({"news": []})
            resp = client.get("/api/stock/600519/news")
        assert resp.status_code == 200
        assert resp.json()["news"] == []


# ============================================================
# 个股 K 线多源降级链
# ============================================================

def _hist_df():
    return pd.DataFrame({
        "日期": pd.to_datetime(["2026-01-06", "2026-01-07", "2026-01-08"]),
        "收盘": [1500.123, 1510.456, 1520.789],
    })


class TestStockKline:
    def test_kline_primary_akshare(self, client, monkeypatch):
        _akshare_stub(monkeypatch, stock_zh_a_hist=lambda **kw: _hist_df())
        resp = client.get("/api/stock/600519/kline", params={"days": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "AKShare 东方财富"
        # days=2 会被夹到下限 5，数据只有 3 条 → 全量返回，round 2 位
        assert data["kline"] == [1500.12, 1510.46, 1520.79]

    def test_kline_days_clamped(self, client, monkeypatch):
        seen = {}

        def fake_hist(**kw):
            seen["called"] = True
            return _hist_df()

        _akshare_stub(monkeypatch, stock_zh_a_hist=fake_hist)
        resp = client.get("/api/stock/600519/kline", params={"days": 99999})
        assert resp.status_code == 200
        # days 上限 120、下限 5，不影响返回长度上限（数据只有 3 条）
        assert len(resp.json()["kline"]) == 3
        assert seen["called"]

    def test_kline_fallback_sina(self, client, monkeypatch):
        _akshare_stub(monkeypatch,
                      stock_zh_a_hist=MagicMock(side_effect=RuntimeError("em blocked")))

        fake_resp = MagicMock()
        fake_resp.json.return_value = [
            {"day": "2026-01-07", "close": "1510.5"},
            {"day": "2026-01-08", "close": "1520.6"},
        ]
        monkeypatch.setattr("requests.get", lambda *a, **kw: fake_resp)
        resp = client.get("/api/stock/600519/kline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "新浪财经"
        assert data["kline"] == [1510.5, 1520.6]
        assert data["dates"] == ["01-07", "01-08"]

    def test_kline_all_sources_fail_502(self, client, monkeypatch):
        _akshare_stub(monkeypatch,
                      stock_zh_a_hist=MagicMock(side_effect=RuntimeError("em blocked")))
        monkeypatch.setattr("requests.get", MagicMock(side_effect=RuntimeError("network down")))
        resp = client.get("/api/stock/600519/kline")
        assert resp.status_code == 502


# ============================================================
# 指数 K 线
# ============================================================

class TestIndexKline:
    def test_index_kline_sina_mapped(self, client, monkeypatch):
        fake_resp = MagicMock()
        fake_resp.json.return_value = [
            {"day": "2026-01-07", "close": "3200.5"},
            {"day": "2026-01-08", "close": "3210.6"},
        ]
        monkeypatch.setattr("requests.get", lambda *a, **kw: fake_resp)
        resp = client.get("/api/index/000001/kline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "上证指数"
        assert data["data_source"] == "新浪财经"
        assert data["kline"] == [3200.5, 3210.6]

    def test_index_kline_fallback_tencent(self, client, monkeypatch):
        # 新浪返回非 list → 走腾讯
        fake_sina = MagicMock()
        fake_sina.json.return_value = {"error": "no data"}
        fake_tx = MagicMock()
        fake_tx.json.return_value = {"data": {"sh000001": {
            "qfqday": [["2026-01-08", "3190", "3210.6", "3220", "3180", "1e8"]],
        }}}

        def fake_get(url, **kw):
            return fake_tx if "ifzq.gtimg" in url else fake_sina

        monkeypatch.setattr("requests.get", fake_get)
        resp = client.get("/api/index/000001/kline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "腾讯证券"
        assert data["kline"] == [3210.6]

    def test_index_kline_unsupported_code_400(self, client):
        resp = client.get("/api/index/999999/kline")
        assert resp.status_code == 400

    def test_index_kline_all_fail_502(self, client, monkeypatch):
        monkeypatch.setattr("requests.get", MagicMock(side_effect=RuntimeError("down")))
        resp = client.get("/api/index/399006/kline")
        assert resp.status_code == 502


# ============================================================
# 行情快照（fail-open）与热门标的
# ============================================================

class TestMarketEndpoints:
    def test_snapshot_fail_open_with_error(self, client, monkeypatch):
        # hithink 关闭（conftest 默认）→ 指数/批量层跳过，逐股走降级链
        with patch("app.api.routes.query_stock_quote") as mock_q:
            mock_q.invoke.side_effect = [_quote_result(), _quote_result(error="全部数据层不可达")]
            resp = client.get("/api/market/snapshot", params={"codes": "600519,000001"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["stocks"]) == 1
        assert data["stocks"][0]["stock_code"] == "600519"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["code"] == "000001"
        assert "updated_at" in data

    def test_snapshot_quote_raises_still_fail_open(self, client, monkeypatch):
        with patch("app.api.routes.query_stock_quote") as mock_q:
            mock_q.invoke.side_effect = RuntimeError("boom")
            resp = client.get("/api/market/snapshot", params={"codes": "600519"})
        assert resp.status_code == 200
        assert resp.json()["errors"][0]["code"] == "600519"

    def test_hot_fallback_ranked_by_change_pct(self, client, monkeypatch):
        _akshare_stub(monkeypatch,
                      stock_hot_rank_em=MagicMock(side_effect=RuntimeError("em blocked")))
        with patch("app.api.routes.query_stock_quote") as mock_q:
            mock_q.invoke.side_effect = [
                _quote_result(pct="1.0"), _quote_result(pct="-0.5"),
                _quote_result(pct="5.8"), _quote_result(pct="0.2"),
                _quote_result(pct="3.3"), _quote_result(pct="2.1"),
                _quote_result(pct="0.0"), _quote_result(pct="-1.1"),
                _quote_result(pct="4.4"), _quote_result(pct="2.9"),
            ]
            resp = client.get("/api/market/hot", params={"take": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "实时涨幅排序"
        pcts = [i["change_pct"] for i in data["items"]]
        assert pcts == sorted(pcts, reverse=True)
        assert len(data["items"]) == 3

    def test_hot_bad_pct_defaults_zero(self, client, monkeypatch):
        _akshare_stub(monkeypatch, stock_hot_rank_em=MagicMock(side_effect=RuntimeError("x")))
        with patch("app.api.routes.query_stock_quote") as mock_q:
            mock_q.invoke.return_value = json.dumps({"error": False, "quote": {"涨跌幅": "N/A"}})
            resp = client.get("/api/market/hot")
        assert resp.status_code == 200
        assert all(i["change_pct"] == 0.0 for i in resp.json()["items"])


# ============================================================
# 财经快讯 / AI HOT
# ============================================================

class TestNewsEndpoints:
    def test_finnews_success(self, client, monkeypatch):
        df = pd.DataFrame({"标题": ["快讯一", "", "快讯三"], "链接": ["http://a", "", "http://c"]})
        _akshare_stub(monkeypatch, stock_info_global_em=lambda: df)
        routes_mod._finnews_cache.update(ts=0.0, items=[])  # 清缓存
        resp = client.get("/api/finnews", params={"take": 2})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert items[0]["title"] == "快讯一"

    def test_finnews_cache_hit(self, client):
        routes_mod._finnews_cache.update(ts=__import__("time").time(), items=[
            {"title": "缓存快讯", "url": None}])
        resp = client.get("/api/finnews")
        assert resp.status_code == 200
        assert resp.json()["items"][0]["title"] == "缓存快讯"

    def test_finnews_failure_502(self, client, monkeypatch):
        _akshare_stub(monkeypatch,
                      stock_info_global_em=MagicMock(side_effect=RuntimeError("em blocked")))
        routes_mod._finnews_cache.update(ts=0.0, items=[])
        resp = client.get("/api/finnews")
        assert resp.status_code == 502


# ============================================================
# 报告保存 / 素材库管理
# ============================================================

class TestMaterials:
    def test_save_and_list_and_get_and_delete(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(routes_mod, "CREATION_DIR", str(tmp_path))
        resp = client.post("/api/save-report", json={
            "query": "贵州茅台调研", "report": "# 报告正文", "watermark": True})
        assert resp.status_code == 200
        fname = resp.json()["filename"]
        assert fname.endswith(".md")

        # 列表
        resp = client.get("/api/materials")
        names = [i["filename"] for i in resp.json()["items"]]
        assert fname in names

        # 读取
        resp = client.get(f"/api/materials/{fname}")
        assert resp.status_code == 200
        assert "报告正文" in resp.json()["content"]
        assert "由 IRIS 智能调研系统生成" in resp.json()["content"]  # 水印

        # 删除
        resp = client.delete(f"/api/materials/{fname}")
        assert resp.status_code == 200
        resp = client.get(f"/api/materials/{fname}")
        assert resp.status_code == 404

    def test_materials_empty_dir(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(routes_mod, "CREATION_DIR", str(tmp_path / "nonexistent"))
        resp = client.get("/api/materials")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_material_path_traversal_blocked(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(routes_mod, "CREATION_DIR", str(tmp_path))
        resp = client.get("/api/materials/..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code == 404


# ============================================================
# TTS / 用量 / 状态
# ============================================================

class TestSystemEndpoints:
    def test_tts_rejects_empty_text(self, client):
        resp = client.post("/api/tts", json={"text": "   "})
        assert resp.status_code == 422

    def test_tts_rejects_overlong_text(self, client):
        resp = client.post("/api/tts", json={"text": "长" * 5001})
        assert resp.status_code == 422

    def test_tts_dashscope_mocked_unavailable_500(self, client):
        # conftest 把 dashscope mock 成非包 MagicMock → from-import 走 ImportError 分支
        resp = client.post("/api/tts", json={"text": "你好，世界"})
        assert resp.status_code == 500
        assert "dashscope" in resp.json()["detail"]

    def test_usage_stats(self, client):
        resp = client.get("/api/usage")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert "usage" in resp.json()

    def test_status_endpoint(self, client, monkeypatch):
        monkeypatch.setattr(routes_mod, "_status_cache", {"ts": 0.0, "data": None})
        with patch("app.api.routes.query_stock_quote") as mock_q:
            mock_q.invoke.return_value = _quote_result(source="同花顺官方API")
            resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_online"] is True
        assert "llm_degraded" in data


# ============================================================
# 研报上传（参数校验）
# ============================================================

class TestReportUpload:
    def test_upload_rejects_non_pdf(self, client):
        resp = client.post("/api/reports/upload",
                           files={"file": ("a.txt", b"hello", "text/plain")})
        assert resp.status_code == 400

    def test_memory_unknown_thread(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(routes_mod, "DB_PATH", str(tmp_path / "no-such.db"))
        resp = client.get("/api/memory/unknown-thread-xyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "" and data["turns"] == 0

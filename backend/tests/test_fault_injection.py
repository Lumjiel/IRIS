"""故障注入测试 — 验证工具层超时/重试/降级链在各级故障下的行为。

覆盖（GOAL 验收 #6：工具有超时/重试/降级 + 故障注入测试）：
- _safe_request：重试次数 / 退避 / 不可重试异常直返 None / None 结果重试
- query_stock_quote：L1 东财挂 → L2 新浪接住；全链挂 → mock 兜底且 degraded 标记
- query_stock_quote：L0 同花顺开启但抛错 → 正确落回 AKShare 链
- query_stock_news：两级网络源全挂 → mock 新闻兜底，永不抛异常
- _tencent_quote_supplement_batch：网络异常 / 垃圾响应 → 静默返回 {}（fail-open）
"""
import json
import time as _time
import types
from unittest.mock import MagicMock

import pandas as pd
import pytest

import sys

# akshare stub（与 test_akshare_tools 同模式；已存在则复用）
if "akshare" not in sys.modules or not isinstance(sys.modules["akshare"], types.ModuleType):
    sys.modules["akshare"] = types.ModuleType("akshare")
mock_ak = sys.modules["akshare"]

import app.tools.akshare_tools as at
from app.tools.akshare_tools import _safe_request, query_stock_quote, query_stock_news


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """故障注入测试不真等退避。"""
    monkeypatch.setattr(_time, "sleep", lambda s: None)


@pytest.fixture(autouse=True)
def _reset_ak():
    for attr in list(vars(mock_ak).keys()):
        if not attr.startswith("_"):
            delattr(mock_ak, attr)
    yield


# ============================================================
# _safe_request：重试封装
# ============================================================

class TestSafeRequest:
    def test_success_first_try_no_retry(self):
        calls = []

        def fn():
            calls.append(1)
            return "ok"

        assert _safe_request(fn, "t", max_retries=2) == "ok"
        assert len(calls) == 1

    def test_network_error_retries_then_succeeds(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 2:
                raise ConnectionError("reset")
            return "ok"

        assert _safe_request(fn, "t", max_retries=2) == "ok"
        assert len(calls) == 2

    def test_all_retries_exhausted_returns_none(self):
        calls = []

        def fn():
            calls.append(1)
            raise TimeoutError("t/o")

        assert _safe_request(fn, "t", max_retries=2) is None
        assert len(calls) == 3  # 1 + max_retries

    def test_non_retryable_error_returns_none_immediately(self):
        calls = []

        def fn():
            calls.append(1)
            raise ValueError("bad params")

        assert _safe_request(fn, "t", max_retries=2) is None
        assert len(calls) == 1  # 不可重试异常不重试

    def test_none_result_is_retried(self):
        calls = []

        def fn():
            calls.append(1)
            return None

        assert _safe_request(fn, "t", max_retries=2) is None
        assert len(calls) == 3

    def test_backoff_sleeps_between_attempts(self):
        sleeps = []
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(_time, "sleep", lambda s: sleeps.append(s))
        try:
            calls = []

            def fn():
                calls.append(1)
                raise ConnectionError("x")

            _safe_request(fn, "t", max_retries=2, base_sleep=1.5)
            # 两次重试间隔：1.5, 3.0（线性退避）
            assert sleeps == [1.5, 3.0]
        finally:
            monkeypatch.undo()


# ============================================================
# query_stock_quote：多源降级链故障注入
# ============================================================

def _sina_df():
    return pd.DataFrame([{
        "代码": "600519", "最新价": 1500.5, "涨跌幅": 2.3, "涨跌额": 33.7,
        "成交量": 12345, "成交额": 1.8e7, "振幅": 2.0, "最高": 1510.0,
        "最低": 1490.0, "今开": 1495.0, "昨收": 1466.8, "换手率": 0.1,
        "市盈率": 25.0, "市净率": 8.0, "总市值": 1.8e12, "流通市值": 1.8e12,
    }])


class TestQuoteChainFaultInjection:
    def test_l1_down_l2_sina_picks_up(self, monkeypatch):
        """东财层返回 None（重试耗尽），新浪层接住 → 新浪数据、不降级。"""
        monkeypatch.setattr(at, "_get_spot_em_cached", lambda: None)
        monkeypatch.setattr(at, "_get_spot_sina_cached", lambda: _sina_df())
        data = json.loads(query_stock_quote.invoke("600519"))
        assert data["error"] is False
        assert data["degraded"] is False
        assert "新浪" in data["quote"]["data_source"]
        assert data["quote"]["最新价"] == "1500.5"
        assert data["quote"]["stock_code"] == "600519"

    def test_l2_empty_rows_falls_to_mock(self, monkeypatch):
        """新浪返回但无该股票 → mock 兜底 + degraded 标记。"""
        monkeypatch.setattr(at, "_get_spot_em_cached", lambda: None)
        empty = _sina_df()
        monkeypatch.setattr(at, "_get_spot_sina_cached", lambda: empty[empty["代码"] == "nope"])
        data = json.loads(query_stock_quote.invoke("600519"))
        assert data["error"] is False
        assert data["degraded"] is True
        assert "模拟" in data["quote"]["data_source"]

    def test_full_chain_down_never_raises(self, monkeypatch):
        """全链故障：两层缓存函数抛网络异常 → mock 兜底，工具永不抛异常。"""
        def boom():
            raise ConnectionError("network down")

        monkeypatch.setattr(at, "_get_spot_em_cached", boom)
        monkeypatch.setattr(at, "_get_spot_sina_cached", boom)
        data = json.loads(query_stock_quote.invoke("600519"))  # 不应抛
        assert data["error"] is False
        assert data["degraded"] is True
        assert "模拟" in data["quote"]["data_source"]
        assert "stock_code" in str(data["quote"])

    def test_hithink_enabled_but_raises_falls_through(self, monkeypatch):
        """L0 同花顺开启但抛错 → 落回 AKShare 链（此处全挂 → mock）。"""
        monkeypatch.setenv("ENABLE_HITHINK", "true")
        fake_ht = types.ModuleType("app.tools.hithink_tools")
        fake_ht.fetch_quote = MagicMock(side_effect=RuntimeError("hithink 5xx"))
        fake_ht.is_enabled = lambda: True
        monkeypatch.setitem(sys.modules, "app.tools.hithink_tools", fake_ht)

        def boom():
            raise ConnectionError("down")

        monkeypatch.setattr(at, "_get_spot_em_cached", boom)
        monkeypatch.setattr(at, "_get_spot_sina_cached", boom)
        data = json.loads(query_stock_quote.invoke("600519"))
        assert data["error"] is False
        assert data["degraded"] is True
        assert "模拟" in data["quote"]["data_source"]


# ============================================================
# query_stock_news：降级链故障注入
# ============================================================

class TestNewsChainFaultInjection:
    def test_all_sources_down_falls_to_mock_never_raises(self, monkeypatch):
        def boom(*a, **kw):
            raise ConnectionError("down")

        mock_ak.stock_news_em = boom
        mock_ak.stock_news_sina = boom
        data = json.loads(query_stock_news.invoke("600519"))
        assert data["error"] is False
        assert data["degraded"] is True
        assert len(data["news"]) > 0
        assert "模拟" in data["data_source"]

    def test_news_l1_returns_empty_l2_succeeds(self, monkeypatch):
        """东财返回空 df → 新浪接住。"""
        mock_ak.stock_news_em = lambda symbol: pd.DataFrame()
        mock_ak.stock_news_sina = lambda symbol: pd.DataFrame([
            {"标题": "新浪快讯", "内容": "测试内容" * 100, "时间": "2026-11-10 09:00"},
        ])
        data = json.loads(query_stock_news.invoke("600519"))
        assert data["error"] is False
        assert data["degraded"] is False
        assert data["data_source"] == "AKShare (新浪财经备用)"
        assert data["news"][0]["title"] == "新浪快讯"
        assert data["news"][0]["source"] == "新浪财经"
        assert len(data["news"][0]["content"]) <= 200  # 摘要截断


# ============================================================
# 腾讯行情补充：fail-open
# ============================================================

class TestTencentSupplementFaultInjection:
    def test_network_error_returns_empty_dict(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "get", MagicMock(side_effect=RuntimeError("timeout")))
        assert at._tencent_quote_supplement_batch(["600519"]) == {}

    def test_garbage_response_returns_empty(self, monkeypatch):
        import httpx
        resp = MagicMock()
        resp.content = b"\xff\xfe garbage no pattern"
        monkeypatch.setattr(httpx, "get", MagicMock(return_value=resp))
        assert at._tencent_quote_supplement_batch(["600519"]) == {}

    def test_invalid_codes_skipped_no_request(self, monkeypatch):
        """非法代码全部被过滤 → 不发请求直接返回 {}。"""
        import httpx
        get = MagicMock(side_effect=AssertionError("不应发起请求"))
        monkeypatch.setattr(httpx, "get", get)
        assert at._tencent_quote_supplement_batch(["abc", "12345", ""]) == {}

    def test_valid_response_parsed(self, monkeypatch):
        import httpx
        line = 'v_sh600519="1~贵州茅台~600519~1500.00~' + "~" * 35 + "1.25~18.02"
        # 下标：38=换手率 39=PE 45=总市值 46=PB
        fields = ["0"] * 47
        fields[3] = "1500.00"
        fields[38] = "1.25"
        fields[39] = "18.02"
        fields[45] = "18800"   # 亿
        fields[46] = "8.88"
        payload = ('v_sh600519="' + "~".join(fields)).encode()
        resp = MagicMock()
        resp.content = payload
        monkeypatch.setattr(httpx, "get", MagicMock(return_value=resp))
        out = at._tencent_quote_supplement_batch(["600519"])
        assert out["600519"]["换手率"] == "1.25%"
        assert out["600519"]["市盈率"] == "18.02"
        assert out["600519"]["市净率"] == "8.88"
        assert float(out["600519"]["总市值"]) == 18800 * 1e8

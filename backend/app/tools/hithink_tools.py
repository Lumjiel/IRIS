"""
同花顺官方金融数据服务（Financial-API）客户端 —— 数据降级链 L0。

契约源: https://github.com/HiThink-Tech/Financial-API/tree/main/docs/api
- Base URL: https://fuyao.aicubes.cn
- 鉴权: header `X-api-key`
- thscode 必须带交易所后缀（600519.SH / 000001.SZ），纯 6 位代码会被拒绝

设计要点（docs/HITHINK_INTEGRATION_PLAN.md）：
- fail-open：任何异常抛 HithinkError，由 akshare_tools 各工具的「第零层」捕获后
  落到下一层数据源，绝不阻塞主流程
- Key 缺失或 ENABLE_HITHINK=false 时 is_enabled()=False，整层跳过（等价原三链）
- 开关/Key 动态读环境变量：测试可按用例启停，无需重启进程
- 同步 httpx 调用——事件循环中的调用方需用 asyncio.to_thread 包装（与 akshare 一致）
"""
import os
from typing import Dict

import httpx

from app.utils.logger import get_logger

log = get_logger("tools.hithink")

BASE_URL = os.getenv("HITHINK_BASE_URL", "https://fuyao.aicubes.cn")

DATA_SOURCE_TAG = "同花顺官方API"


def _api_key() -> str:
    return os.getenv("HITHINK_FINANCE_API_KEY", "")


def _timeout_s() -> float:
    try:
        return float(os.getenv("HITHINK_TIMEOUT_S", "5"))
    except (TypeError, ValueError):
        return 5.0


def is_enabled() -> bool:
    """Key 已配置且开关打开才启用本层；否则整层跳过。动态读环境变量，测试可切换。"""
    enabled = os.getenv("ENABLE_HITHINK", "true").lower() == "true"
    return enabled and bool(_api_key())


class HithinkError(Exception):
    """同花顺 API 调用失败（网络/鉴权/响应异常）。调用方应降级到下一层数据源。"""


def _to_thscode(stock_code: str) -> str:
    """6 位纯代码 → 带交易所后缀的 thscode。已带后缀则原样返回。

    规则：6 开头 → .SH（沪）；0/3 开头 → .SZ（深）；4/8 开头 → .BJ（北交所）。
    """
    code = stock_code.strip()
    if "." in code:
        return code
    if code.startswith("6"):
        return f"{code}.SH"
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    if code.startswith(("4", "8")):
        return f"{code}.BJ"
    raise HithinkError(f"无法识别交易所后缀: {stock_code}")


def _get(path: str, params: Dict) -> Dict:
    """GET 请求并校验业务码（code=0 成功）。任何失败抛 HithinkError。"""
    key = _api_key()
    if not key:
        raise HithinkError("HITHINK_FINANCE_API_KEY 未配置")
    try:
        resp = httpx.get(f"{BASE_URL}{path}", params=params,
                         headers={"X-api-key": key}, timeout=_timeout_s())
    except Exception as e:
        raise HithinkError(f"请求失败: {e}") from e

    if resp.status_code == 401:
        raise HithinkError("鉴权失败（401），请检查 API Key")
    if resp.status_code != 200:
        raise HithinkError(f"HTTP {resp.status_code}: {resp.text[:120]}")

    try:
        body = resp.json()
    except ValueError as e:
        raise HithinkError(f"响应非 JSON: {e}") from e

    if body.get("code") != 0:
        raise HithinkError(f"业务错误 code={body.get('code')} msg={body.get('message')}")
    data = body.get("data")
    if not data:
        raise HithinkError("响应 data 为空")
    return data


def fetch_quote(stock_code: str) -> Dict[str, str]:
    """实时行情快照（对齐 akshare quote 的中文字段形态）。"""
    data = _get("/api/a-share/prices/snapshot", {"thscodes": _to_thscode(stock_code)})
    items = data.get("item") or []
    if not items:
        raise HithinkError(f"无 {stock_code} 行情数据")

    it = items[0]
    return {
        "stock_code": stock_code,
        "最新价": str(it.get("last_price", "N/A")),
        "涨跌幅": str(it.get("price_change_ratio_pct", "N/A")),
        "涨跌额": str(it.get("price_change", "N/A")),
        "成交量": str(it.get("volume", "N/A")),
        "成交额": str(it.get("turnover", "N/A")),
        "最高": str(it.get("high_price", "N/A")),
        "最低": str(it.get("low_price", "N/A")),
        "今开": str(it.get("open_price", "N/A")),
        "昨收": str(it.get("prev_price", "N/A")),
        "延时": "实时",
        "data_source": DATA_SOURCE_TAG,
    }


def fetch_info(stock_code: str) -> Dict[str, str]:
    """公司概况+估值快照（名称、PE/PB/PS/PC）。"""
    data = _get("/api/a-share/valuations/snapshot", {"thscodes": _to_thscode(stock_code)})
    items = data.get("item") or []
    if not items:
        raise HithinkError(f"无 {stock_code} 估值数据")

    it = items[0]
    info = {
        "证券简称": str(it.get("name", "N/A")),
        "stock_code": stock_code,
        "市盈率PE(TTM)": str(it.get("pe_ttm", "N/A")),
        "市盈率PE(MRQ)": str(it.get("pe_mrq", "N/A")),
        "市净率PB(MRQ)": str(it.get("pb_mrq", "N/A")),
        "市销率PS(TTM)": str(it.get("ps_ttm", "N/A")),
        "市现率PCF(TTM)": str(it.get("pcf_ttm", "N/A")),
        "数据时间戳": str(data.get("timestamp", "")),
    }
    return {k: v for k, v in info.items() if v not in ("N/A", "")}


def fetch_financial_indicators(stock_code: str, limit: int = 2) -> Dict[str, str]:
    """核心财务指标（年报利润表最近 N 期；同比由相邻两期计算）。"""
    data = _get("/api/a-share/financials/income-statements",
                {"thscode": _to_thscode(stock_code), "period": "annual",
                 "limit": max(limit, 2)})
    statements = data.get("indicators") or data.get("item") or []
    if len(statements) < 1:
        raise HithinkError(f"无 {stock_code} 利润表数据")

    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    latest = statements[0]
    fields = {
        "report_period": f"{latest.get('fiscal_year', '')}{latest.get('fiscal_period', '')}",
        "total_revenue": latest.get("operating_income"),
        "net_profit": latest.get("parent_holder_net_profit") or latest.get("net_profit"),
        "eps": latest.get("basic_eps"),
    }

    # 同比：需要上一年同期（相邻记录）；缺失留 N/A，不编造
    revenue_yoy = profit_yoy = "N/A"
    if len(statements) >= 2:
        prev = statements[1]
        cur_rev, pre_rev = _num(latest.get("operating_income")), _num(prev.get("operating_income"))
        cur_np, pre_np = (_num(latest.get("parent_holder_net_profit") or latest.get("net_profit")),
                          _num(prev.get("parent_holder_net_profit") or prev.get("net_profit")))
        if cur_rev and pre_rev:
            revenue_yoy = f"{(cur_rev - pre_rev) / abs(pre_rev) * 100:.2f}%"
        if cur_np and pre_np:
            profit_yoy = f"{(cur_np - pre_np) / abs(pre_np) * 100:.2f}%"

    rev, cost = _num(latest.get("operating_income")), _num(latest.get("operating_costs"))
    gross_margin = f"{(rev - cost) / rev * 100:.2f}%" if rev and cost is not None else "N/A"
    np_ = _num(fields["net_profit"])
    net_margin = f"{np_ / rev * 100:.2f}%" if np_ is not None and rev else "N/A"

    return {
        "stock_code": stock_code,
        "report_period": fields["report_period"] or "未知",
        "total_revenue": str(fields["total_revenue"] if fields["total_revenue"] is not None else "N/A"),
        "revenue_yoy_growth": revenue_yoy,
        "net_profit": str(fields["net_profit"] if fields["net_profit"] is not None else "N/A"),
        "net_profit_yoy_growth": profit_yoy,
        "gross_margin": gross_margin,
        "net_margin": net_margin,
        "roe": "N/A",  # 利润表不含 ROE，诚实标注而非估算
        "eps": str(fields["eps"] if fields["eps"] is not None else "N/A"),
        "data_source": DATA_SOURCE_TAG,
    }


def fetch_quotes_batch(stock_codes) -> Dict[str, Dict[str, str]]:
    """批量实时行情快照（一次请求，行情页轮询用，省 API 配额）。

    返回 {6位代码: quote_dict}（字段形态与 fetch_quote 一致）。
    未返回的代码不出现在结果中——由调用方逐股降级，本函数只做一层。
    指数代码需自带交易所后缀（如 000001.SH），纯 6 位按个股规则补后缀。
    """
    if not stock_codes:
        return {}

    reverse = {}  # thscode -> 原始入参代码
    for c in stock_codes[:30]:  # 上限保护：单次最多 30 只
        reverse[_to_thscode(c)] = str(c)

    data = _get("/api/a-share/prices/snapshot", {"thscodes": ",".join(reverse.keys())})
    items = data.get("item") or []

    result: Dict[str, Dict[str, str]] = {}
    for it in items:
        code = reverse.get(str(it.get("thscode", "")))
        if not code:
            continue  # 服务端返回了未请求的代码，忽略
        result[code] = {
            "stock_code": code,
            "最新价": str(it.get("last_price", "N/A")),
            "涨跌幅": str(it.get("price_change_ratio_pct", "N/A")),
            "涨跌额": str(it.get("price_change", "N/A")),
            "成交量": str(it.get("volume", "N/A")),
            "成交额": str(it.get("turnover", "N/A")),
            "最高": str(it.get("high_price", "N/A")),
            "最低": str(it.get("low_price", "N/A")),
            "今开": str(it.get("open_price", "N/A")),
            "昨收": str(it.get("prev_price", "N/A")),
            "延时": "实时",
            "data_source": DATA_SOURCE_TAG,
        }
    return result

"""
AKShare A 股数据工具层
- 三层降级：东方财富 → 雪球/新浪 → 内置模拟数据
- 模块级代理清理（消除 VPN/系统代理残留）
- 所有工具永不抛异常，返回结构化 JSON
- 支持 LangChain @tool 装饰器（Function Calling 就绪）

依赖: akshare >= 1.16.0
"""
import json
import threading
import logging
import os
import time
from typing import Any, Callable, Optional, Dict

from langchain_core.tools import tool

from app.config import DATA_DIR

logger = logging.getLogger(__name__)


# ============================================================
# 模块级代理清理 — 彻底消除 VPN/系统代理残留
# AKShare 使用 requests 发请求，代理环境变量会导致 Connection aborted
# ============================================================
_PROXY_VARS = [
    "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
    "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
]
for _pv in _PROXY_VARS:
    os.environ.pop(_pv, None)
os.environ["NO_PROXY"] = "*"


# ============================================================
# 通用安全重试封装
# ============================================================
def _safe_request(func: Callable, func_name: str = "unknown",
                 max_retries: int = 2, base_sleep: float = 1.5) -> Optional[Any]:
    """
    安全调用 AKShare 接口，失败自动休眠重试。

    - 网络异常（ConnectionError/TimeoutError/OSError）→ 休眠重试
    - 其他异常（参数错误等）→ 返回 None，不重试
    - 全部重试耗尽后返回 None
    """
    last_error = None
    for attempt in range(1 + max_retries):
        try:
            result = func()
            if result is None:
                if attempt < max_retries:
                    time.sleep(base_sleep * (attempt + 1))
                    continue
                return None
            return result
        except (ConnectionError, TimeoutError, OSError) as e:
            last_error = e
            logger.warning("[%s] 第%d次网络异常: %s", func_name, attempt + 1, str(e)[:100])
            if attempt < max_retries:
                time.sleep(base_sleep * (attempt + 1))
        except Exception as e:
            logger.error("[%s] 不可重试异常: %s", func_name, str(e)[:100])
            return None
    logger.error("[%s] 全部%d次尝试失败: %s", func_name, 1 + max_retries, str(last_error)[:100])
    return None



# ============================================================
# 全市场数据缓存 — 消灭 30s 全量拉取（"等半天"最大杀手）
# ============================================================
_SPOT_CACHE: Dict[str, Any] = {"ts": 0.0, "em": None, "sina": None}
_SPOT_TTL = 60  # 60s 缓存，A 股行情延时 15 分钟，60s 完全够用


_SPOT_LOCK = threading.Lock()


def _get_spot_em_cached():
    """带 60s TTL 缓存的全市场东方财富行情（线程安全）。
    首次/缓存过期时真实拉取（~5-15s），命中缓存时 <1ms。"""
    import time as _t
    import akshare as ak  # 局部导入：与工具函数保持一致的延迟导入模式（测试可注入 mock）
    with _SPOT_LOCK:
        now = _t.time()
        if _SPOT_CACHE["em"] is not None and now - _SPOT_CACHE["ts"] < _SPOT_TTL:
            return _SPOT_CACHE["em"]
        df = ak.stock_zh_a_spot_em()
        _SPOT_CACHE["em"] = df
        _SPOT_CACHE["ts"] = now
        return df


def _get_spot_sina_cached():
    """带 60s TTL 缓存的全市场新浪财经行情（备用源）。"""
    import time as _t
    import akshare as ak  # 局部导入：修复 NameError（原实现引用了未定义的模块级 ak）
    with _SPOT_LOCK:
        now = _t.time()
        if _SPOT_CACHE["sina"] is not None and now - _SPOT_CACHE["ts"] < _SPOT_TTL:
            return _SPOT_CACHE["sina"]
        df = ak.stock_zh_a_spot_sina()
        _SPOT_CACHE["sina"] = df
        return df

# 内置模拟快照 —— 网络彻底不可用时的最终兜底
# 数据维护在 mock_snapshot.py：真实感静态快照，字段与真实接口 schema 一致；
# 所有 data_source 标签含「模拟」二字，保证 degraded 标记检测不被绕过。
# ============================================================


def _get_mock_info(stock_code: str) -> Dict[str, str]:
    """根据股票代码返回对应的模拟基本信息"""
    from app.tools.mock_snapshot import get_mock_info
    return get_mock_info(stock_code)


def _get_mock_financial(stock_code: str) -> Dict[str, Any]:
    """根据股票代码返回对应的模拟财务指标"""
    from app.tools.mock_snapshot import get_mock_financial
    return get_mock_financial(stock_code)


def _get_mock_quote(stock_code: str) -> Dict[str, Any]:
    """根据股票代码返回对应的模拟行情"""
    from app.tools.mock_snapshot import get_mock_quote
    return get_mock_quote(stock_code)


# ============================================================
# 工具 1: A 股股票基本信息查询
# 三层降级: 东方财富 → 雪球 → 内置模拟数据
# ============================================================
@tool
def query_stock_info(stock_code: str) -> str:
    """
    查询 A 股股票基本信息，包括公司全称、所属行业、上市日期、总股本、流通股本等。

    参数:
        stock_code: A 股股票代码，如 "600196"（复星医药）、"000001"（平安银行）

    返回:
        JSON 格式字符串，包含公司名称、行业、上市日期、总股本等信息。
        网络不可用时返回内置模拟数据（标注数据来源）。
    """
    logger.info("[Tool] query_stock_info: stock_code=%s", stock_code)

    # ---- 第零层：同花顺官方 API（四层降级链 L0，docs/HITHINK_INTEGRATION_PLAN.md）----
    from app.tools.hithink_tools import is_enabled as _hithink_on
    if _hithink_on():
        try:
            from app.tools.hithink_tools import fetch_info as _ht_info

            info_dict = _ht_info(stock_code)
            data_source = "同花顺官方API"
            logger.info("[Tool] 同花顺官方API信息成功: %d个字段", len(info_dict))
            return json.dumps({
                "error": False, "degraded": False, "stock_code": stock_code,
                "info": info_dict, "data_source": data_source,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("[Tool] 同花顺官方API失败，落回 AKShare 链: %s", str(e)[:120])

    info_dict: Dict[str, str] = {}
    data_source: str = "未知"

    try:
        import akshare as ak

        # ---- 第一层：东方财富主接口 ----
        logger.info("[Tool] 尝试主数据源: AKShare 东方财富")
        info_df = _safe_request(
            func=lambda: ak.stock_individual_info_em(symbol=stock_code),
            func_name="stock_individual_info_em",
            max_retries=2,
        )

        # 双层空值校验: None + DataFrame.empty
        if info_df is not None and hasattr(info_df, 'empty') and not info_df.empty:
            for _, row in info_df.iterrows():
                key = str(row.get("item", ""))
                value = str(row.get("value", ""))
                if key and value and value.lower() not in ("none", "nan", ""):
                    info_dict[key] = value
            data_source = "AKShare (东方财富)"
            logger.info("[Tool] 东方财富接口成功: %d个字段", len(info_dict))
        else:
            logger.warning("[Tool] 东方财富接口返回空数据，尝试备用数据源")

        # ---- 第二层：雪球备用接口 ----
        if not info_dict:
            logger.info("[Tool] 尝试备用数据源: AKShare 雪球")
            try:
                xq_df = _safe_request(
                    func=lambda: ak.stock_individual_basic_info_xq(symbol=stock_code),
                    func_name="stock_individual_basic_info_xq",
                    max_retries=1,
                )
                if xq_df is not None and hasattr(xq_df, 'empty') and not xq_df.empty:
                    xq_dict = xq_df.to_dict(orient="records")
                    if xq_dict:
                        first_record = xq_dict[0]
                        for k, v in first_record.items():
                            if v is not None and str(v).lower() not in ("none", "nan", ""):
                                info_dict[str(k)] = str(v)
                        data_source = "AKShare (雪球备用)"
                        logger.info("[Tool] 雪球备用接口成功: %d个字段", len(info_dict))
            except Exception as e:
                logger.warning("[Tool] 雪球备用接口失败: %s", str(e)[:100])

        # ---- 第三层：内置模拟数据兜底 ----
        if not info_dict:
            logger.info("[Tool] 网络数据源全部失败，使用内置模拟数据")
            info_dict = _get_mock_info(stock_code)
            data_source = "内置模拟数据（网络不可用时的最终兜底）"

    except ImportError:
        logger.warning("[Tool] akshare 库未安装，使用内置模拟数据")
        info_dict = _get_mock_info(stock_code)
        data_source = "内置模拟数据（akshare未安装）"
    except Exception as e:
        logger.error("[Tool] query_stock_info 未预期异常: %s", str(e)[:100])
        info_dict = _get_mock_info(stock_code)
        data_source = f"内置模拟数据（异常降级: {str(e)[:50]}）"

    # 降级标记：mock 兜底的数据必须可被下游识别，不能伪装成真实数据
    result = {
        "error": False,
        "degraded": "模拟数据" in data_source,
        "stock_code": stock_code,
        "info": info_dict,
        "data_source": data_source,
    }
    logger.info("[Tool] query_stock_info 完成: source=%s fields=%d", data_source, len(info_dict))
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================
# 工具 2: 上市公司财务指标查询
# 三层降级: 东方财富利润表 → 财务分析指标 → 内置模拟数据
# ============================================================
@tool
def query_financial_indicators(stock_code: str) -> str:
    """
    查询上市公司核心财务指标，包括营业收入、净利润、毛利率、净利率、ROE、EPS等。

    参数:
        stock_code: A 股股票代码，如 "600196"（复星医药）

    返回:
        JSON 格式字符串，包含营业总收入、同比增长率、归母净利润、毛利率、ROE、EPS 等。
        网络不可用时返回内置模拟数据（标注数据来源）。
    """
    logger.info("[Tool] query_financial_indicators: stock_code=%s", stock_code)

    # ---- 第零层：同花顺官方 API（四层降级链 L0，docs/HITHINK_INTEGRATION_PLAN.md）----
    from app.tools.hithink_tools import is_enabled as _hithink_on
    if _hithink_on():
        try:
            from app.tools.hithink_tools import fetch_financial_indicators as _ht_fin

            indicators = _ht_fin(stock_code)
            indicators.setdefault("data_source", "同花顺官方API")
            logger.info("[Tool] 同花顺官方API财务指标成功: period=%s", indicators.get("report_period"))
            return json.dumps({"error": False, "degraded": False, "indicators": indicators},
                              ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("[Tool] 同花顺官方API失败，落回 AKShare 链: %s", str(e)[:120])

    indicators: Dict[str, Any] = {}
    data_source: str = "未知"

    try:
        import akshare as ak

        # ---- 第一层：东方财富利润表主接口 ----
        logger.info("[Tool] 尝试主数据源: AKShare 东方财富利润表")
        profit_df = _safe_request(
            func=lambda: ak.stock_profit_sheet_by_report_em(symbol=stock_code),
            func_name="stock_profit_sheet_by_report_em",
            max_retries=2,
        )

        if profit_df is not None and hasattr(profit_df, 'empty') and not profit_df.empty:
            try:
                latest = profit_df.head(1).to_dict("records")[0]
            except (IndexError, KeyError, AttributeError):
                latest = {}

            indicators = {
                "stock_code": stock_code,
                "report_period": str(latest.get("报告期", "未知")),
                "total_revenue": str(latest.get("营业总收入", "N/A")),
                "revenue_yoy_growth": str(latest.get("营业总收入同比增长率", "N/A")),
                "net_profit": str(latest.get("归母净利润", "N/A")),
                "net_profit_yoy_growth": str(latest.get("归母净利润同比增长率", "N/A")),
                "gross_margin": str(latest.get("毛利率", "N/A")),
                "net_margin": str(latest.get("净利率", "N/A")),
                "roe": str(latest.get("净资产收益率", "N/A")),
                "eps": str(latest.get("基本每股收益", "N/A")),
                "data_source": "AKShare (东方财富利润表)",
            }
            data_source = "AKShare (东方财富利润表)"
            logger.info("[Tool] 东方财富利润表成功: period=%s", indicators.get("report_period"))
        else:
            logger.warning("[Tool] 东方财富利润表返回空数据，尝试备用数据源")

        # ---- 第二层：财务分析指标备用接口 ----
        if not indicators:
            logger.info("[Tool] 尝试备用数据源: AKShare 财务分析指标")
            try:
                analysis_df = _safe_request(
                    func=lambda: ak.stock_financial_analysis_indicator(symbol=stock_code),
                    func_name="stock_financial_analysis_indicator",
                    max_retries=1,
                )
                if analysis_df is not None and hasattr(analysis_df, 'empty') and not analysis_df.empty:
                    try:
                        latest_row = analysis_df.head(1).to_dict("records")[0]
                    except (IndexError, KeyError, AttributeError):
                        latest_row = {}
                    indicators = {
                        "stock_code": stock_code,
                        "report_period": str(latest_row.get("报告期", latest_row.get("日期", "未知"))),
                        "total_revenue": str(latest_row.get("营业总收入", latest_row.get("营业收入", "N/A"))),
                        "net_profit": str(latest_row.get("归母净利润", latest_row.get("净利润", "N/A"))),
                        "roe": str(latest_row.get("净资产收益率", latest_row.get("ROE", "N/A"))),
                        "eps": str(latest_row.get("基本每股收益", latest_row.get("每股收益", "N/A"))),
                        "gross_margin": str(latest_row.get("销售毛利率", "N/A")),
                        "net_margin": str(latest_row.get("销售净利率", "N/A")),
                        "revenue_yoy_growth": str(latest_row.get("营业收入同比增长率", "N/A")),
                        "net_profit_yoy_growth": str(latest_row.get("归母净利润同比增长率", "N/A")),
                        "data_source": "AKShare (财务分析指标备用)",
                    }
                    data_source = "AKShare (财务分析指标备用)"
                    logger.info("[Tool] 财务分析指标备用接口成功")
            except Exception as e:
                logger.warning("[Tool] 财务分析指标备用接口失败: %s", str(e)[:100])

        # ---- 第三层：内置模拟数据兜底 ----
        if not indicators:
            logger.info("[Tool] 网络数据源全部失败，使用内置模拟数据")
            indicators = _get_mock_financial(stock_code)
            data_source = indicators.get("data_source", "内置模拟数据")

    except ImportError:
        logger.warning("[Tool] akshare 库未安装，使用内置模拟数据")
        indicators = _get_mock_financial(stock_code)
        data_source = "内置模拟数据（akshare未安装）"
    except Exception as e:
        logger.error("[Tool] query_financial_indicators 未预期异常: %s", str(e)[:100])
        indicators = _get_mock_financial(stock_code)
        data_source = f"内置模拟数据（异常降级: {str(e)[:50]}）"

    if "data_source" not in indicators:
        indicators["data_source"] = data_source

    logger.info("[Tool] query_financial_indicators 完成: source=%s", data_source)
    return json.dumps({"error": False, "degraded": "模拟数据" in data_source, "indicators": indicators}, ensure_ascii=False, indent=2)


# ============================================================
# 工具 3: A 股实时行情查询（延时 15 分钟）
# ============================================================
def _tencent_quote_supplement_batch(stock_codes) -> Dict[str, Dict]:
    """批量版腾讯行情补充（单次请求，最多 30 只）。返回 {6位代码: supplement_dict}。

    字段下标实测校准（2026-08-30，与同花顺估值端点交叉验证：PE 18.02/PB 1.25 一致）：
    [38]=换手率% [39]=PE(TTM) [45]=总市值(亿) [46]=PB
    任何失败静默返回空 dict，绝不影响主流程。
    """
    qids, valid = [], []
    for c in stock_codes[:30]:
        code = str(c).strip().split(".")[0]
        if not (len(code) == 6 and code.isdigit()):
            continue
        suffix = "sh" if code.startswith("6") else ("bj" if code.startswith(("4", "8")) else "sz")
        qids.append(f"{suffix}{code}")
        valid.append(code)
    if not qids:
        return {}
    try:
        import httpx
        resp = httpx.get("https://qt.gtimg.cn/q=" + ",".join(qids), timeout=3)
        resp.raise_for_status()
        out: Dict[str, Dict] = {}
        for line in resp.content.decode("gbk", errors="ignore").splitlines():
            if '="' not in line or "v_" not in line:
                continue
            code = line.split("v_")[1].split("=")[0][2:]  # v_sh600196 → 600196
            fields = line.split('="')[1].split("~")
            if code not in valid or len(fields) <= 46:
                continue
            supp: Dict = {}
            if fields[38] and fields[38] not in ("", "0"):
                supp["换手率"] = f"{fields[38]}%"
            if fields[39]:
                supp["市盈率"] = fields[39]
            if fields[46]:
                supp["市净率"] = fields[46]
            if fields[45]:
                try:
                    supp["总市值"] = str(float(fields[45]) * 1e8)  # 亿 → 元，对齐前端 formatBigInt
                except ValueError:
                    pass
            if supp:
                out[code] = supp
        return out
    except Exception:
        return {}


def _tencent_quote_supplement(stock_code: str) -> Dict:
    """单股腾讯行情补充字段（换手率/市盈率/市净率/总市值）。"""
    return _tencent_quote_supplement_batch([stock_code]).get(
        str(stock_code).strip().split(".")[0], {})


@tool
def query_stock_quote(stock_code: str) -> str:
    """
    查询 A 股实时行情（延时 15 分钟），包括最新价、涨跌幅、成交量、市值等。

    参数:
        stock_code: A 股股票代码，如 "600196"（复星医药）

    返回:
        JSON 格式字符串，包含最新价、涨跌幅、成交量、市盈率、总市值等。
        标注 "延时": "15分钟"。网络不可用时返回内置模拟数据。
    """
    logger.info("[Tool] query_stock_quote: stock_code=%s", stock_code)

    # ---- 第零层：同花顺官方 API（四层降级链 L0，docs/HITHINK_INTEGRATION_PLAN.md）----
    from app.tools.hithink_tools import is_enabled as _hithink_on
    if _hithink_on():
        try:
            from app.tools.hithink_tools import fetch_quote as _ht_quote

            quote = _ht_quote(stock_code)
            # 行情快照缺换手率/PE/PB/总市值，用腾讯行情补齐（同花顺估值端点无这几项）
            supplement = _tencent_quote_supplement(stock_code)
            if supplement:
                for k, v in supplement.items():
                    quote.setdefault(k, v)
                quote["data_source"] = "同花顺官方API·腾讯行情补充"
            quote.setdefault("data_source", "同花顺官方API")
            logger.info("[Tool] 同花顺官方API行情成功: price=%s", quote.get("最新价"))
            return json.dumps({"error": False, "degraded": False, "quote": quote},
                              ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("[Tool] 同花顺官方API失败，落回 AKShare 链: %s", str(e)[:120])

    quote: Dict[str, Any] = {}
    data_source: str = "未知"

    try:
        import akshare as ak

        # ---- 第一层：东方财富实时行情 ----
        logger.info("[Tool] 尝试主数据源: AKShare 东方财富实时行情")
        spot_df = _safe_request(
            func=_get_spot_em_cached,
            func_name="stock_zh_a_spot_em",
            max_retries=2,
        )

        if spot_df is not None and hasattr(spot_df, 'empty') and not spot_df.empty:
            # 从全市场数据中筛选目标股票
            matched = spot_df[spot_df["代码"] == stock_code]
            if not matched.empty:
                row = matched.iloc[0]
                quote = {
                    "stock_code": stock_code,
                    "最新价": str(row.get("最新价", "N/A")),
                    "涨跌幅": str(row.get("涨跌幅", "N/A")),
                    "涨跌额": str(row.get("涨跌额", "N/A")),
                    "成交量": str(row.get("成交量", "N/A")),
                    "成交额": str(row.get("成交额", "N/A")),
                    "振幅": str(row.get("振幅", "N/A")),
                    "最高": str(row.get("最高", "N/A")),
                    "最低": str(row.get("最低", "N/A")),
                    "今开": str(row.get("今开", "N/A")),
                    "昨收": str(row.get("昨收", "N/A")),
                    "换手率": str(row.get("换手率", "N/A")),
                    "市盈率-动态": str(row.get("市盈率-动态", "N/A")),
                    "市净率": str(row.get("市净率", "N/A")),
                    "总市值": str(row.get("总市值", "N/A")),
                    "流通市值": str(row.get("流通市值", "N/A")),
                    "延时": "15分钟",
                    "data_source": "AKShare (东方财富)",
                }
                data_source = "AKShare (东方财富)"
                logger.info("[Tool] 东方财富实时行情成功: price=%s", quote.get("最新价"))
            else:
                logger.warning("[Tool] 未找到股票代码 %s 的行情数据", stock_code)

        # ---- 第二层：新浪财经备用 ----
        if not quote:
            logger.info("[Tool] 尝试备用数据源: 新浪财经")
            try:
                sina_df = _safe_request(
                    func=_get_spot_sina_cached,
                    func_name="stock_zh_a_spot_sina",
                    max_retries=1,
                )
                if sina_df is not None and hasattr(sina_df, 'empty') and not sina_df.empty:
                    matched = sina_df[sina_df["代码"] == stock_code]
                    if not matched.empty:
                        row = matched.iloc[0]
                        quote = {
                            "stock_code": stock_code,
                            "最新价": str(row.get("最新价", "N/A")),
                            "涨跌幅": str(row.get("涨跌幅", "N/A")),
                            "涨跌额": str(row.get("涨跌额", "N/A")),
                            "成交量": str(row.get("成交量", "N/A")),
                            "成交额": str(row.get("成交额", "N/A")),
                            "振幅": str(row.get("振幅", "N/A")),
                            "最高": str(row.get("最高", "N/A")),
                            "最低": str(row.get("最低", "N/A")),
                            "今开": str(row.get("今开", "N/A")),
                            "昨收": str(row.get("昨收", "N/A")),
                            "换手率": str(row.get("换手率", "N/A")),
                            "市盈率": str(row.get("市盈率", "N/A")),
                            "市净率": str(row.get("市净率", "N/A")),
                            "总市值": str(row.get("总市值", "N/A")),
                            "流通市值": str(row.get("流通市值", "N/A")),
                            "延时": "15分钟",
                            "data_source": "AKShare (新浪财经备用)",
                        }
                        data_source = "AKShare (新浪财经备用)"
                        logger.info("[Tool] 新浪财经备用接口成功")
            except Exception as e:
                logger.warning("[Tool] 新浪财经备用接口失败: %s", str(e)[:100])

        # ---- 第三层：内置模拟数据兜底 ----
        if not quote:
            logger.info("[Tool] 网络数据源全部失败，使用内置模拟数据")
            quote = _get_mock_quote(stock_code)
            data_source = quote.get("data_source", "内置模拟数据")

    except ImportError:
        logger.warning("[Tool] akshare 库未安装，使用内置模拟数据")
        quote = _get_mock_quote(stock_code)
        data_source = "内置模拟数据（akshare未安装）"
    except Exception as e:
        logger.error("[Tool] query_stock_quote 未预期异常: %s", str(e)[:100])
        quote = _get_mock_quote(stock_code)
        data_source = f"内置模拟数据（异常降级: {str(e)[:50]}）"

    if "data_source" not in quote:
        quote["data_source"] = data_source

    logger.info("[Tool] query_stock_quote 完成: source=%s", data_source)
    return json.dumps({"error": False, "degraded": "模拟数据" in data_source, "quote": quote}, ensure_ascii=False, indent=2)



@tool
def query_stock_news(stock_code: str) -> str:
    """
    查询 A 股个股最新新闻和公告信息。

    参数:
        stock_code: A 股股票代码，如 "600196"（复星医药）

    返回:
        JSON 格式字符串，包含新闻标题、发布时间、来源、内容摘要。
        网络不可用时返回内置模拟数据（标注数据来源）。
    """
    logger.info("[Tool] query_stock_news: stock_code=%s", stock_code)

    news_list: list = []
    data_source: str = "未知"

    try:
        import akshare as ak

        # ---- 第一层：东方财富个股新闻 ----
        logger.info("[Tool] 尝试主数据源: AKShare 东方财富个股新闻")
        news_df = _safe_request(
            func=lambda: ak.stock_news_em(symbol=stock_code),
            func_name="stock_news_em",
            max_retries=2,
        )

        if news_df is not None and hasattr(news_df, 'empty') and not news_df.empty:
            for _, row in news_df.head(10).iterrows():
                news_list.append({
                    "title": str(row.get("新闻标题", row.get("title", "N/A"))),
                    "content": str(row.get("新闻内容", row.get("content", "N/A")))[:200],
                    "publish_time": str(row.get("发布时间", row.get("time", "N/A"))),
                    "source": str(row.get("文章来源", row.get("source", "东方财富"))),
                })
            data_source = "AKShare (东方财富)"
            logger.info("[Tool] 东方财富个股新闻成功: %d条", len(news_list))

        # ---- 第二层：新浪财经备用 ----
        if not news_list:
            logger.info("[Tool] 尝试备用数据源: 新浪财经个股新闻")
            try:
                sina_news = _safe_request(
                    func=lambda: ak.stock_news_sina(symbol=stock_code),
                    func_name="stock_news_sina",
                    max_retries=1,
                )
                if sina_news is not None and hasattr(sina_news, 'empty') and not sina_news.empty:
                    for _, row in sina_news.head(10).iterrows():
                        news_list.append({
                            "title": str(row.get("标题", row.get("title", "N/A"))),
                            "content": str(row.get("内容", row.get("content", "N/A")))[:200],
                            "publish_time": str(row.get("时间", row.get("time", "N/A"))),
                            "source": "新浪财经",
                        })
                    data_source = "AKShare (新浪财经备用)"
            except Exception as e:
                logger.warning("[Tool] 新浪财经备用接口失败: %s", str(e)[:100])

        # ---- 第三层：内置模拟数据兜底 ----
        if not news_list:
            logger.info("[Tool] 网络数据源全部失败，使用内置模拟数据")
            news_list = _get_mock_news(stock_code)
            data_source = "内置模拟数据（网络不可用时的最终兜底）"

    except ImportError:
        logger.warning("[Tool] akshare 库未安装，使用内置模拟数据")
        news_list = _get_mock_news(stock_code)
        data_source = "内置模拟数据（akshare未安装）"
    except Exception as e:
        logger.error("[Tool] query_stock_news 未预期异常: %s", str(e)[:100])
        news_list = _get_mock_news(stock_code)
        data_source = f"内置模拟数据（异常降级: {str(e)[:50]}）"

    logger.info("[Tool] query_stock_news 完成: source=%s, count=%d", data_source, len(news_list))
    return json.dumps({"error": False, "degraded": "模拟数据" in data_source, "news": news_list, "data_source": data_source}, ensure_ascii=False, indent=2)


def _get_mock_news(stock_code: str) -> list:
    """内置模拟新闻数据（来自 mock_snapshot.py 快照）"""
    from app.tools.mock_snapshot import get_mock_news
    return get_mock_news(stock_code)



# ============================================================
# 工具列表（注册到 LangGraph ToolNode）
# ============================================================
AKSHARE_TOOLS = [
    query_stock_info,
    query_financial_indicators,
    query_stock_quote,
    query_stock_news,
]


# ============================================================
# 工具 4: 个股新闻/公告（阶段 5 新增）
# 三层降级: 东方财富 → 新浪 → 内置模拟
# ============================================================

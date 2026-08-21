"""
AKShare A 股数据工具层
- 三层降级：东方财富 → 雪球/新浪 → 内置模拟数据
- 模块级代理清理（消除 VPN/系统代理残留）
- 所有工具永不抛异常，返回结构化 JSON
- 支持 LangChain @tool 装饰器（Function Calling 就绪）

依赖: akshare >= 1.16.0
"""
import json
import os
import time
import logging
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
# 内置模拟数据 — 网络彻底不可用时的最终兜底
# ============================================================
_MOCK_STOCK_INFO: Dict[str, str] = {
    "公司名称": "示例公司",
    "公司全称": "示例股份有限公司",
    "所属行业": "制造业",
    "上市日期": "2000-01-01",
    "上市板块": "上海证券交易所主板",
    "总股本": "10亿股",
    "流通股本": "8亿股",
    "注册地址": "上海市浦东新区",
    "主营业务": "（模拟数据）",
    "董事长": "（模拟）",
    "员工人数": "约10000人",
}

_MOCK_FINANCIAL: Dict[str, Any] = {
    "stock_code": "000000",
    "report_period": "最近报告期",
    "total_revenue": "模拟数据",
    "revenue_yoy_growth": "模拟数据",
    "net_profit": "模拟数据",
    "net_profit_yoy_growth": "模拟数据",
    "gross_margin": "模拟数据",
    "net_margin": "模拟数据",
    "roe": "模拟数据",
    "eps": "模拟数据",
    "data_source": "内置模拟数据（网络不可用时的最终兜底）",
}

_MOCK_QUOTE: Dict[str, Any] = {
    "stock_code": "000000",
    "最新价": "模拟",
    "涨跌幅": "模拟",
    "涨跌额": "模拟",
    "成交量": "模拟",
    "成交额": "模拟",
    "振幅": "模拟",
    "最高": "模拟",
    "最低": "模拟",
    "今开": "模拟",
    "昨收": "模拟",
    "换手率": "模拟",
    "市盈率": "模拟",
    "市净率": "模拟",
    "总市值": "模拟",
    "流通市值": "模拟",
    "延时": "15分钟（模拟）",
    "data_source": "内置模拟数据（网络不可用时的最终兜底）",
}


def _get_mock_info(stock_code: str) -> Dict[str, str]:
    """根据股票代码返回对应的模拟基本信息"""
    data = dict(_MOCK_STOCK_INFO)
    data["股票代码"] = stock_code
    return data


def _get_mock_financial(stock_code: str) -> Dict[str, Any]:
    """根据股票代码返回对应的模拟财务指标"""
    data = dict(_MOCK_FINANCIAL)
    data["stock_code"] = stock_code
    return data


def _get_mock_quote(stock_code: str) -> Dict[str, Any]:
    """根据股票代码返回对应的模拟行情"""
    data = dict(_MOCK_QUOTE)
    data["stock_code"] = stock_code
    return data


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

    result = {
        "error": False,
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
    return json.dumps({"error": False, "indicators": indicators}, ensure_ascii=False, indent=2)


# ============================================================
# 工具 3: A 股实时行情查询（延时 15 分钟）
# ============================================================
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

    quote: Dict[str, Any] = {}
    data_source: str = "未知"

    try:
        import akshare as ak

        # ---- 第一层：东方财富实时行情 ----
        logger.info("[Tool] 尝试主数据源: AKShare 东方财富实时行情")
        spot_df = _safe_request(
            func=lambda: ak.stock_zh_a_spot_em(),
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
                    func=lambda: ak.stock_zh_a_spot_sina(),
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
    return json.dumps({"error": False, "quote": quote}, ensure_ascii=False, indent=2)


# ============================================================
# 工具列表（注册到 LangGraph ToolNode）
# ============================================================
AKSHARE_TOOLS = [
    query_stock_info,
    query_financial_indicators,
    query_stock_quote,
]

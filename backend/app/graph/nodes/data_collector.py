"""
DataCollector 节点 — 金融数据接入 LangGraph

职责:
1. 从查询/股票代码提取代码 → 并行调 AKShare 工具 → 写入 state
2. 任一工具失败不影响另一工具（部分成功策略）
3. 所有工具失败时记录 error_log，流程继续（不中断）
4. 兼容多轮会话：已有数据时跳过重复拉取

面试亮点:
- 扇出并行：3 个独立工具同时调用，减少总延迟
- 降级不中断：工具失败记录到 error_log，流程继续
- 数据源标注：每个数据都标注来源，提升报告可审计性
"""
import re
import json
import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from app.graph.state import AgentState
from app.tools.akshare_tools import (
    query_stock_info,
    query_financial_indicators,
    query_stock_quote,
)

log = logging.getLogger("data_collector")


def _extract_stock_code(state: AgentState) -> str:
    """
    从 state 中提取股票代码。

    优先级:
    1. pending_stock_code（planner 已提取）
    2. user_query 中正则匹配（6 位数字，以 3/6/0 开头）
    3. 返回空字符串（表示无股票代码）
    """
    # 1. 优先使用已提取的代码
    code = state.get("pending_stock_code", "")
    if code and len(code) == 6 and code.isdigit():
        return code

    # 2. 从 query 中正则匹配
    query = state.get("query", "")
    # A 股代码模式：3/6 开头（沪市 60xxxx, 深市 00xxxx/30xxxx）
    patterns = [
        r"\b([36]0\d{4})\b",   # 沪市主板 60xxxx, 创业板 30xxxx
        r"\b(00\d{4})\b",       # 深市主板 00xxxx
        r"(\d{6})",             # 兜底：任意 6 位数字
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            code = match.group(1)
            log.info("[DataCollector] 从 query 提取股票代码: %s", code)
            return code

    return ""


def data_collector_node(state: AgentState) -> Dict[str, Any]:
    """
    金融数据收集节点。

    从 state 获取待分析股票代码，并行调用股票信息查询、财务指标查询和实时行情查询。
    任一工具失败不影响其他工具（部分成功策略）。
    所有工具失败时记录 error_log，流程继续不中断。

    Args:
        state: 当前 AgentState

    Returns:
        dict: 包含 financial_data, data_sources, error_log（如有错误）
    """
    error_log = list(state.get("error_log", []))
    existing_data = dict(state.get("financial_data", {}))
    existing_sources = list(state.get("data_sources", []))

    # ---- 提取股票代码 ----
    stock_code = _extract_stock_code(state)

    # 如果没有股票代码，跳过数据收集
    if not stock_code:
        log.info("[DataCollector] 未找到股票代码，跳过金融数据收集")
        return {
            "financial_data": existing_data,
            "data_sources": existing_sources,
            "error_log": error_log,
        }

    # 如果已有该股票数据（多轮会话），跳过重复拉取
    if existing_data.get("stock_code") == stock_code:
        log.info("[DataCollector] 已有 %s 数据，跳过重复拉取", stock_code)
        return {
            "financial_data": existing_data,
            "data_sources": existing_sources,
            "error_log": error_log,
        }

    log.info("[DataCollector] 开始拉取 %s 的金融数据", stock_code)

    # ---- 并行调用工具（面试亮点: 扇出并行） ----
    financial_data: Dict[str, Any] = {"stock_code": stock_code}
    data_sources: List[str] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_info = executor.submit(query_stock_info.invoke, stock_code)
        future_financial = executor.submit(query_financial_indicators.invoke, stock_code)
        future_quote = executor.submit(query_stock_quote.invoke, stock_code)

        # 收集结果（任一失败不影响另一）
        # 股票基本信息
        try:
            info_result = future_info.result(timeout=30)
            info_data = json.loads(info_result)
            if not info_data.get("error") and info_data.get("info"):
                financial_data["stock_info"] = info_data["info"]
                data_sources.append(info_data.get("data_source", "AKShare"))
                log.info("[DataCollector] 股票信息: %d 字段", len(info_data["info"]))
            else:
                error_log.append(f"[DataCollector] 股票信息查询失败: {info_data.get('message', '未知错误')}")
        except Exception as e:
            error_log.append(f"[DataCollector] 股票信息查询异常: {str(e)[:100]}")

        # 财务指标
        try:
            fin_result = future_financial.result(timeout=30)
            fin_data = json.loads(fin_result)
            if not fin_data.get("error") and fin_data.get("indicators"):
                financial_data["indicators"] = fin_data["indicators"]
                data_sources.append(fin_data["indicators"].get("data_source", "AKShare"))
                log.info("[DataCollector] 财务指标: period=%s", fin_data["indicators"].get("report_period", "N/A"))
            else:
                error_log.append(f"[DataCollector] 财务指标查询失败: {fin_data.get('message', '未知错误')}")
        except Exception as e:
            error_log.append(f"[DataCollector] 财务指标查询异常: {str(e)[:100]}")

        # 实时行情
        try:
            quote_result = future_quote.result(timeout=30)
            quote_data = json.loads(quote_result)
            if not quote_data.get("error") and quote_data.get("quote"):
                financial_data["quote"] = quote_data["quote"]
                data_sources.append(quote_data["quote"].get("data_source", "AKShare"))
                log.info("[DataCollector] 实时行情: price=%s", quote_data["quote"].get("最新价", "N/A"))
            else:
                error_log.append(f"[DataCollector] 实时行情查询失败: {quote_data.get('message', '未知错误')}")
        except Exception as e:
            error_log.append(f"[DataCollector] 实时行情查询异常: {str(e)[:100]}")

    # 去重数据源
    data_sources = list(dict.fromkeys(data_sources))  # 保持顺序去重

    log.info(
        "[DataCollector] 数据收集完成: code=%s sources=%s errors=%d",
        stock_code, data_sources, len(error_log) - len(state.get("error_log", []))
    )

    return {
        "financial_data": financial_data,
        "data_sources": data_sources,
        "error_log": error_log,
    }

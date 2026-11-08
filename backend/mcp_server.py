"""
IRIS MCP Server（stdio）

把 IRIS 的金融数据工具以 MCP 协议暴露，任意 MCP 客户端（Claude Code /
inspector / 其他 Agent）可复用 IRIS 的数据能力——工具层与 Web 前端解耦。

用法：
    cd backend
    python mcp_server.py                # stdio 传输
    npx @modelcontextprotocol/inspector python mcp_server.py   # 调试

安全边界：只暴露只读工具（readOnlyHint），不含写入/删除类操作；
行情数据可能为 15 分钟延时或模拟兜底数据，字段 data_source/degraded 标明口径。
"""

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    "IRIS FinData",
    instructions=(
        "IRIS A 股投研数据工具集：公司概况 / 财务指标 / 实时行情 / 个股新闻 / 研报 PDF 检索。"
        "所有工具只读；行情字段含 data_source 与 degraded，注意口径（模拟数据不可当真实数据引用）。"
    ),
)


def _parse(raw: str) -> dict[str, Any]:
    """akshare 工具返回 JSON 字符串；统一解析并透传 error/degraded 口径字段。"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": True, "message": "工具返回非 JSON 输出", "raw": raw[:200]}


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def query_stock_info(stock_code: str) -> str:
    """查询 A 股公司概况：主营业务、行业、上市日期、总股本等（stock_code 如 "600196"）。"""
    from app.tools.akshare_tools import query_stock_info as _q

    return _q.invoke(stock_code)


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def query_financial_indicators(stock_code: str) -> str:
    """查询 A 股财务指标：营收/净利/ROE/负债率等按报告期（stock_code 如 "600196"）。"""
    from app.tools.akshare_tools import query_financial_indicators as _q

    return _q.invoke(stock_code)


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def query_stock_quote(stock_code: str) -> str:
    """查询 A 股实时行情：最新价/涨跌幅/PE/总市值（可能为 15 分钟延时或模拟兜底，看 data_source）。"""
    from app.tools.akshare_tools import query_stock_quote as _q

    return _q.invoke(stock_code)


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def query_stock_news(stock_code: str) -> str:
    """查询 A 股个股近期新闻/公告聚合（stock_code 如 "600196"）。"""
    from app.tools.akshare_tools import query_stock_news as _q

    return _q.invoke(stock_code)


@mcp.tool(annotations={"readOnlyHint": True})
def search_reports(query: str) -> str:
    """检索已入库的研报 PDF 知识库（ChromaDB 向量检索 + DashScope gte-rerank 精排，失败自动降级纯向量）。"""
    from app.rag.engine import get_retriever

    retriever = get_retriever()
    if retriever is None:
        return json.dumps([], ensure_ascii=False)  # 知识库为空
    docs = retriever.invoke(query)
    return json.dumps(
        [
            {
                "source": d.metadata.get("source", d.metadata.get("source_path", "")),
                "page": d.metadata.get("page", ""),
                "content": d.page_content[:500],
            }
            for d in docs
        ],
        ensure_ascii=False,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")

"""
Function Calling 搜索工具
- 将 Tavily 搜索封装为 LangChain @tool
- LLM 自主决定何时调用、调用什么参数
"""
from langchain_core.tools import tool
from app.tools.search import search_tavily as _search_tavily
from app.utils.logger import get_logger

log = get_logger("search_tools")


@tool
def search_web(query: str) -> str:
    """搜索互联网获取最新信息。当需要了解新闻、行业动态、公司公告、市场观点时使用此工具。参数 query 为搜索关键词，如 '复星医药 2025 年报'。"""
    try:
        log.info(f"[Function Calling] search_web 被调用: {query}")
        result = _search_tavily(query)
        return result if result else "搜索结果为空"
    except Exception as e:
        log.error(f"[Function Calling] search_web 调用失败: {e}")
        return f"搜索失败: {e}"

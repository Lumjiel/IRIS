"""Built-in web search tool backed by Tavily."""
from typing import Optional
from app.tools.registry import ToolRegistry


@ToolRegistry.register(
    name="web_search",
    description="搜索互联网获取最新信息。适用于：实时新闻、技术文档、行业动态、竞品信息、公众号文章。",
)
def web_search(query: str) -> Optional[str]:
    from app.tools.search import search_tavily
    return search_tavily(query)

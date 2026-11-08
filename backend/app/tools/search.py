from tavily import TavilyClient
import os
import time
from app.utils.logger import get_logger
from app.config import TAVILY_MAX_RESULTS, TAVILY_MAX_RETRIES

log = get_logger("search")

# 初始化 Tavily 客户端（启动时校验 key）
_tavily_key = os.getenv("TAVILY_API_KEY")
if not _tavily_key:
    log.warning("TAVILY_API_KEY 未配置，搜索功能不可用")
tavily = TavilyClient(api_key=_tavily_key) if _tavily_key else None


def search_tavily(query: str):
    """使用 Tavily 搜索网络"""
    if not tavily:
        raise RuntimeError("Tavily API 未配置")

    log.info(f"正在搜索: {query}")

    for attempt in range(TAVILY_MAX_RETRIES):
        try:
            response = tavily.search(query=query, search_depth="basic", max_results=TAVILY_MAX_RESULTS)
            context = [result["content"] for result in response["results"]]
            return "\n".join(context)
        except Exception as e:
            if attempt < TAVILY_MAX_RETRIES - 1:
                log.warning(f"搜索失败 (第{attempt+1}次): {e}，2秒后重试")
                time.sleep(2)
            else:
                log.error(f"搜索所有尝试均失败: {e}")
                raise
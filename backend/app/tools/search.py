from tavily import TavilyClient
import os
import time
from dotenv import load_dotenv

load_dotenv()

# 初始化 Tavily 客户端
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def search_tavily(query: str, max_retries: int = 2):
    """
    使用 Tavily 搜索网络。
    返回最相关的 3 条内容。支持重试。
    """
    print(f"--- [工具调用] 正在搜索: {query} ---")

    for attempt in range(max_retries):
        try:
            response = tavily.search(query=query, search_depth="basic", max_results=3)
            context = [result["content"] for result in response["results"]]
            return "\n".join(context)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"--- [搜索] 第 {attempt + 1} 次尝试失败: {e}，2秒后重试 ---")
                time.sleep(2)
            else:
                print(f"--- [搜索] 所有尝试均失败: {e} ---")
                raise
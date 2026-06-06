import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from app.config import LLM_TIMEOUT_FAST, LLM_TIMEOUT_SMART

load_dotenv()

# 模型配置（从环境变量读取，支持降级）
PRIMARY_MODEL = os.getenv("LLM_MODEL_PRIMARY", "qwen3.7-plus")
FALLBACK_MODEL = os.getenv("LLM_MODEL_FALLBACK", "deepseek-v4-flash")


def get_llm(model_type="fast"):
    """
    模型工厂函数。
    :param model_type: "fast" (规划/写作) 或 "smart" (审查/评分)
    两个类型都用同一个模型，仅 temperature 不同。
    """
    temp = 0.7 if model_type == "fast" else 0
    timeout = LLM_TIMEOUT_FAST if model_type == "fast" else LLM_TIMEOUT_SMART

    return ChatOpenAI(
        model=PRIMARY_MODEL,
        temperature=temp,
        base_url=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY"),
        request_timeout=timeout
    )
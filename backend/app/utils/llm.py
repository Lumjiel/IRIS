import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv
from app.config import LLM_TIMEOUT_FAST, LLM_TIMEOUT_SMART
from app.utils.logger import get_logger

load_dotenv()
log = get_logger("llm")

PRIMARY_MODEL = os.getenv("LLM_MODEL_PRIMARY", "qwen3.7-plus")
FALLBACK_MODEL = os.getenv("LLM_MODEL_FALLBACK", "deepseek-v4-flash")

# 降级状态：主模型是否已确认不可用
_primary_exhausted = False


def get_llm(model_type="fast"):
    """
    模型工厂函数。
    :param model_type: "fast" (规划/写作) 或 "smart" (审查/评分)
    """
    temp = 0.7 if model_type == "fast" else 0
    timeout = LLM_TIMEOUT_FAST if model_type == "fast" else LLM_TIMEOUT_SMART

    model = FALLBACK_MODEL if _primary_exhausted else PRIMARY_MODEL

    return ChatOpenAI(
        model=model,
        temperature=temp,
        base_url=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY"),
        request_timeout=timeout
    )


def llm_invoke(messages: list[BaseMessage], model_type="fast"):
    """
    带降级的 LLM 调用。
    主模型额度用完/超时时自动切换到备用模型。
    """
    global _primary_exhausted
    temp = 0.7 if model_type == "fast" else 0
    timeout = LLM_TIMEOUT_FAST if model_type == "fast" else LLM_TIMEOUT_SMART

    # 先试主模型
    if not _primary_exhausted:
        try:
            llm = ChatOpenAI(
                model=PRIMARY_MODEL,
                temperature=temp,
                base_url=os.getenv("OPENAI_API_BASE"),
                api_key=os.getenv("OPENAI_API_KEY"),
                request_timeout=timeout
            )
            return llm.invoke(messages)
        except Exception as e:
            err_msg = str(e).lower()
            # 判断是否为额度/配额耗尽
            if any(kw in err_msg for kw in ["quota", "limit", "insufficient", "balance", "429", "rate"]):
                log.warning(f"主模型 {PRIMARY_MODEL} 额度耗尽，降级到 {FALLBACK_MODEL}")
                _primary_exhausted = True
            else:
                # 非额度问题（网络超时等），也尝试降级
                log.warning(f"主模型 {PRIMARY_MODEL} 调用失败: {e}，尝试降级")

    # 降级到备用模型
    try:
        llm = ChatOpenAI(
            model=FALLBACK_MODEL,
            temperature=temp,
            base_url=os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY"),
            request_timeout=timeout
        )
        return llm.invoke(messages)
    except Exception as e:
        log.error(f"备用模型 {FALLBACK_MODEL} 也失败: {e}")
        raise
import os
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from app.config import LLM_TIMEOUT_FAST, LLM_TIMEOUT_SMART
from app.utils.logger import get_logger

log = get_logger("llm")

# 默认模型（向后兼容）
PRIMARY_MODEL = os.getenv("LLM_MODEL_PRIMARY", "qwen3.7-plus")
FALLBACK_MODEL = os.getenv("LLM_MODEL_FALLBACK", "deepseek-v4-flash")

# 按节点分配模型（未配置时回退到 PRIMARY_MODEL）
NODE_MODELS = {
    "router":     os.getenv("LLM_MODEL_ROUTER",     PRIMARY_MODEL),
    "planner":    os.getenv("LLM_MODEL_PLANNER",    PRIMARY_MODEL),
    "researcher": os.getenv("LLM_MODEL_RESEARCHER", PRIMARY_MODEL),
    "writer":     os.getenv("LLM_MODEL_WRITER",     PRIMARY_MODEL),
    "reviewer":   os.getenv("LLM_MODEL_REVIEWER",   PRIMARY_MODEL),
    "refiner":    os.getenv("LLM_MODEL_REFINER",    PRIMARY_MODEL),
}

# 降级状态
_primary_exhausted = False
_primary_exhausted_at = 0.0
_EXHAUSTED_TTL = 300  # 5分钟后自动恢复尝试主模型


def _is_exhausted() -> bool:
    global _primary_exhausted, _primary_exhausted_at
    if not _primary_exhausted:
        return False
    if time.time() - _primary_exhausted_at > _EXHAUSTED_TTL:
        log.info(f"主模型降级已过 TTL({_EXHAUSTED_TTL}s)，尝试恢复")
        _primary_exhausted = False
        return False
    return True


def _resolve_model(node: str | None = None) -> str:
    """解析模型名称：node 级 > 默认主模型"""
    if node and node in NODE_MODELS:
        return NODE_MODELS[node]
    return PRIMARY_MODEL


def get_llm(model_type="fast", node=None):
    """
    模型工厂函数。
    :param model_type: "fast" (规划/写作) 或 "smart" (审查/评分)
    :param node: 节点名称（router/planner/researcher/writer/reviewer/refiner）
    """
    temp = 0.7 if model_type == "fast" else 0
    timeout = LLM_TIMEOUT_FAST if model_type == "fast" else LLM_TIMEOUT_SMART

    model = FALLBACK_MODEL if _primary_exhausted else _resolve_model(node)

    return ChatOpenAI(
        model=model,
        temperature=temp,
        base_url=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY"),
        request_timeout=timeout
    )


def llm_invoke(messages: list[BaseMessage], model_type="fast", node=None):
    """
    带降级的 LLM 调用。
    主模型额度用完/超时时自动切换到备用模型。
    """
    global _primary_exhausted
    temp = 0.7 if model_type == "fast" else 0
    timeout = LLM_TIMEOUT_FAST if model_type == "fast" else LLM_TIMEOUT_SMART
    model_name = _resolve_model(node)

    # 先试主模型
    if not _is_exhausted():
        try:
            llm = ChatOpenAI(
                model=model_name,
                temperature=temp,
                base_url=os.getenv("OPENAI_API_BASE"),
                api_key=os.getenv("OPENAI_API_KEY"),
                request_timeout=timeout
            )
            return llm.invoke(messages)
        except Exception as e:
            global _primary_exhausted, _primary_exhausted_at
            err_msg = str(e).lower()
            if any(kw in err_msg for kw in ["quota", "limit", "insufficient", "balance", "429", "rate"]):
                log.warning(f"主模型 {model_name} 额度耗尽，降级到 {FALLBACK_MODEL}（{_EXHAUSTED_TTL}s 后自动恢复）")
                _primary_exhausted = True
                _primary_exhausted_at = time.time()
            else:
                log.warning(f"主模型 {model_name} 调用失败: {e}，尝试降级")

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
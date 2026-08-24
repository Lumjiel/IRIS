import os
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from app.config import LLM_TIMEOUT_FAST, LLM_TIMEOUT_SMART
from app.utils.logger import get_logger

log = get_logger("llm")

# === Token 用量统计（进程级累计，GET /api/usage 读取）===
# real：provider 返回的真实 usage（仅 invoke 路径）；
# est：流式路径 provider 不回传 usage，按中文字符≈1.6 chars/token 估算。两者分开累计。
import threading as _threading

_usage_lock = _threading.Lock()
_usage = {"calls": 0, "prompt": 0, "completion": 0,
          "calls_est": 0, "prompt_est": 0, "completion_est": 0}
_CHARS_PER_TOKEN = 1.6  # 中文混合文本经验值


def _record_usage_real(prompt_tokens: int, completion_tokens: int):
    with _usage_lock:
        _usage["calls"] += 1
        _usage["prompt"] += int(prompt_tokens)
        _usage["completion"] += int(completion_tokens)


def _record_usage_estimated(prompt_text: str, completion_text: str):
    with _usage_lock:
        _usage["calls_est"] += 1
        _usage["prompt_est"] += int(len(prompt_text) / _CHARS_PER_TOKEN)
        _usage["completion_est"] += int(len(completion_text) / _CHARS_PER_TOKEN)


def get_usage_snapshot(reset: bool = False) -> dict:
    with _usage_lock:
        snap = dict(_usage)
        if reset:
            for k in _usage:
                _usage[k] = 0
    total_prompt = snap["prompt"] + snap["prompt_est"]
    total_completion = snap["completion"] + snap["completion_est"]
    snap["total_tokens"] = total_prompt + total_completion
    snap["estimated_partial"] = snap["calls_est"] > 0
    return snap

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


_QUOTA_KEYWORDS = ("quota", "limit", "insufficient", "balance", "429", "rate", "freetier", "allocation")


def is_quota_error(e: Exception) -> bool:
    """判断异常是否为额度/限流类错误（需要触发主模型降级）。"""
    msg = str(e).lower()
    return any(kw in msg for kw in _QUOTA_KEYWORDS)


def mark_primary_exhausted(reason: str = ""):
    """外部（含流式路径）标记主模型降级，TTL 后自动恢复。"""
    global _primary_exhausted, _primary_exhausted_at
    _primary_exhausted = True
    _primary_exhausted_at = time.time()
    log.warning(f"主模型标记降级（{_EXHAUSTED_TTL}s 后自动恢复尝试）: {reason}")


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

    # 必须走 TTL 感知的 _is_exhausted()：读裸标志会让流式路径在 5 分钟 TTL 到期后
    # 仍永久钉死在 fallback 模型，无法自动恢复主模型
    model = FALLBACK_MODEL if _is_exhausted() else _resolve_model(node)

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
            resp = llm.invoke(messages)
            um = getattr(resp, "usage_metadata", None)
            if um:
                _record_usage_real(um.get("input_tokens", 0), um.get("output_tokens", 0))
            return resp
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
        resp = llm.invoke(messages)
        um = getattr(resp, "usage_metadata", None)
        if um:
            _record_usage_real(um.get("input_tokens", 0), um.get("output_tokens", 0))
        return resp
    except Exception as e:
        log.error(f"备用模型 {FALLBACK_MODEL} 也失败: {e}")
        raise
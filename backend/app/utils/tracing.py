"""
可观测性 (Langfuse) Trace 接入。

Langfuse 是生产级 LLM 观测平台（trace / token / 成本 / 延迟）。本模块把 Langfuse 的
CallbackHandler 挂到图执行 config 上，从而追踪每个节点、每次 LLM 调用、token 与成本。

未配置 LANGFUSE_PUBLIC_KEY / SECRET_KEY 时自动跳过，不影响运行。
"""
import os

from app.utils.logger import get_logger

log = get_logger("tracing")

_handler = None
_handler_checked = False


def get_langfuse_handler():
    """返回 Langfuse CallbackHandler（懒加载 + 缓存）。未配置返回 None。"""
    global _handler, _handler_checked
    if _handler_checked:
        return _handler
    _handler_checked = True

    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    sk = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").strip()

    if not pk or not sk:
        log.info("Langfuse 未配置（缺 LANGFUSE_PUBLIC_KEY/SECRET_KEY），跳过 tracing")
        _handler = None
        return None

    try:
        # langfuse 4.x: CallbackHandler 从环境变量读 LANGFUSE_SECRET_KEY/HOST
        from langfuse.langchain import CallbackHandler
        _handler = CallbackHandler(public_key=pk)
        log.info(f"Langfuse tracing 已启用 → {host}")
    except Exception as e:
        log.warning(f"Langfuse 初始化失败，跳过 tracing: {e}")
        _handler = None
    return _handler


def build_trace_config(base_config: dict) -> dict:
    """在 base_config 上附加 Langfuse callbacks（若已配置）。"""
    handler = get_langfuse_handler()
    if handler:
        config = dict(base_config)
        callbacks = list(config.get("callbacks", []))
        callbacks.append(handler)
        config["callbacks"] = callbacks
        return config
    return base_config
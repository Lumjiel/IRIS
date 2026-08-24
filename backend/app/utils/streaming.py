"""
LLM 流式输出模块
通过 asyncio.Queue 将 token 逐个推送到 SSE 生成器
"""
import asyncio
from contextvars import ContextVar
from langchain_core.messages import BaseMessage
from app.utils.llm import get_llm
from app.utils.logger import get_logger

log = get_logger("streaming")

_token_queue: ContextVar[asyncio.Queue | None] = ContextVar("token_queue", default=None)

# === 节点状态事件队列（前端时间线真实进度）===
_node_event_queue: ContextVar[asyncio.Queue | None] = ContextVar("node_event_queue", default=None)


def set_token_queue(q: asyncio.Queue | None):
    _token_queue.set(q)


def get_node_event_queue() -> asyncio.Queue | None:
    return _node_event_queue.get()

def set_node_event_queue(q: asyncio.Queue | None):
    _node_event_queue.set(q)

def emit_node_event(step: str, status: str, elapsed: float = 0.0):
    """节点发出 start/done 事件（供 traced_* 包装函数调用）。"""
    q = _node_event_queue.get()
    if q is not None:
        payload = {"step": step, "status": status}
        if elapsed > 0:
            payload["elapsed"] = round(elapsed, 2)
        q.put_nowait(payload)

def get_token_queue() -> asyncio.Queue | None:
    return _token_queue.get()


async def llm_stream_tokens(
    messages: list[BaseMessage],
    model_type: str = "fast",
    node_name: str = "",
    node: str | None = None,
) -> str:
    """
    流式调用 LLM，token 逐个推入队列。
    生产者（线程）写入 channel，消费者（async）读取并推入 queue。
    """
    queue = get_token_queue()

    if queue is None:
        from app.utils.llm import llm_invoke
        response = llm_invoke(messages, model_type=model_type, node=node)
        return response.content or ""

    llm = get_llm(model_type=model_type, node=node)
    channel = asyncio.Queue()
    full_text = ""

    def _producer():
        """在线程中运行同步的 llm.stream()，token 推入 channel。

        降级修复：流式路径此前无 quota 降级（llm_invoke 有、这里漏了），
        主模型 403 FreeTierOnly 时 writer 直接拿空报告。现对齐 invoke 行为：
        额度类错误 → 标记降级 → 用 fallback 模型重试一次。
        """
        try:
            try:
                for chunk in llm.stream(messages):
                    token = chunk.content or ""
                    if token:
                        asyncio.run_coroutine_threadsafe(channel.put(token), loop)
            except Exception as e:
                from app.utils import llm as llm_mod

                if not llm_mod.is_quota_error(e):
                    raise
                llm_mod.mark_primary_exhausted(str(e)[:150])
                log.warning("流式调用触发额度降级，改用备用模型重试")
                fallback_llm = get_llm(model_type=model_type, node=node)  # _is_exhausted 后自动选 FALLBACK
                for chunk in fallback_llm.stream(messages):
                    token = chunk.content or ""
                    if token:
                        asyncio.run_coroutine_threadsafe(channel.put(token), loop)
        except Exception as e:
            log.warning(f"流式调用异常: {e}")
        finally:
            asyncio.run_coroutine_threadsafe(channel.put(None), loop)  # 结束标记

    loop = asyncio.get_running_loop()
    import threading
    producer_thread = threading.Thread(target=_producer, daemon=True)
    producer_thread.start()

    # 消费者：从 channel 读取 token，推入 SSE queue
    while True:
        token = await channel.get()
        if token is None:
            break
        full_text += token
        await queue.put({
            "step": f"{node_name}_token",
            "data": {"token": token},
        })
        await asyncio.sleep(0)  # 让出事件循环

    await queue.put({
        "step": f"{node_name}_token",
        "data": {"token": "", "final": True},
    })

    # 流式路径 provider 不回传 usage，按字符数估算计入用量统计（与真实值分开累计）
    try:
        from app.utils.llm import _record_usage_estimated

        prompt_text = "".join(getattr(m, "content", "") or "" for m in messages)
        _record_usage_estimated(prompt_text, full_text)
    except Exception:
        pass

    return full_text

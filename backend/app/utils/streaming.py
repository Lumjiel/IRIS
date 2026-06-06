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


def set_token_queue(q: asyncio.Queue | None):
    _token_queue.set(q)


def get_token_queue() -> asyncio.Queue | None:
    return _token_queue.get()


async def llm_stream_tokens(
    messages: list[BaseMessage],
    model_type: str = "fast",
    node_name: str = "",
) -> str:
    """
    流式调用 LLM，token 逐个推入队列。
    生产者（线程）写入 channel，消费者（async）读取并推入 queue。
    """
    queue = get_token_queue()

    if queue is None:
        from app.utils.llm import llm_invoke
        response = llm_invoke(messages, model_type=model_type)
        return response.content or ""

    llm = get_llm(model_type=model_type)
    channel = asyncio.Queue()
    full_text = ""

    def _producer():
        """在线程中运行同步的 llm.stream()，token 推入 channel"""
        try:
            for chunk in llm.stream(messages):
                token = chunk.content or ""
                if token:
                    asyncio.run_coroutine_threadsafe(channel.put(token), loop)
        except Exception as e:
            log.warning(f"流式调用异常: {e}")
        finally:
            asyncio.run_coroutine_threadsafe(channel.put(None), loop)  # 结束标记

    loop = asyncio.get_event_loop()
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

    return full_text

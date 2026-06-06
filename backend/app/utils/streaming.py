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

# 每个请求的 token 队列
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
    返回完整响应文本。
    无队列时降级为非流式调用。
    """
    queue = get_token_queue()

    if queue is None:
        from app.utils.llm import llm_invoke
        response = llm_invoke(messages, model_type=model_type)
        return response.content or ""

    llm = get_llm(model_type=model_type)
    full_text = ""

    try:
        for chunk in llm.stream(messages):
            token = chunk.content or ""
            if token:
                full_text += token
                await queue.put({
                    "step": f"{node_name}_token",
                    "data": {"token": token},
                })
    except Exception as e:
        log.warning(f"流式调用失败 ({node_name})，降级为普通调用: {e}")
        from app.utils.llm import llm_invoke
        response = llm_invoke(messages, model_type=model_type)
        full_text = response.content or ""
        await queue.put({
            "step": f"{node_name}_token",
            "data": {"token": full_text, "final": True},
        })

    # 发送流式结束标记
    await queue.put({
        "step": f"{node_name}_token",
        "data": {"token": "", "final": True},
    })

    return full_text

"""streaming.py 单测：队列注册表 / 节点事件 / 同步降级 / 流式生产者 / 额度降级。"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.utils import streaming


def _msg(content):
    m = MagicMock()
    m.content = content
    return m


class TestQueueRegistry:
    def test_default_none(self):
        assert streaming.get_token_queue() is None
        assert streaming.get_node_event_queue() is None

    def test_set_and_get(self):
        q = asyncio.Queue()
        streaming.set_token_queue(q)
        assert streaming.get_token_queue() is q
        streaming.set_token_queue(None)
        assert streaming.get_token_queue() is None

    def test_register_unregister_thread_queues(self):
        tq, nq = asyncio.Queue(), asyncio.Queue()
        streaming.register_queues("t1", tq, nq)
        got = streaming.get_queues_by_thread("t1")
        assert got == {"token": tq, "node": nq}
        streaming.unregister_queues("t1")
        assert streaming.get_queues_by_thread("t1") is None

    def test_unregister_unknown_is_noop(self):
        streaming.unregister_queues("nonexistent-thread")

    def test_emit_node_event_with_queue(self):
        q = asyncio.Queue()
        streaming.set_node_event_queue(q)
        streaming.emit_node_event("writer", "start")
        ev = q.get_nowait()
        assert ev == {"step": "writer", "status": "start"}
        streaming.emit_node_event("writer", "done", elapsed=1.234, data={"k": "v"})
        ev = q.get_nowait()
        assert ev["elapsed"] == 1.23
        assert ev["data"] == {"k": "v"}
        streaming.set_node_event_queue(None)

    def test_emit_node_event_without_queue_is_noop(self):
        streaming.emit_node_event("writer", "start")  # 不应抛异常


class TestLLMStreamTokens:
    async def test_sync_fallback_when_no_queue(self):
        with patch("app.utils.llm.llm_invoke") as mock_inv:
            mock_inv.return_value = _msg("同步结果")
            out = await streaming.llm_stream_tokens([_msg("q")], node="writer")
        assert out == "同步结果"

    async def test_sync_fallback_empty_content(self):
        with patch("app.utils.llm.llm_invoke") as mock_inv:
            mock_inv.return_value = _msg(None)
            out = await streaming.llm_stream_tokens([_msg("q")])
        assert out == ""

    async def test_stream_pushes_tokens_to_queue(self):
        sse_q = asyncio.Queue()
        streaming.set_token_queue(sse_q)
        try:
            llm = MagicMock()
            llm.stream.return_value = iter([_msg("你"), _msg(""), _msg("好")])
            with patch("app.utils.streaming.get_llm", return_value=llm):
                out = await streaming.llm_stream_tokens([_msg("q")], node_name="writer", node="writer")
            assert out == "你好"
            events = []
            while not sse_q.empty():
                events.append(sse_q.get_nowait())
            # 两个非空 token + 1 个 final
            tokens = [e for e in events if not e["data"].get("final")]
            finals = [e for e in events if e["data"].get("final")]
            assert [e["data"]["token"] for e in tokens] == ["你", "好"]
            assert all(e["step"] == "writer_token" for e in events)
            assert len(finals) == 1 and finals[0]["data"]["token"] == ""
        finally:
            streaming.set_token_queue(None)

    async def test_quota_error_triggers_fallback_stream(self):
        sse_q = asyncio.Queue()
        streaming.set_token_queue(sse_q)
        try:
            bad_llm = MagicMock()
            bad_llm.stream.side_effect = RuntimeError("403 FreeTierOnly")
            good_llm = MagicMock()
            good_llm.stream.return_value = iter([_msg("备用")])
            with patch("app.utils.streaming.get_llm", side_effect=[bad_llm, good_llm]), \
                 patch("app.utils.llm.is_quota_error", return_value=True), \
                 patch("app.utils.llm.mark_primary_exhausted") as mock_mark:
                out = await streaming.llm_stream_tokens([_msg("q")], node="writer")
            assert out == "备用"
            mock_mark.assert_called_once()
        finally:
            streaming.set_token_queue(None)

    async def test_non_quota_error_ends_stream_gracefully(self):
        sse_q = asyncio.Queue()
        streaming.set_token_queue(sse_q)
        try:
            llm = MagicMock()
            llm.stream.side_effect = ValueError("boom")
            with patch("app.utils.streaming.get_llm", return_value=llm), \
                 patch("app.utils.llm.is_quota_error", return_value=False):
                out = await streaming.llm_stream_tokens([_msg("q")], node_name="writer")
            assert out == ""
            # 仍应发出 final 标记，消费者不挂死
            events = []
            while not sse_q.empty():
                events.append(sse_q.get_nowait())
            assert any(e["data"].get("final") for e in events)
        finally:
            streaming.set_token_queue(None)

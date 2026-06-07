"""llm.py 工厂和降级逻辑测试。"""
import pytest
from unittest.mock import patch, MagicMock
import time


class TestIsExhausted:
    """_is_exhausted 逻辑测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import app.utils.llm as llm_mod
        llm_mod._primary_exhausted = False
        llm_mod._primary_exhausted_at = 0

    def test_not_exhausted(self):
        from app.utils.llm import _is_exhausted
        assert _is_exhausted() is False

    def test_exhausted_within_ttl(self):
        import app.utils.llm as llm_mod
        from app.utils.llm import _is_exhausted
        llm_mod._primary_exhausted = True
        llm_mod._primary_exhausted_at = time.time()
        assert _is_exhausted() is True

    def test_exhausted_ttl_expired(self):
        import app.utils.llm as llm_mod
        from app.utils.llm import _is_exhausted
        llm_mod._primary_exhausted = True
        llm_mod._primary_exhausted_at = time.time() - 400  # 超过 300s TTL
        assert _is_exhausted() is False
        assert llm_mod._primary_exhausted is False  # TTL 过期后自动重置


class TestGetLlm:
    """get_llm 工厂函数测试。"""

    def setup_method(self):
        import app.utils.llm as llm_mod
        llm_mod._primary_exhausted = False
        llm_mod._primary_exhausted_at = 0

    @patch("app.utils.llm.ChatOpenAI")
    def test_fast_model_temperature(self, mock_chat):
        from app.utils.llm import get_llm
        get_llm("fast")
        call_kwargs = mock_chat.call_args
        assert call_kwargs.kwargs["temperature"] == 0.7

    @patch("app.utils.llm.ChatOpenAI")
    def test_smart_model_temperature(self, mock_chat):
        from app.utils.llm import get_llm
        get_llm("smart")
        call_kwargs = mock_chat.call_args
        assert call_kwargs.kwargs["temperature"] == 0

    @patch("app.utils.llm.ChatOpenAI")
    def test_exhausted_uses_fallback(self, mock_chat):
        import app.utils.llm as llm_mod
        from app.utils.llm import get_llm
        llm_mod._primary_exhausted = True
        llm_mod._primary_exhausted_at = time.time()
        get_llm("fast")
        call_kwargs = mock_chat.call_args
        assert call_kwargs.kwargs["model"] == llm_mod.FALLBACK_MODEL


class TestLlmInvoke:
    """llm_invoke 降级逻辑测试。"""

    def setup_method(self):
        import app.utils.llm as llm_mod
        llm_mod._primary_exhausted = False
        llm_mod._primary_exhausted_at = 0

    @patch("app.utils.llm.ChatOpenAI")
    def test_primary_success(self, mock_chat_cls):
        from app.utils.llm import llm_invoke
        from langchain_core.messages import HumanMessage
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="hello")
        mock_chat_cls.return_value = mock_llm
        result = llm_invoke([HumanMessage(content="test")], model_type="fast")
        assert result.content == "hello"

    @patch("app.utils.llm.ChatOpenAI")
    def test_quota_error_sets_exhaustion_and_falls_back(self, mock_chat_cls):
        import app.utils.llm as llm_mod
        from app.utils.llm import llm_invoke
        from langchain_core.messages import HumanMessage
        primary_llm = MagicMock()
        primary_llm.invoke.side_effect = Exception("quota exceeded")
        fallback_llm = MagicMock()
        fallback_llm.invoke.return_value = MagicMock(content="fallback result")

        call_count = [0]
        def chat_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return primary_llm
            return fallback_llm

        mock_chat_cls.side_effect = chat_side_effect
        result = llm_invoke([HumanMessage(content="test")], model_type="fast")
        assert result.content == "fallback result"
        assert llm_mod._primary_exhausted is True

    @patch("app.utils.llm.ChatOpenAI")
    def test_both_fail_raises(self, mock_chat_cls):
        from app.utils.llm import llm_invoke
        from langchain_core.messages import HumanMessage
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("error")
        mock_chat_cls.return_value = mock_llm
        with pytest.raises(Exception):
            llm_invoke([HumanMessage(content="test")], model_type="fast")

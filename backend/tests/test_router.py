"""router.py 节点测试。"""
import pytest
from unittest.mock import patch, MagicMock


class TestLooksLikeRefine:
    """looks_like_refine 纯函数测试。"""

    def test_empty_string(self):
        from app.graph.nodes.router import looks_like_refine
        assert looks_like_refine("") is False

    def test_whitespace_only(self):
        from app.graph.nodes.router import looks_like_refine
        assert looks_like_refine("   ") is False

    def test_no_trigger_keywords(self):
        from app.graph.nodes.router import looks_like_refine
        assert looks_like_refine("量子计算的最新进展") is False

    def test_refine_keyword_gai(self):
        from app.graph.nodes.router import looks_like_refine
        assert looks_like_refine("帮我改一下标题") is True

    def test_refine_keyword_runse(self):
        from app.graph.nodes.router import looks_like_refine
        assert looks_like_refine("润色这篇文章") is True

    def test_refine_keyword_kuoxie(self):
        from app.graph.nodes.router import looks_like_refine
        assert looks_like_refine("扩写第二段") is True

    def test_refine_keyword_chongxie(self):
        from app.graph.nodes.router import looks_like_refine
        assert looks_like_refine("重写结论部分") is True

    def test_partial_keyword_in_larger_word(self):
        from app.graph.nodes.router import looks_like_refine
        # "改" 嵌入在更大上下文中，仍然匹配
        assert looks_like_refine("请帮我修改一下格式") is True


class TestRouteQuery:
    """route_query 节点测试（mock LLM）。"""

    def test_no_report_always_planner(self, sample_state):
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = ""
        result = route_query(sample_state)
        assert result == "planner"

    def test_missing_report_always_planner(self, sample_state):
        from app.graph.nodes.router import route_query
        sample_state.pop("final_report", None)
        result = route_query(sample_state)
        assert result == "planner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_returns_refine(self, mock_llm, sample_state):
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = "这是一份报告"
        mock_llm.return_value = MagicMock(content="REFINE")
        result = route_query(sample_state)
        assert result == "refiner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_returns_new_topic(self, mock_llm, sample_state):
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = "这是一份报告"
        mock_llm.return_value = MagicMock(content="NEW_TOPIC")
        result = route_query(sample_state)
        assert result == "planner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_garbage_output_fallback_to_refine(self, mock_llm, sample_state):
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = "这是一份报告"
        sample_state["query"] = "帮我改一下标题"
        mock_llm.return_value = MagicMock(content="maybe")
        result = route_query(sample_state)
        assert result == "refiner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_garbage_output_fallback_to_planner(self, mock_llm, sample_state):
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = "这是一份报告"
        sample_state["query"] = "量子计算的最新进展"
        mock_llm.return_value = MagicMock(content="maybe")
        result = route_query(sample_state)
        assert result == "planner"


class TestIsVague:
    """_is_vague 模糊后续检测测试。"""

    def test_vague_you_juede(self):
        from app.graph.nodes.refiner import _is_vague
        assert _is_vague("你觉得呢？") is True

    def test_vague_ranhou_ne(self):
        from app.graph.nodes.refiner import _is_vague
        assert _is_vague("然后呢") is True

    def test_vague_short_continue(self):
        from app.graph.nodes.refiner import _is_vague
        assert _is_vague("继续") is True

    def test_not_vague_specific(self):
        from app.graph.nodes.refiner import _is_vague
        assert _is_vague("把第三段改详细一点，补充量子纠错的内容") is False

    def test_not_vague_long(self):
        from app.graph.nodes.refiner import _is_vague
        assert _is_vague("你觉得这个报告怎么样，有什么需要改进的地方吗？") is False

    def test_not_vague_new_topic(self):
        from app.graph.nodes.refiner import _is_vague
        assert _is_vague("帮我调研一下区块链技术") is False

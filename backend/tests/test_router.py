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


class TestRouteNode:
    """route_node 节点测试（mock LLM）：返回写回 state 的意图结果。"""

    def _patch_classify(self, payload):
        return patch(
            "app.graph.nodes.router._llm_classify",
            return_value=payload,
        )

    @patch("app.graph.nodes.router.route_skill", return_value="")
    @patch("app.graph.nodes.router._list_skills", return_value=[])
    def test_chat_intent(self, mock_skills, mock_skill, sample_state):
        from app.graph.nodes.router import route_node
        with self._patch_classify({"intent": "chat", "confidence": 0.9, "is_followup": False, "entities": [], "skill": ""}):
            result = route_node(sample_state)
        assert result["intent"] == "chat"
        assert result["active_skill"] == ""

    @patch("app.graph.nodes.router.route_skill", return_value="")
    @patch("app.graph.nodes.router._list_skills", return_value=[{"name": "content_research", "description": "公众号内容调研"}])
    def test_research_with_skill(self, mock_skills, mock_skill, sample_state):
        from app.graph.nodes.router import route_node
        with self._patch_classify({"intent": "research", "confidence": 0.95, "is_followup": False, "entities": ["量子计算"], "skill": "content_research"}):
            result = route_node(sample_state)
        assert result["intent"] == "research"
        assert result["active_skill"] == "content_research"

    @patch("app.graph.nodes.router.route_skill", return_value="")
    @patch("app.graph.nodes.router._list_skills", return_value=[])
    def test_refine_invalid_without_report(self, mock_skills, mock_skill, sample_state):
        """无报告时 LLM 说 refine 也应被强制为 research。"""
        from app.graph.nodes.router import route_node
        sample_state["final_report"] = ""
        with self._patch_classify({"intent": "refine", "confidence": 0.9, "is_followup": True, "entities": [], "skill": ""}):
            result = route_node(sample_state)
        assert result["intent"] == "research"

    @patch("app.graph.nodes.router.route_skill", return_value="")
    @patch("app.graph.nodes.router._list_skills", return_value=[])
    def test_llm_failure_fallback_research(self, mock_skills, mock_skill, sample_state):
        """LLM 分类失败（返回 None）时，带调研关键词回退到 research。"""
        from app.graph.nodes.router import route_node
        sample_state["query"] = "帮我调研量子计算"
        with patch("app.graph.nodes.router._llm_classify", return_value=None):
            result = route_node(sample_state)
        assert result["intent"] == "research"
        assert result["active_skill"] == ""  # bigram 未匹配到 skill

    @patch("app.graph.nodes.router.route_skill", return_value="")
    @patch("app.graph.nodes.router._list_skills", return_value=[])
    def test_clarify_when_vague(self, mock_skills, mock_skill, sample_state):
        """低置信度且无明显信号时回退到 clarify 而非默认 research。"""
        from app.graph.nodes.router import route_node
        sample_state["query"] = "xxx"
        with self._patch_classify({"intent": "clarify", "confidence": 0.2, "is_followup": False, "entities": [], "skill": ""}):
            result = route_node(sample_state)
        assert result["intent"] == "clarify"


class TestRouteIntent:
    """route_intent 条件边函数测试：返回意图键，由图映射到节点。"""

    def test_research_key(self, sample_state):
        from app.graph.nodes.router import route_intent
        sample_state["intent"] = "research"
        assert route_intent(sample_state) == "research"

    def test_chat_key(self, sample_state):
        from app.graph.nodes.router import route_intent
        sample_state["intent"] = "chat"
        assert route_intent(sample_state) == "chat"

    def test_clarify_key(self, sample_state):
        from app.graph.nodes.router import route_intent
        sample_state["intent"] = "clarify"
        assert route_intent(sample_state) == "clarify"

    def test_refine_key(self, sample_state):
        from app.graph.nodes.router import route_intent
        sample_state["intent"] = "refine"
        assert route_intent(sample_state) == "refine"

    def test_unknown_fallback_to_research(self, sample_state):
        from app.graph.nodes.router import route_intent
        sample_state["intent"] = "garbage"
        assert route_intent(sample_state) == "research"


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

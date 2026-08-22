"""router.py 节点测试。"""
from unittest.mock import patch, MagicMock

# conftest.py 会先于测试模块加载并注入外部依赖 mock，此处模块级导入安全
from app.graph.nodes.router import route_query


class TestLooksLikeRefine:
    """_looks_like_refine 纯函数测试。"""

    def test_empty_string(self):
        from app.graph.nodes.router import _looks_like_refine
        assert _looks_like_refine("") is False

    def test_whitespace_only(self):
        from app.graph.nodes.router import _looks_like_refine
        assert _looks_like_refine("   ") is False

    def test_no_trigger_keywords(self):
        from app.graph.nodes.router import _looks_like_refine
        assert _looks_like_refine("量子计算的最新进展") is False

    def test_refine_keyword_gai(self):
        from app.graph.nodes.router import _looks_like_refine
        assert _looks_like_refine("帮我改一下标题") is True

    def test_refine_keyword_runse(self):
        from app.graph.nodes.router import _looks_like_refine
        assert _looks_like_refine("润色这篇文章") is True

    def test_refine_keyword_kuoxie(self):
        from app.graph.nodes.router import _looks_like_refine
        assert _looks_like_refine("扩写第二段") is True

    def test_refine_keyword_chongxie(self):
        from app.graph.nodes.router import _looks_like_refine
        assert _looks_like_refine("重写结论部分") is True

    def test_partial_keyword_in_larger_word(self):
        from app.graph.nodes.router import _looks_like_refine
        # "改" 嵌入在更大上下文中（修改），仍然匹配
        assert _looks_like_refine("请帮我修改一下格式") is True


class TestLooksLikeResearch:
    """_looks_like_research 启发式测试。"""

    def test_stock_code_is_research(self):
        from app.graph.nodes.router import _looks_like_research
        assert _looks_like_research("600519 值得买吗") is True

    def test_research_verb(self):
        from app.graph.nodes.router import _looks_like_research
        assert _looks_like_research("分析一下宁德时代") is True

    def test_plain_question_not_research(self):
        from app.graph.nodes.router import _looks_like_research
        assert _looks_like_research("量子计算的最新进展") is False


class TestRouteQuery:
    """route_query 节点测试（mock LLM）。"""

    @patch("app.graph.nodes.router.llm_invoke")
    def test_no_report_research_query_planner(self, mock_llm, sample_state):
        """含研究动词且无报告 → 直接启发式命中 planner（不经 LLM）。"""
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = ""
        sample_state["query"] = "分析一下宁德时代"
        result = route_query(sample_state)
        assert result == "planner"
        mock_llm.assert_not_called()

    @patch("app.graph.nodes.router.llm_invoke")
    def test_no_report_llm_says_chat(self, mock_llm, sample_state):
        """非研究类问题且无报告 → LLM 分类 CHAT → chat 节点。"""
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = ""
        mock_llm.return_value = MagicMock(content="CHAT")
        result = route_query(sample_state)
        assert result == "chat"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_no_report_llm_says_research(self, mock_llm, sample_state):
        """无报告、启发式未命中、LLM 分类 RESEARCH → planner。"""
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = ""
        mock_llm.return_value = MagicMock(content="RESEARCH")
        result = route_query(sample_state)
        assert result == "planner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_returns_refine(self, mock_llm, sample_state):
        sample_state["final_report"] = "这是一份报告"
        mock_llm.return_value = MagicMock(content="REFINE")
        result = route_query(sample_state)
        assert result == "refiner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_returns_research(self, mock_llm, sample_state):
        """有报告时 LLM 分类 RESEARCH → 启动新研究。"""
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = "这是一份报告"
        mock_llm.return_value = MagicMock(content="RESEARCH")
        result = route_query(sample_state)
        assert result == "planner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_garbage_output_fallback_to_refine(self, mock_llm, sample_state):
        sample_state["final_report"] = "这是一份报告"
        sample_state["query"] = "帮我改一下标题"
        mock_llm.return_value = MagicMock(content="maybe")
        result = route_query(sample_state)
        # 非法输出兜底：有报告 + 命中修订触发词 → REFINE
        assert result == "refiner"

    @patch("app.graph.nodes.router.llm_invoke")
    def test_llm_garbage_output_fallback_to_chat(self, mock_llm, sample_state):
        """非法输出兜底：有报告 + 未命中修订触发词 → CHAT。"""
        from app.graph.nodes.router import route_query
        sample_state["final_report"] = "这是一份报告"
        sample_state["query"] = "量子计算的最新进展"
        mock_llm.return_value = MagicMock(content="maybe")
        result = route_query(sample_state)
        assert result == "chat"


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

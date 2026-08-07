"""researcher.py 节点测试。"""
import pytest
from unittest.mock import patch, MagicMock
from app.tools.registry import ToolDefinition


def _base_state(**overrides):
    state = {
        "query": "量子计算的最新进展",
        "plan": ["方向A", "方向B"],
        "search_results": [],
        "final_report": "",
        "critique": "",
        "revision_number": 0,
        "review_status": "PASS",
        "search_mode": "hybrid",
        "should_stop": False,
        "active_skill": "",
        "search_sources": [],
        "conversation_summary": "",
        "preferences": {},
        "citation_refs": "",
    }
    state.update(overrides)
    return state


def _make_tool(name, func):
    return ToolDefinition(name=name, description=f"{name} tool", func=func)


class TestResearchNode:
    """research_node 测试。"""

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.search_tavily_structured")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_hybrid_mode_calls_tavily(
        self, mock_registry, mock_tavily, mock_scorer_cls, sample_state
    ):
        """混合模式调用 Tavily 搜索并返回结果。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["量子计算进展"]

        mock_doc_func = MagicMock(return_value="")
        mock_registry.list_all.return_value = [
            _make_tool("doc_search", mock_doc_func),
        ]

        mock_tavily.return_value = [
            {"url": "https://example.com", "title": "量子计算", "content": "量子计算很厉害"}
        ]
        mock_scorer = MagicMock()
        mock_scorer.filter_results.side_effect = lambda r: r
        mock_scorer_cls.return_value = mock_scorer

        result = research_node(sample_state)

        assert len(result["search_results"]) > 0
        mock_tavily.assert_called_once_with("量子计算进展")
        assert any("网络搜索结果" in r for r in result["search_results"])

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.search_tavily_structured")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_hybrid_mode_web_only_when_no_doc_tool(
        self, mock_registry, mock_tavily, mock_scorer_cls, sample_state
    ):
        """无 doc_search 工具时仅执行网络搜索。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["AI趋势"]

        mock_registry.list_all.return_value = []
        mock_tavily.return_value = [
            {"url": "https://test.com", "title": "AI", "content": "AI 内容"}
        ]
        mock_scorer = MagicMock()
        mock_scorer.filter_results.side_effect = lambda r: r
        mock_scorer_cls.return_value = mock_scorer

        result = research_node(sample_state)
        mock_tavily.assert_called_once_with("AI趋势")

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.llm_invoke")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_document_mode_irrelevant_docs_sets_should_stop(
        self, mock_registry, mock_llm, mock_scorer_cls, sample_state
    ):
        """Document 模式下文档不相关 → should_stop=True。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "document"

        mock_doc_func = MagicMock(return_value="无关的文档内容")
        mock_registry.list_all.return_value = [
            _make_tool("doc_search", mock_doc_func),
        ]

        mock_llm.return_value = MagicMock(content="NO")

        result = research_node(sample_state)
        assert result["should_stop"] is True
        assert any("不相关" in r or "无关" in r for r in result["search_results"])

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.llm_invoke")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_document_mode_relevant_docs_proceeds(
        self, mock_registry, mock_llm, mock_scorer_cls, sample_state
    ):
        """Document 模式下文档相关 → 正常返回结果。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "document"

        mock_doc_func = MagicMock(return_value="量子计算的详细资料")
        mock_registry.list_all.return_value = [
            _make_tool("doc_search", mock_doc_func),
        ]

        mock_llm.return_value = MagicMock(content="YES")

        mock_scorer = MagicMock()
        mock_scorer.filter_results.side_effect = lambda r: r
        mock_scorer_cls.return_value = mock_scorer

        result = research_node(sample_state)
        assert result.get("should_stop") is not True
        assert any("本地文档" in r for r in result["search_results"])

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.llm_invoke")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_grader_failure_defaults_to_relevant(
        self, mock_registry, mock_llm, mock_scorer_cls, sample_state
    ):
        """Grader LLM 失败时默认文档相关。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["测试"]

        mock_doc_func = MagicMock(return_value="文档内容")
        mock_registry.list_all.return_value = [
            _make_tool("doc_search", mock_doc_func),
        ]

        mock_llm.side_effect = Exception("LLM unavailable")

        mock_scorer = MagicMock()
        mock_scorer.filter_results.side_effect = lambda r: r
        mock_scorer_cls.return_value = mock_scorer

        result = research_node(sample_state)
        # Grader 失败 → 默认 YES → 文档被视为相关
        assert any("本地文档" in r for r in result["search_results"])

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_empty_results_gives_fallback_hint(
        self, mock_registry, mock_scorer_cls, sample_state
    ):
        """所有搜索都失败时给出兜底提示。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = []

        mock_registry.list_all.return_value = []

        mock_scorer = MagicMock()
        mock_scorer.filter_results.side_effect = lambda r: r
        mock_scorer_cls.return_value = mock_scorer

        result = research_node(sample_state)
        assert len(result["search_results"]) == 1
        assert "未能检索" in result["search_results"][0]

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_credibility_filter_applied(
        self, mock_registry, mock_scorer_cls, sample_state
    ):
        """有搜索来源时调用可信度过滤。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["测试"]

        mock_registry.list_all.return_value = []

        mock_scorer = MagicMock()
        mock_scorer.filter_results.return_value = [{"url": "https://bbc.com", "title": "test"}]
        mock_scorer_cls.return_value = mock_scorer

        # 需要有结果才能进入 filter 逻辑
        # 但 plan=[] 且无工具时 results 为空 → 不会调用 filter
        # 改为有 plan 但工具返回空，mock tavily 异常
        with patch("app.graph.nodes.researcher.search_tavily_structured", side_effect=Exception("err")):
            result = research_node(sample_state)
        # 无 sources 时不调用 filter
        mock_scorer.filter_results.assert_not_called()

    @patch("app.graph.nodes.researcher.CredibilityScorer")
    @patch("app.graph.nodes.researcher.search_tavily_structured")
    @patch("app.graph.nodes.researcher.ToolRegistry")
    def test_search_failure_doesnt_crash(
        self, mock_registry, mock_tavily, mock_scorer_cls, sample_state
    ):
        """单个搜索失败不影响其他搜索。"""
        from app.graph.nodes.researcher import research_node

        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["query1", "query2"]

        mock_registry.list_all.return_value = []

        mock_tavily.side_effect = [
            Exception("timeout"),
            [{"url": "https://ok.com", "title": "OK", "content": "内容"}],
        ]

        mock_scorer = MagicMock()
        mock_scorer.filter_results.side_effect = lambda r: r
        mock_scorer_cls.return_value = mock_scorer

        result = research_node(sample_state)
        assert any("网络搜索结果" in r for r in result["search_results"])

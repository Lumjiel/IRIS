"""researcher.py 节点测试。"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


class TestResearchNode:
    """research_node 节点测试。"""

    @patch("app.graph.nodes.researcher.search_tavily")
    @patch("app.graph.nodes.researcher.get_retriever")
    def test_hybrid_mode_no_docs_does_web_search(self, mock_retriever, mock_search, sample_state):
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["量子计算进展"]
        mock_retriever.return_value = None  # 无知识库
        mock_search.return_value = "搜索结果内容"
        result = research_node(sample_state)
        assert len(result["search_results"]) > 0
        mock_search.assert_called_once()

    @patch("app.graph.nodes.researcher.search_tavily")
    @patch("app.graph.nodes.researcher.get_retriever")
    def test_hybrid_mode_with_relevant_docs(self, mock_retriever, mock_search, sample_state):
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["量子计算进展"]
        mock_doc = Document(page_content="量子计算是下一代计算技术")
        mock_retriever.return_value = MagicMock()
        mock_retriever.return_value.invoke.return_value = [mock_doc]
        mock_search.return_value = "搜索结果"
        with patch("app.graph.nodes.researcher.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="YES")
            result = research_node(sample_state)
        assert any("本地文档" in r for r in result["search_results"])
        mock_search.assert_called_once()

    @patch("app.graph.nodes.researcher.get_retriever")
    def test_document_mode_irrelevant_docs_sets_should_stop(self, mock_retriever, sample_state):
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "document"
        mock_doc = Document(page_content="完全不相关的内容")
        mock_retriever.return_value = MagicMock()
        mock_retriever.return_value.invoke.return_value = [mock_doc]
        with patch("app.graph.nodes.researcher.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="NO")
            result = research_node(sample_state)
        assert result["should_stop"] is True

    @patch("app.graph.nodes.researcher.get_retriever")
    def test_document_mode_relevant_docs_proceeds(self, mock_retriever, sample_state):
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "document"
        mock_doc = Document(page_content="量子计算的最新进展和应用")
        mock_retriever.return_value = MagicMock()
        mock_retriever.return_value.invoke.return_value = [mock_doc]
        with patch("app.graph.nodes.researcher.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="YES")
            result = research_node(sample_state)
        assert "should_stop" not in result or result.get("should_stop") is not True

    @patch("app.graph.nodes.researcher.search_tavily")
    @patch("app.graph.nodes.researcher.get_retriever")
    def test_all_searches_fail_gives_fallback提示(self, mock_retriever, mock_search, sample_state):
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["量子计算"]
        mock_retriever.return_value = None
        mock_search.side_effect = Exception("Tavily error")
        result = research_node(sample_state)
        assert len(result["search_results"]) == 1
        assert "未能检索" in result["search_results"][0]

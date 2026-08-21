"""researcher.py 节点测试。

researcher 现在只负责本地 RAG 检索 + 文档相关性审计。
网络搜索已迁移至 search_agent（Function Calling）。
"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


class TestResearchNode:
    """research_node 节点测试。"""

    @patch("app.graph.nodes.researcher.get_retriever")
    def test_hybrid_mode_no_docs_no_web_search(self, mock_retriever, sample_state):
        """researcher 不再直接调用 web 搜索，只负责 RAG"""
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["量子计算进展"]
        mock_retriever.return_value = None  # 无知识库
        result = research_node(sample_state)
        # researcher 不再做 web 搜索，search_results 包含提示
        assert "search_results" in result

    @patch("app.graph.nodes.researcher.get_retriever")
    def test_hybrid_mode_with_relevant_docs(self, mock_retriever, sample_state):
        """RAG 检索 + 文档相关性审计"""
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["量子计算进展"]
        mock_doc = Document(page_content="量子计算是下一代计算技术")
        mock_retriever.return_value = MagicMock()
        mock_retriever.return_value.invoke.return_value = [mock_doc]
        with patch("app.graph.nodes.researcher.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="YES")
            result = research_node(sample_state)
        assert any("本地文档" in r for r in result["search_results"])

    @patch("app.graph.nodes.researcher.get_retriever")
    def test_document_mode_irrelevant_docs_sets_should_stop(self, mock_retriever, sample_state):
        """文档模式 + 不相关文档 → should_stop"""
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
        """文档模式 + 相关文档 → 继续"""
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "document"
        mock_doc = Document(page_content="量子计算的最新进展和应用")
        mock_retriever.return_value = MagicMock()
        mock_retriever.return_value.invoke.return_value = [mock_doc]
        with patch("app.graph.nodes.researcher.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="YES")
            result = research_node(sample_state)
        assert "should_stop" not in result or result.get("should_stop") is not True

    @patch("app.graph.nodes.researcher.get_retriever")
    def test_no_retriever_gives_fallback_message(self, mock_retriever, sample_state):
        """无知识库时给出提示"""
        from app.graph.nodes.researcher import research_node
        sample_state["search_mode"] = "hybrid"
        sample_state["plan"] = ["量子计算"]
        mock_retriever.return_value = None
        result = research_node(sample_state)
        assert len(result["search_results"]) == 1
        assert "本地资料" in result["search_results"][0]

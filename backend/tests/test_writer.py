"""writer.py 节点测试。"""
import pytest
from unittest.mock import patch, MagicMock


def _base_state(**overrides):
    state = {
        "query": "量子计算的最新进展",
        "plan": ["方向A"],
        "search_results": ["### 搜索结果\n量子计算很厉害"],
        "final_report": "",
        "critique": "",
        "revision_number": 0,
        "review_status": "PASS",
        "search_mode": "hybrid",
        "should_stop": False,
        "active_skill": "",
        "search_sources": [{"url": "https://example.com", "title": "量子计算"}],
        "conversation_summary": "",
        "preferences": {},
        "citation_refs": "",
        "thread_id": "test-thread",
    }
    state.update(overrides)
    return state


class TestWriteNode:
    """write_node 测试。"""

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories")
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_generates_report(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract, sample_state
    ):
        """LLM 返回正常报告。"""
        from app.graph.nodes.writer import write_node

        mock_llm.return_value = MagicMock(content="## 量子计算报告\n详细内容")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = ""
        mock_citation_cls.return_value = mock_citation

        result = await write_node(sample_state)
        assert "量子计算报告" in result["final_report"]

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories")
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_empty_report_fallback(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract, sample_state
    ):
        """LLM 返回空报告时生成兜底内容。"""
        from app.graph.nodes.writer import write_node

        mock_llm.return_value = MagicMock(content="")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = ""
        mock_citation_cls.return_value = mock_citation

        result = await write_node(sample_state)
        assert "量子计算的最新进展" in result["final_report"]
        assert "暂时无法完整生成" in result["final_report"]

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories")
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_citation_appended(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract, sample_state
    ):
        """有搜索来源时追加引用标注。"""
        from app.graph.nodes.writer import write_node

        mock_llm.return_value = MagicMock(content="报告内容")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = "\n\n## 参考文献\n[1] 来源A"
        mock_citation_cls.return_value = mock_citation

        result = await write_node(sample_state)
        assert "参考文献" in result["final_report"]
        mock_citation.add_source_from_search_result.assert_called()

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories")
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_style_modifier_in_prompt(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract
    ):
        """用户偏好风格注入到 prompt。"""
        from app.graph.nodes.writer import write_node, STYLE_MODIFIERS

        state = _base_state(preferences={"style": "concise", "language": "zh"})
        mock_llm.return_value = MagicMock(content="简洁报告")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = ""
        mock_citation_cls.return_value = mock_citation

        await write_node(state)
        # 验证 prompt 包含了 concise 风格指令
        call_args = mock_llm.call_args[0][0]
        prompt_text = call_args[0].content
        assert STYLE_MODIFIERS["concise"] in prompt_text

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories")
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_english_language_modifier(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract
    ):
        """英文偏好注入 English 指令。"""
        from app.graph.nodes.writer import write_node, LANGUAGE_MODIFIERS

        state = _base_state(preferences={"style": "detailed", "language": "en"})
        mock_llm.return_value = MagicMock(content="Report content")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = ""
        mock_citation_cls.return_value = mock_citation

        await write_node(state)
        call_args = mock_llm.call_args[0][0]
        prompt_text = call_args[0].content
        assert LANGUAGE_MODIFIERS["en"] in prompt_text

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories")
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_critique_included_in_prompt(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract
    ):
        """有审查意见时注入 critique 到 prompt。"""
        from app.graph.nodes.writer import write_node

        state = _base_state(critique="内容不够详细")
        mock_llm.return_value = MagicMock(content="修订报告")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = ""
        mock_citation_cls.return_value = mock_citation

        await write_node(state)
        call_args = mock_llm.call_args[0][0]
        prompt_text = call_args[0].content
        assert "内容不够详细" in prompt_text
        assert "审查意见" in prompt_text or "未通过审查" in prompt_text

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories")
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_extract_memories_called(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract, sample_state
    ):
        """写完报告后调用记忆提取。"""
        from app.graph.nodes.writer import write_node

        mock_llm.return_value = MagicMock(content="报告内容")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = ""
        mock_citation_cls.return_value = mock_citation

        await write_node(sample_state)
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs["query"] == "量子计算的最新进展"

    @pytest.mark.asyncio
    @patch("app.graph.nodes.writer.extract_memories", side_effect=Exception("DB error"))
    @patch("app.graph.nodes.writer.CitationFormatter")
    @patch("app.graph.nodes.writer.get_token_queue", return_value=None)
    @patch("app.graph.nodes.writer.llm_invoke")
    @patch("app.graph.nodes.writer.build_conversation_context", return_value="[当前问题] test")
    async def test_extract_memories_failure_doesnt_crash(
        self, mock_ctx, mock_llm, mock_queue, mock_citation_cls, mock_extract, sample_state
    ):
        """记忆提取失败不影响主流程。"""
        from app.graph.nodes.writer import write_node

        mock_llm.return_value = MagicMock(content="报告内容")
        mock_citation = MagicMock()
        mock_citation.format_references.return_value = ""
        mock_citation_cls.return_value = mock_citation

        result = await write_node(sample_state)
        assert "报告内容" in result["final_report"]

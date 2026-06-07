"""reviewer.py 节点测试。"""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestCleanJsonText:
    """_clean_json_text 纯函数测试。"""

    def test_clean_json_passthrough(self):
        from app.graph.nodes.reviewer import _clean_json_text
        result = _clean_json_text('{"status": "PASS", "feedback": ""}')
        assert result == '{"status": "PASS", "feedback": ""}'

    def test_strips_markdown_fences(self):
        from app.graph.nodes.reviewer import _clean_json_text
        result = _clean_json_text('```json\n{"status": "PASS"}\n```')
        assert result == '{"status": "PASS"}'

    def test_extracts_json_from_surrounding_text(self):
        from app.graph.nodes.reviewer import _clean_json_text
        result = _clean_json_text('Here is the result: {"status": "FAIL", "feedback": "不够详细"} end')
        parsed = json.loads(result)
        assert parsed["status"] == "FAIL"

    def test_empty_string(self):
        from app.graph.nodes.reviewer import _clean_json_text
        result = _clean_json_text("")
        assert result == ""

    def test_none_input(self):
        from app.graph.nodes.reviewer import _clean_json_text
        result = _clean_json_text(None)
        assert result == ""

    def test_no_braces(self):
        from app.graph.nodes.reviewer import _clean_json_text
        result = _clean_json_text("no json here")
        assert result == "no json here"

    def test_multiple_braces_extracts_widest_span(self):
        from app.graph.nodes.reviewer import _clean_json_text
        # 函数行为：从第一个 { 到最后一个 }，多对象场景返回非合法 JSON
        result = _clean_json_text('prefix {"a": 1} middle {"b": 2} suffix')
        assert result == '{"a": 1} middle {"b": 2}'

    def test_single_json_object(self):
        from app.graph.nodes.reviewer import _clean_json_text
        result = _clean_json_text('text {"status": "PASS", "feedback": ""} end')
        parsed = json.loads(result)
        assert parsed["status"] == "PASS"


class TestReviewNode:
    """review_node 节点测试。"""

    def test_short_report_immediate_fail(self, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = "太短"
        result = review_node(sample_state)
        assert result["review_status"] == "FAIL"
        assert result["revision_number"] == 1

    def test_empty_report_immediate_fail(self, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = ""
        result = review_node(sample_state)
        assert result["review_status"] == "FAIL"

    @patch("app.graph.nodes.reviewer.llm_invoke")
    def test_pass_response(self, mock_llm, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = "这是一份足够长的报告，包含了详细的信息和分析。" * 3
        mock_llm.return_value = MagicMock(content='{"status": "PASS", "feedback": ""}')
        result = review_node(sample_state)
        assert result["review_status"] == "PASS"
        assert result["revision_number"] == 1

    @patch("app.graph.nodes.reviewer.llm_invoke")
    def test_fail_response(self, mock_llm, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = "这是一份足够长的报告，包含了详细的信息和分析。" * 3
        mock_llm.return_value = MagicMock(content='{"status": "FAIL", "feedback": "需要更多数据"}')
        result = review_node(sample_state)
        assert result["review_status"] == "FAIL"
        assert "需要更多数据" in result["critique"]

    @patch("app.graph.nodes.reviewer.llm_invoke")
    def test_non_json_then_valid_json_retry(self, mock_llm, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = "这是一份足够长的报告，包含了详细的信息和分析。" * 3
        # 第一次返回非 JSON，第二次返回有效 JSON
        mock_llm.side_effect = [
            MagicMock(content="I think the report is good"),
            MagicMock(content='{"status": "PASS", "feedback": ""}'),
        ]
        result = review_node(sample_state)
        assert result["review_status"] == "PASS"
        assert mock_llm.call_count == 2

    @patch("app.graph.nodes.reviewer.llm_invoke")
    def test_both_retries_fail_closes(self, mock_llm, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = "这是一份足够长的报告，包含了详细的信息和分析。" * 3
        mock_llm.side_effect = [
            MagicMock(content="garbage 1"),
            MagicMock(content="garbage 2"),
        ]
        result = review_node(sample_state)
        assert result["review_status"] == "FAIL"
        assert "审查器输出格式异常" in result["critique"]

    def test_revision_number_increments(self, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = ""
        sample_state["revision_number"] = 2
        result = review_node(sample_state)
        assert result["revision_number"] == 3

    @patch("app.graph.nodes.reviewer.llm_invoke")
    def test_revision_number_increments_on_llm_call(self, mock_llm, sample_state):
        from app.graph.nodes.reviewer import review_node
        sample_state["final_report"] = "这是一份足够长的报告，包含了详细的信息和分析。" * 3
        sample_state["revision_number"] = 1
        mock_llm.return_value = MagicMock(content='{"status": "PASS", "feedback": ""}')
        result = review_node(sample_state)
        assert result["revision_number"] == 2

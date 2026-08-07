"""ReAct 工具调用循环（tool_call / tool_execute）测试。"""
import pytest
from unittest.mock import patch, MagicMock

from app.tools.registry import ToolRegistry


def _state(**overrides):
    s = {
        "query": "帮我查一下",
        "tool_messages": [],
        "tool_iterations": 0,
        "tool_call_request": None,
        "active_skill": "",
        "final_report": "",
    }
    s.update(overrides)
    return s


class TestToolCallNode:
    """tool_call 决策节点。"""

    @patch("app.graph.nodes.tool_call.llm_invoke")
    def test_decides_to_call_tool(self, mock_llm):
        from app.graph.nodes.tool_call import tool_call_node
        mock_llm.return_value = MagicMock(
            content='{"action":"tool","tool":"web_search","arguments":{"query":"量子计算"}}'
        )
        result = tool_call_node(_state())
        assert result["tool_call_request"]["tool"] == "web_search"
        assert result["tool_call_request"]["arguments"]["query"] == "量子计算"
        assert result["tool_iterations"] == 1

    @patch("app.graph.nodes.tool_call.llm_invoke")
    def test_decides_to_answer(self, mock_llm):
        from app.graph.nodes.tool_call import tool_call_node
        mock_llm.return_value = MagicMock(content='{"action":"answer","answer":"这是最终回答"}')
        result = tool_call_node(_state())
        assert result["final_report"] == "这是最终回答"
        assert result["tool_call_request"] is None

    @patch("app.graph.nodes.tool_call.MAX_TOOL_ITERATIONS", 2)
    @patch("app.graph.nodes.tool_call.llm_invoke")
    def test_force_answer_at_max_iterations(self, mock_llm):
        from app.graph.nodes.tool_call import tool_call_node
        # LLM 想继续调工具，但已达最大迭代 -> 强制按 answer 处理（不再发工具请求）
        mock_llm.return_value = MagicMock(
            content='{"action":"tool","tool":"web_search","arguments":{"query":"x"}}'
        )
        result = tool_call_node(_state(tool_iterations=2))
        assert result["tool_call_request"] is None

    @patch("app.graph.nodes.tool_call.MAX_TOOL_ITERATIONS", 2)
    @patch("app.graph.nodes.tool_call.llm_invoke")
    def test_unknown_tool_returns_message(self, mock_llm):
        from app.graph.nodes.tool_call import tool_call_node
        mock_llm.return_value = MagicMock(
            content='{"action":"tool","tool":"nonexistent_tool","arguments":{"query":"x"}}'
        )
        result = tool_call_node(_state())
        # 工具不存在且模糊匹配失败 -> 直接返回错误信息，不再发请求
        assert result["tool_call_request"] is None
        assert "没有可用工具" in result["final_report"] or "抱歉" in result["final_report"]


class TestToolExecuteNode:
    """tool_execute 执行节点。"""

    def test_executes_tool_and_appends_result(self):
        from app.graph.nodes.tool_execute import tool_execute_node
        ToolRegistry.register(name="fake_tool", description="test")(lambda query="": f"result_for_{query}")
        state = _state(tool_call_request={"tool": "fake_tool", "arguments": {"query": "abc"}})
        result = tool_execute_node(state)
        assert len(result["tool_messages"]) == 1
        assert "abc" in result["tool_messages"][0]["content"]

    def test_handles_missing_tool(self):
        from app.graph.nodes.tool_execute import tool_execute_node
        state = _state(tool_call_request={"tool": "ghost", "arguments": {}})
        result = tool_execute_node(state)
        assert "不存在" in result["tool_messages"][0]["content"]

    def test_handles_empty_request(self):
        from app.graph.nodes.tool_execute import tool_execute_node
        result = tool_execute_node(_state(tool_call_request=None))
        assert result == {}
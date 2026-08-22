"""search_agent.py Function Calling 节点测试。

验证 LLM 驱动的工具调用链路：
1. agent 节点生成 tool_calls
2. ToolNode 执行工具
3. route_after_tools 提取结果
"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from app.graph.state import AgentState


def make_sample_state():
    return AgentState(
        query="分析复星医药 600196",
        plan=["复星医药 2025 年报", "复星医药 行业竞争格局"],
        messages=[],
        search_results=[],
        final_report="",
        critique="",
        revision_number=0,
        review_status="PASS",
        search_mode="hybrid",
        should_stop=False,
        conversation_summary="",
        error_code="",
        degraded=False,
        failed_tools=[],
        early_stop=False,
        should_continue=True,
        report_history=[],
        tool_status={},
        preferences={},
        financial_data={},
        data_sources=[],
        pending_stock_code="600196",
    )


class TestSearchAgentNode:
    """search_agent_node 测试。"""

    @patch("app.graph.nodes.search_agent.get_llm")
    def test_agent_calls_search_tool(self, mock_get_llm):
        """LLM 返回 tool_calls → agent 正确生成消息"""
        mock_llm = MagicMock()
        mock_response = AIMessage(
            content="我来搜索复星医药的信息",
            tool_calls=[{
                "id": "call_1",
                "name": "search_web",
                "args": {"query": "复星医药 2025 年报"}
            }]
        )
        mock_llm.bind_tools.return_value.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from app.graph.nodes.search_agent import search_agent_node
        state = make_sample_state()
        result = search_agent_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert len(result["messages"][0].tool_calls) == 1
        assert result["messages"][0].tool_calls[0]["name"] == "search_web"

    @patch("app.graph.nodes.search_agent.get_llm")
    def test_agent_no_tool_calls(self, mock_get_llm):
        """LLM 不调用工具 → agent 返回纯文本消息"""
        mock_llm = MagicMock()
        mock_response = AIMessage(
            content="根据已有信息，复星医药是一家...",
            tool_calls=[]
        )
        mock_llm.bind_tools.return_value.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from app.graph.nodes.search_agent import search_agent_node
        state = make_sample_state()
        result = search_agent_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert result["messages"][0].tool_calls == []

    @patch("app.graph.nodes.search_agent.get_llm")
    def test_replays_message_history(self, mock_get_llm):
        """多轮搜索时必须重放历史（含 ToolMessage），LLM 才能基于已搜结果决策"""
        mock_llm = MagicMock()
        mock_response = AIMessage(content="信息已充分", tool_calls=[])
        mock_llm.bind_tools.return_value.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from app.graph.nodes.search_agent import search_agent_node
        state = make_sample_state()
        history = [
            AIMessage(
                content="我来搜索",
                tool_calls=[{"id": "call_1", "name": "search_web", "args": {"query": "复星医药 2025 年报"}}],
            ),
            ToolMessage(content="2025 年报要点……", tool_call_id="call_1", name="search_web"),
        ]
        state["messages"] = list(history)
        state["search_iteration"] = 1

        search_agent_node(state)

        # 校验传给 LLM 的消息包含完整历史重放
        invoked = mock_llm.bind_tools.return_value.invoke.call_args[0][0]
        assert len(invoked) == 2 + len(history)  # System + Human + 历史
        assert any(isinstance(m, ToolMessage) for m in invoked), "历史中的工具结果必须出现在 LLM 输入中"


class TestSearchToolNode:
    """search_tool_node 测试。"""

    @patch("app.tools.search_tools._search_tavily")
    def test_executes_tool_calls(self, mock_tavily):
        """ToolNode 执行 LLM 的工具调用"""
        from app.graph.nodes.search_agent import search_tool_node
        mock_tavily.return_value = "搜索结果内容"

        state = make_sample_state()
        state["messages"] = [
            AIMessage(
                content="我来搜索",
                tool_calls=[{"id": "call_1", "name": "search_web", "args": {"query": "复星医药"}}]
            )
        ]

        result = search_tool_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], ToolMessage)
        assert result["messages"][0].tool_call_id == "call_1"
        assert "搜索结果内容" in result["messages"][0].content
        mock_tavily.assert_called_once_with("复星医药")

    def test_no_tool_calls_returns_empty(self):
        """无工具调用 → 空结果"""
        from app.graph.nodes.search_agent import search_tool_node
        state = make_sample_state()
        state["messages"] = [AIMessage(content="纯文本", tool_calls=[])]
        result = search_tool_node(state)
        assert result["messages"] == []


class TestRouteAfterTools:
    """route_after_tools 测试。"""

    def test_extract_results_from_tool_messages(self):
        """从 ToolMessage 提取搜索结果"""
        from app.graph.nodes.search_agent import route_after_tools

        state = make_sample_state()
        state["messages"] = [
            HumanMessage(content="用户问题"),
            AIMessage(content="我来搜索", tool_calls=[{"id": "call_1", "name": "search_web", "args": {"query": "test"}}]),
            ToolMessage(content="搜索结果内容", tool_call_id="call_1", name="search_web"),
        ]

        result = route_after_tools(state)

        assert "search_results" in result
        assert len(result["search_results"]) == 1
        assert "搜索结果内容" in result["search_results"][0]

    def test_no_tool_messages_gives_empty_results(self):
        """无 ToolMessage → 空结果"""
        from app.graph.nodes.search_agent import route_after_tools

        state = make_sample_state()
        state["messages"] = [
            HumanMessage(content="用户问题"),
            AIMessage(content="纯文本回复", tool_calls=[]),
        ]

        result = route_after_tools(state)

        assert "search_results" in result
        assert len(result["search_results"]) == 0


class TestSearchWebTool:
    """search_web 工具测试。"""

    @patch("app.tools.search_tools._search_tavily")
    def test_search_web_success(self, mock_tavily):
        """search_web 调用成功"""
        from app.tools.search_tools import search_web
        mock_tavily.return_value = "搜索结果内容"

        result = search_web.invoke({"query": "复星医药"})

        mock_tavily.assert_called_once_with("复星医药")
        assert result == "搜索结果内容"

    @patch("app.tools.search_tools._search_tavily")
    def test_search_web_failure_returns_error(self, mock_tavily):
        """search_web 调用失败不抛异常"""
        from app.tools.search_tools import search_web
        mock_tavily.side_effect = Exception("API error")

        result = search_web.invoke({"query": "复星医药"})

        assert "搜索失败" in result

"""graph.py 路由函数测试。"""
from typing import Any
from unittest.mock import patch

from app.error_types import ErrorCode
from app.graph.graph import route_after_research, should_continue

# langgraph 的 END 哨兵是文档化的稳定公开值（'__end__'），直接引用以解耦 lint 环境对 namespace package 的解析问题
END = "__end__"

def _partial_state(**kwargs: Any) -> Any:
    """构造部分 AgentState。LangGraph 运行时即以部分字典在节点间传递状态，
    路由函数也只读取关心的键，因此测试中用部分字典是符合运行时语义的。"""
    return kwargs


class TestRouteAfterResearch:
    """route_after_research 纯函数测试。"""

    def test_should_stop_returns_end(self):
        result = route_after_research(_partial_state(should_stop=True))
        assert result == END

    def test_should_not_stop_returns_search_agent(self):
        """researcher 正常结束后进入 search_agent（Function Calling 网络调研）。"""
        result = route_after_research(_partial_state(should_stop=False))
        assert result == "search_agent"

    def test_missing_should_stop_returns_search_agent(self):
        result = route_after_research(_partial_state())
        assert result == "search_agent"


class TestShouldContinue:
    """should_continue 纯函数测试。"""

    @patch("app.graph.graph.MAX_ITERATIONS", 3)
    def test_max_iterations_returns_end(self):
        result = should_continue(_partial_state(revision_number=3))
        assert result == END

    @patch("app.graph.graph.MAX_ITERATIONS", 3)
    def test_over_max_iterations_returns_end(self):
        result = should_continue(_partial_state(revision_number=5))
        assert result == END

    @patch("app.graph.graph.MAX_ITERATIONS", 3)
    def test_below_max_and_pass_returns_end(self):
        result = should_continue(_partial_state(revision_number=1, review_status="PASS"))
        assert result == END

    @patch("app.graph.graph.MAX_ITERATIONS", 3)
    def test_below_max_and_fail_returns_planner(self):
        result = should_continue(
            _partial_state(revision_number=1, review_status="FAIL", critique="不够详细")
        )
        assert result == "planner"

    @patch("app.graph.graph.MAX_ITERATIONS", 3)
    def test_error_code_severe_returns_end(self):
        """严重错误码 → 终止循环。"""
        result = should_continue(
            _partial_state(error_code=ErrorCode.VALIDATION_FAILED.value, revision_number=0)
        )
        assert result == END

    @patch("app.graph.graph.MAX_ITERATIONS", 3)
    def test_degraded_error_continues_to_planner(self):
        """降级错误码 → 标记 degraded 并继续规划。"""
        state = _partial_state(
            error_code=ErrorCode.DEGRADED_SEARCH.value, revision_number=0
        )
        result = should_continue(state)
        assert result == "planner"
        assert state.get("degraded") is True

    @patch("app.graph.graph.MAX_ITERATIONS", 3)
    def test_missing_fields_defaults_to_end(self):
        result = should_continue(_partial_state())
        assert result == END

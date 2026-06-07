"""graph.py 路由函数测试。"""
import pytest
from unittest.mock import patch


class TestRouteAfterResearch:
    """route_after_research 纯函数测试。"""

    def test_should_stop_returns_end(self):
        from app.graph.graph import route_after_research
        from langgraph.graph import END
        result = route_after_research({"should_stop": True})
        assert result == END

    def test_should_not_stop_returns_writer(self):
        from app.graph.graph import route_after_research
        result = route_after_research({"should_stop": False})
        assert result == "writer"

    def test_missing_should_stop_returns_writer(self):
        from app.graph.graph import route_after_research
        result = route_after_research({})
        assert result == "writer"


class TestShouldContinue:
    """should_continue 纯函数测试。"""

    @patch("app.graph.graph.MAX_REVISIONS", 3)
    def test_max_revisions_returns_end(self):
        from app.graph.graph import should_continue
        from langgraph.graph import END
        result = should_continue({"revision_number": 3})
        assert result == END

    @patch("app.graph.graph.MAX_REVISIONS", 3)
    def test_over_max_revisions_returns_end(self):
        from app.graph.graph import should_continue
        from langgraph.graph import END
        result = should_continue({"revision_number": 5})
        assert result == END

    @patch("app.graph.graph.MAX_REVISIONS", 3)
    def test_below_max_and_pass_returns_end(self):
        from app.graph.graph import should_continue
        from langgraph.graph import END
        result = should_continue({"revision_number": 1, "review_status": "PASS"})
        assert result == END

    @patch("app.graph.graph.MAX_REVISIONS", 3)
    def test_below_max_and_fail_returns_planner(self):
        from app.graph.graph import should_continue
        result = should_continue({"revision_number": 1, "review_status": "FAIL", "critique": "不够详细"})
        assert result == "planner"

    @patch("app.graph.graph.MAX_REVISIONS", 3)
    def test_missing_fields_defaults_to_end(self):
        from app.graph.graph import should_continue
        from langgraph.graph import END
        result = should_continue({})
        assert result == END

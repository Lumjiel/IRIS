"""Human-in-the-loop（apply_hitl / hitl_gate / router 路由）测试。"""
from unittest.mock import patch, MagicMock


def _state(**overrides):
    s = {
        "query": "量子计算",
        "hitl_choice": "",
        "pending_hitl": False,
        "hitl_mode": "",
        "active_skill": "",
        "critique": "内容不够详细",
        "review_status": "FAIL",
        "revision_number": 1,
    }
    s.update(overrides)
    return s


class TestApplyHitl:
    def test_retry_routes_to_planner(self):
        from app.graph.nodes.apply_hitl import apply_hitl_node
        result = apply_hitl_node(_state(hitl_choice="重试"))
        assert result["hitl_mode"] == "planner"
        assert result["pending_hitl"] is False

    def test_use_existing_finalizes(self):
        from app.graph.nodes.apply_hitl import apply_hitl_node
        result = apply_hitl_node(_state(hitl_choice="就用当前内容定稿"))
        assert result["hitl_mode"] == "end"
        assert result["review_status"] == "PASS"

    def test_redirect_substring(self):
        from app.graph.nodes.apply_hitl import apply_hitl_node
        result = apply_hitl_node(_state(hitl_choice="换个方向：聊聊硬件"))
        assert result["hitl_mode"] == "planner"

    def test_unknown_defaults_to_retry(self):
        from app.graph.nodes.apply_hitl import apply_hitl_node
        result = apply_hitl_node(_state(hitl_choice="随便"))
        assert result["hitl_mode"] == "planner"


class TestHitlGate:
    @patch("app.graph.nodes.hitl_gate.get_token_queue", return_value=None)
    def test_sets_pending_and_question(self, mock_queue):
        from app.graph.nodes.hitl_gate import hitl_gate_node
        result = hitl_gate_node(_state())
        assert result["pending_hitl"] is True
        assert result["hitl_question"]
        assert "审查意见" in result["hitl_question"]


class TestRouterHitl:
    def test_hitl_choice_routes_to_apply_hitl(self, sample_state):
        from app.graph.nodes.router import route_node
        sample_state["hitl_choice"] = "重试"
        result = route_node(sample_state)
        assert result["intent"] == "apply_hitl"

    def test_route_intent_apply_hitl(self, sample_state):
        from app.graph.nodes.router import route_intent
        sample_state["intent"] = "apply_hitl"
        assert route_intent(sample_state) == "apply_hitl"
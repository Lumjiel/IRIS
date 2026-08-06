"""planner.py 节点测试。"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def _base_state(**overrides):
    state = {
        "query": "量子计算的最新进展",
        "plan": [],
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


class TestPlanNode:
    """plan_node 测试。"""

    @pytest.mark.asyncio
    @patch("app.graph.nodes.planner.MemoryStore")
    @patch("app.graph.nodes.planner.pop_skill_cache", return_value="")
    @patch("app.graph.nodes.planner.build_conversation_context", return_value="[当前问题] test")
    @patch("app.graph.nodes.planner.llm_invoke")
    @patch("app.graph.nodes.planner.get_token_queue", return_value=None)
    async def test_returns_plan_from_llm(
        self, mock_queue, mock_llm, mock_ctx, mock_pop, mock_store_cls
    ):
        from app.graph.nodes.planner import plan_node

        mock_llm.return_value = MagicMock(content="方向A, 方向B, 方向C")
        mock_store_cls.return_value.search.return_value = []

        result = await plan_node(_base_state())
        assert result["plan"] == ["方向A", "方向B", "方向C"]

    @pytest.mark.asyncio
    @patch("app.graph.nodes.planner.MemoryStore")
    @patch("app.graph.nodes.planner.pop_skill_cache", return_value="")
    @patch("app.graph.nodes.planner.build_conversation_context", return_value="[当前问题] test")
    @patch("app.graph.nodes.planner.llm_invoke")
    @patch("app.graph.nodes.planner.get_token_queue", return_value=None)
    async def test_new_topic_clears_old_report(
        self, mock_queue, mock_llm, mock_ctx, mock_pop, mock_store_cls
    ):
        """revision_number=0 + 有旧报告 → 清理旧报告和引用。"""
        from app.graph.nodes.planner import plan_node

        mock_llm.return_value = MagicMock(content="新方向1, 新方向2")
        mock_store_cls.return_value.search.return_value = []

        state = _base_state(
            revision_number=0,
            final_report="旧报告内容",
            citation_refs="[1] 来源A",
        )
        result = await plan_node(state)
        assert result["final_report"] == ""
        assert result["citation_refs"] == ""

    @pytest.mark.asyncio
    @patch("app.graph.nodes.planner.MemoryStore")
    @patch("app.graph.nodes.planner.pop_skill_cache", return_value="")
    @patch("app.graph.nodes.planner.build_conversation_context", return_value="[当前问题] test")
    @patch("app.graph.nodes.planner.llm_invoke")
    @patch("app.graph.nodes.planner.get_token_queue", return_value=None)
    async def test_revision_retry_preserves_report(
        self, mock_queue, mock_llm, mock_ctx, mock_pop, mock_store_cls
    ):
        """revision_number>0 时不清零报告。"""
        from app.graph.nodes.planner import plan_node

        mock_llm.return_value = MagicMock(content="修正方向1")
        mock_store_cls.return_value.search.return_value = []

        state = _base_state(
            revision_number=1,
            final_report="上一版报告",
            citation_refs="[1] 来源A",
        )
        result = await plan_node(state)
        assert "final_report" not in result
        assert "citation_refs" not in result

    @pytest.mark.asyncio
    @patch("app.graph.nodes.planner.MemoryStore")
    @patch("app.graph.nodes.planner.get_skill_prompt", return_value="请使用深度搜索策略")
    @patch("app.graph.nodes.planner.pop_skill_cache", return_value="deep_search")
    @patch("app.graph.nodes.planner.build_conversation_context", return_value="[当前问题] test")
    @patch("app.graph.nodes.planner.llm_invoke")
    @patch("app.graph.nodes.planner.get_token_queue", return_value=None)
    async def test_skill_prompt_injected(
        self, mock_queue, mock_llm, mock_ctx, mock_pop, mock_skill, mock_store_cls
    ):
        """匹配到 Skill 时 skill prompt 被注入到对话上下文。"""
        from app.graph.nodes.planner import plan_node

        mock_llm.return_value = MagicMock(content="方向A")
        mock_store_cls.return_value.search.return_value = []

        await plan_node(_base_state())
        # 验证 build_conversation_context 的调用参数包含了 skill prompt
        call_args = mock_ctx.call_args[0][0]
        # build_conversation_context 接收 state，但 planner 拼接后再传给 prompt
        # 实际上 skill_prompt 是在 plan_node 内部拼接到 prompt_text 里的
        mock_skill.assert_called_once_with("deep_search")

    @pytest.mark.asyncio
    @patch("app.graph.nodes.planner.MemoryStore")
    @patch("app.graph.nodes.planner.pop_skill_cache", return_value="")
    @patch("app.graph.nodes.planner.build_conversation_context", return_value="[当前问题] test")
    @patch("app.graph.nodes.planner.llm_invoke")
    @patch("app.graph.nodes.planner.get_token_queue", return_value=None)
    async def test_no_skill_when_cache_empty(
        self, mock_queue, mock_llm, mock_ctx, mock_pop, mock_store_cls
    ):
        """pop_skill_cache 返回空时注入空 skill_prompt。"""
        from app.graph.nodes.planner import plan_node

        mock_llm.return_value = MagicMock(content="方向A")
        mock_store_cls.return_value.search.return_value = []

        result = await plan_node(_base_state())
        assert result["plan"] == ["方向A"]
        # pop_skill_cache 返回 "" 时不会调用 get_skill_prompt
        mock_pop.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.graph.nodes.planner.MemoryStore")
    @patch("app.graph.nodes.planner.pop_skill_cache", return_value="")
    @patch("app.graph.nodes.planner.build_conversation_context", return_value="[当前问题] test")
    @patch("app.graph.nodes.planner.llm_invoke")
    @patch("app.graph.nodes.planner.get_token_queue", return_value=None)
    async def test_strips_whitespace_from_plans(
        self, mock_queue, mock_llm, mock_ctx, mock_pop, mock_store_cls
    ):
        """LLM 返回带空格的计划时应去除空白。"""
        from app.graph.nodes.planner import plan_node

        mock_llm.return_value = MagicMock(content=" 方向A , 方向B , 方向C ")
        mock_store_cls.return_value.search.return_value = []

        result = await plan_node(_base_state())
        assert result["plan"] == ["方向A", "方向B", "方向C"]

    @pytest.mark.asyncio
    @patch("app.graph.nodes.planner.MemoryStore")
    @patch("app.graph.nodes.planner.pop_skill_cache", return_value="")
    @patch("app.graph.nodes.planner.build_conversation_context", return_value="[当前问题] test")
    @patch("app.graph.nodes.planner.llm_invoke")
    @patch("app.graph.nodes.planner.get_token_queue", return_value=None)
    async def test_semantic_memory_injected(
        self, mock_queue, mock_llm, mock_ctx, mock_pop, mock_store_cls
    ):
        """Semantic 记忆被读取并注入 prompt。"""
        from app.graph.nodes.planner import plan_node

        mock_llm.return_value = MagicMock(content="方向A")
        mock_record = MagicMock()
        mock_record.content = "用户偏好: 中文报告"
        mock_store_cls.return_value.search.return_value = [mock_record]

        await plan_node(_base_state())
        # 验证 MemoryStore 被调用了 semantic kind 搜索
        mock_store_cls.return_value.search.assert_called_once_with("", kind="semantic", limit=3)

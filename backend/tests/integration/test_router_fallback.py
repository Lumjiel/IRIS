"""
IRIS 集成测试
- 路由 + 熔断 + 回跳
- 条件边循环终止
- 降级错误处理
- cosine 相似度早停
"""
import pytest
from unittest.mock import patch, MagicMock
from app.graph import create_graph
from app.graph.state import AgentState
from app.error_types import ErrorCode


@pytest.fixture
def mock_memory():
    """Mock checkpointer"""
    from app.graph.checkpoint import get_memory
    return get_memory()


@pytest.fixture
def graph(mock_memory):
    """创建测试用图"""
    return create_graph(memory=mock_memory)


def make_state(**overrides) -> AgentState:
    """创建测试用 AgentState"""
    base: AgentState = {
        "query": "test query",
        "plan": ["sub1", "sub2"],
        "search_results": [],
        "final_report": "",
        "critique": "",
        "revision_number": 0,
        "review_status": "PASS",
        "search_mode": "hybrid",
        "should_stop": False,
        "conversation_summary": "",
        "preferences": {},
        "error_code": None,
        "degraded": False,
        "failed_tools": [],
        "early_stop": False,
        "should_continue": True,
        "report_history": [],
        "tool_status": {},
    }
    base.update(overrides)
    return base


class TestShouldContinue:
    """测试条件边循环终止逻辑"""

    def test_degraded_error_continues_but_marks_degraded(self):
        """降级错误（DEGRADED_SEARCH）继续执行但标记 degraded"""
        from app.graph.graph import should_continue
        state = make_state(error_code=ErrorCode.DEGRADED_SEARCH.value, degraded=True)
        result = should_continue(state)
        assert result == "planner"
        assert state.get("degraded") is True

    def test_tool_failure_ends_loop(self):
        """工具执行失败（非降级错误）终止循环"""
        from app.graph.graph import should_continue
        state = make_state(error_code=ErrorCode.TOOL_EXECUTION_FAILED.value, degraded=False)
        result = should_continue(state)
        assert result == "__end__"

    def test_rate_limit_ends_loop(self):
        """限流错误终止循环"""
        from app.graph.graph import should_continue
        state = make_state(error_code=ErrorCode.RATE_LIMIT.value)
        result = should_continue(state)
        assert result == "__end__"

    def test_reviewer_early_stop_ends(self):
        """reviewer 设置 early_stop 终止循环"""
        from app.graph.graph import should_continue
        state = make_state(early_stop=True, should_continue=False, revision_number=2)
        result = should_continue(state)
        assert result == "__end__"

    def test_should_continue_false_ends(self):
        """should_continue=False 终止循环"""
        from app.graph.graph import should_continue
        state = make_state(should_continue=False, revision_number=2)
        result = should_continue(state)
        assert result == "__end__"

    def test_max_iterations_ends(self):
        """达到最大迭代次数终止"""
        from app.graph.graph import should_continue
        state = make_state(revision_number=5)  # MAX_ITERATIONS = 5
        result = should_continue(state)
        assert result == "__end__"

    def test_normal_revision_continues(self):
        """正常审查不通过时回跳 planner"""
        from app.graph.graph import should_continue
        state = make_state(
            revision_number=1,
            review_status="FAIL",
            critique="需要补充搜索",
        )
        result = should_continue(state)
        assert result == "planner"

    def test_review_pass_ends(self):
        """审查通过时结束"""
        from app.graph.graph import should_continue
        state = make_state(revision_number=0, review_status="PASS")
        result = should_continue(state)
        assert result == "__end__"

    def test_fallback_llm_continues_but_marks_degraded(self):
        """LLM 降级错误继续执行但标记 degraded"""
        from app.graph.graph import should_continue
        state = make_state(error_code=ErrorCode.FALLBACK_LLM.value, degraded=True)
        result = should_continue(state)
        assert result == "planner"
        assert state.get("degraded") is True


class TestResearcherCircuitBreaker:
    """测试 researcher 熔断机制"""

    def test_document_mode_doc_irrelevant_stops(self):
        """document 模式文档不相关时提前终止"""
        from app.graph.nodes.researcher import research_node
        
        state = make_state(search_mode="document", query="量子计算")
        
        # Mock retriever 返回空结果
        with patch("app.graph.nodes.researcher.get_retriever") as mock_get_retriever:
            mock_retriever = MagicMock()
            mock_retriever.invoke.return_value = []
            mock_get_retriever.return_value = mock_retriever
            
            result = research_node(state)
        
        assert result.get("should_stop") is True
        assert result.get("error_code") == ErrorCode.VALIDATION_FAILED

    def test_hybrid_mode_no_web_search_in_researcher(self):
        """researcher 不再直接搜索，网络搜索已迁移至 search_agent"""
        from app.graph.nodes.researcher import research_node
        
        state = make_state(search_mode="hybrid", query="量子计算")
        
        with patch("app.graph.nodes.researcher.get_retriever") as mock_get_retriever:
            mock_retriever = MagicMock()
            mock_retriever.invoke.return_value = []
            mock_get_retriever.return_value = mock_retriever
            
            result = research_node(state)
        
        # researcher 不再做 web 搜索，只返回本地 RAG 结果
        assert "search_results" in result


class TestReviewerEarlyStop:
    """测试 reviewer cosine 相似度早停"""

    def test_high_similarity_triggers_early_stop(self):
        """高相似度触发早停"""
        from app.graph.nodes.reviewer import review_node
        
        # 两份非常相似的报告
        similar_report = "这是一份关于AI Agent的调研报告，内容详尽。" * 5
        
        state = make_state(
            final_report=similar_report,
            report_history=[similar_report],  # 上一版完全相同
        )
        
        result = review_node(state)
        
        assert result.get("early_stop") is True
        assert result.get("should_continue") is False
        assert result.get("review_status") == "PASS"

    def test_low_similarity_continues(self):
        """低相似度继续循环"""
        from app.graph.nodes.reviewer import review_node
        
        state = make_state(
            final_report="第一份报告内容",
            report_history=["完全不同的另一份报告"],
        )
        
        # Mock LLM 返回 PASS
        with patch("app.graph.nodes.reviewer.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(
                content='{"status": "FAIL", "feedback": "需要补充"}'
            )
            result = review_node(state)
        
        assert result.get("early_stop") is False
        assert result.get("should_continue") is True

    def test_empty_report_fails(self):
        """空报告直接 FAIL"""
        from app.graph.nodes.reviewer import review_node
        
        state = make_state(final_report="", report_history=[])
        
        result = review_node(state)
        
        assert result.get("review_status") == "FAIL"
        assert "不完整" in result.get("critique", "")


class TestResearcherValidationNode:
    """测试 researcher Validation Node"""

    def test_failed_tool_marks_degraded(self):
        """失败工具标记降级"""
        from app.graph.nodes.researcher import research_node
        
        state = make_state(
            search_mode="hybrid",
            plan=["AI Agent"],
        )
        
        # Mock retriever 失败
        with patch("app.graph.nodes.researcher.get_retriever") as mock_get_retriever:
            mock_get_retriever.side_effect = Exception("ChromaDB 连接失败")
            
            result = research_node(state)
        
        # 应该标记降级
        assert result.get("degraded") is True
        assert result.get("error_code") == ErrorCode.DEGRADED_SEARCH

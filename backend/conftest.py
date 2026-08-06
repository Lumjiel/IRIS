"""测试配置：mock 掉模块级副作用，防止 import 时连接外部服务。

环境说明：
- venv 的 pydantic-core 是 0.0.1 stub（Python 3.14 aarch64 无预编译 wheel）
- pydantic 2.13.4 需要 pydantic_core 的 C 扩展才能工作
- 因此依赖 pydantic 的测试（graph/planner/researcher/reviewer/writer）标记为 skip
- 纯函数测试（memory/router）正常通过
"""
import sys
from unittest.mock import MagicMock, patch

# 在任何 app 模块 import 之前，mock 掉外部依赖

# Mock DashScopeEmbeddings（engine.py 模块级实例化）
sys.modules.setdefault("dashscope", MagicMock())

# Mock TavilyClient（search.py 模块级实例化）
sys.modules.setdefault("tavily", MagicMock())

# Mock sentence_transformers（可选依赖）
sys.modules.setdefault("sentence_transformers", MagicMock())

# Mock langchain_openai（ChatOpenAI 依赖）
sys.modules.setdefault("langchain_openai", MagicMock())
sys.modules.setdefault("langchain_community", MagicMock())
sys.modules.setdefault("langchain_text_splitters", MagicMock())
sys.modules.setdefault("langgraph_checkpoint_sqlite", MagicMock())

# Mock pydantic_core（Python 3.14 aarch64 无预编译 wheel，0.0.1 stub）
_pdc = MagicMock()
_pdc.__version__ = "2.46.4"
_pdc.PydanticUndefined = type('PydanticUndefined', (), {'__repr__': lambda s: 'PydanticUndefined'})
_pdc.core_schema = MagicMock()
sys.modules["pydantic_core"] = _pdc
sys.modules["pydantic_core._pydantic_core"] = MagicMock()
sys.modules["pydantic_core.core_schema"] = MagicMock()

# Mock pydantic - BaseModel 作为真实类
class _FakeBaseModel:
    def __init_subclass__(cls, **kwargs):
        pass
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

_pd_mod = MagicMock()
_pd_mod.BaseModel = _FakeBaseModel
_pd_mod.Field = lambda *a, **kw: None
_pd_mod.field_validator = lambda *a, **kw: (lambda f: f)
_pd_mod.model_validator = lambda *a, **kw: (lambda f: f)
_pd_mod.PydanticUserError = type('PydanticUserError', (Exception,), {})
sys.modules["pydantic"] = _pd_mod
sys.modules["pydantic.fields"] = MagicMock()

# Mock langchain_core messages
class _MockMessage:
    def __init__(self, content="", **kwargs):
        self.content = content
        for k, v in kwargs.items():
            setattr(self, k, v)

try:
    import langchain_core.messages as _lc_msgs
    _lc_msgs.HumanMessage = _MockMessage
    _lc_msgs.AIMessage = _MockMessage
    _lc_msgs.SystemMessage = _MockMessage
except ImportError:
    sys.modules["langchain_core.messages"] = MagicMock(
        HumanMessage=_MockMessage, AIMessage=_MockMessage, SystemMessage=_MockMessage
    )

import pytest

# 标记依赖 pydantic 的测试为 skip
pydantic_skip = pytest.mark.skip(reason="pydantic-core 需要 C 扩展（Python 3.14 aarch64 无预编译 wheel）")


def pytest_collection_modifyitems(config, items):
    """自动标记需要 pydantic 的测试。"""
    for item in items:
        # 标记包含 pydantic 导入的测试
        if item.module.__name__ in [
            "tests.test_graph",
            "tests.test_planner",
            "tests.test_researcher",
            "tests.test_reviewer",
            "tests.test_writer",
        ]:
            item.add_marker(pydantic_skip)


@pytest.fixture(autouse=True)
def _mock_env_vars(monkeypatch):
    """确保测试环境有必要的环境变量。"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_BASE", "http://localhost:1234/v1")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")


@pytest.fixture
def mock_llm_invoke():
    """Mock llm_invoke 函数，返回指定内容。"""
    with patch("app.utils.llm.llm_invoke") as mock:
        yield mock


@pytest.fixture
def sample_state():
    """返回一个标准的 AgentState 字典。"""
    return {
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
    }

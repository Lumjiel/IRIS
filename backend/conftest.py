"""测试配置：mock 掉模块级副作用，防止 import 时连接外部服务。"""
import sys
from unittest.mock import MagicMock, patch

# 在任何 app 模块 import 之前，mock 掉外部依赖
# 这些 mock 会被 conftest 中的 fixture 进一步细化

# Mock DashScopeEmbeddings（engine.py 模块级实例化）
_dashscope_mock = MagicMock()
sys.modules.setdefault("dashscope", _dashscope_mock)

# Mock TavilyClient（search.py 模块级实例化）
_tavily_mock = MagicMock()
sys.modules.setdefault("tavily", _tavily_mock)

# Mock sentence_transformers（可选依赖）
_st_mock = MagicMock()
sys.modules.setdefault("sentence_transformers", _st_mock)

import pytest


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
    }

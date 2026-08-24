"""P1 Rerank 测试：DashScopeReranker 三条路径 + RerankRetriever 降级 + search_reports 契约。"""
import asyncio
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document


# ============================================================
# 工具：构造 fake dashscope 响应
# ============================================================

def _make_response(status_code=200, results=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.code = "InvalidApiKey" if status_code != 200 else None
    resp.message = "mock error" if status_code != 200 else None
    output = MagicMock()
    output.results = results if results is not None else []
    resp.output = output
    return resp


def _docs(n):
    return [Document(page_content=f"doc-{i}") for i in range(n)]


@pytest.fixture
def fake_dashscope(monkeypatch):
    """替换 reranker 模块内延迟导入的 dashscope，返回可编程的 call。"""
    import sys

    mock = MagicMock()
    monkeypatch.setitem(sys.modules, "dashscope", mock)
    return mock


@pytest.fixture(autouse=True)
def _reset_singleton():
    # app.rag.reranker 的模块级单例；每个用例前后重置避免跨用例污染
    """每个用例重置单例，避免跨用例污染。"""
    import app.rag.reranker as rr

    rr._reranker = None
    yield
    rr._reranker = None


# ============================================================
# DashScopeReranker
# ============================================================

class TestDashScopeReranker:
    def test_rerank_sorts_by_score_and_truncates(self, fake_dashscope):
        from app.rag.reranker import DashScopeReranker

        # 候选 0/1/2，rerank 判定 doc-2 最相关、doc-0 最差；top_k=2 只留前两个
        fake_dashscope.TextReRank.call.return_value = _make_response(
            results=[
                {"index": 2, "relevance_score": 0.9},
                {"index": 1, "relevance_score": 0.5},
                {"index": 0, "relevance_score": 0.1},
            ]
        )
        out = DashScopeReranker().rerank("q", _docs(3), top_k=2)

        assert [d.page_content for d in out] == ["doc-2", "doc-1"]
        assert out[0].metadata["relevance_score"] == pytest.approx(0.9)

    def test_rerank_api_error_raises(self, fake_dashscope):
        from app.rag.reranker import DashScopeReranker, RerankError

        fake_dashscope.TextReRank.call.return_value = _make_response(status_code=401)
        with pytest.raises(RerankError, match="非 200"):
            DashScopeReranker().rerank("q", _docs(3), top_k=2)

    def test_rerank_network_exception_raises(self, fake_dashscope):
        from app.rag.reranker import DashScopeReranker, RerankError

        fake_dashscope.TextReRank.call.side_effect = TimeoutError("timed out")
        with pytest.raises(RerankError, match="调用失败"):
            DashScopeReranker().rerank("q", _docs(3), top_k=2)

    def test_rerank_malformed_response_raises(self, fake_dashscope):
        from app.rag.reranker import DashScopeReranker, RerankError

        fake_dashscope.TextReRank.call.return_value = _make_response(
            results=[{"index": 0}]  # 缺 relevance_score
        )
        with pytest.raises(RerankError, match="响应格式异常"):
            DashScopeReranker().rerank("q", _docs(3), top_k=2)

    def test_empty_docs_short_circuit(self, fake_dashscope):
        from app.rag.reranker import DashScopeReranker

        assert DashScopeReranker().rerank("q", [], top_k=5) == []
        fake_dashscope.TextReRank.call.assert_not_called()


# ============================================================
# RerankRetriever（engine.py 路径 A）
# ============================================================

class TestRerankRetriever:
    def _retriever_with(self, reranker, n_candidates=4):
        from app.rag.engine import RerankRetriever

        vectorstore = MagicMock()
        vectorstore.similarity_search.return_value = _docs(n_candidates)
        return RerankRetriever(vectorstore=vectorstore, reranker=reranker, top_k=2, fetch_k=20)

    def test_success_uses_ranked_order(self, fake_dashscope):
        reranker = MagicMock()

        def _rank(query, docs, top_k):
            return list(reversed(docs))[:top_k]

        reranker.rerank.side_effect = _rank
        out = self._retriever_with(reranker).invoke("q")
        assert [d.page_content for d in out] == ["doc-3", "doc-2"]

    def test_failopen_degrades_to_vector_order(self):
        """I3 关键路径：rerank 抛异常时降级为向量召回序的前 top_k，不抛错。"""
        from app.rag.reranker import RerankError

        reranker = MagicMock()
        reranker.rerank.side_effect = RerankError("gte-rerank 调用失败")
        out = self._retriever_with(reranker).invoke("q")
        assert [d.page_content for d in out] == ["doc-0", "doc-1"]

    def test_no_candidates_returns_empty(self):
        reranker = MagicMock()
        out = self._retriever_with(reranker, n_candidates=0).invoke("q")
        assert out == []
        reranker.rerank.assert_not_called()


# ============================================================
# search_reports（report_ingest.py 路径 B）
# ============================================================

class FakeChroma:
    """替身向量库：固定返回 8 个候选，distance 随 index 递增。"""

    last_call_kwargs = None

    def __init__(self, persist_directory=None, embedding_function=None, **kwargs):
        pass

    def similarity_search_with_score(self, query, k=5, filter=None):
        FakeChroma.last_call_kwargs = {"query": query, "k": k, "filter": filter}
        return [
            (Document(page_content=f"chunk-{i}", metadata={"chunk_index": i}), float(i) * 0.1)
            for i in range(min(k, 8))
        ]


@pytest.fixture
def fake_report_env(monkeypatch, tmp_path):
    """"DB 存在"的假环境 + 替身 Chroma。"""
    import app.rag.report_ingest as ri

    db_dir = tmp_path / "chroma_db"
    db_dir.mkdir()
    (db_dir / "placeholder").write_text("x")
    monkeypatch.setattr(ri, "DB_PATH", str(db_dir))
    monkeypatch.setattr("langchain_community.vectorstores.Chroma", FakeChroma)
    return ri


class TestSearchReports:
    def test_without_rerank_vector_order(self, fake_report_env, monkeypatch):
        ri = fake_report_env
        monkeypatch.setattr("app.config.ENABLE_RERANKER", False)

        results = asyncio.run(ri.search_reports("测试查询", top_k=3))

        assert len(results) == 3
        assert all(r["reranked"] is False for r in results)
        assert results[0]["text"] == "chunk-0"
        assert results[0]["score"] == pytest.approx(0.0)  # Chroma distance

    def test_with_rerank_relevance_contract(self, fake_report_env, monkeypatch):
        """score 契约：reranked=true 时 score=relevance_score（越大越相关）。"""
        ri = fake_report_env
        monkeypatch.setattr("app.config.ENABLE_RERANKER", True)

        reranker = MagicMock()

        def _rank(query, docs, top_k):
            for i, d in enumerate(docs[:top_k]):
                d.metadata["relevance_score"] = 0.99 - i * 0.1
            return docs[:top_k]

        reranker.rerank.side_effect = _rank
        monkeypatch.setattr("app.rag.reranker.get_reranker", lambda: reranker)

        results = asyncio.run(ri.search_reports("测试查询", top_k=3))

        assert all(r["reranked"] is True for r in results)
        assert results[0]["score"] == pytest.approx(0.99)

    def test_with_rerank_few_candidates_skips_api(self, fake_report_env, monkeypatch):
        """候选数 <= top_k 时直接全量返回，不调 rerank API。"""
        ri = fake_report_env
        monkeypatch.setattr("app.config.ENABLE_RERANKER", True)

        called = {"n": 0}
        reranker = MagicMock()

        def _fail(*a, **kw):
            called["n"] += 1
            raise AssertionError("不应调用 rerank")

        reranker.rerank.side_effect = _fail
        monkeypatch.setattr("app.rag.reranker.get_reranker", lambda: reranker)

        # top_k=10 > 候选 8 个 → 不应触发 rerank
        results = asyncio.run(ri.search_reports("测试查询", top_k=10))

        assert called["n"] == 0
        assert len(results) == 8
        assert all(r["reranked"] is False for r in results)

    def test_rerank_failure_falls_back_to_vector_order(self, fake_report_env, monkeypatch):
        ri = fake_report_env
        monkeypatch.setattr("app.config.ENABLE_RERANKER", True)

        reranker = MagicMock()
        reranker.rerank.side_effect = RuntimeError("boom")
        monkeypatch.setattr("app.rag.reranker.get_reranker", lambda: reranker)

        results = asyncio.run(ri.search_reports("测试查询", top_k=3))

        assert len(results) == 3
        assert all(r["reranked"] is False for r in results)
        assert [r["text"] for r in results] == ["chunk-0", "chunk-1", "chunk-2"]

    def test_stock_code_filter_passed_through(self, fake_report_env, monkeypatch):
        ri = fake_report_env
        monkeypatch.setattr("app.config.ENABLE_RERANKER", False)

        asyncio.run(ri.search_reports("测试查询", stock_code="600196", top_k=3))
        assert FakeChroma.last_call_kwargs is not None
        assert FakeChroma.last_call_kwargs["filter"] == {"stock_code": "600196"}
    def test_empty_db_returns_empty(self, monkeypatch, tmp_path):
        import app.rag.report_ingest as ri

        empty_dir = tmp_path / "empty_db"
        empty_dir.mkdir()
        monkeypatch.setattr(ri, "DB_PATH", str(empty_dir))

        assert asyncio.run(ri.search_reports("q")) == []


# ============================================================
# get_retriever 开启态分支
# ============================================================

class TestGetRetrieverEnabled:
    def test_enabled_returns_rerank_retriever(self, monkeypatch, tmp_path):
        """I3：conftest 把 dashscope mock 成 MagicMock，必须显式验证开启态分支排序正确。"""
        import app.rag.engine as eng

        db_dir = tmp_path / "chroma_db"
        db_dir.mkdir()
        (db_dir / "placeholder").write_text("x")
        monkeypatch.setattr(eng, "DB_PATH", str(db_dir))
        monkeypatch.setattr("app.config.ENABLE_RERANKER", True)

        retriever = eng.get_retriever()
        assert isinstance(retriever, eng.RerankRetriever)

    def test_disabled_returns_plain_retriever(self, monkeypatch, tmp_path):
        import app.rag.engine as eng

        db_dir = tmp_path / "chroma_db"
        db_dir.mkdir()
        (db_dir / "placeholder").write_text("x")
        monkeypatch.setattr(eng, "DB_PATH", str(db_dir))
        monkeypatch.setattr(eng, "ENABLE_RERANKER", False)  # engine 模块顶层已导入该名字

        retriever = eng.get_retriever()
        assert not isinstance(retriever, eng.RerankRetriever)

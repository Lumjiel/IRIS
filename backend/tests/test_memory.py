"""memory 系统测试。"""
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock


class TestTruncateAtSentence:
    """_truncate_at_sentence 纯函数测试。"""

    def test_short_text_unchanged(self):
        from app.utils.memory import _truncate_at_sentence
        text = "这是一段短文本。"
        assert _truncate_at_sentence(text, 100) == text

    def test_truncates_at_period(self):
        from app.utils.memory import _truncate_at_sentence
        text = "第一句话。第二句话。第三句话。" * 20
        result = _truncate_at_sentence(text, 30)
        assert len(result) <= 31  # +1 for period
        assert result.endswith("。")

    def test_truncates_at_exclamation(self):
        from app.utils.memory import _truncate_at_sentence
        text = "好厉害！这真棒！太强了！" * 20
        result = _truncate_at_sentence(text, 30)
        assert result.endswith("！") or result.endswith("...")

    def test_truncates_at_question(self):
        from app.utils.memory import _truncate_at_sentence
        text = "为什么呢？怎么回事？你说呢？" * 20
        result = _truncate_at_sentence(text, 30)
        assert result.endswith("？") or result.endswith("...")

    def test_fallback_to_comma(self):
        from app.utils.memory import _truncate_at_sentence
        text = "很长的没有句号的文本，逗号在这里，继续逗号，再来一个逗号" * 20
        result = _truncate_at_sentence(text, 30)
        assert result.endswith("，") or result.endswith("...")

    def test_hard_truncate_fallback(self):
        from app.utils.memory import _truncate_at_sentence
        text = "没有任何标点符号的很长的文本内容" * 20
        result = _truncate_at_sentence(text, 30)
        assert len(result) <= 35
        assert result.endswith("...")

    def test_english_punctuation(self):
        from app.utils.memory import _truncate_at_sentence
        text = "First sentence. Second sentence. Third sentence." * 10
        result = _truncate_at_sentence(text, 40)
        assert result.endswith(".") or result.endswith("...")


class TestBuildConversationContext:
    """build_conversation_context 纯函数测试。"""

    def test_returns_current_query(self):
        from app.utils.memory import build_conversation_context
        state = {"query": "量子计算进展"}
        result = build_conversation_context(state)
        assert "量子计算进展" in result
        assert "[当前问题]" in result

    def test_empty_query(self):
        from app.utils.memory import build_conversation_context
        result = build_conversation_context({"query": ""})
        assert "[当前问题]" in result

    def test_missing_query(self):
        from app.utils.memory import build_conversation_context
        result = build_conversation_context({})
        assert "[当前问题]" in result


class TestUpdateConversationSummary:
    """update_conversation_summary 测试。"""

    def test_first_turn_no_old_summary(self):
        from app.utils.memory import update_conversation_summary
        result = update_conversation_summary(
            old_summary="",
            query="量子计算",
            report="报告内容",
        )
        assert "量子计算" in result
        assert "报告要点" in result

    def test_appends_when_under_threshold(self):
        from app.utils.memory import update_conversation_summary
        old = "旧摘要内容"
        result = update_conversation_summary(
            old_summary=old,
            query="新问题",
            report="新报告",
        )
        assert "旧摘要内容" in result
        assert "新问题" in result

    def test_compresses_when_over_threshold(self):
        from app.utils.memory import update_conversation_summary, SUMMARY_MAX_CHARS
        old = "很长的旧摘要" * 500
        with patch("app.utils.memory.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="压缩后的摘要")
            result = update_conversation_summary(
                old_summary=old,
                query="新问题",
                report="新报告",
            )
            assert result == "压缩后的摘要"
            mock_llm.assert_called_once()

    def test_compression_failure_falls_back_to_truncation(self):
        from app.utils.memory import update_conversation_summary, SUMMARY_MAX_CHARS
        old = "很长的旧摘要" * 500
        with patch("app.utils.memory.llm_invoke", side_effect=Exception("LLM error")):
            result = update_conversation_summary(
                old_summary=old,
                query="新问题",
                report="新报告",
            )
            assert len(result) <= SUMMARY_MAX_CHARS + 20  # some tolerance

    def test_includes_search_directions(self):
        from app.utils.memory import update_conversation_summary
        result = update_conversation_summary(
            old_summary="",
            query="测试",
            report="报告",
            search_directions=["方向A", "方向B"],
        )
        assert "方向A" in result
        assert "方向B" in result

    def test_includes_critique(self):
        from app.utils.memory import update_conversation_summary
        result = update_conversation_summary(
            old_summary="",
            query="测试",
            report="报告",
            critique="内容不够详细",
        )
        assert "内容不够详细" in result


class TestMemoryStore:
    """MemoryStore CRUD 测试。"""

    @pytest.fixture
    def tmp_store(self, tmp_path):
        """创建临时 SQLite 数据库。"""
        from app.memory.store import MemoryStore
        db_path = str(tmp_path / "test_memory.db")
        store = MemoryStore(db_path=db_path)
        yield store

    def test_add_and_get(self, tmp_store):
        """创建记忆后可读取。"""
        record = tmp_store.add(kind="episodic", content="测试内容", thread_id="t1")
        fetched = tmp_store.get(record.id)
        assert fetched is not None
        assert fetched.content == "测试内容"
        assert fetched.kind == "episodic"
        assert fetched.thread_id == "t1"

    def test_add_generates_id(self, tmp_store):
        """添加记忆自动生成唯一 ID。"""
        r1 = tmp_store.add(kind="semantic", content="内容A")
        r2 = tmp_store.add(kind="semantic", content="内容B")
        assert r1.id != r2.id

    def test_search_by_kind(self, tmp_store):
        """按类型筛选记忆。"""
        tmp_store.add(kind="episodic", content="事件记忆")
        tmp_store.add(kind="semantic", content="语义记忆")
        tmp_store.add(kind="procedural", content="程序记忆")

        results = tmp_store.search("", kind="episodic")
        assert len(results) == 1
        assert results[0].kind == "episodic"

    def test_search_by_content(self, tmp_store):
        """按内容搜索记忆。"""
        tmp_store.add(kind="episodic", content="量子计算研究")
        tmp_store.add(kind="episodic", content="区块链技术")
        tmp_store.add(kind="semantic", content="量子计算偏好")

        results = tmp_store.search("量子")
        assert len(results) == 2

    def test_update(self, tmp_store):
        """更新记忆内容。"""
        record = tmp_store.add(kind="semantic", content="旧内容")
        updated = tmp_store.update(record.id, content="新内容")
        assert updated.content == "新内容"
        assert updated.updated_at >= record.updated_at

    def test_update_kind(self, tmp_store):
        """更新记忆类型。"""
        record = tmp_store.add(kind="episodic", content="内容")
        updated = tmp_store.update(record.id, kind="semantic")
        assert updated.kind == "semantic"

    def test_update_nonexistent_returns_none(self, tmp_store):
        """更新不存在的记忆返回 None。"""
        result = tmp_store.update("nonexistent", content="新内容")
        assert result is None

    def test_delete(self, tmp_store):
        """删除记忆。"""
        record = tmp_store.add(kind="episodic", content="待删除")
        assert tmp_store.delete(record.id) is True
        assert tmp_store.get(record.id) is None

    def test_delete_nonexistent_returns_false(self, tmp_store):
        """删除不存在的记忆返回 False。"""
        assert tmp_store.delete("nonexistent") is False

    def test_list_by_kind(self, tmp_store):
        """按类型列出所有记忆。"""
        tmp_store.add(kind="episodic", content="A")
        tmp_store.add(kind="episodic", content="B")
        tmp_store.add(kind="semantic", content="C")

        results = tmp_store.list_by_kind("episodic")
        assert len(results) == 2
        assert all(r.kind == "episodic" for r in results)

    def test_metadata_roundtrip(self, tmp_store):
        """metadata 序列化/反序列化。"""
        meta = {"query": "test", "plan": ["a", "b"]}
        record = tmp_store.add(kind="episodic", content="带元数据", metadata=meta)
        fetched = tmp_store.get(record.id)
        assert fetched.metadata == meta

    def test_search_with_limit(self, tmp_store):
        """搜索结果受 limit 限制。"""
        for i in range(10):
            tmp_store.add(kind="episodic", content=f"记忆{i}")
        results = tmp_store.search("", kind="episodic", limit=3)
        assert len(results) == 3

    def test_empty_query_returns_recent(self, tmp_store):
        """空查询返回最近记录。"""
        tmp_store.add(kind="episodic", content="A")
        tmp_store.add(kind="episodic", content="B")
        results = tmp_store.search("", limit=1)
        assert len(results) == 1


class TestMemorySemanticSearch:
    """内存语义检索（embedding 余弦打分）测试。"""

    def test_cosine_pure(self):
        from app.memory.store import _cosine
        assert _cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
        assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
        assert _cosine(None, [1.0]) == 0.0
        assert _cosine([1.0], None) == 0.0

    def test_semantic_ranks_by_cosine(self, tmp_path):
        from app.memory.store import MemoryStore
        store = MemoryStore(db_path=str(tmp_path / "sem.db"))

        # 模拟嵌入：含"量子"的文本向量指向 [1,0]，其余指向 [0,1]
        fake_embed = lambda t: [1.0, 0.0] if "量子" in t else [0.0, 1.0]
        with patch("app.memory.store._embed", side_effect=fake_embed):
            store.add(kind="episodic", content="量子计算报告")
            store.add(kind="episodic", content="区块链报告")
            results = store.search("量子相关", kind="episodic", limit=1)
        assert results[0].content == "量子计算报告"

    def test_semantic_fallback_to_keyword_when_embed_none(self, tmp_path):
        """嵌入不可用时（_embed 返回 None）无损回退到关键词。"""
        from app.memory.store import MemoryStore
        store = MemoryStore(db_path=str(tmp_path / "kw.db"))
        store.add(kind="episodic", content="量子计算研究")
        store.add(kind="episodic", content="区块链技术")

        with patch("app.memory.store._embed", return_value=None):
            results = store.search("量子", kind="episodic", limit=5)
        contents = [r.content for r in results]
        assert "量子计算研究" in contents


class TestExtractMemories:
    """extract_memories 测试。"""

    @patch("app.memory.extractor.get_token_usage", return_value={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    @patch("app.memory.extractor._get_store")
    def test_creates_episodic_record(self, mock_get_store, mock_usage):
        from app.memory.extractor import extract_memories

        mock_store = MagicMock()
        mock_record = MagicMock()
        mock_store.add.return_value = mock_record
        mock_get_store.return_value = mock_store

        records = extract_memories(
            query="量子计算",
            plan=["方向A"],
            report="报告内容",
            thread_id="t1",
        )
        assert len(records) >= 1
        # episodic 记录
        call_kwargs = mock_store.add.call_args_list[0][1]
        assert call_kwargs["kind"] == "episodic"
        assert "量子计算" in call_kwargs["content"]

    @patch("app.memory.extractor.get_token_usage", return_value={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    @patch("app.memory.extractor._get_store")
    def test_creates_semantic_when_preferences(self, mock_get_store, mock_usage):
        from app.memory.extractor import extract_memories

        mock_store = MagicMock()
        mock_record = MagicMock()
        mock_store.add.return_value = mock_record
        mock_get_store.return_value = mock_store

        records = extract_memories(
            query="test",
            plan=["A"],
            report="report",
            preferences={"style": "concise"},
        )
        # episodic + semantic (preferences)
        kinds = [call[1]["kind"] for call in mock_store.add.call_args_list]
        assert "semantic" in kinds

    @patch("app.memory.extractor.get_token_usage", return_value={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    @patch("app.memory.extractor._get_store")
    def test_creates_procedural_for_plan(self, mock_get_store, mock_usage):
        from app.memory.extractor import extract_memories

        mock_store = MagicMock()
        mock_record = MagicMock()
        mock_store.add.return_value = mock_record
        mock_get_store.return_value = mock_store

        records = extract_memories(
            query="test",
            plan=["方向A", "方向B"],
            report="report",
        )
        kinds = [call[1]["kind"] for call in mock_store.add.call_args_list]
        assert "procedural" in kinds

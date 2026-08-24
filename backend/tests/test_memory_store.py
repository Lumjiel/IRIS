"""P2 长期记忆测试：抽取规则 / Store 幂等与隔离 / prompt 注入 / 降级 / 管理 API。"""
import asyncio

import pytest

from app.utils import memory_store as ms


# ============================================================
# 规则抽取器
# ============================================================

class TestExtractWatchStocks:
    def test_explicit_watch_from_query(self):
        out = ms.extract_watch_stocks("帮我关注一下600196", {})
        assert len(out) == 1
        assert out[0]["kind"] == "watch_stock"
        assert out[0]["stock_code"] == "600196"
        assert out[0]["source"] == "explicit"

    def test_auto_from_research_snapshot(self):
        """研究完成时自动记录本次分析的股票（pending_stock_code）。"""
        out = ms.extract_watch_stocks("分析这只股票", {"pending_stock_code": "600519"})
        assert len(out) == 1
        assert out[0]["stock_code"] == "600519"
        assert out[0]["source"] == "auto"

    def test_auto_dedup_pending_and_financial(self):
        snapshot = {"pending_stock_code": "000001",
                    "financial_data": {"stock_code": "000001"}}
        out = ms.extract_watch_stocks("q", snapshot)
        assert len(out) == 1  # 保序去重，不产生两条

    def test_no_keyword_no_record(self):
        """查询含股票代码但无关注意图 → 不记录（研究产物除外）。"""
        assert ms.extract_watch_stocks("600196 现在多少倍市盈率", {}) == []

    def test_date_like_numbers_not_matched(self):
        """严格正则：日期段号/基金代码等不以 [0368] 开头的 6 位数字不误记。"""
        assert ms.extract_watch_stocks("记住2024年12月31日的事", {}) == []
        assert ms.extract_watch_stocks("记住159915", {}) == []  # 创业板 ETF 基金代码 15 开头

    def test_invalid_snapshot_code_ignored(self):
        out = ms.extract_watch_stocks("", {"pending_stock_code": "abc123"})
        assert out == []


class TestExtractExplicitMemory:
    def test_remember_preference_via_llm(self, monkeypatch):
        class FakeResp:
            content = '{"kind": "preference", "content": "喜欢简洁结论"}'

        monkeypatch.setattr(
            "app.utils.llm.llm_invoke",
            lambda *a, **kw: FakeResp(),
        )
        out = asyncio.run(ms.extract_explicit_memory("记住我喜欢简洁的结论"))
        assert out is not None
        assert out["kind"] == "preference"
        assert out["content"] == "喜欢简洁结论"

    def test_llm_failure_returns_none(self, monkeypatch):
        def _boom(*a, **kw):
            raise RuntimeError("LLM down")

        monkeypatch.setattr("app.utils.llm.llm_invoke", _boom)
        assert asyncio.run(ms.extract_explicit_memory("记住我是医药研究员")) is None

    def test_no_trigger_word_skips_llm(self):
        assert asyncio.run(ms.extract_explicit_memory("今天天气怎么样")) is None

    def test_stock_code_query_skips_llm(self):
        """含股票代码的"记住"已由规则覆盖，不再调 LLM。"""
        assert asyncio.run(ms.extract_explicit_memory("记住600196")) is None


# ============================================================
# Store 读写（真实 AsyncSqliteStore + tmp DB）
# ============================================================

@pytest.fixture
def tmp_store_db(monkeypatch, tmp_path):
    monkeypatch.setattr(ms, "STORE_DB", str(tmp_path / "store_test.db"))
    return ms


class TestStoreReadWrite:
    def test_watch_key_idempotent(self, tmp_store_db):
        """watch:{stock_code} 确定性 key：重复写入不产生重复记录。"""
        mem = {"kind": "watch_stock", "content": "用户研究过股票 600196",
               "stock_code": "600196", "source": "auto"}

        async def _run():
            async with tmp_store_db.open_store() as store:
                await store.setup()
                await tmp_store_db.save_memory_into(store, "u1", mem)
                await tmp_store_db.save_memory_into(store, "u1", mem)
                return await store.asearch(("memories", "u1"), limit=100)

        items = asyncio.run(_run())
        assert len(items) == 1
        assert items[0].key == "watch:600196"

    def test_user_isolation(self, tmp_store_db):
        """user A 的记忆不出现在 user B。"""

        async def _run():
            async with tmp_store_db.open_store() as store:
                await store.setup()
                await tmp_store_db.save_memory_into(
                    store, "u1", {"kind": "fact", "content": "A 的记忆"})
                a = await tmp_store_db.load_user_memories(store, "u1")
                b = await tmp_store_db.load_user_memories(store, "u2")
                return a, b

        a, b = asyncio.run(_run())
        assert a == ["A 的记忆"]
        assert b == []

    def test_load_missing_store_returns_empty(self, tmp_store_db):
        """Store 不可用时降级为空列表，主流程不受影响。"""
        assert asyncio.run(tmp_store_db.load_user_memories(None, "u1")) == []

    def test_load_broken_store_returns_empty(self, tmp_store_db):
        class BrokenStore:
            async def asearch(self, *a, **kw):
                raise RuntimeError("db locked")

        assert asyncio.run(tmp_store_db.load_user_memories(BrokenStore(), "u1")) == []


# ============================================================
# 注入拼装（两态）
# ============================================================

class TestMemoryBlock:
    def test_with_memories(self):
        from app.graph.nodes.load_memories import build_memory_block

        state = {"user_memories": ["用户长期关注复星医药(600196)", "偏好简洁结论"]}
        block = build_memory_block(state)
        assert "【用户长期背景】" in block
        assert "600196" in block
        assert "简洁结论" in block

    def test_without_memories_empty(self):
        from app.graph.nodes.load_memories import build_memory_block

        assert build_memory_block({}) == ""
        assert build_memory_block({"user_memories": []}) == ""


class TestLoadMemoriesNode:
    def test_reads_and_injects(self, tmp_store_db):
        from app.graph.nodes.load_memories import load_memories_node

        async def _run():
            async with tmp_store_db.open_store() as store:
                await store.setup()
                await tmp_store_db.save_memory_into(
                    store, "u1", {"kind": "fact", "content": "测试记忆"})
                return await load_memories_node({"user_id": "u1"}, store=store)

        result = asyncio.run(_run())
        assert result == {"user_memories": ["测试记忆"]}

    def test_store_none_degrades(self):
        from app.graph.nodes.load_memories import load_memories_node

        result = asyncio.run(load_memories_node({"user_id": "u1"}, store=None))
        assert result == {"user_memories": []}

    def test_default_user_fallback(self, tmp_store_db):
        from app.graph.nodes.load_memories import load_memories_node

        async def _run():
            async with tmp_store_db.open_store() as store:
                await store.setup()
                await tmp_store_db.save_memory_into(
                    store, "default", {"kind": "fact", "content": "默认用户记忆"})
                # state 无 user_id 字段 → 回退 default
                return await load_memories_node({}, store=store)

        result = asyncio.run(_run())
        assert result == {"user_memories": ["默认用户记忆"]}


# ============================================================
# 会话级入口 + 演示预置
# ============================================================

class TestRememberFromSession:
    def test_writes_watch_stock_after_research(self, tmp_store_db):
        async def _run():
            async with tmp_store_db.open_store() as store:
                await store.setup()

            await tmp_store_db.remember_from_session(
                "u1", "分析一下这家公司",
                {"pending_stock_code": "600196"},
                thread_id="t1",
            )
            async with tmp_store_db.open_store() as store:
                return await tmp_store_db.load_user_memories(store, "u1")

        contents = asyncio.run(_run())
        assert any("600196" in c for c in contents)

    def test_nothing_to_remember_is_silent(self, tmp_store_db):
        # 无股票代码、无"记住"关键词 → 不写任何东西也不报错
        asyncio.run(tmp_store_db.remember_from_session("u1", "你好", {}))


class TestSeedDemoMemories:
    def test_seeds_once(self, tmp_store_db):
        async def _first():
            await tmp_store_db.seed_demo_memories()
            async with tmp_store_db.open_store() as store:
                await store.setup()
                return await tmp_store_db.load_user_memories(store, "default")

        first = asyncio.run(_first())
        assert len(first) >= 2  # 预置 2 条演示记忆

        # 第二次启动不重复写入（幂等）
        second = asyncio.run(_first())
        assert second == first


# ============================================================
# 管理 API（FastAPI TestClient，依赖均 mock 掉外部服务）
# ============================================================

class TestMemoryAPI:
    def test_list_and_delete_roundtrip(self, tmp_store_db, monkeypatch):
        from fastapi.testclient import TestClient
        import main as main_module

        client = TestClient(main_module.app)

        async def _seed():
            async with tmp_store_db.open_store() as store:
                await store.setup()
                await tmp_store_db.save_memory_into(
                    store, "api-user", {"kind": "watch_stock",
                                        "content": "关注 300750",
                                        "stock_code": "300750"})

        asyncio.run(_seed())

        resp = client.get("/api/memory-items", params={"user_id": "api-user"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        key = data["items"][0]["key"]
        assert key == "watch:300750"

        resp = client.delete("/api/memory-items/watch:300750", params={"user_id": "api-user"})
        assert resp.status_code == 200

        resp = client.get("/api/memory-items", params={"user_id": "api-user"})
        assert resp.json()["count"] == 0

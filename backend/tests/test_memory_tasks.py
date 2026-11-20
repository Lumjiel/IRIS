"""memory_tasks 落盘保护测试：任务表 / 收账 / 启动重放 / fail-open / 重试上限。"""
import asyncio

import pytest

from app.utils import memory_tasks as mt


@pytest.fixture()
def tmp_tasks_db(monkeypatch, tmp_path):
    monkeypatch.setattr(mt, "MEMORY_TASKS_DB", str(tmp_path / "memory_tasks_test.db"))
    return tmp_path / "memory_tasks_test.db"


def _status(db, tid):
    import sqlite3
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT status, attempts, last_error FROM memory_tasks WHERE id=?",
                            (tid,)).fetchone()
    finally:
        conn.close()


class TestEnqueueAndMark:
    def test_enqueue_creates_pending(self, tmp_tasks_db):
        tid = mt.enqueue_memory_task("u1", "t1", "关注600196", {"pending_stock_code": "600196"})
        assert tid is not None
        status, attempts, err = _status(tmp_tasks_db, tid)
        assert status == "pending" and attempts == 0 and err is None

    def test_mark_done(self, tmp_tasks_db):
        tid = mt.enqueue_memory_task("u1", "t1", "q", {})
        mt.mark_memory_task_done(tid)
        status, attempts, err = _status(tmp_tasks_db, tid)
        assert status == "done" and attempts == 0

    def test_mark_error_keeps_pending(self, tmp_tasks_db):
        """意外异常：attempts+1、留 pending，供启动重放。"""
        tid = mt.enqueue_memory_task("u1", "t1", "q", {})
        mt.mark_memory_task_done(tid, error="RuntimeError: boom")
        status, attempts, err = _status(tmp_tasks_db, tid)
        assert status == "pending" and attempts == 1 and "RuntimeError: boom" in err

    def test_enqueue_fail_open(self, tmp_tasks_db, monkeypatch):
        """任务表打不开 → 返回 None 不抛（退回原无保护行为，不阻塞记忆写入）。"""
        monkeypatch.setattr(mt, "_connect",
                            lambda: (_ for _ in ()).throw(RuntimeError("db unavailable")))
        assert mt.enqueue_memory_task("u1", "t1", "q", {}) is None


class TestReplay:
    def test_replay_marks_done(self, tmp_tasks_db, monkeypatch):
        """pending 任务启动重放：调 remember_from_session → 收账 done。"""
        tid = mt.enqueue_memory_task("u1", "t1", "关注600196", {"pending_stock_code": "600196"})
        calls = []

        async def fake_remember(user_id, query, snapshot, thread_id=""):
            calls.append((user_id, query, snapshot, thread_id))

        monkeypatch.setattr("app.utils.memory_store.remember_from_session", fake_remember)
        n = asyncio.run(mt.replay_pending_memory_tasks())
        assert n == 1
        assert calls[0][0] == "u1" and calls[0][2] == {"pending_stock_code": "600196"}
        status, _, _ = _status(tmp_tasks_db, tid)
        assert status == "done"

    def test_replay_failure_keeps_pending_with_attempt(self, tmp_tasks_db, monkeypatch):
        """重放异常 → attempts+1 留 pending（remember_from_session 不抛时通常走不到）。"""
        tid = mt.enqueue_memory_task("u1", "t1", "q", {})

        async def boom(user_id, query, snapshot, thread_id=""):
            raise RuntimeError("store broken")

        monkeypatch.setattr("app.utils.memory_store.remember_from_session", boom)
        n = asyncio.run(mt.replay_pending_memory_tasks())
        assert n == 0
        status, attempts, err = _status(tmp_tasks_db, tid)
        assert status == "pending" and attempts == 1 and "store broken" in err

    def test_replay_skips_done_and_exhausted(self, tmp_tasks_db, monkeypatch):
        """done 与 attempts 超上限的任务不重放。"""
        import sqlite3
        tid1 = mt.enqueue_memory_task("u1", "t1", "q1", {})
        mt.mark_memory_task_done(tid1)
        tid2 = mt.enqueue_memory_task("u1", "t1", "q2", {})
        conn = sqlite3.connect(tmp_tasks_db)
        try:
            conn.execute("UPDATE memory_tasks SET attempts=? WHERE id=?", (mt.MAX_ATTEMPTS, tid2))
            conn.commit()
        finally:
            conn.close()

        calls = []

        async def fake_remember(user_id, query, snapshot, thread_id=""):
            calls.append(query)

        monkeypatch.setattr("app.utils.memory_store.remember_from_session", fake_remember)
        n = asyncio.run(mt.replay_pending_memory_tasks())
        assert n == 0 and calls == []

    def test_replay_fail_open_when_db_broken(self, tmp_tasks_db, monkeypatch):
        monkeypatch.setattr(mt, "_connect",
                            lambda: (_ for _ in ()).throw(RuntimeError("db unavailable")))
        assert asyncio.run(mt.replay_pending_memory_tasks()) == 0

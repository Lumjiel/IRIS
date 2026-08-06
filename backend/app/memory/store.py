import sqlite3
import json
import os
import threading
from typing import List, Optional
from app.memory.models import MemoryRecord
from app.config import MEMORY_DB
from app.utils.logger import get_logger

log = get_logger("memory_store")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    thread_id TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_CREATE_INDEX_KIND = "CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)"
_CREATE_INDEX_THREAD = "CREATE INDEX IF NOT EXISTS idx_memories_thread_id ON memories(thread_id)"


class MemoryStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or MEMORY_DB
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            conn = sqlite3.connect(self.db_path, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute(_CREATE_TABLE)
        conn.execute(_CREATE_INDEX_KIND)
        conn.execute(_CREATE_INDEX_THREAD)
        conn.commit()

    @staticmethod
    def _row_to_record(row: tuple) -> MemoryRecord:
        return MemoryRecord(
            id=row[0],
            kind=row[1],
            content=row[2],
            thread_id=row[3],
            metadata=json.loads(row[4]) if row[4] else {},
            created_at=row[5],
            updated_at=row[6],
        )

    def add(self, kind: str, content: str, thread_id: Optional[str] = None, metadata: Optional[dict] = None) -> MemoryRecord:
        record = MemoryRecord(kind=kind, content=content, thread_id=thread_id, metadata=metadata or {})
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO memories (id, kind, content, thread_id, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record.id, record.kind, record.content, record.thread_id, json.dumps(record.metadata, ensure_ascii=False), record.created_at, record.updated_at),
        )
        conn.commit()
        log.info(f"记忆写入: [{record.kind}] id={record.id[:8]}")
        return record

    def search(self, query: str, kind: Optional[str] = None, limit: int = 10) -> List[MemoryRecord]:
        conn = self._get_conn()
        if kind:
            rows = conn.execute(
                "SELECT id, kind, content, thread_id, metadata, created_at, updated_at FROM memories WHERE kind = ? AND content LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (kind, f"%{query}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, kind, content, thread_id, metadata, created_at, updated_at FROM memories WHERE content LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def list_by_kind(self, kind: str, limit: int = 50) -> List[MemoryRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, kind, content, thread_id, metadata, created_at, updated_at FROM memories WHERE kind = ? ORDER BY updated_at DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, kind, content, thread_id, metadata, created_at, updated_at FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        return self._row_to_record(row) if row else None

    def delete(self, memory_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            log.info(f"记忆删除: id={memory_id[:8]}")
        return deleted

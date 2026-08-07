import sqlite3
import json
import math
import os
import threading
from typing import List, Optional, Tuple

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
    embedding TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_CREATE_INDEX_KIND = "CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)"
_CREATE_INDEX_THREAD = "CREATE INDEX IF NOT EXISTS idx_memories_thread_id ON memories(thread_id)"

# 语义检索候选上限（个人规模 DB 足够；避免全表扫描失控）
_SEM_CANDIDATE_LIMIT = 300

# 嵌入模型缓存（懒加载，避免模块级硬依赖 langchain_community/rag.engine）
_embeddings = None


def _get_embeddings():
    """懒加载 DashScope 嵌入模型。失败返回 None（搜索回退关键词）。

    直接使用 langchain_community 的 DashScopeEmbeddings，避免依赖重型 RAG 引擎
    （chromadb/huggingface）——记忆嵌入只做单条文本向量化，与向量库解耦。
    """
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    try:
        from langchain_community.embeddings import DashScopeEmbeddings
        _embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    except Exception as e:
        log.debug(f"嵌入模型加载失败，记忆检索回退关键词: {e}")
        _embeddings = None
    return _embeddings


def _embed(text: str) -> Optional[List[float]]:
    """对单条文本求嵌入向量。失败返回 None。"""
    try:
        emb = _get_embeddings()
        if emb is None:
            return None
        vec = emb.embed_query((text or "")[:1000])
        return [float(x) for x in vec]
    except Exception as e:
        log.debug(f"embedding 计算失败: {e}")
        return None


def _cosine(a: Optional[List[float]], b: Optional[List[float]]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


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
        # 迁移：老库无 embedding 列时补上
        cols = [r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()]
        if "embedding" not in cols:
            conn.execute("ALTER TABLE memories ADD COLUMN embedding TEXT DEFAULT NULL")
        conn.commit()

    @staticmethod
    def _row_to_record(row: tuple) -> MemoryRecord:
        # (id, kind, content, thread_id, metadata, created_at, updated_at, [embedding])
        return MemoryRecord(
            id=row[0],
            kind=row[1],
            content=row[2],
            thread_id=row[3],
            metadata=json.loads(row[4]) if row[4] else {},
            created_at=row[5],
            updated_at=row[6],
        )

    @staticmethod
    def _fetch_cols() -> str:
        return "id, kind, content, thread_id, metadata, created_at, updated_at"

    def add(self, kind: str, content: str, thread_id: Optional[str] = None, metadata: Optional[dict] = None) -> MemoryRecord:
        record = MemoryRecord(kind=kind, content=content, thread_id=thread_id, metadata=metadata or {})
        emb = _embed(content)
        emb_json = json.dumps(emb) if emb else None
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO memories (id, kind, content, thread_id, metadata, embedding, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (record.id, record.kind, record.content, record.thread_id,
             json.dumps(record.metadata, ensure_ascii=False), emb_json,
             record.created_at, record.updated_at),
        )
        conn.commit()
        log.info(f"记忆写入: [{record.kind}] id={record.id[:8]} (embedding={'有' if emb else '无'})")
        return record

    def search(self, query: str, kind: Optional[str] = None, limit: int = 10) -> List[MemoryRecord]:
        """混合检索：关键词(LIKE) + 语义(余弦)。语义失败时无损回退到关键词。

        - 关键词命中给 1.0 基础分
        - 语义相似度给 0-1 分
        - 两者取该记录的最终得分（取 max），按得分降序返回 top `limit`
        """
        # 空查询：直接返回最近记录（后端列表语义）
        if not (query or "").strip():
            return self.list_by_kind(kind, limit=limit) if kind else self._recent(limit)

        conn = self._get_conn()
        limit_cap = max(limit, _SEM_CANDIDATE_LIMIT)
        if kind:
            rows = conn.execute(
                f"SELECT {self._fetch_cols()}, embedding FROM memories WHERE kind = ? ORDER BY updated_at DESC LIMIT ?",
                (kind, limit_cap),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {self._fetch_cols()}, embedding FROM memories ORDER BY updated_at DESC LIMIT ?",
                (limit_cap,),
            ).fetchall()

        q_lower = (query or "").lower()
        q_vec = _embed(query)

        # 合并打分：id -> (score, record)
        merged: dict[str, Tuple[float, MemoryRecord]] = {}
        for row in rows:
            rec = self._row_to_record(row)
            score = 0.0
            if q_lower and q_lower in rec.content.lower():
                score = max(score, 1.0)
            if q_vec:
                try:
                    emb = json.loads(row[7]) if row[7] else None
                except (json.JSONDecodeError, IndexError):
                    emb = None
                if emb:
                    sim = _cosine(q_vec, emb)
                    score = max(score, sim)
            if score > 0:
                merged[rec.id] = (score, rec)

        ranked = sorted(merged.values(), key=lambda x: x[0], reverse=True)
        return [rec for _, rec in ranked[:limit]]

    def _recent(self, limit: int = 10) -> List[MemoryRecord]:
        """返回最近写入的 limit 条记忆（跨类型）。"""
        conn = self._get_conn()
        rows = conn.execute(
            f"SELECT {self._fetch_cols()} FROM memories ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def list_by_kind(self, kind: str, limit: int = 50) -> List[MemoryRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            f"SELECT {self._fetch_cols()} FROM memories WHERE kind = ? ORDER BY updated_at DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        conn = self._get_conn()
        row = conn.execute(
            f"SELECT {self._fetch_cols()} FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        return self._row_to_record(row) if row else None

    def update(self, memory_id: str, content: Optional[str] = None, kind: Optional[str] = None) -> Optional[MemoryRecord]:
        existing = self.get(memory_id)
        if existing is None:
            return None
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        new_content = content if content is not None else existing.content
        new_kind = kind if kind is not None else existing.kind
        emb = _embed(new_content)
        emb_json = json.dumps(emb) if emb else None
        conn = self._get_conn()
        conn.execute(
            "UPDATE memories SET content = ?, kind = ?, embedding = ?, updated_at = ? WHERE id = ?",
            (new_content, new_kind, emb_json, now, memory_id),
        )
        conn.commit()
        log.info(f"记忆更新: id={memory_id[:8]}")
        return self.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            log.info(f"记忆删除: id={memory_id[:8]}")
        return deleted
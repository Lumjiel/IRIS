from typing import List, Optional
from app.memory.models import MemoryRecord
from app.memory.store import MemoryStore
from app.utils.logger import get_logger

log = get_logger("memory_extractor")

_store: Optional[MemoryStore] = None


def _get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def extract_memories(
    query: str,
    plan: List[str],
    report: str,
    thread_id: Optional[str] = None,
    preferences: Optional[dict] = None,
) -> List[MemoryRecord]:
    store = _get_store()
    records: List[MemoryRecord] = []

    summary = report[:300] if report else ""
    record = store.add(
        kind="episodic",
        content=f"研究主题: {query}。搜索方向: {', '.join(plan)}。报告摘要: {summary}",
        thread_id=thread_id,
        metadata={"query": query, "plan": plan, "summary_length": len(report)},
    )
    records.append(record)

    if preferences:
        prefs_text = ", ".join(f"{k}={v}" for k, v in preferences.items() if v)
        if prefs_text:
            record = store.add(
                kind="semantic",
                content=f"用户偏好: {prefs_text}",
                thread_id=thread_id,
                metadata={"preferences": preferences},
            )
            records.append(record)

    if plan:
        record = store.add(
            kind="procedural",
            content=f"成功的搜索模式: 主题={query}, 方向={', '.join(plan)}",
            thread_id=thread_id,
            metadata={"query": query, "plan": plan},
        )
        records.append(record)

    log.info(f"记忆提取完成: {len(records)} 条 (query={query[:30]})")
    return records


def search_memories(query: str, kind: Optional[str] = None, limit: int = 10) -> List[dict]:
    store = _get_store()
    records = store.search(query, kind=kind, limit=limit)
    return [r.to_dict() for r in records]

"""后台记忆写入任务的落盘保护：任务表 + 启动扫描重放。

背景（1.9 交底的活坑，2026-11-20 补上）：remember_from_session 是进程内
asyncio task，进程在 task 完成前死掉（重启/崩溃），这一轮的记忆抽取动作
就丢了——原料（query + 终态快照）在 checkpoint 里活着，丢的是动作。

机制：
- SSE 收尾、create_task 之前先同步落一条 pending 任务（memory_tasks.db，
  与 checkpoint/store 两库再隔离一个文件，单写方无竞争）
- task 完成回调收账：无错 → done；意外异常 → attempts+1 保留 pending
- 应用启动扫描 pending 重放（remember_from_session 内部 fail-open 不抛；
  幂等仅覆盖 watch:{code} 确定性 key——uuid 类在收账失败窗口内重放会重复）
- fail-open 双向：任务表打不开不阻塞记忆写入（退回原无保护行为）；
  重放失败累计超 MAX_ATTEMPTS 后被重放查询过滤（status 仍 pending，非 dead），防毒任务每轮重试
"""
import json
import sqlite3
from typing import Any, Dict, Optional

from app.config import MEMORY_TASKS_DB
from app.utils.logger import get_logger

log = get_logger("memory_tasks")

MAX_ATTEMPTS = 5

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    thread_id TEXT NOT NULL DEFAULT '',
    query TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
)
"""


def _connect() -> sqlite3.Connection:
    """短命连接，随用随关（与记忆写入的短命 store 上下文同策略）。"""
    conn = sqlite3.connect(MEMORY_TASKS_DB, timeout=5)
    conn.execute(_SCHEMA)  # 建表幂等：首次使用即建，不等启动钩子
    return conn


def enqueue_memory_task(user_id: str, thread_id: str, query: str,
                        snapshot: Dict[str, Any]) -> Optional[int]:
    """落账一条 pending 任务，返回任务 id；表打不开返回 None（fail-open）。"""
    try:
        conn = _connect()
        try:
            cur = conn.execute(
                "INSERT INTO memory_tasks (user_id, thread_id, query, snapshot) VALUES (?, ?, ?, ?)",
                (user_id, thread_id, query, json.dumps(snapshot, ensure_ascii=False)))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    except Exception as e:
        log.warning(f"[MemoryTasks] 任务落账失败（fail-open，退回无保护行为）: {e}")
        return None


def mark_memory_task_done(task_id: int, error: str = "") -> None:
    """task 完成回调收账：无错 → done；有错 → attempts+1 保留 pending 供启动重放。"""
    try:
        conn = _connect()
        try:
            if error:
                conn.execute(
                    "UPDATE memory_tasks SET attempts = attempts + 1, last_error = ? WHERE id = ?",
                    (error[:500], task_id))
            else:
                conn.execute(
                    "UPDATE memory_tasks SET status = 'done', finished_at = datetime('now') WHERE id = ?",
                    (task_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log.warning(f"[MemoryTasks] 任务收账失败（task_id={task_id}，留 pending 待重放）: {e}")


async def replay_pending_memory_tasks() -> int:
    """启动扫描：重放未完成的记忆任务。返回成功重放条数。"""
    from app.utils.memory_store import remember_from_session  # 延迟导入防循环依赖

    try:
        conn = _connect()
    except Exception as e:
        log.warning(f"[MemoryTasks] 启动扫描失败（任务表不可用）: {e}")
        return 0
    try:
        rows = conn.execute(
            "SELECT id, user_id, thread_id, query, snapshot FROM memory_tasks "
            "WHERE status = 'pending' AND attempts < ? ORDER BY id",
            (MAX_ATTEMPTS,)).fetchall()
    finally:
        conn.close()
    if not rows:
        return 0
    log.info(f"[MemoryTasks] 启动扫描：{len(rows)} 条未完成记忆任务待重放")
    n_ok = 0
    for tid, user_id, thread_id, query, snapshot in rows:
        try:
            # 重放直接调会话入口（不经 routes，不会重复落账）；
            # remember_from_session 全链 fail-open 不抛，watch:{code} 幂等 upsert
            await remember_from_session(user_id, query, json.loads(snapshot), thread_id=thread_id)
            mark_memory_task_done(tid)
            n_ok += 1
        except Exception as e:
            mark_memory_task_done(tid, error=f"{type(e).__name__}: {e}")
    log.info(f"[MemoryTasks] 重放完成 {n_ok}/{len(rows)}")
    return n_ok

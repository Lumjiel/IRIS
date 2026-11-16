"""情景推演存档层：SQLite 持久化每次推演，支持历史回看与事后验证。

- 自动存档：analyze 流水线结束时调用 save_run
- 事后验证：verify 结果（推演日至今各标的实际涨跌）回写 verify 字段
- 全部操作 fail-soft：存档失败不影响推演主流程
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.config import SCENARIO_DB
from app.utils.logger import get_logger

log = get_logger("scenario_store")

_TABLE = """
CREATE TABLE IF NOT EXISTS scenario_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    scenario    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    verify      TEXT,
    verified_at TEXT
)
"""

_WATCHLIST = """
CREATE TABLE IF NOT EXISTS watchlist (
    code      TEXT PRIMARY KEY,
    name      TEXT NOT NULL DEFAULT '',
    added_at  TEXT NOT NULL
)
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(SCENARIO_DB, timeout=10)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(_TABLE)  # IF NOT EXISTS，懒建表
        conn.execute(_WATCHLIST)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_run(scenario: str, payload: dict) -> int | None:
    """存档一次推演，返回 run_id；失败返回 None（不抛异常）。"""
    try:
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO scenario_runs (created_at, scenario, payload) VALUES (?, ?, ?)",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    scenario,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            return cur.lastrowid
    except Exception as e:
        log.error(f"推演存档失败: {e}")
        return None


def list_runs(limit: int = 50) -> list[dict]:
    """历史列表（倒序，摘要字段）。"""
    try:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT id, created_at, scenario, payload, verified_at FROM scenario_runs "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for rid, created, scenario, payload, verified_at in rows:
            try:
                data = json.loads(payload)
                impacts = data.get("impacts", [])
            except json.JSONDecodeError:
                impacts = []
            out.append({
                "id": rid,
                "created_at": created,
                "scenario": scenario,
                "impact_count": len(impacts),
                "top_impact": impacts[0] if impacts else None,
                "verified": verified_at is not None,
            })
        return out
    except Exception as e:
        log.error(f"历史列表读取失败: {e}")
        return []


def get_run(run_id: int) -> dict | None:
    """单条详情，含完整 payload；不存在返回 None。"""
    try:
        with _conn() as conn:
            row = conn.execute(
                "SELECT id, created_at, scenario, payload, verify, verified_at "
                "FROM scenario_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        rid, created, scenario, payload, verify, verified_at = row
        return {
            "id": rid,
            "created_at": created,
            "scenario": scenario,
            "payload": json.loads(payload),
            "verify": json.loads(verify) if verify else None,
            "verified_at": verified_at,
        }
    except Exception as e:
        log.error(f"推演详情读取失败[{run_id}]: {e}")
        return None


def delete_run(run_id: int) -> bool:
    try:
        with _conn() as conn:
            conn.execute("DELETE FROM scenario_runs WHERE id = ?", (run_id,))
        return True
    except Exception as e:
        log.error(f"推演删除失败[{run_id}]: {e}")
        return False


def save_verification(run_id: int, verify_payload: dict) -> bool:
    """回写事后验证结果。"""
    try:
        with _conn() as conn:
            conn.execute(
                "UPDATE scenario_runs SET verify = ?, verified_at = ? WHERE id = ?",
                (
                    json.dumps(verify_payload, ensure_ascii=False),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    run_id,
                ),
            )
        return True
    except Exception as e:
        log.error(f"验证结果回写失败[{run_id}]: {e}")
        return False


# ============ 自选股对照 ============

def watchlist_add(code: str, name: str = "") -> bool:
    """添加自选股（已存在则更新名称，幂等）。"""
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO watchlist (code, name, added_at) VALUES (?, ?, ?) "
                "ON CONFLICT(code) DO UPDATE SET name = excluded.name",
                (code, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
        return True
    except Exception as e:
        log.error(f"自选股添加失败[{code}]: {e}")
        return False


def watchlist_remove(code: str) -> bool:
    try:
        with _conn() as conn:
            conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        return True
    except Exception as e:
        log.error(f"自选股删除失败[{code}]: {e}")
        return False


def watchlist_list() -> list[dict]:
    """自选股列表（按加入时间倒序）。"""
    try:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT code, name, added_at FROM watchlist ORDER BY added_at DESC"
            ).fetchall()
        return [{"code": c, "name": n, "added_at": a} for c, n, a in rows]
    except Exception as e:
        log.error(f"自选股读取失败: {e}")
        return []

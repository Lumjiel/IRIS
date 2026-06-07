from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import List
from app.graph.graph import create_graph
import json
import asyncio
import os
import glob
import time
import random
import shutil
from app.rag.engine import process_documents, reset_knowledge_base, UPLOAD_DIR
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.utils.logger import get_logger
from app.config import CHECKPOINT_MAX_AGE_DAYS, MAX_UPLOAD_FILES, MAX_FILE_SIZE_MB, CREATION_DIR, CHECKPOINT_DB, STORE_DB

log = get_logger("routes")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = CHECKPOINT_DB
router = APIRouter()


def _read_checkpoint_state(thread_id: str) -> dict | None:
    """从 SQLite checkpoint 中读取最新的 channel_values（msgpack 格式）"""
    import sqlite3, msgpack
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        row = conn.execute(
            "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
            (thread_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        checkpoint = msgpack.unpackb(row[0], raw=False)
        return checkpoint.get("channel_values", {})
    except Exception as e:
        log.debug(f"读取 checkpoint 失败: {e}")
        return None


def _reset_checkpoint_summary(thread_id: str) -> bool:
    """将 checkpoint 中的 conversation_summary 清空（msgpack 格式）"""
    import sqlite3, msgpack
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        row = conn.execute(
            "SELECT checkpoint_id, checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
            (thread_id,)
        ).fetchone()
        if not row:
            conn.close()
            return False
        ckpt_id, checkpoint_blob = row
        checkpoint = msgpack.unpackb(checkpoint_blob, raw=False)
        channel_values = checkpoint.get("channel_values", {})
        if "conversation_summary" in channel_values:
            channel_values["conversation_summary"] = ""
        checkpoint["channel_values"] = channel_values
        conn.execute(
            "UPDATE checkpoints SET checkpoint = ? WHERE checkpoint_id = ?",
            (msgpack.packb(checkpoint, use_bin_type=True), ckpt_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.warning(f"重置 checkpoint 摘要失败: {e}")
        return False


def cleanup_old_checkpoints(max_age_days: int = 7):
    """清理过期的会话检查点，防止 SQLite 文件无限增长"""
    try:
        import sqlite3
        if not os.path.exists(DB_PATH):
            return
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        if 'checkpoints' in tables:
            cutoff = int((time.time() - max_age_days * 86400) * 1000)
            cursor.execute("DELETE FROM checkpoints WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            if deleted:
                log.info(f"清理了 {deleted} 条过期检查点")
        conn.close()
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            log.debug("数据库被占用，跳过清理")
        else:
            log.warning(f"清理检查点时出错: {e}")
    except Exception as e:
        log.warning(f"清理检查点时出错: {e}")


# --- SQLite 共享限流（多 worker 安全） ---
class RateLimiter:
    """基于 SQLite 的滑动窗口限流器，多 worker 进程共享状态。"""

    def __init__(self, db_path: str, max_requests: int = 5, window_seconds: int = 60):
        self.db_path = db_path
        self.max_requests = max_requests
        self.window = window_seconds
        self._init_db()

    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                key TEXT NOT NULL,
                ts REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key_ts ON rate_limits(key, ts)")
        conn.commit()
        conn.close()

    def is_allowed(self, key: str) -> bool:
        import sqlite3
        now = time.time()
        cutoff = now - self.window
        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            # 清理过期记录
            conn.execute("DELETE FROM rate_limits WHERE ts < ?", (cutoff,))
            # 统计当前窗口内的请求数
            row = conn.execute("SELECT COUNT(*) FROM rate_limits WHERE key = ? AND ts >= ?", (key, cutoff)).fetchone()
            count = row[0] if row else 0
            if count >= self.max_requests:
                conn.close()
                return False
            conn.execute("INSERT INTO rate_limits (key, ts) VALUES (?, ?)", (key, now))
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError:
            return True  # 数据库锁定时放行

# 每个 IP 每分钟最多 5 次研究请求
chat_limiter = RateLimiter(db_path=CHECKPOINT_DB, max_requests=5, window_seconds=60)


class ChatRequest(BaseModel):
    query: str
    search_mode: str = "hybrid"
    thread_id: str
    style: str = "detailed"       # detailed / concise / formal / casual
    language: str = "zh"          # zh / en

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        if len(v) > 2000:
            raise ValueError("研究主题不能超过 2000 字")
        return v             

@router.post("/clear")
async def clear_endpoint():
    try:
        reset_knowledge_base() 
        return {"message": "知识库已重置", "status": "success"}
    except Exception as e:
        log.error(f"清空失败: {e}")
        return {"message": f"清空失败: {str(e)}", "status": "error"}

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    批量上传接口
    """

    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"一次最多只能上传 {MAX_UPLOAD_FILES} 个文件")

    # 先验证所有文件，再执行破坏性操作
    file_contents = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"仅支持 PDF 文件: {file.filename}")
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 超过 {MAX_FILE_SIZE_MB}MB 限制")
        file_contents.append((file.filename, content))

    try:
        reset_knowledge_base()

        saved_paths = []
        for filename, content in file_contents:
            safe_name = os.path.basename(filename)
            file_path = os.path.join(UPLOAD_DIR, safe_name)
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            saved_paths.append(file_path)


        chunks_num = process_documents(saved_paths)

        if chunks_num == 0:
            raise HTTPException(status_code=400, detail="文档解析失败，请检查 PDF 文件是否损坏或缺少 pypdf 依赖")

        # 清理旧文件，防止磁盘爆满
        cleanup_old_uploads(max_age_hours=24)

        return {
            "status": "success",
            "file_count": len(files),
            "chunks_stored": chunks_num,
            "message": "文档解析完成，知识库构建成功"
        }
    except HTTPException:
        raise  # 重新抛出 HTTP 异常
    except Exception as e:
        log.error(f"上传处理失败: {e}")
        raise HTTPException(status_code=500, detail="文档处理失败，请检查文件格式后重试")

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, req: Request):
    # 限流检查
    client_ip = req.client.host if req.client else "unknown"
    if not chat_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="请求太频繁，请稍后再试（每分钟最多 5 次）")

    # 低概率触发检查点清理（避免每次请求都清理）
    if random.random() < 0.1:
        cleanup_old_checkpoints(max_age_days=CHECKPOINT_MAX_AGE_DAYS)

    config = {"configurable": {"thread_id": request.thread_id}}
    async def event_generator():
        try:
            initial_state = {
                "query": request.query,
                "revision_number": 0,
                "search_mode": request.search_mode,
                "preferences": {"style": request.style, "language": request.language},
                # 以下字段必须重置，防止上一轮 session 的残留数据泄漏
                "plan": [],
                "search_results": [],
                "critique": "",
                "review_status": "PASS",
                "should_stop": False,
                # final_report 不重置：router 需要判断是否有已有报告来决定路由
                # conversation_summary 不重置：由 checkpoint 持久化，跨轮保持
            }

            log.info(f"新任务开启 | 模式: {request.search_mode} | 问题: {request.query}")

            async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:
                app = create_graph(memory=memory)

                from app.utils.streaming import set_token_queue
                token_queue: asyncio.Queue = asyncio.Queue()
                set_token_queue(token_queue)

                graph_queue: asyncio.Queue = asyncio.Queue()

                async def _run_graph():
                    try:
                        async for event in app.astream(initial_state, config=config):
                            for node_name, state_update in event.items():
                                ev = json.dumps({"step": node_name, "data": state_update}, ensure_ascii=False)
                                await graph_queue.put(ev)
                    except Exception as e:
                        log.error(f"Graph error: {type(e).__name__}: {e}", exc_info=True)
                        await graph_queue.put(json.dumps({"step": "error", "data": {"message": f"研究过程中发生错误: {type(e).__name__}: {e}"}}, ensure_ascii=False))
                    finally:
                        await graph_queue.put(None)

                graph_task = asyncio.create_task(_run_graph())

                graph_finished = False
                while not graph_finished:
                    had_work = False
                    while True:
                        try:
                            tok = token_queue.get_nowait()
                            yield f"data: {json.dumps(tok, ensure_ascii=False)}\n\n"
                            had_work = True
                        except asyncio.QueueEmpty:
                            break

                    try:
                        g_ev = graph_queue.get_nowait()
                        if g_ev is None:
                            graph_finished = True
                        else:
                            yield f"data: {g_ev}\n\n"
                            had_work = True
                    except asyncio.QueueEmpty:
                        pass

                    if not had_work:
                        await asyncio.sleep(0.01)

                while True:
                    try:
                        tok = token_queue.get_nowait()
                        yield f"data: {json.dumps(tok, ensure_ascii=False)}\n\n"
                    except asyncio.QueueEmpty:
                        break

        except Exception as e:
            log.error(f"[SSE] 流式传输异常: {e}")
            error_data = json.dumps({"step": "error", "data": {"message": "研究过程中发生错误，请重试"}}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        finally:
            from app.utils.streaming import set_token_queue
            set_token_queue(None)
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- 会话记忆管理 ---
@router.get("/memory/{thread_id}")
async def get_memory(thread_id: str):
    """获取指定会话的对话摘要"""
    state = _read_checkpoint_state(thread_id)
    if state is None:
        return {"summary": "", "turns": 0, "searched_directions": [], "summary_length": 0, "summary_max": 2000}
    summary = state.get("conversation_summary", "")
    # 从摘要中提取已搜索的方向（格式: "搜索方向: X、Y、Z"）
    import re
    searched = re.findall(r"搜索方向: (.+)", summary)
    turns = len(searched) if searched else (1 if summary else 0)
    return {
        "summary": summary,
        "turns": turns,
        "searched_directions": [d.strip() for d in searched] if searched else [],
        "summary_length": len(summary),
        "summary_max": 2000,
    }


@router.post("/memory/{thread_id}/reset")
async def reset_memory(thread_id: str):
    """清空指定会话的对话摘要（保留 final_report）"""
    ok = _reset_checkpoint_summary(thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在或无摘要")
    return {"status": "success", "message": "对话记忆已清空"}


# --- AI HOT 新闻代理 ---
import httpx

AIHOT_BASE = "https://aihot.virxact.com"
AIHOT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

@router.get("/aihot/news")
async def aihot_news(mode: str = "selected", take: int = 20, q: str = None):
    """代理 AI HOT API，避免前端 CORS 问题"""
    params = {"mode": mode, "take": take}
    if q:
        params["q"] = q
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{AIHOT_BASE}/api/public/items",
                params=params,
                headers={"User-Agent": AIHOT_UA}
            )
            resp.raise_for_status()
            data = resp.json()
            # 打乱顺序，让「换一批」每次显示不同内容
            if "items" in data:
                random.shuffle(data["items"])
            return data
    except Exception as e:
        log.error(f"AI HOT 请求失败: {e}")
        raise HTTPException(status_code=502, detail="AI 资讯服务暂时不可用")


# --- 保存报告到创作目录 ---
class SaveReportRequest(BaseModel):
    query: str
    report: str
    watermark: bool = True


def cleanup_old_uploads(max_age_hours: int = 24):
    """清理超过指定时间的上传文件，防止磁盘爆满"""
    try:
        if not os.path.exists(UPLOAD_DIR):
            return
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        removed = 0
        for f in glob.glob(os.path.join(UPLOAD_DIR, "*")):
            if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                os.remove(f)
                removed += 1
        if removed:
            log.info(f"清理了 {removed} 个过期上传文件")
    except Exception as e:
        log.warning(f"清理上传文件时出错: {e}")

@router.post("/save-report")
async def save_report(request: SaveReportRequest):
    """将调研报告保存到创作目录"""
    try:
        os.makedirs(CREATION_DIR, exist_ok=True)

        # 生成文件名
        safe_query = "".join(c for c in request.query if c.isalnum() or c in "一二三四五六七八九十百千万亿年月日时分秒AI")
        safe_query = safe_query[:40] or "调研报告"
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}-{safe_query}.md"
        filepath = os.path.join(CREATION_DIR, filename)

        # 追加水印
        content = request.report
        if request.watermark:
            content += "\n\n---\n*由 IRIS 智能调研系统生成 | 寻阶行*\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        log.info(f"报告已保存: {filepath}")
        return {"status": "success", "path": filepath, "filename": filename}
    except Exception as e:
        log.error(f"保存报告失败: {e}")
        raise HTTPException(status_code=500, detail="保存失败")


@router.get("/materials")
async def list_materials():
    """列出素材库中已保存的报告"""
    try:
        if not os.path.exists(CREATION_DIR):
            return {"items": []}
        items = []
        for f in sorted(glob.glob(os.path.join(CREATION_DIR, "*.md")), reverse=True):
            stat = os.stat(f)
            name = os.path.basename(f)
            items.append({
                "filename": name,
                "path": f,
                "size": stat.st_size,
                "mtime": int(stat.st_mtime * 1000),
            })
        return {"items": items}
    except Exception as e:
        log.error(f"列出素材失败: {e}")
        return {"items": []}


@router.delete("/materials/{filename}")
async def delete_material(filename: str):
    """删除素材库中的报告"""
    filepath = os.path.join(CREATION_DIR, filename)
    if not os.path.exists(filepath) or not filepath.startswith(CREATION_DIR):
        raise HTTPException(status_code=404, detail="文件不存在")
    os.remove(filepath)
    return {"status": "success"}


@router.get("/materials/{filename}")
async def get_material(filename: str):
    """读取单个素材内容"""
    filepath = os.path.join(CREATION_DIR, filename)
    if not os.path.exists(filepath) or not filepath.startswith(CREATION_DIR):
        raise HTTPException(status_code=404, detail="文件不存在")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": filename, "content": content}
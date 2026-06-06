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
from collections import defaultdict
from app.rag.engine import process_documents, reset_knowledge_base, UPLOAD_DIR
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.utils.logger import get_logger
from app.config import CHECKPOINT_MAX_AGE_DAYS, MAX_UPLOAD_FILES, MAX_FILE_SIZE_MB, CREATION_DIR, CHECKPOINT_DB

log = get_logger("routes")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = CHECKPOINT_DB
router = APIRouter()


def cleanup_old_checkpoints(max_age_days: int = 7):
    """清理过期的会话检查点，防止 SQLite 文件无限增长"""
    try:
        import sqlite3
        if not os.path.exists(DB_PATH):
            return
        conn = sqlite3.connect(DB_PATH)
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
                cursor.execute("VACUUM")
        conn.close()
    except Exception as e:
        log.warning(f"清理检查点时出错: {e}")


# --- 简单内存限流 ---
class RateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)

        # 每 5 分钟清理一次过期 IP
        if now - self._last_cleanup > 300:
            self._cleanup(cutoff)
            self._last_cleanup = now
        return True

    def _cleanup(self, cutoff: float):
        empty_keys = [k for k, v in self._requests.items() if not v or v[-1] < cutoff]
        for k in empty_keys:
            del self._requests[k]

# 每个 IP 每分钟最多 5 次研究请求
chat_limiter = RateLimiter(max_requests=5, window_seconds=60)


class ChatRequest(BaseModel):
    query: str
    search_mode: str = "hybrid"
    thread_id: str

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
                "search_mode": request.search_mode
            }

            log.info(f"新任务开启 | 模式: {request.search_mode} | 问题: {request.query}")

            async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:
                app = create_graph(memory=memory)

                async for event in app.astream(initial_state, config=config):
                     for node_name, state_update in event.items():
                        data = json.dumps({"step": node_name, "data": state_update}, ensure_ascii=False)
                        yield f"data: {data}\n\n"
                        await asyncio.sleep(0.1)
        except Exception as e:
            log.error(f"[SSE] 流式传输异常: {e}")
            error_data = json.dumps({"step": "error", "data": {"message": "研究过程中发生错误，请重试"}}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
            return resp.json()
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
        safe_query = "".join(c for c in request.query if c.isalnum() or c in "一二三四五六七八九十百千万亿年月日时分秒AI").
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
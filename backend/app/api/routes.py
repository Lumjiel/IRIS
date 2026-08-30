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
from app.tools.akshare_tools import query_stock_info, query_financial_indicators, query_stock_quote, query_stock_news

log = get_logger("routes")

# 后台长期记忆写入任务的强引用集合（防止 task 被 GC 中途丢弃）
_background_mem_tasks: set = set()
from app.utils.memory_store import open_store

# 安全序列化：处理 AIMessage 等非 JSON 可序列化对象
def _safe_json_serialize(obj):
    """递归处理非 JSON 可序列化对象"""
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, (int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [_safe_json_serialize(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): _safe_json_serialize(v) for k, v in obj.items()}
    else:
        # AIMessage 等其他对象转为字符串
        return str(obj)

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
    """清理过期的会话检查点，防止 SQLite 文件无限增长。

    langgraph 的 checkpoints 表没有时间戳列，时间存在 checkpoint blob 的 ts 字段（ISO 字符串）。
    checkpoint_id 是 uuid6（按时间单调递增），因此每个线程只需解包最新一条 blob 判断过期；
    线程整体过期则删除其全部 checkpoints 及关联 writes（避免孤儿写入记录）。
    """
    import sqlite3
    import msgpack
    from datetime import datetime, timedelta, timezone
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH, timeout=5)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        stale_threads: list = []
        seen: set = set()
        # 最新优先遍历：每线程遇到的第一条即最新 checkpoint，只需解包这一条 blob
        for thread_id, blob in conn.execute(
            "SELECT thread_id, checkpoint FROM checkpoints ORDER BY checkpoint_id DESC"
        ):
            if thread_id in seen:
                continue
            seen.add(thread_id)
            try:
                ts = msgpack.unpackb(blob, raw=False).get("ts", "")
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if dt < cutoff:
                    stale_threads.append(thread_id)
            except Exception as e:
                log.debug("跳过无法解析的检查点 %s: %s", thread_id, e)
        if stale_threads:
            placeholders = ",".join("?" * len(stale_threads))
            cur = conn.execute(
                f"DELETE FROM checkpoints WHERE thread_id IN ({placeholders})", stale_threads
            )
            deleted = cur.rowcount
            conn.execute(
                f"DELETE FROM writes WHERE thread_id IN ({placeholders})", stale_threads
            )
            conn.commit()
            if deleted:
                log.info(f"清理了 {deleted} 条过期检查点（{len(stale_threads)} 个过期会话）")
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            log.debug("数据库被占用，跳过清理")
        else:
            log.warning(f"清理检查点时出错: {e}")
    except Exception as e:
        log.warning(f"清理检查点时出错: {e}")
    finally:
        conn.close()


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
        except sqlite3.OperationalError as e:
            # 限流存储故障时拒绝请求（fail-closed）：放行会让锁竞争成为绕过限流的通道
            log.warning(f"RateLimiter 存储异常，本次请求按限流拒绝（fail-closed）: {e}")
            return False

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

async def _pre_run_route(app, config: dict, query: str) -> tuple:
    """从 checkpoint 读已持久化的 final_report 并预跑意图路由（SSE 首事件用）。

    必须在 saver 上下文内、astream 之前调用。final_report 只能从 checkpoint 读——
    initial_state 里没有该字段（故意不重置以保留跨轮报告），从 initial_state 兜底
    永远得到空串，导致第二轮追问 has_report=False 被误判为 chat。

    返回 (route_result, has_report)。
    """
    from app.graph.nodes.router import route_query
    from app.graph.state import AgentState
    persisted_report = ""
    try:
        snap = await app.aget_state(config)
        if snap and snap.values:
            persisted_report = snap.values.get("final_report") or ""
    except Exception as e:
        log.warning(f"读取 checkpoint 状态失败，预跑路由按无报告处理: {e}")
    _route_state = AgentState(query=query, final_report=persisted_report)
    route_result = route_query(_route_state)
    return route_result, bool(persisted_report.strip())


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
    # 长期记忆用户标识：前端 localStorage UUID 随 X-User-Id header 携带，缺省 default
    user_id = req.headers.get("X-User-Id") or "default"

    async def event_generator():
        graph_task = None  # 断连时在 finally 中取消，避免后台僵尸研究任务白烧 LLM 额度
        try:
            initial_state = {
                "query": request.query,
                "user_id": user_id,  # 长期记忆：load_memories 按此读取用户背景
                "revision_number": 0,
                "search_mode": request.search_mode,
                "preferences": {"style": request.style, "language": request.language},
                # 以下字段必须重置，防止上一轮 session 的残留数据泄漏
                "plan": [],
                "search_results": [],
                "critique": "",
                "review_status": "PASS",
                "should_stop": False,
                "search_iteration": 0,  # Function Calling 循环计数重置
                # 错误/降级标志必须重置：LangGraph 会把输入合并进 checkpoint 持久化的线程状态，
                # 不显式重置的字段会残留上一轮的值（一次降级 → 后续每轮被强制打回 planner 重写）
                "error_code": "",
                "degraded": False,
                "failed_tools": [],
                "tool_status": {},
                "report_history": [],  # 防止旧报告触发 cosine 早停误判
                "financial_data": {},  # 上一只股票的数据不得泄漏进新查询
                "data_sources": [],
                "pending_stock_code": "",
                "error_log": [],
                # final_report 不重置：router 需要判断是否有已有报告来决定路由
                # conversation_summary 不重置：由 checkpoint 持久化，跨轮保持
            }
            log.info(f"新任务开启 | 模式: {request.search_mode} | 问题: {request.query}")


            async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory, \
                      open_store() as store:
                app = create_graph(memory=memory, store=store)

                # === 预跑路由（首事件 intent）：checkpoint 读取逻辑见 _pre_run_route ===
                _t_route = time.time()
                route_result, has_report = await _pre_run_route(app, config, request.query)
                route_elapsed = round(time.time() - _t_route, 2)
                # 映射到前端 intent: planner→research, refiner→refine, chat→chat
                INTENT_MAP = {"planner": "research", "refiner": "refine", "chat": "chat"}
                intent = INTENT_MAP.get(route_result, "chat")
                yield f"data: {json.dumps({'step': 'intent', 'data': {'intent': intent, 'route': route_result, 'elapsed': route_elapsed}}, ensure_ascii=False)}\n\n"
                log.info(f"意图判定: {intent} (route={route_result}, has_report={has_report})")
                # 预设路由结果：图入口的 route_query 直接复用，避免同一请求二次 LLM 意图分类
                initial_state["preset_route"] = route_result
                from app.utils.streaming import set_token_queue, set_node_event_queue
                token_queue: asyncio.Queue = asyncio.Queue()
                set_token_queue(token_queue)
                node_event_queue: asyncio.Queue = asyncio.Queue()
                set_node_event_queue(node_event_queue)

                graph_queue: asyncio.Queue = asyncio.Queue()

                async def _run_graph():
                    final_snapshot: dict = {}  # 会话终态快照（后台记忆写入用）
                    try:
                        async for event in app.astream(initial_state, config=config):
                            for node_name, state_update in event.items():
                                if isinstance(state_update, dict):
                                    final_snapshot.update(state_update)
                                safe_data = _safe_json_serialize(state_update)
                                ev = json.dumps({"step": node_name, "data": safe_data}, ensure_ascii=False, default=str)
                                await graph_queue.put(ev)
                    except Exception as e:
                        log.error(f"Graph error: {type(e).__name__}: {e}", exc_info=True)
                        await graph_queue.put(json.dumps({"step": "error", "data": {"message": f"研究过程中发生错误: {type(e).__name__}: {e}"}}, ensure_ascii=False))
                    finally:
                        # 后台长期记忆写入：规则+LLM 抽取 → 独立短命 store 上下文，不阻塞响应、
                        # 不依赖本请求的 store 连接（fail-open，失败只打日志）
                        from app.utils.memory_store import remember_from_session
                        mem_task = asyncio.create_task(
                            remember_from_session(user_id, request.query, final_snapshot,
                                                  thread_id=request.thread_id)
                        )
                        _background_mem_tasks.add(mem_task)
                        mem_task.add_done_callback(_background_mem_tasks.discard)
                        await graph_queue.put(None)

                graph_task = asyncio.create_task(_run_graph())

                graph_finished = False
                last_data_time = time.time()
                HEARTBEAT_INTERVAL = 15  # 秒

                while not graph_finished:
                    had_work = False
                    while True:
                        try:
                            tok = token_queue.get_nowait()
                            yield f"data: {json.dumps(tok, ensure_ascii=False)}\n\n"
                            had_work = True
                            last_data_time = time.time()
                        except asyncio.QueueEmpty:
                            break

                    try:
                        g_ev = graph_queue.get_nowait()
                        if g_ev is None:
                            graph_finished = True
                        else:
                            yield f"data: {g_ev}\n\n"
                            had_work = True
                            last_data_time = time.time()
                    except asyncio.QueueEmpty:
                        pass

                    # 节点状态事件（start/done + elapsed）
                    while True:
                        try:
                            n_ev = node_event_queue.get_nowait()
                            yield f"data: {json.dumps(n_ev, ensure_ascii=False)}\n\n"
                            had_work = True
                            last_data_time = time.time()
                        except asyncio.QueueEmpty:
                            break

                    if not had_work:
                        await asyncio.sleep(0.01)

                    # 心跳：防止 Nginx 等代理因空闲断开连接
                    if not had_work and time.time() - last_data_time > HEARTBEAT_INTERVAL:
                        yield ": heartbeat\n\n"
                        last_data_time = time.time()

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
            # 客户端断开（GeneratorExit）或异常时，取消仍在运行的研究任务
            if graph_task is not None and not graph_task.done():
                graph_task.cancel()
                log.info("[SSE] 客户端断开，已取消后台研究任务")
            from app.utils.streaming import set_token_queue, set_node_event_queue
            set_token_queue(None)
            set_node_event_queue(None)
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



# --- 长期记忆管理（方案 B） ---
@router.get("/memory-items")
async def list_memory_items(user_id: str):
    """列出该用户全部长期记忆（管理页/调试用）。"""
    from app.utils.memory_store import list_all_memories

    items = await list_all_memories(user_id)
    return {"status": "ok", "items": items, "count": len(items)}


@router.delete("/memory-items/{memory_key}")
async def delete_memory_item(memory_key: str, user_id: str):
    """删除单条长期记忆（红线操作，前端需二次确认）。"""
    from app.utils.memory_store import delete_memory

    ok = await delete_memory(user_id, memory_key)
    if not ok:
        raise HTTPException(status_code=500, detail="删除失败")
    return {"status": "success", "message": "记忆已删除"}

# --- 财经快讯（东财全球快讯，akshare + 5 分钟缓存） ---
_finnews_cache: dict = {"ts": 0.0, "items": []}
FINNEWS_TTL_S = 300

@router.get("/finnews")
async def finnews(take: int = 15):
    """东财全球财经快讯，供前端资讯横滚条；失败返回 502，前端回退 AI HOT"""
    now = time.time()
    if _finnews_cache["items"] and now - _finnews_cache["ts"] < FINNEWS_TTL_S:
        return {"items": _finnews_cache["items"][:take]}
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_info_global_em)
        items = []
        for _, row in df.head(30).iterrows():
            title = str(row.get("标题") or "").strip()
            if not title:
                title = str(row.get("摘要") or "").strip()[:50]
            if not title:
                continue
            url = str(row.get("链接") or "").strip()
            items.append({"title": title[:60], "url": url or None})
        if not items:
            raise RuntimeError("empty feed")
        _finnews_cache.update(ts=now, items=items)
        return {"items": items[:take]}
    except Exception as e:
        log.warning(f"财经快讯获取失败: {e}")
        raise HTTPException(status_code=502, detail="财经快讯暂时不可用")

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
    # 防路径穿越：解析真实路径后校验前缀
    filepath = os.path.realpath(os.path.join(CREATION_DIR, filename))
    if not os.path.exists(filepath) or not filepath.startswith(os.path.realpath(CREATION_DIR)):
        raise HTTPException(status_code=404, detail="文件不存在")
    os.remove(filepath)
    return {"status": "success"}


@router.get("/materials/{filename}")
async def get_material(filename: str):
    """读取单个素材内容"""
    # 防路径穿越：解析真实路径后校验前缀
    filepath = os.path.realpath(os.path.join(CREATION_DIR, filename))
    if not os.path.exists(filepath) or not filepath.startswith(os.path.realpath(CREATION_DIR)):
        raise HTTPException(status_code=404, detail="文件不存在")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": filename, "content": content}


# --- TTS 语音合成（CosyVoice） ---
class TTSRequest(BaseModel):
    text: str
    voice: str = "longtian_v3"

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if len(v) > 5000:
            raise ValueError("文本不能超过 5000 字")
        if not v.strip():
            raise ValueError("文本不能为空")
        return v


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """将文本转为语音（DashScope CosyVoice），返回音频流"""
    try:
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer

        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
        dashscope.base_websocket_api_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

        synthesizer = SpeechSynthesizer(model="cosyvoice-v3-flash", voice=request.voice)
        audio_data = synthesizer.call(request.text)

        if not audio_data:
            raise HTTPException(status_code=500, detail="语音合成失败")

        from fastapi.responses import Response
        return Response(content=bytes(audio_data), media_type="audio/mpeg")
    except ImportError:
        raise HTTPException(status_code=500, detail="dashscope 未安装，请 pip install dashscope")
    except Exception as e:
        log.error(f"TTS 合成失败: {e}")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

# ============================================================
# 股票查询 API（投研分析前端用）
# ============================================================

@router.get("/stock/{stock_code}/info")
async def get_stock_info(stock_code: str):
    """查询股票基本信息"""
    result = query_stock_info.invoke(stock_code)
    return json.loads(result)

@router.get("/stock/{stock_code}/financial")
async def get_financial(stock_code: str):
    """查询财务指标"""
    result = query_financial_indicators.invoke(stock_code)
    return json.loads(result)

@router.get("/stock/{stock_code}/quote")
async def get_quote(stock_code: str):
    """查询实时行情"""
    result = query_stock_quote.invoke(stock_code)
    return json.loads(result)


# ============================================================
# 个股新闻/公告（阶段 5 新增）
# ============================================================

@router.get("/stock/{stock_code}/news")
async def get_stock_news(stock_code: str):
    """查询个股新闻/公告"""
    result = query_stock_news.invoke(stock_code)
    return json.loads(result)


# ============================================================
# 行情页批量快照（移动端行情 Tab 轮询用）
# ============================================================

MARKET_INDEX_CODES = [
    {"code": "000001.SH", "name": "上证指数"},
    {"code": "399001.SZ", "name": "深证成指"},
    {"code": "399006.SZ", "name": "创业板指"},
]


@router.get("/market/snapshot")
async def market_snapshot(codes: str = ""):
    """三大指数 + 自选股批量实时快照。

    fail-open：任何一只失败不影响其他——错误进 errors 如实返回，绝不 500。
    指数走同花顺批量层；个股先批量，缺漏逐股落完整降级链（hithink→akshare→…）。
    """
    from app.tools import hithink_tools as ht

    raw = [c.strip() for c in codes.split(",") if c.strip()][:30]
    updated_at = int(time.time() * 1000)

    # 指数（仅同花顺层；akshare 链面向个股设计，指数失败则指数区为空不报错）
    indexes = []
    try:
        if ht.is_enabled():
            idx_map = await asyncio.to_thread(
                ht.fetch_quotes_batch, [i["code"] for i in MARKET_INDEX_CODES])
            for i in MARKET_INDEX_CODES:
                if i["code"] in idx_map:
                    indexes.append({"name": i["name"], **idx_map[i["code"]]})
    except Exception as e:
        log.warning(f"行情页指数获取失败（fail-open 跳过）: {e}")

    stocks, errors = [], []
    batch: dict = {}
    if raw and ht.is_enabled():
        try:
            batch = await asyncio.to_thread(ht.fetch_quotes_batch, raw)
        except Exception as e:
            log.warning(f"行情页批量获取失败，逐股降级: {e}")

    for code in raw:
        q = batch.get(code)
        if q:
            stocks.append(q)
            continue
        # 单股走完整降级链兜底；再失败只记 error，不炸整体响应
        try:
            result = json.loads(await asyncio.to_thread(query_stock_quote.invoke, code))
            if result.get("error"):
                raise RuntimeError(str(result.get("message") or "查询失败")[:120])
            stocks.append({"stock_code": code, **(result.get("quote") or {})})
        except Exception as e:
            errors.append({"code": code, "error": str(e)[:120]})

    # 批量行情缺换手率/PE/PB/总市值，腾讯行情一次性补齐（fail-open）
    try:
        from app.tools.akshare_tools import _tencent_quote_supplement_batch
        supplements = await asyncio.to_thread(
            _tencent_quote_supplement_batch, [s.get("stock_code") for s in stocks if s.get("stock_code")])
        for s in stocks:
            supp = supplements.get(str(s.get("stock_code", "")).split(".")[0])
            if supp:
                for k, v in supp.items():
                    s.setdefault(k, v)
                s["data_source"] = "同花顺官方API·腾讯行情补充"
    except Exception as e:
        log.warning(f"行情补充字段获取失败（fail-open 跳过）: {e}")

    return {"indexes": indexes, "stocks": stocks, "errors": errors, "updated_at": updated_at}

# ============================================================
# 研报 RAG 入库与检索（阶段 5 新增）
# ============================================================

@router.post("/reports/upload")
async def upload_report(file: UploadFile = File(...)):
    """上传研报 PDF 并入库 RAG"""
    from app.rag.report_ingest import ingest_report
    
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件超过 {MAX_FILE_SIZE_MB}MB 限制")
    
    # 保存上传的文件：basename 归一化，防止 filename 携带 ../ 实现路径穿越写入
    safe_name = os.path.basename(file.filename)
    if not safe_name or safe_name in (".", ".."):
        raise HTTPException(status_code=400, detail="非法文件名")
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 入库
    result = ingest_report(file_path, file.filename)
    
    if result["success"]:
        return {"status": "ok", "chunks": result["chunks"], "metadata": result["metadata"]}
    else:
        raise HTTPException(status_code=500, detail=result["error"])


@router.get("/reports/search")
async def search_reports(q: str, stock_code: str = None, top_k: int = 5):
    """检索已入库的研报"""
    from app.rag.report_ingest import search_reports
    
    results = await search_reports(q, stock_code=stock_code, top_k=top_k)
    return {"status": "ok", "results": results, "count": len(results)}


# ============================================================
# 系统状态探测（侧边栏数据源/LLM 状态展示）
# ============================================================

_status_cache = {"ts": 0.0, "data": None}
_STATUS_TTL = 60  # 60s 缓存，避免每次侧边栏渲染都真查



@router.get("/usage")
async def usage_stats(reset: bool = False):
    """进程级 LLM token 用量（benchmark/成本观测用）。

    real=provider 真实回传（invoke 路径）；est=流式路径字符估算。口径分开累计。
    """
    from app.utils.llm import get_usage_snapshot

    return {"status": "ok", "usage": get_usage_snapshot(reset=reset)}


@router.get("/status")
async def system_status():
    """返回数据源与 LLM 降级状态（60s 缓存）"""
    import time as _t
    from app.utils.llm import _is_exhausted

    now = _t.time()
    if _status_cache["data"] and (now - _status_cache["ts"] < _STATUS_TTL):
        return _status_cache["data"]

    # 轻量探测：行情工具自带三层降级，返回的 data_source 即当前实际数据层
    data_source = "未知"
    try:
        # invoke 返回 JSON 字符串（工具约定）；AKShare 为同步阻塞调用，
        # 用 asyncio.to_thread 丢进线程池，避免卡住事件循环（原 fut.result() 同步等待会阻塞最多 30s）
        raw = await asyncio.to_thread(query_stock_quote.invoke, "600519")
        result = json.loads(raw)
        quote = result.get("quote", {})
        data_source = quote.get("data_source", "未知")
    except Exception as e:
        data_source = f"异常（{str(e)[:40]}）"

    payload = {
        "data_source": data_source,
        "data_online": "AKShare" in data_source or "雪球" in data_source,
        "llm_degraded": _is_exhausted(),
        "primary_model": os.getenv("LLM_MODEL_PRIMARY", "qwen3.7-plus"),
        "fallback_model": os.getenv("LLM_MODEL_FALLBACK", "deepseek-v4-flash"),
    }
    _status_cache["ts"] = now
    _status_cache["data"] = payload
    return payload



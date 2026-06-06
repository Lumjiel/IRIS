from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from app.graph.graph import create_graph
import json
import asyncio
import os
import shutil
from app.rag.engine import process_documents, reset_knowledge_base, UPLOAD_DIR
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.utils.logger import get_logger

log = get_logger("routes")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "checkpoints.db")
router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    search_mode: str = "hybrid" # 默认为混合搜索
    thread_id: str             

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

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="一次最多只能上传 5 个文件")

    try:

        reset_knowledge_base()

        saved_paths = []

        for file in files:
            # 文件类型校验
            if not file.filename or not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"仅支持 PDF 文件: {file.filename}")

            # 文件名安全处理（防路径穿越）
            safe_name = os.path.basename(file.filename)
            file_path = os.path.join(UPLOAD_DIR, safe_name)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(file_path)


        chunks_num = process_documents(saved_paths)

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
async def chat_endpoint(request: ChatRequest):
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

创作目录 = os.path.normpath(r"E:\claudecode\创作\projects\公众号\IRIS调研")

@router.post("/save-report")
async def save_report(request: SaveReportRequest):
    """将调研报告保存到寻阶行创作目录"""
    try:
        os.makedirs(创作目录, exist_ok=True)

        # 生成文件名
        safe_query = "".join(c for c in request.query if c.isalnum() or c in "一二三四五六七八九十百千万亿年月日时分秒AI").
        safe_query = safe_query[:40] or "调研报告"
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}-{safe_query}.md"
        filepath = os.path.join(创作目录, filename)

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
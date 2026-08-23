from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import json
from app.api.routes import router
from app.utils.logger import get_logger
from app.config import HOST, PORT, WORKERS, CORS_ORIGINS, LOG_LEVEL
from app.utils.llm import PRIMARY_MODEL, FALLBACK_MODEL

log = get_logger("main")

# 启动时检查关键依赖
def _check_deps():
    missing = []
    for mod in ["langgraph.checkpoint.sqlite.aio", "langgraph", "langchain_openai", "chromadb", "tavily"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        log.error(f"缺少依赖: {', '.join(missing)}，请运行 pip install -r requirements.txt")
        raise SystemExit(1)

_check_deps()

app = FastAPI(title="IRIS Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ORIGINS != ["*"],  # 通配符时不能开 credentials
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


def _preheat_data_cache():
    """后台预热 AKShare 行情缓存（_SPOT_CACHE）。

    目的：演示/首次请求前把东财全市场快照拉进进程内缓存，
    避免第一个用户请求承担冷启动延迟或触发限流。失败不影响服务。
    """
    import threading

    def _warm():
        try:
            from app.tools.akshare_tools import query_stock_quote
            raw = query_stock_quote("600196")
            source = json.loads(raw).get("quote", {}).get("data_source", "未知")
            log.info(f"[Preheat] 行情缓存预热完成，当前数据层: {source}")
        except Exception as e:
            log.warning(f"[Preheat] 缓存预热失败（不影响服务）: {e}")

    threading.Thread(target=_warm, daemon=True, name="preheat-data").start()


_preheat_data_cache()

# 挂载前端静态文件
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """SPA fallback：非 /api 路径全部返回 index.html"""
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    @app.get("/")
    def health_check():
        return {
            "status": "running",
            "model": PRIMARY_MODEL,
            "fallback_model": FALLBACK_MODEL,
        }

if __name__ == "__main__":
    log.info("后端服务正在启动...")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True, workers=1)
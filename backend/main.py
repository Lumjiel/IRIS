from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
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
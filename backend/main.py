from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.routes import router
from app.utils.logger import get_logger
from app.config import HOST, PORT, CORS_ORIGINS, LOG_LEVEL
from app.utils.llm import PRIMARY_MODEL, FALLBACK_MODEL

log = get_logger("main")

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
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
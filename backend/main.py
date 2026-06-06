from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.routes import router
from app.utils.logger import get_logger

log = get_logger("main")

app = FastAPI(title="IRIS Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "running", "model_config": "Qwen-Max + DeepSeek-R1"}

if __name__ == "__main__":
    log.info("后端服务正在启动...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
"""
IRIS 集中配置 - 从环境变量读取所有可配置值
"""
import os
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_TIMEOUT_FAST = int(os.getenv("LLM_TIMEOUT_FAST", "60"))
LLM_TIMEOUT_SMART = int(os.getenv("LLM_TIMEOUT_SMART", "90"))
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "3"))

# RAG
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K = int(os.getenv("TOP_K", "5"))
FETCH_K = int(os.getenv("FETCH_K", "20"))
ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "false").lower() == "true"
MAX_KNOWLEDGE_BASE_CHUNKS = int(os.getenv("MAX_KNOWLEDGE_BASE_CHUNKS", "2000"))
CHECKPOINT_MAX_AGE_DAYS = int(os.getenv("CHECKPOINT_MAX_AGE_DAYS", "7"))

# Search
TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "3"))
TAVILY_MAX_RETRIES = int(os.getenv("TAVILY_MAX_RETRIES", "2"))

# Upload
MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "5"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
WORKERS = int(os.getenv("WORKERS", "1"))  # 2G 服务器建议 1 worker
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

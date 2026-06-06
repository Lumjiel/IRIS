"""
IRIS 集中配置 - 从环境变量读取所有可配置值
"""
import os
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_TIMEOUT_FAST = int(os.getenv("LLM_TIMEOUT_FAST", "120"))
LLM_TIMEOUT_SMART = int(os.getenv("LLM_TIMEOUT_SMART", "120"))
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

# 创作目录（保存报告用）
CREATION_DIR = os.getenv("CREATION_DIR", r"E:\claudecode\创作\projects\公众号\IRIS调研")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
WORKERS = int(os.getenv("WORKERS", "1"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# 数据目录
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CHECKPOINT_DB = os.getenv("CHECKPOINT_DB", os.path.join(DATA_DIR, "checkpoints.db"))

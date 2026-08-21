"""
IRIS Checkpoint 管理
提供 MemorySaver 和 AsyncSqliteSaver 工厂
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.config import CHECKPOINT_DB


def get_memory():
    """获取内存 checkpointer（用于测试）"""
    return MemorySaver()


def get_sqlite():
    """获取 SQLite checkpointer（用于生产）"""
    return AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB)

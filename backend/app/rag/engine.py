import os
import shutil
from typing import Any, List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_core import vectorstores
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from app.utils.logger import get_logger
from app.config import MAX_KNOWLEDGE_BASE_CHUNKS, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, FETCH_K

log = get_logger("rag.engine")

from app.config import (
    MAX_KNOWLEDGE_BASE_CHUNKS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
    FETCH_K,
    ENABLE_RERANKER,
)
from app.rag.reranker import DashScopeReranker, RerankError, get_reranker

log = get_logger("rag.engine")


class RerankRetriever(BaseRetriever):
    """
    两阶段检索：
    1) Chroma 向量召回 fetch_k 个候选
    2) DashScope gte-rerank 精排（fail-open：失败降级为向量序）
    3) 返回 top_k
    """

    vectorstore: Any
    reranker: Any
    top_k: int = 5
    fetch_k: int = 20

    def _get_relevant_documents(self, query: str) -> list[Document]:
        # 1) 先召回更多候选
        candidates: list[Document] = self.vectorstore.similarity_search(query, k=self.fetch_k)
        if not candidates:
            return []

        # 2) rerank 精排；任何异常降级为纯向量序（rerank 是锦上添花，不阻塞检索）
        try:
            return self.reranker.rerank(query, candidates, self.top_k)
        except RerankError as e:
            log.warning(f"[RAG] rerank 失败，降级为纯向量序: {e}")
            return candidates[: self.top_k]

# 定义数据存储路径
# 数据存储路径（从配置读取，Docker 部署时改为持久化卷）
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(_BASE_DIR, "chroma_db"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(_BASE_DIR, "uploads"))


#embeddings = HuggingFaceEmbeddings(model_name="moka-ai/m3e-base")
# 这里用的是阿里云的词嵌入模型，需要配置环境变量，不行的话可以用上面的
embeddings = DashScopeEmbeddings(model='text-embedding-v4')

def reset_knowledge_base():
    """
    重置知识库：
    Windows 兼容版修复：不删除 DB 文件夹（避免 WinError 32），而是清空数据。
    """

    if os.path.exists(UPLOAD_DIR):
        try:
            shutil.rmtree(UPLOAD_DIR)
        except Exception as e:
            log.warning(f"[RAG] 清理上传目录警告: {e}")
    os.makedirs(UPLOAD_DIR, exist_ok=True)


    log.info("[RAG] 正在重置知识库数据...")
    try:
        if os.path.exists(DB_PATH):
            vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
            try:
                vectorstore.delete_collection()
                log.info("[RAG] 知识库 Collection 已删除 (数据已清空)")
            except Exception:
                pass
    except Exception as e:
        log.warning(f"[RAG] 重置数据库时遇到非致命错误 (不影响使用): {e}")

def process_documents(file_paths: List[str]):
    """
    核心逻辑：读取 -> 切片 -> 向量化 -> 存储
    """
    all_splits = []

    for file_path in file_paths:
        log.info(f"正在处理文档: {os.path.basename(file_path)}")
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP
            )
            splits = text_splitter.split_documents(docs)
            all_splits.extend(splits)
        except Exception as e:
            log.error(f"处理文件 {file_path} 失败: {e}")

    if all_splits:
        # 检查片段数上限
        if len(all_splits) > MAX_KNOWLEDGE_BASE_CHUNKS:
            log.warning(f"文档片段数 {len(all_splits)} 超过上限 {MAX_KNOWLEDGE_BASE_CHUNKS}，已截断")
            all_splits = all_splits[:MAX_KNOWLEDGE_BASE_CHUNKS]

        log.info(f"正在将 {len(all_splits)} 个片段写入向量数据库...")
        Chroma.from_documents(
            documents=all_splits,
            embedding=embeddings,
            persist_directory=DB_PATH
        )
        log.info("写入完成")

    return len(all_splits)

def get_retriever():
    """
    获取检索器：给 Agent 用的接口。
    ENABLE_RERANKER=true（默认）时走 DashScope gte-rerank 两阶段精排，失败自动降级纯向量。
    """
    if not os.path.exists(DB_PATH) or not os.listdir(DB_PATH):
        return None
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

    if ENABLE_RERANKER:
        try:
            reranker = get_reranker()
            return RerankRetriever(vectorstore=vectorstore, reranker=reranker, top_k=TOP_K, fetch_k=FETCH_K)
        except Exception as e:
            log.warning(f"Reranker 加载失败，降级为纯向量检索: {e}")

    # 降级：直接用向量相似度 top_k
    return vectorstore.as_retriever(search_kwargs={"k": TOP_K})


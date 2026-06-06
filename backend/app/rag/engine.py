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
from app.config import MAX_KNOWLEDGE_BASE_CHUNKS

log = get_logger("rag.engine")

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None

def get_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker
    if CrossEncoder is None:
        raise RuntimeError(
            "未安装 sentence-transformers，无法启用 reranking。请执行：pip install sentence-transformers"
        )
    _reranker = CrossEncoder(RERANKER_MODEL_NAME)
    return _reranker

class RerankRetriever(BaseRetriever):
    """
    两阶段检索：
    1) Chroma 向量召回 fetch_k 个候选
    2) Cross-Encoder rerank
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

        # 2) rerank：对 (query, doc_text) 打分
        pairs = [(query, d.page_content) for d in candidates]
        scores = self.reranker.predict(pairs)

        # 3) 按分数排序，取 top_k
        ranked = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)
        top_docs = [doc for doc, _ in ranked[: self.top_k]]

        return top_docs

# 定义数据存储路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")   # 数据库文件存这里
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads") # 用户上传的 PDF 存这里


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
                chunk_size=500,
                chunk_overlap=50
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
    获取检索器：给 Agent 用的接口
    启用 ENABLE_RERANKER=true 时使用 CrossEncoder 精排（额外 ~400MB 内存）
    """
    if not os.path.exists(DB_PATH) or not os.listdir(DB_PATH):
        return None
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    top_k = 5
    fetch_k = 20

    enable_reranker = os.getenv("ENABLE_RERANKER", "false").lower() == "true"
    if enable_reranker:
        try:
            reranker = get_reranker()
            return RerankRetriever(vectorstore=vectorstore, reranker=reranker, top_k=top_k, fetch_k=fetch_k)
        except Exception as e:
            log.warning(f"Reranker 加载失败，降级为纯向量检索: {e}")

    # 降级：直接用向量相似度 top_k
    return vectorstore.as_retriever(search_kwargs={"k": top_k})


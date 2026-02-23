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

# 1. 初始化 Embedding 模型
#embeddings = HuggingFaceEmbeddings(model_name="moka-ai/m3e-base")
# 这里用的是阿里云的词嵌入模型，需要配置环境变量，不行的话可以用上面的
embeddings = DashScopeEmbeddings(model='text-embedding-v4')

def reset_knowledge_base():
    """
    重置知识库：
    Windows 兼容版修复：不删除 DB 文件夹（避免 WinError 32），而是清空数据。
    """
    # 1. 清空上传目录 (这个是普通文件，可以直接删)
    if os.path.exists(UPLOAD_DIR):
        try:
            shutil.rmtree(UPLOAD_DIR)
        except Exception as e:
            print(f"--- [RAG] 清理上传目录警告: {e} ---")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 2. 清空 Chroma 数据库
    # 策略：连接到数据库，执行 delete_collection()，而不是删除文件夹
    print("--- [RAG] 正在重置知识库数据... ---")
    try:
        if os.path.exists(DB_PATH):
            # 初始化一个 vectorstore 实例
            vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
            
            # 尝试删除默认的 collection (通常叫 'langchain')
            # 这会清空所有向量数据，但保留文件结构，不会触发文件锁错误
            try:
                vectorstore.delete_collection()
                print("--- [RAG] 知识库 Collection 已删除 (数据已清空) ---")
            except Exception:
                # 如果 Collection 本来就不存在 (比如第一次运行)，这里会报错，直接忽略即可
                pass
    except Exception as e:
        print(f"--- [RAG] 重置数据库时遇到非致命错误 (不影响使用): {e} ---")

def process_documents(file_paths: List[str]):
    """
    核心逻辑：读取 -> 切片 -> 向量化 -> 存储
    """
    all_splits = []
    
    # 2. 遍历处理每一个文件
    for file_path in file_paths:
        print(f"--- [RAG] 正在处理文档: {os.path.basename(file_path)} ---")
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            
            # 3. 文本切片 (Chunking)
            # 这里的参数很有讲究：
            # chunk_size=500: 每个片段 500 个字符
            # chunk_overlap=50: 片段之间重叠 50 个字符，防止把一句话切断了
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            splits = text_splitter.split_documents(docs)
            all_splits.extend(splits)
        except Exception as e:
            print(f"❌ 处理文件 {file_path} 失败: {e}")
    
    # 4. 存入 ChromaDB
    if all_splits:
        print(f"--- [RAG] 正在将 {len(all_splits)} 个片段写入向量数据库... ---")
        Chroma.from_documents(
            documents=all_splits,
            embedding=embeddings,
            persist_directory=DB_PATH
        )
        print("--- [RAG] 写入完成 ---")
    
    return len(all_splits)

def get_retriever():
    """
    获取检索器：给 Agent 用的接口
    """
    # 如果数据库文件夹不存在，说明用户还没上传过文件
    if not os.path.exists(DB_PATH) or not os.listdir(DB_PATH):
        return None
    
    # 加载已存在的数据库
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    top_k = 5
    fetch_k = 20
    reranker = get_reranker()
    # 返回检索器
    # k=5 表示每次搜索最相似的 5 段话
    return RerankRetriever(vectorstore=vectorstore, reranker=reranker, top_k=top_k, fetch_k=fetch_k)


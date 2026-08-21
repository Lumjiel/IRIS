"""
研报 PDF 入库 RAG
- PyMuPDF 抽取研报全文
- 正则抽取实体（公司名/代码/评级/目标价/日期）
- 分块入库 ChromaDB（带元数据）
"""
import os
import re
import json
from typing import Optional, Dict, List, Any
from datetime import datetime

from app.utils.logger import get_logger
from app.config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_KNOWLEDGE_BASE_CHUNKS

log = get_logger("report_ingest")

# ChromaDB 路径（复用 engine.py 的配置）
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(_BASE_DIR, "..", "rag", "chroma_db"))

# ============================================================
# 研报实体抽取
# ============================================================

# 匹配 A 股代码（6 位数字，以 60/00/30/68 开头）
_STOCK_CODE_RE = re.compile(r'\b([68]\d{5}|[03]\d{5})\b')

# 匹配券商评级
_RATING_RE = re.compile(
    r'(买入|增持|推荐|中性|减持|卖出|强烈推荐|谨慎推荐|持有|跑赢大市|落后大市)',
    re.IGNORECASE
)

# 匹配目标价
_TARGET_PRICE_RE = re.compile(r'目标价[：:]?\s*(\d+\.?\d*)\s*(?:元|RMB|CNY)?', re.IGNORECASE)

# 匹配日期（YYYY-MM-DD 或 YYYY年MM月DD日）
_DATE_RE = re.compile(r'(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})')


def extract_report_metadata(text: str, filename: str = "") -> Dict[str, Any]:
    """
    从研报文本中抽取元数据。
    
    返回:
        {
            "stock_code": "600196",
            "stock_name": "复星医药",
            "rating": "买入",
            "target_price": "35.5",
            "report_date": "2025-08-20",
            "source": "券商研报",
            "filename": "...",
            "ingest_time": "2025-08-20T10:30:00"
        }
    """
    metadata = {
        "source": "券商研报",
        "filename": filename,
        "ingest_time": datetime.now().isoformat(timespec="seconds"),
    }
    
    # 抽取股票代码
    code_match = _STOCK_CODE_RE.search(text)
    if code_match:
        metadata["stock_code"] = code_match.group(1)
    
    # 抽取评级
    rating_match = _RATING_RE.search(text)
    if rating_match:
        metadata["rating"] = rating_match.group(1)
    
    # 抽取目标价
    price_match = _TARGET_PRICE_RE.search(text)
    if price_match:
        metadata["target_price"] = price_match.group(1)
    
    # 抽取日期（取第一个匹配）
    date_match = _DATE_RE.search(text)
    if date_match:
        year, month, day = date_match.groups()
        metadata["report_date"] = f"{year}-{int(month):02d}-{int(day):02d}"
    
    # 抽取公司名（简单启发式：第一个出现的"XX股份"或"XX集团"）
    name_match = re.search(r'([\u4e00-\u9fa5]{2,8}(?:股份|集团|科技|药业|银行|保险|证券))', text)
    if name_match:
        metadata["stock_name"] = name_match.group(1)
    
    return metadata


# ============================================================
# PDF 文本抽取
# ============================================================

def extract_text_from_pdf(file_path: str) -> str:
    """
    使用 PyMuPDF 抽取 PDF 全文。
    依赖: pymupdf (fitz)
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError(
            "未安装 PyMuPDF，无法处理研报 PDF。请执行: pip install pymupdf"
        )
    
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    
    full_text = "\n".join(text_parts)
    log.info(f"[研报入库] 抽取 {len(full_text)} 字符（{len(doc)} 页）")
    return full_text


# ============================================================
# 研报入库
# ============================================================

def ingest_report(file_path: str, filename: str = "") -> Dict[str, Any]:
    """
    单个研报 PDF 入库。
    
    流程:
        1. PyMuPDF 抽取全文
        2. 正则抽取元数据
        3. 分块
        4. 写入 ChromaDB（带元数据）
    
    返回:
        {"success": bool, "chunks": int, "metadata": {...}, "error": "..."}
    """
    if not filename:
        filename = os.path.basename(file_path)
    
    if not os.path.exists(file_path):
        return {"success": False, "chunks": 0, "metadata": {}, "error": f"文件不存在: {file_path}"}
    
    try:
        # 1. 抽取文本
        text = extract_text_from_pdf(file_path)
        if not text.strip():
            return {"success": False, "chunks": 0, "metadata": {}, "error": "PDF 文本为空"}
        
        # 2. 抽取元数据
        metadata = extract_report_metadata(text, filename)
        log.info(f"[研报入库] 抽取元数据: {json.dumps(metadata, ensure_ascii=False)}")
        
        # 3. 分块
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_core.documents import Document
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
        )
        
        chunks = splitter.split_text(text)
        
        # 为每个分块附加元数据
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            documents.append(Document(page_content=chunk, metadata=chunk_meta))
        
        # 4. 写入 ChromaDB
        from langchain_community.vectorstores import Chroma
        from app.rag.engine import embeddings
        
        vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
        vectorstore.add_documents(documents)
        
        log.info(f"[研报入库] 成功写入 {len(documents)} 个分块")
        
        return {
            "success": True,
            "chunks": len(documents),
            "metadata": metadata,
            "error": None,
        }
        
    except Exception as e:
        log.error(f"[研报入库] 处理失败: {e}")
        return {"success": False, "chunks": 0, "metadata": {}, "error": str(e)}


def ingest_reports_from_dir(dir_path: str) -> List[Dict[str, Any]]:
    """
    批量入库目录下的所有 PDF 研报。
    
    返回:
        每个文件的入库结果列表
    """
    results = []
    if not os.path.isdir(dir_path):
        return results
    
    for filename in sorted(os.listdir(dir_path)):
        if filename.lower().endswith('.pdf'):
            file_path = os.path.join(dir_path, filename)
            result = ingest_report(file_path, filename)
            results.append(result)
    
    log.info(f"[研报入库] 批量处理完成: {len(results)} 个文件")
    return results


# ============================================================
# 研报检索
# ============================================================

def search_reports(
    query: str,
    stock_code: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    检索已入库的研报。
    
    参数:
        query: 搜索关键词
        stock_code: 可选，按股票代码过滤
        top_k: 返回数量
    
    返回:
        [{"text": "...", "metadata": {...}, "score": 0.95}, ...]
    """
    try:
        from langchain_community.vectorstores import Chroma
        from app.rag.engine import embeddings
        
        if not os.path.exists(DB_PATH) or not os.listdir(DB_PATH):
            return []
        
        vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
        
        # 构建过滤条件
        filter_dict = None
        if stock_code:
            filter_dict = {"stock_code": stock_code}
        
        # 检索
        if filter_dict:
            results = vectorstore.similarity_search_with_score(query, k=top_k, filter=filter_dict)
        else:
            results = vectorstore.similarity_search_with_score(query, k=top_k)
        
        return [
            {
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in results
        ]
        
    except Exception as e:
        log.error(f"[研报检索] 失败: {e}")
        return []

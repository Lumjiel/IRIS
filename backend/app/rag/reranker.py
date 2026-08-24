"""
DashScope gte-rerank 精排器（替代本地 CrossEncoder）。

设计要点（docs/DESIGN_rerank_and_memory.md 方案 A）：
- 与现有 embedding 同供应商同 Key，毫秒级、零本地依赖（无 torch/sentence-transformers）
- fail-open：任何异常抛 RerankError，由上层捕获降级为纯向量序，不阻塞主流程
- 显式短超时（默认 3s），rerank 是锦上添花，不值得阻塞检索热路径
"""
from typing import List

from langchain_core.documents import Document

from app.config import RERANK_MODEL, RERANK_TIMEOUT_S
from app.utils.logger import get_logger

log = get_logger("rag.reranker")


class RerankError(Exception):
    """Rerank 调用失败（网络/限流/响应异常）。上层应捕获并降级为向量序。"""


class DashScopeReranker:
    """gte-rerank 精排器。接口签名对齐原 CrossEncoder 用法，便于替换。"""

    def __init__(self, model: str = RERANK_MODEL):
        self.model = model

    def rerank(self, query: str, docs: List[Document], top_k: int) -> List[Document]:
        """
        对候选文档精排，返回按相关度降序的 top_k 文档。

        异常时抛 RerankError（fail-open 由上层处理），绝不返回部分错误结果。
        同步网络调用——事件循环中的调用方需用 asyncio.to_thread 包装。
        """
        if not docs:
            return []

        import dashscope  # 延迟导入：conftest 可整体 mock

        try:
            response = dashscope.TextReRank.call(
                model=self.model,
                query=query,
                documents=[d.page_content for d in docs],
                top_n=min(top_k, len(docs)),
                return_documents=False,
                timeout=RERANK_TIMEOUT_S,
            )
        except RerankError:
            raise
        except Exception as e:
            raise RerankError(f"gte-rerank 调用失败: {e}") from e

        if response.status_code != 200:
            raise RerankError(
                f"gte-rerank 返回非 200: code={response.code} msg={response.message}"
            )

        results = getattr(response.output, "results", None)
        if not results:
            raise RerankError("gte-rerank 返回空结果")

        ranked: List[Document] = []
        try:
            for item in results:
                idx = int(item["index"])
                if 0 <= idx < len(docs):
                    doc = docs[idx]
                    # 相关度分数写入 metadata，供调用方感知（0-1，越大越相关）
                    doc.metadata["relevance_score"] = float(item["relevance_score"])
                    ranked.append(doc)
        except (KeyError, TypeError, ValueError) as e:
            raise RerankError(f"gte-rerank 响应格式异常: {e}") from e

        # 代码侧强制截断 top_k，不依赖 API 对 top_n 的实现
        return ranked[:top_k]


_reranker = None


def get_reranker() -> DashScopeReranker:
    """单例获取。构造是纯 Python 对象，无模型加载成本。"""
    global _reranker
    if _reranker is None:
        _reranker = DashScopeReranker()
    return _reranker

"""Built-in document search tool backed by the RAG engine."""
from app.tools.registry import ToolRegistry


@ToolRegistry.register(
    name="doc_search",
    description="从已上传的文档中检索相关信息。适用于：内部文档、技术手册、历史报告、PDF资料。",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "要在文档中检索的关键词或问题"}},
        "required": ["query"],
    },
)
def doc_search(query: str) -> str:
    from app.rag.engine import get_retriever
    retriever = get_retriever()
    if not retriever:
        return "[系统提示] 知识库为空，请先上传文档。"
    docs = retriever.invoke(query)
    if not docs:
        return "[系统提示] 未找到相关文档内容。"
    return "\n\n".join(f"[文档]: {doc.page_content}" for doc in docs)

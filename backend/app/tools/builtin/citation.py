"""Built-in citation search tool -- search with source attribution."""
from app.tools.registry import ToolRegistry


@ToolRegistry.register(
    name="citation_search",
    description="搜索并返回带引用标注的结果。适用于：需要标注信息来源的调研。",
)
def citation_search(query: str) -> str:
    from app.tools.search import search_tavily
    from app.utils.citations import CitationFormatter

    formatter = CitationFormatter()
    raw = search_tavily(query)
    if not raw:
        return ""

    parts = raw.split("\n")
    result_lines: list[str] = []
    for i, line in enumerate(parts):
        if line.strip():
            idx = formatter.add_source(url="", title=f"Result {i+1}", snippet=line[:200])
            result_lines.append(f"[{idx}] {line}")
        else:
            result_lines.append(line)
    formatted = "\n".join(result_lines)
    refs = formatter.format_references()
    return formatted + refs if refs else formatted

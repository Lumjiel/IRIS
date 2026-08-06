"""Citation formatting utilities for source-attributed search results."""
from __future__ import annotations

from typing import List


class CitationFormatter:
    """Collects sources and produces inline citation markers + a reference list."""

    def __init__(self):
        self._sources: List[dict] = []

    def add_source(self, url: str, title: str, snippet: str) -> int:
        """Register a source.  Returns its 1-based citation index."""
        self._sources.append({
            "url": url,
            "title": title,
            "snippet": snippet[:200],
        })
        return len(self._sources)

    def format_inline(self, index: int) -> str:
        """Return an inline citation marker like ``[1]``."""
        return f"[{index}]"

    def format_references(self) -> str:
        """Return a Markdown-formatted references section."""
        if not self._sources:
            return ""
        lines = ["\n\n---\n**参考文献**\n"]
        for i, s in enumerate(self._sources, 1):
            title = s.get("title", "")
            url = s.get("url", "")
            if url:
                lines.append(f"[{i}] {title} \u2014 {url}")
            else:
                lines.append(f"[{i}] {title}")
        return "\n".join(lines)

    def add_source_from_search_result(self, result: dict) -> int:
        """Register a source from a Tavily search result dict.

        Accepts ``{"url": "...", "title": "...", "content": "..."}``.
        Returns its 1-based citation index.
        """
        return self.add_source(
            url=result.get("url", ""),
            title=result.get("title", ""),
            snippet=result.get("content", ""),
        )

    @property
    def sources(self) -> List[dict]:
        return list(self._sources)

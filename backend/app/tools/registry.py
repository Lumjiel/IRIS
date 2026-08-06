"""
ToolRegistry -- dynamic tool registration, discovery, and execution.

Tools are registered at import time via decorator or explicit register() call.
Skills can declare required_tools to restrict which tools are used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.utils.logger import get_logger

log = get_logger("tool_registry")


@dataclass
class ToolDefinition:
    """Metadata for a registered tool."""
    name: str
    description: str
    func: Callable
    parameters: dict = field(default_factory=dict)  # JSON Schema


class ToolRegistry:
    """Singleton registry for all available tools."""

    _tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(
        cls,
        name: str = "",
        description: str = "",
        parameters: Optional[dict] = None,
    ):
        """Register a tool.  Can be used as a decorator or called directly.

        Usage as decorator::

            @ToolRegistry.register(name="my_tool", description="...")
            def my_tool(query: str) -> str:
                ...

        Usage as direct call::

            ToolRegistry.register(name="my_tool", description="...", func=my_func)
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name if isinstance(name, str) and name else getattr(func, "__name__", str(func))
            tool_desc = description or func.__doc__ or ""
            defn = ToolDefinition(
                name=tool_name,
                description=tool_desc.strip(),
                func=func,
                parameters=parameters or {},
            )
            cls._tools[tool_name] = defn
            log.info(f"Tool registered: {tool_name}")
            return func

        # Support both decorator and direct-call usage
        if callable(name):
            # @ToolRegistry.register  (no arguments)
            func = name
            tool_name = getattr(func, "__name__", str(func))
            tool_desc = func.__doc__ or ""
            defn = ToolDefinition(
                name=tool_name,
                description=tool_desc.strip(),
                func=func,
                parameters={},
            )
            cls._tools[tool_name] = defn
            log.info(f"Tool registered: {tool_name}")
            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[ToolDefinition]:
        """Lookup a tool by exact name."""
        return cls._tools.get(name)

    @classmethod
    def search(cls, query: str, limit: int = 5) -> List[ToolDefinition]:
        """Keyword-based search across tool names and descriptions.

        Returns up to *limit* tools ranked by relevance score.
        """
        query_lower = query.lower()
        scored: list[tuple[int, ToolDefinition]] = []
        for tool in cls._tools.values():
            score = 0
            if query_lower in tool.name.lower():
                score += 3
            if query_lower in tool.description.lower():
                score += 1
            # token overlap
            for token in query_lower.split():
                if token and token in tool.name.lower():
                    score += 2
                if token and token in tool.description.lower():
                    score += 1
            if score > 0:
                scored.append((score, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]

    @classmethod
    def list_all(cls) -> List[ToolDefinition]:
        """Return every registered tool."""
        return list(cls._tools.values())

    @classmethod
    def get_all(cls) -> List[ToolDefinition]:
        """Alias for list_all()."""
        return cls.list_all()

    @classmethod
    def execute(cls, name: str, **kwargs) -> Any:
        """Execute a registered tool by name."""
        tool = cls._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found in registry")
        return tool.func(**kwargs)

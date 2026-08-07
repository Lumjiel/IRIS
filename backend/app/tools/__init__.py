"""app.tools -- Tool Registry and built-in tools."""

# Import builtin tools so they auto-register via decorators.
from app.tools.builtin import search as _search  # noqa: F401
from app.tools.builtin import doc_search as _doc_search  # noqa: F401
from app.tools.builtin import citation as _citation  # noqa: F401
from app.tools.builtin import skill_manage as _skill_manage  # noqa: F401

from app.tools.registry import ToolRegistry, ToolDefinition  # noqa: F401

__all__ = ["ToolRegistry", "ToolDefinition"]

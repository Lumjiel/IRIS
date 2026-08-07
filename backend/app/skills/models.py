"""Skill 数据模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone


@dataclass
class Skill:
    """单个 Skill 的完整元数据。"""

    name: str
    description: str
    prompt_template: str
    required_tools: list[str] = field(default_factory=list)
    memory_policy: str = "none"  # "read_episodic" | "write_semantic" | "none"
    skill_dir: Path = field(default_factory=Path)
    is_builtin: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "prompt_template": self.prompt_template,
            "required_tools": self.required_tools,
            "memory_policy": self.memory_policy,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

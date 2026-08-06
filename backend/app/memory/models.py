from dataclasses import dataclass, field
from typing import Optional
import uuid
from datetime import datetime, timezone


@dataclass
class MemoryRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    kind: str = "episodic"  # "episodic" | "semantic" | "procedural"
    content: str = ""
    thread_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "content": self.content,
            "thread_id": self.thread_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

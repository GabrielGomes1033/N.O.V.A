from __future__ import annotations

from typing import Any


class VectorStore:
    def __init__(self) -> None:
        self.enabled = False

    def index_text(self, user_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "enabled": self.enabled,
            "reason": "semantic_memory_not_configured",
            "user_id": str(user_id or "").strip() or "default",
            "text_size": len(str(text or "").strip()),
            "metadata": metadata or {},
        }

    def search(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return []

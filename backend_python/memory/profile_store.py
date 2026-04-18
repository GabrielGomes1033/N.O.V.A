from __future__ import annotations

from typing import Any

from memory.sqlite_store import MemoryStore


class ProfileStore:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory_store = memory_store

    def save_fact(
        self,
        user_id: str,
        category: str,
        content: str,
        *,
        importance: int = 3,
    ) -> dict[str, Any]:
        return self.memory_store.save(
            user_id=user_id,
            category=category,
            content=content,
            importance=importance,
            scope="perfil",
            source="profile_store",
        )

    def summary(self, user_id: str, limit: int = 6) -> list[dict[str, Any]]:
        facts = self.memory_store.search_recent(user_id=user_id, limit=limit, scope="perfil")
        if facts:
            return facts
        preferencias = self.memory_store.search_by_category(user_id=user_id, category="preferencia", limit=limit)
        return preferencias

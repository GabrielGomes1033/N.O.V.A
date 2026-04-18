from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

from core.caminhos import pasta_dados_app


DEFAULT_DB_PATH = pasta_dados_app() / "nova_memory.db"
DEFAULT_SCOPE = "longo_prazo"
VALID_SCOPES = {"perfil", "sessao", "longo_prazo", "semantica"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MemoryStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'longo_prazo',
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_user_updated "
            "ON memories (user_id, updated_at DESC)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_user_category "
            "ON memories (user_id, category, updated_at DESC)"
        )
        self.conn.commit()

    def save(
        self,
        user_id: str,
        category: str,
        content: str,
        importance: int = 1,
        *,
        scope: str = DEFAULT_SCOPE,
        source: str = "chat",
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip() or "default"
        cat = str(category or "").strip() or "contexto"
        body = str(content or "").strip()
        if not body:
            raise ValueError("memory content cannot be empty")

        memory_scope = str(scope or DEFAULT_SCOPE).strip().lower()
        if memory_scope not in VALID_SCOPES:
            memory_scope = DEFAULT_SCOPE

        now = _utc_now()
        cur = self.conn.execute(
            """
            INSERT INTO memories (user_id, scope, category, content, importance, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uid,
                memory_scope,
                cat,
                body,
                max(1, int(importance or 1)),
                str(source or "chat").strip() or "chat",
                now,
                now,
            ),
        )
        self.conn.commit()
        return {
            "id": int(cur.lastrowid),
            "user_id": uid,
            "scope": memory_scope,
            "category": cat,
            "content": body,
            "importance": max(1, int(importance or 1)),
            "source": str(source or "chat").strip() or "chat",
            "created_at": now,
            "updated_at": now,
        }

    def search_recent(
        self,
        user_id: str,
        limit: int = 10,
        *,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        uid = str(user_id or "").strip() or "default"
        params: list[Any] = [uid]
        query = (
            "SELECT id, user_id, scope, category, content, importance, source, created_at, updated_at "
            "FROM memories WHERE user_id=?"
        )
        scope_norm = str(scope or "").strip().lower()
        if scope_norm:
            query += " AND scope=?"
            params.append(scope_norm)
        query += " ORDER BY updated_at DESC, importance DESC LIMIT ?"
        params.append(max(1, int(limit or 10)))
        cur = self.conn.execute(query, tuple(params))
        return [dict(row) for row in cur.fetchall()]

    def search_by_category(
        self,
        user_id: str,
        category: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        uid = str(user_id or "").strip() or "default"
        cat = str(category or "").strip()
        cur = self.conn.execute(
            """
            SELECT id, user_id, scope, category, content, importance, source, created_at, updated_at
            FROM memories
            WHERE user_id=? AND category=?
            ORDER BY updated_at DESC, importance DESC
            LIMIT ?
            """,
            (uid, cat, max(1, int(limit or 10))),
        )
        return [dict(row) for row in cur.fetchall()]

    def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        uid = str(user_id or "").strip() or "default"
        term = str(query or "").strip()
        if not term:
            return []
        like = f"%{term}%"
        cur = self.conn.execute(
            """
            SELECT id, user_id, scope, category, content, importance, source, created_at, updated_at
            FROM memories
            WHERE user_id=? AND (content LIKE ? OR category LIKE ?)
            ORDER BY importance DESC, updated_at DESC
            LIMIT ?
            """,
            (uid, like, like, max(1, int(limit or 10))),
        )
        return [dict(row) for row in cur.fetchall()]

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

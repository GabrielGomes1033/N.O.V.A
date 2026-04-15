from __future__ import annotations

from pathlib import Path
import sqlite3

from core.caminhos import pasta_dados_app

DB_PATH = pasta_dados_app() / "nova.db"


class KnowledgeRepository:
    def __init__(self, db_path: Path | None = None):
        self._db_path = Path(db_path or DB_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    gatilho TEXT NOT NULL,
                    gatilho_normalizado TEXT NOT NULL,
                    resposta TEXT NOT NULL,
                    categoria TEXT NOT NULL DEFAULT 'geral',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_items_trigger_norm
                    ON knowledge_items(gatilho_normalizado);

                CREATE INDEX IF NOT EXISTS idx_knowledge_items_categoria
                    ON knowledge_items(categoria);

                CREATE INDEX IF NOT EXISTS idx_knowledge_items_ativo
                    ON knowledge_items(ativo);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_items_trigger_response
                    ON knowledge_items(gatilho_normalizado, resposta);
                """
            )

    def has_items(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM knowledge_items LIMIT 1").fetchone()
        return row is not None

    def list_items(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, gatilho, gatilho_normalizado, resposta, categoria, ativo, criado_em, atualizado_em
                FROM knowledge_items
                ORDER BY categoria, gatilho
                """
            ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def replace_all(self, items: list[dict]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM knowledge_items")
            conn.executemany(
                """
                INSERT INTO knowledge_items (
                    id, gatilho, gatilho_normalizado, resposta, categoria, ativo, criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(item.get("id", "")),
                        str(item.get("gatilho", "")),
                        str(item.get("gatilho_normalizado", "")),
                        str(item.get("resposta", "")),
                        str(item.get("categoria", "geral") or "geral"),
                        1 if item.get("ativo", True) else 0,
                        str(item.get("criado_em", "")),
                        str(item.get("atualizado_em", "")),
                    )
                    for item in items
                ],
            )

    def bootstrap_if_empty(self, items: list[dict]) -> bool:
        if self.has_items():
            return False
        self.replace_all(items)
        return True

    def upsert_for_trigger_response(
        self,
        *,
        item_id: str,
        gatilho: str,
        gatilho_normalizado: str,
        resposta: str,
        categoria: str,
        criado_em: str,
        atualizado_em: str,
    ) -> int:
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM knowledge_items
                WHERE gatilho_normalizado = ? AND resposta = ?
                LIMIT 1
                """,
                (gatilho_normalizado, resposta),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE knowledge_items
                    SET ativo = 1, categoria = ?, atualizado_em = ?, gatilho = ?
                    WHERE id = ?
                    """,
                    (categoria, atualizado_em, gatilho, str(existing["id"])),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO knowledge_items (
                        id, gatilho, gatilho_normalizado, resposta, categoria, ativo, criado_em, atualizado_em
                    ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        item_id,
                        gatilho,
                        gatilho_normalizado,
                        resposta,
                        categoria,
                        criado_em,
                        atualizado_em,
                    ),
                )

            row = conn.execute(
                "SELECT COUNT(*) AS total FROM knowledge_items WHERE gatilho_normalizado = ?",
                (gatilho_normalizado,),
            ).fetchone()
        return int(row["total"] if row else 0)

    def update_item(
        self,
        *,
        item_id: str,
        gatilho: str | None,
        gatilho_normalizado: str | None,
        resposta: str | None,
        categoria: str | None,
        ativo: bool | None,
        atualizado_em: str,
    ) -> dict | None:
        with self._connect() as conn:
            found = conn.execute(
                """
                SELECT id, gatilho, gatilho_normalizado, resposta, categoria, ativo, criado_em, atualizado_em
                FROM knowledge_items
                WHERE id = ?
                LIMIT 1
                """,
                (item_id,),
            ).fetchone()
            if not found:
                return None

            new_gatilho = gatilho if gatilho is not None else str(found["gatilho"])
            new_gatilho_norm = (
                gatilho_normalizado
                if gatilho_normalizado is not None
                else str(found["gatilho_normalizado"])
            )
            new_resposta = resposta if resposta is not None else str(found["resposta"])
            new_categoria = categoria if categoria is not None else str(found["categoria"])
            new_ativo = (1 if ativo else 0) if ativo is not None else int(found["ativo"])

            conn.execute(
                """
                UPDATE knowledge_items
                SET gatilho = ?,
                    gatilho_normalizado = ?,
                    resposta = ?,
                    categoria = ?,
                    ativo = ?,
                    atualizado_em = ?
                WHERE id = ?
                """,
                (
                    new_gatilho,
                    new_gatilho_norm,
                    new_resposta,
                    new_categoria,
                    new_ativo,
                    atualizado_em,
                    item_id,
                ),
            )

            updated = conn.execute(
                """
                SELECT id, gatilho, gatilho_normalizado, resposta, categoria, ativo, criado_em, atualizado_em
                FROM knowledge_items
                WHERE id = ?
                LIMIT 1
                """,
                (item_id,),
            ).fetchone()
        return self._row_to_item(updated) if updated else None

    def delete_item(self, item_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))
        return cur.rowcount > 0

    def list_active_exact(self, texto_normalizado: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT resposta
                FROM knowledge_items
                WHERE ativo = 1 AND gatilho_normalizado = ?
                """,
                (texto_normalizado,),
            ).fetchall()
        return [str(row["resposta"]) for row in rows if str(row["resposta"]).strip()]

    def list_active_similar(self, texto_normalizado: str) -> list[str]:
        like = f"%{texto_normalizado}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT resposta
                FROM knowledge_items
                WHERE ativo = 1
                  AND gatilho_normalizado != ''
                  AND ? LIKE '%' || gatilho_normalizado || '%'
                """,
                (texto_normalizado,),
            ).fetchall()
        return [str(row["resposta"]) for row in rows if str(row["resposta"]).strip()]

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> dict:
        return {
            "id": str(row["id"]),
            "gatilho": str(row["gatilho"]),
            "gatilho_normalizado": str(row["gatilho_normalizado"]),
            "resposta": str(row["resposta"]),
            "categoria": str(row["categoria"]),
            "ativo": bool(int(row["ativo"])),
            "criado_em": str(row["criado_em"]),
            "atualizado_em": str(row["atualizado_em"]),
        }

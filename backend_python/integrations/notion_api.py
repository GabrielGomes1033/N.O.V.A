from __future__ import annotations

from typing import Any

from core.backup_drive import criar_projeto_drive
from core.notion_projects import criar_projeto_notion, notion_disponivel


def create_project(
    name: str,
    description: str = "",
    *,
    provider: str = "",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_name = str(name or "").strip()
    if not project_name:
        return {"ok": False, "error": "project_name_required"}

    requested_provider = str(provider or "").strip().lower()
    metadata = details or {}

    if requested_provider in {"", "auto", "notion"} and notion_disponivel():
        ok, payload = criar_projeto_notion(
            project_name,
            description=str(description or "").strip(),
            details=metadata,
        )
        return {
            "ok": ok,
            "provider": "notion",
            "project_name": project_name,
            "payload": payload,
        }

    ok, payload = criar_projeto_drive(project_name, str(description or "").strip())
    return {
        "ok": ok,
        "provider": "drive",
        "project_name": project_name,
        "payload": payload,
    }

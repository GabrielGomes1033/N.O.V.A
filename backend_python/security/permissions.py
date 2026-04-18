from __future__ import annotations

from typing import Any

from core.painel_admin import listar_usuarios


def permission_summary() -> dict[str, Any]:
    users = listar_usuarios()
    return {
        "ok": True,
        "rbac_ready": True,
        "users_total": len(users),
        "roles": sorted({str(item.get("papel", "usuario")) for item in users if isinstance(item, dict)}),
    }

from __future__ import annotations

from typing import Any

from core.runtime_guard import token_api_configurado


def auth_status() -> dict[str, Any]:
    return {
        "ok": True,
        "token_required": bool(token_api_configurado()),
        "auth_mode": "token" if token_api_configurado() else "open_local",
    }

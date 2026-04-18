from __future__ import annotations

from typing import Any

from core.security_audit import auditoria_humana
from security.auth import auth_status
from security.permissions import permission_summary


def get_security_overview() -> dict[str, Any]:
    return {
        "ok": True,
        "auth": auth_status(),
        "permissions": permission_summary(),
        "audit_text": auditoria_humana(),
    }

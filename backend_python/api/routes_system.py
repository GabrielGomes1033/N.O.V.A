from __future__ import annotations

try:
    from fastapi import APIRouter, Depends, Query
except Exception:
    APIRouter = None
    Depends = None
    Query = None
from core.autonomia_runtime import (
    status_autonomia,
    ler_config_autonomia,
    atualizar_autonomia,
    status_sistema_detalhado,
)
from core.security_audit import (
    executar_auditoria_seguranca,
    obter_historico_auditoria,
)
from core.ops_status import status_operacional
from core.session_audit import listar_auditoria_sessao, validar_cadeia_auditoria
from .dependencies import rate_limit, require_rbac, require_token

if APIRouter is not None:
    router = APIRouter(tags=["system"], dependencies=[Depends(rate_limit(30))])

    @router.get("/system/status")
    def system_status(token: bool = Depends(require_token())):
        """System detailed status migration from api_server.py"""
        return status_sistema_detalhado()

    @router.get("/ops/status")
    def ops_status(token: bool = Depends(require_token())):
        return status_operacional()

    @router.get("/autonomy/status")
    def autonomy_status(token: bool = Depends(require_token())):
        return status_autonomia()

    @router.get("/autonomy/config")
    def autonomy_config(token: bool = Depends(require_token())):
        return {"ok": True, "config": ler_config_autonomia()}

    @router.post("/autonomy/config")
    def update_autonomy_config(
        body: dict,
        token: bool = Depends(require_token()),
        role_ok: bool = Depends(require_rbac("admin", error_detail="rbac_forbidden_autonomy")),
    ):
        ativa = body.get("active")
        confirmar = body.get("confirm_sensitive")
        nivel = body.get("risk_level")
        liberdade = body.get("freedom_level")
        out = atualizar_autonomia(
            ativa=ativa,
            nivel_risco=nivel,
            liberdade=liberdade,
            confirmar_sensivel=confirmar,
        )
        return {"ok": True, "config": out}

    @router.get("/security/audit")
    def security_audit(
        token: bool = Depends(require_token()),
        role_ok: bool = Depends(require_rbac("admin", "security", error_detail="rbac_forbidden_security")),
    ):
        return {"ok": True, "audit": executar_auditoria_seguranca()}

    @router.get("/security/audit/history")
    def audit_history(
        limit: int = Query(default=30, ge=1, le=100),
        token: bool = Depends(require_token()),
        role_ok: bool = Depends(require_rbac("admin", "security", error_detail="rbac_forbidden_security")),
    ):
        return {"ok": True, "items": obter_historico_auditoria(limit=limit)}

    @router.get("/security/session-audit")
    def session_audit(
        limit: int = Query(default=120, ge=1, le=500),
        token: bool = Depends(require_token()),
        role_ok: bool = Depends(require_rbac("admin", "security", error_detail="rbac_forbidden_security")),
    ):
        return {"ok": True, "items": listar_auditoria_sessao(limit=limit)}

    @router.get("/security/session-audit/verify")
    def verify_session_audit(
        token: bool = Depends(require_token()),
        role_ok: bool = Depends(require_rbac("admin", "security", error_detail="rbac_forbidden_security")),
    ):
        return validar_cadeia_auditoria()
else:
    router = None

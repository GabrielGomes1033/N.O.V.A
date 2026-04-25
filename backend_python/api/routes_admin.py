from __future__ import annotations

try:
    from fastapi import APIRouter, Depends, HTTPException
except Exception:
    APIRouter = None
    Depends = None
    HTTPException = None

from core.painel_admin import (
    adicionar_usuario,
    atualizar_usuario,
    listar_usuarios,
    remover_usuario,
    carregar_config_painel,
    atualizar_config_painel,
)
from core.aprendizado_admin import listar_aprendizados
from .dependencies import rate_limit, require_rbac, require_token


# Temp state for migration (migrate to DB later)
def _estado_admin():
    return {
        "knowledge_total": len(listar_aprendizados()),
        "users_total": len(listar_usuarios()),
        "knowledge": listar_aprendizados(),
        "users": listar_usuarios(),
        "config": carregar_config_painel(),
    }


if APIRouter is not None:
    router = APIRouter(
        tags=["admin"],
        prefix="/admin",
        dependencies=[
            Depends(rate_limit(30)),
            Depends(require_token()),
            Depends(require_rbac("admin", error_detail="rbac_forbidden_admin")),
        ],
    )

    @router.get("/state")
    def get_admin_state():
        """Admin state from api_server.py migration"""
        return {"ok": True, "state": _estado_admin()}

    @router.get("/config")
    def get_config():
        return {"ok": True, "config": carregar_config_painel()}

    @router.post("/config")
    def update_config(body: dict):
        config = atualizar_config_painel(**body)
        return {"ok": True, "config": config}

    @router.get("/users")
    def list_users():
        users = listar_usuarios()
        return {"ok": True, "users": users, "total": len(users)}

    @router.post("/users")
    def add_user(body: dict):
        nome = body.get("nome", "")
        papel = body.get("papel", "usuario")
        try:
            user = adicionar_usuario(nome, papel=papel)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True, "user": user, "users": listar_usuarios()}

    @router.put("/users/{user_id}")
    def update_user(user_id: str, body: dict):
        user = atualizar_usuario(user_id=user_id, **body)
        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")
        return {"ok": True, "user": user, "users": listar_usuarios()}

    @router.delete("/users/{user_id}")
    def delete_user(user_id: str):
        ok = remover_usuario(user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="user_not_found")
        return {"ok": True, "removed": True, "users": listar_usuarios()}

else:
    router = None

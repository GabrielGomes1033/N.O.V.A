from __future__ import annotations

try:
    from fastapi import HTTPException, Request, status
except Exception:
    Request = None
    HTTPException = None
    status = None

from core.painel_admin import carregar_config_painel, listar_usuarios
from core.runtime_guard import checar_rate_limit, validar_token


def rate_limit(limit: int = 120, window: int = 60):
    if Request is None:
        return None

    async def _check(request: Request):
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        chave = f"{ip}:{path}"

        ok, retry = checar_rate_limit(
            chave=chave,
            limite=limit,
            janela_s=window,
        )

        if not ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limited",
                    "retry_after_s": retry,
                },
            )

        return True

    return _check


def require_token():
    if Request is None:
        return None

    async def _check(request: Request):
        if not validar_token(request.headers):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized",
            )

        return True

    return _check


def _papel_permitido(role: str, allow: tuple[str, ...]) -> bool:
    normalized = str(role or "").strip().lower()

    if not normalized:
        return False

    if normalized == "admin":
        return True

    return normalized in allow


def require_rbac(*allow: str, error_detail: str = "rbac_forbidden"):
    if Request is None:
        return None

    allowed = tuple(str(item or "").strip().lower() for item in allow if str(item or "").strip())

    async def _check(request: Request):
        cfg = carregar_config_painel()

        if not bool(cfg.get("rbac_ativo", False)):
            return True

        role = str(request.headers.get("X-User-Role", "") or "").strip().lower()
        user = str(request.headers.get("X-User-Name", "") or "").strip().lower()

        if not role or not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="rbac_identity_required",
            )

        valido = False

        for item in listar_usuarios():
            if not bool(item.get("ativo", True)):
                continue

            nome = str(item.get("nome", "")).strip().lower()
            papel = str(item.get("papel", "")).strip().lower()

            if nome == user and papel == role:
                valido = True
                break

        if not valido:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="rbac_user_invalid",
            )

        if allowed and not _papel_permitido(role, allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_detail,
            )

        return True

    return _check

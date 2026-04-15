from __future__ import annotations

from http import HTTPStatus
from typing import Callable

from core.aprendizado_admin import (
    atualizar_aprendizado,
    exportar_aprendizado_json,
    listar_aprendizados,
    remover_aprendizado,
    salvar_aprendizado,
)


def handle_knowledge_get(*, path: str, send_json: Callable[..., None]) -> bool:
    if path != "/knowledge":
        return False

    send_json(exportar_aprendizado_json())
    return True


def handle_knowledge_post(*, path: str, body: dict, send_json: Callable[..., None]) -> bool:
    if path != "/knowledge":
        return False

    gatilho = str(body.get("gatilho", "")).strip()
    resposta = str(body.get("resposta", "")).strip()
    categoria = str(body.get("categoria", "geral")).strip() or "geral"
    if not gatilho or not resposta:
        send_json({"ok": False, "error": "invalid_payload"}, status=HTTPStatus.BAD_REQUEST)
        return True

    salvar_aprendizado(gatilho, resposta, categoria=categoria)
    send_json(exportar_aprendizado_json())
    return True


def handle_knowledge_put(
    *,
    path: str,
    body: dict,
    bool_ou_none: Callable[[object], bool | None],
    send_json: Callable[..., None],
) -> bool:
    if not path.startswith("/knowledge/"):
        return False

    item_id = path.split("/")[-1]
    item = atualizar_aprendizado(
        item_id=item_id,
        gatilho=body.get("gatilho"),
        resposta=body.get("resposta"),
        categoria=body.get("categoria"),
        ativo=bool_ou_none(body.get("ativo")),
    )
    if not item:
        send_json({"ok": False, "error": "knowledge_not_found"}, status=HTTPStatus.NOT_FOUND)
        return True

    send_json({"ok": True, "item": item})
    return True


def handle_knowledge_delete(*, path: str, send_json: Callable[..., None]) -> bool:
    if not path.startswith("/knowledge/"):
        return False

    item_id = path.split("/")[-1]
    ok = remover_aprendizado(item_id)
    if not ok:
        send_json({"ok": False, "error": "knowledge_not_found"}, status=HTTPStatus.NOT_FOUND)
        return True

    send_json({"ok": True, "removed": True, "items": listar_aprendizados()})
    return True

from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_AUDITORIA_SESSAO = pasta_dados_app() / "session_audit_chain.json"


def _db_padrao() -> dict[str, Any]:
    return {"version": 1, "items": []}


def _carregar_db() -> dict[str, Any]:
    db = carregar_json_seguro(ARQUIVO_AUDITORIA_SESSAO, _db_padrao())
    if not isinstance(db, dict):
        db = _db_padrao()
    if not isinstance(db.get("items"), list):
        db["items"] = []
    return db


def _hash_evento(
    *,
    prev_hash: str,
    quando: str,
    evento: str,
    usuario: str,
    ok: bool,
    detalhe: str,
) -> str:
    bruto = f"{prev_hash}|{quando}|{evento}|{usuario}|{int(ok)}|{detalhe}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def registrar_evento_sessao(
    evento: str,
    usuario: str = "",
    ok: bool = True,
    detalhe: str = "",
) -> dict[str, Any]:
    db = _carregar_db()
    items = db.get("items", [])
    prev_hash = str(items[-1].get("hash", "")) if items else ""
    quando = datetime.now().isoformat(timespec="seconds")
    item = {
        "quando": quando,
        "evento": str(evento or "").strip(),
        "usuario": str(usuario or "").strip(),
        "ok": bool(ok),
        "detalhe": str(detalhe or "").strip()[:280],
    }
    item["hash"] = _hash_evento(
        prev_hash=prev_hash,
        quando=item["quando"],
        evento=item["evento"],
        usuario=item["usuario"],
        ok=item["ok"],
        detalhe=item["detalhe"],
    )
    item["prev_hash"] = prev_hash
    items.append(item)
    db["items"] = items[-2000:]
    salvar_json_seguro(ARQUIVO_AUDITORIA_SESSAO, db)
    return item


def listar_auditoria_sessao(limit: int = 120) -> list[dict[str, Any]]:
    db = _carregar_db()
    items = db.get("items", [])
    lim = max(1, min(int(limit), 1000))
    return list(items[-lim:])


def validar_cadeia_auditoria() -> dict[str, Any]:
    items = listar_auditoria_sessao(limit=1000)
    prev_hash = ""
    for idx, item in enumerate(items):
        esperado = _hash_evento(
            prev_hash=prev_hash,
            quando=str(item.get("quando", "")),
            evento=str(item.get("evento", "")),
            usuario=str(item.get("usuario", "")),
            ok=bool(item.get("ok", False)),
            detalhe=str(item.get("detalhe", "")),
        )
        atual = str(item.get("hash", ""))
        if esperado != atual:
            return {
                "ok": False,
                "error": "chain_corrupted",
                "index": idx,
                "expected": esperado,
                "found": atual,
            }
        prev_hash = atual
    return {"ok": True, "items_validated": len(items)}

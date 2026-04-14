from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro
from core.jarvis_fase2 import enfileirar_tarefa


ARQUIVO_APPROVALS = pasta_dados_app() / "approvals_queue.json"


def _db_padrao() -> dict[str, Any]:
    return {"version": 1, "items": []}


def _load() -> dict[str, Any]:
    db = carregar_json_seguro(ARQUIVO_APPROVALS, _db_padrao())
    if not isinstance(db, dict):
        db = _db_padrao()
    if not isinstance(db.get("items"), list):
        db["items"] = []
    return db


def _save(db: dict[str, Any]) -> None:
    salvar_json_seguro(ARQUIVO_APPROVALS, db)


def criar_aprovacao_sensivel(
    objective: str,
    requested_by: str = "",
    reason: str = "ação sensível",
    required_approvals: int = 1,
) -> dict[str, Any]:
    db = _load()
    item = {
        "id": uuid.uuid4().hex[:12],
        "objective": str(objective or "").strip(),
        "requested_by": str(requested_by or "").strip() or "system",
        "reason": str(reason or "").strip() or "ação sensível",
        "status": "pending",
        "required_approvals": max(1, int(required_approvals)),
        "approvals": [],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "approved_by": "",
        "approved_at": "",
        "decision_note": "",
    }
    if not item["objective"]:
        return {"ok": False, "error": "objective_required"}
    items = db.get("items", [])
    items.append(item)
    db["items"] = items[-800:]
    _save(db)
    return {"ok": True, "request": item}


def listar_aprovacoes(status: str = "") -> list[dict[str, Any]]:
    items = _load().get("items", [])
    if status:
        s = status.strip().lower()
        return [x for x in items if str(x.get("status", "")).lower() == s]
    return items


def decidir_aprovacao(
    request_id: str,
    approve: bool,
    approver: str,
    note: str = "",
) -> dict[str, Any]:
    rid = str(request_id or "").strip()
    if not rid:
        return {"ok": False, "error": "request_id_required"}
    db = _load()
    items = db.get("items", [])
    for item in items:
        if str(item.get("id", "")) != rid:
            continue
        if str(item.get("status", "")) != "pending":
            return {"ok": False, "error": "already_decided"}
        aprob = str(approver or "").strip()
        if not aprob:
            return {"ok": False, "error": "approver_required"}
        required = max(1, int(item.get("required_approvals", 1) or 1))
        approvals = item.get("approvals", [])
        if not isinstance(approvals, list):
            approvals = []

        if not approve:
            item["status"] = "rejected"
            item["approved_by"] = aprob
            item["approved_at"] = datetime.now().isoformat(timespec="seconds")
            item["decision_note"] = str(note or "").strip()[:260]
            item["approvals"] = approvals
            _save(db)
            return {"ok": True, "message": "Solicitação rejeitada.", "request": item}

        if any(str(x.get("approver", "")).strip().lower() == aprob.lower() for x in approvals if isinstance(x, dict)):
            return {"ok": False, "error": "approver_already_signed"}

        approvals.append(
            {
                "approver": aprob,
                "when": datetime.now().isoformat(timespec="seconds"),
                "note": str(note or "").strip()[:260],
            }
        )
        item["approvals"] = approvals
        assinaturas = len(approvals)
        if assinaturas < required:
            item["decision_note"] = f"Aprovação parcial {assinaturas}/{required}."
            _save(db)
            return {
                "ok": True,
                "message": f"Aprovação parcial registrada ({assinaturas}/{required}).",
                "request": item,
            }

        item["status"] = "approved"
        item["approved_by"] = aprob
        item["approved_at"] = datetime.now().isoformat(timespec="seconds")
        item["decision_note"] = str(note or "").strip()[:260] or "Aprovado."
        _save(db)
        ok, msg = enfileirar_tarefa(item.get("objective", ""), origem="approval_flow")
        return {"ok": ok, "message": msg, "request": item}
    return {"ok": False, "error": "request_not_found"}

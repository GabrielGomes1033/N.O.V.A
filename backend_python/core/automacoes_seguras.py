from __future__ import annotations

from datetime import datetime
import uuid

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro
from core.assistente_plus import adicionar_lembrete


ARQUIVO_ROTINAS = pasta_dados_app() / "automacoes_seguras.json"


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _db_padrao() -> dict:
    return {"version": 1, "rules": []}


def _load_db() -> dict:
    raw = carregar_json_seguro(ARQUIVO_ROTINAS, _db_padrao())
    if not isinstance(raw, dict):
        raw = _db_padrao()
    if not isinstance(raw.get("rules"), list):
        raw["rules"] = []
    return raw


def _save_db(db: dict) -> None:
    salvar_json_seguro(ARQUIVO_ROTINAS, db)


def listar_rotinas() -> list[dict]:
    return _load_db().get("rules", [])


def adicionar_rotina(gatilho: str, acao_tipo: str, acao_valor: str, sensivel: bool = False) -> dict:
    g = (gatilho or "").strip().lower()
    t = (acao_tipo or "").strip().lower()
    v = (acao_valor or "").strip()
    if len(g) < 2:
        raise ValueError("Gatilho muito curto.")
    if t not in {"responder", "lembrete"}:
        raise ValueError("Tipo de ação inválido. Use responder|lembrete.")
    if len(v) < 2:
        raise ValueError("Ação vazia.")

    rule = {
        "id": uuid.uuid4().hex[:12],
        "gatilho": g,
        "acao_tipo": t,
        "acao_valor": v,
        "sensivel": bool(sensivel),
        "ativo": True,
        "criado_em": _agora(),
        "executado_em": "",
    }

    db = _load_db()
    rules = db.get("rules", [])
    rules.append(rule)
    db["rules"] = rules[-200:]
    _save_db(db)
    return rule


def remover_rotina(rule_id: str) -> bool:
    db = _load_db()
    rules = db.get("rules", [])
    novo = [r for r in rules if str(r.get("id")) != str(rule_id)]
    if len(novo) == len(rules):
        return False
    db["rules"] = novo
    _save_db(db)
    return True


def _marcar_execucao(rule_id: str) -> None:
    db = _load_db()
    rules = db.get("rules", [])
    for r in rules:
        if str(r.get("id")) == str(rule_id):
            r["executado_em"] = _agora()
            break
    db["rules"] = rules
    _save_db(db)


def detectar_rotina_disparada(mensagem: str) -> dict | None:
    m = (mensagem or "").lower().strip()
    if not m:
        return None
    for r in listar_rotinas():
        if not bool(r.get("ativo", True)):
            continue
        gat = str(r.get("gatilho", "")).strip().lower()
        if gat and gat in m:
            return r
    return None


def processar_confirmacao_rotina(user_input: str, contexto: dict) -> str | None:
    pend = contexto.get("rotina_pendente")
    if not isinstance(pend, dict):
        return None

    txt = (user_input or "").strip().lower()
    sim = txt in {"sim", "s", "ok", "confirmar", "pode"}
    nao = txt in {"nao", "não", "n", "cancelar", "cancela"}
    if not (sim or nao):
        return "Confirme a rotina com 'sim' ou 'não'."

    if nao:
        contexto["rotina_pendente"] = None
        return "Rotina cancelada."

    rule = pend.get("rule") if isinstance(pend.get("rule"), dict) else None
    if not rule:
        contexto["rotina_pendente"] = None
        return "Rotina pendente inválida."

    contexto["rotina_pendente"] = None
    return executar_rotina(rule)


def executar_rotina(rule: dict) -> str:
    rid = str(rule.get("id", ""))
    t = str(rule.get("acao_tipo", "")).lower().strip()
    v = str(rule.get("acao_valor", "")).strip()

    if t == "responder":
        _marcar_execucao(rid)
        return f"Rotina executada: {v}"

    if t == "lembrete":
        out = adicionar_lembrete(v)
        _marcar_execucao(rid)
        if out.get("ok"):
            return f"Rotina executada e lembrete salvo: {v}"
        return "Rotina disparou, mas não consegui salvar o lembrete."

    return "Rotina detectada, mas tipo de ação não suportado."

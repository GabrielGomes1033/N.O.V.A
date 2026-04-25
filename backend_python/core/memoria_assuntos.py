from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_MEMORIA_ASSUNTOS = pasta_dados_app() / "memoria_assuntos.json"

ASSUNTOS = {
    "programacao": [
        "python",
        "java",
        "javascript",
        "flutter",
        "backend",
        "frontend",
        "api",
        "codigo",
        "algoritmo",
    ],
    "agentes_ia": [
        "agente",
        "ia",
        "inteligencia artificial",
        "llm",
        "prompt",
        "rag",
        "modelo",
    ],
    "financeiro": [
        "dolar",
        "euro",
        "bitcoin",
        "ethereum",
        "mercado",
        "investimento",
        "acao",
        "ações",
        "cotacao",
        "cotação",
    ],
    "juridico": [
        "contrato",
        "clausula",
        "cláusula",
        "lei",
        "processo",
        "juridico",
        "jurídico",
        "compliance",
    ],
    "saude": [
        "saude",
        "saúde",
        "medico",
        "médico",
        "diagnostico",
        "diagnóstico",
        "medicamento",
        "sintoma",
    ],
    "seguranca": [
        "seguranca",
        "segurança",
        "token",
        "senha",
        "2fa",
        "ciberseguranca",
        "cibersegurança",
        "audit",
        "auditoria",
    ],
    "produto": [
        "roadmap",
        "produto",
        "usuário",
        "usuario",
        "ux",
        "feature",
        "requisito",
        "mvp",
    ],
}


def _db_padrao() -> dict[str, Any]:
    return {"version": 1, "subjects": {}, "updated_at": ""}


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _tokenize(t: str) -> list[str]:
    raw = re.sub(r"[^a-z0-9à-ÿ\s]", " ", (t or "").lower())
    return [w for w in raw.split() if len(w) >= 2]


def _load() -> dict[str, Any]:
    db = carregar_json_seguro(ARQUIVO_MEMORIA_ASSUNTOS, _db_padrao())
    if not isinstance(db, dict):
        db = _db_padrao()
    if not isinstance(db.get("subjects"), dict):
        db["subjects"] = {}
    return db


def _save(db: dict[str, Any]) -> None:
    db["updated_at"] = _agora()
    salvar_json_seguro(ARQUIVO_MEMORIA_ASSUNTOS, db)


def detectar_assuntos(texto: str) -> list[str]:
    t = (texto or "").lower()
    tokens = set(_tokenize(t))
    hits: list[str] = []
    for assunto, palavras in ASSUNTOS.items():
        for p in palavras:
            p_norm = p.strip().lower()
            if not p_norm:
                continue
            if " " in p_norm:
                if p_norm in t:
                    hits.append(assunto)
                    break
            else:
                if p_norm in tokens:
                    hits.append(assunto)
                    break
    return hits


def aprender_assuntos(
    *,
    texto: str,
    origem: str = "chat",
    resumo: str = "",
) -> dict[str, Any]:
    assuntos = detectar_assuntos(texto)
    if not assuntos:
        return {"ok": True, "updated": 0, "subjects": []}

    db = _load()
    subjects = db.get("subjects", {})
    for a in assuntos:
        atual = subjects.get(a, {})
        if not isinstance(atual, dict):
            atual = {}
        atual["count"] = int(atual.get("count", 0) or 0) + 1
        atual["last_seen"] = _agora()
        atual["last_source"] = origem
        if resumo.strip():
            atuais = atual.get("summaries", [])
            if not isinstance(atuais, list):
                atuais = []
            atuais.append(resumo.strip()[:320])
            atual["summaries"] = atuais[-30:]
        toks = _tokenize(texto)
        freq = atual.get("keywords", {})
        if not isinstance(freq, dict):
            freq = {}
        for tok in toks[:220]:
            freq[tok] = int(freq.get(tok, 0) or 0) + 1
        atual["keywords"] = dict(sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:40])
        subjects[a] = atual
    db["subjects"] = subjects
    _save(db)
    return {"ok": True, "updated": len(assuntos), "subjects": assuntos}


def perfil_assuntos(limit: int = 8) -> dict[str, Any]:
    db = _load()
    subjects = db.get("subjects", {})
    items = []
    for k, v in subjects.items():
        if not isinstance(v, dict):
            continue
        kws = v.get("keywords", {})
        if isinstance(kws, dict):
            top = [kk for kk, _ in list(kws.items())[:8]]
        else:
            top = []
        items.append(
            {
                "subject": k,
                "count": int(v.get("count", 0) or 0),
                "last_seen": str(v.get("last_seen", "") or ""),
                "last_source": str(v.get("last_source", "") or ""),
                "top_keywords": top,
                "latest_summary": (
                    (v.get("summaries", []) or [""])[-1]
                    if isinstance(v.get("summaries"), list) and v.get("summaries")
                    else ""
                ),
            }
        )
    items.sort(key=lambda x: x["count"], reverse=True)
    return {
        "ok": True,
        "updated_at": db.get("updated_at", ""),
        "items": items[: max(1, int(limit))],
    }


def dica_contextual_para_pergunta(pergunta: str) -> str:
    assuntos = detectar_assuntos(pergunta)
    if not assuntos:
        return ""
    perf = perfil_assuntos(limit=20).get("items", [])
    if not isinstance(perf, list):
        return ""
    for a in assuntos:
        for item in perf:
            if str(item.get("subject", "")) != a:
                continue
            resumo = str(item.get("latest_summary", "") or "").strip()
            kws = item.get("top_keywords", [])
            kws_txt = ", ".join(kws[:5]) if isinstance(kws, list) else ""
            if resumo:
                return f"Contexto aprendido em {a}: {resumo}"
            if kws_txt:
                return f"Contexto aprendido em {a} (palavras-chave): {kws_txt}."
    return ""

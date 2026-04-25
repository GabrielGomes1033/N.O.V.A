from __future__ import annotations

from datetime import datetime
from typing import Any

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_TRACES = pasta_dados_app() / "agent_traces.json"


def _padrao() -> dict:
    return {"version": 1, "items": []}


def _carregar() -> dict:
    raw = carregar_json_seguro(ARQUIVO_TRACES, _padrao())
    if not isinstance(raw, dict):
        raw = _padrao()
    if not isinstance(raw.get("items"), list):
        raw["items"] = []
    return raw


def registrar_trace(
    *,
    route: str,
    mensagem: str,
    resposta: str,
    evento: str,
    duracao_ms: float,
    ok: bool,
    contexto: dict[str, Any] | None = None,
) -> dict:
    raw = _carregar()
    items = raw.get("items", [])
    if not isinstance(items, list):
        items = []

    ctx = contexto if isinstance(contexto, dict) else {}
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "route": route,
        "evento": (evento or "chat").strip().lower(),
        "ok": bool(ok),
        "duracao_ms": round(float(duracao_ms), 2),
        "mensagem_preview": (mensagem or "").strip()[:180],
        "resposta_preview": (resposta or "").strip()[:240],
        "intencao": str(ctx.get("ultima_intencao", "")).strip(),
    }
    items.append(entry)
    raw["items"] = items[-800:]
    salvar_json_seguro(ARQUIVO_TRACES, raw)
    return entry


def listar_traces(limit: int = 100) -> list[dict]:
    raw = _carregar()
    items = raw.get("items", [])
    if not isinstance(items, list):
        return []
    lim = max(1, min(int(limit), 500))
    return items[-lim:]


def resumo_traces(janela: int = 200) -> dict:
    items = listar_traces(limit=max(1, min(janela, 500)))
    total = len(items)
    erros = len([i for i in items if not bool(i.get("ok", True))])
    latencias = [float(i.get("duracao_ms", 0.0)) for i in items if isinstance(i, dict)]
    lat_media = (sum(latencias) / len(latencias)) if latencias else 0.0

    por_evento: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        ev = str(item.get("evento", "chat")).strip().lower() or "chat"
        slot = por_evento.setdefault(ev, {"total": 0, "erros": 0})
        slot["total"] += 1
        if not bool(item.get("ok", True)):
            slot["erros"] += 1

    taxa_erro = (erros / total * 100.0) if total else 0.0
    alertas = []
    if taxa_erro >= 15.0:
        alertas.append("Taxa de erro elevada nos últimos traces.")
    if lat_media >= 2200:
        alertas.append("Latência média alta detectada.")

    return {
        "total": total,
        "erros": erros,
        "taxa_erro_pct": round(taxa_erro, 2),
        "latencia_media_ms": round(lat_media, 2),
        "por_evento": por_evento,
        "alertas": alertas,
    }

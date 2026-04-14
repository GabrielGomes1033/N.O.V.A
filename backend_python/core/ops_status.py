from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.agent_observability import listar_traces
from core.jarvis_fase2 import carregar_estado


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slo_resposta(traces: list[dict[str, Any]], alvo_ms: float = 1800.0) -> dict[str, Any]:
    validos = []
    ok_count = 0
    for t in traces:
        try:
            dur = float(t.get("duracao_ms", 0.0))
        except (TypeError, ValueError):
            dur = 0.0
        validos.append(dur)
        if bool(t.get("ok", True)):
            ok_count += 1
    total = len(validos)
    if total == 0:
        return {"ok_rate_pct": 100.0, "p95_ms": 0.0, "slo_target_ms": alvo_ms, "slo_met": True}
    ordenados = sorted(validos)
    idx = int(max(0, min(len(ordenados) - 1, round((len(ordenados) - 1) * 0.95))))
    p95 = ordenados[idx]
    ok_rate = (ok_count / total) * 100.0
    return {
        "ok_rate_pct": round(ok_rate, 2),
        "p95_ms": round(p95, 2),
        "slo_target_ms": alvo_ms,
        "slo_met": p95 <= alvo_ms and ok_rate >= 98.0,
    }


def status_operacional() -> dict[str, Any]:
    traces = listar_traces(limit=300)
    estado = carregar_estado()
    queue = estado.get("queue", []) if isinstance(estado.get("queue"), list) else []
    history = estado.get("history", []) if isinstance(estado.get("history"), list) else []
    now = datetime.now()
    ult_hora = now - timedelta(hours=1)
    recentes = []
    for h in history:
        when = str(h.get("concluido_em", "") or "")
        if not when:
            continue
        try:
            if datetime.fromisoformat(when) >= ult_hora:
                recentes.append(h)
        except ValueError:
            pass
    falhas_recentes = len([x for x in recentes if x.get("status") == "falhou"])
    concluidas_recentes = len([x for x in recentes if x.get("status") == "concluido"])
    total_recentes = max(1, falhas_recentes + concluidas_recentes)
    taxa_falha = (falhas_recentes / total_recentes) * 100.0
    slo = _slo_resposta(traces)
    return {
        "ok": True,
        "timestamp": _agora(),
        "runtime": {
            "enabled": bool(estado.get("enabled", False)),
            "pending": len([x for x in queue if x.get("status") == "pendente"]),
            "running": len([x for x in queue if x.get("status") == "executando"]),
            "circuit_open_until": str(estado.get("circuit_open_until", "") or ""),
            "failures_consecutive": int(estado.get("runtime_failures_consecutive", 0) or 0),
        },
        "throughput_last_hour": {
            "completed": concluidas_recentes,
            "failed": falhas_recentes,
            "failure_rate_pct": round(taxa_falha, 2),
        },
        "slo": slo,
    }

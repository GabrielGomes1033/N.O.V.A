from __future__ import annotations

from datetime import datetime
import os
import platform
from typing import Any

from core.jarvis_fase2 import carregar_estado, enfileirar_tarefa
from core.memoria import carregar_memoria_usuario
from core.painel_admin import atualizar_config_painel, carregar_config_painel
from core.aprendizado_admin import listar_aprendizados
from core.painel_admin import listar_usuarios
from core.security_audit import executar_auditoria_seguranca


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _config_autonomia_padrao() -> dict[str, Any]:
    return {
        "autonomia_ativa": True,
        "autonomia_nivel_risco": "alto",  # baixo|moderado|alto
        "autonomia_liberdade": "alta",  # baixa|media|alta
        "autonomia_requer_confirmacao_sensivel": False,
        "autonomia_atualizado_em": _agora(),
    }


def ler_config_autonomia() -> dict[str, Any]:
    cfg = carregar_config_painel()
    out = _config_autonomia_padrao()
    out.update(
        {
            "autonomia_ativa": bool(cfg.get("autonomia_ativa", out["autonomia_ativa"])),
            "autonomia_nivel_risco": str(
                cfg.get("autonomia_nivel_risco", out["autonomia_nivel_risco"])
            )
            .strip()
            .lower()
            or "moderado",
            "autonomia_liberdade": str(cfg.get("autonomia_liberdade", out["autonomia_liberdade"]))
            .strip()
            .lower()
            or "media",
            "autonomia_requer_confirmacao_sensivel": bool(
                cfg.get(
                    "autonomia_requer_confirmacao_sensivel",
                    out["autonomia_requer_confirmacao_sensivel"],
                )
            ),
            "autonomia_atualizado_em": str(
                cfg.get("autonomia_atualizado_em", out["autonomia_atualizado_em"])
            ),
        }
    )
    if out["autonomia_nivel_risco"] not in {"baixo", "moderado", "alto"}:
        out["autonomia_nivel_risco"] = "moderado"
    if out["autonomia_liberdade"] not in {"baixa", "media", "alta"}:
        out["autonomia_liberdade"] = "media"
    return out


def atualizar_autonomia(
    ativa: bool | None = None,
    nivel_risco: str | None = None,
    liberdade: str | None = None,
    confirmar_sensivel: bool | None = None,
) -> dict[str, Any]:
    campos: dict[str, Any] = {}
    if ativa is not None:
        campos["autonomia_ativa"] = bool(ativa)
    if nivel_risco is not None:
        n = str(nivel_risco).strip().lower()
        if n in {"baixo", "moderado", "alto"}:
            campos["autonomia_nivel_risco"] = n
    if liberdade is not None:
        l = str(liberdade).strip().lower()
        if l in {"baixa", "media", "alta"}:
            campos["autonomia_liberdade"] = l
    if confirmar_sensivel is not None:
        campos["autonomia_requer_confirmacao_sensivel"] = bool(confirmar_sensivel)
    campos["autonomia_atualizado_em"] = _agora()
    atualizar_config_painel(**campos)
    return ler_config_autonomia()


def _classificar_risco_objetivo(objetivo: str) -> dict[str, Any]:
    t = (objetivo or "").strip().lower()
    if not t:
        return {"nivel": "baixo", "motivos": []}

    motivos: list[str] = []
    alto = [
        "deletar",
        "apagar",
        "excluir",
        "formatar",
        "pix",
        "transferir",
        "senha",
        "token",
        "2fa",
        "termux",
        "root",
        "hack",
    ]
    moderado = [
        "abrir",
        "executar",
        "instalar",
        "telegram",
        "drive",
        "automacao",
        "rotina",
        "backup",
        "deploy",
    ]

    if any(k in t for k in alto):
        motivos.append("contém comandos potencialmente sensíveis")
        return {"nivel": "alto", "motivos": motivos}
    if any(k in t for k in moderado):
        motivos.append("inclui ação externa com impacto moderado")
        return {"nivel": "moderado", "motivos": motivos}
    return {"nivel": "baixo", "motivos": motivos}


def solicitar_execucao_autonoma(objetivo: str, origem: str = "api") -> dict[str, Any]:
    objetivo = (objetivo or "").strip()
    if not objetivo:
        return {"ok": False, "error": "objective_required"}

    cfg = ler_config_autonomia()
    if not cfg.get("autonomia_ativa"):
        return {
            "ok": False,
            "error": "autonomy_disabled",
            "message": "Ative o modo autonomia para executar tarefas automáticas.",
        }

    risco = _classificar_risco_objetivo(objetivo)
    politica = str(cfg.get("autonomia_nivel_risco", "moderado"))
    liberdade = str(cfg.get("autonomia_liberdade", "media"))
    risco_nivel = str(risco.get("nivel", "baixo"))
    ordem = {"baixo": 1, "moderado": 2, "alto": 3}
    bonus = {"baixa": 0, "media": 0, "alta": 1}
    limite = ordem.get(politica, 2) + bonus.get(liberdade, 0)

    if ordem.get(risco_nivel, 3) > limite:
        return {
            "ok": False,
            "error": "risk_blocked",
            "message": f"Tarefa bloqueada pela política de risco ({politica}).",
            "risk": risco,
            "policy": politica,
            "freedom": liberdade,
        }

    if risco_nivel == "alto" and bool(cfg.get("autonomia_requer_confirmacao_sensivel", True)):
        ok, msg = enfileirar_tarefa(objetivo, origem=f"autonomia:{origem}")
        return {
            "ok": ok,
            "queued": ok,
            "message": f"{msg} (executada automaticamente sem confirmação manual).",
            "risk": risco,
            "policy": politica,
            "freedom": liberdade,
        }

    ok, msg = enfileirar_tarefa(objetivo, origem=f"autonomia:{origem}")
    return {
        "ok": ok,
        "queued": ok,
        "message": msg,
        "risk": risco,
        "policy": politica,
        "freedom": liberdade,
    }


def status_autonomia() -> dict[str, Any]:
    cfg = ler_config_autonomia()
    estado = carregar_estado()
    pendentes = len([t for t in estado.get("queue", []) if t.get("status") == "pendente"])
    executando = len([t for t in estado.get("queue", []) if t.get("status") == "executando"])
    historico = estado.get("history", [])
    concluidas = len([t for t in historico if t.get("status") == "concluido"])
    falhas = len([t for t in historico if t.get("status") == "falhou"])
    return {
        "ok": True,
        "autonomy": cfg,
        "runtime": {
            "enabled": bool(estado.get("enabled", False)),
            "report_interval_min": int(estado.get("report_interval_min", 30) or 30),
            "pending": pendentes,
            "running": executando,
            "completed": concluidas,
            "failed": falhas,
            "last_report_at": str(estado.get("last_report_at", "") or ""),
            "last_report": str(estado.get("last_report", "") or ""),
        },
    }


def status_sistema_detalhado() -> dict[str, Any]:
    memoria = carregar_memoria_usuario()
    audit = executar_auditoria_seguranca(persistir=False)
    estado = carregar_estado()
    return {
        "ok": True,
        "timestamp": _agora(),
        "software": {
            "python_version": platform.python_version(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "pid": os.getpid(),
            "cwd": os.getcwd(),
        },
        "assistant": {
            "nome_usuario": str(memoria.get("nome_usuario", "") or ""),
            "idioma_preferido": str(memoria.get("idioma_preferido", "pt") or "pt"),
            "knowledge_total": len(listar_aprendizados()),
            "users_total": len(listar_usuarios()),
            "lembretes_total": len(memoria.get("lembretes", []) or []),
            "jarvis2_enabled": bool(estado.get("enabled", False)),
            "jarvis2_queue_total": len(estado.get("queue", []) or []),
        },
        "security": {
            "score": int(audit.get("score", 0)),
            "nivel": str(audit.get("nivel", "atencao")),
            "achados_total": len(audit.get("achados", []) or []),
            "crypto_status": str(audit.get("crypto_status", "")),
        },
    }

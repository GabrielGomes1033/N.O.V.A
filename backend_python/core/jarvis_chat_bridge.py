from __future__ import annotations

import re
from typing import Any

from core.orchestrator import get_default_orchestrator
from core.response_style import style_response


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _is_affirmative(text: str) -> bool:
    normalized = _clean(text).lower()
    return normalized in {
        "sim",
        "s",
        "ok",
        "confirmo",
        "pode",
        "execute",
        "executar",
        "aprovado",
        "yes",
        "y",
    }


def _is_negative(text: str) -> bool:
    normalized = _clean(text).lower()
    return normalized in {
        "nao",
        "não",
        "n",
        "cancelar",
        "cancela",
        "negativo",
        "no",
    }


def _pending_tool_subject(tool_name: str) -> str:
    tool = str(tool_name or "").strip()
    if tool == "schedule_calendar_event":
        return "esse agendamento na Google Agenda"
    return tool or "essa acao"


def jarvis_user_id(context: dict[str, Any] | None) -> str:
    ctx = context or {}
    return (
        str(ctx.get("nome_usuario", "")).strip()
        or str(ctx.get("admin_usuario", "")).strip()
        or "default"
    )


def process_pending_tool_confirmation(
    text: str,
    context: dict[str, Any] | None,
    *,
    mode: str = "normal",
) -> dict[str, Any] | None:
    ctx = context or {}
    pending = ctx.get("jarvis_tool_pending")
    if not isinstance(pending, dict) or not pending:
        return None

    if _is_negative(text):
        ctx["jarvis_tool_pending"] = None
        return {
            "handled": True,
            "reply": style_response("Acao cancelada. Nenhuma acao foi executada.", modo=mode),
        }

    if not _is_affirmative(text):
        tool_name = _pending_tool_subject(str(pending.get("tool_name", "")).strip())
        return {
            "handled": True,
            "reply": style_response(
                f"Preciso de uma confirmacao objetiva para executar {tool_name}. Responda sim ou nao.",
                modo=mode,
            ),
        }

    orchestrator = get_default_orchestrator()
    result = orchestrator.execute_tool(
        jarvis_user_id(ctx),
        str(pending.get("tool_name", "")).strip(),
        pending.get("params") or {},
        prompt_text=str(pending.get("prompt_text", "")).strip(),
        mode=str(pending.get("mode", mode)).strip() or mode,
    )
    ctx["jarvis_tool_pending"] = None
    return {"handled": True, **result}


def try_jarvis_tool_flow(
    text: str,
    context: dict[str, Any] | None,
    *,
    mode: str = "normal",
) -> dict[str, Any] | None:
    orchestrator = get_default_orchestrator()
    result = orchestrator.handle(jarvis_user_id(context), text, mode=mode, auto_approve=False)
    if result.get("approval_needed"):
        if isinstance(context, dict):
            context["jarvis_tool_pending"] = {
                "tool_name": result.get("tool_name"),
                "params": result.get("params") or {},
                "prompt_text": text,
                "mode": mode,
            }
        return result

    if result.get("decision_type") == "tool_call":
        return result
    return None


def jarvis_status_snapshot() -> dict[str, Any]:
    orchestrator = get_default_orchestrator()
    return {
        "ok": True,
        "assistant": "NOVA",
        "mode": "jarvis_phase1",
        "tools_total": len(orchestrator.tools.names()),
        "tools": orchestrator.tools.names(),
        "memory_backend": "sqlite",
        "voice_phase": "planned",
    }

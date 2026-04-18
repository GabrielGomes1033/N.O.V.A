from __future__ import annotations

from typing import Callable

from core.jarvis_chat_bridge import process_pending_tool_confirmation
from core.orchestrator import get_default_orchestrator

_PENDING_STRUCTURED_CHAT: dict[str, dict] = {}


def handle_chat_post(
    *,
    path: str,
    body: dict,
    process_message: Callable[[str], str],
    send_json: Callable[[dict], None],
) -> bool:
    if path != "/chat":
        return False

    if any(key in body for key in ("text", "user_id", "mode", "auto_approve")):
        orchestrator = get_default_orchestrator()
        user_id = str(body.get("user_id", "default")).strip() or "default"
        mode = str(body.get("mode", "normal")).strip() or "normal"
        text = str(body.get("text", body.get("message", ""))).strip()
        if user_id in _PENDING_STRUCTURED_CHAT:
            ctx = {
                "nome_usuario": user_id,
                "jarvis_tool_pending": _PENDING_STRUCTURED_CHAT.get(user_id),
            }
            pending_result = process_pending_tool_confirmation(text, ctx, mode=mode)
            if isinstance(pending_result, dict) and pending_result.get("handled"):
                next_pending = ctx.get("jarvis_tool_pending")
                if isinstance(next_pending, dict) and next_pending:
                    _PENDING_STRUCTURED_CHAT[user_id] = next_pending
                else:
                    _PENDING_STRUCTURED_CHAT.pop(user_id, None)
                send_json({"ok": True, **pending_result})
                return True

        result = orchestrator.handle(
            user_id,
            text,
            mode=mode,
            auto_approve=bool(body.get("auto_approve", False)),
        )
        if result.get("approval_needed"):
            _PENDING_STRUCTURED_CHAT[user_id] = {
                "tool_name": result.get("tool_name"),
                "params": result.get("params") or {},
                "prompt_text": text,
                "mode": mode,
            }
        else:
            _PENDING_STRUCTURED_CHAT.pop(user_id, None)
        send_json({"ok": True, **result})
        return True

    message = str(body.get("message", "")).strip()
    reply = process_message(message)
    send_json({"ok": True, "reply": reply})
    return True

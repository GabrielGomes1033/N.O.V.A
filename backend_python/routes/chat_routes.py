from __future__ import annotations

from typing import Callable


def handle_chat_post(
    *,
    path: str,
    body: dict,
    process_message: Callable[[str], str],
    send_json: Callable[[dict], None],
) -> bool:
    if path != "/chat":
        return False

    message = str(body.get("message", "")).strip()
    reply = process_message(message)
    send_json({"ok": True, "reply": reply})
    return True

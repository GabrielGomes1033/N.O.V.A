from __future__ import annotations

import os
from typing import Any


def listen_for_wakeword(keyword: str = "nova") -> dict[str, Any]:
    access_key = os.getenv("PORCUPINE_ACCESS_KEY") or os.getenv("NOVA_PORCUPINE_ACCESS_KEY", "")
    if not access_key:
        return {
            "ok": False,
            "enabled": False,
            "keyword": keyword,
            "reason": "porcupine_access_key_missing",
        }
    return {
        "ok": False,
        "enabled": False,
        "keyword": keyword,
        "reason": "wakeword_runtime_not_started",
    }

from __future__ import annotations

from datetime import datetime
from typing import Any


NOVA_API_VERSION = "2.1.0"


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def build_api_health(*, entrypoint: str) -> dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "service": "nova-api",
        "assistant": "NOVA",
        "mode": "jarvis_phase1",
        "api_version": NOVA_API_VERSION,
        "entrypoint": entrypoint,
        "transport": "http",
        "timestamp": _agora(),
        "capabilities": {
            "chat": True,
            "memory": True,
            "semantic_memory": True,
            "knowledge": True,
            "actions": True,
            "translation": True,
            "voice_status": True,
            "voice_neural": True,
            "documents": True,
            "location": True,
            "reminders": True,
            "calendar": True,
            "security": True,
            "autonomy": True,
            "ops_status": True,
        },
        "platform_support": {
            "android": "full",
            "web": "full",
            "desktop": "full",
            "ios": "partial",
        },
        "client_hints": {
            "android_emulator_base_url": "http://10.0.2.2:8000",
            "desktop_base_url": "http://127.0.0.1:8000",
            "android_device_requires_manual_ip": True,
        },
        "endpoints": [
            "/health",
            "/chat",
            "/jarvis/status",
            "/actions/tools",
            "/memory/recent",
            "/voice/status",
            "/documents/analyze",
            "/ops/status",
        ],
    }

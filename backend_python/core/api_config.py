from __future__ import annotations

import os


DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8000


def resolve_api_host(default: str = DEFAULT_API_HOST) -> str:
    host = str(os.getenv("NOVA_API_HOST", default) or "").strip()
    return host or default


def resolve_api_port(default: int = DEFAULT_API_PORT) -> int:
    raw = (
        str(os.getenv("NOVA_API_PORT", "") or "").strip()
        or str(os.getenv("PORT", "") or "").strip()
    )

    if not raw:
        return default

    try:
        port = int(raw)
    except ValueError:
        return default

    if 1 <= port <= 65535:
        return port
    return default


def build_local_base_url(host: str, *, scheme: str = "http", port: int | None = None) -> str:
    final_port = port if port is not None else resolve_api_port()
    return f"{scheme}://{host}:{final_port}"

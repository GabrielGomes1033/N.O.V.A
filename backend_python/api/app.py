from __future__ import annotations

try:
    from fastapi import FastAPI
except Exception:
    FastAPI = None

from core.api_profile import NOVA_API_VERSION, build_api_health
from api.routes_actions import router as actions_router
from api.routes_chat import router as chat_router
from api.routes_memory import router as memory_router
from api.routes_voice import router as voice_router


def create_app():
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Run `pip install -r backend_python/requirements.txt` first."
        )

    app = FastAPI(
        title="NOVA API",
        version=NOVA_API_VERSION,
        description="Base Jarvis Fase 1 com orquestrador, memoria SQLite e ferramentas seguras.",
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return build_api_health(entrypoint="fastapi_app")

    app.include_router(chat_router)
    app.include_router(memory_router)
    app.include_router(actions_router)
    app.include_router(voice_router)
    return app

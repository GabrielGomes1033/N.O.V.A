from __future__ import annotations

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except Exception:
    FastAPI = None
    CORSMiddleware = None

from core.api_profile import NOVA_API_VERSION, build_api_health
from .routes_actions import router as actions_router
from .routes_chat import router as chat_router
from .routes_compat import router as compat_router
from .routes_location import router as location_router
from .routes_memory import router as memory_router
from .routes_system import router as system_router
from .routes_voice import router as voice_router

try:
    from .routes_admin import router as admin_router
except Exception:
    admin_router = None


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

    if CORSMiddleware is not None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "X-API-Key",
                "X-User-Role",
                "X-User-Name",
            ],
        )

    @app.get("/health")
    def health() -> dict[str, object]:
        return build_api_health(entrypoint="fastapi_app")

    app.include_router(chat_router)
    app.include_router(memory_router)
    app.include_router(actions_router)
    app.include_router(voice_router)

    if compat_router is not None:
        app.include_router(compat_router)

    if admin_router is not None:
        app.include_router(admin_router)

    if system_router is not None:
        app.include_router(system_router)

    if location_router is not None:
        app.include_router(location_router)

    return app

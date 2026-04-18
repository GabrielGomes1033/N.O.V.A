from __future__ import annotations

try:
    from fastapi import APIRouter
except Exception:
    APIRouter = None


if APIRouter is not None:
    router = APIRouter(prefix="/voice", tags=["voice"])

    @router.get("/status")
    def voice_status() -> dict:
        return {
            "ok": True,
            "enabled": False,
            "phase": "planned",
            "message": "Voice pipeline is scaffolded and ready for Phase 2 wiring.",
        }
else:
    router = None

from __future__ import annotations

try:
    from fastapi import APIRouter, Depends
except Exception:
    APIRouter = None
    Depends = None

from .dependencies import rate_limit

if APIRouter is not None:
    router = APIRouter(prefix="/voice", tags=["voice"], dependencies=[Depends(rate_limit(120))])

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

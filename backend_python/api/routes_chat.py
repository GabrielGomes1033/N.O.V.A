from __future__ import annotations

try:
    from fastapi import APIRouter
except Exception:
    APIRouter = None

from core.orchestrator import get_default_orchestrator
from models.schemas import ChatRequest, ChatResponse


if APIRouter is not None:
    router = APIRouter(tags=["chat"])

    @router.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        orchestrator = get_default_orchestrator()
        result = orchestrator.handle(
            req.user_id,
            req.text,
            mode=req.mode,
            auto_approve=req.auto_approve,
        )
        return ChatResponse(ok=True, **result)
else:
    router = None

from __future__ import annotations

try:
    from fastapi import APIRouter
except Exception:
    APIRouter = None

from core.orchestrator import get_default_orchestrator
from models.schemas import ToolApprovalRequest


if APIRouter is not None:
    router = APIRouter(prefix="/actions", tags=["actions"])

    @router.get("/tools")
    def list_tools() -> dict:
        orchestrator = get_default_orchestrator()
        return {"ok": True, "tools": orchestrator.tools.describe()}

    @router.post("/approve", response_model=dict)
    def approve_action(req: ToolApprovalRequest) -> dict:
        orchestrator = get_default_orchestrator()
        result = orchestrator.execute_tool(
            req.user_id,
            req.tool_name,
            req.params,
            prompt_text=req.prompt_text,
            mode=req.mode,
        )
        return {"ok": True, **result}
else:
    router = None

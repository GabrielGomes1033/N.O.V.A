from __future__ import annotations

try:
    from fastapi import APIRouter, Query, Depends
except Exception:
    APIRouter = None
    Query = None
    Depends = None

from .dependencies import rate_limit
from core.orchestrator import get_default_orchestrator
from models.schemas import MemoryCreateRequest, MemorySearchResponse


if APIRouter is not None:
    router = APIRouter(prefix="/memory", tags=["memory"], dependencies=[Depends(rate_limit(120))])

    @router.get("/recent", response_model=MemorySearchResponse)
    def recent_memories_query(user_id: str = Query(...), limit: int = 10) -> MemorySearchResponse:
        store = get_default_orchestrator().memory
        items = store.search_recent(user_id=user_id, limit=limit)
        return MemorySearchResponse(ok=True, items=items, total=len(items))

    @router.get("/recent/{user_id}", response_model=MemorySearchResponse)
    def recent_memories(user_id: str, limit: int = 10) -> MemorySearchResponse:
        store = get_default_orchestrator().memory
        items = store.search_recent(user_id=user_id, limit=limit)
        return MemorySearchResponse(ok=True, items=items, total=len(items))

    @router.get("/search", response_model=MemorySearchResponse)
    def search_memories(
        user_id: str = Query(...), query: str = Query(...), limit: int = 10
    ) -> MemorySearchResponse:
        store = get_default_orchestrator().memory
        items = store.search(user_id=user_id, query=query, limit=limit)
        return MemorySearchResponse(ok=True, items=items, total=len(items))

    @router.post("", response_model=dict)
    def save_memory(req: MemoryCreateRequest) -> dict:
        store = get_default_orchestrator().memory
        item = store.save(
            user_id=req.user_id,
            category=req.category,
            content=req.content,
            importance=req.importance,
            scope=req.scope,
            source="api_memory",
        )
        return {"ok": True, "item": item}

else:
    router = None

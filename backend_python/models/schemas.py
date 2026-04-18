from __future__ import annotations

from typing import Any

try:
    from pydantic import BaseModel, Field
except Exception:
    class BaseModel:
        def __init__(self, **data: Any) -> None:
            annotations = getattr(self.__class__, "__annotations__", {})
            for key in annotations:
                default = getattr(self.__class__, key, None)
                if isinstance(default, list):
                    default = list(default)
                elif isinstance(default, dict):
                    default = dict(default)
                setattr(self, key, data.get(key, default))

        def model_dump(self) -> dict[str, Any]:
            return {
                key: getattr(self, key)
                for key in getattr(self.__class__, "__annotations__", {})
            }

    def Field(default: Any = None, default_factory: Any = None, **_: Any) -> Any:
        if default_factory is not None:
            return default_factory()
        return default


class ChatRequest(BaseModel):
    user_id: str = Field(default="default")
    text: str = Field(default="")
    mode: str = Field(default="normal")
    auto_approve: bool = Field(default=False)


class ChatResponse(BaseModel):
    ok: bool = Field(default=True)
    reply: str = Field(default="")
    decision_type: str = Field(default="response")
    approval_needed: bool = Field(default=False)
    tool_name: str | None = Field(default=None)
    params: dict[str, Any] = Field(default_factory=dict)
    tool_result: dict[str, Any] = Field(default_factory=dict)
    context: list[dict[str, Any]] = Field(default_factory=list)


class MemoryCreateRequest(BaseModel):
    user_id: str = Field(default="default")
    category: str = Field(default="contexto")
    content: str = Field(default="")
    importance: int = Field(default=1)
    scope: str = Field(default="longo_prazo")


class MemorySearchResponse(BaseModel):
    ok: bool = Field(default=True)
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0)


class ToolApprovalRequest(BaseModel):
    user_id: str = Field(default="default")
    tool_name: str = Field(default="")
    params: dict[str, Any] = Field(default_factory=dict)
    prompt_text: str = Field(default="")
    mode: str = Field(default="normal")

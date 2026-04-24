from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pydantic import BaseModel, Field
else:
    try:
        from pydantic import BaseModel, Field
    except Exception:

        class BaseModel:
            def __init__(self, **data: Any) -> None:
                annotations = getattr(self.__class__, "__annotations__", {})
                for key in annotations:
                    default = getattr(self.__class__, key, None)
                    if default is Ellipsis:
                        default = None
                    elif isinstance(default, list):
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
    text: str = Field(..., min_length=1, description="Mensagem do usuário")


class ChatResponse(BaseModel):
    ok: bool = True
    reply: str = ""


class LocationData(BaseModel):
    label: str = ""
    latitude: str = ""
    longitude: str = ""
    updated_at: str = ""


class LocationUpdateRequest(BaseModel):
    label: Optional[str] = Field(default=None, description="Label descritivo da localização")
    latitude: str = Field(..., description="Latitude em formato string")
    longitude: str = Field(..., description="Longitude em formato string")


class LocationReverseRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude (-90 a 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude (-180 a 180)")


class LocationResponse(BaseModel):
    ok: bool = True
    location: Optional[LocationData] = None
    error: Optional[str] = None


class RateLimitError(BaseModel):
    ok: bool = False
    error: str = "rate_limited"
    retry_after_s: int = 0


class MemoryCreateRequest(BaseModel):
    user_id: str = "default"
    category: str = "contexto"
    content: str = Field(..., min_length=1, description="Conteúdo da memória")
    importance: int = Field(default=1, ge=1, le=5, description="Importância de 1 a 5")
    scope: str = "longo_prazo"


class MemorySearchResponse(BaseModel):
    ok: bool = True
    items: list = []
    total: int = 0


class ToolApprovalRequest(BaseModel):
    user_id: str = "default"
    tool_name: str = Field(..., min_length=1, description="Nome da ferramenta")
    params: dict = {}
    prompt_text: str = ""
    mode: str = "normal"

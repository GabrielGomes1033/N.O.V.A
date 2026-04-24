from __future__ import annotations

from datetime import datetime

try:
    from fastapi import APIRouter, HTTPException, status, Query, Depends
except Exception:
    APIRouter = None
    Depends = None

from .dependencies import rate_limit
from models.schemas import (
    LocationUpdateRequest,
    LocationReverseRequest,
    LocationResponse,
    LocationData,
)
from core.memoria import carregar_memoria_usuario, salvar_memoria_usuario
from integrations.maps_provider import reverse_geocode


if APIRouter is not None:
    router = APIRouter(
        tags=["location"], prefix="/location", dependencies=[Depends(rate_limit(120))]
    )

    @router.get("/current", response_model=LocationResponse)
    def get_current_location() -> LocationResponse:
        """Retorna a localização atual armazenada na memória do usuário."""
        memoria = carregar_memoria_usuario()
        location = LocationData(
            label=str(memoria.get("ultima_localizacao", "") or ""),
            latitude=str(memoria.get("ultima_latitude", "") or ""),
            longitude=str(memoria.get("ultima_longitude", "") or ""),
            updated_at=str(memoria.get("ultima_localizacao_em", "") or ""),
        )
        return LocationResponse(ok=True, location=location)

    @router.get("/reverse", response_model=LocationResponse)
    def reverse_location(
        lat: float = Query(..., ge=-90, le=90, description="Latitude (-90 a 90)"),
        lon: float = Query(..., ge=-180, le=180, description="Longitude (-180 a 180)"),
    ) -> LocationResponse:
        """Faz reverse geocoding de coordenadas para endereço legível."""
        out = reverse_geocode(lat, lon)
        if not out.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=out.get("error", "reverse_geocode_failed"),
            )
        label = str(out.get("label", "") or out.get("display_name", "")).strip()
        location = LocationData(
            label=label,
            latitude=str(lat),
            longitude=str(lon),
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        return LocationResponse(ok=True, location=location)

    @router.post("/update", response_model=LocationResponse)
    def update_location(req: LocationUpdateRequest) -> LocationResponse:
        """Atualiza a localização do usuário na memória."""
        memoria = carregar_memoria_usuario()
        memoria["ultima_localizacao"] = req.label or ""
        memoria["ultima_latitude"] = req.latitude
        memoria["ultima_longitude"] = req.longitude
        memoria["ultima_localizacao_em"] = datetime.now().isoformat(timespec="seconds")
        salvar_memoria_usuario(memoria)

        location = LocationData(
            label=req.label or "",
            latitude=req.latitude,
            longitude=req.longitude,
            updated_at=memoria["ultima_localizacao_em"],
        )
        return LocationResponse(ok=True, location=location)

else:
    router = None

from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote_plus

import requests


NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "NOVA-Assistant/1.0 (maps)"
TIMEOUT_PADRAO = 8


def _headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.6",
    }


def gerar_link_busca_maps(query: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus((query or '').strip())}"


def gerar_link_rota_maps(destino: str, latitude: str = "", longitude: str = "") -> str:
    origem = ""
    if latitude and longitude:
        origem = f"&origin={quote_plus(f'{latitude},{longitude}')}"
    return f"https://www.google.com/maps/dir/?api=1&destination={quote_plus((destino or '').strip())}{origem}"


def reverse_geocode(latitude: float, longitude: float) -> dict:
    params = {
        "format": "jsonv2",
        "lat": f"{float(latitude):.6f}",
        "lon": f"{float(longitude):.6f}",
        "zoom": 18,
        "addressdetails": 1,
    }
    try:
        resp = requests.get(
            f"{NOMINATIM_BASE}/reverse",
            params=params,
            headers=_headers(),
            timeout=TIMEOUT_PADRAO,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"ok": False, "error": f"reverse_geocode_fail: {exc}"}

    display = str(data.get("display_name", "")).strip()
    address = data.get("address") if isinstance(data.get("address"), dict) else {}
    principal = (
        address.get("road")
        or address.get("neighbourhood")
        or address.get("suburb")
        or address.get("city")
        or address.get("town")
        or address.get("village")
        or display
    )
    return {
        "ok": True,
        "label": str(principal or display).strip(),
        "display_name": display,
        "latitude": str(data.get("lat", "")).strip(),
        "longitude": str(data.get("lon", "")).strip(),
        "address": address,
        "maps_url": gerar_link_busca_maps(display or f"{latitude},{longitude}"),
    }


def search_places(query: str, latitude: float | None = None, longitude: float | None = None, limit: int = 3) -> dict:
    consulta = str(query or "").strip()
    if not consulta:
        return {"ok": False, "error": "query_required", "items": []}

    params: dict[str, str | int] = {
        "format": "jsonv2",
        "q": consulta,
        "limit": max(1, min(int(limit), 6)),
        "addressdetails": 1,
    }
    if latitude is not None and longitude is not None:
        lat = float(latitude)
        lon = float(longitude)
        delta = Decimal("0.18")
        north = Decimal(str(lat)) + delta
        south = Decimal(str(lat)) - delta
        east = Decimal(str(lon)) + delta
        west = Decimal(str(lon)) - delta
        params["viewbox"] = f"{west},{north},{east},{south}"
        params["bounded"] = 0

    try:
        resp = requests.get(
            f"{NOMINATIM_BASE}/search",
            params=params,
            headers=_headers(),
            timeout=TIMEOUT_PADRAO,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"ok": False, "error": f"search_places_fail: {exc}", "items": []}

    items = []
    if isinstance(data, list):
        for raw in data:
            if not isinstance(raw, dict):
                continue
            display = str(raw.get("display_name", "")).strip()
            address = raw.get("address") if isinstance(raw.get("address"), dict) else {}
            items.append(
                {
                    "name": str(raw.get("name", "")).strip()
                    or str(address.get("attraction") or address.get("shop") or address.get("road") or display).strip(),
                    "display_name": display,
                    "latitude": str(raw.get("lat", "")).strip(),
                    "longitude": str(raw.get("lon", "")).strip(),
                    "type": str(raw.get("type", "")).strip(),
                    "category": str(raw.get("category", "")).strip(),
                    "address": address,
                    "maps_url": gerar_link_busca_maps(display or consulta),
                }
            )
    return {"ok": True, "query": consulta, "items": items}

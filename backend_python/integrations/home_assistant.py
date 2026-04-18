from __future__ import annotations

import os
from typing import Any

import requests


ALLOWED_DOMAINS = {"light", "switch", "scene", "script", "cover", "fan", "climate", "media_player"}


def control_home(entity_id: str, action: str, **service_data: Any) -> dict[str, Any]:
    entity = str(entity_id or "").strip()
    desired_action = str(action or "").strip().lower()
    if not entity:
        return {"ok": False, "error": "entity_id_required"}
    if "." not in entity:
        return {"ok": False, "error": "invalid_entity_id", "entity_id": entity}

    domain = entity.split(".", 1)[0].lower()
    if domain not in ALLOWED_DOMAINS:
        return {"ok": False, "error": "domain_not_allowed", "entity_id": entity}

    if desired_action not in {"turn_on", "turn_off"}:
        return {"ok": False, "error": "unsupported_action", "action": desired_action}

    base_url = (
        os.getenv("HOME_ASSISTANT_URL")
        or os.getenv("NOVA_HOME_ASSISTANT_URL")
        or "http://localhost:8123/api"
    ).rstrip("/")
    token = os.getenv("HOME_ASSISTANT_TOKEN") or os.getenv("NOVA_HOME_ASSISTANT_TOKEN")
    if not token:
        return {"ok": False, "error": "home_assistant_not_configured", "entity_id": entity}

    url = f"{base_url}/services/{domain}/{desired_action}"
    payload = {"entity_id": entity}
    payload.update(service_data)
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        body = response.json() if response.text else {}
        return {
            "ok": True,
            "provider": "home_assistant",
            "entity_id": entity,
            "action": desired_action,
            "result": body,
        }
    except Exception as exc:
        return {
            "ok": False,
            "provider": "home_assistant",
            "entity_id": entity,
            "action": desired_action,
            "error": str(exc),
        }

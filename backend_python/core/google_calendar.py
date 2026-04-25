from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
from typing import Any

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except Exception:
    service_account = None
    build = None


SCOPE_CALENDAR = ["https://www.googleapis.com/auth/calendar"]
_PT_WEEKDAY = {
    "segunda": 0,
    "segunda-feira": 0,
    "terca": 1,
    "terça": 1,
    "terca-feira": 1,
    "terça-feira": 1,
    "quarta": 2,
    "quarta-feira": 2,
    "quinta": 3,
    "quinta-feira": 3,
    "sexta": 4,
    "sexta-feira": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _normalize_natural_times(text: str) -> str:
    normalized = _clean(text)

    def replace_hour_minute(match: re.Match[str]) -> str:
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or "0")
        return f"{hour:02d}:{minute:02d}"

    normalized = re.sub(
        r"\b(?P<hour>\d{1,2})h(?P<minute>\d{2})?\b",
        replace_hour_minute,
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\b(?P<hour>\d{1,2})\s*horas?\b",
        lambda match: f"{int(match.group('hour')):02d}:00",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _calendar_timezone() -> str:
    return (
        _clean(
            os.getenv("GOOGLE_CALENDAR_TIMEZONE")
            or os.getenv("NOVA_GOOGLE_CALENDAR_TIMEZONE")
            or "America/Sao_Paulo"
        )
        or "America/Sao_Paulo"
    )


def _calendar_id() -> str:
    return (
        _clean(os.getenv("GOOGLE_CALENDAR_ID") or os.getenv("NOVA_GOOGLE_CALENDAR_ID") or "primary")
        or "primary"
    )


def _credenciais_disponiveis() -> bool:
    return bool(
        os.getenv("GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE")
        or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE")
    )


def _carregar_credenciais():
    if service_account is None:
        return None

    raw_json = _clean(
        os.getenv("GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
    )
    file_path = _clean(
        os.getenv("GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE")
        or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE")
    )
    try:
        if raw_json:
            info = json.loads(raw_json)
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=SCOPE_CALENDAR,
            )
        if file_path and Path(file_path).is_file():
            return service_account.Credentials.from_service_account_file(
                file_path,
                scopes=SCOPE_CALENDAR,
            )
    except Exception:
        return None
    return None


def _calendar_service():
    if build is None:
        return None
    creds = _carregar_credenciais()
    if creds is None:
        return None
    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception:
        return None


def looks_like_calendar_request(text: str) -> bool:
    normalized = _normalize_natural_times(text).lower()
    if not normalized:
        return False
    has_schedule_verb = bool(
        re.search(
            (
                r"\b(?:agende|agendar|agendamento|marque|marcar|adicione|adicionar|coloque|colocar|"
                r"crie|criar)\b"
            ),
            normalized,
        )
    )
    if not has_schedule_verb:
        return False
    has_event_hint = any(
        token in normalized
        for token in (
            "agenda",
            "evento",
            "compromisso",
            "reuniao",
            "reunião",
            "tarefa",
            "google agenda",
            "google calendar",
        )
    )
    has_time_marker = bool(
        re.search(
            (
                r"\b(?:amanha|amanhã|hoje|segunda|segunda-feira|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo)\b"
                r"|"
                r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"
                r"|"
                r"\b\d{4}-\d{2}-\d{2}\b"
                r"|"
                r"\b\d{1,2}:\d{2}\b"
                r"|"
                r"\b\d{1,2}h(?:\d{2})?\b"
            ),
            normalized,
        )
    )
    return has_time_marker or has_event_hint


def _parse_date(date_text: str, base_now: datetime) -> datetime.date:
    value = _clean(date_text).lower()
    if value in {"hoje"}:
        return base_now.date()
    if value in {"amanha", "amanhã"}:
        return (base_now + timedelta(days=1)).date()
    if value in _PT_WEEKDAY:
        target = _PT_WEEKDAY[value]
        delta = (target - base_now.weekday()) % 7
        if delta == 0:
            delta = 7
        return (base_now + timedelta(days=delta)).date()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return datetime.strptime(value, "%Y-%m-%d").date()
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", value):
        day, month, year = value.split("/")
        year_int = int(year)
        if year_int < 100:
            year_int += 2000
        return datetime(year_int, int(month), int(day)).date()
    raise ValueError("date_not_supported")


def _parse_time(time_text: str) -> tuple[int, int]:
    hour, minute = _clean(time_text).split(":")
    return int(hour), int(minute)


def _extract_duration_minutes(text: str) -> int:
    normalized = _normalize_natural_times(text).lower()
    match = re.search(r"\bpor\s+(\d{1,3})\s*(min|minuto|minutos)\b", normalized)
    if match:
        return max(5, int(match.group(1)))
    match = re.search(r"\bpor\s+(\d{1,2})\s*(h|hora|horas)\b", normalized)
    if match:
        return max(15, int(match.group(1)) * 60)
    return 60


def _extract_datetime_window(text: str, base_now: datetime) -> dict[str, Any]:
    raw = _normalize_natural_times(text)
    patterns = (
        r"(?P<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|amanha|amanhã|hoje|segunda(?:-feira)?|terca(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sabado|sábado|domingo)\s*(?:as|às)?\s*(?P<start>\d{1,2}:\d{2})(?:\s*(?:ate|até|a)\s*(?P<end>\d{1,2}:\d{2}))?",
        r"(?P<start>\d{1,2}:\d{2})\s*(?:ate|até|a)\s*(?P<end>\d{1,2}:\d{2})\s*(?:de\s+)?(?P<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|amanha|amanhã|hoje|segunda(?:-feira)?|terca(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sabado|sábado|domingo)",
        r"(?P<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|amanha|amanhã|hoje|segunda(?:-feira)?|terca(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sabado|sábado|domingo)",
        r"(?:as|às)\s*(?P<start>\d{1,2}:\d{2})(?:\s*(?:ate|até|a)\s*(?P<end>\d{1,2}:\d{2}))?",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        date_text = _clean(match.groupdict().get("date") or "")
        start_text = _clean(match.groupdict().get("start") or "")
        end_text = _clean(match.groupdict().get("end") or "")
        assumed_date = False
        if not date_text:
            if not start_text:
                continue
            hour, minute = _parse_time(start_text)
            candidate = base_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= base_now:
                candidate += timedelta(days=1)
            start_dt = candidate
            assumed_date = True
        else:
            date_value = _parse_date(date_text, base_now)
            if not start_text:
                start_text = "09:00"
                assumed_date = True
            hour, minute = _parse_time(start_text)
            start_dt = datetime.combine(
                date_value,
                datetime.min.time(),
            ).replace(hour=hour, minute=minute)
        if end_text:
            end_hour, end_minute = _parse_time(end_text)
            end_dt = start_dt.replace(hour=end_hour, minute=end_minute)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
        else:
            end_dt = start_dt + timedelta(minutes=_extract_duration_minutes(raw))
        return {
            "start_at": start_dt,
            "end_at": end_dt,
            "matched_text": match.group(0),
            "assumed_date": assumed_date,
        }
    raise ValueError("date_time_not_found")


def _strip_schedule_prefix(text: str) -> str:
    stripped = _clean(text)
    stripped = re.sub(r"^(?:nova[\s,:-]+)?", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(
        (
            r"^(?:agende|agendar|agenda|marque|marcar|crie|criar|adicione|adicionar|coloque)\s+"
            r"(?:(?:um|uma)\s+)?"
            r"(?:(?:na|no)\s+(?:agenda(?:\s+do\s+google)?|google\s+calendar|google\s+agenda)\s+)?"
        ),
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    return stripped.strip(" ,:-")


def parse_calendar_event_request(
    request_text: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    raw = _clean(request_text)
    raw = _normalize_natural_times(raw)
    if not raw:
        return {"ok": False, "error": "request_text_required"}

    base_now = now or datetime.now()
    try:
        window = _extract_datetime_window(raw, base_now)
    except Exception:
        return {
            "ok": False,
            "error": "date_time_not_found",
            "message": (
                "Nao consegui identificar data e hora. Exemplo: "
                "agende reunião com cliente amanhã às 15:00"
            ),
        }

    title = _strip_schedule_prefix(raw)
    matched = _clean(str(window.get("matched_text", "")))
    if matched:
        title = title.replace(matched, " ").strip(" ,:-")
    title = re.sub(
        r"\b(?:na agenda(?: do google)?|no google calendar|na google agenda)\b",
        " ",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\b(?:em|para|de|no|na)\s*$", " ", title, flags=re.IGNORECASE)
    title = _clean(title).strip(" ,:-")
    if not title:
        title = "Compromisso"

    assumption_notes: list[str] = []
    if window.get("assumed_date"):
        assumption_notes.append("Sem data explícita, usei a próxima ocorrência compatível.")
    if _extract_duration_minutes(raw) == 60 and not re.search(
        r"\b(?:ate|até|a)\s+\d{1,2}:\d{2}\b", raw, flags=re.IGNORECASE
    ):
        assumption_notes.append(
            "Como você não informou horário final, usei duração padrão de 1 hora."
        )

    return {
        "ok": True,
        "title": title,
        "description": f"Pedido original: {raw}",
        "start_at": window["start_at"].isoformat(timespec="minutes"),
        "end_at": window["end_at"].isoformat(timespec="minutes"),
        "timezone": _calendar_timezone(),
        "calendar_id": _calendar_id(),
        "assumptions": assumption_notes,
        "request_text": raw,
    }


def status_google_calendar() -> dict[str, Any]:
    if not _credenciais_disponiveis():
        return {
            "ok": False,
            "configured": False,
            "message": (
                "Google Calendar nao configurado. Defina GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON "
                "ou GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE e compartilhe a agenda com essa conta."
            ),
        }
    service = _calendar_service()
    if service is None:
        return {
            "ok": False,
            "configured": False,
            "message": "Google Calendar indisponivel. Credenciais invalidas ou biblioteca ausente.",
        }
    return {
        "ok": True,
        "configured": True,
        "calendar_id": _calendar_id(),
        "timezone": _calendar_timezone(),
    }


def create_google_calendar_event(
    *,
    title: str,
    start_at: str,
    end_at: str,
    description: str = "",
    location: str = "",
    calendar_id: str = "",
    timezone: str = "",
) -> dict[str, Any]:
    service = _calendar_service()
    if service is None:
        return {
            "ok": False,
            "error": "google_calendar_unavailable",
            "message": (
                "Google Calendar nao configurado. Defina as credenciais e compartilhe a agenda "
                "com a service account."
            ),
        }

    summary = _clean(title)
    if len(summary) < 2:
        return {"ok": False, "error": "title_required"}

    start_value = _clean(start_at)
    end_value = _clean(end_at)
    if not start_value or not end_value:
        return {"ok": False, "error": "start_end_required"}

    target_calendar = _clean(calendar_id) or _calendar_id()
    tz = _clean(timezone) or _calendar_timezone()
    event_body = {
        "summary": summary,
        "description": _clean(description),
        "location": _clean(location),
        "start": {
            "dateTime": start_value,
            "timeZone": tz,
        },
        "end": {
            "dateTime": end_value,
            "timeZone": tz,
        },
    }
    try:
        created = (
            service.events()
            .insert(
                calendarId=target_calendar,
                body=event_body,
                sendUpdates="none",
            )
            .execute()
        )
        return {
            "ok": True,
            "provider": "google_calendar",
            "calendar_id": target_calendar,
            "event_id": str(created.get("id", "")).strip(),
            "html_link": str(created.get("htmlLink", "")).strip(),
            "title": summary,
            "start_at": start_value,
            "end_at": end_value,
            "timezone": tz,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": "google_calendar_insert_failed",
            "message": f"Falha ao criar evento na Google Agenda: {exc}",
        }

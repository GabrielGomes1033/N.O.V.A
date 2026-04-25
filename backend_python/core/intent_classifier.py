from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from core.google_calendar import looks_like_calendar_request


SEARCH_PREFIXES = (
    "pesquise",
    "pesquisar",
    "procure",
    "procurar",
    "busque",
    "buscar",
    "me atualize",
    "ultimas noticias",
    "ultimas informacoes",
    "ultimas novidades",
)


@dataclass(frozen=True)
class IntentDecision:
    type: str = "response"
    tool_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _normalize_search_target(query: str) -> str:
    target = _clean(query).strip(" :,-?")
    if not target:
        return ""

    search_engines = r"(?:google|bing|duckduckgo|duck\s+duck\s+go|brave|serpapi)"
    directed_prefixes = (
        (
            r"^(?:na|no|em)\s+wikipedia\s+(?:sobre\s+)?(.+)$",
            lambda m: f"{m.group(1).strip()} wikipedia",
        ),
        (
            r"^wikipedia\s+(?:sobre\s+)?(.+)$",
            lambda m: f"{m.group(1).strip()} wikipedia",
        ),
        (
            r"^(.+?)\s+(?:na|no|em)\s+wikipedia$",
            lambda m: f"{m.group(1).strip()} wikipedia",
        ),
        (
            rf"^(?:na|no|em)\s+{search_engines}\s+(?:sobre\s+)?(.+)$",
            lambda m: m.group(1).strip(),
        ),
        (
            rf"^(.+?)\s+(?:na|no|em)\s+{search_engines}$",
            lambda m: m.group(1).strip(),
        ),
        (
            r"^(?:na|no|em)\s+(?:internet|web)\s+(?:sobre\s+)?(.+)$",
            lambda m: m.group(1).strip(),
        ),
    )

    for pattern, formatter in directed_prefixes:
        match = re.match(pattern, target, flags=re.IGNORECASE)
        if match:
            target = formatter(match).strip()
            break

    return target.strip(" :,-?")


def _extract_search_query(text: str) -> str:
    msg = _clean(text)
    if not msg:
        return ""
    query = re.sub(
        r"^(pesquise|pesquisar|procure|procurar|busque|buscar|me atualize sobre|atualize sobre|ultimas noticias sobre|ultimas informacoes sobre)\s+",
        "",
        msg,
        flags=re.IGNORECASE,
    )
    query = re.sub(r"^(sobre|na internet|na web)\s+", "", query, flags=re.IGNORECASE)
    return _normalize_search_target(query)


def _extract_reminder(text: str) -> tuple[str, str]:
    msg = _clean(text)
    when = ""
    match = re.search(
        r"\b(amanha|amanhã|hoje|as\s+\d{1,2}:\d{2}|\d{1,2}:\d{2}|\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})\b",
        msg,
        flags=re.IGNORECASE,
    )
    if match:
        when = match.group(1)

    title = msg
    for prefix in ("/lembrar", "me lembre de", "me lembre", "lembre-me de", "lembre"):
        if title.lower().startswith(prefix):
            title = title[len(prefix) :].strip(" :,-")
            break
    return title, when


def _extract_memory_payload(text: str) -> tuple[str, str]:
    msg = _clean(text)
    lowered = msg.lower()
    category = "contexto"
    if any(token in lowered for token in ("prefiro", "favorito", "gosto de")):
        category = "preferencia"
    elif any(token in lowered for token in ("meu nome", "eu moro", "eu trabalho", "sou")):
        category = "perfil"
    elif "projeto" in lowered:
        category = "projeto"

    content = re.sub(
        r"^(lembre que|guarde que|salve que|anote que|memorize que)\s+",
        "",
        msg,
        flags=re.IGNORECASE,
    ).strip(" :,-")
    return category, content


def _extract_project_name(text: str) -> tuple[str, str]:
    msg = _clean(text)
    description = ""
    quoted = re.findall(r'"([^"]{2,120})"', msg)
    if quoted:
        return quoted[0].strip(), description
    match = re.search(
        r"(?:projeto(?: novo)?|crie um projeto|criar projeto|novo projeto)\s+(?:chamado\s+)?(.+)$",
        msg,
        flags=re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip(" .,:;-")
        return name, description
    return "", description


def _extract_home_action(text: str) -> tuple[str, str]:
    msg = _clean(text)
    lowered = msg.lower()
    action = ""
    if any(token in lowered for token in ("ligar", "acender", "turn on", "ativar", "abrir")):
        action = "turn_on"
    elif any(
        token in lowered for token in ("desligar", "apagar", "turn off", "desativar", "fechar")
    ):
        action = "turn_off"

    entity = ""
    match = re.search(
        r"\b(light|switch|scene|script|cover|fan|climate|media_player)\.[\w.-]+\b", msg
    )
    if match:
        entity = match.group(0)
    return entity, action


def classify_intent(text: str) -> IntentDecision:
    msg = _clean(text)
    if not msg:
        return IntentDecision()

    lowered = msg.lower()

    if lowered.startswith(("lembre que", "guarde que", "salve que", "anote que", "memorize que")):
        category, content = _extract_memory_payload(msg)
        if content:
            return IntentDecision(
                type="tool_call",
                tool_name="save_memory",
                params={"category": category, "content": content},
            )

    if any(
        token in lowered
        for token in ("ligar", "desligar", "acender", "apagar", "turn on", "turn off")
    ):
        entity_id, action = _extract_home_action(msg)
        if entity_id and action:
            return IntentDecision(
                type="tool_call",
                tool_name="control_home",
                params={"entity_id": entity_id, "action": action},
            )

    if lowered.startswith(("/lembrar", "me lembre", "lembre")):
        title, when = _extract_reminder(msg)
        if title:
            return IntentDecision(
                type="tool_call",
                tool_name="create_reminder",
                params={"title": title, "when": when},
            )

    if any(
        token in lowered
        for token in (
            "o que voce lembra",
            "o que voce sabe sobre",
            "busque na memoria",
            "procure na memoria",
        )
    ):
        query = re.sub(
            r"^(o que voce lembra sobre|o que voce sabe sobre|busque na memoria|procure na memoria)\s+",
            "",
            msg,
            flags=re.IGNORECASE,
        ).strip(" :,-?")
        if query:
            return IntentDecision(
                type="tool_call", tool_name="search_memory", params={"query": query}
            )

    if lowered.startswith(("/resumir", "resuma", "sumarize", "summarize")):
        summary_input = re.sub(
            r"^(\/resumir|resuma|sumarize|summarize)\s*", "", msg, flags=re.IGNORECASE
        )
        if summary_input:
            return IntentDecision(
                type="tool_call",
                tool_name="summarize_text",
                params={"text": summary_input},
            )

    if lowered.startswith(SEARCH_PREFIXES) or any(
        token in lowered for token in ("ultimas", "ultimos", "recentes", "noticias", "informacoes")
    ):
        query = _extract_search_query(msg)
        if query:
            return IntentDecision(type="tool_call", tool_name="search_web", params={"query": query})

    if "projeto" in lowered and any(
        token in lowered for token in ("crie", "criar", "novo", "abra", "abrir")
    ):
        name, description = _extract_project_name(msg)
        if name:
            return IntentDecision(
                type="tool_call",
                tool_name="create_project",
                params={"name": name, "description": description},
            )

    if looks_like_calendar_request(msg):
        return IntentDecision(
            type="tool_call",
            tool_name="schedule_calendar_event",
            params={"request_text": msg},
        )

    return IntentDecision()

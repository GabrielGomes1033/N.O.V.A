from __future__ import annotations

import os
from typing import Any
import re
import unicodedata

import requests


TRANSLATE_TIMEOUT = 12
_TRANSLATION_SHORTCUT_LIMIT = 6

LANGUAGE_ALIASES = {
    "pt": "pt",
    "pt-br": "pt",
    "portugues": "pt",
    "portuguese": "pt",
    "ingles": "en",
    "english": "en",
    "en": "en",
    "espanhol": "es",
    "espanol": "es",
    "espanol latino": "es",
    "spanish": "es",
    "es": "es",
    "frances": "fr",
    "french": "fr",
    "fr": "fr",
    "alemao": "de",
    "german": "de",
    "de": "de",
    "italiano": "it",
    "italian": "it",
    "it": "it",
}

LANGUAGE_LABELS_PT = {
    "pt": "portugues",
    "en": "ingles",
    "es": "espanhol",
    "fr": "frances",
    "de": "alemao",
    "it": "italiano",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _normalize_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def normalize_language_code(raw_language: str) -> str:
    candidate = _normalize_ascii(_clean(raw_language)).replace("_", "-")
    if not candidate:
        return ""
    if candidate in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[candidate]
    if candidate.startswith("pt"):
        return "pt"
    if candidate.startswith("en"):
        return "en"
    if candidate.startswith("es"):
        return "es"
    if candidate.startswith("fr"):
        return "fr"
    if candidate.startswith("de"):
        return "de"
    if candidate.startswith("it"):
        return "it"
    return ""


def language_label_pt(language_code: str) -> str:
    code = normalize_language_code(language_code)
    if not code:
        return "outro idioma"
    return LANGUAGE_LABELS_PT.get(code, code)


def detect_target_language(text: str) -> str:
    normalized = _normalize_ascii(text)
    aliases = sorted(LANGUAGE_ALIASES.keys(), key=len, reverse=True)
    for alias in aliases:
        if re.search(rf"\b{re.escape(alias)}\b", normalized):
            return LANGUAGE_ALIASES[alias]
    return ""


def _looks_like_short_translation_followup(text: str) -> bool:
    normalized = _normalize_ascii(text)
    words = [token for token in normalized.split() if token]
    if not words or len(words) > _TRANSLATION_SHORTCUT_LIMIT:
        return False

    if any(token in normalized for token in ("traduz", "traduza", "traduzir", "translate")):
        return False

    if normalized.startswith(("em ", "para ", "in ", "to ")):
        return True

    if any(
        ref in normalized for ref in ("isso", "essa", "esse", "pesquisa", "resposta", "resultado")
    ):
        if re.search(r"\b(?:em|para|in|to)\b", normalized):
            return True

    return False


def parse_search_translation_request(text: str) -> dict[str, str] | None:
    message = _clean(text)
    if not message:
        return None

    normalized = _normalize_ascii(message)
    target_language = detect_target_language(message)
    search_reference = any(ref in normalized for ref in ("pesquisa", "resultado", "resposta"))
    explicit_translation = search_reference and any(
        token in normalized
        for token in (
            "traduz",
            "traduza",
            "traducao",
            "translate",
            "translation",
            "version in",
            "versao em",
        )
    )
    spoken_translation = (
        bool(target_language)
        and any(
            token in normalized
            for token in (
                "fale",
                "fala",
                "me fale",
                "leia",
                "ler",
                "diga",
                "manda",
                "mostre",
                "me devolva",
                "responda",
            )
        )
        and any(
            ref in normalized
            for ref in ("isso", "essa", "esse", "pesquisa", "resultado", "resposta")
        )
    )

    if (
        not explicit_translation
        and not spoken_translation
        and not _looks_like_short_translation_followup(message)
    ):
        return None

    target_language = target_language or "pt"
    return {
        "target_language": target_language,
        "target_label_pt": language_label_pt(target_language),
    }


def _extract_explicit_text_translation_parts(message: str) -> tuple[str, str]:
    patterns = (
        r'^\s*(?:traduz(?:a|ir)?|translate)\s+(?:o\s+)?(?:texto\s+)?["\'](?P<text>.+?)["\']\s+(?:para|em|to|in)\s+(?P<lang>.+?)\s*$',
        r"^\s*(?:traduz(?:a|ir)?|translate)\s+(?:o\s+)?(?:texto\s+)?(?:para|em|to|in)\s+(?P<lang>.+?)\s*[:\-]\s*(?P<text>.+?)\s*$",
        r"^\s*(?:traduz(?:a|ir)?|translate)\s+(?:para|em|to|in)\s+(?P<lang>[A-Za-zÀ-ÿ_-]+(?:\s+[A-Za-zÀ-ÿ_-]+)?)\s+(?P<text>.+?)\s*$",
        r"^\s*(?:traduz(?:a|ir)?|translate)\s+(?:o\s+)?(?:texto\s+)?(?P<text>.+?)\s+(?:para|em|to|in)\s+(?P<lang>.+?)\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, message, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        return _clean(match.group("text")), _clean(match.group("lang"))
    return "", ""


def _looks_like_contextual_text_reference(text: str) -> bool:
    normalized = _normalize_ascii(text)
    if not normalized:
        return False
    return bool(
        re.fullmatch(
            (
                r"(?:isso(?: aqui)?|esse(?: texto| trecho| resultado)?|essa(?: frase| resposta| mensagem| pesquisa)?|"
                r"esta(?: frase| resposta| mensagem)?|o texto|o trecho|a frase|a resposta|"
                r"ultima(?: resposta| mensagem| frase| pesquisa)|resposta anterior|mensagem anterior)"
            ),
            normalized,
        )
    )


def parse_text_translation_request(text: str) -> dict[str, str] | None:
    message = _clean(text)
    if not message:
        return None

    normalized = _normalize_ascii(message)
    if not any(token in normalized for token in ("traduz", "traduza", "traduzir", "translate")):
        return None

    source_text, raw_target_language = _extract_explicit_text_translation_parts(message)
    if not source_text:
        quoted = re.search(r'["\'](?P<text>.+?)["\']', message, flags=re.DOTALL)
        if quoted:
            source_text = _clean(quoted.group("text"))

    target_language = normalize_language_code(raw_target_language) or detect_target_language(
        message
    )
    if not target_language:
        return {"error": "target_language_missing"}

    if not source_text or _looks_like_contextual_text_reference(source_text):
        return {
            "error": "source_text_missing",
            "target_language": target_language,
            "target_label_pt": language_label_pt(target_language),
        }

    return {
        "source_text": source_text,
        "target_language": target_language,
        "target_label_pt": language_label_pt(target_language),
    }


def _protect_urls(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}

    def replacer(match: re.Match[str]) -> str:
        key = f"URLTOKEN{len(placeholders)}XYZ"
        placeholders[key] = match.group(0)
        return key

    protected = re.sub(r"https?://\S+", replacer, str(text or ""))
    return protected, placeholders


def _restore_urls(text: str, placeholders: dict[str, str]) -> str:
    restored = str(text or "")
    for key, value in placeholders.items():
        restored = restored.replace(key, value)
    return restored


def _translate_via_libretranslate(
    text: str,
    *,
    target_language: str,
    source_language: str,
) -> dict[str, Any]:
    base_url = _clean(os.getenv("NOVA_TRANSLATE_API_URL") or os.getenv("NOVA_LIBRETRANSLATE_URL"))
    if not base_url:
        return {"ok": False, "error": "translate_api_not_configured"}

    payload = {
        "q": text,
        "source": source_language or "auto",
        "target": target_language,
        "format": "text",
    }
    api_key = _clean(os.getenv("NOVA_TRANSLATE_API_KEY"))
    if api_key:
        payload["api_key"] = api_key

    response = requests.post(base_url, json=payload, timeout=TRANSLATE_TIMEOUT)
    response.raise_for_status()
    data = response.json() if response.text else {}
    translated = _clean(str(data.get("translatedText", "")))
    if not translated:
        raise ValueError("empty_translation")
    return {
        "ok": True,
        "translated_text": translated,
        "provider": "libretranslate",
        "detected_source_language": str(
            data.get("detectedLanguage", "") or source_language or "auto"
        ),
    }


def _translate_via_google_public(
    text: str,
    *,
    target_language: str,
    source_language: str,
) -> dict[str, Any]:
    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": source_language or "auto",
            "tl": target_language,
            "dt": "t",
            "q": text,
        },
        timeout=TRANSLATE_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json() if response.text else []
    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        raise ValueError("invalid_google_translate_payload")

    translated_parts: list[str] = []
    for block in data[0]:
        if isinstance(block, list) and block:
            piece = str(block[0] or "")
            if piece:
                translated_parts.append(piece)

    translated = _clean("".join(translated_parts))
    if not translated:
        raise ValueError("empty_translation")

    detected = (
        str(data[2]).strip()
        if len(data) > 2 and isinstance(data[2], str)
        else source_language or "auto"
    )
    return {
        "ok": True,
        "translated_text": translated,
        "provider": "google_public",
        "detected_source_language": detected,
    }


def _translate_via_mymemory(
    text: str,
    *,
    target_language: str,
    source_language: str,
) -> dict[str, Any]:
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={
            "q": text,
            "langpair": f"{source_language or 'auto'}|{target_language}",
        },
        timeout=TRANSLATE_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json() if response.text else {}
    translated = _clean(str((data.get("responseData") or {}).get("translatedText", "")))
    if not translated:
        raise ValueError("empty_translation")
    return {
        "ok": True,
        "translated_text": translated,
        "provider": "mymemory",
        "detected_source_language": source_language or "auto",
    }


def translate_text(
    text: str,
    *,
    target_language: str,
    source_language: str = "auto",
) -> dict[str, Any]:
    body = _clean(text)
    target = normalize_language_code(target_language)
    source = normalize_language_code(source_language) if source_language != "auto" else "auto"
    if not body:
        return {"ok": False, "error": "text_required"}
    if not target:
        return {"ok": False, "error": "target_language_invalid"}

    protected_body, placeholders = _protect_urls(body)
    attempts: list[str] = []

    for provider in (
        _translate_via_libretranslate,
        _translate_via_google_public,
        _translate_via_mymemory,
    ):
        try:
            result = provider(
                protected_body,
                target_language=target,
                source_language=source,
            )
            if not bool(result.get("ok")):
                raise ValueError(str(result.get("error", "translation_provider_failed")))
            translated = _restore_urls(str(result.get("translated_text", "")), placeholders)
            if not _clean(translated):
                raise ValueError("empty_translation")
            return {
                **result,
                "ok": True,
                "translated_text": translated,
                "target_language": target,
            }
        except Exception as exc:
            provider_name = getattr(provider, "__name__", provider.__class__.__name__)
            attempts.append(f"{provider_name}: {exc}")

    return {
        "ok": False,
        "error": "translation_unavailable",
        "attempts": attempts,
        "target_language": target,
    }

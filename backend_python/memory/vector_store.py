from __future__ import annotations

from difflib import SequenceMatcher
import json
import re
import unicodedata
from typing import Any

from memory.sqlite_store import MemoryStore


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DEFAULT_LIMIT_SCAN = 220
_MAX_TOKENS_PER_ITEM = 64
_MIN_TEXT_SIZE = 8
_SEMANTIC_CATEGORY = "semantica"
_SCOPE = "semantica"
_SOURCE = "vector_store"
_STOPWORDS = {
    "a",
    "o",
    "as",
    "os",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "em",
    "para",
    "por",
    "com",
    "sem",
    "um",
    "uma",
    "na",
    "no",
    "nas",
    "nos",
    "que",
    "como",
    "isso",
    "isto",
    "essa",
    "esse",
    "aqui",
    "agora",
    "hoje",
    "me",
    "eu",
    "voce",
    "voces",
    "você",
}
_SYNONYM_GROUPS = (
    {"framework", "stack", "tecnologia", "tecnologias", "tech"},
    {"favorito", "favorita", "preferido", "preferida", "gosto", "curto"},
    {"projeto", "produto", "iniciativa", "demanda"},
    {"lembra", "lembrar", "recorda", "recordar", "memoria", "memória", "sabe"},
    {"resposta", "resumo", "explicacao", "explicação"},
    {"triste", "mal", "abatido", "abatida"},
    {"feliz", "contente", "alegre"},
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _normalize_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def _normalize_token(token: str) -> str:
    base = _normalize_ascii(token)
    base = re.sub(r"[^a-z0-9]", "", base)
    if len(base) > 5 and base.endswith("mente"):
        base = base[:-5]
    elif len(base) > 5 and base.endswith("coes"):
        base = base[:-4] + "cao"
    elif len(base) > 5 and base.endswith("s"):
        base = base[:-1]
    return base


def _build_synonym_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for group in _SYNONYM_GROUPS:
        normalized_group = sorted(
            {_normalize_token(item) for item in group if _normalize_token(item)}
        )
        if not normalized_group:
            continue
        canonical = normalized_group[0]
        for item in normalized_group:
            out[item] = canonical
    return out


_SYNONYMS = _build_synonym_map()


def _canonical_token(token: str) -> str:
    normalized = _normalize_token(token)
    if not normalized:
        return ""
    return _SYNONYMS.get(normalized, normalized)


def _tokenize(text: str) -> list[str]:
    raw_tokens = _TOKEN_RE.findall(_normalize_ascii(text))
    tokens: list[str] = []
    for raw in raw_tokens:
        token = _canonical_token(raw)
        if not token or len(token) < 2 or token in _STOPWORDS:
            continue
        tokens.append(token)
    return tokens


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _json_payload(text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    body = _clean(text)
    tokens = _dedupe_keep_order(_tokenize(body))[:_MAX_TOKENS_PER_ITEM]
    return {
        "text": body,
        "normalized": _clean(_normalize_ascii(body)),
        "tokens": tokens,
        "metadata": metadata or {},
    }


def _score_match(query_payload: dict[str, Any], item_payload: dict[str, Any]) -> float:
    query_tokens = set(query_payload.get("tokens") or [])
    item_tokens = set(item_payload.get("tokens") or [])
    if not query_tokens or not item_tokens:
        return 0.0

    common = query_tokens & item_tokens
    if not common:
        text_ratio = SequenceMatcher(
            None,
            str(query_payload.get("normalized", "")),
            str(item_payload.get("normalized", "")),
        ).ratio()
        return round(text_ratio * 2.0, 4) if text_ratio >= 0.48 else 0.0

    score = float(len(common) * 4)
    normalized_query = str(query_payload.get("normalized", ""))
    normalized_item = str(item_payload.get("normalized", ""))
    if normalized_query and normalized_query in normalized_item:
        score += 5.0

    query_count = max(1, len(query_tokens))
    overlap_ratio = len(common) / query_count
    score += overlap_ratio * 3.0

    sequence_ratio = SequenceMatcher(None, normalized_query, normalized_item).ratio()
    if sequence_ratio >= 0.42:
        score += sequence_ratio * 2.5

    return round(score, 4)


class VectorStore:
    def __init__(self, memory_store: MemoryStore | None = None) -> None:
        self.memory_store = memory_store
        self.enabled = memory_store is not None

    def index_text(
        self,
        user_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip() or "default"
        body = _clean(text)
        payload_metadata = dict(metadata or {})
        if not self.enabled or self.memory_store is None:
            return {
                "ok": False,
                "enabled": self.enabled,
                "reason": "semantic_memory_not_configured",
                "user_id": uid,
                "text_size": len(body),
                "metadata": payload_metadata,
            }

        if len(body) < _MIN_TEXT_SIZE:
            return {
                "ok": False,
                "enabled": self.enabled,
                "reason": "semantic_memory_too_short",
                "user_id": uid,
                "text_size": len(body),
                "metadata": payload_metadata,
            }

        payload = _json_payload(body, payload_metadata)
        if len(payload["tokens"]) < 2:
            return {
                "ok": False,
                "enabled": self.enabled,
                "reason": "semantic_memory_low_signal",
                "user_id": uid,
                "text_size": len(body),
                "metadata": payload_metadata,
            }

        recent = self.memory_store.search_recent(uid, limit=12, scope=_SCOPE)
        normalized_body = payload["normalized"]
        for item in recent:
            try:
                existing = json.loads(str(item.get("content", "")).strip() or "{}")
            except Exception:
                continue
            if not isinstance(existing, dict):
                continue
            if str(existing.get("normalized", "")) == normalized_body:
                return {
                    "ok": True,
                    "enabled": self.enabled,
                    "deduped": True,
                    "user_id": uid,
                    "text_size": len(body),
                    "metadata": payload_metadata,
                }

        saved = self.memory_store.save(
            user_id=uid,
            category=_SEMANTIC_CATEGORY,
            content=json.dumps(payload, ensure_ascii=False),
            importance=1,
            scope=_SCOPE,
            source=_SOURCE,
        )
        return {
            "ok": True,
            "enabled": self.enabled,
            "user_id": uid,
            "text_size": len(body),
            "metadata": payload_metadata,
            "item": saved,
        }

    def search(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        uid = str(user_id or "").strip() or "default"
        body = _clean(query)
        if not self.enabled or self.memory_store is None or not body:
            return []

        query_payload = _json_payload(body, {})
        if len(query_payload["tokens"]) < 2:
            return []

        candidates = self.memory_store.search_recent(
            uid,
            limit=max(limit * 8, _DEFAULT_LIMIT_SCAN),
            scope=_SCOPE,
        )
        scored: list[tuple[float, dict[str, Any]]] = []
        seen_texts: set[str] = set()
        for item in candidates:
            raw = str(item.get("content", "")).strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            text = _clean(str(payload.get("text", "")))
            normalized = str(payload.get("normalized", "")).strip()
            if not text or not normalized or normalized in seen_texts:
                continue
            score = _score_match(query_payload, payload)
            if score <= 0:
                continue
            seen_texts.add(normalized)
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            scored.append(
                (
                    score,
                    {
                        "id": item.get("id"),
                        "user_id": uid,
                        "scope": _SCOPE,
                        "category": str(metadata.get("category", "contexto semantico")),
                        "content": text,
                        "importance": item.get("importance", 1),
                        "source": str(metadata.get("source", _SOURCE)),
                        "created_at": item.get("created_at", ""),
                        "updated_at": item.get("updated_at", ""),
                        "semantic_score": score,
                        "metadata": metadata,
                    },
                )
            )

        scored.sort(key=lambda pair: (pair[0], pair[1].get("updated_at", "")), reverse=True)
        return [item for _, item in scored[: max(1, int(limit or 5))]]

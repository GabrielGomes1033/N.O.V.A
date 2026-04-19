from __future__ import annotations

from dataclasses import asdict
import json
import re
from typing import Any

from core.assistente_plus import adicionar_lembrete
from core.google_calendar import create_google_calendar_event, parse_calendar_event_request
from core.intent_classifier import IntentDecision, classify_intent
from core.respostas import detectar_intencao as detect_response_intent, responder
from core.response_style import style_response
from core.translation_service import (
    language_label_pt,
    parse_search_translation_request,
    parse_text_translation_request,
    translate_text,
)
from core.tools_registry import ToolsRegistry
from integrations.brave_search import search_web as integration_search_web
from integrations.home_assistant import control_home as integration_control_home
from integrations.notion_api import create_project as integration_create_project
from memory.profile_store import ProfileStore
from memory.sqlite_store import MemoryStore
from memory.vector_store import VectorStore


STOPWORDS = {
    "de",
    "da",
    "do",
    "dos",
    "das",
    "a",
    "o",
    "os",
    "as",
    "e",
    "que",
    "como",
    "para",
    "com",
    "por",
    "sem",
    "sobre",
    "uma",
    "um",
    "me",
    "voce",
    "voces",
    "eu",
    "isso",
    "isto",
}

AFFIRMATIVE_REPLIES = {
    "sim",
    "s",
    "ok",
    "confirmo",
    "pode",
    "pode sim",
    "yes",
    "y",
}

NEGATIVE_REPLIES = {
    "nao",
    "não",
    "n",
    "cancelar",
    "cancela",
    "negativo",
    "no",
}

TOOL_APPROVAL_PROMPTS = {
    "schedule_calendar_event": "Posso agendar isso na sua Google Agenda, mas preciso da sua confirmacao.",
}

DEFAULT_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Pesquisa informacoes recentes e resume o que encontrou.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Salva uma memoria util sobre o usuario ou o contexto atual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "content": {"type": "string"},
                    "importance": {"type": "integer"},
                },
                "required": ["category", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Busca memorias recentes ou de longo prazo associadas ao usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Cria um lembrete simples com titulo e horario opcional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "when": {"type": "string"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_project",
            "description": "Cria um projeto no provider configurado com fallback seguro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_calendar_event",
            "description": "Agenda um evento ou tarefa na Google Agenda a partir de um pedido em linguagem natural.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_text": {"type": "string"},
                },
                "required": ["request_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "Resume um texto de forma objetiva e clara.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_home",
            "description": "Controla entidades do Home Assistant depois de confirmacao explicita.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string"},
                    "action": {"type": "string"},
                },
                "required": ["entity_id", "action"],
            },
        },
    },
]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _shorten(text: str, limit: int = 180) -> str:
    body = _normalize_text(text)
    if len(body) <= limit:
        return body
    truncated = body[: max(40, limit)].rsplit(" ", 1)[0].strip()
    return (truncated or body[:limit]).rstrip(" ,.;:-") + "..."


def _summarize_text(text: str) -> str:
    body = _normalize_text(text)
    if not body:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", body)
    top = " ".join(sentences[:2]).strip()
    return _shorten(top or body, 260)


def _approval_prompt(tool_name: str) -> str:
    tool = str(tool_name or "").strip()
    return TOOL_APPROVAL_PROMPTS.get(
        tool,
        f"Posso executar {tool}, mas preciso da sua confirmacao.",
    )


def _extract_named_fact(items: list[dict[str, Any]], label: str) -> str:
    prefix = f"{label.lower()}:"
    for item in items:
        content = _normalize_text(str(item.get("content", "")))
        if not content:
            continue
        lowered = content.lower()
        if lowered.startswith(prefix):
            return content[len(prefix) :].strip()
    return ""


def _is_affirmative_reply(text: str) -> bool:
    return _normalize_text(text).lower() in AFFIRMATIVE_REPLIES


def _is_negative_reply(text: str) -> bool:
    return _normalize_text(text).lower() in NEGATIVE_REPLIES


def _terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_]+", str(text or "").lower())
        if len(token) >= 3 and token not in STOPWORDS
    }


def _best_context_note(text: str, context: list[dict[str, Any]]) -> str:
    terms = _terms(text)
    if not terms:
        return ""
    best_content = ""
    best_score = 0
    for item in context:
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        score = sum(1 for term in terms if term in content.lower())
        if score > best_score:
            best_score = score
            best_content = content
    return _shorten(best_content, 160) if best_score > 0 else ""


def _merge_memory_items(*groups: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group or []:
            content = _normalize_text(str(item.get("content", "")))
            key = content.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(dict(item))
            if len(merged) >= limit:
                return merged
    return merged


def _should_use_semantic_context(text: str) -> bool:
    terms = _terms(text)
    if len(terms) >= 2:
        return True
    lowered = str(text or "").lower()
    return any(token in lowered for token in ("lembra", "contexto", "projeto", "continua", "continue"))


class RuleBasedLLM:
    def decide(self, text: str, context: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        decision: IntentDecision = classify_intent(text)
        return asdict(decision)

    def respond(
        self,
        text: str,
        context: list[dict[str, Any]],
        mode: str = "normal",
        response_context: dict[str, Any] | None = None,
    ) -> str:
        context_hint = _best_context_note(text, context)
        resposta_base = responder(text, contexto=response_context or {})
        if context_hint and any(token in text.lower() for token in ("contexto", "continua", "projeto", "lembra")):
            resposta_base = f"{resposta_base}\nContexto util: {context_hint}"
        return style_response(resposta_base, modo=mode)

    def respond_with_tool_result(
        self,
        text: str,
        tool_name: str,
        result: dict[str, Any],
        context: list[dict[str, Any]],
        mode: str = "normal",
    ) -> str:
        ok = bool(result.get("ok", False))
        if tool_name == "search_web":
            if not ok:
                return style_response(
                    "Nao consegui pesquisar agora. Posso tentar novamente com um recorte mais especifico.",
                    modo=mode,
                )
            resumo = str(result.get("summary", "")).strip()
            if not resumo:
                resumo = "Encontrei resultados, mas sem um resumo confiavel ainda."
            fontes = result.get("sources") or []
            bloco_fontes = ""
            if fontes:
                bloco_fontes = "\nFontes: " + ", ".join(str(item) for item in fontes[:3])
            return style_response(f"Pesquisei e encontrei isto: {resumo}{bloco_fontes}", modo=mode)

        if tool_name == "save_memory":
            if ok:
                return style_response(
                    f"Pronto. Vou lembrar disso como {result.get('category', 'contexto')}.",
                    modo=mode,
                )
            return style_response("Nao consegui salvar essa memoria agora.", modo=mode)

        if tool_name == "search_memory":
            itens = result.get("items") or []
            if not itens:
                return style_response("Nao encontrei memoria relevante sobre esse ponto ainda.", modo=mode)
            linhas = []
            for item in itens[:3]:
                linhas.append(f"- {item.get('category', 'contexto')}: {_shorten(str(item.get('content', '')), 120)}")
            return style_response("Encontrei isto na memoria:\n" + "\n".join(linhas), modo=mode)

        if tool_name == "create_reminder":
            if ok:
                when = str(result.get("when", "")).strip()
                sufixo = f" para {when}" if when else ""
                return style_response(f"Lembrete criado: {result.get('title', '')}{sufixo}.", modo=mode)
            return style_response("Nao consegui criar esse lembrete.", modo=mode)

        if tool_name == "create_project":
            if ok:
                provider = str(result.get("provider", "provider")).strip()
                return style_response(
                    f"Projeto criado em {provider}: {result.get('project_name', '')}.",
                    modo=mode,
                )
            return style_response("Nao consegui criar esse projeto com seguranca agora.", modo=mode)

        if tool_name == "schedule_calendar_event":
            if ok:
                title = str(result.get("title", "")).strip() or "Compromisso"
                start_at = str(result.get("start_at", "")).strip().replace("T", " às ")
                link = str(result.get("html_link", "")).strip()
                assumptions = (result.get("parsed") or {}).get("assumptions") or []
                lines = [f"Evento agendado na Google Agenda: {title} em {start_at}."]
                if assumptions:
                    lines.append("Observacoes: " + " ".join(str(item).strip() for item in assumptions if str(item).strip()))
                if link:
                    lines.append(f"Link: {link}")
                return style_response("\n".join(lines), modo=mode)
            message = str(result.get("message", "")).strip()
            if message:
                return style_response(message, modo=mode)
            return style_response("Nao consegui agendar esse compromisso na Google Agenda.", modo=mode)

        if tool_name == "summarize_text":
            if ok:
                return style_response(str(result.get("summary", "")).strip(), modo=mode)
            return style_response("Nao consegui resumir esse texto.", modo=mode)

        if tool_name == "control_home":
            if ok:
                return style_response(
                    f"Acao enviada com sucesso para {result.get('entity_id', '')}.",
                    modo=mode,
                )
            return style_response("Nao consegui executar essa automacao residencial.", modo=mode)

        return style_response("Ferramenta executada.", modo=mode)


def build_default_tools(memory_store: MemoryStore) -> ToolsRegistry:
    registry = ToolsRegistry()

    def search_web(query: str, user_id: str = "default") -> dict[str, Any]:
        result = integration_search_web(query)
        if result.get("ok"):
            summary = str(result.get("summary", "")).strip()
            if summary:
                memory_store.save(
                    user_id=user_id,
                    category="aprendizado",
                    content=f"Pesquisa web sobre {query}: {summary}",
                    importance=2,
                    scope="sessao",
                    source="search_web",
                )
        return result

    def save_memory(
        category: str,
        content: str,
        importance: int = 2,
        user_id: str = "default",
    ) -> dict[str, Any]:
        saved = memory_store.save(
            user_id=user_id,
            category=category,
            content=content,
            importance=importance,
            scope="longo_prazo",
            source="save_memory",
        )
        return {"ok": True, **saved}

    def search_memory(query: str, user_id: str = "default") -> dict[str, Any]:
        items = memory_store.search(user_id=user_id, query=query, limit=6)
        return {"ok": True, "query": query, "items": items, "total": len(items)}

    def create_reminder(title: str, when: str = "", user_id: str = "default") -> dict[str, Any]:
        out = adicionar_lembrete(title, quando=when)
        return {
            "ok": bool(out.get("ok")),
            "title": title,
            "when": when,
            "result": out,
        }

    def create_project(name: str, description: str = "", user_id: str = "default") -> dict[str, Any]:
        result = integration_create_project(name, description=description)
        if result.get("ok"):
            memory_store.save(
                user_id=user_id,
                category="projeto",
                content=f"Projeto criado: {name}",
                importance=3,
                scope="longo_prazo",
                source="create_project",
            )
        return result

    def schedule_calendar_event(request_text: str, user_id: str = "default") -> dict[str, Any]:
        parsed = parse_calendar_event_request(request_text)
        if not parsed.get("ok"):
            return parsed

        result = create_google_calendar_event(
            title=str(parsed.get("title", "")).strip(),
            start_at=str(parsed.get("start_at", "")).strip(),
            end_at=str(parsed.get("end_at", "")).strip(),
            description=str(parsed.get("description", "")).strip(),
            calendar_id=str(parsed.get("calendar_id", "")).strip(),
            timezone=str(parsed.get("timezone", "")).strip(),
        )
        payload = {**result, "parsed": parsed}
        if result.get("ok"):
            memory_store.save(
                user_id=user_id,
                category="agenda",
                content=(
                    f"Evento agendado na Google Agenda: {payload.get('title', '')} "
                    f"em {payload.get('start_at', '')}"
                ),
                importance=3,
                scope="sessao",
                source="schedule_calendar_event",
            )
        return payload

    def summarize_text(text: str, user_id: str = "default") -> dict[str, Any]:
        return {"ok": True, "summary": _summarize_text(text)}

    def control_home(entity_id: str, action: str, user_id: str = "default") -> dict[str, Any]:
        return integration_control_home(entity_id=entity_id, action=action)

    for schema in DEFAULT_TOOL_SCHEMAS:
        function_name = schema["function"]["name"]
        func = {
            "search_web": search_web,
            "save_memory": save_memory,
            "search_memory": search_memory,
            "create_reminder": create_reminder,
            "create_project": create_project,
            "schedule_calendar_event": schedule_calendar_event,
            "summarize_text": summarize_text,
            "control_home": control_home,
        }[function_name]
        registry.register(
            function_name,
            func,
            schema,
            approval_required=function_name in {"control_home", "schedule_calendar_event"},
        )

    return registry


class NovaOrchestrator:
    def __init__(
        self,
        memory: MemoryStore,
        tools: ToolsRegistry,
        llm: RuleBasedLLM,
        *,
        profile_store: ProfileStore | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.memory = memory
        self.tools = tools
        self.llm = llm
        self.profile_store = profile_store or ProfileStore(memory)
        self.vector_store = vector_store or VectorStore(memory)
        self._last_search_by_user: dict[str, dict[str, Any]] = {}
        self._last_intent_by_user: dict[str, str] = {}
        self._pending_translation_by_user: dict[str, dict[str, Any]] = {}

    def _persist_last_search(
        self,
        user_id: str,
        *,
        prompt_text: str,
        tool_result: dict[str, Any],
        reply: str,
    ) -> None:
        payload = {
            "prompt_text": _normalize_text(prompt_text),
            "reply": str(reply or "").strip(),
            "tool_result": dict(tool_result or {}),
        }
        self.memory.save(
            user_id=user_id,
            category="ultima_pesquisa_contexto",
            content=json.dumps(payload, ensure_ascii=False),
            importance=2,
            scope="sessao",
            source="search_web_state",
        )

    def _load_last_search_from_memory(self, user_id: str) -> dict[str, Any] | None:
        uid = str(user_id or "").strip() or "default"
        rows = self.memory.search_by_category(
            user_id=uid,
            category="ultima_pesquisa_contexto",
            limit=1,
        )
        if not rows:
            return None
        raw = str(rows[0].get("content", "")).strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def _capture_profile_facts(self, user_id: str, text: str) -> None:
        msg = _normalize_text(text)
        if not msg:
            return

        name_match = re.search(r"\bmeu nome (?:e|eh|é)\s+([A-Za-zÀ-ÿ' -]{2,40})", msg, flags=re.IGNORECASE)
        if name_match:
            nome = name_match.group(1).strip().title()
            self.profile_store.save_fact(user_id, "perfil", f"Nome preferido: {nome}", importance=4)

        city_match = re.search(r"\beu moro em\s+([A-Za-zÀ-ÿ' -]{2,50})", msg, flags=re.IGNORECASE)
        if city_match:
            cidade = city_match.group(1).strip().title()
            self.profile_store.save_fact(user_id, "perfil", f"Cidade: {cidade}", importance=3)

        if any(token in msg.lower() for token in ("prefiro", "favorito", "gosto de")):
            self.profile_store.save_fact(user_id, "preferencia", msg, importance=2)

    def _remember_turn(self, user_id: str, text: str, reply: str) -> None:
        user_text = _normalize_text(text)
        assistant_text = _normalize_text(reply)
        if user_text:
            self.memory.save(
                user_id=user_id,
                category="contexto",
                content=f"Usuario: {user_text}",
                importance=1,
                scope="sessao",
                source="chat_user",
            )
            self.vector_store.index_text(
                user_id=user_id,
                text=user_text,
                metadata={"source": "user", "category": "contexto"},
            )
        if assistant_text:
            self.memory.save(
                user_id=user_id,
                category="contexto",
                content=f"NOVA: {assistant_text}",
                importance=1,
                scope="sessao",
                source="chat_assistant",
            )
            self.vector_store.index_text(
                user_id=user_id,
                text=assistant_text,
                metadata={"source": "assistant", "category": "contexto"},
            )

    def _build_response_context(
        self,
        user_id: str,
        *,
        base_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip() or "default"
        profile_items = self.profile_store.summary(uid, limit=6)
        nome_usuario = _extract_named_fact(profile_items, "Nome preferido")
        tratamento = _extract_named_fact(profile_items, "Tratamento")
        return {
            "nome_usuario": nome_usuario,
            "tratamento": tratamento,
            "ultima_intencao": self._last_intent_by_user.get(uid, ""),
            "contexto_recente": list(base_context or []),
        }

    def _build_combined_context(
        self,
        user_id: str,
        text: str,
        *,
        recent_limit: int = 8,
        semantic_limit: int = 4,
    ) -> list[dict[str, Any]]:
        uid = str(user_id or "").strip() or "default"
        recent = self.memory.search_recent(uid, limit=recent_limit)
        if not _should_use_semantic_context(text):
            return recent
        semantic = self.vector_store.search(uid, text, limit=semantic_limit)
        return _merge_memory_items(semantic, recent, limit=recent_limit + semantic_limit)

    def _remember_last_intent(
        self,
        user_id: str,
        text: str,
        *,
        response_context: dict[str, Any] | None = None,
    ) -> None:
        uid = str(user_id or "").strip() or "default"
        intent = detect_response_intent(text, contexto=response_context or {})
        if intent and intent != "desconhecido":
            self._last_intent_by_user[uid] = intent

    def _remember_last_search(
        self,
        user_id: str,
        *,
        prompt_text: str,
        tool_result: dict[str, Any],
        reply: str,
    ) -> None:
        self._last_search_by_user[str(user_id or "").strip() or "default"] = {
            "prompt_text": _normalize_text(prompt_text),
            "reply": str(reply or "").strip(),
            "tool_result": dict(tool_result or {}),
        }
        self._persist_last_search(
            str(user_id or "").strip() or "default",
            prompt_text=prompt_text,
            tool_result=tool_result,
            reply=reply,
        )

    def _offer_search_translation(self, user_id: str, reply: str) -> str:
        uid = str(user_id or "").strip() or "default"
        target_language = "pt"
        target_label_pt = language_label_pt(target_language)
        self._pending_translation_by_user[uid] = {
            "kind": "search",
            "target_language": target_language,
            "target_label_pt": target_label_pt,
        }
        offer = (
            f"Se quiser, eu tambem posso traduzir essa pesquisa para {target_label_pt}. "
            "Responda sim ou nao."
        )
        return f"{str(reply or '').rstrip()}\n\n{offer}"

    def _translate_last_search(
        self,
        user_id: str,
        text: str,
        *,
        target_language: str,
        target_label_pt: str,
        mode: str = "normal",
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip() or "default"
        self._pending_translation_by_user.pop(uid, None)
        last_search = self._last_search_by_user.get(uid)
        if not isinstance(last_search, dict) or not last_search.get("reply"):
            last_search = self._load_last_search_from_memory(uid)
        if not isinstance(last_search, dict) or not last_search.get("reply"):
            reply = style_response(
                "Posso traduzir a ultima pesquisa, mas ainda nao tenho uma pesquisa recente nesta conversa.",
                modo=mode,
            )
            self._remember_turn(uid, text, reply)
            return {
                "reply": reply,
                "decision_type": "response",
                "approval_needed": False,
                "tool_name": None,
                "params": {},
                "tool_result": {},
                "context": self.memory.search_recent(uid, limit=8),
            }

        translatable_reply = re.sub(
            r"^\s*Pesquisei e encontrei isto:\s*",
            "",
            str(last_search.get("reply", "")),
            flags=re.IGNORECASE,
        ).strip()
        translation = translate_text(
            translatable_reply,
            target_language=target_language,
        )
        if not translation.get("ok"):
            reply = style_response(
                f"Nao consegui traduzir a ultima pesquisa para {target_label_pt} agora.",
                modo=mode,
            )
            self._remember_turn(uid, text, reply)
            return {
                "reply": reply,
                "decision_type": "response",
                "approval_needed": False,
                "tool_name": None,
                "params": {},
                "tool_result": translation,
                "context": self.memory.search_recent(uid, limit=8),
            }

        translated_text = str(translation.get("translated_text", "")).strip()
        reply = style_response(
            f"Traducao da ultima pesquisa para {target_label_pt}:\n\n{translated_text}",
            modo=mode,
        )
        self.memory.save(
            user_id=uid,
            category="pesquisa_traduzida",
            content=f"Traducao de pesquisa para {target_language}: {_shorten(translated_text, 240)}",
            importance=2,
            scope="sessao",
            source="translate_search",
        )
        self._remember_turn(uid, text, reply)
        return {
            "reply": reply,
            "decision_type": "response",
            "approval_needed": False,
            "tool_name": None,
            "params": {"target_language": target_language},
            "tool_result": translation,
            "context": self.memory.search_recent(uid, limit=8),
        }

    def _handle_search_translation(
        self,
        user_id: str,
        text: str,
        *,
        mode: str = "normal",
    ) -> dict[str, Any] | None:
        request = parse_search_translation_request(text)
        if request is None:
            return None

        target_language = str(request.get("target_language", "")).strip() or "pt"
        target_label_pt = str(request.get("target_label_pt", "")).strip() or target_language
        return self._translate_last_search(
            user_id,
            text,
            target_language=target_language,
            target_label_pt=target_label_pt,
            mode=mode,
        )

    def _handle_pending_translation_confirmation(
        self,
        user_id: str,
        text: str,
        *,
        mode: str = "normal",
    ) -> dict[str, Any] | None:
        uid = str(user_id or "").strip() or "default"
        pending = self._pending_translation_by_user.get(uid)
        if not isinstance(pending, dict) or not pending:
            return None

        if _is_negative_reply(text):
            self._pending_translation_by_user.pop(uid, None)
            reply = style_response(
                "Tudo bem. Mantive a pesquisa no idioma original.",
                modo=mode,
            )
            self._remember_turn(uid, text, reply)
            return {
                "reply": reply,
                "decision_type": "response",
                "approval_needed": False,
                "tool_name": None,
                "params": {},
                "tool_result": {"ok": True, "cancelled": True},
                "context": self.memory.search_recent(uid, limit=8),
            }

        if not _is_affirmative_reply(text):
            self._pending_translation_by_user.pop(uid, None)
            return None

        if str(pending.get("kind", "")).strip() == "search":
            return self._translate_last_search(
                uid,
                text,
                target_language=str(pending.get("target_language", "")).strip() or "pt",
                target_label_pt=str(pending.get("target_label_pt", "")).strip() or "portugues",
                mode=mode,
            )

        self._pending_translation_by_user.pop(uid, None)
        return None

    def _handle_text_translation(
        self,
        user_id: str,
        text: str,
        *,
        mode: str = "normal",
    ) -> dict[str, Any] | None:
        request = parse_text_translation_request(text)
        if request is None:
            return None

        uid = str(user_id or "").strip() or "default"
        error = str(request.get("error", "")).strip()
        if error == "target_language_missing":
            reply = style_response(
                'Posso traduzir texto, mas preciso do idioma de destino. Exemplo: traduza "Bom dia" para ingles.',
                modo=mode,
            )
            self._remember_turn(uid, text, reply)
            return {
                "reply": reply,
                "decision_type": "response",
                "approval_needed": False,
                "tool_name": None,
                "params": {},
                "tool_result": {"ok": False, "error": error},
                "context": self.memory.search_recent(uid, limit=8),
            }

        if error == "source_text_missing":
            target_label_pt = str(request.get("target_label_pt", "")).strip()
            reply = style_response(
                (
                    f'Me mande o texto junto do pedido para eu traduzir para {target_label_pt}. '
                    'Exemplo: traduza "Bom dia" para ingles.'
                ),
                modo=mode,
            )
            self._remember_turn(uid, text, reply)
            return {
                "reply": reply,
                "decision_type": "response",
                "approval_needed": False,
                "tool_name": None,
                "params": {},
                "tool_result": {"ok": False, "error": error},
                "context": self.memory.search_recent(uid, limit=8),
            }

        source_text = str(request.get("source_text", "")).strip()
        target_language = str(request.get("target_language", "")).strip() or "pt"
        target_label_pt = str(request.get("target_label_pt", "")).strip() or target_language
        translation = translate_text(
            source_text,
            target_language=target_language,
        )
        if not translation.get("ok"):
            reply = style_response(
                f"Nao consegui traduzir esse texto para {target_label_pt} agora.",
                modo=mode,
            )
            self._remember_turn(uid, text, reply)
            return {
                "reply": reply,
                "decision_type": "response",
                "approval_needed": False,
                "tool_name": None,
                "params": {
                    "source_text": source_text,
                    "target_language": target_language,
                },
                "tool_result": translation,
                "context": self.memory.search_recent(uid, limit=8),
            }

        translated_text = str(translation.get("translated_text", "")).strip()
        reply = style_response(
            f"Traducao do texto para {target_label_pt}:\n\n{translated_text}",
            modo=mode,
        )
        self.memory.save(
            user_id=uid,
            category="texto_traduzido",
            content=(
                f"Traducao de texto para {target_language}: "
                f"{_shorten(source_text, 140)} -> {_shorten(translated_text, 140)}"
            ),
            importance=2,
            scope="sessao",
            source="translate_text",
        )
        self._remember_turn(uid, text, reply)
        return {
            "reply": reply,
            "decision_type": "response",
            "approval_needed": False,
            "tool_name": None,
            "params": {
                "source_text": source_text,
                "target_language": target_language,
            },
            "tool_result": translation,
            "context": self.memory.search_recent(uid, limit=8),
        }

    def execute_tool(
        self,
        user_id: str,
        tool_name: str,
        params: dict[str, Any] | None,
        *,
        prompt_text: str = "",
        mode: str = "normal",
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip() or "default"
        tool = str(tool_name or "").strip()
        if not tool:
            return {
                "reply": style_response("Ferramenta nao informada.", modo=mode),
                "decision_type": "tool_call",
                "approval_needed": False,
                "tool_name": "",
                "params": {},
                "tool_result": {"ok": False, "error": "tool_name_required"},
                "context": self.memory.search_recent(uid, limit=8),
            }

        context = self._build_combined_context(uid, prompt_text or tool)
        result = self.tools.execute(tool, params or {}, user_id=uid)
        if tool == "search_memory":
            query = str((params or {}).get("query", "")).strip()
            semantic_items = self.vector_store.search(uid, query, limit=4)
            merged_items = _merge_memory_items(
                result.get("items") or [],
                semantic_items,
                limit=6,
            )
            result = {
                **result,
                "items": merged_items,
                "semantic_items": semantic_items,
                "total": len(merged_items),
            }
        response_context = self._build_response_context(uid, base_context=context)
        reply = self.llm.respond_with_tool_result(
            prompt_text or tool,
            tool_name=tool,
            result=result,
            context=context,
            mode=mode,
        )
        if tool == "search_web" and bool(result.get("ok")):
            self._remember_last_search(
                uid,
                prompt_text=prompt_text or tool,
                tool_result=result,
                reply=reply,
            )
            self.vector_store.index_text(
                user_id=uid,
                text=f"Pesquisa web sobre {result.get('query', '')}: {result.get('summary', '')}",
                metadata={"source": "search_web", "category": "pesquisa"},
            )
            reply = self._offer_search_translation(uid, reply)
        if tool == "schedule_calendar_event" and bool(result.get("ok")):
            self.vector_store.index_text(
                user_id=uid,
                text=f"Evento agendado: {result.get('title', '')} em {result.get('start_at', '')}",
                metadata={"source": "google_calendar", "category": "agenda"},
            )
        self._remember_turn(uid, prompt_text or tool, reply)
        if prompt_text:
            self._remember_last_intent(uid, prompt_text, response_context=response_context)
        return {
            "reply": reply,
            "decision_type": "tool_call",
            "approval_needed": False,
            "tool_name": tool,
            "params": params or {},
            "tool_result": result,
            "context": self._build_combined_context(uid, prompt_text or tool),
        }

    def handle(
        self,
        user_id: str,
        text: str,
        *,
        mode: str = "normal",
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip() or "default"
        msg = _normalize_text(text)
        if not msg:
            return {
                "reply": style_response("Preciso de uma mensagem para continuar.", modo=mode),
                "decision_type": "response",
                "approval_needed": False,
                "tool_name": None,
                "params": {},
                "tool_result": {},
                "context": self.memory.search_recent(uid, limit=8),
            }

        self._capture_profile_facts(uid, msg)
        translated_offer = self._handle_pending_translation_confirmation(uid, msg, mode=mode)
        if translated_offer is not None:
            return translated_offer
        translated_search = self._handle_search_translation(uid, msg, mode=mode)
        if translated_search is not None:
            return translated_search
        translated_text = self._handle_text_translation(uid, msg, mode=mode)
        if translated_text is not None:
            return translated_text
        context = self._build_combined_context(uid, msg)
        response_context = self._build_response_context(uid, base_context=context)

        decision = self.llm.decide(
            text=msg,
            context=context,
            tools=self.tools.schemas(),
        )

        if decision.get("type") == "tool_call":
            tool_name = str(decision.get("tool_name", "")).strip()
            params = decision.get("params") or {}
            if self.tools.requires_approval(tool_name) and not auto_approve:
                return {
                    "reply": style_response(
                        _approval_prompt(tool_name),
                        modo=mode,
                    ),
                    "decision_type": "tool_call",
                    "approval_needed": True,
                    "tool_name": tool_name,
                    "params": params,
                    "tool_result": {},
                    "context": context,
                }
            return self.execute_tool(
                uid,
                tool_name,
                params,
                prompt_text=msg,
                mode=mode,
            )

        final_reply = self.llm.respond(
            msg,
            context=context,
            mode=mode,
            response_context=response_context,
        )
        self._remember_turn(uid, msg, final_reply)
        self._remember_last_intent(uid, msg, response_context=response_context)
        return {
            "reply": final_reply,
            "decision_type": "response",
            "approval_needed": False,
            "tool_name": None,
            "params": {},
            "tool_result": {},
            "context": self._build_combined_context(uid, msg),
        }


_DEFAULT_ORCHESTRATOR: NovaOrchestrator | None = None


def get_default_orchestrator() -> NovaOrchestrator:
    global _DEFAULT_ORCHESTRATOR
    if _DEFAULT_ORCHESTRATOR is None:
        memory = MemoryStore()
        _DEFAULT_ORCHESTRATOR = NovaOrchestrator(
            memory=memory,
            tools=build_default_tools(memory),
            llm=RuleBasedLLM(),
        )
    return _DEFAULT_ORCHESTRATOR

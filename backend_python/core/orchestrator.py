from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from core.assistente_plus import adicionar_lembrete
from core.intent_classifier import IntentDecision, classify_intent
from core.respostas import responder
from core.response_style import style_response
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


class RuleBasedLLM:
    def decide(self, text: str, context: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        decision: IntentDecision = classify_intent(text)
        return asdict(decision)

    def respond(self, text: str, context: list[dict[str, Any]], mode: str = "normal") -> str:
        context_hint = _best_context_note(text, context)
        resposta_base = responder(text, contexto={})
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
            "summarize_text": summarize_text,
            "control_home": control_home,
        }[function_name]
        registry.register(
            function_name,
            func,
            schema,
            approval_required=function_name in {"control_home"},
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
        self.vector_store = vector_store or VectorStore()

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
        if assistant_text:
            self.memory.save(
                user_id=user_id,
                category="contexto",
                content=f"NOVA: {assistant_text}",
                importance=1,
                scope="sessao",
                source="chat_assistant",
            )
            self.vector_store.index_text(user_id=user_id, text=assistant_text, metadata={"source": "assistant"})

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

        context = self.memory.search_recent(uid, limit=8)
        result = self.tools.execute(tool, params or {}, user_id=uid)
        reply = self.llm.respond_with_tool_result(
            prompt_text or tool,
            tool_name=tool,
            result=result,
            context=context,
            mode=mode,
        )
        self._remember_turn(uid, prompt_text or tool, reply)
        return {
            "reply": reply,
            "decision_type": "tool_call",
            "approval_needed": False,
            "tool_name": tool,
            "params": params or {},
            "tool_result": result,
            "context": self.memory.search_recent(uid, limit=8),
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
        context = self.memory.search_recent(uid, limit=8)

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
                        f"Posso executar {tool_name}, mas preciso da sua confirmacao.",
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

        final_reply = self.llm.respond(msg, context=context, mode=mode)
        self._remember_turn(uid, msg, final_reply)
        return {
            "reply": final_reply,
            "decision_type": "response",
            "approval_needed": False,
            "tool_name": None,
            "params": {},
            "tool_result": {},
            "context": self.memory.search_recent(uid, limit=8),
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

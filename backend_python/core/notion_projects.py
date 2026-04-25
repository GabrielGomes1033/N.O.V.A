from __future__ import annotations

from dataclasses import dataclass
import os
import re
import unicodedata
from typing import Any

import requests


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = os.getenv("NOVA_NOTION_VERSION", "2026-03-11").strip() or "2026-03-11"

_VERBOS_CRIAR = (
    "crie",
    "criar",
    "cria",
    "abra",
    "abrir",
    "abre",
    "adicione",
    "adicionar",
    "adiciona",
    "cadastre",
    "cadastrar",
    "registra",
    "registre",
    "registrar",
    "inicie",
    "iniciar",
    "inicia",
    "gere",
    "gerar",
    "monte",
    "montar",
    "prepare",
    "preparar",
)

_PREFIXOS_ASSISTENTE = (
    "nova",
    "ei nova",
    "hey nova",
    "ok nova",
    "okay nova",
    "ola nova",
    "olá nova",
)

_PREFIXOS_CORTESIA = (
    "por favor",
    "por gentileza",
    "pode",
    "você pode",
    "voce pode",
    "consegue",
    "quero que você",
    "quero que voce",
    "preciso que você",
    "preciso que voce",
)


@dataclass(frozen=True)
class PedidoCriacaoProjeto:
    matched: bool = False
    provider: str = ""
    explicit_provider: bool = False
    project_name: str = ""
    description: str = ""
    area: str = ""
    priority: str = ""
    responsible: str = ""
    link: str = ""


def _normalizar_texto(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.lower()
    t = re.sub(r"[^\w\s/:-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _remover_prefixos_conversa(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        return ""

    for prefixo in _PREFIXOS_ASSISTENTE:
        padrao = r"^" + re.escape(prefixo) + r"[\s,:-]*"
        t = re.sub(padrao, "", t, flags=re.IGNORECASE).strip()

    for prefixo in _PREFIXOS_CORTESIA:
        padrao = r"^" + re.escape(prefixo) + r"\s+"
        t = re.sub(padrao, "", t, flags=re.IGNORECASE).strip()

    t = re.sub(r"^(pra mim|para mim)\s+", "", t, flags=re.IGNORECASE).strip()
    return t


def _detectar_provider(normalizado: str) -> tuple[str, bool]:
    if " notion" in f" {normalizado} ":
        return "notion", True
    if "google drive" in normalizado or re.search(r"\bdrive\b", normalizado):
        return "drive", True
    return provider_padrao_projeto(), False


def _parece_pedido_criar_projeto(normalizado: str) -> bool:
    if normalizado.startswith(("/notion projeto ", "/projeto ")):
        return True
    if normalizado in {"/projeto", "/notion projeto"}:
        return True
    if not re.search(r"\bprojeto\b", normalizado):
        return False
    if normalizado.startswith(("novo projeto", "projeto novo")):
        return True
    return any(re.search(rf"\b{re.escape(verbo)}\b", normalizado) for verbo in _VERBOS_CRIAR)


def _nome_entre_aspas(texto: str) -> str:
    achados = re.findall(r"[\"“”'`]\s*([^\"“”'`]{2,120}?)\s*[\"“”'`]", texto or "")
    if not achados:
        return ""
    return achados[0].strip()


def _extrair_nome_explicito(texto: str) -> str:
    if not texto:
        return ""

    padroes = [
        r"(?:chamado|chamada|com o nome|nome(?: do projeto)?(?: e| é)?|intitulado|batizado(?: como)?)\s*[\"“”'`]\s*([^\"“”'`]{2,120}?)\s*[\"“”'`]",
        r"(?:crie|criar|cria|abra|abrir|abre|adicione|adicionar|adiciona|cadastre|cadastrar|registre|registrar|registra|inicie|iniciar|inicia|gere|gerar|monte|montar|prepare|preparar)\s+(?:um\s+)?(?:novo\s+)?projeto(?:\s+(?:no|na)\s+notion|\s+(?:no|na)\s+google\s+drive|\s+(?:no|na)\s+drive)?\s*[\"“”'`]\s*([^\"“”'`]{2,120}?)\s*[\"“”'`]",
        r"(?:novo projeto|projeto novo)(?:\s+(?:no|na)\s+notion|\s+(?:no|na)\s+google\s+drive|\s+(?:no|na)\s+drive)?\s*[\"“”'`]\s*([^\"“”'`]{2,120}?)\s*[\"“”'`]",
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, flags=re.IGNORECASE)
        if match:
            return _limpar_valor_campo(match.group(1))
    return ""


def _limpar_valor_campo(valor: str) -> str:
    t = (valor or "").strip()
    if not t:
        return ""
    t = re.sub(r"\s+", " ", t).strip()
    return t.strip(" \t\n\r.,:;!?-\"'`")


def _marcadores_campos_regex() -> str:
    prefixo = r"\s+(?:e\s+)?"
    return (
        rf"(?:{prefixo}(?:com\s+)?descri[cç][aã]o(?:\s+inicial|\s+do\s+projeto)?\b"
        rf"|{prefixo}(?:na|no|em)\s+[áa]rea\b"
        rf"|{prefixo}[áa]rea\b"
        rf"|{prefixo}(?:com\s+)?prioridade\b"
        rf"|{prefixo}(?:com\s+)?respons[aá]vel\b"
        rf"|{prefixo}(?:com\s+)?(?:link|url)\b"
        rf"|{prefixo}(?:chamado|chamada|com\s+o\s+nome|nome(?:\s+do\s+projeto)?(?:\s+e|\s+é)?|intitulado|batizado(?:\s+como)?)\b"
        rf"|{prefixo}https?://\S+"
        r"|$)"
    )


def _extrair_segmento(texto: str, prefixos: tuple[str, ...]) -> str:
    if not texto:
        return ""
    lookahead = _marcadores_campos_regex()
    for prefixo in prefixos:
        padrao = prefixo + r"\s*[:=-]?\s*(.+?)(?=" + lookahead + r")"
        match = re.search(padrao, texto, flags=re.IGNORECASE)
        if match:
            return _limpar_valor_campo(match.group(1))
    return ""


def _extrair_descricao(texto: str) -> str:
    return _extrair_segmento(
        texto,
        (
            r"(?:com\s+)?descri[cç][aã]o(?:\s+inicial|\s+do\s+projeto)?",
            r"(?:com\s+)?detalhes(?:\s+do\s+projeto)?",
        ),
    )


def _extrair_area(texto: str) -> str:
    return _extrair_segmento(
        texto,
        (
            r"(?:na|no|em)\s+[áa]rea",
            r"[áa]rea",
        ),
    )


def _extrair_prioridade(texto: str) -> str:
    for padrao in (
        r"(?:com\s+)?prioridade\s+(?:e|é)?\s*(.+?)(?=" + _marcadores_campos_regex() + r")",
        r"\b(alta|m[ée]dia|media|baixa|urgente)\s+prioridade\b",
    ):
        match = re.search(padrao, texto, flags=re.IGNORECASE)
        if match:
            return _limpar_valor_campo(match.group(1))
    return ""


def _extrair_responsavel(texto: str) -> str:
    return _extrair_segmento(
        texto,
        (r"(?:com\s+)?respons[aá]vel\s+(?:e|é)?",),
    )


def _extrair_link(texto: str) -> str:
    match = re.search(r"https?://\S+", texto or "", flags=re.IGNORECASE)
    if match:
        return _limpar_valor_campo(match.group(0))
    return _extrair_segmento(
        texto,
        (
            r"(?:com\s+)?link",
            r"(?:com\s+)?url",
        ),
    )


def _limpar_nome_extraido(nome: str) -> str:
    t = (nome or "").strip()
    if not t:
        return ""

    t = t.strip(" \t\n\r.,:;!?-")
    t = re.sub(
        r"^(chamado|chamada|com o nome|nome(?: do projeto)?(?: e| é)?|intitulado|batizado(?: como)?)\s+",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"^(e\s+)?(o\s+)?nome(?: do projeto)?\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^(pra|para)\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+(por favor|pra mim|para mim)$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+(no|na)\s+notion$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+(no|na)\s+google\s+drive$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+(no|na)\s+drive$", "", t, flags=re.IGNORECASE)
    t = t.strip(" \t\n\r.,:;!?-\"'`")
    return t


def _remover_metadados_do_nome(nome: str) -> str:
    t = (nome or "").strip()
    if not t:
        return ""

    t = re.sub(r"https?://\S+", "", t, flags=re.IGNORECASE).strip()
    padroes = [
        r"\s+(?:com\s+)?descri[cç][aã]o(?:\s+inicial|\s+do\s+projeto)?\b.*$",
        r"\s+(?:com\s+)?detalhes(?:\s+do\s+projeto)?\b.*$",
        r"\s+(?:na|no|em)\s+[áa]rea\b.*$",
        r"\s+[áa]rea\b.*$",
        r"\s+(?:com\s+)?prioridade\b.*$",
        r"\s+\b(?:alta|m[ée]dia|media|baixa|urgente)\s+prioridade\b.*$",
        r"\s+(?:com\s+)?respons[aá]vel\b.*$",
        r"\s+(?:com\s+)?(?:link|url)\b.*$",
    ]
    for padrao in padroes:
        t = re.sub(padrao, "", t, flags=re.IGNORECASE).strip()
    return _limpar_nome_extraido(t)


def provider_padrao_projeto() -> str:
    provider = os.getenv("NOVA_PROJECT_PROVIDER", "").strip().lower()
    if provider in {"notion", "drive"}:
        return provider
    if notion_disponivel():
        return "notion"
    return "drive"


def notion_disponivel() -> bool:
    return bool(
        _notion_token() and (_notion_data_source_id() or _notion_page_id() or _notion_database_id())
    )


def interpretar_pedido_criacao_projeto(texto: str) -> PedidoCriacaoProjeto:
    original = (texto or "").strip()
    if not original:
        return PedidoCriacaoProjeto()

    limpo = _remover_prefixos_conversa(original)
    normalizado = _normalizar_texto(limpo)
    provider, explicit_provider = _detectar_provider(f" {normalizado} ")

    if not _parece_pedido_criar_projeto(normalizado):
        return PedidoCriacaoProjeto()

    description = _extrair_descricao(limpo)
    area = _extrair_area(limpo)
    priority = _extrair_prioridade(limpo)
    responsible = _extrair_responsavel(limpo)
    link = _extrair_link(limpo)

    if normalizado.startswith("/notion projeto"):
        nome = limpo.split(" ", 2)[2].strip() if len(limpo.split()) >= 3 else ""
        return PedidoCriacaoProjeto(
            True,
            "notion",
            True,
            _remover_metadados_do_nome(nome),
            description,
            area,
            priority,
            responsible,
            link,
        )

    if normalizado.startswith("/projeto"):
        nome = limpo.split(" ", 1)[1].strip() if len(limpo.split()) >= 2 else ""
        return PedidoCriacaoProjeto(
            True,
            provider,
            explicit_provider,
            _remover_metadados_do_nome(nome),
            description,
            area,
            priority,
            responsible,
            link,
        )

    nome = _extrair_nome_explicito(limpo)

    if not nome:
        nome = _nome_entre_aspas(limpo)

    if not nome:
        padroes = [
            r"(?:projeto|novo projeto|projeto novo)\s+(?:chamado|chamada|com o nome|nome(?: do projeto)?(?: e| é)?|intitulado|batizado(?: como)?)\s+(.+)$",
            r"(?:crie|criar|cria|abra|abrir|abre|adicione|adicionar|adiciona|cadastre|cadastrar|registre|registrar|registra|inicie|iniciar|inicia|gere|gerar|monte|montar|prepare|preparar)\s+(?:um\s+)?(?:novo\s+)?projeto(?:\s+(?:no|na)\s+notion|\s+(?:no|na)\s+google\s+drive|\s+(?:no|na)\s+drive)?\s+(.+)$",
            r"(?:novo projeto|projeto novo)(?:\s+(?:no|na)\s+notion|\s+(?:no|na)\s+google\s+drive|\s+(?:no|na)\s+drive)?\s+(.+)$",
            r"(?:crie|criar|cria|abra|abrir|abre|adicione|adicionar|adiciona|cadastre|cadastrar|registre|registrar|registra|inicie|iniciar|inicia|gere|gerar|monte|montar|prepare|preparar).+?\bprojeto\b.+?\b(?:para|pra)\b\s+(.+)$",
        ]
        for padrao in padroes:
            match = re.search(padrao, limpo, flags=re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                break

    nome = _remover_metadados_do_nome(nome)
    return PedidoCriacaoProjeto(
        True,
        provider,
        explicit_provider,
        nome,
        description,
        area,
        priority,
        responsible,
        link,
    )


def _notion_token() -> str:
    return os.getenv("NOVA_NOTION_TOKEN", "").strip()


def _notion_data_source_id() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_DATA_SOURCE_ID", "").strip()


def _notion_database_id() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_DATABASE_ID", "").strip()


def _notion_page_id() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_PAGE_ID", "").strip()


def _notion_title_property() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_TITLE_PROPERTY", "").strip()


def _notion_status_property() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_STATUS_PROPERTY", "").strip()


def _notion_status_value() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_STATUS_VALUE", "").strip()


def _notion_description_property() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_DESCRIPTION_PROPERTY", "").strip()


def _notion_area_property() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_AREA_PROPERTY", "").strip()


def _notion_priority_property() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_PRIORITY_PROPERTY", "").strip()


def _notion_responsible_property() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_RESPONSIBLE_PROPERTY", "").strip()


def _notion_link_property() -> str:
    return os.getenv("NOVA_NOTION_PROJECTS_LINK_PROPERTY", "").strip()


def _notion_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_notion_token()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _friendly_notion_error(status_code: int, message: str) -> str:
    if status_code == 401:
        return "Token do Notion inválido ou expirado."
    if status_code == 403:
        return "A integração do Notion não tem permissão suficiente. Ative Insert Content e compartilhe o destino com a integração."
    if status_code == 404:
        return "Não encontrei o destino no Notion. Verifique o ID informado e compartilhe a página/data source com a integração."
    if status_code == 429:
        return "O Notion aplicou limite de taxa. Tente novamente em alguns segundos."
    detalhe = (message or "").strip()
    if detalhe:
        return f"Falha na API do Notion ({status_code}): {detalhe}"
    return f"Falha na API do Notion ({status_code})."


def _notion_request(
    method: str, path: str, payload: dict[str, Any] | None = None
) -> tuple[bool, dict[str, Any] | str]:
    try:
        resp = requests.request(
            method,
            f"{NOTION_API_BASE}{path}",
            headers=_notion_headers(),
            json=payload,
            timeout=(5, 25),
        )
    except requests.RequestException as exc:
        return False, f"Não consegui conectar na API do Notion: {exc}"

    try:
        body = resp.json()
    except ValueError:
        body = {}

    if 200 <= resp.status_code < 300:
        return True, body if isinstance(body, dict) else {}

    mensagem = ""
    if isinstance(body, dict):
        mensagem = str(body.get("message") or body.get("code") or "").strip()
    if not mensagem:
        mensagem = (resp.text or "").strip()[:280]
    return False, _friendly_notion_error(resp.status_code, mensagem)


def _detectar_title_property(properties: dict[str, Any]) -> str:
    configured = _notion_title_property()
    if configured:
        return configured
    for nome, meta in (properties or {}).items():
        if isinstance(meta, dict) and meta.get("type") == "title":
            return str(nome)
    return ""


def _resolver_property_name(
    properties: dict[str, Any],
    *,
    configured: str = "",
    aliases: tuple[str, ...] = (),
    accepted_types: tuple[str, ...] = (),
) -> str:
    if configured and configured in properties:
        meta = properties.get(configured)
        if not accepted_types or (isinstance(meta, dict) and meta.get("type") in accepted_types):
            return configured

    aliases_norm = {_normalizar_texto(alias) for alias in aliases if alias}
    for nome, meta in (properties or {}).items():
        if not isinstance(meta, dict):
            continue
        if accepted_types and meta.get("type") not in accepted_types:
            continue
        if _normalizar_texto(str(nome)) in aliases_norm:
            return str(nome)
    return ""


def _coletar_opcoes_property(meta: dict[str, Any]) -> list[str]:
    if not isinstance(meta, dict):
        return []
    property_type = meta.get("type")
    if property_type not in {"select", "status"}:
        return []
    raw = meta.get(property_type) or {}
    options = raw.get("options") or []
    out: list[str] = []
    for item in options:
        if isinstance(item, dict) and item.get("name"):
            out.append(str(item.get("name")))
    return out


def _resolver_nome_opcao(meta: dict[str, Any], valor: str) -> str:
    valor_limpo = _limpar_valor_campo(valor)
    if not valor_limpo:
        return ""
    opcoes = _coletar_opcoes_property(meta)
    if not opcoes:
        return valor_limpo

    valor_norm = _normalizar_texto(valor_limpo)
    for opcao in opcoes:
        if _normalizar_texto(opcao) == valor_norm:
            return opcao
    for opcao in opcoes:
        opcao_norm = _normalizar_texto(opcao)
        if valor_norm in opcao_norm or opcao_norm in valor_norm:
            return opcao
    return valor_limpo


def _listar_usuarios_notion() -> list[dict[str, Any]]:
    usuarios: list[dict[str, Any]] = []
    start_cursor = ""
    for _ in range(5):
        path = "/users?page_size=100"
        if start_cursor:
            path += f"&start_cursor={start_cursor}"
        ok, payload = _notion_request("GET", path)
        if not ok or not isinstance(payload, dict):
            break
        results = payload.get("results", [])
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    usuarios.append(item)
        if not payload.get("has_more"):
            break
        start_cursor = str(payload.get("next_cursor") or "").strip()
        if not start_cursor:
            break
    return usuarios


def _resolver_usuario_notion(valor: str) -> tuple[str, str]:
    alvo = _limpar_valor_campo(valor)
    if not alvo:
        return "", ""

    alvo_norm = _normalizar_texto(alvo)
    for usuario in _listar_usuarios_notion():
        if usuario.get("type") != "person":
            continue
        nome = str(usuario.get("name") or "").strip()
        email = str((usuario.get("person") or {}).get("email") or "").strip()
        candidatos = [nome, email]
        for candidato in candidatos:
            if candidato and _normalizar_texto(candidato) == alvo_norm:
                return str(usuario.get("id") or ""), nome or email or alvo
        for candidato in candidatos:
            candidato_norm = _normalizar_texto(candidato)
            if candidato_norm and (alvo_norm in candidato_norm or candidato_norm in alvo_norm):
                return str(usuario.get("id") or ""), nome or email or alvo
    return "", ""


def _montar_propriedades_data_source(
    *,
    project_name: str,
    description: str = "",
    details: dict[str, str] | None = None,
    properties: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | str, list[str], list[str]]:
    props = properties or {}
    info = details or {}
    warnings: list[str] = []
    filled_fields: list[str] = []
    title_property = _detectar_title_property(props)
    if not title_property:
        return (
            False,
            "Não consegui identificar a coluna de título do data source no Notion. "
            "Defina NOVA_NOTION_PROJECTS_TITLE_PROPERTY ou conceda acesso de leitura ao data source.",
            [],
            [],
        )

    notion_properties: dict[str, Any] = {
        title_property: {
            "title": [
                {
                    "text": {
                        "content": project_name[:200],
                    }
                }
            ]
        }
    }
    filled_fields.append(title_property)

    status_property = _notion_status_property()
    status_value = _notion_status_value()
    if status_property and status_value:
        meta = props.get(status_property)
        property_type = meta.get("type") if isinstance(meta, dict) else ""
        if property_type == "status":
            notion_properties[status_property] = {"status": {"name": status_value}}
            filled_fields.append(status_property)
        elif property_type == "select":
            notion_properties[status_property] = {"select": {"name": status_value}}
            filled_fields.append(status_property)

    description_property = _resolver_property_name(
        props,
        configured=_notion_description_property(),
        aliases=("Descrição", "Descricao", "Detalhes", "Resumo"),
        accepted_types=("rich_text",),
    )
    description_text = _limpar_valor_campo(str(info.get("description") or description or ""))
    if description_property and description_text:
        notion_properties[description_property] = {
            "rich_text": [
                {
                    "text": {
                        "content": description_text[:1800],
                    }
                }
            ]
        }
        filled_fields.append(description_property)

    area_property = _resolver_property_name(
        props,
        configured=_notion_area_property(),
        aliases=("Área", "Area"),
        accepted_types=("select", "multi_select"),
    )
    area_value = _limpar_valor_campo(str(info.get("area") or ""))
    if area_property and area_value:
        area_meta = props.get(area_property) if isinstance(props.get(area_property), dict) else {}
        area_name = _resolver_nome_opcao(area_meta, area_value)
        property_type = area_meta.get("type")
        if property_type == "select":
            notion_properties[area_property] = {"select": {"name": area_name}}
            filled_fields.append(area_property)
        elif property_type == "multi_select":
            notion_properties[area_property] = {"multi_select": [{"name": area_name}]}
            filled_fields.append(area_property)

    priority_property = _resolver_property_name(
        props,
        configured=_notion_priority_property(),
        aliases=("Prioridade", "Priority"),
        accepted_types=("select",),
    )
    priority_value = _limpar_valor_campo(str(info.get("priority") or ""))
    if priority_property and priority_value:
        priority_meta = (
            props.get(priority_property) if isinstance(props.get(priority_property), dict) else {}
        )
        priority_name = _resolver_nome_opcao(priority_meta, priority_value)
        notion_properties[priority_property] = {"select": {"name": priority_name}}
        filled_fields.append(priority_property)

    link_property = _resolver_property_name(
        props,
        configured=_notion_link_property(),
        aliases=("Link", "URL", "Url"),
        accepted_types=("url",),
    )
    link_value = _limpar_valor_campo(str(info.get("link") or ""))
    if link_property and link_value:
        notion_properties[link_property] = {"url": link_value}
        filled_fields.append(link_property)

    responsible_property = _resolver_property_name(
        props,
        configured=_notion_responsible_property(),
        aliases=("Responsável", "Responsavel", "Owner"),
        accepted_types=("people",),
    )
    responsible_value = _limpar_valor_campo(str(info.get("responsible") or ""))
    if responsible_property and responsible_value:
        user_id, resolved_name = _resolver_usuario_notion(responsible_value)
        if user_id:
            notion_properties[responsible_property] = {"people": [{"id": user_id}]}
            filled_fields.append(responsible_property)
        else:
            warnings.append(
                f"Não encontrei o responsável '{responsible_value}' entre os usuários visíveis da integração."
            )

    return True, notion_properties, filled_fields, warnings


def _resolver_parent_notion() -> tuple[str, str]:
    if _notion_data_source_id():
        return "data_source_id", _notion_data_source_id()
    if _notion_page_id():
        return "page_id", _notion_page_id()
    if _notion_database_id():
        return "database_id", _notion_database_id()
    return "", ""


def _resolver_data_source_id(database_id: str) -> str:
    ok, payload = _notion_request("GET", f"/databases/{database_id}")
    if not ok or not isinstance(payload, dict):
        return ""
    data_sources = payload.get("data_sources", [])
    if not isinstance(data_sources, list):
        return ""
    for item in data_sources:
        if isinstance(item, dict) and item.get("id"):
            return str(item.get("id"))
    return ""


def criar_projeto_notion(
    project_name: str,
    description: str = "",
    details: dict[str, str] | None = None,
) -> tuple[bool, dict[str, Any] | str]:
    nome = (project_name or "").strip()
    if len(nome) < 2:
        return False, "Nome do projeto precisa ter ao menos 2 caracteres."

    if not notion_disponivel():
        return (
            False,
            "Integração do Notion não configurada. Defina NOVA_NOTION_TOKEN e "
            "NOVA_NOTION_PROJECTS_DATA_SOURCE_ID, NOVA_NOTION_PROJECTS_DATABASE_ID ou "
            "NOVA_NOTION_PROJECTS_PAGE_ID.",
        )

    parent_type, parent_id = _resolver_parent_notion()
    if not parent_id:
        return False, "Destino do Notion não configurado."

    properties: dict[str, Any]
    filled_fields: list[str] = []
    warnings: list[str] = []
    if parent_type == "database_id":
        resolved = _resolver_data_source_id(parent_id)
        if resolved:
            parent_type = "data_source_id"
            parent_id = resolved

    if parent_type in {"data_source_id", "database_id"}:
        schema: dict[str, Any] = {}
        if parent_type == "data_source_id":
            ok_schema, payload_schema = _notion_request("GET", f"/data_sources/{parent_id}")
            if ok_schema and isinstance(payload_schema, dict):
                raw_properties = payload_schema.get("properties", {})
                if isinstance(raw_properties, dict):
                    schema = raw_properties
        ok_props, notion_properties, filled_fields, warnings = _montar_propriedades_data_source(
            project_name=nome,
            description=description,
            details=details,
            properties=schema,
        )
        if not ok_props:
            return False, notion_properties
        properties = notion_properties
    else:
        properties = {
            "title": {
                "title": [
                    {
                        "text": {
                            "content": nome[:200],
                        }
                    }
                ]
            }
        }

    payload = {
        "parent": {
            parent_type: parent_id,
        },
        "properties": properties,
    }

    ok, out = _notion_request("POST", "/pages", payload=payload)
    if not ok or not isinstance(out, dict):
        return False, out

    return True, {
        "provider": "notion",
        "project_name": nome,
        "page_id": out.get("id"),
        "page_url": out.get("url") or out.get("public_url"),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "description": description,
        "filled_fields": filled_fields,
        "warnings": warnings,
    }

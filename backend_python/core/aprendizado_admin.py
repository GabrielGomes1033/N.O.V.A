from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
import re
import unicodedata
import uuid

from core.caminhos import pasta_dados_app
from core.knowledge_repository import KnowledgeRepository
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_APRENDIZADO = pasta_dados_app() / "aprendizado.json"
ARQUIVO_APRENDIZADO_LEGADO = Path(__file__).with_name("aprendizado.json")

_REPO = KnowledgeRepository()
_MIGRACAO_LEGADO_CONCLUIDA = False


def normalizar_texto(texto: str) -> str:
    texto = (texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    texto = re.sub(r"[^\w\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _id_curto() -> str:
    return uuid.uuid4().hex[:12]


def _normalizar_item(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None

    gatilho = str(item.get("gatilho", "")).strip()
    resposta = str(item.get("resposta", "")).strip()
    categoria = str(item.get("categoria", "geral") or "geral").strip() or "geral"
    ativo = bool(item.get("ativo", True))

    gatilho_norm = normalizar_texto(gatilho)
    if not gatilho_norm or not resposta:
        return None

    criado = str(item.get("criado_em", "")).strip() or _agora()
    atualizado = str(item.get("atualizado_em", "")).strip() or _agora()

    return {
        "id": str(item.get("id", "")).strip() or _id_curto(),
        "gatilho": gatilho,
        "gatilho_normalizado": gatilho_norm,
        "resposta": resposta,
        "categoria": categoria,
        "ativo": ativo,
        "criado_em": criado,
        "atualizado_em": atualizado,
    }


def _converter_formato_legado(dados: dict) -> list[dict]:
    itens = []
    for pergunta, respostas in (dados or {}).items():
        gatilho = str(pergunta or "").strip()
        if isinstance(respostas, str):
            respostas = [respostas]
        if not isinstance(respostas, list):
            continue
        for resposta in respostas:
            item = _normalizar_item(
                {
                    "gatilho": gatilho,
                    "resposta": str(resposta or "").strip(),
                    "categoria": "geral",
                }
            )
            if item:
                itens.append(item)
    return itens


def _normalizar_carga_bruta(dados: object) -> list[dict]:
    if isinstance(dados, dict) and isinstance(dados.get("items"), list):
        bruto = dados.get("items", [])
    elif isinstance(dados, dict):
        bruto = _converter_formato_legado(dados)
    elif isinstance(dados, list):
        bruto = dados
    else:
        bruto = []

    itens = []
    vistos_ids = set()
    for raw in bruto:
        item = _normalizar_item(raw)
        if not item:
            continue
        if item["id"] in vistos_ids:
            item["id"] = _id_curto()
        vistos_ids.add(item["id"])
        itens.append(item)
    return itens


def _carregar_base_json(caminho: Path) -> list[dict]:
    if not caminho.is_file():
        return []
    dados = carregar_json_seguro(caminho, {})
    return _normalizar_carga_bruta(dados)


def _garantir_migracao_legado() -> None:
    global _MIGRACAO_LEGADO_CONCLUIDA
    if _MIGRACAO_LEGADO_CONCLUIDA:
        return
    _MIGRACAO_LEGADO_CONCLUIDA = True

    if _REPO.has_items():
        return

    itens: list[dict] = []
    for origem in (ARQUIVO_APRENDIZADO, ARQUIVO_APRENDIZADO_LEGADO):
        if not origem.is_file():
            continue
        dados = carregar_json_seguro(origem, {})
        itens.extend(_normalizar_carga_bruta(dados))

    # Não migra vazio para evitar sobrescrever base já ativa em futuros boots.
    if not itens:
        return

    dedup = {}
    for item in itens:
        chave = (
            item.get("gatilho_normalizado", ""),
            item.get("resposta", ""),
        )
        dedup[chave] = item

    _REPO.bootstrap_if_empty(list(dedup.values()))


def carregar_base_aprendizado(arquivo: Path = ARQUIVO_APRENDIZADO) -> list[dict]:
    caminho = Path(arquivo)
    if caminho != ARQUIVO_APRENDIZADO:
        return _carregar_base_json(caminho)

    _garantir_migracao_legado()
    return _REPO.list_items()


def salvar_base_aprendizado(itens: list[dict], arquivo: Path = ARQUIVO_APRENDIZADO) -> bool:
    caminho = Path(arquivo)
    itens_validos = _normalizar_carga_bruta(itens)

    if caminho != ARQUIVO_APRENDIZADO:
        payload = {"versao": 2, "items": itens_validos}
        salvar_json_seguro(caminho, payload)
        return True

    _garantir_migracao_legado()
    _REPO.replace_all(itens_validos)
    return True


def listar_aprendizados() -> list[dict]:
    itens = carregar_base_aprendizado()
    return sorted(itens, key=lambda i: (i.get("categoria", ""), i.get("gatilho", "")))


def salvar_aprendizado(pergunta: str, resposta: str, categoria: str = "geral") -> int:
    pergunta = (pergunta or "").strip()
    resposta = (resposta or "").strip()
    categoria = (categoria or "geral").strip() or "geral"

    if not pergunta or not resposta:
        raise ValueError("Pergunta e resposta precisam estar preenchidas.")

    _garantir_migracao_legado()

    pergunta_norm = normalizar_texto(pergunta)
    if not pergunta_norm:
        raise ValueError("Pergunta e resposta precisam estar preenchidas.")

    agora = _agora()
    return _REPO.upsert_for_trigger_response(
        item_id=_id_curto(),
        gatilho=pergunta,
        gatilho_normalizado=pergunta_norm,
        resposta=resposta,
        categoria=categoria,
        criado_em=agora,
        atualizado_em=agora,
    )


def atualizar_aprendizado(
    item_id: str,
    gatilho: str | None = None,
    resposta: str | None = None,
    categoria: str | None = None,
    ativo: bool | None = None,
) -> dict | None:
    _garantir_migracao_legado()

    gatilho_limpo: str | None = None
    gatilho_norm: str | None = None
    if gatilho is not None:
        g = gatilho.strip()
        if g:
            gatilho_limpo = g
            gatilho_norm = normalizar_texto(g)

    resposta_limpa: str | None = None
    if resposta is not None and resposta.strip():
        resposta_limpa = resposta.strip()

    categoria_limpa: str | None = None
    if categoria is not None:
        categoria_limpa = categoria.strip() or "geral"

    return _REPO.update_item(
        item_id=item_id,
        gatilho=gatilho_limpo,
        gatilho_normalizado=gatilho_norm,
        resposta=resposta_limpa,
        categoria=categoria_limpa,
        ativo=ativo,
        atualizado_em=_agora(),
    )


def remover_aprendizado(item_id: str) -> bool:
    _garantir_migracao_legado()
    return _REPO.delete_item(item_id)


def buscar_resposta_aprendida(msg: str) -> str | None:
    _garantir_migracao_legado()

    texto = normalizar_texto(msg)
    if not texto:
        return None

    exatas = _REPO.list_active_exact(texto)
    if exatas:
        return random.choice(exatas)

    similares = _REPO.list_active_similar(texto)
    if similares:
        return random.choice(similares)

    return None


def carregar_aprendizado_legado() -> dict[str, list[str]]:
    resultado: dict[str, list[str]] = {}
    for item in carregar_base_aprendizado():
        if not item.get("ativo", True):
            continue
        chave = item.get("gatilho_normalizado", "")
        resp = str(item.get("resposta", "")).strip()
        if not chave or not resp:
            continue
        resultado.setdefault(chave, [])
        if resp not in resultado[chave]:
            resultado[chave].append(resp)
    return resultado


def exportar_aprendizado_json() -> dict:
    itens = listar_aprendizados()
    categorias = sorted({item.get("categoria", "geral") for item in itens})
    return {
        "ok": True,
        "total": len(itens),
        "categorias": categorias,
        "items": itens,
    }

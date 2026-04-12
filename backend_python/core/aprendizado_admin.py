from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import random
import re
import unicodedata
import uuid

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_APRENDIZADO = pasta_dados_app() / "aprendizado.json"
ARQUIVO_APRENDIZADO_LEGADO = Path(__file__).with_name("aprendizado.json")


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


def carregar_base_aprendizado(arquivo: Path = ARQUIVO_APRENDIZADO) -> list[dict]:
    caminho = Path(arquivo)
    dados: object = []

    if not caminho.is_file():
        if caminho == ARQUIVO_APRENDIZADO and ARQUIVO_APRENDIZADO_LEGADO.is_file():
            dados = carregar_json_seguro(ARQUIVO_APRENDIZADO_LEGADO, {})
        else:
            return []
    else:
        dados = carregar_json_seguro(caminho, [])

    if isinstance(dados, dict) and isinstance(dados.get("items"), list):
        bruto = dados.get("items", [])
    elif isinstance(dados, dict):
        bruto = _converter_formato_legado(dados)
    elif isinstance(dados, list):
        bruto = dados
    else:
        bruto = []

    itens = []
    vistos = set()
    for raw in bruto:
        item = _normalizar_item(raw)
        if not item:
            continue
        if item["id"] in vistos:
            item["id"] = _id_curto()
        vistos.add(item["id"])
        itens.append(item)

    if caminho == ARQUIVO_APRENDIZADO:
        salvar_base_aprendizado(itens, arquivo=caminho)
    return itens


def salvar_base_aprendizado(itens: list[dict], arquivo: Path = ARQUIVO_APRENDIZADO) -> bool:
    payload = {"versao": 2, "items": itens}
    return salvar_json_seguro(Path(arquivo), payload)


def listar_aprendizados() -> list[dict]:
    itens = carregar_base_aprendizado()
    return sorted(itens, key=lambda i: (i.get("categoria", ""), i.get("gatilho", "")))


def salvar_aprendizado(pergunta: str, resposta: str, categoria: str = "geral") -> int:
    pergunta = (pergunta or "").strip()
    resposta = (resposta or "").strip()
    if not pergunta or not resposta:
        raise ValueError("Pergunta e resposta precisam estar preenchidas.")

    itens = carregar_base_aprendizado()
    pergunta_norm = normalizar_texto(pergunta)

    for item in itens:
        if item["gatilho_normalizado"] == pergunta_norm and item["resposta"].strip() == resposta:
            item["ativo"] = True
            item["categoria"] = categoria or item.get("categoria", "geral")
            item["atualizado_em"] = _agora()
            salvar_base_aprendizado(itens)
            return len([i for i in itens if i["gatilho_normalizado"] == pergunta_norm])

    novo = _normalizar_item(
        {
            "gatilho": pergunta,
            "resposta": resposta,
            "categoria": categoria or "geral",
            "ativo": True,
            "criado_em": _agora(),
            "atualizado_em": _agora(),
        }
    )
    if not novo:
        raise ValueError("Pergunta e resposta precisam estar preenchidas.")
    itens.append(novo)
    salvar_base_aprendizado(itens)
    return len([i for i in itens if i["gatilho_normalizado"] == pergunta_norm])


def atualizar_aprendizado(item_id: str, gatilho: str | None = None, resposta: str | None = None, categoria: str | None = None, ativo: bool | None = None) -> dict | None:
    itens = carregar_base_aprendizado()
    for item in itens:
        if item.get("id") != item_id:
            continue
        if gatilho is not None:
            gatilho = gatilho.strip()
            if gatilho:
                item["gatilho"] = gatilho
                item["gatilho_normalizado"] = normalizar_texto(gatilho)
        if resposta is not None and resposta.strip():
            item["resposta"] = resposta.strip()
        if categoria is not None:
            item["categoria"] = categoria.strip() or "geral"
        if ativo is not None:
            item["ativo"] = bool(ativo)
        item["atualizado_em"] = _agora()
        salvar_base_aprendizado(itens)
        return item
    return None


def remover_aprendizado(item_id: str) -> bool:
    itens = carregar_base_aprendizado()
    total_antes = len(itens)
    itens = [item for item in itens if item.get("id") != item_id]
    if len(itens) == total_antes:
        return False
    salvar_base_aprendizado(itens)
    return True


def buscar_resposta_aprendida(msg: str) -> str | None:
    texto = normalizar_texto(msg)
    if not texto:
        return None

    itens = [i for i in carregar_base_aprendizado() if i.get("ativo", True)]

    exatas = [i for i in itens if i.get("gatilho_normalizado") == texto]
    if exatas:
        return random.choice(exatas).get("resposta")

    similares = [i for i in itens if i.get("gatilho_normalizado") and i["gatilho_normalizado"] in texto]
    if similares:
        return random.choice(similares).get("resposta")

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

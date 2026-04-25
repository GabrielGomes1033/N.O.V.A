# Utilitários de pesquisa da NOVA.
# Este módulo tenta gerar um resumo curto do tema pesquisado antes de abrir a busca no navegador.
from __future__ import annotations

import re
from urllib.parse import quote

import requests


TIMEOUT_PADRAO = 4
WIKIPEDIA_HEADERS = {"User-Agent": "NOVA-Assistente/1.0 (resumo de pesquisa local)"}


def _limpar_texto(texto: str) -> str:
    # Remove excesso de espaços, referências e trechos que não ficam naturais no chat.
    texto = re.sub(r"\[[^\]]+\]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _resumo_curto(texto: str, limite_sentencas: int = 2, limite_chars: int = 320) -> str:
    # Encurta o texto para algo breve e agradável de ler e ouvir.
    texto = _limpar_texto(texto)
    partes = re.split(r"(?<=[.!?])\s+", texto)
    resumo = " ".join(parte for parte in partes[:limite_sentencas] if parte).strip()
    if not resumo:
        resumo = texto

    if len(resumo) > limite_chars:
        corte = resumo[:limite_chars].rsplit(" ", 1)[0].strip()
        resumo = f"{corte}..."

    return resumo


def _buscar_titulo_wikipedia(consulta: str, idioma: str) -> str | None:
    # Usa a busca da Wikipedia para encontrar a página mais provável para a consulta.
    url = (
        f"https://{idioma}.wikipedia.org/w/api.php"
        f"?action=opensearch&search={quote(consulta)}&limit=1&namespace=0&format=json"
    )
    resposta = requests.get(url, headers=WIKIPEDIA_HEADERS, timeout=TIMEOUT_PADRAO)
    resposta.raise_for_status()
    dados = resposta.json()
    titulos = dados[1] if isinstance(dados, list) and len(dados) > 1 else []
    if not titulos:
        return None
    return str(titulos[0]).strip() or None


def _buscar_resumo_wikipedia_por_titulo(titulo: str, idioma: str) -> str | None:
    # Busca o resumo da página encontrada.
    url = f"https://{idioma}.wikipedia.org/api/rest_v1/page/summary/{quote(titulo)}"
    resposta = requests.get(url, headers=WIKIPEDIA_HEADERS, timeout=TIMEOUT_PADRAO)
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    dados = resposta.json()
    extrato = str(dados.get("extract", "")).strip()
    if not extrato:
        return None
    return _resumo_curto(extrato)


def gerar_pesquisa_wikipedia(consulta: str) -> dict[str, str] | None:
    # Busca um artigo na Wikipedia e devolve os dados principais para chat, link e voz.
    consulta = consulta.strip()
    if not consulta:
        return None

    for idioma, fonte in (("pt", "Wikipedia PT"), ("en", "Wikipedia EN")):
        try:
            titulo = _buscar_titulo_wikipedia(consulta, idioma)
            if not titulo:
                continue
            resumo = _buscar_resumo_wikipedia_por_titulo(titulo, idioma)
            if resumo:
                return {
                    "titulo": titulo,
                    "resumo": resumo,
                    "fonte": fonte,
                    "url": f"https://{idioma}.wikipedia.org/wiki/{quote(titulo.replace(' ', '_'))}",
                }
        except requests.RequestException:
            continue

    return None


def gerar_resumo_pesquisa(consulta: str) -> tuple[str | None, str | None]:
    # Mantém compatibilidade com o fluxo antigo quando só o resumo é necessário.
    resultado = gerar_pesquisa_wikipedia(consulta)
    if not resultado:
        return None, None
    return resultado["resumo"], resultado["fonte"]

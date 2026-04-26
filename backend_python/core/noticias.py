from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import re
import unicodedata
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

from core.formatador import formatar_noticias

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dependência opcional
    load_dotenv = None


TIMEOUT_PADRAO = 6


def _carregar_env() -> None:
    if load_dotenv is None:
        return
    base = Path(__file__).resolve()
    candidatos = [
        base.parents[1] / ".env",
        base.parents[2] / ".env",
    ]
    for caminho in candidatos:
        if caminho.exists():
            load_dotenv(caminho, override=False)


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def _strip_tags(texto: str) -> str:
    return _limpar(re.sub(r"<[^>]+>", " ", str(texto or "")))


def _normalizar(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", base).strip()


_MAPA_NOTICIAS = {
    "brasil": {
        "title": "Notícias do Brasil",
        "gnews": {"category": "general", "country": "br", "lang": "pt"},
        "rss_query": "Brasil",
    },
    "mundo": {
        "title": "Notícias do mundo",
        "gnews": {"category": "world", "lang": "pt"},
        "rss_query": "mundo OR internacional",
    },
    "tecnologia": {
        "title": "Notícias de tecnologia",
        "gnews": {"category": "technology", "lang": "pt"},
        "rss_query": "tecnologia",
    },
    "mercado_financeiro": {
        "title": "Notícias do mercado financeiro",
        "gnews": {"category": "business", "lang": "pt"},
        "rss_query": "mercado financeiro OR bolsa OR economia",
    },
}


def detectar_categoria_noticias(texto: str) -> str | None:
    t = _normalizar(texto)
    if not any(chave in t for chave in ("noticia", "noticias", "manchete", "manchetes")):
        return None
    if "tecnologia" in t or "tech" in t:
        return "tecnologia"
    if "mercado financeiro" in t or ("economia" in t and "noticia" in t):
        return "mercado_financeiro"
    if "brasil" in t:
        return "brasil"
    if "mundo" in t or "internacional" in t or "globais" in t:
        return "mundo"
    return None


def _buscar_gnews(categoria: str, limit: int = 5) -> dict | None:
    _carregar_env()
    api_key = (os.getenv("GNEWS_API_KEY") or "").strip()
    if not api_key:
        return None

    config = _MAPA_NOTICIAS.get(categoria)
    if not config:
        return None

    try:
        resposta = requests.get(
            "https://gnews.io/api/v4/top-headlines",
            params={
                **config["gnews"],
                "max": max(1, min(int(limit), 10)),
                "apikey": api_key,
            },
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        resposta.raise_for_status()
        data = resposta.json() if resposta.text else {}
    except Exception:
        return None

    artigos = data.get("articles", []) if isinstance(data, dict) else []
    itens = []
    for artigo in artigos[:limit]:
        if not isinstance(artigo, dict):
            continue
        source = artigo.get("source", {}) if isinstance(artigo.get("source"), dict) else {}
        itens.append(
            {
                "title": _limpar(artigo.get("title", "")),
                "summary": _limpar(artigo.get("description", "")),
                "url": _limpar(artigo.get("url", "")),
                "published_at": _limpar(artigo.get("publishedAt", "")),
                "source_name": _limpar(source.get("name", "")),
            }
        )

    if not itens:
        return None

    return {
        "ok": True,
        "category": categoria,
        "title": config["title"],
        "items": itens,
        "sources": ["GNews"],
        "updated_at": _agora(),
    }


def _buscar_google_news_rss(categoria: str, limit: int = 5) -> dict:
    config = _MAPA_NOTICIAS[categoria]
    url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(config["rss_query"])
        + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )
    try:
        resposta = requests.get(
            url,
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        resposta.raise_for_status()
        root = ET.fromstring(resposta.text or "")
    except Exception:
        return {
            "ok": False,
            "category": categoria,
            "title": config["title"],
            "items": [],
            "sources": ["Google News RSS"],
            "updated_at": _agora(),
        }

    itens = []
    for item in root.findall("./channel/item")[:limit]:
        titulo = _limpar(item.findtext("title") or "")
        link = _limpar(item.findtext("link") or "")
        descricao = _strip_tags(item.findtext("description") or "")
        fonte = _limpar(item.findtext("source") or "")
        publicado = _limpar(item.findtext("pubDate") or "")
        if titulo:
            itens.append(
                {
                    "title": titulo,
                    "summary": descricao,
                    "url": link,
                    "published_at": publicado,
                    "source_name": fonte,
                }
            )

    return {
        "ok": bool(itens),
        "category": categoria,
        "title": config["title"],
        "items": itens,
        "sources": ["Google News RSS"],
        "updated_at": _agora(),
    }


def buscar_noticias_categoria(categoria: str, limit: int = 5) -> dict:
    categoria = _normalizar(categoria).replace(" ", "_")
    if categoria not in _MAPA_NOTICIAS:
        return {
            "ok": False,
            "title": "Notícias",
            "items": [],
            "sources": [],
            "updated_at": _agora(),
        }

    via_gnews = _buscar_gnews(categoria, limit=limit)
    if via_gnews:
        return via_gnews
    return _buscar_google_news_rss(categoria, limit=limit)


def responder_consulta_noticias(texto: str) -> str | None:
    categoria = detectar_categoria_noticias(texto)
    if not categoria:
        return None
    return formatar_noticias(buscar_noticias_categoria(categoria))

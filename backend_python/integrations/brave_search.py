from __future__ import annotations

import os
from typing import Any

import requests

from core.assistente_plus import pesquisar_na_internet
from core.pesquisa import gerar_pesquisa_wikipedia


BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def _map_brave_results(payload: dict[str, Any]) -> list[dict[str, str]]:
    web = payload.get("web", {}) if isinstance(payload, dict) else {}
    items = web.get("results", []) if isinstance(web, dict) else []
    results: list[dict[str, str]] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        snippet = str(item.get("description", "")).strip()
        url = str(item.get("url", "")).strip()
        if not (title or snippet or url):
            continue
        results.append(
            {
                "title": title,
                "snippet": snippet,
                "url": url,
            }
        )
    return results


def search_web(query: str) -> dict[str, Any]:
    consulta = str(query or "").strip()
    if not consulta:
        return {"ok": False, "error": "query_required", "query": ""}

    api_key = os.getenv("BRAVE_API_KEY") or os.getenv("NOVA_BRAVE_API_KEY")
    if api_key:
        try:
            response = requests.get(
                BRAVE_SEARCH_URL,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
                params={"q": consulta},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json() if response.text else {}
            results = _map_brave_results(payload)
            summary = ""
            if results:
                first = results[0]
                summary = first.get("snippet", "") or first.get("title", "")
            return {
                "ok": True,
                "provider": "brave",
                "query": consulta,
                "summary": summary,
                "results": results,
                "sources": [item.get("url", "") for item in results if item.get("url")],
            }
        except Exception as exc:
            brave_error = str(exc)
        else:
            brave_error = ""
    else:
        brave_error = "brave_api_key_missing"

    fallback = pesquisar_na_internet(consulta)
    if fallback.get("ok"):
        links = [link for link in (fallback.get("links") or []) if isinstance(link, str)]
        return {
            "ok": True,
            "provider": "fallback_search",
            "query": consulta,
            "summary": str(fallback.get("resumo", "")).strip(),
            "results": [
                {
                    "title": str(fallback.get("consulta", consulta)).strip(),
                    "snippet": str(fallback.get("resumo", "")).strip(),
                    "url": links[0] if links else "",
                }
            ],
            "sources": links or [str(src).strip() for src in (fallback.get("fontes") or [])],
            "warnings": [brave_error] if brave_error else [],
        }

    wiki = gerar_pesquisa_wikipedia(consulta)
    if wiki:
        url = str(wiki.get("url", "")).strip()
        return {
            "ok": True,
            "provider": "wikipedia",
            "query": consulta,
            "summary": str(wiki.get("resumo", "")).strip(),
            "results": [
                {
                    "title": str(wiki.get("titulo", consulta)).strip(),
                    "snippet": str(wiki.get("resumo", "")).strip(),
                    "url": url,
                }
            ],
            "sources": [url] if url else [],
            "warnings": [brave_error] if brave_error else [],
        }

    return {
        "ok": False,
        "error": "search_unavailable",
        "query": consulta,
        "warnings": [brave_error] if brave_error else [],
    }

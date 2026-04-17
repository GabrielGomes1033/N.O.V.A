from __future__ import annotations

from datetime import datetime
from html import unescape
from pathlib import Path
import ast
import math
import os
import re
import unicodedata
from urllib.parse import parse_qs, quote_plus, unquote, urlparse, urlsplit
import xml.etree.ElementTree as ET

import requests

from core.caminhos import pasta_dados_app
from core.memoria import carregar_memoria_usuario, salvar_memoria_usuario
from core.pesquisa import gerar_pesquisa_wikipedia
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_LEMBRETES = pasta_dados_app() / "lembretes.json"
TIMEOUT_PADRAO = 6


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _limpar(texto: str) -> str:
    t = (texto or "").strip()
    return re.sub(r"\s+", " ", t)


def aprender_gostos_por_mensagem(msg: str) -> None:
    texto = _limpar(msg).lower()
    if not texto:
        return

    mapa_topicos = {
        "programacao": ["python", "java", "javascript", "api", "codigo", "programa", "flutter", "backend"],
        "ia": ["ia", "inteligencia artificial", "agente", "llm", "openai", "modelo"],
        "financas": ["mercado", "acao", "ações", "dolar", "euro", "bitcoin", "ethereum", "cripto"],
        "clima": ["clima", "tempo", "chuva", "temperatura"],
        "musica": ["musica", "música", "playlist", "som", "ouvir"],
        "produtividade": ["lembrete", "agenda", "tarefa", "projeto", "organizar"],
    }

    hits = []
    for topico, palavras in mapa_topicos.items():
        if any(p in texto for p in palavras):
            hits.append(topico)

    if not hits:
        return

    memoria = carregar_memoria_usuario()
    favoritos = memoria.get("topicos_favoritos", [])
    if not isinstance(favoritos, list):
        favoritos = []

    for topico in hits:
        favoritos.append(topico)

    # Mantém os 8 tópicos mais recorrentes na janela recente.
    contagem = {}
    for item in favoritos[-120:]:
        contagem[item] = contagem.get(item, 0) + 1

    top_ordenado = sorted(contagem.items(), key=lambda kv: kv[1], reverse=True)
    memoria["topicos_favoritos"] = [k for k, _ in top_ordenado[:8]]
    memoria["ultima_interacao"] = _agora()
    salvar_memoria_usuario(memoria)


def resumo_adaptacao_usuario() -> str:
    memoria = carregar_memoria_usuario()
    favoritos = memoria.get("topicos_favoritos", [])
    if not isinstance(favoritos, list) or not favoritos:
        return "Ainda estou entendendo seus gostos."
    return "Estou me adaptando ao seu estilo. Seus tópicos favoritos recentes: " + ", ".join(favoritos[:5]) + "."


def _strip_tags(texto_html: str) -> str:
    return _limpar(unescape(re.sub(r"<[^>]+>", " ", texto_html or "")))


def _tokens(texto: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9à-ÿ]+", (texto or "").lower()) if t}


def _dedupe_ordem(itens: list[str]) -> list[str]:
    vistos = set()
    saida: list[str] = []
    for item in itens:
        v = (item or "").strip()
        if not v or v in vistos:
            continue
        vistos.add(v)
        saida.append(v)
    return saida


def _resumir_texto(texto: str, limite: int = 220) -> str:
    t = _limpar(texto)
    if len(t) <= limite:
        return t
    recorte = t[: max(40, limite)].rsplit(" ", 1)[0].strip()
    return (recorte or t[:limite]).rstrip(" ,.;:-") + "..."


def _normalizar_ascii(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    return t.encode("ascii", "ignore").decode("ascii").lower()


def _termos_relevantes_consulta(consulta: str) -> set[str]:
    stopwords = {
        "de",
        "do",
        "da",
        "dos",
        "das",
        "e",
        "a",
        "o",
        "as",
        "os",
        "um",
        "uma",
        "para",
        "por",
        "com",
        "sem",
        "sobre",
        "que",
        "como",
        "hoje",
        "agora",
        "qual",
        "quais",
        "me",
        "na",
        "no",
        "nas",
        "nos",
    }
    return {t for t in _tokens(consulta) if len(t) >= 3 and t not in stopwords}


def _pontuar_resultado_web(item: dict, termos: set[str]) -> int:
    if not isinstance(item, dict):
        return -1
    titulo = _limpar(str(item.get("title", ""))).lower()
    snippet = _limpar(str(item.get("snippet", ""))).lower()
    domain = _limpar(str(item.get("domain", ""))).lower()
    if not titulo and not snippet:
        return -1

    texto = f"{titulo} {snippet} {domain}".strip()
    if not texto:
        return -1

    score = 0
    houve_match = False
    titulo_n = _normalizar_ascii(titulo)
    snippet_n = _normalizar_ascii(snippet)
    domain_n = _normalizar_ascii(domain)
    termos_n = {_normalizar_ascii(t) for t in termos}
    if termos:
        for termo in termos_n:
            if termo in titulo_n:
                score += 4
                houve_match = True
            elif termo in snippet_n:
                score += 2
                houve_match = True
            elif termo in domain_n:
                score += 1
                houve_match = True
        if not houve_match:
            return 0
    else:
        score += 1

    # Evita snippets longos/poluídos ganharem prioridade.
    tam_snippet = len(snippet)
    if 35 <= tam_snippet <= 220:
        score += 2
    elif tam_snippet > 320:
        score -= 1

    return score


def _organizar_resultados_web(resultados: list[dict], consulta: str) -> list[dict]:
    if not isinstance(resultados, list) or not resultados:
        return []
    termos = _termos_relevantes_consulta(consulta)
    enriquecidos: list[tuple[int, int, dict]] = []
    for idx, item in enumerate(resultados):
        score = _pontuar_resultado_web(item, termos)
        if score < 0:
            continue
        if termos and score == 0:
            continue
        enriquecidos.append((score, idx, item))

    if not enriquecidos:
        return resultados[:4] if not termos else []

    enriquecidos.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    # Evita repetição excessiva do mesmo domínio no topo.
    saida: list[dict] = []
    dom_count: dict[str, int] = {}
    for _, _, item in enriquecidos:
        domain = _limpar(str(item.get("domain", ""))).lower()
        if domain:
            vezes = dom_count.get(domain, 0)
            if vezes >= 2:
                continue
            dom_count[domain] = vezes + 1
        saida.append(item)
        if len(saida) >= 6:
            break

    return saida or resultados[:4]


def _consulta_base(consulta: str) -> str:
    c = (consulta or "").strip()
    c = re.sub(
        r"^(biografia de|quem e|quem é|sobre|cotacao de|cotação de|cotacao|cotação|preco de|preço de|valor de)\s+",
        "",
        c,
        flags=re.IGNORECASE,
    )
    c = re.sub(r"\b(hoje|agora)$", "", c, flags=re.IGNORECASE).strip(" ,.-")
    return c or (consulta or "").strip()


def extrair_consulta_pesquisa_web(mensagem: str) -> str:
    texto = _limpar((mensagem or "").strip(" \n\t"))
    if not texto:
        return ""

    padroes = (
        r"^(?:\/google)\s+",
        r"^(?:pesquise|pesquisar|procure|procurar|busque|buscar)\s+(?:na internet\s+)?(?:sobre\s+)?",
        r"^(?:me explique|explique|explica)\s+",
        r"^(?:me fale sobre|fale sobre|quero saber sobre)\s+",
        r"^(?:me atualize sobre|atualize sobre|ultimas noticias sobre|últimas notícias sobre|noticias sobre|notícias sobre)\s+",
        r"^(?:qual a diferenca entre|qual a diferença entre|diferenca entre|diferença entre|compare)\s+",
        r"^(?:o que e|o que é|quem e|quem é|qual e|qual é|como funciona)\s+",
    )

    consulta = texto
    houve_mudanca = True
    while houve_mudanca and consulta:
        houve_mudanca = False
        for padrao in padroes:
            novo = re.sub(padrao, "", consulta, flags=re.IGNORECASE).strip(" :,-?")
            if novo != consulta:
                consulta = novo
                houve_mudanca = True
                break

    return _consulta_base(consulta.strip(" ?")) if consulta else ""


def mensagem_vale_pesquisa_web(mensagem: str) -> bool:
    texto = _normalizar_ascii(_limpar(mensagem))
    if not texto:
        return False

    if texto.startswith("/") and not texto.startswith("/google "):
        return False

    bloqueios_exatos = {
        "oi",
        "ola",
        "olá",
        "e ai",
        "e aí",
        "tudo bem",
        "obrigado",
        "obrigada",
        "valeu",
        "tchau",
        "ate logo",
        "até logo",
        "ajuda",
        "help",
    }
    if texto in {_normalizar_ascii(item) for item in bloqueios_exatos}:
        return False

    bloqueios_trechos = (
        "seu nome",
        "quem voce e",
        "quem você e",
        "como voce esta",
        "como você esta",
        "que horas",
        "qual a hora",
        "data de hoje",
    )
    if any(trecho in texto for trecho in bloqueios_trechos):
        return False

    return len(re.findall(r"[a-z0-9à-ÿ]+", texto)) >= 2


def deve_acionar_pesquisa_web(mensagem: str, modo_pesquisa: bool = False) -> bool:
    if not mensagem_vale_pesquisa_web(mensagem):
        return False

    texto = _normalizar_ascii(_limpar(mensagem))
    tokens = re.findall(r"[a-z0-9]+", texto)

    gatilhos_explicitos = (
        "pesquise",
        "pesquisar",
        "procure",
        "procurar",
        "buscar",
        "busque",
        "na internet",
        "me explique",
        "explique",
        "me fale sobre",
        "quero saber sobre",
        "ultimas noticias",
        "ultimas atualizacoes",
        "atualizacoes sobre",
        "noticias sobre",
        "diferenca entre",
        "compare",
        "comparar",
        "como funciona",
        "o que e",
        "quem e",
        "qual e",
    )
    if any(gatilho in texto for gatilho in gatilhos_explicitos):
        return True

    interrogativos_factuais = (
        "quem ",
        "qual ",
        "quais ",
        "quando ",
        "onde ",
        "como ",
        "quanto ",
        "quantos ",
        "quantas ",
        "por que ",
        "porque ",
    )
    if texto.startswith(interrogativos_factuais) and len(tokens) >= 3:
        return True

    if any(t in texto for t in ("hoje", "agora", "atual", "atualizado", "recente", "ultimos", "ultimas")):
        return True

    if modo_pesquisa and (("?" in (mensagem or "")) or len(tokens) >= 5):
        return True

    return False


def _normalizar_url_resultado(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        parsed = urlsplit(raw)
        if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
            q = parse_qs(parsed.query or "")
            destino = (q.get("uddg") or [""])[0]
            if destino:
                return unquote(destino)
    except Exception:
        pass
    return raw


def _buscar_bing_web(consulta: str, limit: int = 5) -> list[dict]:
    try:
        url = f"https://www.bing.com/search?format=rss&q={quote_plus(consulta)}"
        r = requests.get(
            url,
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        r.raise_for_status()
        root = ET.fromstring(r.text)
    except Exception:
        return []

    itens: list[dict] = []
    vistos = set()
    for item in root.findall("./channel/item"):
        title = _limpar((item.findtext("title") or ""))
        link = _normalizar_url_resultado(item.findtext("link") or "")
        desc = _strip_tags(item.findtext("description") or "")
        if not link or link in vistos:
            continue
        vistos.add(link)
        dominio = urlparse(link).netloc.lower().replace("www.", "")
        itens.append(
            {
                "title": title,
                "snippet": desc,
                "url": link,
                "domain": dominio,
            }
        )
        if len(itens) >= max(1, limit):
            break
    return itens


def _buscar_brave_web(consulta: str, limit: int = 5) -> list[dict]:
    api_key = (
        os.getenv("NOVA_BRAVE_API_KEY")
        or os.getenv("BRAVE_SEARCH_API_KEY")
        or os.getenv("BRAVE_API_KEY")
        or ""
    ).strip()
    if not api_key:
        return []
    try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={
                "q": consulta,
                "count": max(1, min(int(limit), 20)),
                "search_lang": "pt",
                "country": "br",
            },
            headers={
                "X-Subscription-Token": api_key,
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "User-Agent": "NOVA-Assistente/1.0",
            },
            timeout=TIMEOUT_PADRAO,
        )
        r.raise_for_status()
        data = r.json() if r.text else {}
    except Exception:
        return []

    results = (
        data.get("web", {}).get("results", [])
        if isinstance(data, dict)
        else []
    )
    if not isinstance(results, list):
        return []

    itens: list[dict] = []
    vistos = set()
    for item in results[: max(1, limit * 2)]:
        if not isinstance(item, dict):
            continue
        url = _normalizar_url_resultado(str(item.get("url", "")).strip())
        if not url or url in vistos:
            continue
        vistos.add(url)
        title = _limpar(str(item.get("title", "")))
        snippet_raw = str(item.get("description", "") or "")
        if not snippet_raw:
            extras = item.get("extra_snippets", [])
            if isinstance(extras, list) and extras:
                snippet_raw = str(extras[0] or "")
        snippet = _limpar(snippet_raw)
        dominio = urlparse(url).netloc.lower().replace("www.", "")
        itens.append(
            {
                "title": title,
                "snippet": snippet,
                "url": url,
                "domain": dominio,
            }
        )
        if len(itens) >= limit:
            break
    return itens


def _buscar_serpapi_web(consulta: str, limit: int = 5) -> list[dict]:
    api_key = (
        os.getenv("NOVA_SERPAPI_KEY")
        or os.getenv("SERPAPI_API_KEY")
        or os.getenv("SERPAPI_KEY")
        or ""
    ).strip()
    if not api_key:
        return []
    try:
        r = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": consulta,
                "api_key": api_key,
                "hl": "pt-br",
                "gl": "br",
                "num": max(1, min(int(limit), 10)),
            },
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        r.raise_for_status()
        data = r.json() if r.text else {}
    except Exception:
        return []

    results = data.get("organic_results", []) if isinstance(data, dict) else []
    if not isinstance(results, list):
        return []

    itens: list[dict] = []
    vistos = set()
    for item in results[: max(1, limit * 2)]:
        if not isinstance(item, dict):
            continue
        url = _normalizar_url_resultado(str(item.get("link", "")).strip())
        if not url or url in vistos:
            continue
        vistos.add(url)
        title = _limpar(str(item.get("title", "")))
        snippet = _limpar(str(item.get("snippet", "")))
        dominio = urlparse(url).netloc.lower().replace("www.", "")
        itens.append(
            {
                "title": title,
                "snippet": snippet,
                "url": url,
                "domain": dominio,
            }
        )
        if len(itens) >= limit:
            break
    return itens


def _buscar_duckduckgo_web(consulta: str, limit: int = 5) -> list[dict]:
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(consulta)}"
        r = requests.get(
            url,
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        r.raise_for_status()
        html = r.text or ""
    except Exception:
        return []

    titulos = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</a>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    itens: list[dict] = []
    vistos = set()
    for idx, (href, titulo_html) in enumerate(titulos[: max(1, limit * 2)]):
        destino = _normalizar_url_resultado(href)
        if not destino or destino in vistos:
            continue
        vistos.add(destino)
        titulo = _strip_tags(titulo_html)
        snippet = _strip_tags(snippets[idx] if idx < len(snippets) else "")
        dominio = urlparse(destino).netloc.lower().replace("www.", "")
        itens.append(
            {
                "title": titulo,
                "snippet": snippet,
                "url": destino,
                "domain": dominio,
            }
        )
        if len(itens) >= limit:
            break
    return itens


def _buscar_itunes_musica(consulta: str, limit: int = 3) -> list[str]:
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": consulta, "entity": "song", "limit": max(1, limit)},
            timeout=TIMEOUT_PADRAO,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results", []) if isinstance(data, dict) else []
        linhas = []
        for item in results[:limit]:
            track = _limpar(str(item.get("trackName", "")))
            artist = _limpar(str(item.get("artistName", "")))
            album = _limpar(str(item.get("collectionName", "")))
            if track and artist:
                linhas.append(f"{track} - {artist}" + (f" ({album})" if album else ""))
        return linhas
    except Exception:
        return []


def _buscar_financas_web(consulta: str) -> list[str]:
    try:
        r = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": consulta, "quotesCount": 5, "newsCount": 3},
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        r.raise_for_status()
        data = r.json() if r.text else {}
        linhas = []
        for q in (data.get("quotes", []) or [])[:4]:
            symbol = _limpar(str(q.get("symbol", "")))
            nome = _limpar(str(q.get("shortname") or q.get("longname") or ""))
            exch = _limpar(str(q.get("exchDisp", "")))
            if symbol and nome:
                linhas.append(f"{symbol}: {nome}" + (f" [{exch}]" if exch else ""))
        for n in (data.get("news", []) or [])[:2]:
            t = _limpar(str(n.get("title", "")))
            p = _limpar(str(n.get("publisher", "")))
            if t:
                linhas.append(t + (f" ({p})" if p else ""))
        return linhas[:6]
    except Exception:
        return []


def _buscar_github_programacao(consulta: str, limit: int = 3) -> list[str]:
    try:
        r = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": consulta, "sort": "stars", "order": "desc", "per_page": max(1, limit)},
            timeout=TIMEOUT_PADRAO,
            headers={"Accept": "application/vnd.github+json"},
        )
        r.raise_for_status()
        data = r.json() if r.text else {}
        items = data.get("items", []) if isinstance(data, dict) else []
        linhas = []
        for item in items[:limit]:
            full_name = _limpar(str(item.get("full_name", "")))
            stars = int(item.get("stargazers_count", 0) or 0)
            desc = _limpar(str(item.get("description", "")))
            if full_name:
                linha = f"{full_name} ★{stars}"
                if desc:
                    linha += f" - {desc[:120]}"
                linhas.append(linha)
        return linhas
    except Exception:
        return []


def pesquisar_na_internet(consulta: str) -> dict:
    consulta = _limpar(consulta)
    if not consulta:
        return {"ok": False, "resumo": "Consulta vazia.", "fontes": [], "links": []}

    consulta_base = _consulta_base(consulta)
    tk = _tokens(consulta_base)
    termos_consulta = _termos_relevantes_consulta(consulta_base)
    secoes: list[str] = []
    resumo_rapido = ""
    destaques_web: list[str] = []
    secao_programacao: list[str] = []
    secao_musica: list[str] = []
    secao_financas: list[str] = []
    fontes: list[str] = []
    links: list[str] = []

    # 1) DuckDuckGo instant answer
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(consulta)}&format=json&no_redirect=1&no_html=1"
        r = requests.get(url, timeout=TIMEOUT_PADRAO)
        r.raise_for_status()
        data = r.json()
        abstract = _limpar(str(data.get("AbstractText", "")))
        heading = _limpar(str(data.get("Heading", "")))
        if abstract:
            prefixo = f"{heading}: " if heading else ""
            candidato = _resumir_texto(prefixo + abstract, limite=280)
            score = _pontuar_resultado_web({"title": heading, "snippet": abstract, "domain": ""}, termos_consulta)
            if score > 0 or not termos_consulta:
                resumo_rapido = candidato
                fontes.append("DuckDuckGo")
        else:
            relacionados = data.get("RelatedTopics", [])
            itens = []
            if isinstance(relacionados, list):
                for item in relacionados[:4]:
                    if isinstance(item, dict) and item.get("Text"):
                        itens.append(_limpar(str(item.get("Text"))))
                    elif isinstance(item, dict) and isinstance(item.get("Topics"), list):
                        for sub in item.get("Topics", [])[:2]:
                            if isinstance(sub, dict) and sub.get("Text"):
                                itens.append(_limpar(str(sub.get("Text"))))
                    if len(itens) >= 4:
                        break
            if itens:
                candidato = _resumir_texto("; ".join(itens[:3]), limite=260)
                score = _pontuar_resultado_web({"title": "", "snippet": candidato, "domain": ""}, termos_consulta)
                if score > 0 or not termos_consulta:
                    resumo_rapido = candidato
                    fontes.append("DuckDuckGo")
    except Exception:
        pass

    # 2) Busca web geral (não limitada a Wikipedia), com provider premium opcional.
    provider_busca = ""
    web_results = _buscar_brave_web(consulta_base, limit=6)
    if web_results:
        provider_busca = "BraveSearchAPI"
    if not web_results:
        web_results = _buscar_serpapi_web(consulta_base, limit=6)
        if web_results:
            provider_busca = "SerpAPI"
    if not web_results:
        web_results = _buscar_bing_web(consulta_base, limit=5)
        if web_results:
            provider_busca = "Bing"
    if not web_results:
        web_results = _buscar_duckduckgo_web(consulta_base, limit=5)
        if web_results:
            provider_busca = "DuckDuckGoHTML"
    if web_results:
        if provider_busca:
            fontes.append(provider_busca)
        web_results_ordenados = _organizar_resultados_web(web_results, consulta_base)
        for item in web_results_ordenados[:3]:
            titulo = _resumir_texto(str(item.get("title", "")), limite=95)
            snippet = _resumir_texto(str(item.get("snippet", "")), limite=125)
            dominio = _limpar(str(item.get("domain", "")))
            url_item = _limpar(str(item.get("url", "")))
            if url_item:
                links.append(url_item)
            if dominio:
                fontes.append(dominio)

            if titulo and snippet:
                linha = f"{titulo} ({dominio}) — {snippet}" if dominio else f"{titulo} — {snippet}"
            elif titulo:
                linha = f"{titulo} ({dominio})" if dominio else titulo
            else:
                linha = f"{snippet} ({dominio})" if dominio else snippet
            linha = _limpar(linha)
            if linha:
                destaques_web.append(linha)

    # 3) Wikipedia (continua como fonte extra, com consulta simplificada)
    try:
        wiki = gerar_pesquisa_wikipedia(consulta_base)
        if wiki:
            titulo_wiki = _resumir_texto(str(wiki.get("titulo", "")), limite=80)
            resumo_wiki = _resumir_texto(str(wiki.get("resumo", "")), limite=200)
            trecho = _limpar(f"{titulo_wiki}: {resumo_wiki}") if titulo_wiki else resumo_wiki
            score_wiki = _pontuar_resultado_web(
                {"title": titulo_wiki, "snippet": resumo_wiki, "domain": "wikipedia.org"},
                termos_consulta,
            )
            if trecho and (score_wiki > 0 or not termos_consulta):
                if not resumo_rapido:
                    resumo_rapido = trecho
                elif len(destaques_web) < 4:
                    destaques_web.append(f"Wikipedia — {trecho}")
                fontes.append(wiki.get("fonte", "Wikipedia"))
                if wiki.get("url"):
                    links.append(str(wiki.get("url")))
    except Exception:
        pass

    # 4) StackOverflow + GitHub quando assunto técnico
    tech_tokens = {
        "api",
        "python",
        "java",
        "javascript",
        "flutter",
        "agente",
        "ia",
        "llm",
        "erro",
        "bug",
        "codigo",
        "código",
        "programacao",
        "programação",
        "backend",
        "frontend",
    }
    if any(t in tk for t in tech_tokens):
        try:
            so_url = (
                "https://api.stackexchange.com/2.3/search/advanced"
                f"?order=desc&sort=relevance&site=stackoverflow&accepted=True&answers=1&title={quote_plus(consulta_base)}"
            )
            r = requests.get(so_url, timeout=TIMEOUT_PADRAO)
            r.raise_for_status()
            data = r.json()
            items = data.get("items", []) if isinstance(data, dict) else []
            titulos = []
            for item in items[:3]:
                title = _limpar(re.sub(r"<[^>]+>", "", str(item.get("title", ""))))
                if title:
                    titulos.append(title)
            if titulos:
                for t in titulos[:2]:
                    secao_programacao.append("Stack Overflow: " + _resumir_texto(t, limite=110))
                fontes.append("StackOverflow")
        except Exception:
            pass
        gh = _buscar_github_programacao(consulta_base, limit=3)
        if gh:
            for item in gh[:2]:
                secao_programacao.append("GitHub: " + _resumir_texto(item, limite=125))
            fontes.append("GitHub")

    # 5) Música
    music_tokens = {"musica", "música", "musicas", "músicas", "cantor", "banda", "album", "álbum", "playlist"}
    if any(t in tk for t in music_tokens):
        tracks = _buscar_itunes_musica(consulta_base, limit=4)
        if tracks:
            secao_musica = [_resumir_texto(t, limite=110) for t in tracks[:4]]
            fontes.append("iTunes")

    # 6) Finanças
    finance_tokens = {"acao", "ações", "bolsa", "dolar", "dólar", "euro", "bitcoin", "ethereum", "cripto", "financa", "finanças", "mercado", "cotacao", "cotação"}
    if any(t in tk for t in finance_tokens):
        cot = cotacoes_financeiras()
        if cot.get("ok"):
            partes = []
            if cot.get("dolar_brl") is not None:
                partes.append(f"Dólar R$ {cot['dolar_brl']:.4f}")
            if cot.get("euro_brl") is not None:
                partes.append(f"Euro R$ {cot['euro_brl']:.4f}")
            if cot.get("bitcoin_usd") is not None:
                partes.append(f"Bitcoin US$ {cot['bitcoin_usd']:.2f}")
            if cot.get("ethereum_usd") is not None:
                partes.append(f"Ethereum US$ {cot['ethereum_usd']:.2f}")
            if partes:
                secao_financas.append("Cotações: " + " | ".join(partes))
            for src in cot.get("source", []) or []:
                fontes.append(str(src))
        mercados = _buscar_financas_web(consulta_base)
        if mercados:
            for item in mercados[:3]:
                secao_financas.append(_resumir_texto(item, limite=120))
            fontes.append("YahooFinance")

    if resumo_rapido:
        secoes.append("Resumo direto:\n" + resumo_rapido)

    if destaques_web:
        linhas = [f"{i}. {txt}" for i, txt in enumerate(destaques_web[:4], start=1)]
        secoes.append("Pontos principais:\n" + "\n".join(linhas))

    if secao_programacao:
        secoes.append("Contexto técnico:\n" + "\n".join(f"- {x}" for x in secao_programacao[:4]))

    if secao_musica:
        secoes.append("Referências de música:\n" + "\n".join(f"- {x}" for x in secao_musica[:4]))

    if secao_financas:
        secoes.append("Panorama financeiro:\n" + "\n".join(f"- {x}" for x in secao_financas[:4]))

    if not secoes:
        return {
            "ok": False,
            "resumo": "Não consegui coletar fontes agora. Se quiser, me ensine essa resposta com /ensinar pergunta = resposta.",
            "fontes": [],
            "links": [],
        }

    resumo = "\n\n".join(s for s in secoes if s.strip()).strip()
    if len(resumo) > 1400:
        resumo = resumo[:1400].rsplit(" ", 1)[0].rstrip(" ,.;:-") + "..."

    fontes = _dedupe_ordem(fontes)
    links = _dedupe_ordem(links)

    return {
        "ok": True,
        "consulta": consulta_base,
        "resumo": resumo,
        "fontes": fontes[:12],
        "links": links[:8],
    }


def formatar_resposta_pesquisa(resultado: dict, max_fontes: int = 6, max_links: int = 3) -> str:
    if not isinstance(resultado, dict):
        return "Não consegui organizar a resposta da pesquisa agora."

    resumo = str(resultado.get("resumo", "")).strip()
    if not resumo:
        return "Não consegui encontrar um resumo agora."

    consulta = _limpar(str(resultado.get("consulta", "")))
    if consulta:
        abertura = f"Pesquisei sobre {consulta} e organizei o que encontrei de forma direta:"
    else:
        abertura = "Pesquisei agora e organizei o que encontrei de forma direta:"

    partes = [abertura, resumo]

    fontes_raw = resultado.get("fontes", [])
    fontes = _dedupe_ordem([str(x) for x in fontes_raw if str(x).strip()])[: max(1, max_fontes)]
    if fontes:
        partes.append("Fontes consultadas:\n" + "\n".join(f"- {f}" for f in fontes))

    links_raw = resultado.get("links", [])
    links = _dedupe_ordem([str(x) for x in links_raw if str(x).strip()])[: max(1, max_links)]
    if links:
        partes.append("Se quiser se aprofundar:\n" + "\n".join(f"{i}. {u}" for i, u in enumerate(links, start=1)))

    texto = "\n\n".join(p for p in partes if p.strip())
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return texto


def cotacoes_financeiras() -> dict:
    resultado = {
        "ok": True,
        "dolar_brl": None,
        "euro_brl": None,
        "bitcoin_usd": None,
        "ethereum_usd": None,
        "updated_at": _agora(),
        "source": [],
    }

    try:
        fx = requests.get("https://api.frankfurter.app/latest?from=USD&to=BRL", timeout=TIMEOUT_PADRAO)
        fx.raise_for_status()
        d = fx.json()
        resultado["dolar_brl"] = float(d.get("rates", {}).get("BRL"))
        resultado["source"].append("Frankfurter")
    except Exception:
        pass

    try:
        fx = requests.get("https://api.frankfurter.app/latest?from=EUR&to=BRL", timeout=TIMEOUT_PADRAO)
        fx.raise_for_status()
        d = fx.json()
        resultado["euro_brl"] = float(d.get("rates", {}).get("BRL"))
        if "Frankfurter" not in resultado["source"]:
            resultado["source"].append("Frankfurter")
    except Exception:
        pass

    try:
        cg = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd",
            timeout=TIMEOUT_PADRAO,
        )
        cg.raise_for_status()
        d = cg.json()
        resultado["bitcoin_usd"] = float(d.get("bitcoin", {}).get("usd"))
        resultado["ethereum_usd"] = float(d.get("ethereum", {}).get("usd"))
        resultado["source"].append("CoinGecko")
    except Exception:
        pass

    if not any([resultado["dolar_brl"], resultado["euro_brl"], resultado["bitcoin_usd"], resultado["ethereum_usd"]]):
        return {"ok": False, "error": "sem_dados"}

    return resultado


def formatar_cotacoes_humanas(c: dict) -> str:
    if c.get("ok") is not True:
        return "Não consegui atualizar cotações agora."

    partes = []
    if c.get("dolar_brl") is not None:
        partes.append(f"Dólar: R$ {c['dolar_brl']:.4f}")
    if c.get("euro_brl") is not None:
        partes.append(f"Euro: R$ {c['euro_brl']:.4f}")
    if c.get("bitcoin_usd") is not None:
        partes.append(f"Bitcoin: US$ {c['bitcoin_usd']:.2f}")
    if c.get("ethereum_usd") is not None:
        partes.append(f"Ethereum: US$ {c['ethereum_usd']:.2f}")

    base = " | ".join(partes) if partes else "Sem cotações disponíveis."
    fontes = c.get("source", [])
    if fontes:
        base += "\nFontes: " + ", ".join(fontes)
    return base


def consultar_clima(cidade: str | None = None) -> str:
    cidade = _limpar(cidade or "")
    if not cidade:
        cidade = "Sao Paulo"

    try:
        url = f"https://wttr.in/{quote_plus(cidade)}?format=j1"
        r = requests.get(url, timeout=TIMEOUT_PADRAO)
        r.raise_for_status()
        d = r.json()
        atual = (d.get("current_condition") or [{}])[0]
        temp = atual.get("temp_C")
        sens = atual.get("FeelsLikeC")
        desc = ((atual.get("weatherDesc") or [{}])[0].get("value") or "").strip().lower()
        if temp is None:
            return "Não consegui ler o clima agora."
        return f"Agora em {cidade}: {desc}, temperatura de {temp}°C e sensação de {sens}°C."
    except Exception:
        return "Não consegui consultar o clima agora."


def _descricao_weathercode(code: int) -> str:
    mapa = {
        0: "céu limpo",
        1: "predominantemente limpo",
        2: "parcialmente nublado",
        3: "nublado",
        45: "névoa",
        48: "névoa com geada",
        51: "garoa fraca",
        53: "garoa moderada",
        55: "garoa intensa",
        61: "chuva fraca",
        63: "chuva moderada",
        65: "chuva forte",
        71: "neve fraca",
        73: "neve moderada",
        75: "neve forte",
        80: "pancadas de chuva fracas",
        81: "pancadas de chuva moderadas",
        82: "pancadas de chuva fortes",
        95: "trovoadas",
        96: "trovoadas com granizo fraco",
        99: "trovoadas com granizo forte",
    }
    return mapa.get(int(code), "condição variável")


def consultar_clima_por_coordenadas(latitude: float, longitude: float) -> str:
    try:
        lat = float(latitude)
        lon = float(longitude)
    except Exception:
        return "Coordenadas inválidas para clima."

    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,weathercode"
        )
        r = requests.get(url, timeout=TIMEOUT_PADRAO)
        r.raise_for_status()
        data = r.json()
        current = data.get("current", {}) if isinstance(data, dict) else {}
        temp = current.get("temperature_2m")
        sens = current.get("apparent_temperature")
        code = int(current.get("weathercode", -1))
        if temp is None:
            return "Não consegui ler o clima por coordenadas agora."
        desc = _descricao_weathercode(code)
        return (
            f"Agora na sua localização ({lat:.4f}, {lon:.4f}): {desc}, "
            f"temperatura de {temp}°C e sensação de {sens}°C."
        )
    except Exception:
        return "Não consegui consultar o clima da sua localização agora."


def _carregar_lembretes() -> list[dict]:
    dados = carregar_json_seguro(ARQUIVO_LEMBRETES, [])
    if not isinstance(dados, list):
        return []
    validos = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        texto = _limpar(str(item.get("texto", "")))
        if not texto:
            continue
        validos.append(
            {
                "id": str(item.get("id", "")).strip() or f"lem_{int(datetime.now().timestamp())}",
                "texto": texto,
                "quando": _limpar(str(item.get("quando", ""))),
                "criado_em": _limpar(str(item.get("criado_em", ""))) or _agora(),
                "feito": bool(item.get("feito", False)),
            }
        )
    return validos


def _salvar_lembretes(lembretes: list[dict]) -> None:
    salvar_json_seguro(ARQUIVO_LEMBRETES, lembretes[-300:])


def adicionar_lembrete(texto: str, quando: str = "") -> dict:
    texto = _limpar(texto)
    quando = _limpar(quando)
    if not texto:
        return {"ok": False, "error": "texto_vazio"}
    lembretes = _carregar_lembretes()
    item = {
        "id": f"lem_{int(datetime.now().timestamp()*1000)}",
        "texto": texto,
        "quando": quando,
        "criado_em": _agora(),
        "feito": False,
    }
    lembretes.append(item)
    _salvar_lembretes(lembretes)
    return {"ok": True, "item": item}


def listar_lembretes() -> list[dict]:
    return _carregar_lembretes()


_OPERADORES = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
    ast.FloorDiv: lambda a, b: a // b,
}

_FUNCOES = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
}

_CONSTS = {
    "pi": math.pi,
    "e": math.e,
}


def _eval_ast(node):
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("constante inválida")
    if isinstance(node, ast.BinOp):
        op = _OPERADORES.get(type(node.op))
        if op is None:
            raise ValueError("operador não permitido")
        return op(_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -_eval_ast(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +_eval_ast(node.operand)
        raise ValueError("unário não permitido")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("função inválida")
        nome = node.func.id
        fn = _FUNCOES.get(nome)
        if fn is None:
            raise ValueError("função não permitida")
        args = [_eval_ast(a) for a in node.args]
        return fn(*args)
    if isinstance(node, ast.Name):
        if node.id in _CONSTS:
            return _CONSTS[node.id]
        raise ValueError("nome inválido")
    raise ValueError("expressão não suportada")


def calcular_expressao(expr: str) -> dict:
    expr = _limpar(expr)
    expr = expr.replace("^", "**")
    if not expr:
        return {"ok": False, "error": "expressao_vazia"}
    try:
        tree = ast.parse(expr, mode="eval")
        valor = _eval_ast(tree)
        return {"ok": True, "resultado": float(valor)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

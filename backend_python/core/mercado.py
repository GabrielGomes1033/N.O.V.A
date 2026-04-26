from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import re
import unicodedata

import requests

from core.formatador import (
    formatar_cotacao_ativo,
    formatar_cotacoes_basicas,
    formatar_resumo_mercado,
)
from core.noticias import buscar_noticias_categoria

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dependência opcional
    load_dotenv = None

try:
    import yfinance as yf
except Exception:  # pragma: no cover - dependência opcional
    yf = None


TIMEOUT_PADRAO = 6

ATIVOS_SUPORTADOS = {
    "dolar": {
        "name": "Dólar",
        "symbol": "USDBRL=X",
        "currency": "BRL",
        "kind": "fx",
        "alpha_from": "USD",
        "alpha_to": "BRL",
        "aliases": ["dolar", "dólar", "usd", "usdbrl", "usd/brl"],
    },
    "euro": {
        "name": "Euro",
        "symbol": "EURBRL=X",
        "currency": "BRL",
        "kind": "fx",
        "alpha_from": "EUR",
        "alpha_to": "BRL",
        "aliases": ["euro", "eur", "eurbrl", "eur/brl"],
    },
    "bitcoin": {
        "name": "Bitcoin",
        "symbol": "BTC-USD",
        "currency": "USD",
        "kind": "crypto",
        "aliases": ["bitcoin", "btc", "btcusd", "btc/usd"],
    },
    "ethereum": {
        "name": "Ethereum",
        "symbol": "ETH-USD",
        "currency": "USD",
        "kind": "crypto",
        "aliases": ["ethereum", "eth", "ethusd", "eth/usd"],
    },
    "petrobras": {
        "name": "Petrobras",
        "symbol": "PETR4.SA",
        "currency": "BRL",
        "kind": "equity",
        "aliases": ["petrobras", "petr4", "petr3"],
    },
    "vale": {
        "name": "Vale",
        "symbol": "VALE3.SA",
        "currency": "BRL",
        "kind": "equity",
        "aliases": ["vale", "vale3"],
    },
    "itau": {
        "name": "Itaú",
        "symbol": "ITUB4.SA",
        "currency": "BRL",
        "kind": "equity",
        "aliases": ["itau", "itaú", "itub4"],
    },
    "ibovespa": {
        "name": "Ibovespa",
        "symbol": "^BVSP",
        "currency": "BRL",
        "kind": "index",
        "aliases": ["ibovespa", "ibov", "bovespa"],
    },
}


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


def _normalizar(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", base).strip()


def _as_float(valor) -> float | None:
    try:
        if valor is None or valor == "":
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def _detectar_ativo(texto: str) -> str | None:
    normalizado = _normalizar(texto)
    for chave, meta in ATIVOS_SUPORTADOS.items():
        for alias in meta.get("aliases", []):
            if alias in normalizado:
                return chave
    return None


def _cotacao_via_yfinance(chave: str) -> dict | None:
    if yf is None:
        return None
    meta = ATIVOS_SUPORTADOS[chave]
    try:
        ticker = yf.Ticker(meta["symbol"])
        historico = ticker.history(period="5d", interval="1d", auto_adjust=False)
    except Exception:
        return None

    if historico is None or getattr(historico, "empty", True):
        return None

    try:
        closes = historico["Close"].dropna()
        if getattr(closes, "empty", True):
            return None
        price = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) > 1 else None
        day_high = None
        day_low = None
        highs = historico["High"].dropna()
        lows = historico["Low"].dropna()
        if not getattr(highs, "empty", True):
            day_high = float(highs.iloc[-1])
        if not getattr(lows, "empty", True):
            day_low = float(lows.iloc[-1])
    except Exception:
        return None

    change_pct = None
    if prev not in (None, 0):
        change_pct = ((price - prev) / prev) * 100.0

    return {
        "ok": True,
        "name": meta["name"],
        "symbol": meta["symbol"],
        "currency": meta["currency"],
        "price": price,
        "previous_close": prev,
        "change_pct": change_pct,
        "day_high": day_high,
        "day_low": day_low,
        "updated_at": _agora(),
        "sources": ["Yahoo Finance via yfinance"],
    }


def _cotacao_via_alpha_vantage(chave: str) -> dict | None:
    _carregar_env()
    meta = ATIVOS_SUPORTADOS[chave]
    api_key = (os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key or meta.get("kind") != "fx":
        return None
    try:
        resposta = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": meta["alpha_from"],
                "to_currency": meta["alpha_to"],
                "apikey": api_key,
            },
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        resposta.raise_for_status()
        data = resposta.json() if resposta.text else {}
        rate = data.get("Realtime Currency Exchange Rate", {}) if isinstance(data, dict) else {}
        price = _as_float(rate.get("5. Exchange Rate"))
        if price is None:
            return None
        return {
            "ok": True,
            "name": meta["name"],
            "symbol": meta["symbol"],
            "currency": meta["currency"],
            "price": price,
            "updated_at": _agora(),
            "sources": ["Alpha Vantage"],
        }
    except Exception:
        return None


def _cotacao_fx_fallback(chave: str) -> dict | None:
    meta = ATIVOS_SUPORTADOS[chave]
    try:
        resposta = requests.get(
            f"https://api.frankfurter.app/latest?from={meta['alpha_from']}&to={meta['alpha_to']}",
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        resposta.raise_for_status()
        data = resposta.json() if resposta.text else {}
        price = _as_float((data.get("rates") or {}).get(meta["alpha_to"]))
        if price is None:
            return None
        return {
            "ok": True,
            "name": meta["name"],
            "symbol": meta["symbol"],
            "currency": meta["currency"],
            "price": price,
            "updated_at": _agora(),
            "sources": ["Frankfurter"],
        }
    except Exception:
        return None


def _cotacao_crypto_fallback(chave: str) -> dict | None:
    meta = ATIVOS_SUPORTADOS[chave]
    cripto_id = "bitcoin" if chave == "bitcoin" else "ethereum"
    try:
        resposta = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": cripto_id, "vs_currencies": "usd"},
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        resposta.raise_for_status()
        data = resposta.json() if resposta.text else {}
        price = _as_float((data.get(cripto_id) or {}).get("usd"))
        if price is None:
            return None
        return {
            "ok": True,
            "name": meta["name"],
            "symbol": meta["symbol"],
            "currency": meta["currency"],
            "price": price,
            "updated_at": _agora(),
            "sources": ["CoinGecko"],
        }
    except Exception:
        return None


def _cotacao_via_finnhub(chave: str) -> dict | None:
    _carregar_env()
    meta = ATIVOS_SUPORTADOS[chave]
    api_key = (os.getenv("FINNHUB_API_KEY") or "").strip()
    if not api_key or meta.get("kind") not in {"equity", "index"}:
        return None

    try:
        resposta = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": meta["symbol"], "token": api_key},
            timeout=TIMEOUT_PADRAO,
            headers={"User-Agent": "NOVA-Assistente/1.0"},
        )
        resposta.raise_for_status()
        data = resposta.json() if resposta.text else {}
        price = _as_float(data.get("c")) if isinstance(data, dict) else None
        if price is None:
            return None
        return {
            "ok": True,
            "name": meta["name"],
            "symbol": meta["symbol"],
            "currency": meta["currency"],
            "price": price,
            "previous_close": _as_float(data.get("pc")),
            "change_pct": _as_float(data.get("dp")),
            "day_high": _as_float(data.get("h")),
            "day_low": _as_float(data.get("l")),
            "updated_at": _agora(),
            "sources": ["Finnhub"],
        }
    except Exception:
        return None


def consultar_ativo_financeiro(chave: str) -> dict | None:
    chave = _normalizar(chave).replace(" ", "_")
    if chave not in ATIVOS_SUPORTADOS:
        return None

    via_yahoo = _cotacao_via_yfinance(chave)
    if via_yahoo:
        return via_yahoo

    meta = ATIVOS_SUPORTADOS[chave]
    if meta.get("kind") == "fx":
        return _cotacao_via_alpha_vantage(chave) or _cotacao_fx_fallback(chave)
    if meta.get("kind") == "crypto":
        return _cotacao_crypto_fallback(chave)
    if meta.get("kind") in {"equity", "index"}:
        return _cotacao_via_finnhub(chave)
    return None


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

    mapa = {
        "dolar": "dolar_brl",
        "euro": "euro_brl",
        "bitcoin": "bitcoin_usd",
        "ethereum": "ethereum_usd",
    }
    for chave, campo in mapa.items():
        cotacao = consultar_ativo_financeiro(chave)
        if not cotacao:
            continue
        resultado[campo] = cotacao.get("price")
        for fonte in cotacao.get("sources", []) or []:
            if fonte not in resultado["source"]:
                resultado["source"].append(fonte)

    if not any(
        [
            resultado["dolar_brl"],
            resultado["euro_brl"],
            resultado["bitcoin_usd"],
            resultado["ethereum_usd"],
        ]
    ):
        return {"ok": False, "error": "sem_dados"}

    return resultado


def formatar_cotacoes_humanas(cotacoes: dict) -> str:
    return formatar_cotacoes_basicas(cotacoes)


def gerar_resumo_mercado() -> dict:
    ativos = []
    fontes = []
    for chave in ["dolar", "euro", "bitcoin", "petrobras", "vale", "itau", "ibovespa"]:
        cotacao = consultar_ativo_financeiro(chave)
        if not cotacao:
            continue
        ativos.append(cotacao)
        for fonte in cotacao.get("sources", []) or []:
            if fonte not in fontes:
                fontes.append(fonte)

    noticias = buscar_noticias_categoria("mercado_financeiro", limit=3)
    for fonte in noticias.get("sources", []) if isinstance(noticias, dict) else []:
        if fonte not in fontes:
            fontes.append(fonte)

    return {
        "ok": bool(ativos),
        "assets": ativos,
        "headlines": noticias.get("items", []) if isinstance(noticias, dict) else [],
        "sources": fontes,
        "updated_at": _agora(),
    }


def responder_consulta_mercado(texto: str) -> str | None:
    normalizado = _normalizar(texto)

    if "resumo do mercado financeiro" in normalizado or (
        "mercado financeiro" in normalizado and "noticia" not in normalizado
    ):
        return formatar_resumo_mercado(gerar_resumo_mercado())

    ativo = _detectar_ativo(normalizado)
    if ativo and any(
        termo in normalizado
        for termo in ("cotacao", "cotacao da", "cotacao do", "qual o", "qual a", "hoje")
    ):
        cotacao = consultar_ativo_financeiro(ativo)
        if cotacao:
            return formatar_cotacao_ativo(cotacao)
        return f"Não consegui atualizar a cotação de {ATIVOS_SUPORTADOS[ativo]['name']} agora."

    if any(
        termo in normalizado
        for termo in ("cotacao", "dolar", "euro", "bitcoin", "ethereum", "mercado financeiro")
    ):
        return formatar_cotacoes_humanas(cotacoes_financeiras())

    return None

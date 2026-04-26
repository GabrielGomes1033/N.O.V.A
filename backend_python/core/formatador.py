from __future__ import annotations

from datetime import datetime
import re


def _limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def _resumir(texto: str, limite: int = 140) -> str:
    base = _limpar(texto)
    if len(base) <= limite:
        return base
    corte = base[: max(40, limite)].rsplit(" ", 1)[0].strip()
    return (corte or base[:limite]).rstrip(" ,.;:-") + "..."


def _fmt_numero(valor: float, casas: int = 2) -> str:
    texto = f"{float(valor):,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda(valor: float | None, moeda: str) -> str:
    if valor is None:
        return "indisponível"
    if moeda.upper() == "BRL":
        return f"R$ {_fmt_numero(valor, 4 if valor < 10 else 2)}"
    if moeda.upper() == "USD":
        return f"US$ {_fmt_numero(valor, 2)}"
    if moeda.upper() == "EUR":
        return f"EUR {_fmt_numero(valor, 2)}"
    return f"{moeda.upper()} {_fmt_numero(valor, 2)}"


def formatar_variacao_percentual(valor: float | None) -> str:
    if valor is None:
        return ""
    sinal = "+" if valor >= 0 else ""
    return f"{sinal}{_fmt_numero(valor, 2)}%"


def formatar_noticias(resultado: dict) -> str:
    titulo = _limpar(resultado.get("title", "Notícias"))
    itens = resultado.get("items", [])
    if not isinstance(itens, list) or not itens:
        return f"{titulo}: não consegui atualizar as manchetes agora."

    linhas = [f"{titulo}:"]
    for idx, item in enumerate(itens[:5], start=1):
        if not isinstance(item, dict):
            continue
        manchete = _limpar(item.get("title", ""))
        resumo = _resumir(item.get("summary") or item.get("description") or "", limite=120)
        fonte = _limpar(item.get("source_name") or item.get("source") or "")
        linha = f"{idx}. {manchete}" if manchete else f"{idx}. Atualização sem título"
        if resumo:
            linha += f" — {resumo}"
        if fonte:
            linha += f" ({fonte})"
        linhas.append(linha)

    atualizado_em = _limpar(resultado.get("updated_at", ""))
    if atualizado_em:
        try:
            stamp = datetime.fromisoformat(atualizado_em.replace("Z", "+00:00"))
            linhas.append(f"Atualizado em: {stamp.strftime('%d/%m/%Y %H:%M')}")
        except ValueError:
            linhas.append(f"Atualizado em: {atualizado_em}")

    fontes = resultado.get("sources", [])
    if isinstance(fontes, list) and fontes:
        linhas.append("Fontes: " + ", ".join(_limpar(f) for f in fontes if _limpar(f)))
    return "\n".join(linhas)


def formatar_cotacao_ativo(cotacao: dict) -> str:
    nome = _limpar(cotacao.get("name", "Ativo"))
    simbolo = _limpar(cotacao.get("symbol", ""))
    moeda = _limpar(cotacao.get("currency", "BRL")) or "BRL"
    preco = formatar_moeda(cotacao.get("price"), moeda)
    variacao = formatar_variacao_percentual(cotacao.get("change_pct"))
    maxima = formatar_moeda(cotacao.get("day_high"), moeda) if cotacao.get("day_high") else ""
    minima = formatar_moeda(cotacao.get("day_low"), moeda) if cotacao.get("day_low") else ""

    base = nome
    if simbolo:
        base += f" ({simbolo})"
    base += f": {preco}"
    if variacao:
        base += f" | variação {variacao}"
    if maxima and minima:
        base += f" | faixa do dia {minima} a {maxima}"

    fontes = cotacao.get("sources", [])
    if isinstance(fontes, list) and fontes:
        base += "\nFontes: " + ", ".join(_limpar(f) for f in fontes if _limpar(f))
    return base


def formatar_resumo_mercado(resumo: dict) -> str:
    ativos = resumo.get("assets", [])
    if not isinstance(ativos, list) or not ativos:
        return "Não consegui atualizar o resumo do mercado financeiro agora."

    linhas = ["Resumo do mercado financeiro:"]
    for item in ativos[:6]:
        if not isinstance(item, dict):
            continue
        nome = _limpar(item.get("name", item.get("symbol", "Ativo")))
        moeda = _limpar(item.get("currency", "BRL")) or "BRL"
        preco = formatar_moeda(item.get("price"), moeda)
        variacao = formatar_variacao_percentual(item.get("change_pct"))
        linha = f"- {nome}: {preco}"
        if variacao:
            linha += f" ({variacao})"
        linhas.append(linha)

    headlines = resumo.get("headlines", [])
    if isinstance(headlines, list) and headlines:
        linhas.append("")
        linhas.append("Destaques do mercado:")
        for idx, item in enumerate(headlines[:3], start=1):
            if not isinstance(item, dict):
                continue
            manchete = _limpar(item.get("title", ""))
            fonte = _limpar(item.get("source_name") or item.get("source") or "")
            linha = f"{idx}. {manchete}" if manchete else f"{idx}. Atualização financeira"
            if fonte:
                linha += f" ({fonte})"
            linhas.append(linha)

    fontes = resumo.get("sources", [])
    if isinstance(fontes, list) and fontes:
        linhas.append("")
        linhas.append("Fontes: " + ", ".join(_limpar(f) for f in fontes if _limpar(f)))
    return "\n".join(linhas)


def formatar_cotacoes_basicas(cotacoes: dict) -> str:
    if cotacoes.get("ok") is not True:
        return "Não consegui atualizar cotações agora."

    partes = []
    if cotacoes.get("dolar_brl") is not None:
        partes.append(f"Dólar: {formatar_moeda(cotacoes['dolar_brl'], 'BRL')}")
    if cotacoes.get("euro_brl") is not None:
        partes.append(f"Euro: {formatar_moeda(cotacoes['euro_brl'], 'BRL')}")
    if cotacoes.get("bitcoin_usd") is not None:
        partes.append(f"Bitcoin: {formatar_moeda(cotacoes['bitcoin_usd'], 'USD')}")
    if cotacoes.get("ethereum_usd") is not None:
        partes.append(f"Ethereum: {formatar_moeda(cotacoes['ethereum_usd'], 'USD')}")

    base = " | ".join(partes) if partes else "Sem cotações disponíveis."
    fontes = cotacoes.get("source", [])
    if isinstance(fontes, list) and fontes:
        base += "\nFontes: " + ", ".join(_limpar(f) for f in fontes if _limpar(f))
    return base

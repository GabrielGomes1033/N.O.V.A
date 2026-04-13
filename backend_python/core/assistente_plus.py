from __future__ import annotations

from datetime import datetime
from pathlib import Path
import ast
import math
import re
from urllib.parse import quote_plus

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


def pesquisar_na_internet(consulta: str) -> dict:
    consulta = _limpar(consulta)
    if not consulta:
        return {"ok": False, "resumo": "Consulta vazia."}

    blocos: list[str] = []
    fontes: list[str] = []

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
            blocos.append(prefixo + abstract)
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
                blocos.append("; ".join(itens))
                fontes.append("DuckDuckGo")
    except Exception:
        pass

    # 2) Wikipedia
    try:
        wiki = gerar_pesquisa_wikipedia(consulta)
        if wiki:
            blocos.append(f"{wiki.get('titulo')}: {wiki.get('resumo')}")
            fontes.append(wiki.get("fonte", "Wikipedia"))
    except Exception:
        pass

    # 3) StackOverflow quando assunto técnico
    consulta_l = consulta.lower()
    if any(t in consulta_l for t in ["api", "python", "java", "javascript", "flutter", "agente", "ia", "llm", "erro", "bug"]):
        try:
            so_url = (
                "https://api.stackexchange.com/2.3/search/advanced"
                f"?order=desc&sort=relevance&site=stackoverflow&accepted=True&answers=1&title={quote_plus(consulta)}"
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
                blocos.append("No Stack Overflow, os tópicos mais próximos foram: " + "; ".join(titulos))
                fontes.append("StackOverflow")
        except Exception:
            pass

    if not blocos:
        return {
            "ok": False,
            "resumo": "Não consegui coletar fontes agora. Se quiser, me ensine essa resposta com /ensinar pergunta = resposta.",
            "fontes": [],
        }

    resumo = " ".join(blocos)
    resumo = re.sub(r"\s+", " ", resumo).strip()
    if len(resumo) > 1200:
        resumo = resumo[:1200].rsplit(" ", 1)[0] + "..."

    return {
        "ok": True,
        "resumo": resumo,
        "fontes": sorted(set(f for f in fontes if f)),
    }


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

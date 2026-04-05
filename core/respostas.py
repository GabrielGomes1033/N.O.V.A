from datetime import datetime
from pathlib import Path
import random
import re
import unicodedata

from core.personalidade import estilizar


ARQUIVO_MODOS = Path(__file__).with_name("modos.txt")

INTENCOES = {
    "saudacao": [
        "oi",
        "ola",
        "e ai",
        "bom dia",
        "boa tarde",
        "boa noite",
        "salve",
        "opa",
        "fala",
        "hey",
    ],
    "pergunta_nome": [
        "seu nome",
        "como te chama",
        "quem e voce",
        "qual seu nome",
        "como voce se chama",
        "quem ta falando",
    ],
    "como_esta": [
        "como voce esta",
        "como ce ta",
        "como ta",
        "tudo bem",
        "ta bem",
        "beleza",
        "de boa",
    ],
    "agradecimento": [
        "obrigado",
        "obrigada",
        "valeu",
        "agradeco",
        "grato",
        "grata",
        "tmj",
    ],
    "ajuda": [
        "ajuda",
        "me ajuda",
        "pode me ajudar",
        "voce pode me ajudar",
        "como funciona",
        "o que voce faz",
        "em que voce ajuda",
    ],
    "hora": [
        "hora",
        "que horas",
        "me diga a hora",
        "horario",
        "qual a hora",
    ],
    "data": [
        "data",
        "que dia",
        "qual e a data",
        "dia de hoje",
        "data de hoje",
        "que dia e hoje",
    ],
    "idade": [
        "quantos anos voce tem",
        "qual sua idade",
        "idade",
        "quando voce nasceu",
    ],
    "criador": [
        "quem te criou",
        "quem fez voce",
        "quem e seu criador",
        "quem te programou",
    ],
    "elogio": [
        "voce e inteligente",
        "voce e legal",
        "voce e incrivel",
        "mandou bem",
        "arrasou",
        "adorei",
        "gostei de voce",
    ],
    "despedida": [
        "tchau",
        "ate logo",
        "falou",
        "fui",
        "ate mais",
        "tenha um bom dia",
        "boa noite vou indo",
    ],
    "sair": ["sair", "encerrar", "fechar"],
}

INTENCAO_PADRAO = "desconhecido"


def normalizar_texto(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    texto = re.sub(r"[^\w\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def carregar_respostas(arquivo=ARQUIVO_MODOS, modo="normal"):
    caminho = Path(arquivo)
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo de respostas não encontrado: {caminho}")

    respostas = {}
    atual_modo = None

    with caminho.open("r", encoding="utf-8") as arquivo_txt:
        for linha in arquivo_txt:
            linha = linha.strip()
            if not linha:
                continue

            if linha.startswith("# Modo"):
                atual_modo = linha.replace("# Modo", "", 1).strip().lower()
                continue

            if atual_modo != modo.lower() or "=" not in linha:
                continue

            chave, resp = linha.split("=", 1)
            respostas[chave.strip()] = [item.strip() for item in resp.split("|") if item.strip()]

    return respostas


def detectar_intencao(msg):
    texto = normalizar_texto(msg)

    for chave, palavras in INTENCOES.items():
        for palavra in palavras:
            termo = normalizar_texto(palavra)
            padrao = r"\b" + re.escape(termo) + r"\b"
            if re.search(padrao, texto):
                return chave

    if texto.endswith(" oi") or texto.startswith("oi "):
        return "saudacao"

    return INTENCAO_PADRAO


def responder(msg, respostas_txt=ARQUIVO_MODOS, modo="normal"):
    respostas = carregar_respostas(respostas_txt, modo=modo)
    intencao = detectar_intencao(msg)
    opcoes = respostas.get(intencao) or respostas.get(
        INTENCAO_PADRAO,
        ["Hmm... não entendi."],
    )

    resposta = random.choice(opcoes)
    if resposta == "exit":
        return "exit"

    agora = datetime.now()
    resposta = resposta.replace("{hora}", agora.strftime("%H:%M"))
    resposta = resposta.replace("{data}", agora.strftime("%d/%m/%Y"))
    return estilizar(resposta)

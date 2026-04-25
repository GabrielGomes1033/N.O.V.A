# Controla o "tom de voz" da NOVA.
# Cada modo adiciona prefixos e sufixos diferentes às respostas base.
import random

# Catálogo de estilos disponíveis no aplicativo.
modos = {
    "normal": {"prefixos": ["", "", ""], "sufixos": ["", "", ""]},
    "engracado": {
        "prefixos": ["😂 Olha só...", "Hmm, interessante!", "KKKK vamos lá:"],
        "sufixos": [" 😄", " 🤣", " (essa foi boa)"],
    },
    "formal": {
        "prefixos": ["Compreendo.", "De acordo com sua solicitação:", "Certamente."],
        "sufixos": [" Estou à disposição.", " Caso precise de mais ajuda, informe.", ""],
    },
    "sarcastico": {
        "prefixos": ["Ah claro...", "Nossa, que surpresa...", "Uau, ninguém esperava isso..."],
        "sufixos": [" 🙄", " 😏", " (óbvio)"],
    },
    "inspirador": {
        "prefixos": ["🌟 Lembre-se:", "Aqui vai uma reflexão:", "Para você pensar:"],
        "sufixos": [" ✨", " 💡", " 🌈"],
    },
    "tecnologico": {
        "prefixos": ["🤖 Processando...", "Analisando dados:", "Sinal recebido:"],
        "sufixos": [" ⚡", " 🛰️", " ✅"],
    },
}

# Guarda o modo selecionado no momento.
modo_atual = "normal"


def set_modo(modo):
    # Troca o modo global se o nome informado existir no catálogo.
    global modo_atual
    if modo in modos:
        modo_atual = modo
        return f"Modo alterado para '{modo.upper()}'"
    return "Modo não encontrado."


def estilizar(resposta):
    # Aplica pequenas variações para que a mesma resposta pareça mais viva.
    estilo = modos.get(modo_atual, modos["normal"])
    prefixo = random.choice(estilo["prefixos"]).strip()
    sufixo = random.choice(estilo["sufixos"]).strip()

    if prefixo:
        resposta = f"{prefixo} {resposta}"
    if sufixo:
        resposta = f"{resposta} {sufixo}"

    return resposta

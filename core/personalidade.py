import random

modos = {
    "normal": {
        "prefixos": ["", "", ""],
        "sufixos": ["", "", ""]
    },
    "engracado": {
        "prefixos": ["😂 Olha só...", "Hmm, interessante!", "KKKK vamos lá:"],
        "sufixos": [" 😄", " 🤣", " (essa foi boa)"]
    },
    "formal": {
        "prefixos": ["Compreendo.", "De acordo com sua solicitação:", "Certamente."],
        "sufixos": [" Estou à disposição.", " Caso precise de mais ajuda, informe.", ""]
    },
    "sarcastico": {
        "prefixos": ["Ah claro...", "Nossa, que surpresa...", "Uau, ninguém esperava isso..."],
        "sufixos": [" 🙄", " 😏", " (óbvio)"]
    },
    "inspirador": {
        "prefixos": ["🌟 Lembre-se:", "Aqui vai uma reflexão:", "Para você pensar:"],
        "sufixos": [" ✨", " 💡", " 🌈"]
    },
    "tecnologico": {
        "prefixos": ["🤖 Processando...", "Analisando dados:", "Sinal recebido:"],
        "sufixos": [" ⚡", " 🛰️", " ✅"]
    }
}

modo_atual = "normal"

def set_modo(modo):
    global modo_atual
    if modo in modos:
        modo_atual = modo
        return f"Modo alterado para '{modo.upper()}'"
    return "Modo não encontrado."

def estilizar(resposta):
    estilo = modos.get(modo_atual, modos["normal"])
    prefixo = random.choice(estilo["prefixos"]).strip()
    sufixo = random.choice(estilo["sufixos"]).strip()

    if prefixo:
        resposta = f"{prefixo} {resposta}"
    if sufixo:
        resposta = f"{resposta} {sufixo}"

    return resposta
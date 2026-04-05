from datetime import datetime
import random

# 🎭 Personalidade do bot
def estilizar(respostas):
    return random.choice(respostas)

def responder(msg):
    msg = msg.lower()

    if "oi" in msg or "olá" in msg:
        return estilizar([
            "E aí! 😎",
            "Olá, humano 👋",
            "Fala comigo 😏",
            "Oi! Tava te esperando 😄"
        ])

    elif "seu nome" in msg:
        return estilizar([
            "Sou seu assistente 😎",
            "Pode me chamar de Jarvis versão brasileira 🇧🇷",
            "Ainda não tenho nome… quer me dar um? 👀"
        ])

    elif "hora" in msg:
        agora = datetime.now().strftime("%H:%M")
        return estilizar([
            f"Agora são {agora} ⏰",
            f"Relógio na mão: {agora}",
            f"São exatamente {agora}, sem atraso 😌"
        ])

    elif "data" in msg:
        hoje = datetime.now().strftime("%d/%m/%Y")
        return estilizar([
            f"Hoje é {hoje} 📅",
            f"A data de hoje: {hoje}",
            f"Estamos em {hoje}, não esquece 😄"
        ])

    elif "sair" in msg:
        return "exit"

    else:
        return estilizar([
            "Hmm... não entendi 🤔",
            "Pode repetir? Meu cérebro bugou 😅",
            "Não captei isso não 😬",
            "Explica melhor aí 👀"
        ])
# gerar_modos.py
import random
from datetime import datetime

# Modos de conversa
modos = ["normal", "engracado", "tecnologico"]

# Intenções com frases base
intencoes = {
    "saudacao": [
        "Oi", "Olá", "E aí", "Salve", "Oiê", "Fala", "Hey", "Bem-vindo"
    ],
    "pergunta_nome": [
        "Sou a NOVA", "Pode me chamar de NOVA", "Eu sou a NOVA", "Aqui é a NOVA, sua assistente"
    ],
    "hora": [
        "Agora são {hora}", "Olha no relógio, são {hora}", "Hora atual: {hora}", "Neste momento temos {hora}"
    ],
    "data": [
        "Hoje é {data}", "A data de hoje é {data}", "Estamos em {data}", "No calendário, é {data}"
    ],
    "desconhecido": [
        "Hmm... não entendi", "Pode repetir?", "Não captei isso", "Hã? 😵", "Repete, por favor", "Confesso que não entendi"
    ]
}

# Emojis para dar personalidade
emojis = ["😄","😎","🤖","🌟","😂","😅","🤪","👋","😉","🤔"]

# Gírias e pequenas variações para deixar mais humano
variacoes = ["", " hein?", " 😜", " haha", " 😏", " 🤩", " 😉"]

# Número de respostas por intenção
respostas_por_intencao = 2000  # 2000 x 6 intenções x 3 modos > 10.000 respostas

# Arquivo de saída
arquivo_saida = "core/modos.txt"

with open(arquivo_saida, "w", encoding="utf-8") as f:
    for modo in modos:
        f.write(f"# Modo {modo}\n")
        for chave, frases in intencoes.items():
            respostas = []
            for _ in range(respostas_por_intencao):
                frase = random.choice(frases)
                emoji = random.choice(emojis)
                variacao = random.choice(variacoes)
                respostas.append(f"{frase} {emoji}{variacao}")
            # Junta todas as respostas separadas por '|'
            f.write(f"{chave}=" + "|".join(respostas) + "\n")
        f.write("\n")

print(f"✅ Arquivo '{arquivo_saida}' gerado com sucesso! Mais de 10.000 respostas.")
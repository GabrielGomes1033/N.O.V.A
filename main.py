from core.logica import responder

def main():
    print("🤖 Chatbot iniciado! Digite 'sair' para encerrar.\n")

    while True:
        user = input("Você: ")
        resposta = responder(user)

        if resposta == "exit":
            print("Bot: Até mais! 👋")
            break

        print("Bot:", resposta)

if __name__ == "__main__":
    main()
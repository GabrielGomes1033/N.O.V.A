from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout

from core import personalidade
from core.personalidade import modos, set_modo
from core.respostas import responder


class ChatRoot(BoxLayout):
    modo_label = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.atualizar_modo_label()
        Clock.schedule_once(lambda *_: self.mensagem_inicial(), 0)

    def mensagem_inicial(self):
        modos_disponiveis = ", ".join(sorted(modos))
        self.adicionar_mensagem(
            "NOVA",
            (
                "Oi! Eu sou a NOVA. Digite sua mensagem abaixo.\n"
                f"Use /modo <nome> para trocar o estilo. Modos: {modos_disponiveis}."
            ),
        )

    def atualizar_modo_label(self):
        self.modo_label = f"Modo atual: {personalidade.modo_atual.upper()}"

    def enviar_mensagem(self):
        entrada = self.ids.entrada
        texto = entrada.text.strip()
        if not texto:
            return

        entrada.text = ""
        self.adicionar_mensagem("Você", texto)

        if texto.lower().startswith("/modo"):
            self.processar_comando_modo(texto)
            return

        resposta = responder(texto)
        if resposta == "exit":
            resposta = "Se quiser encerrar, é só fechar o aplicativo. Eu continuo por aqui."
        self.adicionar_mensagem("NOVA", resposta)

    def processar_comando_modo(self, texto):
        partes = texto.split(maxsplit=1)
        if len(partes) < 2:
            disponiveis = ", ".join(sorted(modos))
            self.adicionar_mensagem(
                "NOVA",
                f"Use /modo <nome>. Modos disponíveis: {disponiveis}.",
            )
            return

        novo_modo = partes[1].strip().lower()
        resposta = set_modo(novo_modo)
        self.atualizar_modo_label()
        self.adicionar_mensagem("NOVA", resposta)

    def adicionar_mensagem(self, autor, texto):
        historico = self.ids.historico
        trecho = f"[b]{autor}:[/b] {texto}"
        historico.text = f"{historico.text}\n\n{trecho}".strip()
        Clock.schedule_once(lambda *_: self.rolar_para_baixo(), 0)

    def rolar_para_baixo(self):
        self.ids.scroll.scroll_y = 0


class ChatBotApp(App):
    def build(self):
        self.title = "ChatBot Assistente"
        return Builder.load_file("assistente.kv")


if __name__ == "__main__":
    ChatBotApp().run()

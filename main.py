# Arquivo principal do aplicativo Kivy.
# Aqui ficam a janela, o fluxo da interface e os comandos digitados pelo usuário.
from datetime import datetime
import os
from pathlib import Path
from urllib.parse import quote_plus
import webbrowser

# Mantém cache e logs do Kivy dentro do projeto para evitar erros com ~/.kivy.
PASTA_KIVY = Path(__file__).resolve().parent / ".kivy"
PASTA_KIVY.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("KIVY_HOME", str(PASTA_KIVY))

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout

from core import personalidade
from core.personalidade import modos, set_modo
from core.pesquisa import gerar_pesquisa_wikipedia
from core.respostas import detectar_intencao, extrair_nome_usuario, responder, salvar_aprendizado
from core.voz import definir_voz_ativa, descricao_voz, falar, voz_ativa, voz_disponivel


class ChatRoot(BoxLayout):
    # Propriedades reativas usadas pela interface .kv.
    modo_label = StringProperty("")
    assistente_status = StringProperty("NOVA online e pronta para conversar")
    painel_status = StringProperty("")
    monitor_texto = StringProperty("")
    monitor_resumo = StringProperty("MONITOR ONLINE")
    voz_label = StringProperty("")
    comandos_texto = StringProperty(
        "/modo normal  |  /modo formal  |  /modo tecnologico\n"
        "/ensinar pergunta = resposta\n"
        "/aprender pergunta = resposta\n"
        "/google assunto  |  /pesquisar assunto\n"
        "/voz on  |  /voz off\n"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.contexto_conversa = {
            "ultima_intencao": None,
            "ultima_mensagem_usuario": "",
            "ultima_resposta_assistente": "",
            "nome_usuario": "",
        }
        # Inicializa os textos da interface e agenda atualizações visuais.
        self.atualizar_modo_label()
        self.atualizar_painel_status()
        self.atualizar_voz_label()
        self.registrar_evento("Sistema inicializado")
        Clock.schedule_interval(self.atualizar_relogio, 1)
        Clock.schedule_once(lambda *_: self.mensagem_inicial(), 0)

    def mensagem_inicial(self):
        # Exibe a primeira mensagem da NOVA assim que a tela termina de carregar.
        modos_disponiveis = ", ".join(sorted(modos))
        self.adicionar_mensagem(
            "NOVA",
            (
                "Oi! Eu sou a NOVA. Digite sua mensagem abaixo.\n"
                f"Use /modo <nome> para trocar o estilo. Modos: {modos_disponiveis}.\n"
                "Se quiser me ensinar algo novo, use /ensinar pergunta = resposta.\n"
                "Para pesquisar, use /google assunto ou /pesquisar assunto. Eu busco um resumo na Wikipedia e leio para você.\n"
                "A voz agora roda em um processo separado para manter o app mais estável.\n"
                "Para controlar a voz, use /voz on ou /voz off."
            ),
        )

    def atualizar_modo_label(self):
        # Reflete na tela o modo de personalidade atualmente ativo.
        self.modo_label = f"Modo atual: {personalidade.modo_atual.upper()}"

    def atualizar_voz_label(self):
        # Mostra na interface se a síntese de voz está ativa e disponível.
        if not voz_disponivel():
            self.voz_label = "Voz: desabilitada"
        elif voz_ativa():
            self.voz_label = f"Voz: {descricao_voz()}"
        else:
            self.voz_label = "Voz: desligada"

    def atualizar_painel_status(self):
        # Monta a barra de status no estilo "HUD", mostrando estado, modo e hora.
        self.painel_status = (
            f"SISTEMA ONLINE  |  MODO {personalidade.modo_atual.upper()}  |  "
            f"{datetime.now().strftime('%H:%M:%S')}"
        )

    def atualizar_relogio(self, *_):
        # Mantém o relógio do painel em tempo real.
        self.atualizar_painel_status()

    def registrar_evento(self, evento):
        # Alimenta o painel de monitoramento com os últimos eventos do assistente.
        horario = datetime.now().strftime("%H:%M:%S")
        linha = f"[{horario}] {evento}"
        linhas_atuais = [item for item in self.monitor_texto.split("\n") if item.strip()]
        novas_linhas = [linha, *linhas_atuais][:8]
        self.monitor_texto = "\n".join(novas_linhas)
        self.monitor_resumo = evento.upper()

    def enviar_mensagem(self):
        # Lê o texto digitado, registra no histórico e decide qual fluxo seguir.
        entrada = self.ids.entrada
        texto = entrada.text.strip()
        if not texto:
            return

        entrada.text = ""
        self.adicionar_mensagem("Você", texto)
        self.assistente_status = "NOVA pensando na resposta..."
        self.registrar_evento(f"Entrada recebida: {texto}")
        nome_detectado = extrair_nome_usuario(texto)
        if nome_detectado:
            self.contexto_conversa["nome_usuario"] = nome_detectado
            self.registrar_evento(f"Nome do usuário identificado: {nome_detectado}")

        # Comandos são tratados antes do fluxo normal de conversa.
        if texto.lower().startswith("/modo"):
            self.registrar_evento("Comando identificado: troca de modo")
            self.processar_comando_modo(texto)
            return

        if texto.lower().startswith("/ensinar") or texto.lower().startswith("/aprender"):
            self.registrar_evento("Comando identificado: aprendizado")
            self.processar_comando_ensinar(texto)
            return

        if texto.lower().startswith("/google") or texto.lower().startswith("/pesquisar"):
            self.registrar_evento("Comando identificado: pesquisa web")
            self.processar_comando_google(texto)
            return

        if texto.lower().startswith("/voz"):
            self.registrar_evento("Comando identificado: controle de voz")
            self.processar_comando_voz(texto)
            return

        # Mensagens comuns passam pelo motor de respostas da NOVA.
        intencao = detectar_intencao(texto, contexto=self.contexto_conversa)
        self.registrar_evento(f"Intenção detectada: {intencao}")
        resposta = responder(texto, contexto=self.contexto_conversa)
        if resposta == "exit":
            self.registrar_evento("Ação gerada: sinal de encerramento")
            resposta = "Se quiser encerrar, é só fechar o aplicativo. Eu continuo por aqui."
        else:
            self.registrar_evento("Resposta gerada com sucesso")
        self.contexto_conversa["ultima_intencao"] = intencao
        self.contexto_conversa["ultima_mensagem_usuario"] = texto
        self.contexto_conversa["ultima_resposta_assistente"] = resposta
        self.assistente_status = "NOVA online e conversando com você"
        self.atualizar_painel_status()
        self.adicionar_mensagem("NOVA", resposta)
        if falar(resposta):
            self.atualizar_voz_label()
            self.registrar_evento(f"Síntese de voz executada: {descricao_voz()}")
        elif voz_disponivel() and not voz_ativa():
            self.registrar_evento("Voz disponível, mas desligada")
        else:
            self.registrar_evento("Voz neural indisponível no momento")

    def processar_comando_ensinar(self, texto):
        # Permite ao usuário ensinar respostas novas usando:
        # /ensinar pergunta = resposta
        comando, _, conteudo = texto.partition(" ")
        conteudo = conteudo.strip()

        if "=" not in conteudo:
            self.assistente_status = "NOVA aguardando um ensino válido"
            self.registrar_evento("Falha no aprendizado: formato inválido")
            self.adicionar_mensagem(
                "NOVA",
                "Use /ensinar pergunta = resposta. Exemplo: /ensinar quem é o homem de ferro = Tony Stark.",
            )
            return

        # Separa a pergunta ensinada da resposta que a NOVA deve memorizar.
        pergunta, resposta = [parte.strip() for parte in conteudo.split("=", 1)]
        if not pergunta or not resposta:
            self.assistente_status = "NOVA aguardando um ensino válido"
            self.registrar_evento("Falha no aprendizado: pergunta ou resposta vazia")
            self.adicionar_mensagem(
                "NOVA",
                "Para eu aprender, preciso de uma pergunta e de uma resposta.",
            )
            return

        # Salva o aprendizado em arquivo para que ele continue disponível depois.
        total_respostas = salvar_aprendizado(pergunta, resposta)
        self.assistente_status = "NOVA assimilando novo conhecimento"
        self.atualizar_painel_status()
        self.registrar_evento(f"Conhecimento salvo para: {pergunta}")
        self.adicionar_mensagem(
            "NOVA",
            (
                f"Aprendi isso com sucesso. Quando você perguntar '{pergunta}', "
                f"eu poderei responder '{resposta}'. Total de respostas ensinadas para essa pergunta: {total_respostas}."
            ),
        )

    def processar_comando_google(self, texto):
        # Busca um resumo na Wikipedia e usa o Google apenas como plano de reserva.
        partes = texto.split(maxsplit=1)
        if len(partes) < 2 or not partes[1].strip():
            self.assistente_status = "NOVA aguardando um termo de pesquisa"
            self.registrar_evento("Falha na pesquisa: nenhum termo informado")
            mensagem = "Use /google assunto ou /pesquisar assunto. Exemplo: /google clima em São Paulo."
            self.adicionar_mensagem(
                "NOVA",
                mensagem,
            )
            if falar(mensagem):
                self.registrar_evento("Orientação de pesquisa falada")
            return

        consulta = partes[1].strip()
        url_google = f"https://www.google.com/search?q={quote_plus(consulta)}"
        pesquisa_wikipedia = gerar_pesquisa_wikipedia(consulta)

        self.assistente_status = "NOVA em modo de pesquisa"
        self.atualizar_painel_status()
        self.registrar_evento(f"Pesquisa preparada: {consulta}")

        if pesquisa_wikipedia:
            titulo = pesquisa_wikipedia["titulo"]
            resumo = pesquisa_wikipedia["resumo"]
            fonte = pesquisa_wikipedia["fonte"]
            url_wikipedia = pesquisa_wikipedia["url"]
            navegador_aberto = webbrowser.open(url_wikipedia)
            self.registrar_evento(f"Resumo de pesquisa gerado: {fonte}")

            if navegador_aberto:
                self.registrar_evento("Wikipedia aberta com sucesso")
                mensagem = (
                    f"Encontrei um resumo sobre '{consulta}' na {fonte}.\n\n"
                    f"Título: {titulo}\n"
                    f"Resumo: {resumo}\n\n"
                    f"Link: {url_wikipedia}"
                )
            else:
                self.registrar_evento("Wikipedia não abriu; link exibido no chat")
                mensagem = (
                    f"Encontrei um resumo sobre '{consulta}' na {fonte}.\n\n"
                    f"Título: {titulo}\n"
                    f"Resumo: {resumo}\n\n"
                    f"Não consegui abrir a página automaticamente, mas aqui está o link: {url_wikipedia}"
                )

            mensagem_voz = f"Aqui está o resumo sobre {consulta}. {resumo}"
        else:
            self.registrar_evento("Resumo de pesquisa indisponível")
            navegador_aberto = webbrowser.open(url_google)
            if navegador_aberto:
                self.registrar_evento("Google aberto como reserva")
                mensagem = (
                    f"Não encontrei um resumo confiável na Wikipedia para '{consulta}'.\n\n"
                    f"Deixei a pesquisa no Google pronta para você.\n\nLink: {url_google}"
                )
                mensagem_voz = (
                    f"Não encontrei um resumo na Wikipedia sobre {consulta}. "
                    "Mas deixei a pesquisa no Google pronta para você."
                )
            else:
                self.registrar_evento("Google não abriu; link exibido no chat")
                mensagem = (
                    f"Não encontrei um resumo confiável na Wikipedia para '{consulta}'.\n\n"
                    f"Também não consegui abrir o navegador automaticamente. Aqui está o link da pesquisa: {url_google}"
                )
                mensagem_voz = (
                    f"Não encontrei um resumo na Wikipedia sobre {consulta}. "
                    "O link da pesquisa ficou no chat para você."
                )

        self.adicionar_mensagem("NOVA", mensagem)
        if falar(mensagem_voz):
            self.registrar_evento("Resultado de pesquisa falado")

    def processar_comando_voz(self, texto):
        # Liga ou desliga o retorno de voz da NOVA.
        partes = texto.split(maxsplit=1)
        if len(partes) < 2:
            self.registrar_evento("Falha no comando de voz: parâmetro ausente")
            self.adicionar_mensagem(
                "NOVA",
                f"{self.voz_label}. Use /voz on para ligar ou /voz off para desligar.",
            )
            return

        if not voz_disponivel():
            self.registrar_evento("Falha no comando de voz: engine indisponível")
            self.atualizar_voz_label()
            self.adicionar_mensagem(
                "NOVA",
                "A voz não está disponível neste ambiente no momento.",
            )
            return

        valor = partes[1].strip().lower()
        if valor in {"on", "ligar", "ativar"}:
            definir_voz_ativa(True)
            self.atualizar_voz_label()
            self.registrar_evento("Retorno de voz ativado")
            self.adicionar_mensagem("NOVA", "Retorno de voz ativado.")
            falar("Retorno de voz ativado.")
            return

        if valor in {"off", "desligar", "desativar"}:
            definir_voz_ativa(False)
            self.atualizar_voz_label()
            self.registrar_evento("Retorno de voz desativado")
            self.adicionar_mensagem("NOVA", "Retorno de voz desativado.")
            return

        self.registrar_evento("Falha no comando de voz: valor inválido")
        self.adicionar_mensagem(
            "NOVA",
            "Use /voz on para ligar ou /voz off para desligar.",
        )

    def processar_comando_modo(self, texto):
        # Altera a personalidade da NOVA com base no comando /modo.
        partes = texto.split(maxsplit=1)
        if len(partes) < 2:
            disponiveis = ", ".join(sorted(modos))
            self.assistente_status = "NOVA aguardando um modo válido"
            self.registrar_evento("Falha na troca de modo: nome ausente")
            self.adicionar_mensagem(
                "NOVA",
                f"Use /modo <nome>. Modos disponíveis: {disponiveis}.",
            )
            return

        novo_modo = partes[1].strip().lower()
        resposta = set_modo(novo_modo)
        self.atualizar_modo_label()
        self.atualizar_voz_label()
        self.assistente_status = f"NOVA em modo {personalidade.modo_atual.upper()}"
        self.atualizar_painel_status()
        self.registrar_evento(f"Modo alterado para: {personalidade.modo_atual.upper()}")
        self.adicionar_mensagem("NOVA", resposta)

    def adicionar_mensagem(self, autor, texto):
        # Adiciona uma nova linha ao histórico usando markup simples do Kivy.
        historico = self.ids.historico
        trecho = f"[b]{autor}:[/b] {texto}"
        historico.text = f"{historico.text}\n\n{trecho}".strip()
        Clock.schedule_once(lambda *_: self.rolar_para_baixo(), 0)

    def rolar_para_baixo(self):
        # Mantém a conversa sempre posicionada na mensagem mais recente.
        self.ids.scroll.scroll_y = 0


class ChatBotApp(App):
    def build(self):
        # Carrega o layout descrito em assistente.kv e define o título da janela.
        self.title = "ChatBot Assistente"
        return Builder.load_file("assistente.kv")


if __name__ == "__main__":
    # Ponto de entrada quando o projeto é executado diretamente.
    ChatBotApp().run()

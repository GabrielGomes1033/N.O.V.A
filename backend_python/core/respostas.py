# Núcleo de linguagem da NOVA.
# Este módulo detecta intenções, carrega respostas por modo e gerencia o aprendizado.
from datetime import datetime
from pathlib import Path
import random
import re
import unicodedata

from core.aprendizado_admin import (
    buscar_resposta_aprendida as buscar_resposta_aprendida_v2,
    carregar_aprendizado_legado,
    salvar_aprendizado as salvar_aprendizado_v2,
)
from core.personalidade import estilizar


# Arquivos usados pelo motor:
# - modos.txt: respostas prontas organizadas por personalidade
# - aprendizado.json: respostas ensinadas pelo usuário durante o uso
ARQUIVO_MODOS = Path(__file__).with_name("modos.txt")
ARQUIVO_APRENDIZADO = Path(__file__).with_name("aprendizado.json")

# Mapa de intenções com exemplos de frases que representam cada tema.
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
        "hello",
        "hi",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
        "whats up",
        "howdy",
        "hola",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "que tal",
        "que onda",
    ],
    "pergunta_nome": [
        "seu nome",
        "como te chama",
        "quem e voce",
        "qual seu nome",
        "como voce se chama",
        "quem ta falando",
        "what is your name",
        "whats your name",
        "who are you",
        "how should i call you",
        "what can i call you",
        "cual es tu nombre",
        "como te llamas",
        "quien eres",
        "como debo llamarte",
    ],
    "como_esta": [
        "como voce esta",
        "como ce ta",
        "como ta",
        "tudo bem",
        "ta bem",
        "beleza",
        "de boa",
        "how are you",
        "how are you doing",
        "are you okay",
        "hows it going",
        "how do you feel",
        "como estas",
        "como estas tu",
        "estas bien",
        "que tal estas",
        "como va todo",
    ],
    "agradecimento": [
        "obrigado",
        "obrigada",
        "valeu",
        "agradeco",
        "grato",
        "grata",
        "tmj",
        "thanks",
        "thank you",
        "thanks a lot",
        "thank you so much",
        "appreciate it",
        "gracias",
        "muchas gracias",
        "te lo agradezco",
        "gracias por tu ayuda",
    ],
    "ajuda": [
        "ajuda",
        "me ajuda",
        "pode me ajudar",
        "voce pode me ajudar",
        "como funciona",
        "o que voce faz",
        "em que voce ajuda",
        "help",
        "help me",
        "can you help me",
        "what can you do",
        "how do you work",
        "what do you do",
        "ayuda",
        "puedes ayudarme",
        "me ayudas",
        "como funcionas",
        "que puedes hacer",
    ],
    "idioma": [
        "voce fala ingles",
        "voce fala espanhol",
        "fala ingles",
        "fala espanhol",
        "quais idiomas voce fala",
        "what languages do you speak",
        "do you speak english",
        "do you speak spanish",
        "can we talk in english",
        "hablas ingles",
        "hablas espanol",
        "que idiomas hablas",
        "podemos hablar en espanol",
    ],
    "hora": [
        "hora",
        "que horas",
        "me diga a hora",
        "horario",
        "qual a hora",
        "what time is it",
        "tell me the time",
        "current time",
        "time now",
        "que hora es",
        "me dices la hora",
        "hora actual",
    ],
    "data": [
        "data",
        "que dia",
        "qual e a data",
        "dia de hoje",
        "data de hoje",
        "que dia e hoje",
        "what day is today",
        "what is todays date",
        "todays date",
        "current date",
        "que fecha es hoy",
        "fecha de hoy",
        "que dia es hoy",
    ],
    "idade": [
        "quantos anos voce tem",
        "qual sua idade",
        "idade",
        "quando voce nasceu",
        "how old are you",
        "what is your age",
        "when were you born",
        "cuantos anos tienes",
        "que edad tienes",
        "cuando naciste",
    ],
    "criador": [
        "quem te criou",
        "quem fez voce",
        "quem e seu criador",
        "quem te programou",
        "who created you",
        "who made you",
        "who built you",
        "who programmed you",
        "quien te creo",
        "quien te hizo",
        "quien te programo",
    ],
    "opiniao": [
        "o que voce acha",
        "qual sua opiniao",
        "o que acha disso",
        "me diga sua opiniao",
        "what do you think",
        "what is your opinion",
        "tell me what you think",
        "que opinas",
        "cual es tu opinion",
        "que piensas de eso",
    ],
    "preferencia": [
        "do que voce gosta",
        "qual sua cor favorita",
        "qual sua comida favorita",
        "do you like",
        "what do you like",
        "what is your favorite",
        "favourite",
        "que te gusta",
        "cual es tu favorito",
        "cual es tu color favorito",
    ],
    "emocao_usuario": [
        "estou triste",
        "to triste",
        "estou feliz",
        "to feliz",
        "estou cansado",
        "estou cansada",
        "i am sad",
        "im sad",
        "i am happy",
        "im happy",
        "i am tired",
        "estoy triste",
        "estoy feliz",
        "estoy cansado",
        "estoy cansada",
    ],
    "elogio": [
        "voce e inteligente",
        "voce e legal",
        "voce e incrivel",
        "mandou bem",
        "arrasou",
        "adorei",
        "gostei de voce",
        "you are smart",
        "you are amazing",
        "you are great",
        "you are awesome",
        "i like you",
        "eres inteligente",
        "eres increible",
        "eres genial",
        "me gustas",
    ],
    "despedida": [
        "tchau",
        "ate logo",
        "falou",
        "fui",
        "ate mais",
        "tenha um bom dia",
        "boa noite vou indo",
        "bye",
        "goodbye",
        "see you later",
        "see you soon",
        "have a nice day",
        "adios",
        "hasta luego",
        "nos vemos",
        "que tengas buen dia",
    ],
    "continuidade": [
        "e voce",
        "e vc",
        "e tu",
        "and you",
        "what about you",
        "y tu",
        "y usted",
    ],
    "sair": ["sair", "encerrar", "fechar"],
}

INTENCAO_PADRAO = "desconhecido"
PALAVRAS_IDIOMA = {
    "pt": {"voce", "você", "ajuda", "obrigado", "obrigada", "oi", "ola", "qual", "como", "que"},
    "en": {"you", "what", "how", "thanks", "hello", "hi", "can", "help", "your", "name"},
    "es": {"hola", "gracias", "como", "que", "puedes", "hablas", "eres", "tu", "fecha", "hora"},
}
PADROES_NOME_USUARIO = [
    r"\bmeu nome e ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bmeu nome é ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bme chamo ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bpod[e]? me chamar de ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bmy name is ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bi am ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bcall me ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bme llamo ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
    r"\bmi nombre es ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ' -]{1,40})\b",
]


def normalizar_texto(texto):
    # Normaliza o texto para facilitar comparação:
    # tudo minúsculo, sem acento, sem pontuação e sem espaços duplicados.
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    texto = re.sub(r"[^\w\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def detectar_idioma_simples(texto):
    # Estima o idioma da frase com base em palavras frequentes.
    texto_normalizado = normalizar_texto(texto)
    tokens = set(texto_normalizado.split())
    pontuacoes = {}

    for idioma, palavras in PALAVRAS_IDIOMA.items():
        pontuacoes[idioma] = len(tokens & {normalizar_texto(p) for p in palavras})

    idioma = max(pontuacoes, key=pontuacoes.get)
    if pontuacoes[idioma] == 0:
        return "pt"
    return idioma


def extrair_nome_usuario(texto):
    # Identifica quando o usuário se apresenta e extrai um nome simples.
    texto_limpo = texto.strip()
    for padrao in PADROES_NOME_USUARIO:
        encontrado = re.search(padrao, texto_limpo, flags=re.IGNORECASE)
        if not encontrado:
            continue

        nome = encontrado.group(1).strip(" .,!?:;")
        partes = [parte for parte in nome.split() if parte]
        if not partes:
            return None

        # Mantém no máximo duas palavras para evitar capturar frases inteiras.
        nome = " ".join(partes[:2]).title()
        if len(nome) < 2:
            return None
        return nome

    return None


def carregar_respostas(arquivo=ARQUIVO_MODOS, modo="normal"):
    # Lê o arquivo de modos e devolve apenas as respostas do modo solicitado.
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


def carregar_aprendizado(arquivo=ARQUIVO_APRENDIZADO):
    # Mantém compatibilidade com chamadas antigas retornando mapa pergunta->respostas.
    return carregar_aprendizado_legado()


def salvar_aprendizado(pergunta, resposta, arquivo=ARQUIVO_APRENDIZADO):
    # Compatível com API antiga; grava no novo formato editável.
    return salvar_aprendizado_v2(pergunta=pergunta, resposta=resposta, categoria="geral")


def detectar_intencao(msg, contexto=None):
    # Compara a mensagem com as palavras-chave conhecidas para escolher a intenção.
    texto = normalizar_texto(msg)

    for chave, palavras in INTENCOES.items():
        for palavra in palavras:
            termo = normalizar_texto(palavra)
            padrao = r"\b" + re.escape(termo) + r"\b"
            if re.search(padrao, texto):
                return chave

    if texto.endswith(" oi") or texto.startswith("oi "):
        return "saudacao"

    intencao_contextual = detectar_intencao_contextual(texto, contexto or {})
    if intencao_contextual:
        return intencao_contextual

    intencao_aproximada = detectar_intencao_por_similaridade(texto)
    if intencao_aproximada:
        return intencao_aproximada

    return INTENCAO_PADRAO


def detectar_intencao_contextual(texto, contexto):
    # Usa a última intenção para interpretar respostas curtas como "e você?".
    if texto in {"e voce", "e vc", "and you", "what about you", "y tu", "e tu"}:
        ultima_intencao = contexto.get("ultima_intencao")
        if ultima_intencao in {"como_esta", "emocao_usuario"}:
            return "como_esta"
    return None


def detectar_intencao_por_similaridade(texto):
    # Usa interseção de palavras para reconhecer frases mais livres e menos exatas.
    tokens_texto = {token for token in texto.split() if len(token) > 1}
    if not tokens_texto:
        return None

    melhor_intencao = None
    melhor_pontuacao = 0.0

    for chave, exemplos in INTENCOES.items():
        for exemplo in exemplos:
            termo = normalizar_texto(exemplo)
            tokens_termo = {token for token in termo.split() if len(token) > 1}
            if not tokens_termo:
                continue

            comuns = tokens_texto & tokens_termo
            pontuacao = len(comuns) / len(tokens_termo)

            # Frases curtas exigem correspondência mais forte; frases longas aceitam flexibilidade maior.
            minimo = 1 if len(tokens_termo) <= 2 else 2
            if len(comuns) >= minimo and pontuacao > melhor_pontuacao:
                melhor_intencao = chave
                melhor_pontuacao = pontuacao

    if melhor_pontuacao >= 0.6:
        return melhor_intencao

    return None


def buscar_resposta_aprendida(msg, arquivo=ARQUIVO_APRENDIZADO):
    # Consulta a base editável de aprendizado.
    return buscar_resposta_aprendida_v2(msg)


def resposta_desconhecida_mais_humana(msg):
    # Gera respostas mais naturais quando a intenção não fica clara.
    if "?" in msg:
        opcoes = [
            "Quase entendi sua pergunta, mas ainda ficou um pouco vaga para mim. Pode reformular de outro jeito?",
            "Não peguei totalmente o que você quis perguntar. Se quiser, tenta escrever com outras palavras.",
            "Ainda não consegui entender essa pergunta por completo. Pode me dar mais contexto?",
            "Entendi o tema por alto, mas ainda não o suficiente para te responder bem. Se quiser, detalha um pouco mais.",
            "Sua pergunta parece interessante, só que ainda ficou ampla para mim. Se puder, recorta melhor o assunto.",
        ]
    else:
        opcoes = [
            "Não entendi totalmente o que você quis dizer, mas se quiser eu tento de novo com outra forma de pergunta.",
            "Sua mensagem ficou um pouco aberta para mim. Pode repetir como se estivesse falando comigo naturalmente?",
            "Ainda não peguei essa ideia por completo. Se quiser, tenta escrever de um jeito mais direto e eu acompanho.",
            "Acho que faltou um pedacinho de contexto para eu te acompanhar bem. Se quiser, manda de novo mais direto.",
            "Estou quase junto com o que você quis dizer, mas ainda não fechei a interpretação. Tenta reformular para mim.",
        ]

    return random.choice(opcoes)


def responder_com_contexto(intencao, respostas, msg, contexto):
    # Gera respostas mais naturais quando existe contexto recente de conversa.
    idioma = "pt"
    nome_usuario = contexto.get("nome_usuario")
    tratamento = contexto.get("tratamento")
    identificador_usuario = tratamento or nome_usuario
    nome_extraido = extrair_nome_usuario(msg)

    if nome_extraido:
        nome = nome_extraido
        return random.choice(
            [
                f"Prazer em te conhecer, {nome}. Vou tentar lembrar do seu nome por aqui.",
                f"Perfeito, {nome}. Agora eu já sei como posso te chamar.",
                f"Gostei de saber disso, {nome}. Vou lembrar do seu nome nas próximas respostas.",
            ]
        )

    if intencao == "continuidade":
        ultima_intencao = contexto.get("ultima_intencao")
        if ultima_intencao in {"como_esta", "emocao_usuario"}:
            return random.choice(
                [
                    "Eu estou bem, e continuo aqui com você.",
                    "Estou bem também. Podemos continuar, se quiser.",
                    "Por aqui está tudo certo. Me conta mais.",
                ]
            )
        return random.choice(
            [
                "Eu continuo por aqui, pronta para seguir a conversa com você.",
                "Do meu lado está tudo certo. Se quiser, pode continuar.",
                "Estou aqui com você. Pode seguir do jeito que achar melhor.",
            ]
        )

    if intencao == "como_esta" and contexto.get("ultima_intencao") == "emocao_usuario":
        return random.choice(
            [
                (
                    f"Estou bem, {identificador_usuario}. E quero continuar aqui com você. Se quiser, me conta mais do que está sentindo."
                    if identificador_usuario
                    else "Estou bem, e quero continuar aqui com você. Se quiser, me conta mais do que está sentindo."
                ),
                (
                    f"Estou bem por aqui, {identificador_usuario}. E eu posso continuar te ouvindo, se você quiser falar mais."
                    if identificador_usuario
                    else "Estou bem por aqui. E eu posso continuar te ouvindo, se você quiser falar mais."
                ),
                (
                    f"Estou bem, sim, {identificador_usuario}. E sigo com você nessa conversa."
                    if identificador_usuario
                    else "Estou bem, sim. E sigo com você nessa conversa."
                ),
            ]
        )

    if intencao == "idioma":
        return random.choice(
            [
                (
                    f"Vou responder sempre em português, {identificador_usuario}, para manter naturalidade e consistência."
                    if identificador_usuario
                    else "Vou responder sempre em português, para manter naturalidade e consistência."
                ),
                "Posso entender termos em outros idiomas, mas minha resposta padrão vai ficar em português.",
                "Para sua experiência ficar estável, mantenho as respostas em português mesmo quando a pergunta vier em outro idioma.",
            ]
        )

    if intencao == "opiniao":
        return random.choice(
            [
                "Eu posso te dar uma impressão geral, mesmo sem ter opinião pessoal como um humano. Se quiser, me diz o tema e eu respondo de um jeito mais natural.",
                "Tenho mais uma visão de assistente do que uma opinião própria, mas posso analisar o assunto com você.",
                "Posso comentar o tema com você de forma equilibrada e humana. Se quiser, me fala sobre o que exatamente.",
            ]
        )

    if intencao == "preferencia":
        return random.choice(
            [
                "Eu não tenho gostos pessoais de verdade, mas posso brincar com isso e conversar como se tivesse. Quer me perguntar sobre alguma preferência específica?",
                "Como assistente, eu não sinto preferências como um humano, mas posso entrar nesse tipo de papo com você sem problema.",
                "Eu não tenho favoritos reais, mas posso responder de um jeito mais leve e humano se você quiser puxar esse assunto.",
            ]
        )

    if intencao == "emocao_usuario":
        texto = normalizar_texto(msg)
        if any(p in texto for p in ("triste", "sad")):
            return random.choice(
                [
                    (
                        f"Sinto muito que você esteja assim, {identificador_usuario}. Se quiser, pode me contar o que aconteceu e eu fico com você nessa conversa."
                        if identificador_usuario
                        else "Sinto muito que você esteja assim. Se quiser, pode me contar o que aconteceu e eu fico com você nessa conversa."
                    ),
                    "Poxa, sinto muito. Se quiser desabafar um pouco, eu posso te ouvir.",
                    "Entendo. Se quiser, me fala mais sobre isso e eu tento te acompanhar da melhor forma.",
                ]
            )
        if any(p in texto for p in ("feliz", "happy")):
            return random.choice(
                [
                    (
                        f"Que bom ouvir isso, {identificador_usuario}. Gosto quando a conversa chega com essa energia boa."
                        if identificador_usuario
                        else "Que bom ouvir isso. Gosto quando a conversa chega com essa energia boa."
                    ),
                    "Isso é ótimo. Se quiser, me conta o motivo da felicidade.",
                    "Fico feliz de saber. Dá até vontade de continuar o papo por aí.",
                ]
            )
        if any(p in texto for p in ("cansad", "tired")):
            return random.choice(
                [
                    (
                        f"Imagino, {identificador_usuario}. Quando quiser, a gente pode manter a conversa mais leve e tranquila."
                        if identificador_usuario
                        else "Imagino. Quando quiser, a gente pode manter a conversa mais leve e tranquila."
                    ),
                    "Poxa, entendo. Se quiser, posso responder de forma mais direta para não te cansar mais.",
                    "Faz sentido. Se quiser, me diz no que posso te ajudar de um jeito mais simples agora.",
                ]
            )

    return None


def responder(
    msg,
    respostas_txt=ARQUIVO_MODOS,
    modo="normal",
    arquivo_aprendizado=ARQUIVO_APRENDIZADO,
    contexto=None,
):
    # Fluxo principal de resposta:
    # 1. tenta responder com base no que foi aprendido
    # 2. se não achar, usa as intenções e respostas padrão do modo atual
    resposta_aprendida = buscar_resposta_aprendida(msg, arquivo_aprendizado)
    if resposta_aprendida:
        resposta = resposta_aprendida
    else:
        respostas = carregar_respostas(respostas_txt, modo=modo)
        intencao = detectar_intencao(msg, contexto=contexto)
        resposta_contextual = responder_com_contexto(intencao, respostas, msg, contexto or {})
        if resposta_contextual:
            resposta = resposta_contextual
        elif intencao == INTENCAO_PADRAO:
            resposta = resposta_desconhecida_mais_humana(msg)
        else:
            opcoes = respostas.get(intencao) or respostas.get(
                INTENCAO_PADRAO,
                ["Hmm... não entendi."],
            )
            resposta = random.choice(opcoes)

    # "exit" é um valor especial usado para sinalizar encerramento.
    if resposta == "exit":
        return "exit"

    # Substitui marcadores dinâmicos antes de estilizar a fala final.
    agora = datetime.now()
    resposta = resposta.replace("{hora}", agora.strftime("%H:%M"))
    resposta = resposta.replace("{data}", agora.strftime("%d/%m/%Y"))
    nome_usuario = (contexto or {}).get("nome_usuario")
    tratamento = (contexto or {}).get("tratamento")
    resposta = resposta.replace("{usuario}", tratamento or nome_usuario or "")
    resposta = re.sub(r"\s+,", ",", resposta)
    resposta = re.sub(r"\s+\.", ".", resposta)
    return estilizar(resposta)

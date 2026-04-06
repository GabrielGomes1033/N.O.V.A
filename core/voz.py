# Camada de voz da NOVA.
# A fala roda em um processo separado para evitar travamentos na interface.
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys


PASTA_CACHE_VOZ = Path("/tmp/nova_voice")
VOZ_NEURAL_PADRAO = "pt-BR-FranciscaNeural"
GST_PLAYER = "/usr/bin/gst-play-1.0"

_voz_ativa = True
_processo_voz = None


SUBSTITUICOES_DE_FALA = {
    "NOVA // INTERFACE TATICA": "Nova",
    "ASSISTENTE DE BORDO": "assistente",
    "CANAL SEGURO": "",
    "SISTEMA ONLINE": "",
}

REMOVER_DA_FALA = [
    "Compreendo.",
    "De acordo com sua solicitação:",
    "Certamente.",
    "😂 Olha só...",
    "Hmm, interessante!",
    "KKKK vamos lá:",
    "Ah claro...",
    "Nossa, que surpresa...",
    "Uau, ninguém esperava isso...",
    "🌟 Lembre-se:",
    "Aqui vai uma reflexão:",
    "Para você pensar:",
    "🤖 Processando...",
    "Analisando dados:",
    "Sinal recebido:",
    "Estou à disposição.",
    "Caso precise de mais ajuda, informe.",
    "(essa foi boa)",
    "(óbvio)",
]

EXPRESSOES_MAIS_HUMANAS = {
    "Não captei isso.": "Não entendi muito bem.",
    "Não consegui compreender sua mensagem com clareza.": "Não entendi muito bem o que você quis dizer.",
    "Não identifiquei corretamente a intenção da mensagem.": "Não consegui entender direitinho.",
    "Entrada não reconhecida.": "Não entendi direito.",
    "Comando ambíguo. Tente novamente.": "Pode repetir de outro jeito?",
    "Retorno de voz ativado.": "Pronto, agora eu vou falar com você.",
    "Retorno de voz desativado.": "Certo, vou parar de falar em voz alta.",
}


def _worker_path():
    return Path(__file__).with_name("voz_worker.py")


def _player_disponivel():
    return Path(GST_PLAYER).exists()


def _tts_disponivel():
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        return False
    return True


def voz_disponivel():
    return _player_disponivel() and _tts_disponivel() and _worker_path().is_file()


def voz_ativa():
    return _voz_ativa


def definir_voz_ativa(ativa):
    global _voz_ativa
    _voz_ativa = bool(ativa)


def descricao_voz():
    if voz_disponivel():
        return VOZ_NEURAL_PADRAO
    return "indisponível"


def _pontuacao_humana(texto):
    texto = re.sub(r"https?://\S+", "o link está no chat", texto)
    texto = re.sub(r"\[[^\]]*\]", " ", texto)
    texto = re.sub(r"[\U00010000-\U0010ffff]", " ", texto)
    texto = texto.replace("//", ", ")
    texto = texto.replace("...", ".")
    texto = texto.replace(":", ", ")

    for origem, destino in SUBSTITUICOES_DE_FALA.items():
        texto = texto.replace(origem, destino)

    for trecho in REMOVER_DA_FALA:
        texto = texto.replace(trecho, " ")

    for origem, destino in EXPRESSOES_MAIS_HUMANAS.items():
        texto = texto.replace(origem, destino)

    texto = re.sub(r"\b(timestamp atual|registro temporal ativo)\b", "agora", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bidentificação\b", "eu sou", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bmodo alterado para\b", "agora estou no modo", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bpesquisa iniciada no google para\b", "pesquisei no Google por", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bnão consegui abrir o navegador automaticamente, mas aqui está sua pesquisa\b", "não consegui abrir o navegador, mas a pesquisa está no chat", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\beu poderei responder\b", "eu vou responder", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\btotal de respostas ensinadas para essa pergunta\b", "agora eu sei", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b(\d{2}):(\d{2})\b", r"\1 e \2", texto)
    texto = re.sub(r"\b(\d{2})/(\d{2})/(\d{4})\b", r"\1 do \2 de \3", texto)
    texto = re.sub(r"\bNOVA\b", "Nova", texto)
    texto = re.sub(r"\s+", " ", texto).strip(" ,.-")

    if texto and texto[-1] not in ".!?":
        texto += "."
    return texto


def preparar_texto_para_voz(texto):
    texto = _pontuacao_humana(texto)
    texto = re.sub(r"\b(Oi|Olá|Tudo certo|Imagina)\b(?![,!.?])", r"\1,", texto)
    texto = texto.replace(". ", "... ")
    texto = texto.replace(", o link está no chat", ". O link está no chat")
    return re.sub(r"\s+", " ", texto).strip()


def _encerrar_processo_anterior():
    global _processo_voz
    if _processo_voz is None:
        return

    if _processo_voz.poll() is None:
        try:
            _processo_voz.terminate()
        except OSError:
            pass

    _processo_voz = None


def falar(texto):
    global _processo_voz
    if not voz_disponivel() or not _voz_ativa:
        return False

    texto_limpo = preparar_texto_para_voz(texto)
    if not texto_limpo:
        return False

    PASTA_CACHE_VOZ.mkdir(parents=True, exist_ok=True)
    _encerrar_processo_anterior()

    comando = [
        sys.executable,
        str(_worker_path()),
        texto_limpo,
        str(PASTA_CACHE_VOZ),
        VOZ_NEURAL_PADRAO,
        GST_PLAYER,
    ]

    _processo_voz = subprocess.Popen(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        env=os.environ.copy(),
    )
    return True

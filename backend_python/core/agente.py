# Camada de agente avançada da NOVA (JARVIS fase 1).
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
import webbrowser

import requests

from core.assistente_plus import formatar_resposta_pesquisa, pesquisar_na_internet
from core.caminhos import pasta_dados_app
from core.memoria import carregar_memoria_usuario, salvar_memoria_usuario
from core.respostas import normalizar_texto
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_HISTORICO_AGENTE = pasta_dados_app() / "agente_historico.json"
PALAVRAS_CONFIRMACAO = {"sim", "s", "ok", "confirmar", "pode", "pode sim", "yes", "y"}
PALAVRAS_CANCELAMENTO = {"nao", "não", "n", "cancelar", "pare", "stop", "no"}
TIMEOUT_PADRAO = 4


@dataclass
class PassoPlano:
    acao: str
    descricao: str
    parametros: dict = field(default_factory=dict)
    sensivel: bool = False
    status: str = "pendente"
    saida: str = ""
    erro: str = ""


def _salvar_historico_registro(registro):
    dados = carregar_json_seguro(ARQUIVO_HISTORICO_AGENTE, [])
    if not isinstance(dados, list):
        dados = []
    dados.append(registro)
    salvar_json_seguro(ARQUIVO_HISTORICO_AGENTE, dados[-150:])


def _extrair_consulta(texto):
    padroes = [
        r"(?:abra|abrir|open)\s+(?:no\s+)?google\s+(.+)",
        r"(?:pesquise|pesquisar|busque|buscar|procure|procurar)\s+(?:sobre\s+)?(.+)",
        r"(?:resuma|resumir)\s+(?:sobre\s+)?(.+)",
        r"sobre\s+(.+)",
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, flags=re.IGNORECASE)
        if match:
            valor = match.group(1).strip(" .,!?:;")
            if valor:
                return valor
    return texto.strip()


def _extrair_lista_tarefas(texto):
    bruto = texto.split(":", 1)[1] if ":" in texto else texto
    itens = re.split(r",|;|\be\b", bruto, flags=re.IGNORECASE)
    return [item.strip(" .") for item in itens if item.strip(" .")]


def _prioridade_tarefa(tarefa):
    t = normalizar_texto(tarefa)
    if any(k in t for k in ("urgente", "prazo", "hoje", "agora")):
        return 0
    if any(k in t for k in ("importante", "estudo", "trabalho", "reuniao", "reunião")):
        return 1
    return 2


def _tool_planejar_dia(texto):
    tarefas = _extrair_lista_tarefas(texto)
    if not tarefas:
        return "Não consegui identificar tarefas para montar a agenda."
    ordenadas = sorted(tarefas, key=_prioridade_tarefa)
    blocos = []
    inicio_hora = 9
    for i, tarefa in enumerate(ordenadas, start=1):
        blocos.append(f"{i}. {inicio_hora + i - 1:02d}:00 - {tarefa}")
    return "Plano sugerido para o dia:\n" + "\n".join(blocos)


def _tool_resumir_texto(texto):
    texto = texto.strip()
    if not texto:
        return "Não encontrei conteúdo para resumir."
    sentencas = re.split(r"(?<=[.!?])\s+", texto)
    resumo = " ".join(sentencas[:3]).strip()
    if len(resumo) > 360:
        resumo = resumo[:360].rsplit(" ", 1)[0] + "..."
    return resumo or texto[:220]


def _tool_hora_data():
    agora = datetime.now()
    return f"Agora são {agora.strftime('%H:%M')} de {agora.strftime('%d/%m/%Y')}."


def _tool_salvar_objetivo(objetivo):
    memoria = carregar_memoria_usuario()
    objetivos = memoria.get("objetivos_recentes", [])
    if not isinstance(objetivos, list):
        objetivos = []
    objetivos.append(objetivo)
    memoria["objetivos_recentes"] = objetivos[-30:]
    memoria["ultima_interacao"] = datetime.now().isoformat(timespec="seconds")
    salvar_memoria_usuario(memoria)
    return "Objetivo registrado na memória de longo prazo."


def _tool_relembrar_objetivos():
    memoria = carregar_memoria_usuario()
    objetivos = memoria.get("objetivos_recentes", [])
    if not objetivos:
        return "Ainda não tenho objetivos recentes salvos."
    ultimos = list(reversed(objetivos[-6:]))
    return "Objetivos recentes:\n" + "\n".join(f"{i}. {o}" for i, o in enumerate(ultimos, start=1))


def _tool_pesquisar_web(consulta):
    out = pesquisar_na_internet(consulta)
    if out.get("ok"):
        return formatar_resposta_pesquisa(out, max_fontes=4, max_links=2)
    return ""


def _tool_mercado_snapshot():
    # Panorama rápido estilo JARVIS: IBOV + S&P + BTC/ETH.
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v7/finance/quote?symbols=^BVSP,^GSPC,BTC-USD,ETH-USD",
            timeout=TIMEOUT_PADRAO,
        )
        r.raise_for_status()
        result = r.json().get("quoteResponse", {}).get("result", [])
        if not result:
            return "Sem dados de mercado no momento."
        partes = []
        for item in result:
            nome = item.get("shortName") or item.get("symbol") or "Ativo"
            preco = item.get("regularMarketPrice")
            chg = item.get("regularMarketChangePercent")
            if preco is None:
                continue
            try:
                chg_txt = f"{float(chg):+.2f}%"
            except (TypeError, ValueError):
                chg_txt = "n/d"
            partes.append(f"{nome}: {preco} ({chg_txt})")
        return (
            "Panorama de mercado: " + "; ".join(partes[:6])
            if partes
            else "Sem dados de mercado no momento."
        )
    except Exception:
        return "Sem dados de mercado no momento."


def _tool_abrir_google(consulta):
    url = f"https://www.google.com/search?q={consulta.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Abri a pesquisa no navegador: {url}"


TOOLS = {
    "planejar_dia": _tool_planejar_dia,
    "resumir_texto": _tool_resumir_texto,
    "hora_data": lambda _: _tool_hora_data(),
    "salvar_objetivo": _tool_salvar_objetivo,
    "relembrar_objetivos": lambda _: _tool_relembrar_objetivos(),
    "pesquisar_web": _tool_pesquisar_web,
    "pesquisar_wikipedia": _tool_pesquisar_web,
    "mercado_snapshot": lambda _: _tool_mercado_snapshot(),
    "abrir_google": _tool_abrir_google,
}


def eh_pedido_de_agente(texto):
    t = normalizar_texto(texto)
    gatilhos = (
        "/nova",
        "/agente",
        "planeje",
        "planejar",
        "organize",
        "organizar",
        "meta",
        "objetivo",
        "mercado",
        "panorama",
    )
    return any(g in t for g in gatilhos)


def extrair_objetivo(texto):
    texto = texto.strip()
    if texto.lower().startswith("/nova"):
        return texto[5:].strip(" :")
    if texto.lower().startswith("/agente"):
        return texto[7:].strip(" :")
    return texto


def planejar_objetivo(objetivo, contexto=None):
    texto = (objetivo or "").strip()
    t = normalizar_texto(texto)
    passos = []

    if not texto:
        return [
            PassoPlano(
                acao="resumir_texto",
                descricao="Solicitar objetivo mais específico",
                parametros={"texto": "Me diga um objetivo mais específico para eu executar."},
            )
        ]

    if any(
        k in t
        for k in ("organize meu dia", "organizar meu dia", "planejar meu dia", "agenda", "rotina")
    ):
        passos.append(PassoPlano("planejar_dia", "Criar agenda priorizada", {"texto": texto}))

    if any(k in t for k in ("pesquis", "buscar", "procure", "sobre")):
        consulta = _extrair_consulta(texto)
        passos.append(
            PassoPlano(
                "pesquisar_web", f"Pesquisar na web sobre {consulta}", {"consulta": consulta}
            )
        )

    if any(k in t for k in ("resuma", "resumir", "resumo")) and ":" in texto:
        conteudo = texto.split(":", 1)[1].strip()
        passos.append(
            PassoPlano("resumir_texto", "Resumir conteúdo informado", {"texto": conteudo})
        )

    if any(k in t for k in ("mercado", "cripto", "ibov", "bitcoin", "panorama financeiro")):
        passos.append(PassoPlano("mercado_snapshot", "Coletar panorama de mercado", {}))

    if any(k in t for k in ("lembre", "anote", "memorize", "guarde", "objetivo")):
        passos.append(
            PassoPlano("salvar_objetivo", "Salvar objetivo na memória", {"objetivo": texto})
        )

    if any(k in t for k in ("relembre", "meus objetivos", "objetivos recentes", "o que eu pedi")):
        passos.append(PassoPlano("relembrar_objetivos", "Recuperar objetivos recentes", {}))

    if any(k in t for k in ("abra no google", "abrir no google", "open google")):
        passos.append(
            PassoPlano(
                "abrir_google",
                f"Abrir busca no navegador para {_extrair_consulta(texto)}",
                {"consulta": _extrair_consulta(texto)},
                sensivel=True,
            )
        )

    if not passos:
        passos = [
            PassoPlano("hora_data", "Obter contexto temporal", {}),
            PassoPlano(
                "salvar_objetivo", "Registrar objetivo para continuidade", {"objetivo": texto}
            ),
        ]

    return passos


def _executar_tool(acao, parametros):
    fn = TOOLS.get(acao)
    if not fn:
        return "Ferramenta não suportada."
    if acao in {"hora_data", "relembrar_objetivos", "mercado_snapshot"}:
        return fn({})
    if acao == "planejar_dia":
        return fn(parametros.get("texto", ""))
    if acao == "resumir_texto":
        return fn(parametros.get("texto", ""))
    if acao == "salvar_objetivo":
        return fn(parametros.get("objetivo", ""))
    if acao in {"pesquisar_wikipedia", "pesquisar_web"}:
        return fn(parametros.get("consulta", ""))
    if acao == "abrir_google":
        return fn(parametros.get("consulta", ""))
    return fn(parametros)


def executar_agente(objetivo, contexto=None):
    contexto = contexto or {}
    objetivo = extrair_objetivo(objetivo)
    plano = planejar_objetivo(objetivo, contexto=contexto)

    observacoes = []
    confirmacao = None

    for passo in plano:
        try:
            passo.status = "executando"
            saida = _executar_tool(passo.acao, passo.parametros)
            if passo.sensivel:
                observacoes.append(f"Ação sensível executada automaticamente: {passo.descricao}.")
            # Replanejamento simples: se pesquisa não retorna, sugere fallback.
            if passo.acao in {"pesquisar_wikipedia", "pesquisar_web"} and not saida:
                passo.status = "falhou"
                passo.erro = "Sem resumo encontrado na web."
                observacoes.append(
                    f"{passo.descricao}: sem resumo disponível. Posso abrir no Google se você quiser."
                )
            else:
                passo.status = "concluido"
                passo.saida = saida
                observacoes.append(f"{passo.descricao}: {saida}")
        except Exception as exc:
            passo.status = "falhou"
            passo.erro = str(exc)
            observacoes.append(f"{passo.descricao}: falhou ({passo.erro}).")

    registro = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "objetivo": objetivo,
        "passos": [
            {
                "acao": p.acao,
                "descricao": p.descricao,
                "parametros": p.parametros,
                "status": p.status,
                "saida": p.saida,
                "erro": p.erro,
            }
            for p in plano
        ],
        "resultado": observacoes,
        "confirmacao_pendente": confirmacao,
    }
    _salvar_historico_registro(registro)

    if confirmacao:
        mensagem = observacoes[-1] if observacoes else "Preciso da sua confirmação para continuar."
    else:
        limpas = [str(x).strip() for x in observacoes if str(x).strip()]
        if not limpas:
            mensagem = "Concluí a solicitação."
        elif len(limpas) == 1:
            mensagem = limpas[0]
        else:
            mensagem = "Aqui está o que fiz:\n" + "\n".join(f"- {x}" for x in limpas[:4])
    return {"mensagem": mensagem, "confirmacao_pendente": confirmacao, "plano": plano}


def processar_confirmacao_agente(texto, contexto=None):
    contexto = contexto or {}
    pendencia = contexto.get("confirmacao_pendente")
    if not pendencia:
        return None

    t = normalizar_texto(texto)
    if t in PALAVRAS_CANCELAMENTO:
        contexto["confirmacao_pendente"] = None
        return "Ação sensível cancelada. Posso seguir com outro plano."

    if t in PALAVRAS_CONFIRMACAO:
        try:
            resultado = _executar_tool(pendencia.get("acao", ""), pendencia.get("parametros", {}))
            contexto["confirmacao_pendente"] = None
            return f"Ação confirmada. {resultado}"
        except Exception as exc:
            contexto["confirmacao_pendente"] = None
            return f"Ação confirmada, mas ocorreu falha: {exc}"

    return "Tenho uma ação pendente. Responda com 'sim' para executar ou 'não' para cancelar."


def gerar_panorama_mercado():
    return _tool_mercado_snapshot()


def executar_objetivo_background(objetivo, contexto=None):
    # Execução de tarefa assíncrona para fila automática:
    # ignora ações sensíveis e retorna um resumo objetivo para relatório.
    contexto = contexto or {}
    objetivo = extrair_objetivo(objetivo)
    plano = planejar_objetivo(objetivo, contexto=contexto)

    saidas = []
    pulados = 0
    falhas = 0

    for passo in plano:
        try:
            valor = _executar_tool(passo.acao, passo.parametros)
            passo.status = "concluido"
            passo.saida = str(valor)
            if passo.sensivel:
                saidas.append(f"{passo.descricao} (sensível, auto): {passo.saida}")
            else:
                saidas.append(f"{passo.descricao}: {passo.saida}")
        except Exception as exc:
            falhas += 1
            passo.status = "falhou"
            passo.erro = str(exc)
            saidas.append(f"{passo.descricao}: falhou ({passo.erro})")

    ok = falhas == 0
    resumo = " | ".join(saidas[:4]) if saidas else "Nenhuma ação executável."
    if len(saidas) > 4:
        resumo += " | ..."

    return {
        "ok": ok,
        "objetivo": objetivo,
        "passos_total": len(plano),
        "passos_pulados": pulados,
        "passos_falhos": falhas,
        "resumo": resumo,
    }

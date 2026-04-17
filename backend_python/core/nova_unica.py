from __future__ import annotations

from datetime import datetime
import re

from core.assistente_plus import (
    adicionar_lembrete,
    calcular_expressao,
    consultar_clima,
    cotacoes_financeiras,
    deve_acionar_pesquisa_web,
    extrair_consulta_pesquisa_web,
    formatar_cotacoes_humanas,
    formatar_resposta_pesquisa,
    listar_lembretes,
    pesquisar_na_internet,
)
from core.caminhos import pasta_dados_app
from core.memoria import carregar_memoria_usuario
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_PERFIL = pasta_dados_app() / "perfil_unico.json"
ARQUIVO_METRICAS = pasta_dados_app() / "metricas_unica.json"


def _agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _perfil_padrao() -> dict:
    return {
        "versao": 1,
        "tom": "natural",
        "tamanho_resposta": "media",
        "proatividade": True,
        "areas_interesse": {},
        "feedback_medio": 0.0,
        "feedback_total": 0,
        "ultima_atualizacao": _agora_iso(),
        "ultimo_briefing_data": "",
    }


def carregar_perfil() -> dict:
    dados = carregar_json_seguro(ARQUIVO_PERFIL, _perfil_padrao())
    if not isinstance(dados, dict):
        dados = _perfil_padrao()

    perfil = _perfil_padrao()
    perfil.update(dados)
    if not isinstance(perfil.get("areas_interesse"), dict):
        perfil["areas_interesse"] = {}
    salvar_json_seguro(ARQUIVO_PERFIL, perfil)
    return perfil


def salvar_perfil(perfil: dict) -> None:
    base = _perfil_padrao()
    base.update(perfil or {})
    base["ultima_atualizacao"] = _agora_iso()
    salvar_json_seguro(ARQUIVO_PERFIL, base)


def _atualizar_interesses(perfil: dict, texto: str) -> dict:
    texto_l = texto.lower()
    mapa = {
        "programacao": ["python", "java", "javascript", "api", "codigo", "flutter", "backend"],
        "ia": ["ia", "inteligencia artificial", "agente", "llm", "prompt", "openai"],
        "ciberseguranca": ["ciber", "cyber", "seguranca", "segurança", "hacker", "termux", "pentest"],
        "financas": ["dolar", "euro", "bitcoin", "ethereum", "mercado", "cotacao", "invest"],
        "produtividade": ["lembrete", "agenda", "planejar", "projeto", "organizar"],
        "clima": ["tempo", "clima", "temperatura", "chuva"],
    }
    areas = perfil.get("areas_interesse", {})
    if not isinstance(areas, dict):
        areas = {}

    for area, termos in mapa.items():
        if any(t in texto_l for t in termos):
            areas[area] = int(areas.get(area, 0)) + 1

    perfil["areas_interesse"] = areas
    return perfil


def atualizar_perfil_por_interacao(mensagem: str, resposta: str) -> dict:
    perfil = carregar_perfil()
    perfil = _atualizar_interesses(perfil, mensagem)

    if len(mensagem.strip()) <= 15:
        perfil["tamanho_resposta"] = "curta"
    elif len(mensagem.strip()) >= 140:
        perfil["tamanho_resposta"] = "longa"

    if any(t in mensagem.lower() for t in ["formal", "profissional", "objetivo"]):
        perfil["tom"] = "formal"
    elif any(t in mensagem.lower() for t in ["leve", "humano", "casual", "natural"]):
        perfil["tom"] = "natural"

    salvar_perfil(perfil)
    return perfil


def aplicar_identidade_nova(texto: str, perfil: dict, nome_usuario: str = "") -> str:
    t = (texto or "").strip()
    if not t:
        return t

    tom = str(perfil.get("tom", "natural"))
    tamanho = str(perfil.get("tamanho_resposta", "media"))

    if tamanho == "curta" and len(t) > 300:
        t = t[:300].rsplit(" ", 1)[0] + "..."

    if tom == "formal":
        if nome_usuario:
            t = f"{nome_usuario}, {t}"
        if not t.endswith((".", "!", "?")):
            t += "."
        return t

    # tom natural: evita chamar o nome em toda resposta para não soar repetitivo.
    return t


def _metricas_padrao() -> dict:
    return {
        "versao": 1,
        "chat_total": 0,
        "chat_erros": 0,
        "tempo_medio_ms": 0.0,
        "feedback_total": 0,
        "feedback_media": 0.0,
        "eventos": [],
        "atualizado_em": _agora_iso(),
    }


def carregar_metricas() -> dict:
    dados = carregar_json_seguro(ARQUIVO_METRICAS, _metricas_padrao())
    if not isinstance(dados, dict):
        dados = _metricas_padrao()
    base = _metricas_padrao()
    base.update(dados)
    if not isinstance(base.get("eventos"), list):
        base["eventos"] = []
    return base


def registrar_metrica(evento: str, duracao_ms: float, ok: bool = True) -> None:
    met = carregar_metricas()
    met["chat_total"] = int(met.get("chat_total", 0)) + 1
    if not ok:
        met["chat_erros"] = int(met.get("chat_erros", 0)) + 1

    atual = float(met.get("tempo_medio_ms", 0.0))
    total = int(met.get("chat_total", 1))
    met["tempo_medio_ms"] = ((atual * (total - 1)) + float(duracao_ms)) / total

    eventos = met.get("eventos", [])
    if not isinstance(eventos, list):
        eventos = []
    eventos.append(
        {
            "quando": _agora_iso(),
            "evento": evento,
            "duracao_ms": round(float(duracao_ms), 2),
            "ok": bool(ok),
        }
    )
    met["eventos"] = eventos[-300:]
    met["atualizado_em"] = _agora_iso()
    salvar_json_seguro(ARQUIVO_METRICAS, met)


def registrar_feedback(score: int, comentario: str = "") -> dict:
    score = max(1, min(5, int(score)))
    met = carregar_metricas()
    total = int(met.get("feedback_total", 0)) + 1
    media_antiga = float(met.get("feedback_media", 0.0))
    media_nova = ((media_antiga * (total - 1)) + score) / total

    met["feedback_total"] = total
    met["feedback_media"] = media_nova
    eventos = met.get("eventos", [])
    if not isinstance(eventos, list):
        eventos = []
    eventos.append(
        {
            "quando": _agora_iso(),
            "evento": "feedback",
            "score": score,
            "comentario": (comentario or "").strip(),
        }
    )
    met["eventos"] = eventos[-300:]
    met["atualizado_em"] = _agora_iso()
    salvar_json_seguro(ARQUIVO_METRICAS, met)

    perfil = carregar_perfil()
    perfil["feedback_total"] = total
    perfil["feedback_medio"] = media_nova
    salvar_perfil(perfil)

    return {
        "ok": True,
        "score": score,
        "feedback_total": total,
        "feedback_medio": round(media_nova, 2),
    }


def resumo_metricas() -> dict:
    met = carregar_metricas()
    total = int(met.get("chat_total", 0))
    erros = int(met.get("chat_erros", 0))
    taxa = 0.0 if total == 0 else ((total - erros) / total) * 100
    return {
        "chat_total": total,
        "chat_erros": erros,
        "taxa_sucesso_pct": round(taxa, 2),
        "tempo_medio_ms": round(float(met.get("tempo_medio_ms", 0.0)), 2),
        "feedback_total": int(met.get("feedback_total", 0)),
        "feedback_media": round(float(met.get("feedback_media", 0.0)), 2),
        "atualizado_em": met.get("atualizado_em", ""),
    }


def resumo_metricas_recursos() -> dict:
    met = carregar_metricas()
    eventos = met.get("eventos", [])
    if not isinstance(eventos, list):
        eventos = []

    recursos = {
        "voz": {"total": 0, "erros": 0},
        "busca": {"total": 0, "erros": 0},
        "lembretes": {"total": 0, "erros": 0},
        "mercado": {"total": 0, "erros": 0},
        "clima": {"total": 0, "erros": 0},
        "automacoes": {"total": 0, "erros": 0},
        "rag": {"total": 0, "erros": 0},
        "admin": {"total": 0, "erros": 0},
    }

    mapa = {
        "voz": {"voice", "wake_word", "tts"},
        "busca": {"web_search", "search", "orchestrator"},
        "lembretes": {"reminder_add", "reminder_list"},
        "mercado": {"market"},
        "clima": {"weather"},
        "automacoes": {"automation_add", "automation_remove", "automation_list", "automation_exec", "automation_confirm"},
        "rag": {"rag_index", "rag_query"},
        "admin": {"admin", "security", "audit"},
    }

    for ev in eventos:
        if not isinstance(ev, dict):
            continue
        nome = str(ev.get("evento", "")).strip().lower()
        ok = bool(ev.get("ok", True))
        for recurso, keys in mapa.items():
            if nome in keys:
                recursos[recurso]["total"] += 1
                if not ok:
                    recursos[recurso]["erros"] += 1

    for recurso, item in recursos.items():
        total = int(item.get("total", 0))
        erros = int(item.get("erros", 0))
        taxa = 100.0 if total == 0 else ((total - erros) / total) * 100.0
        item["taxa_sucesso_pct"] = round(taxa, 2)
        item["taxa_erro_pct"] = round(100.0 - taxa, 2)
        recursos[recurso] = item

    return {
        "resumo": resumo_metricas(),
        "recursos": recursos,
        "total_eventos_observados": len(eventos),
    }


def gerar_alertas_recomendacoes() -> list[dict]:
    resumo = resumo_metricas()
    recursos = resumo_metricas_recursos().get("recursos", {})
    if not isinstance(recursos, dict):
        recursos = {}

    alertas: list[dict] = []
    if float(resumo.get("taxa_sucesso_pct", 100.0)) < 92.0:
        alertas.append(
            {
                "nivel": "alto",
                "titulo": "Taxa geral de sucesso abaixo do ideal",
                "detalhe": f"Atual: {resumo.get('taxa_sucesso_pct')}%.",
                "recomendacao": "Revisar últimos erros no painel e habilitar fallback para funcionalidades críticas.",
            }
        )

    tempo_medio = float(resumo.get("tempo_medio_ms", 0.0))
    if tempo_medio > 2500:
        alertas.append(
            {
                "nivel": "medio",
                "titulo": "Latência média elevada",
                "detalhe": f"Tempo médio atual: {round(tempo_medio, 2)} ms.",
                "recomendacao": "Ativar cache de consultas e reduzir chamadas externas simultâneas no backend.",
            }
        )

    for nome, stats in recursos.items():
        if not isinstance(stats, dict):
            continue
        total = int(stats.get("total", 0))
        taxa = float(stats.get("taxa_sucesso_pct", 100.0))
        if total >= 5 and taxa < 85:
            alertas.append(
                {
                    "nivel": "medio",
                    "titulo": f"Instabilidade no recurso: {nome}",
                    "detalhe": f"Sucesso: {taxa}% em {total} eventos.",
                    "recomendacao": f"Validar configuração do módulo {nome} e habilitar monitoramento detalhado.",
                }
            )

    if not alertas:
        alertas.append(
            {
                "nivel": "info",
                "titulo": "Sistema estável",
                "detalhe": "Nenhum alerta crítico encontrado nas métricas recentes.",
                "recomendacao": "Manter rotação de segredos, backups e auditorias periódicas.",
            }
        )

    return alertas


def gerar_briefing_proativo(cidade: str = "") -> str:
    memoria = carregar_memoria_usuario()
    nome = str(memoria.get("nome_usuario", "")).strip() or "chefe"

    clima = consultar_clima(cidade)
    mercado = formatar_cotacoes_humanas(cotacoes_financeiras())
    lembretes = listar_lembretes()
    pendentes = [l for l in lembretes if not l.get("feito")]

    linhas = [
        f"Bom dia, {nome}. Aqui está seu briefing:",
        f"Clima: {clima}",
        f"Mercado: {mercado}",
    ]

    if pendentes:
        top = pendentes[:4]
        itens = "; ".join([f"{i.get('texto')}" for i in top])
        linhas.append(f"Lembretes pendentes: {itens}")
    else:
        linhas.append("Lembretes pendentes: nenhum no momento.")

    return "\n".join(linhas)


def briefing_automatico_se_necessario() -> str | None:
    perfil = carregar_perfil()
    if not bool(perfil.get("proatividade", True)):
        return None

    hoje = datetime.now().strftime("%Y-%m-%d")
    ultimo = str(perfil.get("ultimo_briefing_data", ""))
    if ultimo == hoje:
        return None

    briefing = gerar_briefing_proativo("")
    perfil["ultimo_briefing_data"] = hoje
    salvar_perfil(perfil)
    return briefing


def _extrair_para_lembrete(texto: str) -> tuple[str, str]:
    raw = (texto or "").strip()
    quando = ""
    m = re.search(r"\b(amanha|amanhã|hoje|as\s+\d{1,2}:\d{2}|\d{1,2}:\d{2})\b", raw, flags=re.IGNORECASE)
    if m:
        quando = m.group(1)
    item = raw
    for pref in ["me lembre de", "lembre", "/lembrar"]:
        if item.lower().startswith(pref):
            item = item[len(pref) :].strip(" :,-")
            break
    return item, quando


def _resposta_ciberseguranca_defensiva(msg: str) -> str | None:
    l = (msg or "").lower()
    gatilhos = ["ciber", "cyber", "hacker", "seguranca", "segurança", "termux", "pentest"]
    if not any(k in l for k in gatilhos):
        return None

    if any(k in l for k in ["invadir", "burlar", "exploit", "roubar", "quebrar senha", "phishing"]):
        return (
            "Eu só posso ajudar com cibersegurança defensiva e uso legal. "
            "Posso te guiar em proteção do celular, hardening, análise de riscos, auditoria autorizada e resposta a incidentes."
        )

    linhas = [
        "Modo cibersegurança defensiva ativado.",
        "Posso ajudar com: hardening Android, privacidade, revisão de permissões, autenticação forte, backup seguro e monitoramento.",
        "No Termux, para uso autorizado, recomendo trilha base:",
        "1) pkg update && pkg upgrade",
        "2) pkg install python git openssh",
        "3) Verificação defensiva de rede/aparelhos apenas com autorização do proprietário.",
        "Se você quiser, eu monto um plano personalizado de segurança para seu dispositivo em etapas.",
    ]
    return "\n".join(linhas)


def orquestrar_consulta(mensagem: str, contexto: dict | None = None) -> dict | None:
    contexto = contexto or {}
    msg = (mensagem or "").strip()
    if not msg:
        return None
    l = msg.lower()
    modo_pesquisa = bool(contexto.get("modo_pesquisa"))

    # Cálculo
    if l.startswith("/calcular") or l.startswith("calcule") or l.startswith("quanto e") or l.startswith("quanto é"):
        expr = re.sub(r"^(\/calcular|calcule|quanto e|quanto é)", "", msg, flags=re.IGNORECASE).strip(" =:")
        calc = calcular_expressao(expr)
        if calc.get("ok"):
            return {"resposta": f"Resultado: {calc.get('resultado')}"}
        web = pesquisar_na_internet(f"como resolver: {expr}")
        if web.get("ok"):
            return {
                "resposta": "Fiquei em dúvida no cálculo, então consultei a web para validar:\n"
                + formatar_resposta_pesquisa(web)
            }
        return {
            "resposta": "Tive dúvida nesse cálculo. Pode me ensinar esse padrão com /ensinar pergunta = resposta."
        }

    # Mercado
    if any(k in l for k in ["cotacao", "cotação", "dolar", "euro", "bitcoin", "ethereum", "mercado"]):
        return {"resposta": formatar_cotacoes_humanas(cotacoes_financeiras())}

    # Clima
    if any(k in l for k in ["clima", "tempo", "temperatura"]):
        cidade = ""
        m = re.search(r"(?:em|de)\s+([a-zA-ZÀ-ÿ' -]{2,40})$", msg, flags=re.IGNORECASE)
        if m:
            cidade = m.group(1).strip()
        return {"resposta": consultar_clima(cidade)}

    # Lembretes
    if l.startswith("/lembrar") or "me lembre" in l or "lembre" in l:
        texto, quando = _extrair_para_lembrete(msg)
        out = adicionar_lembrete(texto, quando=quando)
        if out.get("ok"):
            return {"resposta": f"Lembrete salvo: {out['item'].get('texto')}"}
        return {"resposta": "Não consegui salvar lembrete. Pode repetir com mais detalhes?"}

    if l in {"/lembretes", "listar lembretes", "meus lembretes"}:
        itens = listar_lembretes()
        if not itens:
            return {"resposta": "Você não tem lembretes salvos."}
        linhas = [f"{i + 1}. {x.get('texto')}" for i, x in enumerate(itens[-12:])]
        return {"resposta": "Seus lembretes:\n" + "\n".join(linhas)}

    # Cibersegurança defensiva / Termux
    ciber = _resposta_ciberseguranca_defensiva(msg)
    if ciber:
        return {"resposta": ciber}

    # Pesquisa inteligente (web)
    if deve_acionar_pesquisa_web(msg, modo_pesquisa=modo_pesquisa):
        consulta = extrair_consulta_pesquisa_web(msg)
        if len(consulta) >= 3:
            pesquisa = pesquisar_na_internet(consulta)
            if pesquisa.get("ok"):
                return {"resposta": formatar_resposta_pesquisa(pesquisa)}
            if modo_pesquisa:
                return {
                    "resposta": "Estou com o modo pesquisa ativo, mas não achei fontes boas para essa pergunta agora. "
                    "Se quiser, reformule o tema ou peça um recorte mais específico."
                }
            return {
                "resposta": "Não achei fontes confiáveis agora. Se quiser, me ensine essa resposta para eu aprender."
            }

    return None


def explicar_orquestrador() -> str:
    return (
        "Orquestrador ativo: eu avalio intenção e escolho automaticamente ferramentas de cálculo, pesquisa web, "
        "clima, mercado, lembretes e memória adaptativa antes de cair na resposta genérica."
    )

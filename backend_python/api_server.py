from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.admin import (
    autenticar_admin,
    configurar_admin,
    configurar_admin_2fa,
    explicacao_completa_admin,
    gerar_codigo_2fa_admin,
    rotacionar_segredo_2fa,
    status_admin,
)
from core.agente import eh_pedido_de_agente, executar_agente, processar_confirmacao_agente, planejar_objetivo
from core.despertador import (
    configurar_despertador,
    desativar_despertador,
    disparar_despertador,
    iniciar_monitor_despertador,
    status_despertador,
)
from core.jarvis_fase2 import (
    enfileirar_tarefa,
    iniciar_runtime as iniciar_runtime_fase2,
    ligar_fase2,
    desligar_fase2,
    limpar_fila,
    listar_fila,
    relatorio_agora,
    status_fase2,
)
from core.backup_drive import criar_projeto_drive, restaurar_backup_drive, sincronizar_backup_drive, status_backup_drive
from core.assistente_plus import (
    adicionar_lembrete,
    aprender_gostos_por_mensagem,
    calcular_expressao,
    consultar_clima,
    consultar_clima_por_coordenadas,
    cotacoes_financeiras,
    formatar_cotacoes_humanas,
    formatar_resposta_pesquisa,
    listar_lembretes,
    pesquisar_na_internet,
    resumo_adaptacao_usuario,
)
from core.nova_unica import (
    aplicar_identidade_nova,
    atualizar_perfil_por_interacao,
    briefing_automatico_se_necessario,
    carregar_perfil,
    explicar_orquestrador,
    gerar_briefing_proativo,
    orquestrar_consulta,
    registrar_feedback,
    registrar_metrica,
    resumo_metricas,
    resumo_metricas_recursos,
    gerar_alertas_recomendacoes,
)
from core.notion_projects import (
    criar_projeto_notion,
    interpretar_pedido_criacao_projeto,
    notion_disponivel,
    provider_padrao_projeto,
)
from core.aprendizado_admin import (
    listar_aprendizados,
    salvar_aprendizado as salvar_aprendizado_admin,
)
from core.memoria import carregar_memoria_usuario, formatar_memoria_usuario, salvar_memoria_usuario, registrar_interacao_usuario
from core.painel_admin import (
    adicionar_usuario,
    atualizar_config_painel,
    atualizar_usuario,
    carregar_config_painel,
    listar_usuarios,
    remover_usuario,
)
from core.pesquisa import gerar_pesquisa_wikipedia
from core.respostas import carregar_aprendizado, detectar_intencao, extrair_nome_usuario, responder, salvar_aprendizado
from core.telegram_envio import enviar_mensagem_telegram
from core.security_audit import auditoria_humana, executar_auditoria_seguranca, obter_historico_auditoria
from core.premium_memory import (
    aprender_de_mensagem as premium_aprender,
    atualizar_perfil as premium_atualizar_perfil,
    exportar_perfis as premium_exportar_perfis,
    importar_perfis as premium_importar_perfis,
    obter_perfil as premium_obter_perfil,
    personalizar_resposta_por_contexto as premium_personalizar_resposta,
)
from core.rag_local import consultar_rag, reindexar_documentos, registrar_feedback_rag, estatisticas_feedback_rag
from core.automacoes_seguras import (
    adicionar_rotina,
    detectar_rotina_disparada,
    executar_rotina,
    listar_rotinas,
    processar_confirmacao_rotina,
    remover_rotina,
)
from core.voz_neural_api import sintetizar_neural_base64
from core.voz import falar
from core.agent_observability import registrar_trace, listar_traces, resumo_traces
from core.runtime_guard import checar_rate_limit, validar_token, token_api_configurado
from core.autonomia_runtime import (
    atualizar_autonomia,
    ler_config_autonomia,
    solicitar_execucao_autonoma,
    status_autonomia,
    status_sistema_detalhado,
)
from core.session_audit import listar_auditoria_sessao, validar_cadeia_auditoria, registrar_evento_sessao
from core.ops_status import status_operacional
from core.document_analysis import analisar_documento_base64
from core.approval_flow import listar_aprovacoes, decidir_aprovacao
from core.jarvis_chat_bridge import (
    jarvis_status_snapshot,
    process_pending_tool_confirmation,
    try_jarvis_tool_flow,
)
from core.orchestrator import get_default_orchestrator
from core.memoria_assuntos import aprender_assuntos, perfil_assuntos, dica_contextual_para_pergunta
from core.help_center import ajuda_texto_humano, ajuda_topicos
from routes.chat_routes import handle_chat_post
from routes.knowledge_routes import (
    handle_knowledge_delete,
    handle_knowledge_get,
    handle_knowledge_post,
    handle_knowledge_put,
)


def _novo_contexto():
    memoria = carregar_memoria_usuario()
    return {
        "nome_usuario": memoria.get("nome_usuario", ""),
        "idioma_preferido": memoria.get("idioma_preferido", "pt"),
        "tratamento": memoria.get("tratamento", ""),
        "modo_pesquisa": bool(memoria.get("modo_pesquisa", False)),
        "ultima_intencao": "",
        "confirmacao_pendente": None,
        "rotina_pendente": None,
        "jarvis_tool_pending": None,
        "admin_autenticado": False,
        "admin_usuario": "",
    }


CONTEXTO = _novo_contexto()
API_TTS_SERVIDOR_ATIVO = os.getenv("NOVA_API_SERVER_TTS", "0").strip().lower() in {"1", "true", "on", "sim", "yes"}


def sincronizar_memoria():
    memoria = carregar_memoria_usuario()
    memoria["nome_usuario"] = CONTEXTO.get("nome_usuario", "")
    memoria["idioma_preferido"] = CONTEXTO.get("idioma_preferido", "pt")
    memoria["tratamento"] = CONTEXTO.get("tratamento", "")
    memoria["modo_pesquisa"] = bool(CONTEXTO.get("modo_pesquisa", False))
    salvar_memoria_usuario(memoria)


def _exemplos_criacao_projeto() -> str:
    return (
        "Exemplos por voz ou texto:\n"
        "- Nova, crie um novo projeto chamado Atlas Comercial\n"
        "- Nova, abre um projeto novo CRM Interno\n"
        "- Nova, crie um projeto chamado Atlas Comercial na área Comercial com prioridade Alta\n"
        "- Novo projeto \"Planejamento Q4\"\n"
        "- /projeto Assistente Financeiro IA\n"
        "- /notion projeto Roadmap 2026"
    )


def _criar_projeto_remoto(
    nome_projeto: str,
    descricao: str = "",
    provider: str = "",
    details: dict[str, str] | None = None,
) -> tuple[str, bool, dict | str]:
    destino = (provider or "").strip().lower() or provider_padrao_projeto()
    if destino == "notion":
        ok, payload = criar_projeto_notion(nome_projeto, description=descricao, details=details)
        return "notion", ok, payload

    ok, payload = criar_projeto_drive(nome_projeto=nome_projeto, descricao=descricao)
    return "drive", ok, payload


def _formatar_resposta_projeto(provider: str, payload: dict) -> str:
    if provider == "notion":
        base = (
            f"Projeto criado no Notion: {payload.get('project_name')}.\n"
            f"Página: {payload.get('page_url') or payload.get('page_id')}"
        )
        extras = []
        filled_fields = payload.get("filled_fields") or []
        if isinstance(filled_fields, list) and filled_fields:
            extras.append("Campos preenchidos: " + ", ".join(str(item) for item in filled_fields))
        warnings = payload.get("warnings") or []
        if isinstance(warnings, list) and warnings:
            extras.append("Observações: " + " | ".join(str(item) for item in warnings))
        if extras:
            return base + "\n" + "\n".join(extras)
        return base

    return (
        f"Projeto criado no Google Drive: {payload.get('folder_name')}.\n"
        f"Pasta: {payload.get('folder_link') or payload.get('folder_id')}\n"
        f"Arquivo de plano: {payload.get('file_link') or payload.get('file_id')}"
    )


def _cmd_admin(texto):
    partes = texto.strip().split()
    if len(partes) == 1:
        return (
            "Comandos admin: /admin login <usuario> <senha> [2fa] | /admin logout | /admin status | "
            "/admin explicar | /admin configurar <usuario> <senha> | "
            "/admin 2fa status|ligar|desligar|obrigatorio on|off|codigo|rotacionar | "
            "/admin despertador status|ligar|desligar|testar"
        )

    acao = partes[1].lower()
    if acao == "login":
        if len(partes) < 4:
            return "Use /admin login <usuario> <senha> [codigo_2fa]."
        codigo_2fa = partes[4] if len(partes) >= 5 else ""
        if autenticar_admin(partes[2], partes[3], codigo_2fa=codigo_2fa):
            CONTEXTO["admin_autenticado"] = True
            CONTEXTO["admin_usuario"] = partes[2]
            return f"Login admin confirmado para {partes[2]}."
        return "Credenciais admin inválidas (ou 2FA obrigatório/incorreto)."

    if acao == "logout":
        CONTEXTO["admin_autenticado"] = False
        CONTEXTO["admin_usuario"] = ""
        return "Sessão admin encerrada."

    if acao in {"status", "explicar", "configurar", "despertador", "jarvis2", "drivebackup", "2fa"} and not CONTEXTO.get("admin_autenticado"):
        return "Comando restrito. Faça /admin login primeiro."

    if acao == "status":
        return status_admin()
    if acao == "explicar":
        return explicacao_completa_admin()
    if acao == "configurar":
        if len(partes) < 4:
            return "Use /admin configurar <usuario> <senha>."
        ok, msg = configurar_admin(partes[2], partes[3])
        if ok:
            CONTEXTO["admin_usuario"] = partes[2]
        return msg

    if acao == "2fa":
        if len(partes) < 3:
            return "Use /admin 2fa status|ligar|desligar|obrigatorio on|off|codigo|rotacionar"
        sub = partes[2].lower()
        if sub == "status":
            ok, payload = gerar_codigo_2fa_admin()
            if ok:
                return f"2FA ativo. Código atual (teste local): {payload}"
            return str(payload)
        if sub == "ligar":
            configurar_admin_2fa(True)
            return "2FA ativado. Próximo login: /admin login <usuario> <senha> <codigo_2fa>."
        if sub == "desligar":
            configurar_admin_2fa(False)
            return "2FA desativado."
        if sub == "codigo":
            ok, payload = gerar_codigo_2fa_admin()
            return f"Código 2FA atual: {payload}" if ok else str(payload)
        if sub == "rotacionar":
            ok, payload = rotacionar_segredo_2fa()
            return str(payload)
        if sub == "obrigatorio":
            if len(partes) < 4:
                return "Use /admin 2fa obrigatorio on|off"
            flag = partes[3].lower().strip()
            if flag in {"on", "ligar", "sim", "true", "1"}:
                from core.admin import carregar_config_admin
                from core.seguranca import salvar_json_seguro
                from core.admin import ARQUIVO_ADMIN

                cfg = carregar_config_admin()
                cfg["admin_2fa_required"] = True
                salvar_json_seguro(ARQUIVO_ADMIN, cfg)
                registrar_evento_sessao("2fa_required_on", usuario=str(cfg.get("usuario_admin", "")), ok=True)
                return "2FA obrigatório ativado para login admin."
            if flag in {"off", "desligar", "nao", "não", "false", "0"}:
                from core.admin import carregar_config_admin
                from core.seguranca import salvar_json_seguro
                from core.admin import ARQUIVO_ADMIN

                cfg = carregar_config_admin()
                cfg["admin_2fa_required"] = False
                salvar_json_seguro(ARQUIVO_ADMIN, cfg)
                registrar_evento_sessao("2fa_required_off", usuario=str(cfg.get("usuario_admin", "")), ok=True)
                return "2FA obrigatório desativado."
            return "Valor inválido. Use on|off."
        return "Subcomando 2FA inválido."

    if acao == "despertador":
        if len(partes) < 3:
            return "Use /admin despertador status|ligar HH:MM [cidade] [nome]|desligar|testar"
        sub = partes[2].lower()
        if sub == "status":
            return status_despertador()
        if sub == "desligar":
            return desativar_despertador()
        if sub == "testar":
            _, msg = disparar_despertador(falar_callback=falar, forcar=True)
            return msg
        if sub == "ligar":
            if len(partes) < 4:
                return "Use /admin despertador ligar HH:MM [cidade] [nome]."
            hora = partes[3]
            cidade = partes[4] if len(partes) >= 5 else None
            nome = " ".join(partes[5:]) if len(partes) >= 6 else None
            ok, msg = configurar_despertador(hora=hora, cidade=cidade, saudacao_nome=nome, ativo=True)
            if ok:
                iniciar_monitor_despertador(falar_callback=falar)
            return msg
        return "Subcomando de despertador não reconhecido."

    if acao == "jarvis2":
        if len(partes) < 3:
            return (
                "Use /admin jarvis2 status|ligar [intervalo]|desligar|enfileirar <objetivo>|"
                "fila|limpar|relatorio"
            )
        sub = partes[2].lower()
        if sub == "status":
            return status_fase2()
        if sub == "ligar":
            intervalo = 30
            if len(partes) >= 4:
                try:
                    intervalo = int(partes[3])
                except ValueError:
                    intervalo = 30
            iniciar_runtime_fase2()
            return ligar_fase2(intervalo)
        if sub == "desligar":
            return desligar_fase2()
        if sub == "enfileirar":
            objetivo = " ".join(partes[3:]).strip()
            ok, msg = enfileirar_tarefa(objetivo, origem="admin_api")
            return msg
        if sub == "fila":
            return listar_fila()
        if sub == "limpar":
            return limpar_fila()
        if sub == "relatorio":
            return relatorio_agora()
        return "Subcomando jarvis2 não reconhecido."

    if acao == "drivebackup":
        if len(partes) < 3:
            return "Use /admin drivebackup status|sincronizar|restaurar"
        sub = partes[2].lower()
        if sub == "status":
            return status_backup_drive()
        if sub == "sincronizar":
            ok, msg = sincronizar_backup_drive()
            return msg
        if sub == "restaurar":
            ok, msg = restaurar_backup_drive()
            return msg
        return "Subcomando drivebackup não reconhecido."

    return "Comando admin não reconhecido."


def processar_mensagem(user):
    inicio = time.perf_counter()
    user = (user or "").strip()
    CONTEXTO["idioma_preferido"] = "pt"

    def ret(msg, ok=True, evento="chat"):
        registrar_interacao_usuario(user, msg)
        duracao_ms = (time.perf_counter() - inicio) * 1000.0
        try:
            registrar_metrica(evento, duracao_ms, ok=ok)
        except Exception:
            pass
        try:
            registrar_trace(
                route="/chat",
                mensagem=user,
                resposta=msg,
                evento=evento,
                duracao_ms=duracao_ms,
                ok=ok,
                contexto=CONTEXTO,
            )
        except Exception:
            pass
        return msg

    if not user:
        return ret("Mensagem vazia.")

    aprender_gostos_por_mensagem(user)
    try:
        aprender_assuntos(texto=user, origem="chat_user")
    except Exception:
        pass
    premium_aprender(CONTEXTO.get("nome_usuario", "") or "default", user)

    def aprender_de_pesquisa(consulta: str, resumo: str, fontes: list[str] | None = None) -> None:
        consulta_limpa = (consulta or "").strip()
        resumo_limpo = (resumo or "").strip()
        fontes = fontes or []
        if not consulta_limpa or not resumo_limpo:
            return
        try:
            salvar_aprendizado_admin(
                f"pesquisa sobre {consulta_limpa}",
                resumo_limpo,
                categoria="pesquisa_web",
            )
            salvar_aprendizado_admin(
                f"o que foi pesquisado sobre {consulta_limpa}",
                resumo_limpo,
                categoria="pesquisa_web",
            )
            if fontes:
                salvar_aprendizado_admin(
                    f"fontes da pesquisa sobre {consulta_limpa}",
                    ", ".join(fontes),
                    categoria="pesquisa_web",
                )
            aprender_assuntos(
                texto=f"{consulta_limpa}\n{resumo_limpo}\n{' '.join(fontes)}",
                origem="web_search",
                resumo=resumo_limpo,
            )
        except Exception:
            pass

    if CONTEXTO.get("rotina_pendente"):
        resp_rotina = processar_confirmacao_rotina(user, contexto=CONTEXTO)
        if resp_rotina:
            return ret(resp_rotina, evento="automation_confirm")

    rotina = detectar_rotina_disparada(user)
    if rotina:
        if rotina.get("sensivel"):
            CONTEXTO["rotina_pendente"] = {"rule": rotina}
            return ret(
                f"Rotina sensível detectada ({rotina.get('gatilho')}). Confirma execução? Responda sim/não.",
                evento="automation_pending",
            )
        return ret(executar_rotina(rotina), evento="automation_exec")

    if CONTEXTO.get("confirmacao_pendente"):
        resp_confirm = processar_confirmacao_agente(user, contexto=CONTEXTO)
        if resp_confirm:
            return ret(resp_confirm)

    tool_confirm = process_pending_tool_confirmation(user, CONTEXTO, mode="normal")
    if isinstance(tool_confirm, dict) and tool_confirm.get("handled"):
        return ret(str(tool_confirm.get("reply", "")), evento="jarvis_tool_confirm")

    user_l = user.lower().strip()

    if user_l in {"nova", "ei nova", "ok nova", "olá nova", "ola nova"}:
        return ret("Oi chefe. Estou pronta para ajudar.")

    if user_l in {"/help", "help", "ajuda", "menu help", "comandos", "o que voce faz", "o que você faz"}:
        return ret(ajuda_texto_humano(), evento="help")

    if user_l in {
        "/modo pesquisa",
        "modo pesquisa",
        "ativar modo pesquisa",
        "ligar modo pesquisa",
        "pesquisa ligada",
        "ativar pesquisa",
    }:
        CONTEXTO["modo_pesquisa"] = True
        sincronizar_memoria()
        return ret(
            "Modo pesquisa ativado. A partir de agora eu vou priorizar busca na web para perguntas abertas, "
            "explicações, comparações e assuntos atuais. Se quiser voltar ao chat normal, diga '/modo conversa'.",
            evento="search_mode_on",
        )

    if user_l in {
        "/modo conversa",
        "/modo normal",
        "modo conversa",
        "desativar modo pesquisa",
        "desligar modo pesquisa",
        "pesquisa desligada",
        "sair do modo pesquisa",
    }:
        CONTEXTO["modo_pesquisa"] = False
        sincronizar_memoria()
        return ret(
            "Modo pesquisa desativado. Voltei ao fluxo normal de conversa, usando pesquisa só quando você pedir ou quando fizer sentido claro.",
            evento="search_mode_off",
        )

    if any(k in user_l for k in ["quem voce e", "quem você é", "o que voce e", "o que você é"]):
        return ret(
            "Eu sou a NOVA, sua assistente de IA. Minhas funções incluem: chat inteligente, voz, memória por assunto, "
            "aprendizado automático com documentos, RAG com fontes, automações seguras, lembretes e suporte a tarefas autônomas com controle de risco.",
            evento="identity",
        )

    if any(k in user_l for k in ["responda em ingles", "responda em inglês", "fale em ingles", "fale em inglês", "speak english"]):
        return ret("Posso entender termos em inglês, mas para manter sua experiência premium eu vou responder em português.")

    if user_l in {"/orquestrador", "como voce decide", "como você decide"}:
        return ret(explicar_orquestrador())

    if user_l.startswith("/feedback"):
        try:
            partes = user.split(" ", 2)
            score = int(partes[1]) if len(partes) >= 2 else 5
            comentario = partes[2] if len(partes) >= 3 else ""
            out = registrar_feedback(score, comentario=comentario)
            return ret(
                f"Feedback registrado. Nota média atual: {out.get('feedback_medio')} "
                f"({out.get('feedback_total')} avaliações)."
            )
        except Exception:
            return ret("Use /feedback <1-5> <comentário opcional>.")

    if user_l in {"/metricas", "/métricas", "status da assistente"}:
        met = resumo_metricas()
        return ret(
            "Métricas da NOVA:\n"
            f"- Chats: {met.get('chat_total')}\n"
            f"- Taxa de sucesso: {met.get('taxa_sucesso_pct')}%\n"
            f"- Tempo médio: {met.get('tempo_medio_ms')} ms\n"
            f"- Feedback médio: {met.get('feedback_media')} ({met.get('feedback_total')} avaliações)"
        )

    if user_l in {
        "/seguranca",
        "/segurança",
        "/auditoria",
        "/auditoria seguranca",
        "/auditoria segurança",
        "varredura de seguranca",
        "varredura de segurança",
    }:
        return ret(auditoria_humana())

    if user_l in {"/status sistema", "/scan sistema", "/diagnostico sistema", "/diagnóstico sistema"}:
        diag = status_sistema_detalhado()
        sec = diag.get("security", {})
        assist = diag.get("assistant", {})
        soft = diag.get("software", {})
        return ret(
            "Status detalhado do sistema:\n"
            f"- OS: {soft.get('os')}\n"
            f"- Python: {soft.get('python_version')}\n"
            f"- Usuário atual: {assist.get('nome_usuario') or 'não definido'}\n"
            f"- Base de conhecimento: {assist.get('knowledge_total')}\n"
            f"- Usuários admin/painel: {assist.get('users_total')}\n"
            f"- Lembretes: {assist.get('lembretes_total')}\n"
            f"- Score segurança: {sec.get('score')} ({sec.get('nivel')})"
        )

    if user_l in {"/autonomia status", "status autonomia"}:
        auto = status_autonomia()
        ac = auto.get("autonomy", {})
        rt = auto.get("runtime", {})
        return ret(
            "Status de autonomia:\n"
            f"- Ativa: {'sim' if ac.get('autonomia_ativa') else 'não'}\n"
            f"- Política de risco: {ac.get('autonomia_nivel_risco')}\n"
            f"- Liberdade operacional: {ac.get('autonomia_liberdade', 'media')}\n"
            f"- Confirmação sensível: {'sim' if ac.get('autonomia_requer_confirmacao_sensivel') else 'não'}\n"
            f"- Runtime JARVIS2: {'ativo' if rt.get('enabled') else 'desativado'}\n"
            f"- Fila pendente: {rt.get('pending')} | executando: {rt.get('running')}"
        )

    if user_l in {"/autonomia ligar", "ligar autonomia"}:
        auto = atualizar_autonomia(ativa=True)
        return ret(
            f"Modo autonomia ativado. Política de risco atual: {auto.get('autonomia_nivel_risco')}."
        )

    if user_l in {"/autonomia desligar", "desligar autonomia"}:
        atualizar_autonomia(ativa=False)
        return ret("Modo autonomia desativado.")

    if user_l.startswith("/autonomia risco "):
        nivel = user_l.replace("/autonomia risco ", "").strip()
        auto = atualizar_autonomia(nivel_risco=nivel)
        return ret(
            f"Política de risco atualizada para: {auto.get('autonomia_nivel_risco')}."
        )

    if user_l.startswith("/autonomia liberdade "):
        valor = user_l.replace("/autonomia liberdade ", "").strip()
        auto = atualizar_autonomia(liberdade=valor)
        return ret(
            f"Liberdade operacional atualizada para: {auto.get('autonomia_liberdade', 'media')}."
        )

    if user_l.startswith("/briefing") or "briefing" == user_l:
        cidade = ""
        partes = user.split(" ", 1)
        if len(partes) > 1:
            cidade = partes[1].strip()
        return ret(gerar_briefing_proativo(cidade=cidade))

    if user.startswith("/ensinar"):
        try:
            _, conteudo = user.split(" ", 1)
            pergunta, resposta_txt = conteudo.split("=", 1)
            total = salvar_aprendizado(pergunta.strip(), resposta_txt.strip())
            return ret(f"Aprendi! ({total} respostas salvas).")
        except Exception:
            return ret("Use /ensinar pergunta = resposta.")

    if user.startswith("/rag reindex"):
        try:
            partes = user.split(" ", 2)
            paths = []
            if len(partes) >= 3 and partes[2].strip():
                paths = [p.strip() for p in partes[2].split(",") if p.strip()]
            out = reindexar_documentos(paths if paths else None)
            return ret(
                f"RAG reindexado. Arquivos: {out.get('indexed_files')} | Chunks: {out.get('indexed_chunks')}",
                evento="rag_index",
            )
        except Exception:
            return ret("Use /rag reindex [arquivo1,arquivo2,...]", ok=False, evento="rag_index")

    if user.startswith("/rag "):
        pergunta = user[5:].strip()
        out = consultar_rag(pergunta)
        if out.get("ok"):
            fontes = ", ".join(out.get("sources", []))
            return ret(
                f"{out.get('answer', '')}\n\nFontes: {fontes}",
                evento="rag_query",
            )
        return ret("RAG sem resultado. Reindexe com /rag reindex.", ok=False, evento="rag_query")

    if user.startswith("/rotina adicionar "):
        try:
            payload = user[len("/rotina adicionar ") :].strip()
            gat, resto = payload.split("=>", 1)
            gat = gat.strip()
            sensivel = " sensivel" in resto.lower() or " sensível" in resto.lower()
            resto = resto.replace(" sensivel", "").replace(" sensível", "").strip()
            tipo, valor = resto.split(":", 1)
            rule = adicionar_rotina(gat, tipo.strip(), valor.strip(), sensivel=sensivel)
            return ret(f"Rotina criada ({rule.get('id')}).", evento="automation_add")
        except Exception:
            return ret(
                "Use /rotina adicionar gatilho => responder:mensagem [sensivel] ou lembrete:texto",
                ok=False,
                evento="automation_add",
            )

    if user_l in {"/rotina listar", "listar rotinas"}:
        rules = listar_rotinas()
        if not rules:
            return ret("Nenhuma rotina cadastrada.", evento="automation_list")
        linhas = []
        for r in rules[-20:]:
            linhas.append(
                f"{r.get('id')} | {r.get('gatilho')} => {r.get('acao_tipo')} | sensível={r.get('sensivel')} | ativo={r.get('ativo')}"
            )
        return ret("Rotinas:\n" + "\n".join(linhas), evento="automation_list")

    if user.startswith("/rotina remover "):
        rid = user[len("/rotina remover ") :].strip()
        ok_rm = remover_rotina(rid)
        if ok_rm:
            return ret("Rotina removida.", evento="automation_remove")
        return ret("Rotina não encontrada.", ok=False, evento="automation_remove")

    if user.startswith("/google"):
        try:
            _, consulta = user.split(" ", 1)
            pesquisa = pesquisar_na_internet(consulta)
            if pesquisa.get("ok"):
                fontes = pesquisa.get("fontes", [])
                aprender_de_pesquisa(consulta, str(pesquisa.get("resumo", "")), fontes)
                return ret(formatar_resposta_pesquisa(pesquisa), evento="web_search")
            return ret(
                "Não consegui pesquisar agora. Se quiser, me ensine essa resposta usando /ensinar pergunta = resposta."
            )
        except Exception:
            return ret("Use /google algo.", ok=False, evento="web_search")

    if user_l.startswith("pesquisar ") or user_l.startswith("pesquise ") or user_l.startswith("buscar ") or user_l.startswith("busque "):
        consulta = re.sub(r"^(pesquisar|pesquise|buscar|busque)\s+", "", user, flags=re.IGNORECASE).strip(" :,-")
        if consulta:
            resultado = pesquisar_na_internet(consulta)
            if resultado.get("ok"):
                fontes = resultado.get("fontes", [])
                aprender_de_pesquisa(consulta, str(resultado.get("resumo", "")), fontes)
                return ret(formatar_resposta_pesquisa(resultado), evento="web_search")
        return ret("Não consegui encontrar agora. Se quiser, me ensine essa resposta e eu aprendo.", ok=False, evento="web_search")

    if any(k in user_l for k in ["pesquise na internet", "procure na internet", "buscar na internet", "pesquise sobre", "procure sobre"]):
        consulta = user
        consulta = re.sub(r"^(pesquise|procure|buscar|busque)(\s+na internet|\s+sobre)?", "", consulta, flags=re.IGNORECASE).strip(" :,-")
        resultado = pesquisar_na_internet(consulta)
        if resultado.get("ok"):
            fontes = resultado.get("fontes", [])
            aprender_de_pesquisa(consulta, str(resultado.get("resumo", "")), fontes)
            return ret(formatar_resposta_pesquisa(resultado), evento="web_search")
        return ret("Não consegui encontrar agora. Se quiser, me ensine essa resposta e eu aprendo.", ok=False, evento="web_search")

    if user_l.startswith("/lembrar ") or user_l.startswith("me lembre") or user_l.startswith("lembre-me"):
        texto = user
        for pref in ["/lembrar", "me lembre de", "me lembre", "lembre-me de", "lembre-me"]:
            if texto.lower().startswith(pref):
                texto = texto[len(pref) :].strip(" :,-")
                break
        def _parse_quando(frase: str) -> str:
            f = (frase or "").strip()
            now = datetime.now()

            m_iso = re.search(r"\b(\d{4}-\d{2}-\d{2})[ T](\d{1,2}:\d{2})\b", f)
            if m_iso:
                dt = datetime.strptime(f"{m_iso.group(1)} {m_iso.group(2)}", "%Y-%m-%d %H:%M")
                return dt.isoformat(timespec="minutes")

            m_br = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2})\b", f)
            if m_br:
                d = m_br.group(1).split("/")
                dd, mm = int(d[0]), int(d[1])
                yy = int(d[2]) if len(d[2]) == 4 else int(f"20{d[2]}")
                dt = datetime.strptime(f"{yy:04d}-{mm:02d}-{dd:02d} {m_br.group(2)}", "%Y-%m-%d %H:%M")
                return dt.isoformat(timespec="minutes")

            m_amanha = re.search(r"\bamanh[ãa]\b.*?\b(\d{1,2}:\d{2})\b", f, flags=re.IGNORECASE)
            if m_amanha:
                dt = (now + timedelta(days=1)).replace(
                    hour=int(m_amanha.group(1).split(":")[0]),
                    minute=int(m_amanha.group(1).split(":")[1]),
                    second=0,
                    microsecond=0,
                )
                return dt.isoformat(timespec="minutes")

            m_hoje = re.search(r"\bhoje\b.*?\b(\d{1,2}:\d{2})\b", f, flags=re.IGNORECASE)
            if m_hoje:
                hh, mi = [int(x) for x in m_hoje.group(1).split(":")]
                dt = now.replace(hour=hh, minute=mi, second=0, microsecond=0)
                return dt.isoformat(timespec="minutes")

            m_hora = re.search(r"\b(\d{1,2}:\d{2})\b", f)
            if m_hora:
                hh, mi = [int(x) for x in m_hora.group(1).split(":")]
                dt = now.replace(hour=hh, minute=mi, second=0, microsecond=0)
                if dt <= now:
                    dt = dt + timedelta(days=1)
                return dt.isoformat(timespec="minutes")
            return ""

        quando = _parse_quando(texto)
        if not quando:
            return ret(
                "Para criar lembrete com notificação, me diga data e hora. Ex: '/lembrar pagar conta 13/04/2026 09:30'.",
                ok=False,
                evento="reminder_add",
            )
        item = adicionar_lembrete(texto, quando=quando)
        if item.get("ok"):
            return ret(f"Lembrete salvo, chefe: {item['item'].get('texto')}", evento="reminder_add")
        return ret("Não consegui salvar o lembrete. Me diga exatamente o que devo lembrar.", ok=False, evento="reminder_add")

    if user_l in {"/lembretes", "listar lembretes", "meus lembretes"}:
        lembretes = listar_lembretes()
        if not lembretes:
            return ret("Você ainda não tem lembretes salvos.")
        linhas = []
        for i, item in enumerate(lembretes[-12:], start=1):
            quando = item.get("quando") or "sem horário definido"
            linhas.append(f"{i}. {item.get('texto')} ({quando})")
        return ret("Seus lembretes:\n" + "\n".join(linhas), evento="reminder_list")

    if any(k in user_l for k in ["cotacao", "cotação", "dolar", "euro", "bitcoin", "ethereum", "mercado financeiro"]):
        return ret(formatar_cotacoes_humanas(cotacoes_financeiras()), evento="market")

    if any(k in user_l for k in ["clima", "tempo agora", "temperatura"]):
        cidade = ""
        m = re.search(r"(?:em|de)\s+([a-zA-ZÀ-ÿ' -]{2,40})$", user, flags=re.IGNORECASE)
        if m:
            cidade = m.group(1).strip()
        return ret(consultar_clima(cidade), evento="weather")

    if user_l.startswith("/calcular ") or user_l.startswith("calcule ") or user_l.startswith("quanto e "):
        expr = user
        for pref in ["/calcular", "calcule", "quanto e", "quanto é"]:
            if expr.lower().startswith(pref):
                expr = expr[len(pref) :].strip(" =:")
                break
        calc = calcular_expressao(expr)
        if calc.get("ok"):
            return ret(f"Resultado: {calc.get('resultado')}", evento="calc")
        pesquisa = pesquisar_na_internet(f"resolver expressão matemática: {expr}")
        if pesquisa.get("ok"):
            aprender_de_pesquisa(
                f"resolver expressão matemática: {expr}",
                str(pesquisa.get("resumo", "")),
                pesquisa.get("fontes", []),
            )
            return ret(
                "Não consegui resolver internamente com total confiança, então pesquisei para confirmar:\n"
                + formatar_resposta_pesquisa(pesquisa),
                evento="calc",
            )
        return ret(
            "Tive dúvida nesse cálculo. Se quiser, me mande a expressão com mais contexto ou me ensine como resolver esse padrão.",
            ok=False,
            evento="calc",
        )

    pedido_projeto = interpretar_pedido_criacao_projeto(user)
    if pedido_projeto.matched:
        nome_projeto = (pedido_projeto.project_name or "").strip()
        provider = pedido_projeto.provider or provider_padrao_projeto()
        if provider == "notion" and pedido_projeto.explicit_provider and not notion_disponivel():
            return ret(
                "Você pediu para criar no Notion, mas a integração ainda não está configurada.\n"
                "Defina NOVA_NOTION_TOKEN e NOVA_NOTION_PROJECTS_DATA_SOURCE_ID, "
                "NOVA_NOTION_PROJECTS_DATABASE_ID ou NOVA_NOTION_PROJECTS_PAGE_ID.\n\n"
                + _exemplos_criacao_projeto(),
                ok=False,
                evento="notion_project",
            )
        if len(nome_projeto) < 2:
            destino = "Notion" if provider == "notion" else "Google Drive"
            return ret(
                f"Me diga o nome do projeto para eu criar no {destino}.\n\n" + _exemplos_criacao_projeto(),
                ok=False,
                evento="project_intent",
            )
        provider_usado, ok, payload = _criar_projeto_remoto(
            nome_projeto,
            descricao=f"Projeto solicitado por {CONTEXTO.get('nome_usuario') or 'usuário'}: {nome_projeto}",
            provider=provider,
            details={
                "description": pedido_projeto.description,
                "area": pedido_projeto.area,
                "priority": pedido_projeto.priority,
                "responsible": pedido_projeto.responsible,
                "link": pedido_projeto.link,
            },
        )
        if ok and isinstance(payload, dict):
            return ret(
                _formatar_resposta_projeto(provider_usado, payload),
                evento=f"{provider_usado}_project",
            )
        return ret(str(payload), ok=False, evento=f"{provider_usado}_project")

    # Orquestrador inteligente automático para perguntas mais livres.
    orquestrado = orquestrar_consulta(user, contexto=CONTEXTO)
    if isinstance(orquestrado, dict) and orquestrado.get("resposta"):
        return ret(str(orquestrado.get("resposta")), evento="orchestrator")

    jarvis_tool = try_jarvis_tool_flow(user, CONTEXTO, mode="normal")
    if isinstance(jarvis_tool, dict) and jarvis_tool.get("reply"):
        evento = "jarvis_tool_pending" if jarvis_tool.get("approval_needed") else "jarvis_tool"
        return ret(str(jarvis_tool.get("reply")), evento=evento)

    if user.startswith("/nome"):
        try:
            _, nome = user.split(" ", 1)
            CONTEXTO["nome_usuario"] = nome.strip().title()
            sincronizar_memoria()
            return ret(f"Beleza, vou te chamar de {CONTEXTO['nome_usuario']}.")
        except Exception:
            return ret("Use /nome SeuNome.")

    if user.startswith("/memoria"):
        return ret(formatar_memoria_usuario(carregar_memoria_usuario()))

    if user.startswith("/admin"):
        return ret(_cmd_admin(user))

    if user.startswith("/nova") or user.startswith("/agente") or eh_pedido_de_agente(user):
        resultado = executar_agente(user, contexto=CONTEXTO)
        CONTEXTO["confirmacao_pendente"] = resultado.get("confirmacao_pendente")
        sincronizar_memoria()
        return ret(resultado.get("mensagem", "Plano executado."))

    nome = extrair_nome_usuario(user)
    if nome:
        CONTEXTO["nome_usuario"] = nome
        sincronizar_memoria()

    intencao = detectar_intencao(user, CONTEXTO)
    CONTEXTO["ultima_intencao"] = intencao
    resposta = responder(user, contexto=CONTEXTO)
    if intencao == "saudacao":
        memoria = carregar_memoria_usuario()
        hora = datetime.now().hour
        if 5 <= hora < 12:
            saud = "Bom dia"
        elif 12 <= hora < 18:
            saud = "Boa tarde"
        else:
            saud = "Boa noite"
        nome = (CONTEXTO.get("nome_usuario") or memoria.get("nome_usuario") or "").strip()
        if nome:
            resposta = f"{saud}, {nome}. Como posso ajudar você agora?"
        else:
            resposta = f"{saud}. Como posso ajudar você agora?"
    if "não entendi" in resposta.lower() or "não consegui entender" in resposta.lower():
        resposta += " Se quiser, me ensine essa resposta com /ensinar pergunta = resposta."
    if any(k in user_l for k in ["programação", "programacao", "api", "agente de ia", "agentes de ia"]):
        resposta += " Eu também posso te ajudar com programação, APIs e arquitetura de agentes de IA."
    if "gosto" in user_l or "me adapte" in user_l or "adapt" in user_l:
        resposta += " " + resumo_adaptacao_usuario()
    briefing = briefing_automatico_se_necessario()
    if briefing and intencao in {"saudacao", "ajuda"}:
        resposta = f"{resposta}\n\n{briefing}"
    try:
        perfil = atualizar_perfil_por_interacao(user, resposta)
        resposta = aplicar_identidade_nova(
            resposta,
            perfil=perfil,
            nome_usuario=CONTEXTO.get("nome_usuario", ""),
        )
    except Exception:
        pass
    # Evita empilhamento de saudações e respostas "coladas" em intents curtas.
    if intencao not in {"saudacao", "agradecimento", "despedida", "continuidade", "como_esta"}:
        try:
            resposta = premium_personalizar_resposta(
                CONTEXTO.get("nome_usuario", "") or "default",
                resposta,
            )
        except Exception:
            pass

    # Só injeta RAG automaticamente em perguntas mais completas para não poluir respostas simples.
    deve_consultar_rag_auto = ("?" in user) or (len(user.split()) >= 5)
    if deve_consultar_rag_auto:
        try:
            rag = consultar_rag(user)
            if rag.get("ok"):
                fontes = ", ".join(rag.get("sources", []))
                snippet = ""
                snippets = rag.get("snippets", [])
                if isinstance(snippets, list) and snippets:
                    snippet = str(snippets[0])[:220]
                resposta = (
                    f"{resposta}\n\nReferências da sua base local: {fontes}\nTrecho: {snippet}"
                )
        except Exception:
            pass
    try:
        dica = dica_contextual_para_pergunta(user)
        if dica and len(user.split()) >= 4:
            resposta = f"{resposta}\n\n{dica}"
    except Exception:
        pass
    if API_TTS_SERVIDOR_ATIVO:
        try:
            falar(resposta)
        except Exception:
            pass
    return ret(resposta)


def _json_body(handler: BaseHTTPRequestHandler):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        raw = handler.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def _bool_ou_none(valor):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        v = valor.strip().lower()
        if v in {"true", "1", "sim", "yes", "on"}:
            return True
        if v in {"false", "0", "nao", "não", "no", "off"}:
            return False
    return None


def _estado_admin():
    conhecimentos = listar_aprendizados()
    usuarios = listar_usuarios()
    config = carregar_config_painel()
    return {
        "knowledge_total": len(conhecimentos),
        "users_total": len(usuarios),
        "knowledge": conhecimentos,
        "users": usuarios,
        "config": config,
    }


def _papel_permitido(role: str, allow: tuple[str, ...]) -> bool:
    r = (role or "").strip().lower()
    if not r:
        return False
    if r == "admin":
        return True
    return r in allow


class NovaHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=HTTPStatus.OK):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _rate_limit_ok(self, route: str) -> bool:
        ip = self.client_address[0] if self.client_address else "unknown"
        limite = 120
        janela = 60
        if route.startswith("/chat"):
            limite = 90
        if route.startswith("/admin") or route.startswith("/security"):
            limite = 30
        ok, retry = checar_rate_limit(chave=f"{ip}:{route}", limite=limite, janela_s=janela)
        if ok:
            return True
        self._send_json(
            {"ok": False, "error": "rate_limited", "retry_after_s": retry},
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )
        return False

    def _token_required_for(self, path: str) -> bool:
        if not token_api_configurado():
            return False
        protegidas = (
            path.startswith("/admin")
            or path.startswith("/security")
            or path.startswith("/backup")
            or path.startswith("/automation")
            or path.startswith("/autonomy")
            or path.startswith("/ops")
            or path.startswith("/approvals")
            or path.startswith("/documents")
            or path.startswith("/rag/index")
            or path.startswith("/rag/feedback")
            or path.startswith("/agent/")
        )
        return protegidas

    def _auth_ok(self, path: str) -> bool:
        if not self._token_required_for(path):
            return True
        if validar_token(self.headers):
            return True
        self._send_json({"ok": False, "error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
        return False

    def _rbac_ok(self, path: str, method: str) -> bool:
        cfg = carregar_config_painel()
        if not bool(cfg.get("rbac_ativo", False)):
            return True

        role = str(self.headers.get("X-User-Role", "") or "").strip().lower()
        user = str(self.headers.get("X-User-Name", "") or "").strip()
        if not role or not user:
            self._send_json(
                {"ok": False, "error": "rbac_identity_required"},
                status=HTTPStatus.FORBIDDEN,
            )
            return False

        usuarios = listar_usuarios()
        valido = False
        for u in usuarios:
            if not bool(u.get("ativo", True)):
                continue
            nome = str(u.get("nome", "")).strip().lower()
            papel = str(u.get("papel", "")).strip().lower()
            if nome == user.lower() and papel == role:
                valido = True
                break
        if not valido:
            self._send_json({"ok": False, "error": "rbac_user_invalid"}, status=HTTPStatus.FORBIDDEN)
            return False

        # Matriz simples de permissões por endpoint.
        if path.startswith("/admin") and not _papel_permitido(role, ("admin",)):
            self._send_json({"ok": False, "error": "rbac_forbidden_admin"}, status=HTTPStatus.FORBIDDEN)
            return False
        if path.startswith("/security") and not _papel_permitido(role, ("admin", "security")):
            self._send_json({"ok": False, "error": "rbac_forbidden_security"}, status=HTTPStatus.FORBIDDEN)
            return False
        if path.startswith("/autonomy/config") and not _papel_permitido(role, ("admin",)):
            self._send_json({"ok": False, "error": "rbac_forbidden_autonomy"}, status=HTTPStatus.FORBIDDEN)
            return False
        if path.startswith("/autonomy/task") and not _papel_permitido(role, ("admin", "operator")):
            self._send_json({"ok": False, "error": "rbac_forbidden_task"}, status=HTTPStatus.FORBIDDEN)
            return False
        if path.startswith("/approvals") and not _papel_permitido(role, ("admin", "security")):
            self._send_json({"ok": False, "error": "rbac_forbidden_approval"}, status=HTTPStatus.FORBIDDEN)
            return False
        if path.startswith("/documents/analyze") and not _papel_permitido(role, ("admin", "operator", "analyst")):
            self._send_json({"ok": False, "error": "rbac_forbidden_documents"}, status=HTTPStatus.FORBIDDEN)
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query or "")
        if not self._rate_limit_ok(path):
            return
        if not self._auth_ok(path):
            return
        if not self._rbac_ok(path, "GET"):
            return

        if path == "/":
            self._send_json(
                {
                    "ok": True,
                    "status": "online",
                    "service": "nova-api",
                    "endpoints": [
                        "/health",
                        "/chat",
                        "/jarvis/status",
                        "/actions/tools",
                        "/memory/recent",
                        "/voice/status",
                        "/market/quotes",
                        "/weather/now",
                        "/system/status",
                        "/autonomy/status",
                        "/ops/status",
                    ],
                }
            )
            return
        if path == "/health":
            self._send_json({"ok": True, "service": "nova-api"})
            return
        if path == "/jarvis/status":
            self._send_json(jarvis_status_snapshot())
            return
        if path == "/actions/tools":
            self._send_json({"ok": True, "tools": get_default_orchestrator().tools.describe()})
            return
        if path == "/voice/status":
            self._send_json(
                {
                    "ok": True,
                    "enabled": False,
                    "phase": "planned",
                    "message": "Voice pipeline scaffolded; use /voice/neural for TTS and Phase 2 for live audio.",
                }
            )
            return
        if path == "/memory/recent":
            user_id = str(query.get("user_id", ["default"])[0] or "default").strip() or "default"
            try:
                limit = int(query.get("limit", ["8"])[0])
            except Exception:
                limit = 8
            items = get_default_orchestrator().memory.search_recent(
                user_id=user_id,
                limit=max(1, min(limit, 50)),
            )
            self._send_json({"ok": True, "items": items, "total": len(items)})
            return
        if path == "/memory/search":
            user_id = str(query.get("user_id", ["default"])[0] or "default").strip() or "default"
            search_query = str(query.get("query", [""])[0] or "").strip()
            try:
                limit = int(query.get("limit", ["8"])[0])
            except Exception:
                limit = 8
            items = get_default_orchestrator().memory.search(
                user_id=user_id,
                query=search_query,
                limit=max(1, min(limit, 50)),
            )
            self._send_json({"ok": True, "items": items, "total": len(items)})
            return
        if path == "/ops/status":
            self._send_json(status_operacional())
            return
        if path == "/approvals":
            status = (query.get("status", [""])[0] or "").strip()
            self._send_json({"ok": True, "items": listar_aprovacoes(status=status)})
            return
        if path == "/system/status":
            self._send_json(status_sistema_detalhado())
            return
        if path == "/backup/export":
            self._send_json(
                {
                    "ok": True,
                    "backup": {
                        "memory": carregar_memoria_usuario(),
                        "knowledge": listar_aprendizados(),
                        "users": listar_usuarios(),
                        "config": carregar_config_painel(),
                        "premium_profiles": premium_exportar_perfis(),
                    },
                }
            )
            return
        if handle_knowledge_get(path=path, send_json=self._send_json):
            return
        if path == "/admin/users":
            usuarios = listar_usuarios()
            self._send_json({"ok": True, "users": usuarios, "total": len(usuarios)})
            return
        if path == "/admin/config":
            self._send_json({"ok": True, "config": carregar_config_painel()})
            return
        if path == "/admin/state":
            self._send_json({"ok": True, "state": _estado_admin()})
            return
        if path == "/insights/profile":
            self._send_json({"ok": True, "profile": carregar_perfil()})
            return
        if path == "/insights/metrics":
            self._send_json({"ok": True, "metrics": resumo_metricas()})
            return
        if path == "/insights/resources":
            self._send_json({"ok": True, "resources": resumo_metricas_recursos()})
            return
        if path == "/insights/alerts":
            self._send_json({"ok": True, "alerts": gerar_alertas_recomendacoes()})
            return
        if path == "/memory/subjects":
            try:
                limit = int((query.get("limit", ["8"])[0] or "8").strip())
            except Exception:
                limit = 8
            self._send_json(perfil_assuntos(limit=limit))
            return
        if path == "/help/topics":
            self._send_json(ajuda_topicos())
            return
        if path == "/observability/traces":
            try:
                limit = int((query.get("limit", ["120"])[0] or "120").strip())
            except Exception:
                limit = 120
            self._send_json({"ok": True, "items": listar_traces(limit=limit)})
            return
        if path == "/observability/summary":
            try:
                janela = int((query.get("window", ["200"])[0] or "200").strip())
            except Exception:
                janela = 200
            self._send_json({"ok": True, "summary": resumo_traces(janela=janela)})
            return
        if path == "/premium/profile":
            user_id = (query.get("user_id", ["default"])[0] or "default").strip()
            self._send_json({"ok": True, "profile": premium_obter_perfil(user_id)})
            return
        if path == "/security/audit":
            self._send_json({"ok": True, "audit": executar_auditoria_seguranca()})
            return
        if path == "/security/audit/history":
            try:
                limit = int((query.get("limit", ["30"])[0] or "30").strip())
            except Exception:
                limit = 30
            self._send_json({"ok": True, "items": obter_historico_auditoria(limit=limit)})
            return
        if path == "/security/session-audit":
            try:
                limit = int((query.get("limit", ["120"])[0] or "120").strip())
            except Exception:
                limit = 120
            self._send_json({"ok": True, "items": listar_auditoria_sessao(limit=limit)})
            return
        if path == "/security/session-audit/verify":
            self._send_json(validar_cadeia_auditoria())
            return
        if path == "/assistant/briefing":
            cidade = (query.get("city", [""])[0] or "").strip()
            self._send_json({"ok": True, "briefing": gerar_briefing_proativo(cidade)})
            return
        if path == "/market/quotes":
            cotacoes = cotacoes_financeiras()
            self._send_json({"ok": cotacoes.get("ok") is True, "quotes": cotacoes})
            return
        if path == "/weather/now":
            cidade = (query.get("city", [""])[0] or "").strip()
            self._send_json({"ok": True, "summary": consultar_clima(cidade)})
            return
        if path == "/weather/by-coords":
            lat_raw = (query.get("lat", [""])[0] or "").strip()
            lon_raw = (query.get("lon", [""])[0] or "").strip()
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
            except Exception:
                self._send_json({"ok": False, "error": "invalid_coords"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": True, "summary": consultar_clima_por_coordenadas(lat, lon)})
            return
        if path == "/location/current":
            memoria = carregar_memoria_usuario()
            self._send_json(
                {
                    "ok": True,
                    "location": {
                        "label": str(memoria.get("ultima_localizacao", "") or ""),
                        "latitude": str(memoria.get("ultima_latitude", "") or ""),
                        "longitude": str(memoria.get("ultima_longitude", "") or ""),
                        "updated_at": str(memoria.get("ultima_localizacao_em", "") or ""),
                    },
                }
            )
            return
        if path == "/reminders":
            lembretes = listar_lembretes()
            self._send_json({"ok": True, "items": lembretes, "total": len(lembretes)})
            return
        if path == "/automation/rules":
            rules = listar_rotinas()
            self._send_json({"ok": True, "rules": rules, "total": len(rules)})
            return
        if path == "/rag/feedback/stats":
            self._send_json(estatisticas_feedback_rag())
            return
        if path == "/autonomy/status":
            self._send_json(status_autonomia())
            return
        if path == "/autonomy/config":
            self._send_json({"ok": True, "config": ler_config_autonomia()})
            return

        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if not self._rate_limit_ok(path):
            return
        if not self._auth_ok(path):
            return
        if not self._rbac_ok(path, "POST"):
            return
        body = _json_body(self)
        if body is None:
            self._send_json({"ok": False, "error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
            return

        if handle_chat_post(
            path=path,
            body=body,
            process_message=processar_mensagem,
            send_json=self._send_json,
        ):
            return

        if path == "/backup/restore":
            backup = body.get("backup", {})
            memory = backup.get("memory", {}) if isinstance(backup, dict) else {}
            if not isinstance(memory, dict):
                self._send_json({"ok": False, "error": "invalid_backup"}, status=HTTPStatus.BAD_REQUEST)
                return
            salvar_memoria_usuario(memory)
            if isinstance(backup, dict):
                if isinstance(backup.get("knowledge"), list):
                    from core.aprendizado_admin import salvar_base_aprendizado

                    salvar_base_aprendizado(backup.get("knowledge", []))
                if isinstance(backup.get("users"), list):
                    from core.seguranca import salvar_json_seguro
                    from core.painel_admin import ARQUIVO_USUARIOS

                    salvar_json_seguro(ARQUIVO_USUARIOS, backup.get("users"))
                if isinstance(backup.get("config"), dict):
                    atualizar_config_painel(**backup.get("config", {}))
                if isinstance(backup.get("premium_profiles"), dict):
                    premium_importar_perfis(backup.get("premium_profiles"))
            self._send_json({"ok": True, "restored": True})
            return

        if path == "/premium/profile":
            user_id = str(body.get("user_id", "default")).strip() or "default"
            profile = body.get("profile", {})
            if not isinstance(profile, dict):
                self._send_json({"ok": False, "error": "invalid_profile"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": True, "profile": premium_atualizar_perfil(user_id, profile)})
            return

        if path == "/memory":
            user_id = str(body.get("user_id", "default")).strip() or "default"
            category = str(body.get("category", "contexto")).strip() or "contexto"
            content = str(body.get("content", "")).strip()
            if not content:
                self._send_json({"ok": False, "error": "content_required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                importance = int(body.get("importance", 1))
            except Exception:
                importance = 1
            scope = str(body.get("scope", "longo_prazo")).strip() or "longo_prazo"
            item = get_default_orchestrator().memory.save(
                user_id=user_id,
                category=category,
                content=content,
                importance=importance,
                scope=scope,
                source="api_server",
            )
            self._send_json({"ok": True, "item": item})
            return

        if path == "/actions/approve":
            user_id = str(body.get("user_id", "default")).strip() or "default"
            tool_name = str(body.get("tool_name", "")).strip()
            params = body.get("params", {})
            prompt_text = str(body.get("prompt_text", "")).strip()
            if not tool_name:
                self._send_json({"ok": False, "error": "tool_name_required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not isinstance(params, dict):
                self._send_json({"ok": False, "error": "invalid_params"}, status=HTTPStatus.BAD_REQUEST)
                return
            result = get_default_orchestrator().execute_tool(
                user_id,
                tool_name,
                params,
                prompt_text=prompt_text,
                mode="normal",
            )
            self._send_json({"ok": True, **result})
            return

        if path == "/rag/index":
            paths = body.get("paths")
            lst = paths if isinstance(paths, list) else None
            out = reindexar_documentos(lst)
            self._send_json({"ok": True, "result": out})
            return

        if path == "/rag/query":
            pergunta = str(body.get("query", "")).strip()
            out = consultar_rag(pergunta)
            status = HTTPStatus.OK if out.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json({"ok": out.get("ok") is True, "result": out}, status=status)
            return

        if path == "/rag/feedback":
            pergunta = str(body.get("query", "")).strip()
            chunk_id = str(body.get("chunk_id", "")).strip()
            try:
                score = int(body.get("score", 1))
            except Exception:
                score = 1
            out = registrar_feedback_rag(pergunta, chunk_id, score=score)
            status = HTTPStatus.OK if out.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json(out, status=status)
            return
        if path == "/autonomy/config":
            ativa = _bool_ou_none(body.get("active"))
            confirmar = _bool_ou_none(body.get("confirm_sensitive"))
            nivel = body.get("risk_level")
            liberdade = body.get("freedom_level")
            out = atualizar_autonomia(
                ativa=ativa,
                nivel_risco=str(nivel).strip().lower() if nivel is not None else None,
                liberdade=str(liberdade).strip().lower() if liberdade is not None else None,
                confirmar_sensivel=confirmar,
            )
            self._send_json({"ok": True, "config": out})
            return
        if path == "/autonomy/task":
            objetivo = str(body.get("objective", "")).strip()
            origem = str(body.get("source", "api")).strip() or "api"
            out = solicitar_execucao_autonoma(objetivo, origem=origem)
            if out.get("error") == "confirmation_required":
                ok, msg = enfileirar_tarefa(objetivo, origem=f"autonomia:{origem}:auto")
                status = HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST
                self._send_json(
                    {
                        "ok": ok,
                        "queued": ok,
                        "message": msg,
                        "autonomy_mode": "full_auto",
                        "note": "Confirmação manual ignorada por configuração de autonomia total.",
                        "risk": out.get("risk", {}),
                    },
                    status=status,
                )
                return
            status = HTTPStatus.OK if out.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json(out, status=status)
            return
        if path == "/approvals/decide":
            req_id = str(body.get("request_id", "")).strip()
            approve = bool(body.get("approve", False))
            approver = str(body.get("approver", "")).strip() or str(
                self.headers.get("X-User-Name", "")
            ).strip()
            note = str(body.get("note", "")).strip()
            out = decidir_aprovacao(req_id, approve=approve, approver=approver, note=note)
            status = HTTPStatus.OK if out.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json(out, status=status)
            return
        if path == "/documents/analyze":
            filename = str(body.get("filename", "")).strip()
            content_b64 = str(body.get("content_base64", "")).strip()
            auto_learn = True
            out = analisar_documento_base64(filename, content_b64, auto_learn=auto_learn)
            status = HTTPStatus.OK if out.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json(out, status=status)
            return

        if path == "/agent/plan":
            objetivo = str(body.get("objective", "")).strip()
            if not objetivo:
                self._send_json({"ok": False, "error": "objective_required"}, status=HTTPStatus.BAD_REQUEST)
                return
            plano = planejar_objetivo(objetivo, contexto=CONTEXTO)
            steps = []
            needs_confirmation = False
            for p in plano:
                item = {
                    "action": getattr(p, "acao", ""),
                    "description": getattr(p, "descricao", ""),
                    "parameters": getattr(p, "parametros", {}),
                    "sensitive": bool(getattr(p, "sensivel", False)),
                }
                if item["sensitive"]:
                    needs_confirmation = True
                steps.append(item)
            self._send_json(
                {
                    "ok": True,
                    "objective": objetivo,
                    "plan": steps,
                    "needs_confirmation": needs_confirmation,
                }
            )
            return

        if path == "/agent/execute":
            objetivo = str(body.get("objective", "")).strip()
            if not objetivo:
                self._send_json({"ok": False, "error": "objective_required"}, status=HTTPStatus.BAD_REQUEST)
                return
            resultado = executar_agente(objetivo, contexto=CONTEXTO)
            CONTEXTO["confirmacao_pendente"] = resultado.get("confirmacao_pendente")
            steps = []
            for p in (resultado.get("plano", []) or []):
                steps.append(
                    {
                        "action": getattr(p, "acao", ""),
                        "description": getattr(p, "descricao", ""),
                        "parameters": getattr(p, "parametros", {}),
                        "status": getattr(p, "status", ""),
                        "output": getattr(p, "saida", ""),
                        "error": getattr(p, "erro", ""),
                        "sensitive": bool(getattr(p, "sensivel", False)),
                    }
                )
            self._send_json(
                {
                    "ok": True,
                    "message": resultado.get("mensagem", ""),
                    "confirmation_pending": resultado.get("confirmacao_pendente"),
                    "plan": steps,
                }
            )
            return

        if path == "/automation/rules":
            try:
                rule = adicionar_rotina(
                    gatilho=str(body.get("trigger", "")),
                    acao_tipo=str(body.get("action_type", "")),
                    acao_valor=str(body.get("action_value", "")),
                    sensivel=bool(body.get("sensitive", False)),
                )
                self._send_json({"ok": True, "rule": rule, "rules": listar_rotinas()})
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if handle_knowledge_post(path=path, body=body, send_json=self._send_json):
            return

        if path == "/admin/users":
            nome = str(body.get("nome", "")).strip()
            papel = str(body.get("papel", "usuario")).strip() or "usuario"
            try:
                user = adicionar_usuario(nome, papel=papel)
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": True, "user": user, "users": listar_usuarios()})
            return

        if path == "/admin/config":
            campos = {}
            if "voz_ativa" in body:
                campos["voz_ativa"] = _bool_ou_none(body.get("voz_ativa"))
            if "voice_neural_hybrid" in body:
                campos["voice_neural_hybrid"] = _bool_ou_none(body.get("voice_neural_hybrid"))
            if "voice_profile" in body:
                campos["voice_profile"] = body.get("voice_profile")
            if "escuta_ativa" in body:
                campos["escuta_ativa"] = _bool_ou_none(body.get("escuta_ativa"))
            if "wake_word" in body:
                campos["wake_word"] = body.get("wake_word")
            if "continuous_wake" in body:
                campos["continuous_wake"] = _bool_ou_none(body.get("continuous_wake"))
            if "push_to_talk_only" in body:
                campos["push_to_talk_only"] = _bool_ou_none(body.get("push_to_talk_only"))
            if "allow_voice_on_lock" in body:
                campos["allow_voice_on_lock"] = _bool_ou_none(body.get("allow_voice_on_lock"))
            if "autonomia_ativa" in body:
                campos["autonomia_ativa"] = _bool_ou_none(body.get("autonomia_ativa"))
            if "autonomia_nivel_risco" in body:
                campos["autonomia_nivel_risco"] = body.get("autonomia_nivel_risco")
            if "autonomia_liberdade" in body:
                campos["autonomia_liberdade"] = body.get("autonomia_liberdade")
            if "autonomia_requer_confirmacao_sensivel" in body:
                campos["autonomia_requer_confirmacao_sensivel"] = _bool_ou_none(
                    body.get("autonomia_requer_confirmacao_sensivel")
                )
            if "rbac_ativo" in body:
                campos["rbac_ativo"] = _bool_ou_none(body.get("rbac_ativo"))
            if "auto_document_learning" in body:
                campos["auto_document_learning"] = _bool_ou_none(body.get("auto_document_learning"))
            if "admin_guard" in body:
                campos["admin_guard"] = _bool_ou_none(body.get("admin_guard"))
            if "telegram_ativo" in body:
                campos["telegram_ativo"] = _bool_ou_none(body.get("telegram_ativo"))
            if "telegram_token" in body:
                campos["telegram_token"] = body.get("telegram_token")
            if "telegram_chat_id" in body:
                campos["telegram_chat_id"] = body.get("telegram_chat_id")
            config = atualizar_config_painel(**campos)
            self._send_json({"ok": True, "config": config})
            return

        if path == "/telegram/send":
            mensagem = str(body.get("message", "")).strip()
            config = carregar_config_painel()
            if not config.get("telegram_ativo"):
                self._send_json({"ok": False, "error": "telegram_disabled"}, status=HTTPStatus.BAD_REQUEST)
                return
            ok, msg = enviar_mensagem_telegram(
                token=str(config.get("telegram_token", "")),
                chat_id=str(config.get("telegram_chat_id", "")),
                mensagem=mensagem,
            )
            status = HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST
            self._send_json({"ok": ok, "message": msg}, status=status)
            return

        if path == "/search/web":
            consulta = str(body.get("query", "")).strip()
            if not consulta:
                self._send_json({"ok": False, "error": "query_required"}, status=HTTPStatus.BAD_REQUEST)
                return
            resultado = pesquisar_na_internet(consulta)
            self._send_json(
                {
                    "ok": resultado.get("ok") is True,
                    "summary": formatar_resposta_pesquisa(resultado) if resultado.get("ok") else resultado.get("resumo", ""),
                    "sources": resultado.get("fontes", []),
                    "links": resultado.get("links", []),
                }
            )
            return

        if path == "/insights/feedback":
            try:
                score = int(body.get("score", 5))
            except Exception:
                score = 5
            comentario = str(body.get("comment", "")).strip()
            out = registrar_feedback(score, comentario=comentario)
            self._send_json(out)
            return

        if path == "/reminders":
            texto = str(body.get("text", "")).strip()
            quando = str(body.get("when", "")).strip()
            if not quando:
                self._send_json(
                    {"ok": False, "error": "when_required", "message": "Informe data/hora para o lembrete."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                datetime.fromisoformat(quando.replace("Z", "+00:00"))
            except Exception:
                self._send_json(
                    {"ok": False, "error": "when_invalid", "message": "Formato de data/hora inválido."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            item = adicionar_lembrete(texto, quando=quando)
            status = HTTPStatus.OK if item.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json(item, status=status)
            return

        if path == "/location/update":
            label = str(body.get("label", "")).strip()
            lat = str(body.get("latitude", "")).strip()
            lon = str(body.get("longitude", "")).strip()
            memoria = carregar_memoria_usuario()
            memoria["ultima_localizacao"] = label
            memoria["ultima_latitude"] = lat
            memoria["ultima_longitude"] = lon
            memoria["ultima_localizacao_em"] = datetime.now().isoformat(timespec="seconds")
            salvar_memoria_usuario(memoria)
            self._send_json(
                {
                    "ok": True,
                    "location": {
                        "label": label,
                        "latitude": lat,
                        "longitude": lon,
                        "updated_at": memoria["ultima_localizacao_em"],
                    },
                }
            )
            return

        if path == "/project/create":
            nome = str(body.get("name", "")).strip()
            descricao = str(body.get("description", "")).strip()
            provider = str(body.get("provider", "")).strip().lower()
            provider_usado, ok, payload = _criar_projeto_remoto(
                nome,
                descricao,
                provider=provider,
                details={
                    "description": descricao,
                    "area": str(body.get("area", "")).strip(),
                    "priority": str(body.get("priority", "")).strip(),
                    "responsible": str(body.get("responsible", "")).strip(),
                    "link": str(body.get("link", "")).strip(),
                },
            )
            status = HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST
            self._send_json(
                {
                    "ok": ok,
                    "provider": provider_usado,
                    "project": payload if ok else None,
                    "error": None if ok else payload,
                },
                status=status,
            )
            return

        if path == "/voice/neural":
            texto = str(body.get("text", "")).strip()
            perfil = str(body.get("voice_profile", "feminina")).strip()
            out = sintetizar_neural_base64(texto, perfil=perfil)
            status = HTTPStatus.OK if out.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json(out, status=status)
            return

        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if not self._rate_limit_ok(path):
            return
        if not self._auth_ok(path):
            return
        if not self._rbac_ok(path, "PUT"):
            return
        body = _json_body(self)
        if body is None:
            self._send_json({"ok": False, "error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
            return

        if handle_knowledge_put(
            path=path,
            body=body,
            bool_ou_none=_bool_ou_none,
            send_json=self._send_json,
        ):
            return

        if path.startswith("/admin/users/"):
            user_id = path.split("/")[-1]
            user = atualizar_usuario(
                user_id=user_id,
                nome=body.get("nome"),
                papel=body.get("papel"),
                ativo=_bool_ou_none(body.get("ativo")),
            )
            if not user:
                self._send_json({"ok": False, "error": "user_not_found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True, "user": user, "users": listar_usuarios()})
            return

        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if not self._rate_limit_ok(path):
            return
        if not self._auth_ok(path):
            return
        if not self._rbac_ok(path, "DELETE"):
            return

        if handle_knowledge_delete(path=path, send_json=self._send_json):
            return

        if path.startswith("/admin/users/"):
            user_id = path.split("/")[-1]
            ok = remover_usuario(user_id)
            if not ok:
                self._send_json({"ok": False, "error": "user_not_found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True, "removed": True, "users": listar_usuarios()})
            return

        if path.startswith("/automation/rules/"):
            rule_id = path.split("/")[-1]
            ok = remover_rotina(rule_id)
            if not ok:
                self._send_json({"ok": False, "error": "rule_not_found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True, "removed": True, "rules": listar_rotinas()})
            return

        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Servidor HTTP da NOVA")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = parser.parse_args()

    try:
        carregar_memoria_usuario()
        carregar_aprendizado()
        iniciar_monitor_despertador(falar_callback=falar)
        iniciar_runtime_fase2()
    except Exception:
        pass

    server = ThreadingHTTPServer((args.host, args.port), NovaHandler)
    print(f"NOVA API online em http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

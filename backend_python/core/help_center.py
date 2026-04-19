from __future__ import annotations

from typing import Any


def ajuda_topicos() -> dict[str, Any]:
    comandos = [
        {"cmd": "/help", "desc": "Mostra visão geral da assistente e comandos."},
        {"cmd": "/status sistema", "desc": "Retorna status detalhado de software e segurança."},
        {"cmd": "/autonomia status", "desc": "Mostra estado atual de autonomia e fila."},
        {"cmd": "/autonomia ligar|desligar", "desc": "Liga/desliga modo autonomia."},
        {"cmd": "/autonomia risco baixo|moderado|alto", "desc": "Define política de risco."},
        {"cmd": "/autonomia liberdade baixa|media|alta", "desc": "Ajusta liberdade operacional da execução autônoma."},
        {"cmd": "/rag reindex [arquivos]", "desc": "Reindexa base RAG local."},
        {"cmd": "/rag <pergunta>", "desc": "Consulta base RAG com fontes."},
        {"cmd": "/google <consulta>", "desc": "Pesquisa na internet e resume."},
        {"cmd": 'traduza "<texto>" para <idioma>', "desc": "Traduz um texto enviado na propria mensagem."},
        {"cmd": "traduza essa pesquisa para <idioma>", "desc": "Traduz a ultima pesquisa da conversa para o idioma pedido."},
        {"cmd": "me fale essa pesquisa em <idioma>", "desc": "Atalho natural por voz para ouvir/receber a ultima pesquisa em outro idioma."},
        {"cmd": "agende <evento> amanha as 15:00", "desc": "Cria um evento na Google Agenda com horario natural."},
        {"cmd": "marque reuniao em 2026-05-01 14:00 ate 15:30", "desc": "Agenda um compromisso com inicio e fim definidos."},
        {"cmd": "pesquise no Maps por <lugar>", "desc": "Atalho local do app para abrir busca gratuita no Maps, sem SDK pago."},
        {"cmd": "pesquise no YouTube por <tema>", "desc": "Atalho local do app para abrir busca no YouTube."},
        {"cmd": "/modo pesquisa", "desc": "Opcional: força pesquisa web assistida de forma mais agressiva."},
        {"cmd": "/modo conversa", "desc": "Opcional: reduz a priorização automática de pesquisa e volta ao chat mais conversacional."},
        {"cmd": "/lembrar <texto> <data/hora>", "desc": "Cria lembrete com data/hora."},
        {"cmd": "/lembretes", "desc": "Lista lembretes ativos."},
        {"cmd": "/calcular <expressao>", "desc": "Executa cálculo."},
        {"cmd": "/projeto <nome>", "desc": "Cria projeto no destino padrão configurado (Notion ou Google Drive)."},
        {"cmd": "/notion projeto <nome>", "desc": "Cria projeto diretamente no Notion."},
        {"cmd": "/admin login <u> <s> [2fa]", "desc": "Login administrativo."},
        {"cmd": "/admin 2fa status|ligar|desligar|obrigatorio on|off|codigo|rotacionar", "desc": "Gerencia 2FA admin."},
        {"cmd": "/admin jarvis2 status|ligar|desligar|enfileirar|fila|limpar|relatorio", "desc": "Gerencia runtime JARVIS2."},
        {"cmd": "/admin drivebackup status|sincronizar|restaurar", "desc": "Opera backup em Drive."},
    ]
    topicos = [
        {
            "topic": "Identidade",
            "text": "A NOVA é uma assistente de IA com memória, voz, automações seguras, análise de documentos e execução assistida por política de risco.",
        },
        {
            "topic": "Voz e Interface",
            "text": "Possui modo escuta, push-to-talk, wake word, painel admin responsivo e atalhos locais para abrir YouTube e Maps por voz.",
        },
        {
            "topic": "Conhecimento e Aprendizado",
            "text": "Aprende por conversa, por documentos anexados (automático), por RAG local com fontes e agora pesquisa automaticamente na web quando a pergunta pede contexto factual.",
        },
        {
            "topic": "Autonomia e Segurança",
            "text": "Autonomia com bloqueios por risco, aprovação para ações sensíveis, RBAC opcional e auditoria de sessão encadeada.",
        },
        {
            "topic": "Operação",
            "text": "Inclui métricas operacionais, status de runtime e monitoramento de falhas.",
        },
    ]
    return {"ok": True, "topics": topicos, "commands": comandos}


def ajuda_texto_humano() -> str:
    payload = ajuda_topicos()
    linhas = [
        "Help da NOVA:",
        "Eu sou a NOVA, uma assistente de IA com memória, voz, RAG, automações seguras e modo autônomo controlado.",
        "Você também pode pedir por voz ou texto algo como 'Nova, crie um novo projeto chamado Atlas'.",
        "Perguntas factuais como 'quem descobriu o Brasil' ou 'como funciona MCP' já podem disparar pesquisa web automaticamente.",
        'Para traduzir um texto direto, use algo como: traduza "Bom dia" para ingles.',
        "Depois de responder uma pesquisa, eu tambem posso oferecer a traducao no proprio chat. Basta responder sim ou nao.",
        "Depois de uma pesquisa, você pode pedir 'traduza essa pesquisa para inglês' ou 'me fale essa pesquisa em português'.",
        "Tambem posso agendar tarefas e compromissos na Google Agenda com pedidos como 'agende reuniao com cliente amanha as 15h'.",
        "Para funcionar, a agenda escolhida precisa estar compartilhada com a service account configurada no backend.",
        "",
        "Tópicos principais:",
    ]
    for t in payload.get("topics", []):
        linhas.append(f"- {t.get('topic')}: {t.get('text')}")
    linhas.append("")
    linhas.append("Comandos principais:")
    for c in payload.get("commands", [])[:20]:
        linhas.append(f"- {c.get('cmd')}: {c.get('desc')}")
    return "\n".join(linhas)

from __future__ import annotations

from datetime import datetime

from core.admin import carregar_config_admin
from core.caminhos import pasta_dados_app
from core.painel_admin import carregar_config_painel, listar_usuarios
from core.seguranca import carregar_json_seguro, salvar_json_seguro, status_criptografia


ARQUIVO_AUDITORIA = pasta_dados_app() / "security_audit_history.json"


def _checklist_formal() -> list[dict]:
    return [
        {
            "categoria": "Tokens e Segredos",
            "itens": [
                "Tokens fora de texto puro em banco local",
                "Rotação de token e revogação quando necessário",
                "Segredos com escopo mínimo",
            ],
        },
        {
            "categoria": "Permissões e Superfície de Ataque",
            "itens": [
                "Somente permissões estritamente necessárias",
                "Serviços em background com objetivo claro",
                "Bloqueio de ações sensíveis sem autenticação",
            ],
        },
        {
            "categoria": "Acesso Administrativo",
            "itens": [
                "Credencial padrão de admin desativada",
                "Pelo menos um admin ativo",
                "Sessão curta para operações administrativas",
            ],
        },
        {
            "categoria": "Hardening",
            "itens": [
                "Criptografia de dados em repouso ativa",
                "Registro de eventos críticos",
                "Plano de atualização e resposta a incidentes",
            ],
        },
    ]


def _historico_padrao() -> dict:
    return {"version": 1, "items": []}


def _carregar_historico_raw() -> dict:
    raw = carregar_json_seguro(ARQUIVO_AUDITORIA, _historico_padrao())
    if not isinstance(raw, dict):
        raw = _historico_padrao()
    items = raw.get("items")
    if not isinstance(items, list):
        raw["items"] = []
    return raw


def obter_historico_auditoria(limit: int = 30) -> list[dict]:
    raw = _carregar_historico_raw()
    items = raw.get("items", [])
    lim = max(1, min(int(limit), 200))
    return list(items[-lim:])


def _registrar_no_historico(snapshot: dict) -> None:
    raw = _carregar_historico_raw()
    items = raw.get("items", [])
    if not isinstance(items, list):
        items = []

    entry = {
        "audit_time": snapshot.get("audit_time"),
        "score": int(snapshot.get("score", 0)),
        "nivel": snapshot.get("nivel", "atencao"),
        "achados_total": len(snapshot.get("achados", []) or []),
        "crypto_status": snapshot.get("crypto_status", ""),
    }

    items.append(entry)
    raw["items"] = items[-240:]
    salvar_json_seguro(ARQUIVO_AUDITORIA, raw)


def executar_auditoria_seguranca(persistir: bool = True) -> dict:
    admin_cfg = carregar_config_admin()
    painel_cfg = carregar_config_painel()
    usuarios = listar_usuarios()

    score = 100
    achados: list[dict] = []

    senha_padrao = bool(admin_cfg.get("usa_senha_padrao", True))
    if senha_padrao:
        score -= 35
        achados.append(
            {
                "severidade": "critico",
                "titulo": "Senha padrão de admin ativa",
                "detalhe": "A credencial administrativa ainda usa padrão inicial.",
                "acao": "Trocar com /admin configurar <usuario> <senha_forte> imediatamente.",
            }
        )

    admins_ativos = [
        u
        for u in usuarios
        if str(u.get("papel", "")).lower() == "admin" and bool(u.get("ativo", True))
    ]
    if not admins_ativos:
        score -= 25
        achados.append(
            {
                "severidade": "alto",
                "titulo": "Sem admin ativo no painel",
                "detalhe": "Nenhum usuário com papel admin ativo foi encontrado.",
                "acao": "Manter ao menos 1 admin ativo para governança e recuperação.",
            }
        )

    telegram_ativo = bool(painel_cfg.get("telegram_ativo", False))
    token = str(painel_cfg.get("telegram_token", "") or "").strip()
    chat_id = str(painel_cfg.get("telegram_chat_id", "") or "").strip()
    if telegram_ativo and (not token or not chat_id):
        score -= 20
        achados.append(
            {
                "severidade": "alto",
                "titulo": "Telegram ativo sem configuração completa",
                "detalhe": "Integração ativa com token/chat incompleto aumenta falhas e risco operacional.",
                "acao": "Completar token/chat ou desativar Telegram até validar credenciais.",
            }
        )

    wake_word = str(painel_cfg.get("wake_word", "nova") or "nova").strip()
    if len(wake_word) < 3:
        score -= 5
        achados.append(
            {
                "severidade": "medio",
                "titulo": "Wake word muito curta",
                "detalhe": "Palavra de ativação curta aumenta falso positivo por ruído.",
                "acao": "Usar wake word com 4+ caracteres e baixa ambiguidade.",
            }
        )

    cripto = status_criptografia()
    if "inativa" in cripto.lower() or "desabilitada" in cripto.lower():
        score -= 25
        achados.append(
            {
                "severidade": "critico",
                "titulo": "Criptografia em repouso não confirmada",
                "detalhe": cripto,
                "acao": "Ativar proteção de dados em repouso para arquivos críticos.",
            }
        )

    score = max(0, min(100, score))
    if score >= 85:
        nivel = "bom"
    elif score >= 65:
        nivel = "atencao"
    else:
        nivel = "critico"

    historico = obter_historico_auditoria(limit=1)
    score_anterior = int(historico[-1].get("score", score)) if historico else score
    delta = score - score_anterior if historico else 0

    prioridades = [
        "1) Eliminar credenciais padrão e reforçar autenticação admin.",
        "2) Garantir tokens completos e rotacionáveis para integrações externas.",
        "3) Revisar permissões e manter somente o mínimo necessário.",
        "4) Fortalecer trilha de auditoria e plano de resposta a incidentes.",
    ]

    out = {
        "ok": True,
        "audit_time": datetime.now().isoformat(timespec="seconds"),
        "score": score,
        "score_anterior": score_anterior,
        "delta_vs_previous": delta,
        "nivel": nivel,
        "crypto_status": cripto,
        "admins_ativos": len(admins_ativos),
        "users_total": len(usuarios),
        "telegram_ativo": telegram_ativo,
        "checklist_formal": _checklist_formal(),
        "achados": achados,
        "prioridades": prioridades,
    }

    if persistir:
        _registrar_no_historico(out)

    return out


def auditoria_humana() -> str:
    out = executar_auditoria_seguranca(persistir=True)
    linhas = [
        "Varredura formal de segurança:",
        f"- Score: {out.get('score')}/100 ({out.get('nivel')})",
        f"- Delta vs anterior: {out.get('delta_vs_previous')}",
        f"- Criptografia: {out.get('crypto_status')}",
        f"- Admins ativos: {out.get('admins_ativos')}",
        f"- Telegram ativo: {'sim' if out.get('telegram_ativo') else 'não'}",
    ]

    achados = out.get("achados", [])
    if achados:
        linhas.append("- Achados:")
        for a in achados[:8]:
            linhas.append(
                f"  * [{a.get('severidade')}] {a.get('titulo')}: {a.get('acao')}"
            )
    else:
        linhas.append("- Achados: nenhum crítico no momento.")

    linhas.append("- Prioridades:")
    for p in out.get("prioridades", [])[:4]:
        linhas.append(f"  * {p}")

    return "\n".join(linhas)

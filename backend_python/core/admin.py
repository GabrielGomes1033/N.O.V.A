# Funções de administração da NOVA.
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import base64
import hashlib
import hmac
import os
import time

from core.caminhos import pasta_dados_app
from core.seguranca import (
    carregar_json_seguro,
    gerar_hash_senha,
    salvar_json_seguro,
    status_criptografia,
    verificar_hash_senha,
)
from core.session_audit import registrar_evento_sessao


ARQUIVO_ADMIN = pasta_dados_app() / "admin_config.json"


def _config_padrao():
    usuario = os.getenv("NOVA_ADMIN_USER", "admin").strip() or "admin"
    senha_default = os.getenv("NOVA_ADMIN_PASSWORD", "admin123")
    return {
        "usuario_admin": usuario,
        "senha_hash": gerar_hash_senha(senha_default),
        "usa_senha_padrao": os.getenv("NOVA_ADMIN_PASSWORD") is None,
        "tentativas_falhas": 0,
        "bloqueado_ate": 0,
        "admin_2fa_ativo": False,
        "admin_2fa_required": True,
        "admin_2fa_secret": "",
        "sessoes_auditoria": [],
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }


def carregar_config_admin():
    if not Path(ARQUIVO_ADMIN).is_file():
        config = _config_padrao()
        salvar_json_seguro(ARQUIVO_ADMIN, config)
        return config

    dados = carregar_json_seguro(ARQUIVO_ADMIN, _config_padrao())
    if not isinstance(dados, dict):
        dados = _config_padrao()
        salvar_json_seguro(ARQUIVO_ADMIN, dados)
    base = _config_padrao()
    base.update(dados)
    if not isinstance(base.get("sessoes_auditoria"), list):
        base["sessoes_auditoria"] = []
    salvar_json_seguro(ARQUIVO_ADMIN, base)
    return base


def _registrar_sessao(evento: str, usuario: str = "", ok: bool = True, cfg: dict | None = None):
    cfg = cfg if isinstance(cfg, dict) else carregar_config_admin()
    logs = cfg.get("sessoes_auditoria", [])
    if not isinstance(logs, list):
        logs = []
    logs.append(
        {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "evento": evento,
            "usuario": (usuario or "").strip(),
            "ok": bool(ok),
        }
    )
    cfg["sessoes_auditoria"] = logs[-120:]
    try:
        registrar_evento_sessao(evento=evento, usuario=usuario, ok=ok)
    except Exception:
        pass
    cfg["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    salvar_json_seguro(ARQUIVO_ADMIN, cfg)
    return cfg


def _totp(secret_b32: str, ts: int | None = None, step: int = 30, digits: int = 6) -> str:
    if ts is None:
        ts = int(time.time())
    key = base64.b32decode(secret_b32 + "=" * ((8 - len(secret_b32) % 8) % 8), casefold=True)
    counter = int(ts // step).to_bytes(8, "big")
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    code_int = ((digest[off] & 0x7F) << 24) | ((digest[off + 1] & 0xFF) << 16) | ((digest[off + 2] & 0xFF) << 8) | (digest[off + 3] & 0xFF)
    return str(code_int % (10**digits)).zfill(digits)


def _validar_totp(secret_b32: str, codigo: str, janela: int = 1) -> bool:
    code = (codigo or "").strip()
    if not code.isdigit():
        return False
    now = int(time.time())
    for w in range(-janela, janela + 1):
        if _totp(secret_b32, ts=now + (w * 30)) == code:
            return True
    return False


def configurar_admin_2fa(ativo: bool, secret: str = ""):
    cfg = carregar_config_admin()
    if ativo:
        if not secret:
            raw = os.urandom(20)
            secret = base64.b32encode(raw).decode("ascii").rstrip("=")
        cfg["admin_2fa_ativo"] = True
        cfg["admin_2fa_secret"] = secret
        cfg = _registrar_sessao("2fa_ativado", usuario=str(cfg.get("usuario_admin", "")), ok=True, cfg=cfg)
    else:
        cfg["admin_2fa_ativo"] = False
        cfg["admin_2fa_secret"] = ""
        cfg = _registrar_sessao("2fa_desativado", usuario=str(cfg.get("usuario_admin", "")), ok=True, cfg=cfg)
    cfg["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    salvar_json_seguro(ARQUIVO_ADMIN, cfg)
    return cfg


def gerar_codigo_2fa_admin():
    cfg = carregar_config_admin()
    if not cfg.get("admin_2fa_ativo"):
        return False, "2FA inativo. Ative com /admin 2fa ligar."
    secret = str(cfg.get("admin_2fa_secret", ""))
    if not secret:
        return False, "2FA sem segredo configurado."
    return True, _totp(secret)


def rotacionar_segredo_2fa():
    cfg = carregar_config_admin()
    if not cfg.get("admin_2fa_ativo"):
        return False, "2FA está inativo."
    novo = base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")
    cfg["admin_2fa_secret"] = novo
    cfg["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    salvar_json_seguro(ARQUIVO_ADMIN, cfg)
    _registrar_sessao("2fa_rotacionado", usuario=str(cfg.get("usuario_admin", "")), ok=True)
    return True, f"Segredo 2FA rotacionado. Novo segredo base32: {novo}"


def configurar_admin(usuario, senha):
    usuario = (usuario or "").strip()
    senha = (senha or "").strip()
    if len(usuario) < 3 or len(senha) < 8:
        return False, "Usuário precisa ter 3+ caracteres e senha 8+ caracteres."

    config = carregar_config_admin()
    config["usuario_admin"] = usuario
    config["senha_hash"] = gerar_hash_senha(senha)
    config["usa_senha_padrao"] = False
    config["tentativas_falhas"] = 0
    config["bloqueado_ate"] = 0
    config["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    salvar_json_seguro(ARQUIVO_ADMIN, config)
    _registrar_sessao("credenciais_atualizadas", usuario=usuario, ok=True)
    return True, "Credenciais de admin atualizadas com sucesso."


def autenticar_admin(usuario, senha, codigo_2fa: str = ""):
    config = carregar_config_admin()
    bloqueado_ate = int(config.get("bloqueado_ate", 0) or 0)
    now = int(time.time())
    if bloqueado_ate > now:
        return False

    usuario_ok = (usuario or "").strip() == str(config.get("usuario_admin", ""))
    senha_ok = verificar_hash_senha((senha or "").strip(), config.get("senha_hash", {}))
    twofa_ok = True
    twofa_required = bool(config.get("admin_2fa_required", True))
    if twofa_required and not config.get("admin_2fa_ativo"):
        _registrar_sessao(
            "login_admin_2fa_required",
            usuario=(usuario or ""),
            ok=False,
        )
        return False
    if config.get("admin_2fa_ativo"):
        secret = str(config.get("admin_2fa_secret", ""))
        twofa_ok = bool(secret) and _validar_totp(secret, codigo_2fa)

    ok = usuario_ok and senha_ok and twofa_ok
    if ok:
        config["tentativas_falhas"] = 0
        config["bloqueado_ate"] = 0
        salvar_json_seguro(ARQUIVO_ADMIN, config)
        _registrar_sessao("login_admin", usuario=(usuario or ""), ok=True)
        return True

    tent = int(config.get("tentativas_falhas", 0)) + 1
    config["tentativas_falhas"] = tent
    if tent >= 5:
        config["bloqueado_ate"] = now + (10 * 60)
        config["tentativas_falhas"] = 0
    config["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    salvar_json_seguro(ARQUIVO_ADMIN, config)
    _registrar_sessao("login_admin", usuario=(usuario or ""), ok=False)
    return False


def status_admin():
    config = carregar_config_admin()
    aviso = "Senha padrão ativa: SIM (recomendado trocar)." if config.get("usa_senha_padrao") else "Senha padrão ativa: NÃO."
    twofa = "2FA: ATIVO." if config.get("admin_2fa_ativo") else "2FA: INATIVO."
    twofa_req = (
        "2FA obrigatório: SIM."
        if config.get("admin_2fa_required", True)
        else "2FA obrigatório: NÃO."
    )
    bloqueado_ate = int(config.get("bloqueado_ate", 0) or 0)
    bloqueio = "Conta desbloqueada."
    if bloqueado_ate > int(time.time()):
        bloqueio = f"Conta bloqueada até epoch {bloqueado_ate}."
    return (
        f"Admin configurado: {config.get('usuario_admin', 'admin')}\n"
        f"{aviso}\n"
        f"{twofa}\n"
        f"{twofa_req}\n"
        f"{bloqueio}\n"
        f"{status_criptografia()}"
    )


def explicacao_completa_admin():
    return (
        "Arquitetura completa da NOVA (visão admin):\n"
        "1. Entrada e roteamento: `main.py` controla o loop, identifica comandos, mantém contexto e delega para os módulos.\n"
        "2. Motor de linguagem: `core/respostas.py` detecta intenção, tenta memória aprendida e escolhe respostas por modo.\n"
        "3. Camada agente: `core/agente.py` executa ciclo pensar->agir->observar com plano de passos e confirmação de ações sensíveis.\n"
        "3.1. JARVIS fase 2: `core/jarvis_fase2.py` mantém fila de tarefas em background e emite relatórios proativos automáticos.\n"
        "4. Memória de longo prazo: `core/memoria.py` persiste nome, idioma, tratamento, objetivos recentes e última interação.\n"
        "5. Pesquisa externa: `core/pesquisa.py` consulta Wikipedia (PT/EN), resume e devolve link/fonte.\n"
        "6. Voz: `core/voz.py` e `core/voz_worker.py` fazem TTS em subprocesso para não travar o chat.\n"
        "7. Personalidade: `core/personalidade.py` estiliza saída por modo (normal/formal/etc).\n"
        "8. Segurança: `core/seguranca.py` aplica criptografia de dados em repouso (Fernet), hash de senha admin com PBKDF2-HMAC-SHA256 e proteção de chave local.\n"
        "9. Dados persistentes: memória, aprendizado, histórico de agente e configuração admin são lidos/escritos pela camada segura.\n"
        "10. Compatibilidade e fallback: se um módulo falhar no import, `main.py` mantém fallback para evitar quebra total do app.\n"
        "\n"
        f"Estado de segurança atual: {status_criptografia()}"
    )

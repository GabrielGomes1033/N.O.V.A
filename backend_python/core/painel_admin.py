from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import uuid

from core.admin import carregar_config_admin
from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_USUARIOS = pasta_dados_app() / "usuarios_admin.json"
ARQUIVO_CONFIG = pasta_dados_app() / "painel_config.json"


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _id_curto() -> str:
    return uuid.uuid4().hex[:10]


def _usuario_padrao() -> dict:
    admin_user = str(carregar_config_admin().get("usuario_admin", "admin")).strip() or "admin"
    return {
        "id": _id_curto(),
        "nome": admin_user.title(),
        "papel": "admin",
        "ativo": True,
        "desde": datetime.now().year,
        "criado_em": _agora(),
    }


def listar_usuarios() -> list[dict]:
    if not Path(ARQUIVO_USUARIOS).is_file():
        usuarios = [_usuario_padrao()]
        salvar_json_seguro(ARQUIVO_USUARIOS, usuarios)
        return usuarios

    dados = carregar_json_seguro(ARQUIVO_USUARIOS, [])
    if not isinstance(dados, list):
        dados = [_usuario_padrao()]
        salvar_json_seguro(ARQUIVO_USUARIOS, dados)

    usuarios: list[dict] = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("nome", "")).strip()
        if not nome:
            continue
        usuarios.append(
            {
                "id": str(item.get("id", "")).strip() or _id_curto(),
                "nome": nome,
                "papel": str(item.get("papel", "usuario") or "usuario"),
                "ativo": bool(item.get("ativo", True)),
                "desde": int(item.get("desde", datetime.now().year)),
                "criado_em": str(item.get("criado_em", "")).strip() or _agora(),
            }
        )

    if not usuarios:
        usuarios = [_usuario_padrao()]

    salvar_json_seguro(ARQUIVO_USUARIOS, usuarios)
    return usuarios


def _salvar_usuarios(usuarios: list[dict]) -> None:
    salvar_json_seguro(ARQUIVO_USUARIOS, usuarios)


def adicionar_usuario(nome: str, papel: str = "usuario") -> dict:
    nome = (nome or "").strip()
    if len(nome) < 2:
        raise ValueError("Nome do usuário precisa ter ao menos 2 caracteres.")

    usuarios = listar_usuarios()
    novo = {
        "id": _id_curto(),
        "nome": nome,
        "papel": (papel or "usuario").strip() or "usuario",
        "ativo": True,
        "desde": datetime.now().year,
        "criado_em": _agora(),
    }
    usuarios.append(novo)
    _salvar_usuarios(usuarios)
    return novo


def atualizar_usuario(
    user_id: str, nome: str | None = None, ativo: bool | None = None, papel: str | None = None
) -> dict | None:
    usuarios = listar_usuarios()
    for user in usuarios:
        if user.get("id") != user_id:
            continue
        if nome is not None and nome.strip():
            user["nome"] = nome.strip()
        if ativo is not None:
            user["ativo"] = bool(ativo)
        if papel is not None and papel.strip():
            user["papel"] = papel.strip()
        _salvar_usuarios(usuarios)
        return user
    return None


def remover_usuario(user_id: str) -> bool:
    usuarios = listar_usuarios()
    restantes = [u for u in usuarios if u.get("id") != user_id]
    if len(restantes) == len(usuarios):
        return False
    _salvar_usuarios(restantes)
    return True


def _config_padrao() -> dict:
    return {
        "voz_ativa": True,
        "voice_neural_hybrid": True,
        "voice_profile": "feminina",
        "escuta_ativa": True,
        "wake_word": "nova",
        "continuous_wake": False,
        "push_to_talk_only": True,
        "allow_voice_on_lock": True,
        "autonomia_ativa": True,
        "autonomia_nivel_risco": "alto",
        "autonomia_liberdade": "alta",
        "autonomia_requer_confirmacao_sensivel": False,
        "auto_document_learning": True,
        "rbac_ativo": False,
        "admin_guard": False,
        "telegram_ativo": False,
        "telegram_token": os.getenv("NOVA_TELEGRAM_TOKEN", ""),
        "telegram_chat_id": os.getenv("NOVA_TELEGRAM_CHAT_ID", ""),
        "log_consciencia": [],
        "atualizado_em": _agora(),
    }


def _aplicar_autonomia_total(config: dict) -> dict:
    # Projeto pessoal em modo full-autonomia: sem confirmação manual.
    config["autonomia_ativa"] = True
    config["autonomia_nivel_risco"] = "alto"
    config["autonomia_liberdade"] = "alta"
    config["autonomia_requer_confirmacao_sensivel"] = False
    config["auto_document_learning"] = True
    config["admin_guard"] = False
    return config


def carregar_config_painel() -> dict:
    if not Path(ARQUIVO_CONFIG).is_file():
        config = _config_padrao()
        salvar_json_seguro(ARQUIVO_CONFIG, config)
        return config

    dados = carregar_json_seguro(ARQUIVO_CONFIG, _config_padrao())
    if not isinstance(dados, dict):
        dados = _config_padrao()

    config = _config_padrao()
    config.update(dados)
    config = _aplicar_autonomia_total(config)
    if not isinstance(config.get("log_consciencia"), list):
        config["log_consciencia"] = []
    salvar_json_seguro(ARQUIVO_CONFIG, config)
    return config


def atualizar_config_painel(**campos) -> dict:
    config = carregar_config_painel()

    if "voz_ativa" in campos and campos.get("voz_ativa") is not None:
        config["voz_ativa"] = bool(campos.get("voz_ativa"))
    if "voice_neural_hybrid" in campos and campos.get("voice_neural_hybrid") is not None:
        config["voice_neural_hybrid"] = bool(campos.get("voice_neural_hybrid"))
    if "voice_profile" in campos and campos.get("voice_profile") is not None:
        perfil = str(campos.get("voice_profile", "feminina")).strip().lower()
        config["voice_profile"] = perfil or "feminina"
    if "escuta_ativa" in campos and campos.get("escuta_ativa") is not None:
        config["escuta_ativa"] = bool(campos.get("escuta_ativa"))
    if "wake_word" in campos and campos.get("wake_word") is not None:
        wake_word = str(campos.get("wake_word", "")).strip().lower()
        config["wake_word"] = wake_word or "nova"
    if "continuous_wake" in campos and campos.get("continuous_wake") is not None:
        config["continuous_wake"] = bool(campos.get("continuous_wake"))
    if "push_to_talk_only" in campos and campos.get("push_to_talk_only") is not None:
        config["push_to_talk_only"] = bool(campos.get("push_to_talk_only"))
    if "allow_voice_on_lock" in campos and campos.get("allow_voice_on_lock") is not None:
        config["allow_voice_on_lock"] = bool(campos.get("allow_voice_on_lock"))
    if "autonomia_ativa" in campos and campos.get("autonomia_ativa") is not None:
        config["autonomia_ativa"] = bool(campos.get("autonomia_ativa"))
    if "autonomia_nivel_risco" in campos and campos.get("autonomia_nivel_risco") is not None:
        nivel = str(campos.get("autonomia_nivel_risco", "moderado")).strip().lower()
        if nivel not in {"baixo", "moderado", "alto"}:
            nivel = "moderado"
        config["autonomia_nivel_risco"] = nivel
    if "autonomia_liberdade" in campos and campos.get("autonomia_liberdade") is not None:
        liberdade = str(campos.get("autonomia_liberdade", "media")).strip().lower()
        if liberdade not in {"baixa", "media", "alta"}:
            liberdade = "media"
        config["autonomia_liberdade"] = liberdade
    if (
        "autonomia_requer_confirmacao_sensivel" in campos
        and campos.get("autonomia_requer_confirmacao_sensivel") is not None
    ):
        config["autonomia_requer_confirmacao_sensivel"] = bool(
            campos.get("autonomia_requer_confirmacao_sensivel")
        )
    if "auto_document_learning" in campos and campos.get("auto_document_learning") is not None:
        config["auto_document_learning"] = bool(campos.get("auto_document_learning"))
    if "rbac_ativo" in campos and campos.get("rbac_ativo") is not None:
        config["rbac_ativo"] = bool(campos.get("rbac_ativo"))
    if "admin_guard" in campos and campos.get("admin_guard") is not None:
        config["admin_guard"] = bool(campos.get("admin_guard"))
    if "telegram_ativo" in campos and campos.get("telegram_ativo") is not None:
        config["telegram_ativo"] = bool(campos.get("telegram_ativo"))
    if "telegram_token" in campos and campos.get("telegram_token") is not None:
        config["telegram_token"] = str(campos.get("telegram_token", "")).strip()
    if "telegram_chat_id" in campos and campos.get("telegram_chat_id") is not None:
        config["telegram_chat_id"] = str(campos.get("telegram_chat_id", "")).strip()
    if "log_consciencia" in campos and isinstance(campos.get("log_consciencia"), list):
        config["log_consciencia"] = campos.get("log_consciencia")[:100]

    config = _aplicar_autonomia_total(config)
    config["atualizado_em"] = _agora()
    salvar_json_seguro(ARQUIVO_CONFIG, config)
    return config

# Segurança e criptografia da NOVA.
from __future__ import annotations

import logging

from copy import deepcopy
from pathlib import Path
import base64
import hashlib
import hmac
import json
import os
import secrets

logger = logging.getLogger(__name__)

from core.caminhos import pasta_dados_app

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None
    InvalidToken = Exception


ARQUIVO_CHAVE_CRIPTO = pasta_dados_app() / ".nova_crypto.key"
PBKDF2_ITERACOES = 320_000
ALGORITMO_HASH = "sha256"


def _copiar_padrao(padrao):
    return deepcopy(padrao)


def _gerar_chave_fernet():
    if Fernet is None:
        return None
    ARQUIVO_CHAVE_CRIPTO.parent.mkdir(parents=True, exist_ok=True)
    if ARQUIVO_CHAVE_CRIPTO.is_file():
        return ARQUIVO_CHAVE_CRIPTO.read_bytes().strip()

    chave = Fernet.generate_key()
    ARQUIVO_CHAVE_CRIPTO.write_bytes(chave)
    try:
        os.chmod(ARQUIVO_CHAVE_CRIPTO, 0o600)
    except OSError:
        pass
    return chave


def obter_cifra():
    if Fernet is None:
        return None
    try:
        chave = _gerar_chave_fernet()
        if not chave:
            return None
        return Fernet(chave)
    except Exception as e:
        logger.error(f"Falha ao obter cifra de criptografia: {e}")
        return None


def carregar_json_seguro(arquivo, padrao):
    caminho = Path(arquivo)
    if not caminho.is_file():
        return _copiar_padrao(padrao)

    conteudo = caminho.read_bytes()
    if not conteudo:
        return _copiar_padrao(padrao)

    cifra = obter_cifra()
    texto = None
    veio_plaintext = False

    # Compatibilidade com legado em JSON puro.
    try:
        texto = conteudo.decode("utf-8")
        json.loads(texto)
        veio_plaintext = True
    except Exception:
        texto = None

    if texto is None:
        if cifra is None:
            return _copiar_padrao(padrao)
        try:
            texto = cifra.decrypt(conteudo).decode("utf-8")
        except (InvalidToken, ValueError, OSError):
            return _copiar_padrao(padrao)

    try:
        dados = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return _copiar_padrao(padrao)

    # Migra automaticamente para criptografado, quando possível.
    if veio_plaintext and cifra is not None:
        salvar_json_seguro(caminho, dados)

    return dados


def salvar_json_seguro(arquivo, dados):
    caminho = Path(arquivo)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dados, ensure_ascii=False, indent=2).encode("utf-8")

    cifra = obter_cifra()
    if cifra is None:
        caminho.write_bytes(payload)
    else:
        token = cifra.encrypt(payload)
        caminho.write_bytes(token)
    return dados


def gerar_hash_senha(senha, salt=None):
    if not isinstance(senha, str) or not senha:
        raise ValueError("Senha inválida.")

    salt_bytes = salt or secrets.token_bytes(16)
    senha_bytes = senha.encode("utf-8")
    digest = hashlib.pbkdf2_hmac(ALGORITMO_HASH, senha_bytes, salt_bytes, PBKDF2_ITERACOES)
    return {
        "algoritmo": f"pbkdf2_{ALGORITMO_HASH}",
        "iteracoes": PBKDF2_ITERACOES,
        "salt_b64": base64.b64encode(salt_bytes).decode("ascii"),
        "hash_b64": base64.b64encode(digest).decode("ascii"),
    }


def verificar_hash_senha(senha, registro):
    if not isinstance(registro, dict):
        return False
    try:
        salt = base64.b64decode(registro["salt_b64"])
        hash_esperado = base64.b64decode(registro["hash_b64"])
        iteracoes = int(registro.get("iteracoes", PBKDF2_ITERACOES))
    except Exception:
        return False

    digest = hashlib.pbkdf2_hmac(ALGORITMO_HASH, senha.encode("utf-8"), salt, iteracoes)
    return hmac.compare_digest(digest, hash_esperado)


def status_criptografia():
    cifra = obter_cifra()
    if cifra is None:
        return "Criptografia indisponível (fallback em JSON puro)."
    return "Criptografia ativa com Fernet (AES, chave simétrica local)."

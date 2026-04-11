# Funções de administração da NOVA.
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os

from core.caminhos import pasta_dados_app
from core.seguranca import (
    carregar_json_seguro,
    gerar_hash_senha,
    salvar_json_seguro,
    status_criptografia,
    verificar_hash_senha,
)


ARQUIVO_ADMIN = pasta_dados_app() / "admin_config.json"


def _config_padrao():
    usuario = os.getenv("NOVA_ADMIN_USER", "admin").strip() or "admin"
    senha_default = os.getenv("NOVA_ADMIN_PASSWORD", "admin123")
    return {
        "usuario_admin": usuario,
        "senha_hash": gerar_hash_senha(senha_default),
        "usa_senha_padrao": os.getenv("NOVA_ADMIN_PASSWORD") is None,
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
    return dados


def configurar_admin(usuario, senha):
    usuario = (usuario or "").strip()
    senha = (senha or "").strip()
    if len(usuario) < 3 or len(senha) < 8:
        return False, "Usuário precisa ter 3+ caracteres e senha 8+ caracteres."

    config = carregar_config_admin()
    config["usuario_admin"] = usuario
    config["senha_hash"] = gerar_hash_senha(senha)
    config["usa_senha_padrao"] = False
    config["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    salvar_json_seguro(ARQUIVO_ADMIN, config)
    return True, "Credenciais de admin atualizadas com sucesso."


def autenticar_admin(usuario, senha):
    config = carregar_config_admin()
    usuario_ok = (usuario or "").strip() == str(config.get("usuario_admin", ""))
    senha_ok = verificar_hash_senha((senha or "").strip(), config.get("senha_hash", {}))
    return usuario_ok and senha_ok


def status_admin():
    config = carregar_config_admin()
    aviso = "Senha padrão ativa: SIM (recomendado trocar)." if config.get("usa_senha_padrao") else "Senha padrão ativa: NÃO."
    return (
        f"Admin configurado: {config.get('usuario_admin', 'admin')}\n"
        f"{aviso}\n"
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

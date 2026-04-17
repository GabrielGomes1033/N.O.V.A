# Memória persistente da NOVA para dados do usuário.
# Guarda preferências simples para a assistente soar mais pessoal.
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_MEMORIA = pasta_dados_app() / "memoria_usuario.json"
MEMORIA_PADRAO = {
    "nome_usuario": "",
    "idioma_preferido": "pt",
    "tratamento": "",
    "modo_pesquisa": False,
    "topicos_favoritos": [],
    "objetivos_recentes": [],
    "ultima_interacao": "",
    "interacoes_recentes": [],
    "ultima_localizacao": "",
    "ultima_latitude": "",
    "ultima_longitude": "",
    "ultima_localizacao_em": "",
}
IDIOMAS_SUPORTADOS = {"pt", "en", "es"}


def carregar_memoria_usuario(arquivo=ARQUIVO_MEMORIA):
    # Lê a memória persistente e retorna um dicionário pronto para uso.
    caminho = Path(arquivo)
    if not caminho.is_file():
        return MEMORIA_PADRAO.copy()

    dados = carregar_json_seguro(caminho, MEMORIA_PADRAO.copy())
    if not isinstance(dados, dict):
        return MEMORIA_PADRAO.copy()

    memoria = MEMORIA_PADRAO.copy()
    if isinstance(dados, dict):
        memoria.update({chave: dados.get(chave, valor) for chave, valor in memoria.items()})

    if memoria["idioma_preferido"] not in IDIOMAS_SUPORTADOS:
        memoria["idioma_preferido"] = MEMORIA_PADRAO["idioma_preferido"]

    if not isinstance(memoria["topicos_favoritos"], list):
        memoria["topicos_favoritos"] = []
    if not isinstance(memoria["objetivos_recentes"], list):
        memoria["objetivos_recentes"] = []
    if not isinstance(memoria["ultima_interacao"], str):
        memoria["ultima_interacao"] = ""
    if not isinstance(memoria["interacoes_recentes"], list):
        memoria["interacoes_recentes"] = []

    return memoria


def salvar_memoria_usuario(memoria, arquivo=ARQUIVO_MEMORIA):
    # Persiste a memória atual no disco.
    caminho = Path(arquivo)
    dados = MEMORIA_PADRAO.copy()
    dados.update(memoria or {})
    if dados["idioma_preferido"] not in IDIOMAS_SUPORTADOS:
        dados["idioma_preferido"] = MEMORIA_PADRAO["idioma_preferido"]

    return salvar_json_seguro(caminho, dados)


def atualizar_memoria_usuario(**campos):
    # Atualiza apenas os campos informados e salva o resultado.
    memoria = carregar_memoria_usuario()
    for chave, valor in campos.items():
        if chave not in MEMORIA_PADRAO:
            continue
        memoria[chave] = valor
    return salvar_memoria_usuario(memoria)


def registrar_interacao_usuario(entrada, resposta):
    memoria = carregar_memoria_usuario()
    historico = memoria.get("interacoes_recentes", [])
    if not isinstance(historico, list):
        historico = []

    historico.append(
        {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "entrada": str(entrada or "").strip(),
            "resposta": str(resposta or "").strip(),
        }
    )
    memoria["interacoes_recentes"] = historico[-30:]
    memoria["ultima_interacao"] = datetime.now().isoformat(timespec="seconds")
    return salvar_memoria_usuario(memoria)


def esquecer_memoria(campo=None):
    # Limpa um campo específico ou toda a memória do usuário.
    if not campo:
        return salvar_memoria_usuario(MEMORIA_PADRAO.copy())

    memoria = carregar_memoria_usuario()
    if campo in MEMORIA_PADRAO:
        memoria[campo] = MEMORIA_PADRAO[campo]
    return salvar_memoria_usuario(memoria)


def idioma_legivel(codigo):
    # Converte o código de idioma para um texto amigável na interface.
    nomes = {
        "pt": "Português",
        "en": "English",
        "es": "Español",
    }
    return nomes.get(codigo, "Português")


def formatar_memoria_usuario(memoria):
    # Gera um resumo simples da memória para mostrar no chat.
    memoria = MEMORIA_PADRAO | (memoria or {})
    nome = memoria.get("nome_usuario") or "não definido"
    idioma = idioma_legivel(memoria.get("idioma_preferido", "pt"))
    tratamento = memoria.get("tratamento") or "padrão"
    topicos = ", ".join(memoria.get("topicos_favoritos", [])) or "nenhum"
    modo_pesquisa = "ativo" if memoria.get("modo_pesquisa") else "desativado"
    objetivos = memoria.get("objetivos_recentes", [])
    ultimo_objetivo = objetivos[-1] if objetivos else "nenhum"
    ultima_interacao = memoria.get("ultima_interacao") or "não registrada"
    localizacao = memoria.get("ultima_localizacao") or "não definida"
    return (
        f"Nome: {nome}\n"
        f"Idioma preferido: {idioma}\n"
        f"Tratamento: {tratamento}\n"
        f"Modo pesquisa: {modo_pesquisa}\n"
        f"Tópicos favoritos: {topicos}\n"
        f"Último objetivo: {ultimo_objetivo}\n"
        f"Última interação: {ultima_interacao}\n"
        f"Localização: {localizacao}"
    )

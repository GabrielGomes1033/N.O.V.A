from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from core.dev_gerador import (
    criar_estrutura,
    formatar_lista_arquivos,
    nome_seguro,
    pasta_projetos_gerados,
)
from core.dev_revisor import analisar_erro, explicar_codigo
from core.dev_templates import (
    ADMIN_CSS,
    ADMIN_HTML,
    ADMIN_JS,
    API_FLASK_SQLITE,
    API_FASTAPI,
    API_FLASK,
    CSS_BASICO,
    ESTOQUE_CSS,
    ESTOQUE_HTML,
    ESTOQUE_JS,
    HTML_BASICO,
    JS_BASICO,
    LOGIN_CSS,
    LOGIN_HTML,
    LOGIN_JS,
    README_ADMIN,
    README_API,
    README_API_DB,
    README_ESTOQUE,
    README_SITE,
    REQUIREMENTS_FLASK_SQLITE,
    REQUIREMENTS_FASTAPI,
    REQUIREMENTS_FLASK,
)


def _normalizar(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", base).strip()


def _limpar_prefixo_nova(texto: str) -> str:
    return re.sub(r"^(nova[,:\s-]+)", "", str(texto or "").strip(), flags=re.IGNORECASE).strip()


_VERBOS_CRIACAO = r"(?:criar|crie|gerar|gere|montar|monte|fazer|faca|faça|desenvolver|desenvolva|quero|preciso(?:\s+de)?)"


def _extrair_nome_projeto(comando: str, padrao: str, default: str) -> str:
    texto = _limpar_prefixo_nova(comando)
    match = re.search(
        padrao + r"(?:\s+(?:chamado|com nome|nomeado)\s+(.+))?$",
        texto,
        flags=re.IGNORECASE,
    )
    if not match:
        return default

    candidato = (match.group(1) or "").strip(" .,:;\"'")
    if not candidato:
        return default

    candidato = re.sub(
        r"\b(para mim|por favor|agora|basico|b[aá]sico)\b",
        "",
        candidato,
        flags=re.IGNORECASE,
    ).strip(" _-")
    return nome_seguro(candidato or default)


def _resumo_criacao(tipo: str, payload: dict[str, object]) -> str:
    nome = str(payload.get("project_name", "projeto"))
    criados = formatar_lista_arquivos(payload.get("created_files", []))
    preservados = formatar_lista_arquivos(payload.get("preserved_files", []))
    caminho = payload.get("project_dir")
    pasta = nome if not isinstance(caminho, Path) else caminho.name

    linhas = [f"{tipo} criado com sucesso na pasta: projetos_gerados/{pasta}"]
    if criados != "nenhum":
        linhas.append(f"Arquivos criados: {criados}")
    if preservados != "nenhum":
        linhas.append(f"Arquivos preservados: {preservados}")
    return "\n".join(linhas)


def criar_site(nome_projeto: str = "site_nova", *, base_dir: str | Path | None = None) -> str:
    payload = criar_estrutura(
        nome_projeto,
        {
            "index.html": HTML_BASICO,
            "style.css": CSS_BASICO,
            "script.js": JS_BASICO,
            "README.md": README_SITE,
        },
        base_dir=base_dir,
    )
    return _resumo_criacao("Site", payload)


def criar_api(
    nome_projeto: str = "api_nova",
    *,
    stack: str = "flask",
    base_dir: str | Path | None = None,
) -> str:
    stack_normalizada = _normalizar(stack)
    if "fastapi" in stack_normalizada:
        arquivos = {
            "app.py": API_FASTAPI,
            "requirements.txt": REQUIREMENTS_FASTAPI,
            "README.md": README_API,
        }
        titulo = "API FastAPI"
    else:
        arquivos = {
            "app.py": API_FLASK,
            "requirements.txt": REQUIREMENTS_FLASK,
            "README.md": README_API,
        }
        titulo = "API Python"

    payload = criar_estrutura(nome_projeto, arquivos, base_dir=base_dir)
    return _resumo_criacao(titulo, payload)


def criar_api_com_banco(
    nome_projeto: str = "api_nova_db",
    *,
    base_dir: str | Path | None = None,
) -> str:
    payload = criar_estrutura(
        nome_projeto,
        {
            "app.py": API_FLASK_SQLITE,
            "requirements.txt": REQUIREMENTS_FLASK_SQLITE,
            "README.md": README_API_DB,
        },
        base_dir=base_dir,
    )
    return _resumo_criacao("API com banco de dados", payload)


def criar_sistema_login(
    nome_projeto: str = "sistema_login",
    *,
    base_dir: str | Path | None = None,
) -> str:
    payload = criar_estrutura(
        nome_projeto,
        {
            "index.html": LOGIN_HTML,
            "style.css": LOGIN_CSS,
            "script.js": LOGIN_JS,
            "README.md": README_SITE,
        },
        base_dir=base_dir,
    )
    return _resumo_criacao("Sistema de login", payload)


def criar_sistema_estoque(
    nome_projeto: str = "sistema_estoque",
    *,
    base_dir: str | Path | None = None,
) -> str:
    payload = criar_estrutura(
        nome_projeto,
        {
            "index.html": ESTOQUE_HTML,
            "style.css": ESTOQUE_CSS,
            "script.js": ESTOQUE_JS,
            "README.md": README_ESTOQUE,
        },
        base_dir=base_dir,
    )
    return _resumo_criacao("Sistema de estoque", payload)


def criar_painel_admin(
    nome_projeto: str = "painel_admin",
    *,
    base_dir: str | Path | None = None,
) -> str:
    payload = criar_estrutura(
        nome_projeto,
        {
            "index.html": ADMIN_HTML,
            "style.css": ADMIN_CSS,
            "script.js": ADMIN_JS,
            "README.md": README_ADMIN,
        },
        base_dir=base_dir,
    )
    return _resumo_criacao("Painel administrativo", payload)


def menu_desenvolvedor() -> str:
    return (
        "Modo desenvolvedor da NOVA ativado.\n\n"
        "Eu posso ajudar com:\n\n"
        "1. Criar site básico\n"
        "Comando: Nova, criar site\n\n"
        "2. Criar API Python\n"
        "Comando: Nova, criar API\n\n"
        "3. Criar sistema de login\n"
        "Comando: Nova, criar sistema de login\n\n"
        "4. Criar sistema de estoque\n"
        "Comando: Nova, criar sistema de estoque\n\n"
        "5. Criar API com banco de dados\n"
        "Comando: Nova, criar API com banco de dados\n\n"
        "6. Criar painel administrativo\n"
        "Comando: Nova, criar painel administrativo\n\n"
        "7. Explicar código\n"
        "Comando: Nova, explique este código: <cole o trecho>\n\n"
        "8. Corrigir erro\n"
        "Comando: Nova, corrija este erro: <cole o erro>\n\n"
        "Antes de escrever arquivos, eu peço confirmação. Para seguir, responda: confirmar criação.\n"
        "Tudo é gerado dentro da pasta projetos_gerados."
    )


def _extrair_conteudo(texto: str, gatilhos: tuple[str, ...]) -> str:
    bruto = _limpar_prefixo_nova(texto)
    normalizado = _normalizar(bruto)
    for gatilho in gatilhos:
        if gatilho in normalizado:
            indice = normalizado.find(gatilho)
            trecho_original = bruto[indice + len(gatilho) :].strip(" :\n\t-")
            return trecho_original
    return ""


def _contexto_dev(contexto: dict | None) -> dict:
    return contexto if isinstance(contexto, dict) else {}


def _salvar_pendencia_dev(contexto: dict, pendencia: dict[str, object]) -> None:
    contexto["dev_pending_action"] = pendencia


def _limpar_pendencia_dev(contexto: dict) -> None:
    if isinstance(contexto, dict):
        contexto.pop("dev_pending_action", None)


def _obter_pendencia_dev(contexto: dict | None) -> dict[str, object] | None:
    if not isinstance(contexto, dict):
        return None
    pendencia = contexto.get("dev_pending_action")
    return pendencia if isinstance(pendencia, dict) else None


def _texto_confirma(normalizado: str) -> bool:
    confirmacoes = (
        "confirmar criacao",
        "confirmar criação",
        "confirmar",
        "pode criar",
        "pode gerar",
        "sim pode criar",
        "sim pode gerar",
        "sim",
        "prosseguir",
    )
    return any(expr == normalizado or normalizado.startswith(expr + " ") for expr in confirmacoes)


def _texto_cancela(normalizado: str) -> bool:
    cancelamentos = (
        "cancelar criacao",
        "cancelar criação",
        "cancelar",
        "nao criar",
        "não criar",
        "deixa pra la",
        "deixa pra lá",
    )
    return any(expr == normalizado or normalizado.startswith(expr + " ") for expr in cancelamentos)


def _montar_pendencia(
    *,
    action: str,
    project_name: str,
    title: str,
    kwargs: dict[str, object] | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, object]:
    pasta_raiz = pasta_projetos_gerados(base_dir)
    return {
        "action": action,
        "project_name": project_name,
        "title": title,
        "kwargs": kwargs or {},
        "preview_path": str((pasta_raiz / project_name).resolve()),
    }


def _executar_pendencia(pendencia: dict[str, object], *, base_dir: str | Path | None = None) -> str:
    action = str(pendencia.get("action", "") or "")
    project_name = str(pendencia.get("project_name", "") or "")
    kwargs = dict(pendencia.get("kwargs", {}) or {})

    if action == "site":
        return criar_site(project_name, base_dir=base_dir)
    if action == "api":
        return criar_api(project_name, stack=str(kwargs.get("stack", "flask")), base_dir=base_dir)
    if action == "api_db":
        return criar_api_com_banco(project_name, base_dir=base_dir)
    if action == "login":
        return criar_sistema_login(project_name, base_dir=base_dir)
    if action == "estoque":
        return criar_sistema_estoque(project_name, base_dir=base_dir)
    if action == "painel_admin":
        return criar_painel_admin(project_name, base_dir=base_dir)
    return "Não consegui executar a criação pendente."


def _pedir_confirmacao(pendencia: dict[str, object]) -> str:
    titulo = str(pendencia.get("title", "Projeto"))
    preview_path = str(pendencia.get("preview_path", ""))
    return (
        f"Posso criar {titulo} em:\n{preview_path}\n\n"
        "Se estiver tudo certo, responda: confirmar criação"
    )


def processar_comando_dev(
    comando: str,
    *,
    contexto: dict | None = None,
    base_dir: str | Path | None = None,
) -> str | None:
    bruto = _limpar_prefixo_nova(comando)
    normalizado = _normalizar(bruto)
    if not normalizado:
        return None
    ctx = _contexto_dev(contexto)
    pendencia = _obter_pendencia_dev(ctx)

    if pendencia and _texto_confirma(normalizado):
        _limpar_pendencia_dev(ctx)
        return _executar_pendencia(pendencia, base_dir=base_dir)

    if pendencia and _texto_cancela(normalizado):
        _limpar_pendencia_dev(ctx)
        return "Criação cancelada. Quando quiser, eu preparo outro projeto para você."

    if any(chave in normalizado for chave in ("modo desenvolvedor", "desenvolver sistema")):
        return menu_desenvolvedor()

    if re.search(rf"\b{_VERBOS_CRIACAO}\b.*\bsite\b", normalizado):
        nome = _extrair_nome_projeto(bruto, rf".*\b{_VERBOS_CRIACAO}\b.*\bsite\b", "site_nova")
        nova_pendencia = _montar_pendencia(
            action="site",
            project_name=nome,
            title="um site",
            base_dir=base_dir,
        )
        _salvar_pendencia_dev(ctx, nova_pendencia)
        return _pedir_confirmacao(nova_pendencia)

    if (
        re.search(rf"\b{_VERBOS_CRIACAO}\b.*\bapi\b", normalizado)
        and "banco de dados" in normalizado
    ):
        nome = _extrair_nome_projeto(
            bruto,
            rf".*\b{_VERBOS_CRIACAO}\b.*\bapi\b.*\bbanco de dados\b",
            "api_nova_db",
        )
        nova_pendencia = _montar_pendencia(
            action="api_db",
            project_name=nome,
            title="uma API com banco de dados",
            base_dir=base_dir,
        )
        _salvar_pendencia_dev(ctx, nova_pendencia)
        return _pedir_confirmacao(nova_pendencia)

    if re.search(rf"\b{_VERBOS_CRIACAO}\b.*\bapi\b", normalizado):
        nome = _extrair_nome_projeto(bruto, rf".*\b{_VERBOS_CRIACAO}\b.*\bapi\b", "api_nova")
        stack = "fastapi" if "fastapi" in normalizado else "flask"
        titulo = "uma API FastAPI" if stack == "fastapi" else "uma API Python"
        nova_pendencia = _montar_pendencia(
            action="api",
            project_name=nome,
            title=titulo,
            kwargs={"stack": stack},
            base_dir=base_dir,
        )
        _salvar_pendencia_dev(ctx, nova_pendencia)
        return _pedir_confirmacao(nova_pendencia)

    if re.search(rf"\b{_VERBOS_CRIACAO}\b.*\bsistema de login\b", normalizado):
        nome = _extrair_nome_projeto(
            bruto,
            rf".*\b{_VERBOS_CRIACAO}\b.*\bsistema de login\b",
            "sistema_login",
        )
        nova_pendencia = _montar_pendencia(
            action="login",
            project_name=nome,
            title="um sistema de login",
            base_dir=base_dir,
        )
        _salvar_pendencia_dev(ctx, nova_pendencia)
        return _pedir_confirmacao(nova_pendencia)

    if re.search(rf"\b{_VERBOS_CRIACAO}\b.*\bsistema de estoque\b", normalizado):
        nome = _extrair_nome_projeto(
            bruto,
            rf".*\b{_VERBOS_CRIACAO}\b.*\bsistema de estoque\b",
            "sistema_estoque",
        )
        nova_pendencia = _montar_pendencia(
            action="estoque",
            project_name=nome,
            title="um sistema de estoque",
            base_dir=base_dir,
        )
        _salvar_pendencia_dev(ctx, nova_pendencia)
        return _pedir_confirmacao(nova_pendencia)

    if re.search(rf"\b{_VERBOS_CRIACAO}\b.*\bpainel administrativo\b", normalizado):
        nome = _extrair_nome_projeto(
            bruto,
            rf".*\b{_VERBOS_CRIACAO}\b.*\bpainel administrativo\b",
            "painel_admin",
        )
        nova_pendencia = _montar_pendencia(
            action="painel_admin",
            project_name=nome,
            title="um painel administrativo",
            base_dir=base_dir,
        )
        _salvar_pendencia_dev(ctx, nova_pendencia)
        return _pedir_confirmacao(nova_pendencia)

    if any(chave in normalizado for chave in ("corrigir erro", "corrija este erro")):
        detalhe = _extrair_conteudo(bruto, ("corrigir erro", "corrija este erro"))
        if detalhe:
            return analisar_erro(detalhe)
        return "Cole o erro completo do terminal para eu analisar."

    if any(
        chave in normalizado
        for chave in ("explique este codigo", "explicar este codigo", "explique esse codigo")
    ):
        detalhe = _extrair_conteudo(
            bruto,
            ("explique este codigo", "explicar este codigo", "explique esse codigo"),
        )
        if detalhe:
            return explicar_codigo(detalhe)
        return "Cole o código completo para eu explicar de forma clara."

    return None

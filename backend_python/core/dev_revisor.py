from __future__ import annotations

import re


def _resumo_traceback(erro: str) -> list[str]:
    linhas = []
    for arquivo, linha in re.findall(r'File "([^"]+)", line (\d+)', erro or "")[:3]:
        linhas.append(f"Arquivo provável: {arquivo}, linha {linha}.")
    return linhas


def analisar_erro(erro: str) -> str:
    erro_texto = str(erro or "")
    erro_lower = erro_texto.lower()
    detalhes = _resumo_traceback(erro_texto)

    if "modulenotfounderror" in erro_lower or "no module named" in erro_lower:
        resposta = (
            "Erro identificado: biblioteca não instalada.\n\n"
            "Solução provável:\n"
            "1. Ative seu ambiente virtual.\n"
            "2. Instale a biblioteca que aparece no erro.\n\n"
            "Exemplo:\n"
            "pip install nome_da_biblioteca"
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    if "syntaxerror" in erro_lower:
        resposta = (
            "Erro identificado: erro de sintaxe.\n\n"
            "Verifique:\n"
            "1. Parênteses abertos.\n"
            "2. Aspas abertas.\n"
            "3. Dois pontos faltando.\n"
            "4. Identação incorreta."
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    if "indentationerror" in erro_lower:
        resposta = (
            "Erro identificado: erro de identação.\n\n"
            "Solução:\n"
            "Organize os espaços no início das linhas.\n"
            "No Python, blocos dentro de if, for, while e def precisam estar indentados."
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    if "nameerror" in erro_lower:
        resposta = (
            "Erro identificado: variável ou função não definida.\n\n"
            "Verifique se o nome foi declarado antes do uso e se não houve erro de digitação."
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    if "typeerror" in erro_lower:
        resposta = (
            "Erro identificado: uso incompatível de tipos.\n\n"
            "Confira os valores recebidos pela função e confirme se você não está somando, chamando ou iterando um tipo incorreto."
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    if "attributeerror" in erro_lower:
        resposta = (
            "Erro identificado: atributo ou método inexistente.\n\n"
            "Verifique o tipo real do objeto e confirme se o método chamado existe para ele."
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    if "jsondecodeerror" in erro_lower:
        resposta = (
            "Erro identificado: JSON inválido.\n\n"
            "Confira vírgulas, aspas duplas e chaves ou colchetes faltando antes de tentar carregar o arquivo ou a resposta."
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    if "referenceerror" in erro_lower or "is not defined" in erro_lower:
        return (
            "Erro identificado: variável JavaScript não definida.\n\n"
            "Confirme se o nome foi declarado antes do uso e se o script foi carregado na ordem correta."
        )

    if "cannot read properties of undefined" in erro_lower:
        return (
            "Erro identificado: acesso a objeto indefinido no JavaScript.\n\n"
            "Verifique se o elemento ou dado existe antes de acessar suas propriedades."
        )

    if "operationalerror" in erro_lower or "integrityerror" in erro_lower:
        resposta = (
            "Erro identificado: falha relacionada ao banco de dados.\n\n"
            "Revise a conexão, a criação das tabelas e os dados enviados nas operações de insert ou update."
        )
        if detalhes:
            resposta += "\n\n" + "\n".join(detalhes)
        return resposta

    resposta = (
        "Não reconheci esse erro automaticamente.\n\n"
        "Envie o erro completo do terminal para eu analisar melhor."
    )
    if detalhes:
        resposta += "\n\n" + "\n".join(detalhes)
    return resposta


def explicar_codigo(codigo: str) -> str:
    trecho = str(codigo or "").strip()
    if not trecho:
        return "Cole o código completo para eu explicar linha por linha."

    codigo_lower = trecho.lower()
    pontos: list[str] = []
    resumo = "Parece ser um trecho de código."

    if "<html" in codigo_lower or "<body" in codigo_lower:
        resumo = "Esse código monta uma página HTML."
        if "<form" in codigo_lower:
            pontos.append("Existe um formulário para capturar dados do usuário.")
        if "script.js" in codigo_lower or "<script" in codigo_lower:
            pontos.append("A página depende de JavaScript para comportamento interativo.")
        if "style.css" in codigo_lower or "<link" in codigo_lower:
            pontos.append("O visual está separado em um arquivo CSS externo.")
    elif "from flask import" in codigo_lower or "flask(" in codigo_lower:
        resumo = "Esse código define uma API ou aplicação Flask."
        if "@app.route" in codigo_lower:
            pontos.append("As rotas HTTP estão sendo declaradas com decoradores do Flask.")
        if "request" in codigo_lower:
            pontos.append("Há leitura de dados enviados pelo cliente.")
    elif "from fastapi import" in codigo_lower or "fastapi(" in codigo_lower:
        resumo = "Esse código define uma API FastAPI."
        if "@app.get" in codigo_lower or "@app.post" in codigo_lower:
            pontos.append("As rotas estão separadas por método HTTP.")
    elif re.search(r"^\s*def\s+\w+\(", trecho, flags=re.MULTILINE):
        resumo = "Esse código define uma ou mais funções Python."
        pontos.append("As funções encapsulam comportamentos reutilizáveis.")
        if "return " in codigo_lower:
            pontos.append("Existe retorno explícito de valores.")
    elif re.search(r"^\s*class\s+\w+", trecho, flags=re.MULTILINE):
        resumo = "Esse código define uma classe."
        pontos.append("A classe agrupa dados e comportamentos relacionados.")
    elif "function " in codigo_lower or "=>" in codigo_lower:
        resumo = "Esse código parece ser JavaScript."
        if "addEventListener" in trecho or "onclick" in codigo_lower:
            pontos.append("Existe interação com eventos da interface.")
        if "fetch(" in codigo_lower:
            pontos.append("Há chamada HTTP para API ou serviço externo.")
    elif "{" in trecho and ":" in trecho and ";" in trecho:
        resumo = "Esse código parece ser CSS."
        pontos.append("As regras controlam aparência, espaçamento e comportamento visual.")
    elif (
        "select " in codigo_lower or "insert into" in codigo_lower or "create table" in codigo_lower
    ):
        resumo = "Esse trecho parece ser SQL."
        pontos.append("Ele manipula ou consulta dados em banco.")

    if 'if __name__ == "__main__"' in trecho:
        pontos.append("O bloco principal roda apenas quando o arquivo é executado diretamente.")

    total_funcoes = len(re.findall(r"^\s*def\s+\w+\(", trecho, flags=re.MULTILINE))
    total_rotas = len(re.findall(r"@\s*app\.(?:route|get|post|put|delete)", trecho))
    if total_funcoes:
        pontos.append(f"Há {total_funcoes} função(ões) definida(s) nesse trecho.")
    if total_rotas:
        pontos.append(f"Há {total_rotas} rota(s) HTTP declarada(s).")

    if not pontos:
        pontos.append("Se você quiser, eu também posso revisar esse trecho em busca de melhorias.")

    linhas = ["Explicação rápida do código:", resumo, "", "Pontos principais:"]
    linhas.extend(f"- {item}" for item in pontos[:5])
    return "\n".join(linhas)

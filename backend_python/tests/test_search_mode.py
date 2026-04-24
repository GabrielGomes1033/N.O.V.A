from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.assistente_plus import (
    _organizar_resultados_web,
    deve_acionar_pesquisa_web,
    extrair_consulta_pesquisa_web,
    formatar_resposta_pesquisa,
)
from core.intent_classifier import classify_intent
from core.nova_unica import orquestrar_consulta


class SearchModeTests(unittest.TestCase):
    def test_extrai_consulta_de_frase_natural_encadeada(self) -> None:
        consulta = extrair_consulta_pesquisa_web("Me explique como funciona o protocolo MCP?")
        self.assertEqual(consulta, "protocolo MCP")

    def test_extrai_consulta_dirigida_para_wikipedia(self) -> None:
        consulta = extrair_consulta_pesquisa_web("pesquise no Wikipedia LLM")
        self.assertEqual(consulta, "LLM wikipedia")

    def test_extrai_consulta_dirigida_para_google(self) -> None:
        consulta = extrair_consulta_pesquisa_web("pesquise no Google sobre MCP")
        self.assertEqual(consulta, "MCP")

    def test_intent_classifier_limpa_alvo_google(self) -> None:
        decision = classify_intent("pesquise LLM no google")
        self.assertEqual(decision.tool_name, "search_web")
        self.assertEqual(decision.params["query"], "LLM")

    def test_detecta_pedido_de_pesquisa_por_atualidade(self) -> None:
        self.assertTrue(deve_acionar_pesquisa_web("Quais as últimas notícias sobre agentes de IA?"))

    def test_detecta_pergunta_factual_sem_ativacao(self) -> None:
        self.assertTrue(deve_acionar_pesquisa_web("Quem descobriu o Brasil"))

    def test_extrai_consulta_comparativa_com_vs(self) -> None:
        consulta = extrair_consulta_pesquisa_web("Qual a diferença entre FastAPI e Flask?")
        self.assertEqual(consulta, "FastAPI vs Flask")

    def test_nao_aciona_pesquisa_para_pergunta_pessoal_da_assistente(self) -> None:
        self.assertFalse(deve_acionar_pesquisa_web("Qual o seu nome?"))

    def test_modo_pesquisa_nao_forca_busca_para_pedido_vago(self) -> None:
        self.assertFalse(deve_acionar_pesquisa_web("me ajuda com isso", modo_pesquisa=True))

    def test_prioriza_documentacao_oficial_em_consulta_tecnica(self) -> None:
        ordenados = _organizar_resultados_web(
            [
                {
                    "title": "Tutorial completo de FastAPI",
                    "snippet": "Um guia genérico com várias dicas de framework.",
                    "domain": "blog-exemplo.dev",
                    "url": "https://blog-exemplo.dev/fastapi",
                },
                {
                    "title": "Dependencies - FastAPI",
                    "snippet": "Official FastAPI documentation about dependency injection.",
                    "domain": "fastapi.tiangolo.com",
                    "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
                },
            ],
            "FastAPI dependency injection",
        )

        self.assertEqual(ordenados[0]["domain"], "fastapi.tiangolo.com")

    def test_nao_aciona_pesquisa_para_conversa_curta(self) -> None:
        self.assertFalse(deve_acionar_pesquisa_web("Oi, tudo bem?"))

    def test_formata_resposta_pesquisa_com_abertura_natural(self) -> None:
        texto = formatar_resposta_pesquisa(
            {
                "ok": True,
                "consulta": "Model Context Protocol",
                "resumo": "Resumo direto:\nÉ um padrão para integrar modelos com ferramentas.",
                "fontes": ["Wikipedia PT", "DuckDuckGo"],
                "links": ["https://example.com/mcp"],
            }
        )
        self.assertIn("Pesquisei sobre Model Context Protocol", texto)
        self.assertIn("Fontes consultadas", texto)
        self.assertIn("Se quiser se aprofundar", texto)

    def test_orquestrador_respeita_modo_pesquisa(self) -> None:
        with patch(
            "core.nova_unica.pesquisar_na_internet",
            return_value={
                "ok": True,
                "consulta": "frameworks para agentes de IA",
                "resumo": "Resumo direto:\nHá foco em orquestração, memória e uso de ferramentas.",
                "fontes": ["DuckDuckGo"],
                "links": [],
            },
        ):
            resposta = orquestrar_consulta(
                "frameworks para agentes de IA",
                contexto={"modo_pesquisa": True},
            )

        self.assertIsInstance(resposta, dict)
        self.assertIn("Pesquisei sobre frameworks para agentes de IA", resposta["resposta"])

    def test_orquestrador_nao_quebra_em_consulta_de_clima(self) -> None:
        with patch("core.nova_unica.consultar_clima", return_value="Tempo estável em Recife."):
            resposta = orquestrar_consulta("clima em Recife")

        self.assertEqual(resposta, {"resposta": "Tempo estável em Recife."})

    def test_orquestrador_pesquisa_pergunta_factual_sem_modo_explicito(self) -> None:
        with patch(
            "core.nova_unica.pesquisar_na_internet",
            return_value={
                "ok": True,
                "consulta": "descobriu o Brasil",
                "resumo": "Resumo direto:\nA resposta costuma citar Pedro Álvares Cabral em 1500.",
                "fontes": ["Wikipedia PT"],
                "links": [],
            },
        ):
            resposta = orquestrar_consulta("Quem descobriu o Brasil")

        self.assertIsInstance(resposta, dict)
        self.assertIn("Pesquisei sobre descobriu o Brasil", resposta["resposta"])


if __name__ == "__main__":
    unittest.main()

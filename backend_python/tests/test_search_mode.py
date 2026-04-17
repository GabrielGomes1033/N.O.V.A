from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.assistente_plus import (
    deve_acionar_pesquisa_web,
    extrair_consulta_pesquisa_web,
    formatar_resposta_pesquisa,
)
from core.nova_unica import orquestrar_consulta


class SearchModeTests(unittest.TestCase):
    def test_extrai_consulta_de_frase_natural_encadeada(self) -> None:
        consulta = extrair_consulta_pesquisa_web(
            "Me explique como funciona o protocolo MCP?"
        )
        self.assertEqual(consulta, "o protocolo MCP")

    def test_detecta_pedido_de_pesquisa_por_atualidade(self) -> None:
        self.assertTrue(
            deve_acionar_pesquisa_web(
                "Quais as últimas notícias sobre agentes de IA?"
            )
        )

    def test_detecta_pergunta_factual_sem_ativacao(self) -> None:
        self.assertTrue(
            deve_acionar_pesquisa_web("Quem descobriu o Brasil")
        )

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

from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.mercado import responder_consulta_mercado
from core.noticias import detectar_categoria_noticias, responder_consulta_noticias


class MarketNewsTests(unittest.TestCase):
    def test_detecta_noticias_do_brasil(self) -> None:
        self.assertEqual(detectar_categoria_noticias("notícias do brasil"), "brasil")

    def test_detecta_noticias_de_tecnologia(self) -> None:
        self.assertEqual(
            detectar_categoria_noticias("últimas notícias de tecnologia"), "tecnologia"
        )

    def test_responde_consulta_de_noticias(self) -> None:
        with patch(
            "core.noticias.buscar_noticias_categoria",
            return_value={
                "ok": True,
                "title": "Notícias do mundo",
                "items": [
                    {
                        "title": "Mercados acompanham decisão global",
                        "summary": "Leitura resumida.",
                        "source_name": "Agência X",
                    }
                ],
                "sources": ["GNews"],
                "updated_at": "2026-04-26T12:00:00",
            },
        ):
            texto = responder_consulta_noticias("notícias do mundo")

        self.assertIsInstance(texto, str)
        self.assertIn("Notícias do mundo", texto)
        self.assertIn("Mercados acompanham decisão global", texto)

    def test_responde_cotacao_de_acao(self) -> None:
        with patch(
            "core.mercado.consultar_ativo_financeiro",
            return_value={
                "ok": True,
                "name": "Petrobras",
                "symbol": "PETR4.SA",
                "currency": "BRL",
                "price": 36.72,
                "change_pct": 1.84,
                "day_high": 37.05,
                "day_low": 36.11,
                "sources": ["Yahoo Finance via yfinance"],
            },
        ):
            texto = responder_consulta_mercado("cotação da petrobras")

        self.assertIsInstance(texto, str)
        self.assertIn("Petrobras", texto)
        self.assertIn("PETR4.SA", texto)
        self.assertIn("variação", texto)

    def test_responde_resumo_do_mercado_financeiro(self) -> None:
        with patch(
            "core.mercado.gerar_resumo_mercado",
            return_value={
                "ok": True,
                "assets": [
                    {"name": "Dólar", "currency": "BRL", "price": 5.43, "change_pct": 0.25},
                    {"name": "Bitcoin", "currency": "USD", "price": 68432.11, "change_pct": 2.11},
                ],
                "headlines": [
                    {"title": "Bolsas operam em alta", "source_name": "Portal Financeiro"}
                ],
                "sources": ["Yahoo Finance via yfinance", "GNews"],
            },
        ):
            texto = responder_consulta_mercado("resumo do mercado financeiro")

        self.assertIsInstance(texto, str)
        self.assertIn("Resumo do mercado financeiro", texto)
        self.assertIn("Dólar", texto)
        self.assertIn("Bolsas operam em alta", texto)


if __name__ == "__main__":
    unittest.main()

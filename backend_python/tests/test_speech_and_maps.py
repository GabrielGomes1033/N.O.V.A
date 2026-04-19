from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import api_server
from core.speech_formatter import (
    data_por_extenso,
    hora_por_extenso,
    moeda_por_extenso,
    preparar_texto_para_fala,
)


class SpeechAndMapsTests(unittest.TestCase):
    def test_moeda_por_extenso_fica_natural(self) -> None:
        self.assertEqual(
            moeda_por_extenso("5.40", moeda="USD"),
            "cinco dolares e quarenta centavos",
        )

    def test_hora_por_extenso_fica_natural(self) -> None:
        self.assertEqual(hora_por_extenso("18:30"), "seis e meia da tarde")

    def test_data_por_extenso_fica_natural(self) -> None:
        self.assertEqual(
            data_por_extenso("19/04/2026"),
            "dezenove de abril de dois mil e vinte e seis",
        )

    def test_preparar_texto_para_fala_converte_moeda_data_hora(self) -> None:
        texto = preparar_texto_para_fala(
            "Agora sao 18:30. Dolar US$ 5.40. Hoje e 19/04/2026."
        )
        self.assertIn("seis e meia da tarde", texto)
        self.assertIn("cinco dolares e quarenta centavos", texto)
        self.assertIn("dezenove de abril de dois mil e vinte e seis", texto)

    def test_detecta_comando_de_localizacao_atual(self) -> None:
        self.assertTrue(api_server._intencao_localizacao_atual("Nova, qual é minha localização"))

    def test_extrai_consulta_onde_fica(self) -> None:
        self.assertEqual(
            api_server._extrair_consulta_onde_fica("Nova onde fica Mercado Municipal"),
            "Mercado Municipal",
        )

    def test_extrai_consulta_rota(self) -> None:
        self.assertEqual(
            api_server._extrair_consulta_rota("Nova como chego em Parque Ibirapuera"),
            "Parque Ibirapuera",
        )

    def test_responde_localizacao_atual_com_reverse_geocode(self) -> None:
        memoria = {
            "ultima_localizacao": "",
            "ultima_latitude": "-23.550520",
            "ultima_longitude": "-46.633308",
            "ultima_localizacao_em": "2026-04-19T08:30:00",
        }
        with patch("api_server.carregar_memoria_usuario", return_value=memoria):
            with patch(
                "api_server.reverse_geocode",
                return_value={"ok": True, "label": "Praça da Sé, São Paulo"},
            ):
                with patch("api_server.salvar_memoria_usuario"):
                    resposta = api_server._responder_localizacao_atual()

        self.assertIn("Praça da Sé, São Paulo", resposta)

    def test_responde_busca_mapa_com_link(self) -> None:
        with patch("api_server.carregar_memoria_usuario", return_value={}):
            with patch(
                "api_server.search_places",
                return_value={
                    "ok": True,
                    "items": [
                        {
                            "name": "Mercado Municipal de São Paulo",
                            "display_name": "Mercado Municipal de São Paulo, Centro Histórico, São Paulo",
                            "maps_url": "https://maps.example/mercado",
                        }
                    ],
                },
            ):
                resposta = api_server._responder_busca_mapa("Mercado Municipal", modo="busca")

        self.assertIn("Mercado Municipal de São Paulo", resposta)
        self.assertIn("https://maps.example/mercado", resposta)


if __name__ == "__main__":
    unittest.main()

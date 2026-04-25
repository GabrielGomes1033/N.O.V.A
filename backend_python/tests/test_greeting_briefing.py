from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import api_server
from core.nova_unica import gerar_briefing_proativo, saudacao_por_periodo


class GreetingBriefingTests(unittest.TestCase):
    def test_saudacao_por_periodo_respeita_madrugada(self) -> None:
        from datetime import datetime

        self.assertEqual(
            saudacao_por_periodo(datetime(2026, 4, 19, 3, 16)),
            "Boa noite",
        )

    def test_briefing_proativo_usa_saudacao_do_periodo(self) -> None:
        with patch("core.nova_unica.saudacao_por_periodo", return_value="Boa noite"):
            with patch(
                "core.nova_unica.carregar_memoria_usuario", return_value={"nome_usuario": "Gabriel"}
            ):
                with patch(
                    "core.nova_unica.consultar_clima", return_value="céu limpo em São Paulo."
                ):
                    with patch("core.nova_unica.cotacoes_financeiras", return_value={}):
                        with patch(
                            "core.nova_unica.formatar_cotacoes_humanas",
                            return_value="Dólar: R$ 5,00 | Euro: R$ 5,90",
                        ):
                            with patch("core.nova_unica.listar_lembretes", return_value=[]):
                                briefing = gerar_briefing_proativo()

        self.assertTrue(briefing.startswith("Boa noite, Gabriel. Aqui está seu briefing:"))

    def test_saudacao_nao_sobrepoe_briefing_automatico(self) -> None:
        briefing = (
            "Boa noite, Gabriel. Aqui está seu briefing:\n"
            "Clima: céu limpo em São Paulo.\n"
            "Mercado: Dólar: R$ 5,00 | Euro: R$ 5,90\n"
            "Lembretes pendentes: nenhum no momento."
        )
        contexto_original = dict(api_server.CONTEXTO)

        try:
            api_server.CONTEXTO.clear()
            api_server.CONTEXTO.update(api_server._novo_contexto())
            api_server.CONTEXTO["nome_usuario"] = "Gabriel"

            with patch("api_server.detectar_intencao", return_value="saudacao"):
                with patch("api_server.responder", return_value="Olá!"):
                    with patch(
                        "api_server.briefing_automatico_se_necessario", return_value=briefing
                    ):
                        with patch(
                            "api_server.carregar_memoria_usuario",
                            return_value={"nome_usuario": "Gabriel"},
                        ):
                            with patch(
                                "api_server.atualizar_perfil_por_interacao", return_value={}
                            ):
                                with patch(
                                    "api_server.aplicar_identidade_nova",
                                    side_effect=lambda texto, **_: texto,
                                ):
                                    with patch("api_server.registrar_interacao_usuario"):
                                        with patch("api_server.registrar_metrica"):
                                            with patch("api_server.registrar_trace"):
                                                resposta = api_server.processar_mensagem("oi")
        finally:
            api_server.CONTEXTO.clear()
            api_server.CONTEXTO.update(contexto_original)

        self.assertEqual(resposta, briefing)
        self.assertEqual(resposta.count("Boa noite"), 1)
        self.assertNotIn("Como posso ajudar você agora?", resposta)


if __name__ == "__main__":
    unittest.main()

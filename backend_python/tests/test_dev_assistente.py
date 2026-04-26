from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.dev_assistente import (
    criar_api,
    criar_api_com_banco,
    criar_painel_admin,
    criar_sistema_estoque,
    criar_site,
    menu_desenvolvedor,
    processar_comando_dev,
)
from core.dev_revisor import analisar_erro, explicar_codigo
from core.nova_unica import orquestrar_consulta
from core.respostas import responder


class DevAssistantTests(unittest.TestCase):
    def test_menu_desenvolvedor_exibe_opcoes(self) -> None:
        texto = menu_desenvolvedor()
        self.assertIn("Modo desenvolvedor da NOVA ativado", texto)
        self.assertIn("Criar sistema de estoque", texto)
        self.assertIn("confirmar criação", texto)

    def test_criar_site_gera_arquivos_na_pasta_informada(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resposta = criar_site("Meu Site", base_dir=tmp)
            pasta = Path(tmp) / "meu_site"
            self.assertTrue((pasta / "index.html").exists())
            self.assertTrue((pasta / "style.css").exists())
            self.assertTrue((pasta / "script.js").exists())
            self.assertIn("Site criado com sucesso", resposta)

    def test_criar_api_fastapi_gera_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resposta = criar_api("Api Interna", stack="fastapi", base_dir=tmp)
            pasta = Path(tmp) / "api_interna"
            requirements = (pasta / "requirements.txt").read_text(encoding="utf-8")
            self.assertIn("fastapi", requirements)
            self.assertIn("API FastAPI", resposta)
            app_py = (pasta / "app.py").read_text(encoding="utf-8")
            self.assertIn('@app.get("/usuarios")', app_py)

    def test_criar_api_com_banco_gera_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resposta = criar_api_com_banco("api estoque", base_dir=tmp)
            pasta = Path(tmp) / "api_estoque"
            app_py = (pasta / "app.py").read_text(encoding="utf-8")
            self.assertIn("sqlite3", app_py)
            self.assertIn("CREATE TABLE IF NOT EXISTS produtos", app_py)
            self.assertIn("API com banco de dados", resposta)

    def test_criar_sistema_estoque_gera_tabela(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            criar_sistema_estoque("estoque loja", base_dir=tmp)
            html = (Path(tmp) / "estoque_loja" / "index.html").read_text(encoding="utf-8")
            self.assertIn("Controle de estoque", html)
            self.assertIn("lista-estoque", html)

    def test_criar_painel_admin_gera_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resposta = criar_painel_admin("painel central", base_dir=tmp)
            html = (Path(tmp) / "painel_central" / "index.html").read_text(encoding="utf-8")
            self.assertIn("NOVA Control Center", html)
            self.assertIn("Painel administrativo", resposta)

    def test_processa_comando_dev_para_correcao_de_erro(self) -> None:
        resposta = processar_comando_dev(
            "Nova, corrija este erro: ModuleNotFoundError: no module named flask"
        )
        self.assertIsInstance(resposta, str)
        self.assertIn("biblioteca não instalada", resposta)

    def test_analisa_erro_de_sintaxe(self) -> None:
        resposta = analisar_erro("SyntaxError: invalid syntax")
        self.assertIn("erro de sintaxe", resposta)

    def test_explica_codigo_html(self) -> None:
        resposta = explicar_codigo(
            "<html><body><form></form><script src='script.js'></script></body></html>"
        )
        self.assertIn("página HTML", resposta)
        self.assertIn("formulário", resposta)

    def test_analisar_erro_inclui_linha_quando_houver_traceback(self) -> None:
        resposta = analisar_erro(
            'Traceback (most recent call last):\n  File "/tmp/app.py", line 22, in <module>\n    import x\nModuleNotFoundError: No module named x'
        )
        self.assertIn("linha 22", resposta)

    def test_fluxo_com_confirmacao_cria_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contexto = {}
            resposta = processar_comando_dev(
                "Nova, monte um site chamado Portal Alpha",
                contexto=contexto,
                base_dir=tmp,
            )
            self.assertIn("Posso criar um site", resposta)
            self.assertIn("portal_alpha", resposta)
            self.assertIn("dev_pending_action", contexto)

            resposta_confirmada = processar_comando_dev(
                "confirmar criação",
                contexto=contexto,
                base_dir=tmp,
            )
            self.assertIn("Site criado com sucesso", resposta_confirmada)
            self.assertNotIn("dev_pending_action", contexto)
            self.assertTrue((Path(tmp) / "portal_alpha" / "index.html").exists())

    def test_fluxo_cancelamento_limpa_pendencia(self) -> None:
        contexto = {}
        resposta = processar_comando_dev("Nova, crie uma API", contexto=contexto)
        self.assertIn("Posso criar", resposta)
        cancelamento = processar_comando_dev("cancelar criação", contexto=contexto)
        self.assertIn("Criação cancelada", cancelamento)
        self.assertNotIn("dev_pending_action", contexto)

    def test_comando_api_com_banco_pede_confirmacao(self) -> None:
        contexto = {}
        resposta = processar_comando_dev(
            "Nova, quero criar API com banco de dados", contexto=contexto
        )
        self.assertIn("API com banco de dados", resposta)

    def test_orquestrador_responde_modo_dev(self) -> None:
        with patch(
            "core.nova_unica.processar_comando_dev",
            return_value="Modo desenvolvedor da NOVA ativado.",
        ):
            resposta = orquestrar_consulta("Nova, modo desenvolvedor")
        self.assertEqual(resposta, {"resposta": "Modo desenvolvedor da NOVA ativado."})

    def test_responder_prioriza_fluxo_dev(self) -> None:
        with patch(
            "core.respostas.processar_comando_dev",
            return_value="Site criado com sucesso na pasta: site_nova",
        ):
            resposta = responder("Nova, criar site", contexto={})
        self.assertIn("Site criado com sucesso", resposta)


if __name__ == "__main__":
    unittest.main()

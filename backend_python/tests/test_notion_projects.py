from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.notion_projects import (
    _montar_propriedades_data_source,
    interpretar_pedido_criacao_projeto,
    provider_padrao_projeto,
)


class PedidoCriacaoProjetoTests(unittest.TestCase):
    def test_extrai_nome_com_wake_word_e_notion(self) -> None:
        pedido = interpretar_pedido_criacao_projeto(
            'Nova, crie um novo projeto no Notion chamado "Atlas Comercial"'
        )
        self.assertTrue(pedido.matched)
        self.assertEqual(pedido.provider, "notion")
        self.assertTrue(pedido.explicit_provider)
        self.assertEqual(pedido.project_name, "Atlas Comercial")

    def test_extrai_nome_de_frase_curta_natural(self) -> None:
        pedido = interpretar_pedido_criacao_projeto("Novo projeto Planejamento Q4")
        self.assertTrue(pedido.matched)
        self.assertEqual(pedido.project_name, "Planejamento Q4")

    def test_forca_drive_quando_mencionado(self) -> None:
        pedido = interpretar_pedido_criacao_projeto(
            "Crie um projeto no Drive chamado Portal do Cliente"
        )
        self.assertTrue(pedido.matched)
        self.assertEqual(pedido.provider, "drive")
        self.assertTrue(pedido.explicit_provider)
        self.assertEqual(pedido.project_name, "Portal do Cliente")

    def test_detecta_intencao_mesmo_sem_nome(self) -> None:
        pedido = interpretar_pedido_criacao_projeto("Nova, crie um novo projeto")
        self.assertTrue(pedido.matched)
        self.assertEqual(pedido.project_name, "")

    def test_extrai_campos_extras_em_linguagem_natural(self) -> None:
        pedido = interpretar_pedido_criacao_projeto(
            "Nova, crie um projeto chamado Portal do Cliente na área Comercial "
            "com prioridade alta com descrição MVP B2B com responsável Gabriel Gomes "
            "e link https://exemplo.com"
        )
        self.assertTrue(pedido.matched)
        self.assertEqual(pedido.project_name, "Portal do Cliente")
        self.assertEqual(pedido.area, "Comercial")
        self.assertEqual(pedido.priority.lower(), "alta")
        self.assertEqual(pedido.description, "MVP B2B")
        self.assertEqual(pedido.responsible, "Gabriel Gomes")
        self.assertEqual(pedido.link, "https://exemplo.com")

    def test_extrai_nome_quando_descricao_entre_aspas_vem_primeiro(self) -> None:
        pedido = interpretar_pedido_criacao_projeto(
            'Nova, crie um projeto com descrição "MVP B2B" chamado "Portal do Cliente"'
        )
        self.assertTrue(pedido.matched)
        self.assertEqual(pedido.project_name, "Portal do Cliente")
        self.assertEqual(pedido.description, "MVP B2B")

    def test_provider_padrao_prefere_notion_quando_configurado(self) -> None:
        with patch.dict(
            os.environ,
            {
                "NOVA_NOTION_TOKEN": "secret",
                "NOVA_NOTION_PROJECTS_DATA_SOURCE_ID": "abc123",
                "NOVA_PROJECT_PROVIDER": "",
            },
            clear=False,
        ):
            self.assertEqual(provider_padrao_projeto(), "notion")

    def test_monta_propriedades_extras_do_data_source(self) -> None:
        schema = {
            "Nome": {"type": "title"},
            "Status": {"type": "status", "status": {"options": [{"name": "Backlog"}]}},
            "Descrição": {"type": "rich_text"},
            "Área": {"type": "select", "select": {"options": [{"name": "Comercial"}]}},
            "Prioridade": {"type": "select", "select": {"options": [{"name": "Alta"}]}},
            "Responsável": {"type": "people"},
            "Link": {"type": "url"},
        }
        with patch.dict(
            os.environ,
            {
                "NOVA_NOTION_PROJECTS_TITLE_PROPERTY": "Nome",
                "NOVA_NOTION_PROJECTS_STATUS_PROPERTY": "Status",
                "NOVA_NOTION_PROJECTS_STATUS_VALUE": "Backlog",
                "NOVA_NOTION_PROJECTS_DESCRIPTION_PROPERTY": "Descrição",
                "NOVA_NOTION_PROJECTS_AREA_PROPERTY": "Área",
                "NOVA_NOTION_PROJECTS_PRIORITY_PROPERTY": "Prioridade",
                "NOVA_NOTION_PROJECTS_RESPONSIBLE_PROPERTY": "Responsável",
                "NOVA_NOTION_PROJECTS_LINK_PROPERTY": "Link",
            },
            clear=False,
        ):
            with patch("core.notion_projects._resolver_usuario_notion", return_value=("user_123", "Gabriel Gomes")):
                ok, payload, filled_fields, warnings = _montar_propriedades_data_source(
                    project_name="Atlas Comercial",
                    description="Descrição padrão",
                    details={
                        "description": "MVP B2B",
                        "area": "Comercial",
                        "priority": "alta",
                        "responsible": "Gabriel Gomes",
                        "link": "https://exemplo.com",
                    },
                    properties=schema,
                )

        self.assertTrue(ok)
        self.assertEqual(payload["Nome"]["title"][0]["text"]["content"], "Atlas Comercial")
        self.assertEqual(payload["Status"]["status"]["name"], "Backlog")
        self.assertEqual(payload["Descrição"]["rich_text"][0]["text"]["content"], "MVP B2B")
        self.assertEqual(payload["Área"]["select"]["name"], "Comercial")
        self.assertEqual(payload["Prioridade"]["select"]["name"], "Alta")
        self.assertEqual(payload["Responsável"]["people"][0]["id"], "user_123")
        self.assertEqual(payload["Link"]["url"], "https://exemplo.com")
        self.assertIn("Descrição", filled_fields)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()

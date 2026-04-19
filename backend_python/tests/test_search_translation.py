from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.orchestrator import NovaOrchestrator, RuleBasedLLM, build_default_tools
from core.translation_service import (
    parse_search_translation_request,
    parse_text_translation_request,
    translate_text,
)
from memory.sqlite_store import MemoryStore


class SearchTranslationTests(unittest.TestCase):
    def test_parse_search_translation_request_detects_target_language(self) -> None:
        pedido = parse_search_translation_request(
            "traduza essa pesquisa para ingles"
        )
        self.assertIsNotNone(pedido)
        self.assertEqual(pedido["target_language"], "en")

        atalho = parse_search_translation_request("em portugues")
        self.assertIsNotNone(atalho)
        self.assertEqual(atalho["target_language"], "pt")

        voz = parse_search_translation_request(
            "me fale essa pesquisa em espanhol"
        )
        self.assertIsNotNone(voz)
        self.assertEqual(voz["target_language"], "es")

    def test_parse_text_translation_request_extracts_explicit_text(self) -> None:
        pedido = parse_text_translation_request(
            'traduza "Bom dia, mundo" para ingles'
        )
        self.assertIsNotNone(pedido)
        self.assertEqual(pedido["source_text"], "Bom dia, mundo")
        self.assertEqual(pedido["target_language"], "en")

        pedido_com_dois_pontos = parse_text_translation_request(
            "traduza para portugues: Good morning"
        )
        self.assertIsNotNone(pedido_com_dois_pontos)
        self.assertEqual(pedido_com_dois_pontos["source_text"], "Good morning")
        self.assertEqual(pedido_com_dois_pontos["target_language"], "pt")

    def test_translate_last_search_after_web_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(Path(tmpdir) / "nova_memory_test.db")
            orchestrator = NovaOrchestrator(
                memory=memory,
                tools=build_default_tools(memory),
                llm=RuleBasedLLM(),
            )

            with patch(
                "core.orchestrator.integration_search_web",
                return_value={
                    "ok": True,
                    "query": "carros eletricos",
                    "summary": "Electric cars reduce emissions and depend on battery infrastructure.",
                    "sources": ["https://example.com/cars"],
                },
            ):
                pesquisa = orchestrator.handle(
                    "tester",
                    "pesquise sobre carros eletricos",
                )

            self.assertIn("Pesquisei", pesquisa["reply"])
            self.assertIn("Responda sim ou nao", pesquisa["reply"])

            with patch(
                "core.orchestrator.translate_text",
                return_value={
                    "ok": True,
                    "translated_text": "Electric cars reduce emissions and depend on battery infrastructure.",
                    "provider": "mock",
                    "target_language": "en",
                },
            ):
                traducao = orchestrator.handle(
                    "tester",
                    "traduza essa pesquisa para ingles",
                )

            self.assertIn("Traducao da ultima pesquisa para ingles", traducao["reply"])
            self.assertIn("Electric cars reduce emissions", traducao["reply"])
            memory.close()

    def test_search_reply_can_offer_translation_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(Path(tmpdir) / "nova_memory_test.db")
            orchestrator = NovaOrchestrator(
                memory=memory,
                tools=build_default_tools(memory),
                llm=RuleBasedLLM(),
            )

            with patch(
                "core.orchestrator.integration_search_web",
                return_value={
                    "ok": True,
                    "query": "electric cars",
                    "summary": "Electric cars reduce emissions.",
                    "sources": ["https://example.com/cars"],
                },
            ):
                pesquisa = orchestrator.handle(
                    "tester",
                    "pesquise sobre electric cars",
                )

            with patch(
                "core.orchestrator.translate_text",
                return_value={
                    "ok": True,
                    "translated_text": "Carros eletricos reduzem emissoes.",
                    "provider": "mock",
                    "target_language": "pt",
                },
            ):
                traducao = orchestrator.handle(
                    "tester",
                    "sim",
                )

            self.assertIn("traduzir essa pesquisa para portugues", pesquisa["reply"].lower())
            self.assertIn("Traducao da ultima pesquisa para portugues", traducao["reply"])
            self.assertIn("Carros eletricos reduzem emissoes", traducao["reply"])
            memory.close()

    def test_search_reply_translation_offer_can_be_declined(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(Path(tmpdir) / "nova_memory_test.db")
            orchestrator = NovaOrchestrator(
                memory=memory,
                tools=build_default_tools(memory),
                llm=RuleBasedLLM(),
            )

            with patch(
                "core.orchestrator.integration_search_web",
                return_value={
                    "ok": True,
                    "query": "electric cars",
                    "summary": "Electric cars reduce emissions.",
                    "sources": ["https://example.com/cars"],
                },
            ):
                orchestrator.handle(
                    "tester",
                    "pesquise sobre electric cars",
                )

            resposta = orchestrator.handle(
                "tester",
                "nao",
            )

            self.assertIn("Mantive a pesquisa no idioma original", resposta["reply"])
            memory.close()

    def test_translate_last_search_without_previous_search_returns_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(Path(tmpdir) / "nova_memory_test.db")
            orchestrator = NovaOrchestrator(
                memory=memory,
                tools=build_default_tools(memory),
                llm=RuleBasedLLM(),
            )

            resposta = orchestrator.handle(
                "tester",
                "traduza essa pesquisa para ingles",
            )

            self.assertIn("ainda nao tenho uma pesquisa recente", resposta["reply"])
            memory.close()

    def test_translate_last_search_persists_across_new_orchestrator_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nova_memory_test.db"

            memory1 = MemoryStore(db_path)
            orchestrator1 = NovaOrchestrator(
                memory=memory1,
                tools=build_default_tools(memory1),
                llm=RuleBasedLLM(),
            )

            with patch(
                "core.orchestrator.integration_search_web",
                return_value={
                    "ok": True,
                    "query": "electric cars",
                    "summary": "Electric cars use battery power for propulsion.",
                    "sources": ["https://example.com/cars"],
                },
            ):
                orchestrator1.handle(
                    "tester",
                    "pesquise sobre electric cars",
                )
            memory1.close()

            memory2 = MemoryStore(db_path)
            orchestrator2 = NovaOrchestrator(
                memory=memory2,
                tools=build_default_tools(memory2),
                llm=RuleBasedLLM(),
            )

            with patch(
                "core.orchestrator.translate_text",
                return_value={
                    "ok": True,
                    "translated_text": "Carros eletricos usam bateria para propulsao.",
                    "provider": "mock",
                    "target_language": "pt",
                },
            ):
                resposta = orchestrator2.handle(
                    "tester",
                    "me fale essa pesquisa em portugues",
                )

            self.assertIn("Traducao da ultima pesquisa para portugues", resposta["reply"])
            self.assertIn("Carros eletricos usam bateria", resposta["reply"])
            memory2.close()

    def test_translate_explicit_text_in_chat(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(Path(tmpdir) / "nova_memory_test.db")
            orchestrator = NovaOrchestrator(
                memory=memory,
                tools=build_default_tools(memory),
                llm=RuleBasedLLM(),
            )

            with patch(
                "core.orchestrator.translate_text",
                return_value={
                    "ok": True,
                    "translated_text": "Good morning",
                    "provider": "mock",
                    "target_language": "en",
                },
            ):
                resposta = orchestrator.handle(
                    "tester",
                    'traduza "Bom dia" para ingles',
                )

            self.assertIn("Traducao do texto para ingles", resposta["reply"])
            self.assertIn("Good morning", resposta["reply"])
            memory.close()

    def test_translate_text_without_explicit_source_returns_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(Path(tmpdir) / "nova_memory_test.db")
            orchestrator = NovaOrchestrator(
                memory=memory,
                tools=build_default_tools(memory),
                llm=RuleBasedLLM(),
            )

            resposta = orchestrator.handle(
                "tester",
                "traduza isso para ingles",
            )

            self.assertIn("Me mande o texto junto do pedido", resposta["reply"])
            memory.close()

    def test_translate_text_uses_next_provider_when_first_is_unavailable(self) -> None:
        with patch(
            "core.translation_service._translate_via_libretranslate",
            return_value={"ok": False, "error": "translate_api_not_configured"},
        ):
            with patch(
                "core.translation_service._translate_via_google_public",
                return_value={
                    "ok": True,
                    "translated_text": "Hello world",
                    "provider": "mock_google",
                    "detected_source_language": "pt",
                },
            ):
                result = translate_text(
                    "Ola mundo",
                    target_language="en",
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["translated_text"], "Hello world")
        self.assertEqual(result["target_language"], "en")


if __name__ == "__main__":
    unittest.main()

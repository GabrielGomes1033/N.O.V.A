from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.orchestrator import NovaOrchestrator, RuleBasedLLM, build_default_tools
from memory.sqlite_store import MemoryStore
from routes.chat_routes import handle_chat_post


class JarvisPhase1Tests(unittest.TestCase):
    def test_memory_store_persists_and_searches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            store.save("gabriel", "perfil", "Nome preferido: Gabriel", importance=4, scope="perfil")
            store.save("gabriel", "projeto", "Projeto NOVA Jarvis em andamento", importance=3)

            recentes = store.search_recent("gabriel", limit=5)
            busca = store.search("gabriel", "Jarvis", limit=5)

        self.assertEqual(len(recentes), 2)
        self.assertEqual(len(busca), 1)
        self.assertEqual(busca[0]["category"], "projeto")

    def test_orchestrator_requires_approval_for_home_control(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            orchestrator = NovaOrchestrator(
                memory=store,
                tools=build_default_tools(store),
                llm=RuleBasedLLM(),
            )

            result = orchestrator.handle(
                "gabriel",
                "ligar light.sala agora",
                mode="normal",
            )

        self.assertTrue(result["approval_needed"])
        self.assertEqual(result["tool_name"], "control_home")

    def test_orchestrator_saves_and_recalls_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            orchestrator = NovaOrchestrator(
                memory=store,
                tools=build_default_tools(store),
                llm=RuleBasedLLM(),
            )

            save_result = orchestrator.handle(
                "gabriel",
                "lembre que meu framework favorito e Flutter",
                mode="normal",
            )
            recall_result = orchestrator.handle(
                "gabriel",
                "o que voce lembra sobre framework favorito",
                mode="normal",
            )

        self.assertFalse(save_result["approval_needed"])
        self.assertEqual(save_result["tool_name"], "save_memory")
        self.assertIn("Flutter", recall_result["reply"])

    def test_legacy_chat_route_accepts_new_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            orchestrator = NovaOrchestrator(
                memory=store,
                tools=build_default_tools(store),
                llm=RuleBasedLLM(),
            )

            import routes.chat_routes as chat_routes_module

            old_getter = chat_routes_module.get_default_orchestrator
            chat_routes_module.get_default_orchestrator = lambda: orchestrator
            payloads: list[dict] = []

            try:
                handled = handle_chat_post(
                    path="/chat",
                    body={"user_id": "gabriel", "text": "resuma NOVA precisa de memoria e acoes"},
                    process_message=lambda message: f"legacy:{message}",
                    send_json=payloads.append,
                )
            finally:
                chat_routes_module.get_default_orchestrator = old_getter

        self.assertTrue(handled)
        self.assertEqual(len(payloads), 1)
        self.assertTrue(payloads[0]["ok"])
        self.assertEqual(payloads[0]["tool_name"], "summarize_text")

    def test_structured_chat_keeps_sensitive_approval_between_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            orchestrator = NovaOrchestrator(
                memory=store,
                tools=build_default_tools(store),
                llm=RuleBasedLLM(),
            )

            import routes.chat_routes as chat_routes_module

            old_getter = chat_routes_module.get_default_orchestrator
            old_pending = dict(chat_routes_module._PENDING_STRUCTURED_CHAT)
            chat_routes_module.get_default_orchestrator = lambda: orchestrator
            chat_routes_module._PENDING_STRUCTURED_CHAT.clear()
            payloads: list[dict] = []

            try:
                first = handle_chat_post(
                    path="/chat",
                    body={"user_id": "gabriel", "text": "ligar light.sala agora"},
                    process_message=lambda message: f"legacy:{message}",
                    send_json=payloads.append,
                )
                second = handle_chat_post(
                    path="/chat",
                    body={"user_id": "gabriel", "text": "sim"},
                    process_message=lambda message: f"legacy:{message}",
                    send_json=payloads.append,
                )
            finally:
                chat_routes_module.get_default_orchestrator = old_getter
                chat_routes_module._PENDING_STRUCTURED_CHAT.clear()
                chat_routes_module._PENDING_STRUCTURED_CHAT.update(old_pending)

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(len(payloads), 2)
        self.assertTrue(payloads[0]["approval_needed"])
        self.assertIn("control_home", payloads[0]["reply"])
        self.assertIn("reply", payloads[1])


if __name__ == "__main__":
    unittest.main()

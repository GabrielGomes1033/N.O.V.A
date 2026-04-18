from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.jarvis_chat_bridge as bridge
from core.orchestrator import NovaOrchestrator, RuleBasedLLM, build_default_tools
from memory.sqlite_store import MemoryStore


class JarvisBridgeTests(unittest.TestCase):
    def test_pending_sensitive_tool_can_be_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            orchestrator = NovaOrchestrator(
                memory=store,
                tools=build_default_tools(store),
                llm=RuleBasedLLM(),
            )
            original = bridge.get_default_orchestrator
            bridge.get_default_orchestrator = lambda: orchestrator
            context = {'nome_usuario': 'gabriel'}

            try:
                result = bridge.try_jarvis_tool_flow(
                    'ligar light.sala agora',
                    context,
                    mode='normal',
                )
                confirm = bridge.process_pending_tool_confirmation(
                    'sim',
                    context,
                    mode='normal',
                )
            finally:
                bridge.get_default_orchestrator = original

        self.assertIsNotNone(result)
        self.assertTrue(result['approval_needed'])
        self.assertIsInstance(context.get('jarvis_tool_pending'), type(None))
        self.assertTrue(confirm['handled'])
        self.assertIn('reply', confirm)

    def test_status_snapshot_lists_tools(self) -> None:
        snapshot = bridge.jarvis_status_snapshot()
        self.assertTrue(snapshot['ok'])
        self.assertGreaterEqual(snapshot['tools_total'], 1)
        self.assertIn('search_web', snapshot['tools'])


if __name__ == '__main__':
    unittest.main()

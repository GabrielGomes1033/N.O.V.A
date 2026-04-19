from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.google_calendar import looks_like_calendar_request, parse_calendar_event_request
from core.orchestrator import NovaOrchestrator, RuleBasedLLM, build_default_tools
from memory.sqlite_store import MemoryStore


class GoogleCalendarScheduleTests(unittest.TestCase):
    def test_parser_accepts_natural_time_format(self) -> None:
        parsed = parse_calendar_event_request(
            "Agende reuniao com cliente amanha as 15h",
            now=datetime(2026, 4, 23, 10, 0),
        )

        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["title"], "reuniao com cliente")
        self.assertEqual(parsed["start_at"], "2026-04-24T15:00")
        self.assertEqual(parsed["end_at"], "2026-04-24T16:00")
        self.assertTrue(any("1 hora" in item for item in parsed["assumptions"]))
        self.assertTrue(looks_like_calendar_request("Agende reuniao com cliente amanha as 15h"))

    def test_orchestrator_requires_approval_for_calendar_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            orchestrator = NovaOrchestrator(
                memory=store,
                tools=build_default_tools(store),
                llm=RuleBasedLLM(),
            )

            result = orchestrator.handle(
                "gabriel",
                "agende reuniao com cliente amanha as 15:00",
                mode="normal",
            )

        self.assertTrue(result["approval_needed"])
        self.assertEqual(result["tool_name"], "schedule_calendar_event")
        self.assertIn("Google Agenda", result["reply"])

    def test_orchestrator_executes_calendar_schedule_when_approved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")
            orchestrator = NovaOrchestrator(
                memory=store,
                tools=build_default_tools(store),
                llm=RuleBasedLLM(),
            )

            with patch(
                "core.orchestrator.create_google_calendar_event",
                return_value={
                    "ok": True,
                    "provider": "google_calendar",
                    "calendar_id": "primary",
                    "event_id": "evt_123",
                    "html_link": "https://calendar.google.com/event?eid=evt_123",
                    "title": "reuniao com cliente",
                    "start_at": "2026-04-24T15:00",
                    "end_at": "2026-04-24T16:00",
                    "timezone": "America/Sao_Paulo",
                },
            ):
                result = orchestrator.handle(
                    "gabriel",
                    "agende reuniao com cliente amanha as 15h",
                    mode="normal",
                    auto_approve=True,
                )
                semantic = orchestrator.vector_store.search("gabriel", "reuniao cliente", limit=3)
                recent = store.search_recent("gabriel", limit=10)

        self.assertFalse(result["approval_needed"])
        self.assertEqual(result["tool_name"], "schedule_calendar_event")
        self.assertIn("Evento agendado na Google Agenda", result["reply"])
        self.assertIn("calendar.google.com", result["reply"])
        self.assertTrue(any(item.get("category") == "agenda" for item in recent))
        self.assertTrue(semantic)
        self.assertIn("reuniao com cliente", semantic[0]["content"].lower())


if __name__ == "__main__":
    unittest.main()

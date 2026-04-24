from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.app import create_app
from core import runtime_guard


class ApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_guard._BUCKETS.clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        self.client.close()
        runtime_guard._BUCKETS.clear()

    def test_health_endpoint_returns_core_metadata(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["entrypoint"], "fastapi_app")
        self.assertEqual(payload["service"], "nova-api")
        self.assertIn("/chat", payload["endpoints"])

    def test_voice_status_rate_limit_returns_429(self) -> None:
        last_ok = None
        for _ in range(120):
            last_ok = self.client.get("/voice/status")

        self.assertIsNotNone(last_ok)
        assert last_ok is not None
        self.assertEqual(last_ok.status_code, 200)

        limited = self.client.get("/voice/status")

        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["detail"]["error"], "rate_limited")

    def test_cors_preflight_options_still_passes_after_get_rate_limit(self) -> None:
        for _ in range(121):
            self.client.get("/voice/status")

        response = self.client.options(
            "/voice/status",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "https://example.com")
        self.assertIn("GET", response.headers["access-control-allow-methods"])


if __name__ == "__main__":
    unittest.main()

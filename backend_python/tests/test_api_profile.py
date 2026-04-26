from __future__ import annotations

from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.api_config import DEFAULT_API_PORT
from core.api_profile import NOVA_API_VERSION, build_api_health


class ApiProfileTests(unittest.TestCase):
    def test_build_api_health_exposes_core_metadata(self):
        with patch.dict(
            os.environ,
            {
                "NOVA_API_PORT": "",
                "PORT": "",
            },
            clear=False,
        ):
            payload = build_api_health(entrypoint="test")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "nova-api")
        self.assertEqual(payload["assistant"], "NOVA")
        self.assertEqual(payload["api_version"], NOVA_API_VERSION)
        self.assertEqual(payload["entrypoint"], "test")
        self.assertIn("/chat", payload["endpoints"])
        self.assertTrue(payload["capabilities"]["chat"])
        self.assertTrue(payload["capabilities"]["semantic_memory"])
        self.assertTrue(payload["capabilities"]["calendar"])
        self.assertEqual(payload["platform_support"]["android"], "full")
        self.assertEqual(
            payload["client_hints"]["desktop_base_url"],
            f"http://127.0.0.1:{DEFAULT_API_PORT}",
        )

    def test_build_api_health_uses_env_port_in_client_hints(self):
        with patch.dict(
            os.environ,
            {
                "NOVA_API_PORT": "8119",
                "PORT": "",
            },
            clear=False,
        ):
            payload = build_api_health(entrypoint="test")

        self.assertEqual(
            payload["client_hints"]["android_emulator_base_url"],
            "http://10.0.2.2:8119",
        )
        self.assertEqual(
            payload["client_hints"]["desktop_base_url"],
            "http://127.0.0.1:8119",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.api_profile import NOVA_API_VERSION, build_api_health


class ApiProfileTests(unittest.TestCase):
    def test_build_api_health_exposes_core_metadata(self):
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


if __name__ == "__main__":
    unittest.main()

"""网关线路测速测试：排序、推荐最低延迟、不可达置底/无推荐。用 mock 探测，不打真实网络。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import panghu_ai_client as installer  # noqa: E402


class GatewayLatencyTests(unittest.TestCase):
    def test_recommend_lowest_latency_and_sort(self):
        endpoints = [
            {"id": "a", "label": "A", "url": "https://a"},
            {"id": "b", "label": "B", "url": "https://b"},
            {"id": "c", "label": "C", "url": "https://c"},
        ]
        fake = {
            "https://a": {"reachable": True, "latency_ms": 120, "status": 200, "error": ""},
            "https://b": {"reachable": True, "latency_ms": 45, "status": 200, "error": ""},
            "https://c": {"reachable": False, "latency_ms": None, "status": None, "error": "timeout"},
        }
        with patch.object(installer, "_measure_endpoint_latency", side_effect=lambda url, timeout=8: fake[url]):
            result = installer.measure_gateway_latency(endpoints)
        self.assertEqual(result["recommended_id"], "b")
        self.assertEqual(result["recommended_url"], "https://b")
        self.assertEqual(result["endpoints"][0]["id"], "b")  # 最快在前
        self.assertEqual(result["endpoints"][-1]["id"], "c")  # 不可达置底

    def test_all_unreachable_no_recommend(self):
        endpoints = [{"id": "x", "label": "X", "url": "https://x"}]
        fake = {"reachable": False, "latency_ms": None, "status": None, "error": "down"}
        with patch.object(installer, "_measure_endpoint_latency", side_effect=lambda url, timeout=8: fake):
            result = installer.measure_gateway_latency(endpoints)
        self.assertIsNone(result["recommended_id"])
        self.assertIsNone(result["recommended_url"])

    def test_default_candidates_include_primary(self):
        ids = {e["id"] for e in installer.GATEWAY_ENDPOINT_CANDIDATES}
        self.assertIn("primary", ids)
        primary = next(e for e in installer.GATEWAY_ENDPOINT_CANDIDATES if e["id"] == "primary")
        self.assertEqual(primary["url"], installer.DEFAULT_BASE_URL)


if __name__ == "__main__":
    unittest.main()

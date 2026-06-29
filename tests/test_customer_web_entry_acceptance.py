import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import customer_web_entry_acceptance  # noqa: E402


class CustomerWebEntryAcceptanceTests(unittest.TestCase):
    def test_pywebview_missing_blocks_customer_web_flow_pages(self) -> None:
        with patch.object(customer_web_entry_acceptance.installer, "embedded_webview_available", return_value=False), \
             patch.object(importlib.util, "find_spec", return_value=None):
            report = customer_web_entry_acceptance.build_report()

        self.assertEqual(report["web_entry_status"], "blocked")
        self.assertFalse(report["runtime_webview_loaded"])
        flow_pages = [page for page in report["pages"] if page["requires_customer_web_flow"]]
        self.assertGreater(len(flow_pages), 0)
        register_page = next(page for page in report["pages"] if page["module"] == "login_gate" and page["item"] == "register")
        self.assertIn("/register?invite=LOCAL-ACCEPTANCE", register_page["url"])
        for page in flow_pages:
            self.assertEqual(page["entry_status"], "blocked")
            self.assertIn("pywebview", "\n".join(page["blocking_gaps"]))

    def test_runtime_loaded_marks_public_mapped_customer_pages_ready(self) -> None:
        with patch.object(customer_web_entry_acceptance.installer, "embedded_webview_available", return_value=True), \
             patch.object(importlib.util, "find_spec", return_value=object()):
            report = customer_web_entry_acceptance.build_report()

        self.assertEqual(report["web_entry_status"], "ready")
        self.assertTrue(report["runtime_webview_loaded"])
        register_page = next(page for page in report["pages"] if page["module"] == "login_gate" and page["item"] == "register")
        self.assertEqual(register_page["entry_status"], "ready")
        self.assertEqual(register_page["embedded_title"], "胖虎AI 推广返佣")
        for page in report["pages"]:
            self.assertIn(page["entry_status"], {"ready", "blocked"})
            if page["requires_customer_web_flow"]:
                self.assertTrue(page["embedded_title"])
                self.assertEqual(page["entry_status"], "ready")
                self.assertEqual(page["blocking_gaps"], [])

    def test_sim_subdomain_is_allowed_for_sms_control_center(self) -> None:
        self.assertTrue(customer_web_entry_acceptance.public_customer_domain_allowed("https://sim.aitokenapi.cc"))
        self.assertFalse(customer_web_entry_acceptance.public_customer_domain_allowed("https://example.com/services"))

    def test_script_outputs_json_without_opening_browser(self) -> None:
        with patch.object(customer_web_entry_acceptance.installer, "embedded_webview_available", return_value=False), \
             patch.object(importlib.util, "find_spec", return_value=None), \
             patch("builtins.print") as fake_print:
            exit_code = customer_web_entry_acceptance.main()

        self.assertEqual(exit_code, 1)
        payload = json.loads(fake_print.call_args.args[0])
        self.assertEqual(payload["web_entry_status"], "blocked")


if __name__ == "__main__":
    unittest.main()

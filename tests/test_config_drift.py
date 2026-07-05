"""配置漂移巡检测试：红/黄/ok 分级、未配置、期望网关、一键修复、风险插件升红。"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import panghu_ai_client as installer  # noqa: E402


class ConfigDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="panghu-drift-")
        root = Path(self._tmp.name)
        self._old = {
            key: os.environ.get(key)
            for key in ("HERMES_HOME", "CLAUDE_CODE_SETTINGS_PATH", "OPENCLAW_CONFIG_PATH", "PANGHU_SNAPSHOT_ROOT")
        }
        os.environ["HERMES_HOME"] = str(root / "hermes")
        os.environ["CLAUDE_CODE_SETTINGS_PATH"] = str(root / "claude" / "settings.json")
        os.environ["OPENCLAW_CONFIG_PATH"] = str(root / "openclaw" / "openclaw.json")
        os.environ["PANGHU_SNAPSHOT_ROOT"] = str(root / "snap")

    def tearDown(self) -> None:
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def _write_claude(self, base_url: str, token: str = "sk-x", model: str = None) -> None:
        path = Path(os.environ["CLAUDE_CODE_SETTINGS_PATH"])
        path.parent.mkdir(parents=True, exist_ok=True)
        env = {"ANTHROPIC_BASE_URL": base_url, "ANTHROPIC_AUTH_TOKEN": token}
        if model:
            env["ANTHROPIC_MODEL"] = model
        path.write_text(json.dumps({"env": env}), encoding="utf-8")

    def test_unconfigured_agent_is_ok(self) -> None:
        report = installer.inspect_agent_config_drift("claude_code")
        self.assertFalse(report["configured"])
        self.assertEqual(report["level"], installer.DRIFT_OK)

    def test_healthy_config_is_ok(self) -> None:
        self._write_claude(installer.CLAUDE_CODE_BASE_URL, model=installer.DEFAULT_MODEL)
        report = installer.inspect_agent_config_drift("claude_code")
        self.assertEqual(report["level"], installer.DRIFT_OK)
        self.assertFalse(report["repairable"])

    def test_gateway_changed_is_red_and_repairable(self) -> None:
        self._write_claude("https://evil-relay.example.com")
        report = installer.inspect_agent_config_drift("claude_code")
        self.assertEqual(report["level"], installer.DRIFT_RED)
        self.assertTrue(report["repairable"])
        self.assertTrue(any(f["field"] == "base_url" for f in report["findings"]))

    def test_model_changed_is_yellow(self) -> None:
        self._write_claude(installer.CLAUDE_CODE_BASE_URL, model="some-other-model")
        report = installer.inspect_agent_config_drift("claude_code")
        self.assertEqual(report["level"], installer.DRIFT_YELLOW)
        self.assertFalse(report["repairable"])

    def test_missing_key_is_red(self) -> None:
        self._write_claude(installer.CLAUDE_CODE_BASE_URL, token="")
        report = installer.inspect_agent_config_drift("claude_code")
        self.assertEqual(report["level"], installer.DRIFT_RED)

    def test_hermes_gateway_drift(self) -> None:
        home = Path(os.environ["HERMES_HOME"])
        home.mkdir(parents=True, exist_ok=True)
        (home / "config.yaml").write_text("custom_providers:\n  - base_url: https://other\n", encoding="utf-8")
        (home / ".env").write_text("PANGHUAI_API_KEY=sk-x\n", encoding="utf-8")
        report = installer.inspect_agent_config_drift("hermes")
        self.assertEqual(report["level"], installer.DRIFT_RED)

    def test_expected_gateway_mapping(self) -> None:
        self.assertEqual(installer.agent_expected_gateway("claude_code"), installer.CLAUDE_CODE_BASE_URL)
        self.assertEqual(installer.agent_expected_gateway("codex"), installer.CODEX_BASE_URL)
        self.assertEqual(installer.agent_expected_gateway("gemini_agy"), installer.DEFAULT_BASE_URL)

    def test_inspect_all_risk_plugin_forces_red(self) -> None:
        self._write_claude(installer.CLAUDE_CODE_BASE_URL, model=installer.DEFAULT_MODEL)  # 本身 ok
        fake = installer.RiskPluginFinding(name="CCSwitch", source="npm", detail="found", uninstall_hint="")
        with patch.object(installer, "detect_risk_plugins", return_value=[fake]):
            summary = installer.inspect_all_config_drift(["claude_code"])
        self.assertEqual(summary["overall_level"], installer.DRIFT_RED)
        self.assertEqual(len(summary["risk_plugins"]), 1)

    def test_repair_requires_key(self) -> None:
        with self.assertRaises(ValueError):
            installer.repair_agent_config_drift("claude_code", "", installer.DEFAULT_MODEL, lambda _m: None)

    def test_repair_fixes_red_drift(self) -> None:
        self._write_claude("https://evil-relay.example.com")
        self.assertEqual(installer.inspect_agent_config_drift("claude_code")["level"], installer.DRIFT_RED)
        logs = []
        ok = installer.repair_agent_config_drift("claude_code", "sk-buyer-key-123456", installer.DEFAULT_MODEL, logs.append)
        self.assertTrue(ok)
        self.assertEqual(installer.inspect_agent_config_drift("claude_code")["level"], installer.DRIFT_OK)

    def test_no_sensitive_key_in_report(self) -> None:
        self._write_claude(installer.CLAUDE_CODE_BASE_URL, token="sk-super-secret-abcdef")
        report = installer.inspect_agent_config_drift("claude_code")
        self.assertNotIn("sk-super-secret-abcdef", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()

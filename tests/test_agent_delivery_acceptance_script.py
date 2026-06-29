import os
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agent_delivery_acceptance  # noqa: E402


class AgentDeliveryAcceptanceScriptTests(unittest.TestCase):
    def run_script(self, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "agent_delivery_acceptance.py"), *args],
            cwd=ROOT,
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    def test_cli_scope_selected_agents_do_not_block_on_client_detection(self) -> None:
        result = self.run_script("--delivery-scope", "cli", "--agents", "codex,claude_code,openclaw,hermes")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["delivery_scope"], "cli")
        self.assertEqual(report["delivery_status"], "blocked")
        self.assertEqual(report["selected_agent_ids"], ["codex", "claude_code", "openclaw", "hermes"])
        self.assertNotIn("客户端未确认", "\n".join(report["blocking_gaps"]))
        self.assertIn("最小中文对话未执行", "\n".join(report["blocking_gaps"]))
        for item in report["agents"]:
            self.assertEqual(item["delivery_status"], "blocked")
            self.assertIn("cli", item["mode_statuses"])
            self.assertNotIn("client", item["mode_statuses"])
            self.assertIn(item["mode_statuses"]["dialogue"], {"not_run", "not_supported"})

    def test_selected_gemini_agy_stays_blocking_even_for_cli_scope(self) -> None:
        result = self.run_script("--delivery-scope", "cli", "--agents", "gemini_agy")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["delivery_status"], "blocked")
        self.assertEqual(report["delivery_scope"], "cli")
        self.assertEqual(report["selected_agent_ids"], ["gemini_agy"])
        self.assertEqual(report["agents"][0]["delivery_status"], "blocked")
        self.assertEqual(report["agents"][0]["mode_statuses"]["cli"], "not_supported")
        self.assertEqual(report["agents"][0]["mode_statuses"]["dialogue"], "not_supported")
        self.assertIn("Gemini / agy 配置待开发", "\n".join(report["blocking_gaps"]))

    def test_client_scope_selected_agent_blocks_on_unconfirmed_client(self) -> None:
        result = self.run_script("--delivery-scope", "client", "--agents", "claude_code")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["delivery_status"], "blocked")
        self.assertEqual(report["delivery_scope"], "client")
        self.assertEqual(report["selected_agent_ids"], ["claude_code"])
        self.assertEqual(report["agents"][0]["delivery_status"], "blocked")
        self.assertNotIn("cli", report["agents"][0]["mode_statuses"])
        self.assertIn(report["agents"][0]["mode_statuses"]["client"], {"ready", "not_confirmed"})
        self.assertEqual(report["agents"][0]["mode_statuses"]["dialogue"], "not_run")
        self.assertIn("ClaudeCode 客户端未确认", "\n".join(report["blocking_gaps"]))

    def test_both_scope_reports_cli_and_client_as_separate_delivery_modes(self) -> None:
        result = self.run_script("--delivery-scope", "both", "--agents", "codex")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["delivery_status"], "blocked")
        self.assertEqual(report["agents"][0]["selected_modes"], ["cli", "client"])
        self.assertIn("cli", report["agents"][0]["mode_statuses"])
        self.assertIn("client", report["agents"][0]["mode_statuses"])
        self.assertEqual(report["agents"][0]["mode_statuses"]["dialogue"], "not_run")

    def test_isolated_acceptance_env_writes_temp_configs_without_user_paths(self) -> None:
        calls = []

        def fake_install(name):
            def _inner(api_key, model, log):
                calls.append((name, api_key, model))
                log(f"{name} ok")
                return True

            return _inner

        old_env = {
            key: os.environ.get(key)
            for key in ("CLAUDE_CODE_SETTINGS_PATH", "OPENCLAW_CONFIG_PATH", "HERMES_HOME")
        }
        try:
            with patch.object(agent_delivery_acceptance.installer, "install_claude_code_config", side_effect=fake_install("claude")), \
                 patch.object(agent_delivery_acceptance.installer, "install_openclaw_config", side_effect=fake_install("openclaw")), \
                 patch.object(agent_delivery_acceptance.installer, "install_hermes_config", side_effect=fake_install("hermes")):
                temp_env = agent_delivery_acceptance.configure_isolated_acceptance_env("sk-test-secret-123456", "gpt-5.4")
                self.assertIsNotNone(temp_env)
                assert temp_env is not None
                temp_root = Path(temp_env.name)

                self.assertEqual(calls, [
                    ("claude", "sk-test-secret-123456", "gpt-5.4"),
                    ("openclaw", "sk-test-secret-123456", "gpt-5.4"),
                    ("hermes", "sk-test-secret-123456", "gpt-5.4"),
                ])
                self.assertTrue(str(os.environ["CLAUDE_CODE_SETTINGS_PATH"]).startswith(str(temp_root)))
                self.assertTrue(str(os.environ["OPENCLAW_CONFIG_PATH"]).startswith(str(temp_root)))
                self.assertTrue(str(os.environ["HERMES_HOME"]).startswith(str(temp_root)))
                temp_env.cleanup()
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_dialogue_probe_wrapper_passes_timeout_and_sanitizes_nothing_itself(self) -> None:
        agent = next(agent for agent in agent_delivery_acceptance.installer.AGENTS if agent.id == "openclaw")
        captured = {}

        def fake_run(command, timeout=900):
            captured["command"] = command
            captured["timeout"] = timeout
            return False, "failed"

        with patch.object(agent_delivery_acceptance.installer, "run_command", side_effect=fake_run):
            ok, output = agent_delivery_acceptance.run_agent_dialogue_probe_with_timeout(agent, "cli", "gpt-5.4", 7)

        self.assertFalse(ok)
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(captured["command"][0], "openclaw")
        self.assertEqual(output, "failed")

    def test_gemini_dialogue_probe_reports_not_supported(self) -> None:
        agent = next(agent for agent in agent_delivery_acceptance.installer.AGENTS if agent.id == "gemini_agy")
        ok, output = agent_delivery_acceptance.run_agent_dialogue_probe_with_timeout(agent, "cli", "gpt-5.4", 7)

        self.assertFalse(ok)
        self.assertIn("配置待开发", output)

    def test_codex_gateway_probe_requires_acceptance_key(self) -> None:
        ok, output = agent_delivery_acceptance.run_codex_gateway_probe("", "gpt-5.4")

        self.assertFalse(ok)
        self.assertIn("PANGHU_AGENT_ACCEPTANCE_API_KEY", output)

    def test_codex_gateway_probe_sanitizes_api_key_from_output(self) -> None:
        secret = "sk-test-secret-123456"

        def fake_probe(base_url, api_key, model):
            self.assertEqual(base_url, agent_delivery_acceptance.installer.DEFAULT_BASE_URL)
            self.assertEqual(api_key, secret)
            self.assertEqual(model, "gpt-5.4")
            return False, f"upstream echoed {secret}"

        with patch.object(agent_delivery_acceptance.installer, "run_real_task_probe", side_effect=fake_probe):
            ok, output = agent_delivery_acceptance.run_codex_gateway_probe(secret, "gpt-5.4")

        self.assertFalse(ok)
        self.assertNotIn(secret, output)
        self.assertIn("***", output)


if __name__ == "__main__":
    unittest.main()

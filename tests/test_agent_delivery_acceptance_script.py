import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agent_delivery_acceptance  # noqa: E402


class AgentDeliveryAcceptanceScriptTests(unittest.TestCase):
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

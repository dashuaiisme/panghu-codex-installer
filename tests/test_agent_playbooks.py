import sys
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import panghu_codex_installer as installer  # noqa: E402


class AgentPlaybookTests(unittest.TestCase):
    def test_five_agent_catalog_includes_gemini_agy_install_entry(self) -> None:
        self.assertEqual(
            {agent.id for agent in installer.AGENTS},
            {"codex", "claude_code", "hermes", "openclaw", "gemini_agy"},
        )

    def test_every_agent_has_cli_and_client_modes_marked_configurable(self) -> None:
        for agent in installer.AGENTS:
            modes = {mode.id: mode for mode in agent.modes}
            self.assertIn("cli", modes, agent.id)
            self.assertIn("client", modes, agent.id)
            if agent.id == "gemini_agy":
                self.assertFalse(modes["cli"].supports_config, agent.id)
                self.assertFalse(modes["client"].supports_config, agent.id)
            else:
                self.assertTrue(modes["cli"].supports_config, agent.id)
                self.assertTrue(modes["client"].supports_config, agent.id)

    def test_non_codex_agents_have_complete_direct_conversation_playbooks(self) -> None:
        for agent_id in ("claude_code", "openclaw", "hermes"):
            playbook = installer.agent_delivery_playbook(agent_id)
            self.assertEqual(playbook.agent_id, agent_id)
            self.assertTrue(playbook.cli_supported)
            self.assertTrue(playbook.client_supported)
            self.assertTrue(playbook.skip_third_party_channels)
            self.assertIn("对话", playbook.customer_goal)
            expected_base = "https://aitokenapi.cc" if agent_id == "claude_code" else "https://aitokenapi.cc/v1"
            self.assertIn(expected_base, "\n".join(playbook.config_commands))
            self.assertTrue(any("API" in command or "KEY" in command for command in playbook.config_commands))
            self.assertTrue(playbook.minimal_dialogue_check)

    def test_customer_copy_no_longer_says_cc_openclaw_hermes_are_install_only(self) -> None:
        setup_guide = installer.build_agent_setup_guide_content(
            [(agent, "cli") for agent in installer.AGENTS],
            "sk-test-secret-123456",
        )
        choice_help = installer.agent_choice_help_text()
        combined = setup_guide + "\n" + choice_help
        self.assertNotIn("只安装，不写 Key", combined)
        self.assertNotIn("当前只生成中文说明", combined)
        self.assertIn("第三方通道默认跳过", combined)
        self.assertIn("直接对话", combined)

    def test_config_plan_for_each_agent_contains_write_and_dialogue_steps(self) -> None:
        for agent in installer.AGENTS:
            for mode in ("cli", "client"):
                plan = installer.build_agent_config_plan(
                    agent_id=agent.id,
                    mode_id=mode,
                    api_key="sk-test-secret-123456",
                    model="gpt-5.4",
                )
                text = "\n".join(plan)
                self.assertIn(agent.id, text)
                if agent.id == "gemini_agy":
                    self.assertIn("配置待开发", text)
                    self.assertIn("Google 账号自行登录", text)
                    self.assertNotIn("sk-test-secret-123456", text)
                else:
                    self.assertIn("https://aitokenapi.cc/v1", text)
                    self.assertIn("gpt-5.4", text)
                    self.assertIn("第三方通道默认跳过", text)
                    self.assertIn("最小对话验证", text)
                self.assertNotIn("QQ", text)
                self.assertNotIn("微信", text)
                self.assertNotIn("Telegram", text)

    def test_gemini_agy_is_install_only_and_not_complete_delivery(self) -> None:
        gemini = next(agent for agent in installer.AGENTS if agent.id == "gemini_agy")

        self.assertEqual(gemini.verify_command, ("agy", "--version"))
        self.assertFalse(installer.apply_agent_config(gemini, "cli", "sk-test-secret-123456", "gpt-5.4", lambda _msg: None))
        self.assertIn("配置待开发", installer.agent_dialogue_probe_command_text(gemini, "gpt-5.4"))
        ok, message = installer.run_agent_dialogue_probe(gemini, "cli", "gpt-5.4")
        self.assertFalse(ok)
        self.assertIn("配置待开发", message)

    def test_claude_code_config_writes_official_settings_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            logs = []
            with patch.object(installer.Path, "home", return_value=home):
                self.assertTrue(installer.install_claude_code_config("sk-test-secret-123456", "gpt-5.4", logs.append))

            settings_path = home / ".claude" / "settings.json"
            text = settings_path.read_text(encoding="utf-8")
            self.assertIn('"ANTHROPIC_BASE_URL": "https://aitokenapi.cc"', text)
            self.assertIn('"ANTHROPIC_AUTH_TOKEN": "sk-test-secret-123456"', text)
            self.assertIn('"ANTHROPIC_API_KEY": "sk-test-secret-123456"', text)
            self.assertIn('"ANTHROPIC_MODEL": "gpt-5.4"', text)
            self.assertIn('"ANTHROPIC_CUSTOM_MODEL_OPTION": "gpt-5.4"', text)
            self.assertIn("已写入 Claude Code/CC 设置", "\n".join(logs))

    def test_claude_code_config_can_use_isolated_settings_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            settings_path = Path(temp) / "settings.json"
            logs = []
            with patch.dict(installer.os.environ, {"CLAUDE_CODE_SETTINGS_PATH": str(settings_path)}):
                self.assertTrue(installer.install_claude_code_config("sk-test-secret-123456", "gpt-5.4", logs.append))
                self.assertEqual(installer.claude_code_settings_path(), settings_path)
                self.assertEqual(
                    installer.agent_dialogue_probe_command("claude_code", "gpt-5.4"),
                    [
                        "claude",
                        "--settings",
                        str(settings_path),
                        "--bare",
                        "--model",
                        "gpt-5.4",
                        "-p",
                        installer.AGENT_DIALOGUE_PROBE_PROMPT,
                    ],
                )

    def test_openclaw_config_writes_direct_conversation_provider_and_skips_channels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "openclaw.json"
            logs = []
            with patch.object(installer, "openclaw_config_path", return_value=config_path):
                self.assertTrue(installer.install_openclaw_config("sk-test-secret-123456", "gpt-5.4", logs.append))

            text = config_path.read_text(encoding="utf-8")
            self.assertIn('"baseUrl": "https://aitokenapi.cc/v1"', text)
            self.assertIn('"api": "openai-completions"', text)
            self.assertIn('"apiKey": "sk-test-secret-123456"', text)
            self.assertIn('"primary": "panghuai/gpt-5.4"', text)
            self.assertIn('"models": {', text)
            self.assertIn('"panghuai/gpt-5.4": {}', text)
            self.assertNotIn("third_party_channels", text)
            self.assertNotIn("QQ", text)
            self.assertNotIn("微信", text)
            self.assertNotIn("Telegram", text)

    def test_hermes_config_writes_yaml_and_env_for_panghuai_gateway(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            logs = []
            with patch.object(installer, "hermes_config_path", return_value=root / "config.yaml"), patch.object(
                installer, "hermes_env_path", return_value=root / ".env"
            ), patch.object(installer.shutil, "which", return_value=None):
                self.assertTrue(installer.install_hermes_config("sk-test-secret-123456", "gpt-5.4", logs.append))

            config_text = (root / "config.yaml").read_text(encoding="utf-8")
            env_text = (root / ".env").read_text(encoding="utf-8")
            self.assertIn("custom_providers:", config_text)
            self.assertIn("name: panghuai", config_text)
            self.assertIn("base_url: https://aitokenapi.cc/v1", config_text)
            self.assertIn("key_env: PANGHUAI_API_KEY", config_text)
            self.assertIn("provider: custom:panghuai", config_text)
            self.assertIn('default: "gpt-5.4"', config_text)
            self.assertIn("api_mode: chat_completions", config_text)
            self.assertNotIn("third_party_default", config_text)
            self.assertEqual(env_text, "PANGHUAI_API_KEY=sk-test-secret-123456\n")

    def test_non_codex_dialogue_probe_commands_are_real_cli_checks(self) -> None:
        self.assertEqual(
            installer.agent_dialogue_probe_command("claude_code", "gpt-5.4"),
            ["claude", "--model", "gpt-5.4", "-p", installer.AGENT_DIALOGUE_PROBE_PROMPT],
        )
        self.assertEqual(
            installer.agent_dialogue_probe_command("openclaw", "gpt-5.4"),
            [
                "openclaw",
                "infer",
                "model",
                "run",
                "--model",
                "panghuai/gpt-5.4",
                "--prompt",
                installer.AGENT_DIALOGUE_PROBE_PROMPT,
                "--json",
            ],
        )
        self.assertEqual(
            installer.agent_dialogue_probe_command("hermes", "gpt-5.4"),
            [
                "hermes",
                "--provider",
                "custom:panghuai",
                "--model",
                "gpt-5.4",
                "-z",
                installer.AGENT_DIALOGUE_PROBE_PROMPT,
            ],
        )

    def test_dialogue_probe_command_text_is_customer_copy_safe(self) -> None:
        openclaw = next(agent for agent in installer.AGENTS if agent.id == "openclaw")
        codex = next(agent for agent in installer.AGENTS if agent.id == "codex")

        self.assertIn("openclaw infer model run", installer.agent_dialogue_probe_command_text(openclaw, "gpt-5.4"))
        self.assertIn("--prompt", installer.agent_dialogue_probe_command_text(openclaw, "gpt-5.4"))
        self.assertIn("胖虎AI /v1/chat/completions", installer.agent_dialogue_probe_command_text(codex, "gpt-5.4"))

    def test_hermes_error_summary_reads_request_dump_without_leaking_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sessions = root / "sessions"
            sessions.mkdir()
            (sessions / "request_dump_selftest.json").write_text(
                json.dumps(
                    {
                        "request": {
                            "url": "https://aitokenapi.cc/v1/chat/completions",
                            "headers": {"Authorization": "Bearer sk-test-secret-123456"},
                        },
                        "error": {
                            "status_code": 401,
                            "body": {"message": "Invalid token for sk-test-secret-123456"},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = installer.recent_hermes_error_summary(root)

            self.assertIn("https://aitokenapi.cc/v1/chat/completions", summary)
            self.assertIn("状态码：401", summary)
            self.assertIn("无效令牌", summary)
            self.assertNotIn("sk-test-secret-123456", summary)

    def test_customer_acceptance_matrix_reports_done_and_not_done_per_agent(self) -> None:
        codex_progress = installer.DeploymentProgress()
        codex_progress.mark(installer.DeploymentNode.INSTALL, installer.NodeStatus.PASS)
        codex_progress.mark(installer.DeploymentNode.CONFIG_WRITE, installer.NodeStatus.PASS)
        codex_progress.mark(installer.DeploymentNode.LAUNCH_VERIFY, installer.NodeStatus.PASS)
        codex_progress.mark(installer.DeploymentNode.REAL_TASK_VERIFY, installer.NodeStatus.PASS)
        hermes_progress = installer.DeploymentProgress()
        hermes_progress.mark(installer.DeploymentNode.INSTALL, installer.NodeStatus.PASS)
        hermes_progress.mark(installer.DeploymentNode.CONFIG_WRITE, installer.NodeStatus.PASS)
        hermes_progress.mark(installer.DeploymentNode.LAUNCH_VERIFY, installer.NodeStatus.NEEDS_MANUAL)
        hermes_progress.mark(installer.DeploymentNode.REAL_TASK_VERIFY, installer.NodeStatus.FAILED)

        matrix = installer.build_customer_agent_acceptance_matrix(
            selected=[
                (next(agent for agent in installer.AGENTS if agent.id == "codex"), "cli"),
                (next(agent for agent in installer.AGENTS if agent.id == "hermes"), "client"),
            ],
            agent_progress={
                ("codex", "direct_api"): codex_progress,
                ("hermes", "client"): hermes_progress,
            },
            real_task_results={
                ("codex", "direct_api"): installer.RealTaskVerificationResult(
                    diagnostic_code="PH-CFG-MATRIX",
                    agent_id="codex",
                    mode_key="direct_api",
                    passed=True,
                    status=installer.NodeStatus.PASS,
                    customer_message="真实任务验证已通过。",
                    response_excerpt="胖虎AI配置验证成功",
                )
            },
            diagnostic_code="PH-CFG-MATRIX",
        )

        self.assertIn("客户可见功能验收矩阵", matrix)
        self.assertIn("Codex(CLI)：完整交付", matrix)
        self.assertIn("Hermes(客户端)：未完整交付", matrix)
        self.assertIn("最小对话：失败", matrix)
        self.assertIn("复验命令：hermes --provider custom:panghuai --model gpt-5.4 -z", matrix)
        self.assertIn("诊断码：PH-CFG-MATRIX", matrix)


if __name__ == "__main__":
    unittest.main()

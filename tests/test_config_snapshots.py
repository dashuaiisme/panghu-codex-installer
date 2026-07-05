"""统一配置快照层测试：original 永久快照、10 份轮转、回滚、回滚的回滚、一键恢复。"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import panghu_ai_client as installer  # noqa: E402


class ConfigSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="panghu-snap-test-")
        root = Path(self._tmp.name)
        self._old_env = {
            key: os.environ.get(key)
            for key in ("PANGHU_SNAPSHOT_ROOT", "HERMES_HOME", "CLAUDE_CODE_SETTINGS_PATH")
        }
        os.environ["PANGHU_SNAPSHOT_ROOT"] = str(root / "snapshots")
        os.environ["HERMES_HOME"] = str(root / "hermes")
        os.environ["CLAUDE_CODE_SETTINGS_PATH"] = str(root / "claude" / "settings.json")
        self.hermes_config = Path(os.environ["HERMES_HOME"]) / "config.yaml"
        self.hermes_env = Path(os.environ["HERMES_HOME"]) / ".env"

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def _write_hermes(self, config_text: str, env_text: str | None = None) -> None:
        self.hermes_config.parent.mkdir(parents=True, exist_ok=True)
        self.hermes_config.write_text(config_text, encoding="utf-8")
        if env_text is None:
            if self.hermes_env.exists():
                self.hermes_env.unlink()
        else:
            self.hermes_env.write_text(env_text, encoding="utf-8")

    def test_original_snapshot_created_once_and_never_pruned(self) -> None:
        self._write_hermes("provider: user-own\n")
        installer.ensure_original_config_snapshot("hermes")
        self._write_hermes("provider: changed\n")
        installer.ensure_original_config_snapshot("hermes")  # 第二次不覆盖

        for index in range(installer.SNAPSHOT_KEEP_COUNT + 5):
            installer.create_config_snapshot("hermes", f"round-{index}", name=f"2026-test-{index:04d}")

        snapshots = installer.list_config_snapshots("hermes")
        names = [item["name"] for item in snapshots]
        self.assertIn(installer.ORIGINAL_SNAPSHOT_NAME, names)
        rotating = [name for name in names if name != installer.ORIGINAL_SNAPSHOT_NAME]
        self.assertEqual(len(rotating), installer.SNAPSHOT_KEEP_COUNT)

        original = next(item for item in snapshots if item["is_original"])
        self.assertEqual(original["reason"], "接管前原始配置")
        # original 内容仍是首次接管前的
        saved = Path(os.environ["PANGHU_SNAPSHOT_ROOT"]) / "hermes" / "original" / "config.yaml"
        self.assertEqual(saved.read_text(encoding="utf-8"), "provider: user-own\n")

    def test_restore_roundtrip_and_absent_file_removal(self) -> None:
        logs: list[str] = []
        self._write_hermes("v1\n", env_text=None)  # .env 不存在
        snap = installer.create_config_snapshot("hermes", "v1-state", name="2026-snap-v1")
        self.assertTrue((snap / "meta.json").exists())

        self._write_hermes("v2\n", env_text="KEY=2\n")  # 改配置并新增 .env
        installer.restore_config_snapshot("hermes", "2026-snap-v1", logs.append)

        self.assertEqual(self.hermes_config.read_text(encoding="utf-8"), "v1\n")
        self.assertFalse(self.hermes_env.exists())  # 快照时不存在的文件被移除

        # 回滚的回滚：restore 前自动生成的 pre-restore 快照应包含 v2 状态
        snapshots = installer.list_config_snapshots("hermes")
        pre_restore = [item for item in snapshots if "回滚到" in item["reason"]]
        self.assertTrue(pre_restore)
        installer.restore_config_snapshot("hermes", pre_restore[0]["name"], logs.append)
        self.assertEqual(self.hermes_config.read_text(encoding="utf-8"), "v2\n")
        self.assertEqual(self.hermes_env.read_text(encoding="utf-8"), "KEY=2\n")

    def test_restore_original_config_one_click(self) -> None:
        logs: list[str] = []
        self._write_hermes("factory\n")
        installer.ensure_original_config_snapshot("hermes")
        self._write_hermes("panghu-configured\n", env_text="PANGHUAI_API_KEY=sk-x\n")
        installer.restore_original_config("hermes", logs.append)
        self.assertEqual(self.hermes_config.read_text(encoding="utf-8"), "factory\n")
        self.assertFalse(self.hermes_env.exists())
        self.assertTrue(any("回滚到快照 original" in line or "original" in line for line in logs))

    def test_unknown_agent_and_missing_snapshot_raise(self) -> None:
        with self.assertRaises(ValueError):
            installer.agent_config_target_paths("unknown_agent")
        with self.assertRaises(ValueError):
            installer.restore_config_snapshot("hermes", "no-such-snapshot", lambda _msg: None)

    def test_snapshot_meta_contains_reason_and_paths(self) -> None:
        self._write_hermes("meta-check\n", env_text="A=1\n")
        snap = installer.create_config_snapshot("hermes", "meta-reason", name="2026-meta")
        meta = json.loads((snap / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["agent_id"], "hermes")
        self.assertEqual(meta["reason"], "meta-reason")
        self.assertEqual(set(meta["files"]), {"config.yaml", ".env"})
        self.assertEqual(meta["absent"], [])


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import commercial_release_acceptance  # noqa: E402


def run_acceptance_script(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "commercial_release_acceptance.py"),
            *args,
        ],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


class CommercialReleaseAcceptanceTests(unittest.TestCase):
    def test_release_artifact_names_use_single_unicode_safe_app_name(self) -> None:
        app_name = "胖虎AI客户端"

        self.assertEqual(commercial_release_acceptance.customer_app_name(), app_name)
        self.assertEqual(commercial_release_acceptance.WINDOWS_RELEASE_ARTIFACT, f"{app_name}-Windows.zip")
        self.assertEqual(
            commercial_release_acceptance.RELEASE_ARTIFACTS,
            [
                f"{app_name}-Windows.zip",
                f"{app_name}-Mac-AppleSilicon.zip",
                f"{app_name}-Mac-Intel.zip",
            ],
        )
        self.assertEqual(
            commercial_release_acceptance.default_windows_release_zip(),
            ROOT / "release" / f"{app_name}-Windows.zip",
        )

    def test_release_acceptance_script_does_not_scatter_raw_artifact_name_literals(self) -> None:
        script_text = (ROOT / "scripts" / "commercial_release_acceptance.py").read_text(encoding="utf-8")

        self.assertNotIn("胖虎AI客户端-Windows.zip", script_text)
        self.assertNotIn("胖虎AI客户端-Mac-AppleSilicon.zip", script_text)
        self.assertNotIn("胖虎AI客户端-Mac-Intel.zip", script_text)

    def test_release_acceptance_script_reports_local_artifacts_and_offline_flow(self) -> None:
        result = run_acceptance_script("--json")
        report = json.loads(result.stdout)

        self.assertTrue(report["offline_only"])
        self.assertIn(report["status"], {"PASS", "WARN"})
        self.assertEqual(report["commercial_flow"]["status"], "PASS")
        self.assertEqual(report["commercial_flow"]["entitlement"]["remaining_uses_after_failed_session"], 1)
        self.assertEqual(report["commercial_flow"]["entitlement"]["remaining_uses_after_completed_session"], 0)
        self.assertTrue(report["commercial_flow"]["device_policy"]["new_device_blocked"])
        self.assertEqual(report["commercial_flow"]["device_policy"]["remaining_uses_after_device_block"], 1)

        artifacts = report["release_artifacts"]
        self.assertIn("胖虎AI客户端-Windows.zip", artifacts)
        self.assertIn("胖虎AI客户端-Mac-AppleSilicon.zip", artifacts)
        self.assertIn("胖虎AI客户端-Mac-Intel.zip", artifacts)
        for info in artifacts.values():
            self.assertIn(info["freshness"], {"fresh", "stale", "missing"})
            if info["exists"]:
                self.assertRegex(info["sha256"], r"^[A-Fa-f0-9]{64}$")
                self.assertGreater(info["size"], 0)
            else:
                self.assertEqual(info["sha256"], "")
                self.assertEqual(info["size"], 0)

        if all(not info["exists"] for info in artifacts.values()):
            self.assertTrue(any("缺少本地客户包" in warning for warning in report["warnings"]))

        generated_key = report["generated_public_key_module"]
        self.assertFalse(generated_key["has_bom"])
        self.assertTrue(generated_key["syntax_ok"])
        self.assertTrue(generated_key["gitignored"])

        self.assertFalse(report["hard_boundaries"]["external_mutation_executed"])
        self.assertFalse(report["hard_boundaries"]["private_key_material_found"])
        self.assertFalse(report["hard_boundaries"]["packaged_app_commercial_literals_found"])
        self.assertTrue(report["untracked_superpowers_dir_present"])
        self.assertIn("review_notes", report)

    def test_static_publish_command_mentions_are_review_notes_not_release_warnings(self) -> None:
        result = run_acceptance_script("--json", "--deep-scan")
        report = json.loads(result.stdout)

        self.assertEqual(report["hard_boundaries"]["scan_mode"], "deep")
        self.assertTrue(report["hard_boundaries"]["static_pattern_hits"])
        self.assertTrue(report["review_notes"])
        self.assertNotIn("发现文档或脚本中存在生产/发布相关命令字样，请人工确认本轮未执行。", report["warnings"])

    def test_release_acceptance_defaults_to_light_scan_to_avoid_heavy_docs_and_ci_walk(self) -> None:
        result = run_acceptance_script("--json", "--artifact-scope", "windows")
        report = json.loads(result.stdout)

        self.assertEqual(report["hard_boundaries"]["scan_mode"], "light")
        scanned_files = report["hard_boundaries"]["text_files_scanned"]
        self.assertIn("src/panghu_ai_client.py", scanned_files)
        self.assertIn("src/commercial_core.py", scanned_files)
        self.assertIn("src/commercial_api.py", scanned_files)
        self.assertNotIn("docs/TECHNICAL_MAINTENANCE_MANUAL.md", scanned_files)
        self.assertNotIn(".github/workflows/build-mac-release.yml", scanned_files)
        self.assertEqual(report["hard_boundaries"]["static_pattern_hits"], [])

    def test_packaged_app_source_does_not_embed_commercial_price_or_commission_examples(self) -> None:
        result = run_acceptance_script("--json")
        report = json.loads(result.stdout)

        self.assertFalse(report["hard_boundaries"]["packaged_app_commercial_literals_found"])
        self.assertEqual(report["hard_boundaries"]["packaged_app_commercial_literal_hits"], [])
        self.assertFalse(report["hard_boundaries"]["packaged_app_commercial_static_values_found"])
        self.assertEqual(report["hard_boundaries"]["packaged_app_commercial_static_value_hits"], [])

    def test_release_acceptance_scans_all_customer_app_commercial_source_files(self) -> None:
        result = run_acceptance_script("--json")
        report = json.loads(result.stdout)

        scanned = report["hard_boundaries"]["packaged_app_source_files_scanned"]
        self.assertIn("src/panghu_ai_client.py", scanned)
        self.assertIn("src/commercial_core.py", scanned)
        self.assertIn("src/commercial_api.py", scanned)

    def test_release_acceptance_blocks_non_codex_agents_from_full_paid_delivery(self) -> None:
        result = run_acceptance_script("--json")
        report = json.loads(result.stdout)

        self.assertIn("non_codex_full_config_delivery_found", report["hard_boundaries"])
        self.assertFalse(report["hard_boundaries"]["non_codex_full_config_delivery_found"])
        self.assertEqual(report["hard_boundaries"]["non_codex_full_config_delivery_hits"], [])

    def test_release_acceptance_blocks_communication_link_client_claiming_real_delivery(self) -> None:
        result = run_acceptance_script("--json")
        report = json.loads(result.stdout)

        self.assertIn("communication_link_real_delivery_claim_found", report["hard_boundaries"])
        self.assertFalse(report["hard_boundaries"]["communication_link_real_delivery_claim_found"])
        self.assertEqual(report["hard_boundaries"]["communication_link_real_delivery_claim_hits"], [])

    def test_generated_public_key_module_is_not_release_freshness_source(self) -> None:
        baseline_paths = {path.relative_to(ROOT).as_posix() for path in commercial_release_acceptance._source_baseline_paths()}

        self.assertNotIn("src/commercial_manifest_public_key.py", baseline_paths)

    def test_artifact_scope_limits_release_artifacts_for_ci_platform_jobs(self) -> None:
        result = run_acceptance_script("--json", "--artifact-scope", "windows")
        report = json.loads(result.stdout)

        self.assertEqual(list(report["release_artifacts"].keys()), ["胖虎AI客户端-Windows.zip"])

    def test_release_artifact_names_do_not_accept_legacy_aliases(self) -> None:
        aliases = commercial_release_acceptance.release_artifact_aliases("胖虎AI客户端-Windows.zip")

        self.assertEqual(["胖虎AI客户端-Windows.zip"], aliases)

    def test_packaged_zip_content_scan_reports_internal_project_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "客户包.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("胖虎AI客户端.exe", b"binary")
                archive.writestr("docs/TECHNICAL_MAINTENANCE_MANUAL.md", "internal manual")
                archive.writestr("scripts/commercial_manifest_signer.py", "signer")
                archive.writestr("tests/test_commercial_release_acceptance.py", "test")
                archive.writestr(".github/workflows/build-mac-release.yml", "ci")
                archive.writestr("src/commercial_core.py", "source")
                archive.writestr("src/commercial_backend_contract.py", "backend simulator")
                archive.writestr("certifi/core.py", "third party package")

            report = commercial_release_acceptance.inspect_packaged_zip_contents(zip_path)

        self.assertTrue(report["internal_files_found"])
        self.assertIn("docs/TECHNICAL_MAINTENANCE_MANUAL.md", report["internal_file_hits"])
        self.assertIn("scripts/commercial_manifest_signer.py", report["internal_file_hits"])
        self.assertIn("tests/test_commercial_release_acceptance.py", report["internal_file_hits"])
        self.assertIn(".github/workflows/build-mac-release.yml", report["internal_file_hits"])
        self.assertIn("src/commercial_core.py", report["internal_file_hits"])
        self.assertIn("src/commercial_backend_contract.py", report["internal_file_hits"])
        self.assertNotIn("certifi/core.py", report["internal_file_hits"])

    def test_packaged_zip_content_scan_reports_nested_internal_project_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "客户包.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("胖虎AI客户端/胖虎AI客户端.exe", b"binary")
                archive.writestr("胖虎AI客户端/docs/TECHNICAL_MAINTENANCE_MANUAL.md", "internal manual")
                archive.writestr("胖虎AI客户端/scripts/commercial_manifest_signer.py", "signer")
                archive.writestr("胖虎AI客户端/src/commercial_backend_contract.py", "backend simulator")
                archive.writestr("胖虎AI客户端/certifi/core.py", "third party package")

            report = commercial_release_acceptance.inspect_packaged_zip_contents(zip_path)

        self.assertTrue(report["internal_files_found"])
        self.assertIn("胖虎AI客户端/docs/TECHNICAL_MAINTENANCE_MANUAL.md", report["internal_file_hits"])
        self.assertIn("胖虎AI客户端/scripts/commercial_manifest_signer.py", report["internal_file_hits"])
        self.assertIn("胖虎AI客户端/src/commercial_backend_contract.py", report["internal_file_hits"])
        self.assertNotIn("胖虎AI客户端/certifi/core.py", report["internal_file_hits"])

    def test_release_acceptance_reports_packaged_zip_content_scan(self) -> None:
        result = run_acceptance_script("--json", "--artifact-scope", "windows")
        report = json.loads(result.stdout)

        self.assertIn("packaged_artifact_contents", report)
        self.assertIn("胖虎AI客户端-Windows.zip", report["packaged_artifact_contents"])
        self.assertFalse(
            report["packaged_artifact_contents"]["胖虎AI客户端-Windows.zip"]["internal_files_found"]
        )

    def test_release_acceptance_reports_temporary_files_left_in_release_dir(self) -> None:
        with TemporaryDirectory() as temp_dir:
            release_dir = Path(temp_dir) / "release"
            release_dir.mkdir()
            (release_dir / "zip-validation-repro.zip.tmp").write_bytes(b"tmp")
            (release_dir / "keep.txt").write_text("not a temp package", encoding="utf-8")

            with patch.object(commercial_release_acceptance, "ROOT", Path(temp_dir)):
                report = commercial_release_acceptance.build_release_temp_file_report()

        self.assertTrue(report["temp_files_found"])
        self.assertEqual(report["temp_file_hits"], ["release/zip-validation-repro.zip.tmp"])

    def test_packaged_self_test_runs_exe_extracted_from_customer_zip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "Windows.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("胖虎AI客户端/胖虎AI客户端.exe", b"fake")

            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="UI self-test OK\n",
                stderr="",
            )
            with patch.object(commercial_release_acceptance.subprocess, "run", return_value=completed) as run_mock:
                report = commercial_release_acceptance.run_packaged_self_test(zip_path)

        command = run_mock.call_args_list[0].args[0]
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(command[1], "--self-test")
        self.assertTrue(str(command[0]).endswith("胖虎AI客户端.exe"))
        self.assertNotIn(str(ROOT / "release"), str(command[0]))
        self.assertEqual(report["source_zip"], str(zip_path.relative_to(ROOT)) if zip_path.is_relative_to(ROOT) else str(zip_path))

    def test_local_packaged_self_test_requires_explicit_opt_in(self) -> None:
        original_environ = os.environ.copy()
        try:
            os.environ.pop("CI", None)
            os.environ.pop("GITHUB_ACTIONS", None)
            os.environ.pop("PANGHU_ALLOW_LOCAL_PACKAGED_SELF_TEST", None)

            with patch.object(
                commercial_release_acceptance,
                "run_packaged_self_test",
                return_value={"status": "PASS"},
            ) as self_test_mock:
                report = commercial_release_acceptance.build_report(
                    include_exe_self_test=True,
                    artifact_scope="windows",
                )

            self.assertEqual(report["packaged_self_test"]["status"], "SKIPPED")
            self.assertIn("PANGHU_ALLOW_LOCAL_PACKAGED_SELF_TEST=1", report["packaged_self_test"]["message"])
            self_test_mock.assert_not_called()
        finally:
            os.environ.clear()
            os.environ.update(original_environ)

    def test_packaged_self_test_cleans_temp_exe_process_after_run(self) -> None:
        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "Windows.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("胖虎AI客户端/胖虎AI客户端.exe", b"fake")

            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="UI self-test OK\n",
                stderr="",
            )
            with (
                patch.object(commercial_release_acceptance.sys, "platform", "win32"),
                patch.object(commercial_release_acceptance.subprocess, "run", return_value=completed) as run_mock,
            ):
                report = commercial_release_acceptance.run_packaged_self_test(zip_path)

        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(run_mock.call_count, 2)
        cleanup_command = run_mock.call_args_list[1].args[0]
        self.assertEqual(cleanup_command[:4], ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass"])
        self.assertIn("-Command", cleanup_command)
        self.assertTrue(any("panghu-release-selftest-" in str(part) for part in cleanup_command))

    def test_packaged_self_test_timeout_reports_failure_and_cleans_temp_process(self) -> None:
        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "Windows.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("胖虎AI客户端/胖虎AI客户端.exe", b"fake")

            cleanup_completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            timeout = subprocess.TimeoutExpired(
                cmd=["fake.exe", "--self-test"],
                timeout=commercial_release_acceptance.PACKAGED_SELF_TEST_TIMEOUT_SECONDS,
                output="partial output",
                stderr="still running",
            )
            with (
                patch.object(commercial_release_acceptance.sys, "platform", "win32"),
                patch.object(commercial_release_acceptance.subprocess, "run", side_effect=[timeout, cleanup_completed]) as run_mock,
            ):
                report = commercial_release_acceptance.run_packaged_self_test(zip_path)

        self.assertEqual(report["status"], "FAIL")
        self.assertIn("超时", report["message"])
        self.assertEqual(report["timeout_seconds"], commercial_release_acceptance.PACKAGED_SELF_TEST_TIMEOUT_SECONDS)
        self.assertEqual(report["stdout"], "partial output")
        self.assertEqual(report["stderr"], "still running")
        self.assertEqual(run_mock.call_count, 2)
        cleanup_command = run_mock.call_args_list[1].args[0]
        self.assertEqual(cleanup_command[:4], ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass"])
        self.assertTrue(any("panghu-release-selftest-" in str(part) for part in cleanup_command))

    def test_packaged_self_test_rejects_zip_path_traversal_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "bad.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("../outside.exe", b"bad")

            report = commercial_release_acceptance.run_packaged_self_test(zip_path)

        self.assertEqual(report["status"], "FAIL")
        self.assertIn("不安全路径", report["message"])

    def test_strict_mode_exits_nonzero_when_acceptance_has_warnings(self) -> None:
        warn_report = {
            "status": "WARN",
            "warnings": ["forced warning"],
            "release_artifacts": {},
            "review_notes": [],
        }

        with patch.object(commercial_release_acceptance, "build_report", return_value=warn_report):
            with patch.object(sys, "argv", ["commercial_release_acceptance.py", "--json", "--strict"]):
                with self.assertRaises(SystemExit) as raised:
                    commercial_release_acceptance.main()

        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()

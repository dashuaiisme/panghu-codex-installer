import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CommercialBuildScriptTests(unittest.TestCase):
    def test_windows_build_generates_commercial_manifest_public_key_module(self) -> None:
        text = (ROOT / "scripts" / "build-windows-exe.ps1").read_text(encoding="utf-8")

        self.assertIn("PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM", text)
        self.assertIn("PANGHU_REQUIRE_COMMERCIAL_MANIFEST_PUBLIC_KEY", text)
        self.assertIn("commercial_manifest_public_key.py", text)
        self.assertIn("PUBLIC_KEY_PEM", text)
        self.assertIn("WriteAllLines($publicKeyModule", text)
        self.assertIn("Failed to generate commercial manifest public key module", text)
        self.assertIn("Production commercial build requires PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM", text)

    def test_mac_build_generates_commercial_manifest_public_key_module(self) -> None:
        text = (ROOT / "scripts" / "build-mac-app.command").read_text(encoding="utf-8")

        self.assertIn("PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM", text)
        self.assertIn("PANGHU_REQUIRE_COMMERCIAL_MANIFEST_PUBLIC_KEY", text)
        self.assertIn("commercial_manifest_public_key.py", text)
        self.assertIn("PUBLIC_KEY_PEM", text)
        self.assertIn("write_text(", text)
        self.assertIn("Production commercial build requires PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM", text)

    def test_build_scripts_always_overwrite_generated_public_key_module(self) -> None:
        windows = (ROOT / "scripts" / "build-windows-exe.ps1").read_text(encoding="utf-8")
        mac = (ROOT / "scripts" / "build-mac-app.command").read_text(encoding="utf-8")

        self.assertNotIn("Add-Content", windows)
        self.assertNotIn(">>", windows)
        self.assertNotIn(">>", mac)
        self.assertIn("$publicKeyPem = [string]$env:PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM", windows)
        self.assertIn("ConvertTo-Json -Compress $publicKeyPem", windows)
        self.assertIn('os.environ.get("PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM", "")', mac)

    def test_ci_requires_commercial_public_key_for_customer_release_builds(self) -> None:
        text = (ROOT / ".github" / "workflows" / "build-mac-release.yml").read_text(encoding="utf-8")

        self.assertGreaterEqual(text.count("PANGHU_REQUIRE_COMMERCIAL_MANIFEST_PUBLIC_KEY: \"1\""), 2)

    def test_production_public_key_requirement_fails_before_dependency_install(self) -> None:
        windows = (ROOT / "scripts" / "build-windows-exe.ps1").read_text(encoding="utf-8")
        mac = (ROOT / "scripts" / "build-mac-app.command").read_text(encoding="utf-8")

        self.assertLess(
            windows.index("Production commercial build requires PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM"),
            windows.index("pip install"),
        )
        self.assertLess(
            mac.index("Production commercial build requires PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM"),
            mac.index("pip install"),
        )

    def test_windows_build_uses_unicode_safe_zip_creation(self) -> None:
        text = (ROOT / "scripts" / "build-windows-exe.ps1").read_text(encoding="utf-8")

        self.assertIn("System.IO.Compression.ZipFile", text)
        self.assertIn("CreateFromDirectory", text)
        self.assertNotIn("Compress-Archive", text)

    def test_windows_build_validates_zip_before_replacing_customer_package(self) -> None:
        text = (ROOT / "scripts" / "build-windows-exe.ps1").read_text(encoding="utf-8")

        self.assertIn("$tempZip", text)
        self.assertIn("OpenRead($tempZip)", text)
        self.assertIn("Entries", text)
        self.assertIn("Windows zip validation failed", text)
        self.assertIn("Move-Item -LiteralPath $tempZip -Destination $zip -Force", text)

    def test_build_scripts_package_webview_ui_shell(self) -> None:
        windows = (ROOT / "scripts" / "build-windows-exe.ps1").read_text(encoding="utf-8")
        mac = (ROOT / "scripts" / "build-mac-app.command").read_text(encoding="utf-8")

        self.assertTrue((ROOT / "src" / "ui" / "index.html").exists())
        self.assertIn("src\\ui", windows)
        self.assertIn(";ui", windows)
        self.assertIn("src/ui:ui", mac)
        self.assertIn('cp -R "$ROOT/src/ui"', mac)

    def test_generated_public_key_module_is_not_tracked(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("src/commercial_manifest_public_key.py", text)

    def test_github_workflow_injects_commercial_public_key_and_runs_acceptance(self) -> None:
        text = (ROOT / ".github" / "workflows" / "build-mac-release.yml").read_text(encoding="utf-8")

        self.assertIn("PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM: ${{ secrets.PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM }}", text)
        self.assertGreaterEqual(text.count("PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM"), 2)
        self.assertIn("commercial_release_acceptance.py --with-exe-self-test --deep-scan --json --artifact-scope windows --strict", text)
        self.assertIn("package_scope: mac-intel", text)
        self.assertIn("package_scope: mac-apple-silicon", text)
        self.assertIn("commercial_release_acceptance.py --with-exe-self-test --deep-scan --json --artifact-scope ${{ matrix.package_scope }} --strict", text)
        self.assertIn("Verify public release gate", text)
        self.assertIn("Public Release upload is blocked because commercial release acceptance", text)

    def test_github_workflow_uses_current_customer_package_names_only(self) -> None:
        text = (ROOT / ".github" / "workflows" / "build-mac-release.yml").read_text(encoding="utf-8")
        old_english_prefix = "".join(["AI", ".", "Agent"])
        old_chinese_tool_name = "".join(["胖虎AI", "多", "Agent", "一键", "部署", "工具"])
        old_spaced_tool_name = "".join(["多", " Agent", " 一键", "配置", "工具"])

        self.assertIn("胖虎AI客户端-Windows.zip", text)
        self.assertIn("胖虎AI客户端-Mac-${{ matrix.package_suffix }}.zip", text)
        self.assertNotIn(old_english_prefix, text)
        self.assertNotIn(old_chinese_tool_name, text)
        self.assertNotIn(old_spaced_tool_name, text)

    def test_mac_workflow_revalidates_final_zip_after_notarization_repack(self) -> None:
        text = (ROOT / ".github" / "workflows" / "build-mac-release.yml").read_text(encoding="utf-8")
        mac_job = text[text.index("build-mac:") :]

        final_acceptance = "Final commercial release acceptance"
        self.assertIn(final_acceptance, mac_job)
        self.assertGreater(mac_job.index(final_acceptance), mac_job.index("Notarize app"))
        self.assertLess(mac_job.index(final_acceptance), mac_job.index("Prepare release asset"))
        self.assertGreaterEqual(
            mac_job.count("python scripts/commercial_release_acceptance.py --with-exe-self-test --deep-scan --json --artifact-scope ${{ matrix.package_scope }} --strict"),
            2,
        )

    def test_mac_workflow_self_tests_final_zip_after_notarization_repack(self) -> None:
        text = (ROOT / ".github" / "workflows" / "build-mac-release.yml").read_text(encoding="utf-8")
        mac_job = text[text.index("build-mac:") :]

        final_zip_test = "Test final Mac zip"
        final_acceptance = "Final commercial release acceptance"
        self.assertIn(final_zip_test, mac_job)
        self.assertGreater(mac_job.index(final_zip_test), mac_job.index("Notarize app"))
        self.assertLess(mac_job.index(final_zip_test), mac_job.index(final_acceptance))
        self.assertLess(mac_job.index(final_zip_test), mac_job.index("Prepare release asset"))
        self.assertIn('ZIP_PATH="release/胖虎AI客户端-Mac-${{ matrix.package_suffix }}.zip"', mac_job)
        self.assertIn("/usr/bin/ditto -x -k \"$ZIP_PATH\" \"$FINAL_ZIP_TEST_DIR\"", mac_job)
        self.assertIn("\"$FINAL_ZIP_TEST_DIR/胖虎AI客户端.app/Contents/MacOS/胖虎AI客户端\" --self-test", mac_job)


if __name__ == "__main__":
    unittest.main()

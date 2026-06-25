import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from commercial_core import validate_commercial_manifest_trust  # noqa: E402


class ManifestSigningToolTests(unittest.TestCase):
    def test_tool_generates_keypair_and_signs_manifest_that_client_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            private_key = tmp_path / "manifest-ed25519-private.pem"
            public_key = tmp_path / "manifest-ed25519-public.pem"
            manifest_path = tmp_path / "manifest.json"
            signed_path = tmp_path / "manifest.signed.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "products": [],
                        "entitlements": [],
                        "commercial_enabled": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "commercial_manifest_signer.py"),
                    "generate-keypair",
                    "--private-key",
                    str(private_key),
                    "--public-key",
                    str(public_key),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "commercial_manifest_signer.py"),
                    "sign",
                    "--manifest",
                    str(manifest_path),
                    "--private-key",
                    str(private_key),
                    "--key-id",
                    "test-key-1",
                    "--output",
                    str(signed_path),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            signed_manifest = json.loads(signed_path.read_text(encoding="utf-8"))
            decision = validate_commercial_manifest_trust(
                signed_manifest,
                public_key_pem=public_key.read_text(encoding="utf-8"),
            )

            self.assertTrue(decision.trusted, decision.message)
            self.assertEqual(signed_manifest["manifest_signature_algorithm"], "ed25519")
            self.assertEqual(signed_manifest["manifest_key_id"], "test-key-1")

    def test_tool_signed_manifest_rejects_after_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            private_key = tmp_path / "private.pem"
            public_key = tmp_path / "public.pem"
            manifest_path = tmp_path / "manifest.json"
            signed_path = tmp_path / "manifest.signed.json"
            manifest_path.write_text('{"products":[],"commercial_enabled":true}', encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "commercial_manifest_signer.py"),
                    "generate-keypair",
                    "--private-key",
                    str(private_key),
                    "--public-key",
                    str(public_key),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "commercial_manifest_signer.py"),
                    "sign",
                    "--manifest",
                    str(manifest_path),
                    "--private-key",
                    str(private_key),
                    "--key-id",
                    "test-key-1",
                    "--output",
                    str(signed_path),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            signed_manifest = json.loads(signed_path.read_text(encoding="utf-8"))
            signed_manifest["products"].append({"product_id": "tampered"})

            decision = validate_commercial_manifest_trust(
                signed_manifest,
                public_key_pem=public_key.read_text(encoding="utf-8"),
            )

            self.assertFalse(decision.trusted)
            self.assertIn("验签失败", decision.message)


if __name__ == "__main__":
    unittest.main()

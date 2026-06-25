from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from commercial_core import canonical_commercial_manifest_payload  # noqa: E402


def generate_keypair(private_key_path: Path, public_key_path: Path, overwrite: bool) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if not overwrite:
        for path in (private_key_path, public_key_path):
            if path.exists():
                raise SystemExit(f"Refusing to overwrite existing key file: {path}")
    private_key = Ed25519PrivateKey.generate()
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def sign_manifest(manifest_path: Path, private_key_path: Path, key_id: str, output_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise SystemExit("Manifest root must be a JSON object.")
    manifest.pop("manifest_signature", None)
    manifest["manifest_signature_algorithm"] = "ed25519"
    manifest["manifest_key_id"] = key_id
    manifest["manifest_issued_at"] = datetime.now(timezone.utc).isoformat()

    private_key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    signature = private_key.sign(canonical_commercial_manifest_payload(manifest))
    manifest["manifest_signature"] = "ed25519:" + base64.b64encode(signature).decode("ascii")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sign Panghu commercial deployer manifests.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    keypair = subparsers.add_parser("generate-keypair", help="Generate an Ed25519 manifest signing keypair.")
    keypair.add_argument("--private-key", required=True, type=Path)
    keypair.add_argument("--public-key", required=True, type=Path)
    keypair.add_argument("--overwrite", action="store_true")

    sign = subparsers.add_parser("sign", help="Sign a commercial deployer manifest.")
    sign.add_argument("--manifest", required=True, type=Path)
    sign.add_argument("--private-key", required=True, type=Path)
    sign.add_argument("--key-id", required=True)
    sign.add_argument("--output", required=True, type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "generate-keypair":
        generate_keypair(args.private_key, args.public_key, args.overwrite)
        return
    if args.command == "sign":
        sign_manifest(args.manifest, args.private_key, args.key_id, args.output)
        return
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()

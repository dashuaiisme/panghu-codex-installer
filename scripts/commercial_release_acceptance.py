from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(SRC))

from commercial_flow_acceptance import run_acceptance  # noqa: E402


def customer_app_name() -> str:
    try:
        from panghu_codex_installer import APP_NAME
    except Exception:
        name_parts = (
            chr(0x80D6),
            chr(0x864E),
            "AI",
            chr(0x591A),
            "Agent",
            chr(0x4E00),
            chr(0x952E),
            chr(0x90E8),
            chr(0x7F72),
            chr(0x5DE5),
            chr(0x5177),
        )
        return "".join(name_parts)
    return APP_NAME


WINDOWS_RELEASE_ARTIFACT = f"{customer_app_name()}-Windows.zip"
MAC_APPLE_SILICON_RELEASE_ARTIFACT = f"{customer_app_name()}-Mac-AppleSilicon.zip"
MAC_INTEL_RELEASE_ARTIFACT = f"{customer_app_name()}-Mac-Intel.zip"

RELEASE_ARTIFACTS = [
    WINDOWS_RELEASE_ARTIFACT,
    MAC_APPLE_SILICON_RELEASE_ARTIFACT,
    MAC_INTEL_RELEASE_ARTIFACT,
]

ARTIFACT_SCOPES = {
    "all": RELEASE_ARTIFACTS,
    "windows": [WINDOWS_RELEASE_ARTIFACT],
    "mac-apple-silicon": [MAC_APPLE_SILICON_RELEASE_ARTIFACT],
    "mac-intel": [MAC_INTEL_RELEASE_ARTIFACT],
}

BOUNDARY_PATTERNS = [
    "gh" + " release",
    "gh" + " workflow",
    "Invoke" + "-WebRequest",
    "ssh" + " ",
    "scp" + " ",
]

PRIVATE_KEY_PATTERNS = [
    "-----BEGIN " + "PRIVATE KEY-----",
    "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
]

PACKAGED_APP_COMMERCIAL_LITERAL_PATTERNS = [
    '"price_cents":',
    '"commission_ratio":',
]

PACKAGED_APP_COMMERCIAL_STATIC_VALUE_PATTERNS = [
    re.compile(r"\bremaining_uses\s*=\s*-?\d+\b"),
    re.compile(r"\bdevice_limit\s*=\s*\d+\b"),
    re.compile(r"\bis_listed\s*=\s*(True|False)\b"),
    re.compile(r"\bvalid_until\s*=\s*['\"][^'\"]+['\"]"),
]

PACKAGED_APP_COMMERCIAL_SOURCE_FILES = {
    "src/panghu_codex_installer.py",
    "src/commercial_core.py",
    "src/commercial_api.py",
}

LIGHT_HARD_BOUNDARY_SOURCE_FILES = {
    "requirements-build.txt",
    "scripts/build-windows-exe.ps1",
    "scripts/build-mac-app.command",
    "scripts/commercial_flow_acceptance.py",
    "scripts/commercial_manifest_signer.py",
    "scripts/commercial_release_acceptance.py",
    *PACKAGED_APP_COMMERCIAL_SOURCE_FILES,
}

NON_CODEX_AGENT_IDS = ("claude_code", "openclaw", "hermes")
NON_CODEX_FULL_CONFIG_PATTERN = re.compile(
    r"(?P<agent>claude_code|openclaw|hermes)(?:(?!\n\s*\n).){0,500}"
    r"(?P<scope>full_config)(?:(?!\n\s*\n).){0,500}"
    r"(?P<allowed>full_config_allowed\s*[:=]\s*True|\"full_config_allowed\"\s*:\s*true)",
    re.IGNORECASE | re.DOTALL,
)

PACKAGED_SELF_TEST_TIMEOUT_SECONDS = 30
LOCAL_PACKAGED_SELF_TEST_OPT_IN_ENV = "PANGHU_ALLOW_LOCAL_PACKAGED_SELF_TEST"

PACKAGED_INTERNAL_EXACT_PATHS = {
    ".github/workflows/build-mac-release.yml",
    "docs/COMMERCIAL_BACKEND_API_CONTRACT.md",
    "docs/TECHNICAL_MAINTENANCE_MANUAL.md",
    "scripts/commercial_flow_acceptance.py",
    "scripts/commercial_manifest_signer.py",
    "scripts/commercial_release_acceptance.py",
    "src/commercial_api.py",
    "src/commercial_backend_contract.py",
    "src/commercial_core.py",
}

PACKAGED_INTERNAL_PREFIXES = (
    ".codex/",
    ".github/",
    "docs/superpowers/",
    "tests/",
)

PACKAGED_SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    "commercial_manifest_private_key.pem",
    "id_ed25519",
    "id_rsa",
    "private.key",
    "private.pem",
}

RELEASE_TEMP_FILE_PATTERNS = (
    "*.tmp",
    "*.tmp.zip",
    "zip-validation-*",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _source_baseline_paths() -> list[Path]:
    candidates = [
        *ROOT.glob("src/**/*.py"),
        *ROOT.glob("scripts/build-*.ps1"),
        *ROOT.glob("scripts/build-*.command"),
        ROOT / "requirements-build.txt",
    ]
    generated_files = {SRC / "commercial_manifest_public_key.py"}
    return [path for path in candidates if path.is_file() and path not in generated_files]


def _source_baseline_mtime() -> float:
    candidates = _source_baseline_paths()
    mtimes = [path.stat().st_mtime for path in candidates if path.is_file()]
    return max(mtimes) if mtimes else 0.0


def build_release_artifact_report(artifact_scope: str = "all") -> dict:
    artifact_names = ARTIFACT_SCOPES[artifact_scope]
    report = {}
    source_baseline = _source_baseline_mtime()
    for artifact_name in artifact_names:
        path = ROOT / "release" / artifact_name
        exists = path.exists()
        mtime = path.stat().st_mtime if exists else None
        freshness = "missing"
        if exists:
            freshness = "fresh" if mtime is not None and mtime >= source_baseline else "stale"
        report[artifact_name] = {
            "exists": exists,
            "size": path.stat().st_size if exists else 0,
            "sha256": _sha256(path) if exists else "",
            "last_write_time": mtime,
            "freshness": freshness,
            "source_baseline_time": source_baseline,
        }
    return report


def _is_packaged_internal_file(name: str) -> bool:
    normalized = name.replace("\\", "/").lstrip("/")
    lowered = normalized.lower()
    if normalized in PACKAGED_INTERNAL_EXACT_PATHS:
        return True
    if any(lowered.startswith(prefix.lower()) for prefix in PACKAGED_INTERNAL_PREFIXES):
        return True
    filename = Path(normalized).name
    if filename.lower() in PACKAGED_SENSITIVE_FILENAMES:
        return True
    return filename.startswith("deployer-commercial-") and filename.endswith(".md")


def inspect_packaged_zip_contents(path: Path) -> dict:
    if not path.exists():
        return {
            "exists": False,
            "zip_readable": False,
            "entry_count": 0,
            "internal_files_found": False,
            "internal_file_hits": [],
        }
    hits = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in names:
            normalized = name.replace("\\", "/").lstrip("/")
            if _is_packaged_internal_file(normalized):
                hits.append(normalized)

    return {
        "exists": True,
        "zip_readable": True,
        "entry_count": len(names),
        "internal_files_found": bool(hits),
        "internal_file_hits": sorted(set(hits)),
    }


def build_packaged_artifact_content_report(artifact_scope: str = "all") -> dict:
    report = {}
    for artifact_name in ARTIFACT_SCOPES[artifact_scope]:
        report[artifact_name] = inspect_packaged_zip_contents(ROOT / "release" / artifact_name)
    return report


def build_release_temp_file_report() -> dict:
    release_dir = ROOT / "release"
    hits: list[str] = []
    if release_dir.exists():
        for pattern in RELEASE_TEMP_FILE_PATTERNS:
            for path in release_dir.glob(pattern):
                if path.is_file():
                    hits.append(path.relative_to(ROOT).as_posix())
    return {
        "temp_files_found": bool(hits),
        "temp_file_hits": sorted(set(hits)),
    }


def build_generated_public_key_module_report() -> dict:
    module = SRC / "commercial_manifest_public_key.py"
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    exists = module.exists()
    has_bom = False
    syntax_ok = False
    public_key_injected = False
    if exists:
        raw = module.read_bytes()
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        text = module.read_text(encoding="utf-8")
        ast.parse(text, filename=str(module))
        syntax_ok = True
        namespace: dict[str, str] = {}
        exec(compile(text, str(module), "exec"), {}, namespace)
        public_key_injected = bool(namespace.get("PUBLIC_KEY_PEM", "").strip())

    return {
        "exists": exists,
        "has_bom": has_bom,
        "syntax_ok": syntax_ok,
        "public_key_injected": public_key_injected,
        "gitignored": "src/commercial_manifest_public_key.py" in gitignore,
    }


def _hard_boundary_text_files(deep_scan: bool) -> list[Path]:
    if not deep_scan:
        return sorted(
            (ROOT / relative for relative in LIGHT_HARD_BOUNDARY_SOURCE_FILES if (ROOT / relative).is_file()),
            key=lambda path: path.relative_to(ROOT).as_posix(),
        )
    return [
        path
        for path in [
            *ROOT.glob("src/**/*.py"),
            *ROOT.glob("scripts/**/*.py"),
            *ROOT.glob("scripts/**/*.ps1"),
            *ROOT.glob("scripts/**/*.command"),
            *ROOT.glob("docs/**/*.md"),
            *ROOT.glob("tests/**/*.py"),
            *ROOT.glob(".github/**/*.yml"),
        ]
        if path.is_file()
    ]


def build_hard_boundary_report(deep_scan: bool = False) -> dict:
    tracked_text_files = _hard_boundary_text_files(deep_scan)
    pattern_hits = []
    private_key_hits = []
    packaged_app_commercial_literal_hits = []
    packaged_app_commercial_static_value_hits = []
    non_codex_full_config_delivery_hits = []
    packaged_app_source_files_scanned = []
    for path in tracked_text_files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT).as_posix()
        for pattern in BOUNDARY_PATTERNS:
            if pattern in text:
                pattern_hits.append({"file": relative, "pattern": pattern})
        for pattern in PRIVATE_KEY_PATTERNS:
            if pattern in text:
                private_key_hits.append({"file": relative, "pattern": pattern})
        if relative in PACKAGED_APP_COMMERCIAL_SOURCE_FILES:
            packaged_app_source_files_scanned.append(relative)
            for pattern in PACKAGED_APP_COMMERCIAL_LITERAL_PATTERNS:
                if pattern in text:
                    packaged_app_commercial_literal_hits.append({"file": relative, "pattern": pattern})
            for pattern in PACKAGED_APP_COMMERCIAL_STATIC_VALUE_PATTERNS:
                if pattern.search(text):
                    packaged_app_commercial_static_value_hits.append({"file": relative, "pattern": pattern.pattern})
            for match in NON_CODEX_FULL_CONFIG_PATTERN.finditer(text):
                non_codex_full_config_delivery_hits.append(
                    {
                        "file": relative,
                        "agent_id": match.group("agent").lower(),
                        "pattern": "non_codex_full_config_allowed",
                    }
                )

    return {
        "scan_mode": "deep" if deep_scan else "light",
        "text_files_scanned": sorted(path.relative_to(ROOT).as_posix() for path in tracked_text_files),
        "external_mutation_executed": False,
        "static_pattern_hits": pattern_hits,
        "private_key_material_found": bool(private_key_hits),
        "private_key_hits": private_key_hits,
        "packaged_app_commercial_literals_found": bool(packaged_app_commercial_literal_hits),
        "packaged_app_commercial_literal_hits": packaged_app_commercial_literal_hits,
        "packaged_app_commercial_static_values_found": bool(packaged_app_commercial_static_value_hits),
        "packaged_app_commercial_static_value_hits": packaged_app_commercial_static_value_hits,
        "packaged_app_source_files_scanned": sorted(set(packaged_app_source_files_scanned)),
        "non_codex_full_config_delivery_found": bool(non_codex_full_config_delivery_hits),
        "non_codex_full_config_delivery_hits": non_codex_full_config_delivery_hits,
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def should_run_packaged_self_test() -> bool:
    return (
        os.environ.get("CI", "").lower() == "true"
        or os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
        or os.environ.get(LOCAL_PACKAGED_SELF_TEST_OPT_IN_ENV) == "1"
    )


def default_windows_release_zip() -> Path:
    return ROOT / "release" / WINDOWS_RELEASE_ARTIFACT


def _safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> tuple[bool, str]:
    destination_root = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        try:
            target.relative_to(destination_root)
        except ValueError:
            return False, f"客户 zip 包含不安全路径：{member.filename}"
    archive.extractall(destination)
    return True, ""


def _cleanup_windows_processes_under(root: Path) -> None:
    if sys.platform != "win32":
        return
    script = r"""
$Root = [System.IO.Path]::GetFullPath($args[0])
Get-Process | Where-Object {
    try {
        $_.Path -and [System.IO.Path]::GetFullPath($_.Path).StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)
    } catch {
        $false
    }
} | Stop-Process -Force
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script, str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def run_packaged_self_test(zip_path: Path | None = None) -> dict:
    source_zip = zip_path or default_windows_release_zip()
    if not source_zip.exists():
        return {"status": "WARN", "message": "未找到 Windows 客户 zip，跳过包内自检。", "source_zip": _display_path(source_zip)}
    with tempfile.TemporaryDirectory(prefix="panghu-release-selftest-") as temp_dir:
        extract_root = Path(temp_dir)
        with zipfile.ZipFile(source_zip) as archive:
            safe, message = _safe_extract_zip(archive, extract_root)
            if not safe:
                return {"status": "FAIL", "message": message, "source_zip": _display_path(source_zip)}
        exe_candidates = sorted(extract_root.rglob("*Agent*.exe")) or sorted(extract_root.rglob("*.exe"))
        if not exe_candidates:
            return {"status": "WARN", "message": "Windows 客户 zip 内未找到 exe，跳过包内自检。", "source_zip": _display_path(source_zip)}
        try:
            command = [str(exe_candidates[0]), "--self-test"]
            result = subprocess.run(
                command,
                cwd=extract_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=PACKAGED_SELF_TEST_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "status": "FAIL",
                "message": "Windows 包内自检超时。",
                "path": _display_path(exe_candidates[0]),
                "source_zip": _display_path(source_zip),
                "timeout_seconds": PACKAGED_SELF_TEST_TIMEOUT_SECONDS,
                "stdout": (exc.output or "").strip(),
                "stderr": (exc.stderr or "").strip(),
            }
        finally:
            _cleanup_windows_processes_under(extract_root)
        return {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "path": _display_path(exe_candidates[0]),
            "source_zip": _display_path(source_zip),
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }


def run_legacy_packaged_self_test() -> dict:
    release_dir = ROOT / "release"
    exe_candidates = sorted(release_dir.rglob("*Agent*.exe"))
    if not exe_candidates:
        return {"status": "WARN", "message": "未找到 Windows exe，跳过包内自检。"}
    result = subprocess.run(
        [str(exe_candidates[0]), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "path": str(exe_candidates[0].relative_to(ROOT)),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def build_report(include_exe_self_test: bool, artifact_scope: str = "all", deep_scan: bool = False) -> dict:
    artifact_report = build_release_artifact_report(artifact_scope=artifact_scope)
    packaged_content_report = build_packaged_artifact_content_report(artifact_scope=artifact_scope)
    release_temp_files = build_release_temp_file_report()
    missing_artifacts = [name for name, info in artifact_report.items() if not info["exists"]]
    commercial_flow = run_acceptance()
    generated_public_key = build_generated_public_key_module_report()
    hard_boundaries = build_hard_boundary_report(deep_scan=deep_scan)
    if include_exe_self_test and should_run_packaged_self_test():
        packaged_self_test = run_packaged_self_test()
    elif include_exe_self_test:
        packaged_self_test = {
            "status": "SKIPPED",
            "message": (
                "Local packaged self-test is skipped by default; set "
                f"{LOCAL_PACKAGED_SELF_TEST_OPT_IN_ENV}=1 to run it outside CI."
            ),
        }
    else:
        packaged_self_test = {"status": "SKIPPED"}

    warnings = []
    review_notes = []
    if missing_artifacts:
        warnings.append("缺少本地客户包：" + ", ".join(missing_artifacts))
    stale_artifacts = [name for name, info in artifact_report.items() if info.get("freshness") == "stale"]
    if stale_artifacts:
        warnings.append("以下客户包早于当前源码或构建脚本，需要重包：" + ", ".join(stale_artifacts))
    if not generated_public_key["public_key_injected"]:
        warnings.append("当前构建未注入商业清单生产公钥，商业清单会保持拒绝状态。")
    if hard_boundaries["static_pattern_hits"]:
        review_notes.append("文档或 CI 文件中存在生产/发布命令字样；本脚本只做静态提示，不代表本轮执行过发布动作。")
    if hard_boundaries["packaged_app_commercial_literals_found"]:
        warnings.append("客户包主程序包含商业价格或返佣比例样例，请移到测试或服务端清单。")
    if hard_boundaries["packaged_app_commercial_static_values_found"]:
        warnings.append("客户包主程序包含商业次数、有效期、设备数或上架状态样例，请移到测试或服务端清单。")
    if hard_boundaries["non_codex_full_config_delivery_found"]:
        warnings.append("客户包主程序疑似把未通过功能验收矩阵的 Agent 标为完整付费交付，请先完成配置写入、启动检测和最小对话验证。")
    content_hits = [
        f"{name}: " + ", ".join(info["internal_file_hits"])
        for name, info in packaged_content_report.items()
        if info["internal_files_found"]
    ]
    if content_hits:
        warnings.append("客户包 zip 内包含内部维护/测试/源码资料：" + "；".join(content_hits))
    if release_temp_files["temp_files_found"]:
        warnings.append("release 目录存在临时验证残留：" + ", ".join(release_temp_files["temp_file_hits"]))
    if packaged_self_test["status"] == "FAIL":
        warnings.append("Windows 包内自检失败。")

    return {
        "status": "PASS" if not warnings else "WARN",
        "offline_only": True,
        "artifact_scope": artifact_scope,
        "commercial_flow": commercial_flow,
        "release_artifacts": artifact_report,
        "packaged_artifact_contents": packaged_content_report,
        "release_temp_files": release_temp_files,
        "generated_public_key_module": generated_public_key,
        "hard_boundaries": hard_boundaries,
        "packaged_self_test": packaged_self_test,
        "untracked_superpowers_dir_present": (ROOT / "docs" / "superpowers").exists(),
        "warnings": warnings,
        "review_notes": review_notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local commercial release acceptance checks.")
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    parser.add_argument("--with-exe-self-test", action="store_true", help="Run packaged Windows exe --self-test.")
    parser.add_argument("--deep-scan", action="store_true", help="Scan docs, tests, and CI files for release boundary review notes.")
    parser.add_argument(
        "--artifact-scope",
        choices=sorted(ARTIFACT_SCOPES),
        default="all",
        help="Limit release artifact checks to one CI platform scope.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when the report is not PASS.")
    args = parser.parse_args()

    report = build_report(include_exe_self_test=args.with_exe_self_test, artifact_scope=args.artifact_scope, deep_scan=args.deep_scan)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        if args.strict and report["status"] != "PASS":
            raise SystemExit(1)
        return

    print(f"商业版本地验收：{report['status']}")
    for name, info in report["release_artifacts"].items():
        marker = "存在" if info["exists"] else "缺失"
        print(f"{name}：{marker} size={info['size']} sha256={info['sha256']}")
    for warning in report["warnings"]:
        print(f"警告：{warning}")
    for note in report["review_notes"]:
        print(f"提示：{note}")
    if args.strict and report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

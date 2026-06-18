import http.cookiejar
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import uuid
import webbrowser
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener, urlopen

try:
    import certifi
except Exception:  # pragma: no cover - runtime fallback for incomplete dev environments
    certifi = None


APP_NAME = "胖虎AI多Agent一键部署工具"
APP_VERSION = "1.0.15"
HTTP_USER_AGENT = f"PanghuAI-Agent-Deployer/{APP_VERSION}"
DEFAULT_BASE_URL = "https://aitokenapi.cc"
DEFAULT_MODEL = "gpt-5.4"
CODEX_PROVIDER_NAME = "panghuAI"
CODEX_BASE_URL = "https://aitokenapi.cc/v1"
TEMP_OPENAI_ACCESS_SECONDS = 600
TEMP_OPENAI_ACCESS_MAX_SECONDS = 600
GITHUB_RELEASE_API = "https://api.github.com/repos/dashuaiisme/panghu-codex-installer/releases/latest"
PUBLIC_UPDATE_MANIFEST_URL = f"{DEFAULT_BASE_URL}/deployer/latest.json"
WINDOWS_RELEASE_DIR_NAME = "胖虎AI多Agent一键部署工具"
WINDOWS_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Windows.zip"
WINDOWS_RELEASE_ASSET_ALIASES = (WINDOWS_RELEASE_ASSET_NAME, "AI.Agent.-Windows.zip")
MAC_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac.zip"
MAC_RELEASE_ASSET_ALIASES = (MAC_RELEASE_ASSET_NAME, "AI.Agent.-Mac.zip")
MAC_APPLE_SILICON_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac-AppleSilicon.zip"
MAC_INTEL_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac-Intel.zip"
MAC_APPLE_SILICON_RELEASE_ASSET_ALIASES = (
    MAC_APPLE_SILICON_RELEASE_ASSET_NAME,
    "AI.Agent.-Mac-AppleSilicon.zip",
    MAC_RELEASE_ASSET_NAME,
    "AI.Agent.-Mac.zip",
)
MAC_INTEL_RELEASE_ASSET_ALIASES = (MAC_INTEL_RELEASE_ASSET_NAME, "AI.Agent.-Mac-Intel.zip")
LOGIN_URL = f"{DEFAULT_BASE_URL}/api/user/login?turnstile="
DEPLOYER_ACTIVATE_URL = f"{DEFAULT_BASE_URL}/api/deployer/activate"
DEPLOYER_MANIFEST_URL = f"{DEFAULT_BASE_URL}/api/deployer/manifest"
REGISTER_URL = f"{DEFAULT_BASE_URL}/register"
KEY_CREATE_URL = f"{DEFAULT_BASE_URL}/login?next=/console/token"
CODEX_WINDOWS_STORE_URL = "https://get.microsoft.com/installer/download/9PLM9XGG6VKS?cid=website_cta_psi"
CODEX_DOWNLOAD_URL = "https://developers.openai.com/codex/"
CLAUDE_CODE_DOCS_URL = "https://docs.anthropic.com/en/docs/claude-code/setup"
OPENCLAW_DOCS_URL = "https://docs.openclaw.ai/start/getting-started"
HERMES_DOCS_URL = "https://hermes-agent.nousresearch.com/docs/zh-Hans/getting-started/installation"
OFFICIAL_PACKAGE_SUFFIXES = (".msixbundle", ".msix", ".appx", ".appxbundle", ".appinstaller")
PANGHU_AGENTS_START = "<!-- PANGHUAI_CODEX_RULES_START -->"
PANGHU_AGENTS_END = "<!-- PANGHUAI_CODEX_RULES_END -->"
APP_BG = "#f2eee7"
CARD_BG = "#fffdf8"
PANEL_BG = "#fbf6ee"
INK = "#2b2520"
MUTED = "#756b60"
PRIMARY = "#9f5132"
PRIMARY_DARK = "#67331f"
ACCENT = "#2f7d65"
BORDER = "#e4d8ca"
WARNING_BG = "#fff3e3"
GOLD = "#b9762b"
GOLD_SOFT = "#fff3d6"
LOCKED_BG = "#eee6dc"
SUCCESS_BG = "#eaf5ee"
INFO_BG = "#f6efe5"


@dataclass(frozen=True)
class AgentMode:
    id: str
    label: str
    note: str
    supports_auto_install: bool = True
    supports_config: bool = False


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    description: str
    verify_command: tuple[str, ...]
    modes: tuple[AgentMode, ...]
    config_note: str


@dataclass(frozen=True)
class RiskPluginSpec:
    id: str
    name: str
    aliases: tuple[str, ...]
    npm_packages: tuple[str, ...]
    marker_paths: tuple[Path, ...]
    uninstall_hint: str


@dataclass(frozen=True)
class RiskPluginFinding:
    name: str
    source: str
    detail: str
    uninstall_hint: str


@dataclass(frozen=True)
class TemporaryOpenAIAccessConfig:
    proxy: str
    duration_seconds: int = TEMP_OPENAI_ACCESS_SECONDS


class CodexConfigMode(str, Enum):
    DIRECT_API = "direct_api"
    DUAL_STATE = "dual_state"


AGENTS = (
    AgentSpec(
        id="codex",
        name="Codex",
        description="OpenAI 官方 Codex Agent，支持 CLI 与 Windows 客户端安装/修复。",
        verify_command=("codex", "--version"),
        modes=(
            AgentMode("cli", "CLI", "安装官方 Codex CLI。", supports_config=True),
            AgentMode("client", "客户端", "Windows 走官方 Store/App 包；其他系统打开官方入口。", supports_config=True),
        ),
        config_note="可自动写入胖虎AI API Key、接口、模型、中文规则和默认工作区。",
    ),
    AgentSpec(
        id="claude_code",
        name="ClaudeCode",
        description="Anthropic 官方 Claude Code Agent。本工具只安装，不写配置。",
        verify_command=("claude", "--version"),
        modes=(
            AgentMode("cli", "CLI", "使用官方 npm 包安装 Claude Code。"),
            AgentMode("client", "客户端", "打开 Claude Code 官方安装入口；不伪造第三方客户端。", supports_auto_install=False),
        ),
        config_note="只安装 Agent，不写 Key，不改 ClaudeCode 账号或配置。",
    ),
    AgentSpec(
        id="openclaw",
        name="OpenClaw",
        description="OpenClaw Agent，优先走官方在线安装与官方客户端入口。",
        verify_command=("openclaw", "--version"),
        modes=(
            AgentMode("cli", "CLI", "使用 OpenClaw 官方在线脚本安装。"),
            AgentMode("client", "客户端", "打开 OpenClaw 官方客户端/Hub 入口。", supports_auto_install=False),
        ),
        config_note="当前只在官方安全路径明确时配置；本版先安装并给出中文配置指引。",
    ),
    AgentSpec(
        id="hermes",
        name="Hermes",
        description="Nous Research Hermes Agent，优先走官方在线安装。",
        verify_command=("hermes", "--version"),
        modes=(
            AgentMode("cli", "CLI", "使用 Hermes 官方在线安装入口。"),
            AgentMode("client", "客户端", "打开 Hermes 官方文档；不伪造桌面客户端。", supports_auto_install=False),
        ),
        config_note="当前只在官方安全路径明确时配置；本版先安装并给出中文配置指引。",
    ),
)

RISK_PLUGIN_SPECS = (
    RiskPluginSpec(
        id="ccswitch",
        name="CCSwitch",
        aliases=("ccswitch", "cc-switch", "claude-code-switch"),
        npm_packages=("ccswitch", "cc-switch", "claude-code-switch"),
        marker_paths=(Path.home() / ".ccswitch", Path.home() / ".claude-code-switch"),
        uninstall_hint="如果是 npm 安装，请执行 npm uninstall -g ccswitch cc-switch claude-code-switch；如果是单独客户端，请在系统应用列表里卸载。",
    ),
    RiskPluginSpec(
        id="codex_plus_plus",
        name="Codex++",
        aliases=("codex++", "codexpp", "codex-plus-plus", "codex-plusplus"),
        npm_packages=("codex++", "codexpp", "codex-plus-plus", "codex-plusplus"),
        marker_paths=(Path.home() / ".codex++", Path.home() / ".codexpp", Path.home() / ".codex-plus-plus"),
        uninstall_hint="如果是 npm 安装，请执行 npm uninstall -g codex++ codexpp codex-plus-plus codex-plusplus；如果是压缩包或客户端安装，请删除对应程序并移除 PATH。",
    ),
    RiskPluginSpec(
        id="claude_code_router",
        name="Claude Code Router / CCR",
        aliases=("ccr", "claude-code-router"),
        npm_packages=("ccr", "claude-code-router", "@musistudio/claude-code-router"),
        marker_paths=(Path.home() / ".claude-code-router", Path.home() / ".config" / "claude-code-router"),
        uninstall_hint="如果是 npm 安装，请执行 npm uninstall -g ccr claude-code-router @musistudio/claude-code-router；如果仍在运行，请先退出该工具。",
    ),
)


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return "******"
    return f"{value[:6]}...{value[-4:]}"


def sanitize_log_text(message: str, *known_secrets: str) -> str:
    text = str(message)
    for secret in known_secrets:
        secret = str(secret or "").strip()
        if secret:
            text = text.replace(secret, mask_key(secret))
    return re.sub(r"\bsk[-_][A-Za-z0-9][A-Za-z0-9._-]{8,}\b", lambda match: mask_key(match.group(0)), text)


def codex_home() -> Path:
    return Path.home() / ".codex"


def codex_auth_path() -> Path:
    return codex_home() / "auth.json"


def workspace_root() -> Path:
    return Path.home() / "Documents" / "胖虎AI-Agent工作区"


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "PanghuAI-Agent-Deployer"
    return Path.home() / ".panghuai-agent-deployer"


def profile_path() -> Path:
    return app_data_dir() / "profile.json"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def asset_path(name: str) -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled = Path(bundled_root) / "assets" / name
        if bundled.exists():
            return bundled
    root = app_root()
    for candidate in (
        root / "assets" / name,
        root.parent / "Resources" / "assets" / name,
        root.parent / "Frameworks" / "assets" / name,
    ):
        if candidate.exists():
            return candidate
    return app_root() / "assets" / name


def current_system_id() -> str:
    name = platform.system()
    if name == "Windows":
        return "windows"
    if name == "Darwin":
        return "mac"
    return "other"


def run_command(command: list[str], timeout: int = 900) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return False, f"未找到命令：{command[0]}"
    except subprocess.TimeoutExpired:
        return False, "命令执行超时。"
    except Exception as exc:
        return False, f"命令执行失败：{exc}"
    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode == 0:
        return True, output or "命令执行完成。"
    return False, output or f"命令退出码：{result.returncode}"


def command_exists(command: str) -> tuple[bool, str]:
    exe = shutil.which(command)
    return bool(exe), exe or ""


def version_for(command: tuple[str, ...]) -> tuple[bool, str]:
    if not shutil.which(command[0]):
        return False, ""
    ok, output = run_command(list(command), timeout=12)
    return ok, output.splitlines()[0] if output else ""


def npm_global_packages() -> set[str]:
    if not shutil.which("npm"):
        return set()
    try:
        result = subprocess.run(
            ["npm", "list", "-g", "--depth=0", "--json"],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
    except Exception:
        return set()
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return set()
    dependencies = payload.get("dependencies") or {}
    if not isinstance(dependencies, dict):
        return set()
    return {str(name).lower() for name in dependencies}


def running_process_text() -> str:
    if platform.system() == "Windows":
        ok, output = run_command(["tasklist", "/FO", "CSV", "/NH"], timeout=5)
    else:
        ok, output = run_command(["ps", "-ax", "-o", "command="], timeout=5)
    return output.lower() if ok else ""


def process_text_contains_alias(process_text: str, alias: str) -> bool:
    alias = alias.strip().lower()
    if not process_text or not alias:
        return False
    pattern = rf"(?<![a-z0-9_.+\-]){re.escape(alias)}(?![a-z0-9_.+\-])"
    return re.search(pattern, process_text.lower()) is not None


def detect_risk_plugins() -> list[RiskPluginFinding]:
    findings: list[RiskPluginFinding] = []
    npm_packages = npm_global_packages()
    process_text = running_process_text()
    seen: set[tuple[str, str, str]] = set()

    def add(spec: RiskPluginSpec, source: str, detail: str) -> None:
        key = (spec.id, source, detail)
        if key in seen:
            return
        seen.add(key)
        findings.append(RiskPluginFinding(spec.name, source, detail, spec.uninstall_hint))

    for spec in RISK_PLUGIN_SPECS:
        for alias in spec.aliases:
            exists, path = command_exists(alias)
            if exists:
                add(spec, "命令", f"{alias} -> {path}")
            if process_text_contains_alias(process_text, alias):
                add(spec, "运行中", f"检测到进程关键字：{alias}")
        for package_name in spec.npm_packages:
            if package_name.lower() in npm_packages:
                add(spec, "npm 全局包", package_name)
        for marker_path in spec.marker_paths:
            if marker_path.exists():
                add(spec, "配置目录", str(marker_path))
    return findings


def risk_plugin_report_lines(findings: list[RiskPluginFinding]) -> list[str]:
    if not findings:
        return ["风险插件：未发现 ccswitch、codex++、CCR 等第三方配置切换工具。"]
    lines = [
        "风险插件：发现第三方配置切换工具，已禁止继续安装。",
        "原因：这类工具可能接管或改写 Codex / ClaudeCode 配置，导致胖虎AI写入的配置被改坏。",
    ]
    for finding in findings:
        lines.append(f"- {finding.name}：{finding.source}，{finding.detail}")
    lines.append("请先卸载或禁用这些工具，重新打开本工具后再部署。")
    return lines


def format_risk_plugin_block_message(findings: list[RiskPluginFinding]) -> str:
    lines = [
        "检测到会改写 Agent 配置的第三方插件，已停止安装。",
        "",
        "为了防止这些软件把 Codex / ClaudeCode 配置改坏，请先卸载或禁用后再继续。",
        "",
        "发现项目：",
    ]
    for finding in findings:
        lines.append(f"- {finding.name}（{finding.source}）：{finding.detail}")
    hints = []
    for finding in findings:
        if finding.uninstall_hint not in hints:
            hints.append(finding.uninstall_hint)
    if hints:
        lines.extend(["", "处理建议："])
        lines.extend(f"- {hint}" for hint in hints)
    lines.extend(["", "处理完成后，请重新打开本工具并重新检测环境。"])
    return "\n".join(lines)


def codex_command_exists() -> tuple[bool, str]:
    return version_for(("codex", "--version"))


def codex_app_package_exists() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, ""
    ok, output = run_command(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1 -ExpandProperty PackageFullName",
        ],
        timeout=12,
    )
    package = output.strip() if ok else ""
    return bool(package), package


def create_codex_shortcuts(log) -> None:
    if platform.system() != "Windows":
        return
    package_ok, _package = codex_app_package_exists()
    if not package_ok:
        return
    shortcut_targets = [
        Path.home() / "Desktop" / "Codex.lnk",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Codex.lnk",
    ]
    shortcut_commands = []
    for target in shortcut_targets:
        if not str(target):
            continue
        safe_target = str(target).replace("'", "''")
        shortcut_commands.append(
            f"$s = $shell.CreateShortcut('{safe_target}'); "
            "$s.TargetPath = 'explorer.exe'; "
            "$s.Arguments = 'shell:AppsFolder\\OpenAI.Codex_8wekyb3d8bbwe!App'; "
            "$s.IconLocation = 'shell32.dll,220'; "
            "$s.Save()"
        )
    script = "\n".join(
        [
            "$shell = New-Object -ComObject WScript.Shell",
            *shortcut_commands,
        ]
    )
    ok, output = run_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=20)
    if ok:
        log("已创建 Codex 快捷方式：桌面和开始菜单。")
    else:
        log(f"Codex 快捷方式创建失败：{output}")


def agent_client_status(agent: AgentSpec) -> tuple[bool, str]:
    if agent.id == "codex":
        return codex_app_package_exists()
    if agent.id == "claude_code":
        return False, "ClaudeCode 当前按官方 CLI/文档入口检测，未发现可稳定识别的独立客户端包。"
    if agent.id == "openclaw":
        return False, "OpenClaw 当前按官方 CLI/Hub 入口检测，未发现可稳定识别的独立客户端包。"
    if agent.id == "hermes":
        return False, "Hermes 当前按官方 CLI/文档入口检测，未发现可稳定识别的独立客户端包。"
    return False, "未配置客户端检测规则。"


def agent_install_status_lines() -> list[str]:
    lines = ["Agent 检测："]
    for agent in AGENTS:
        cli_ok, cli_version = version_for(agent.verify_command)
        client_ok, client_detail = agent_client_status(agent)
        cli_text = f"CLI 已找到 {cli_version}" if cli_ok else "CLI 未找到"
        if client_ok:
            client_text = f"客户端已找到 {client_detail}"
        else:
            client_text = f"客户端未确认：{client_detail}"
        lines.append(f"- {agent.name}: {cli_text}；{client_text}")
    return lines


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_saved_profile() -> dict:
    path = profile_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_profile_data(data: dict) -> None:
    current = load_saved_profile()
    current.update(data)
    safe = {
        "username": str(current.get("username") or ""),
        "user": current.get("user") if isinstance(current.get("user"), dict) else {},
        "deployer_auth": current.get("deployer_auth") if isinstance(current.get("deployer_auth"), dict) else {},
        "api_key": str(current.get("api_key") or ""),
        "base_url": DEFAULT_BASE_URL,
        "model": str(current.get("model") or DEFAULT_MODEL),
        "skip_test": bool(current.get("skip_test")),
        "open_app": bool(current.get("open_app", True)),
    }
    write_text(profile_path(), json.dumps(safe, ensure_ascii=False, indent=2) + "\n")


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, backup)
    return backup


def restore_backup(path: Path, backup: Path | None, existed_before: bool) -> None:
    if backup and backup.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, path)
    elif not existed_before and path.exists():
        path.unlink()


def latest_backup_for(path: Path) -> Path | None:
    if not path.parent.exists():
        return None
    backups = sorted(
        path.parent.glob(f"{path.name}.bak-*"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return backups[0] if backups else None


def restore_latest_backups(log) -> bool:
    targets = [
        codex_home() / "config.toml",
        codex_auth_path(),
        codex_home() / "AGENTS.md",
        workspace_root() / "AGENTS.md",
    ]
    restored = False
    for target in targets:
        backup = latest_backup_for(target)
        if not backup:
            log(f"未找到可恢复备份：{target}")
            continue
        restore_backup(target, backup, True)
        restored = True
        log(f"已恢复：{target} <- {backup}")
    return restored


def build_config(api_key: str, base_url: str, model: str) -> str:
    return '''model_provider = "panghuAI"
model = "gpt-5.4"
review_model = "gpt-5.4"
model_reasoning_effort = "xhigh"
disable_response_storage = true
network_access = "enabled"
windows_wsl_setup_acknowledged = true
model_context_window = 1000000
model_auto_compact_token_limit =600000

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
requires_openai_auth = true
'''


def build_dual_state_config(api_key: str, base_url: str, model: str) -> str:
    safe_api_key = api_key.strip().replace("\\", "\\\\").replace('"', '\\"')
    config = build_config(api_key, base_url, model)
    return config.replace(
        'wire_api = "responses"\n',
        f'wire_api = "responses"\nexperimental_bearer_token = "{safe_api_key}"\n',
    )


def chinese_rules() -> str:
    return """# 胖虎AI Agent 客户默认规则

- 默认使用简体中文回答。
- 用户没有明确要求英文时，不要切换到英文。
- 解释步骤时使用普通用户能看懂的说法，少用英文术语。
- 遇到 API、模型、网络、权限问题时，先给出可执行的修复步骤。
"""


def managed_chinese_rules_block() -> str:
    return f"{PANGHU_AGENTS_START}\n{chinese_rules().strip()}\n{PANGHU_AGENTS_END}\n"


def merge_agents_rules(existing: str) -> str:
    block = managed_chinese_rules_block()
    pattern = re.compile(
        rf"{re.escape(PANGHU_AGENTS_START)}.*?{re.escape(PANGHU_AGENTS_END)}\s*",
        re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(block, existing)
    prefix = existing.rstrip()
    if prefix:
        return f"{prefix}\n\n{block}"
    return block


def section_name(line: str) -> str | None:
    match = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
    if match:
        return match.group(1).strip()
    return None


def remove_sections(lines: list[str], names: set[str]) -> list[str]:
    kept: list[str] = []
    skipping = False
    for line in lines:
        name = section_name(line)
        if name is not None:
            skipping = name in names
        if not skipping:
            kept.append(line)
    return kept


def update_top_level_keys(lines: list[str], values: list[str], keys: set[str]) -> list[str]:
    first_section = next((idx for idx, line in enumerate(lines) if section_name(line) is not None), len(lines))
    top = []
    for line in lines[:first_section]:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key not in keys:
            top.append(line)
    while top and top[-1].strip() == "":
        top.pop()
    rest = lines[first_section:]
    merged = top + values
    if rest:
        merged.append("")
        merged.extend(rest)
    return merged


def update_or_append_section(lines: list[str], name: str, values: list[str], keys: set[str]) -> list[str]:
    start = next((idx for idx, line in enumerate(lines) if section_name(line) == name), None)
    if start is None:
        result = lines[:]
        if result and result[-1].strip():
            result.append("")
        result.append(f"[{name}]")
        result.extend(values)
        return result

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if section_name(lines[idx]) is not None:
            end = idx
            break

    body = []
    for line in lines[start + 1 : end]:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key not in keys:
            body.append(line)
    return lines[: start + 1] + values + body + lines[end:]


def merge_config(existing: str, api_key: str, base_url: str, model: str) -> str:
    return build_config(api_key, base_url, model)


def build_auth_json(existing: str, api_key: str) -> str:
    return build_direct_api_auth_json(existing, api_key)


def build_direct_api_auth_json(existing: str, api_key: str) -> str:
    payload = {"OPENAI_API_KEY": api_key.strip()}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_dual_state_auth_json(existing: str, api_key: str) -> str:
    try:
        payload = json.loads(existing) if existing.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
    except json.JSONDecodeError:
        payload = {}
    payload["auth_mode"] = "chatgpt"
    payload["OPENAI_API_KEY"] = None
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def trusted_ssl_context() -> ssl.SSLContext:
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def trusted_urlopen(req: Request, timeout: int = 20):
    return urlopen(req, timeout=timeout, context=trusted_ssl_context())


def build_trusted_opener(cookie_jar: http.cookiejar.CookieJar | None = None):
    handlers = [HTTPSHandler(context=trusted_ssl_context())]
    if cookie_jar is not None:
        handlers.insert(0, HTTPCookieProcessor(cookie_jar))
    return build_opener(*handlers)


def download_with_trusted_certs(url: str, target: Path) -> None:
    req = Request(url, headers={"User-Agent": HTTP_USER_AGENT})
    with trusted_urlopen(req, timeout=60) as resp, target.open("wb") as file:
        shutil.copyfileobj(resp, file)


def test_api(base_url: str, api_key: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/v1/models"
    req = Request(url, headers={"Authorization": f"Bearer {api_key}"}, method="GET")
    try:
        with trusted_urlopen(req, timeout=20) as resp:
            return True, f"接口连通正常：HTTP {resp.status}"
    except HTTPError as exc:
        return False, f"接口返回错误：HTTP {exc.code}"
    except URLError as exc:
        return False, f"接口连接失败：{exc.reason}"
    except Exception as exc:
        return False, f"接口测试失败：{exc}"


def current_platform_for_license() -> str:
    system = current_system_id()
    return system if system in {"windows", "mac"} else "unknown"


def device_fingerprint() -> str:
    raw = "|".join(
        [
            platform.node(),
            platform.system(),
            platform.release(),
            platform.machine(),
            str(uuid.getnode()),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def open_json_with_cookies(
    cookie_jar: http.cookiejar.CookieJar,
    url: str,
    method: str,
    body: dict | None = None,
    headers: dict | None = None,
) -> dict:
    opener = build_trusted_opener(cookie_jar)
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": HTTP_USER_AGENT,
        **(headers or {}),
    }
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=request_headers, method=method)
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login_panghuai(username: str, password: str, cookie_jar: http.cookiejar.CookieJar) -> tuple[bool, str, dict]:
    if not username.strip() or not password:
        return False, "请输入胖虎AI账号和密码。", {}
    opener = build_trusted_opener(cookie_jar)
    body = json.dumps({"username": username.strip(), "password": password}).encode("utf-8")
    req = Request(
        LOGIN_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": HTTP_USER_AGENT},
        method="POST",
    )
    try:
        with opener.open(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return False, f"登录接口返回错误：HTTP {exc.code}", {}
    except URLError as exc:
        return False, f"登录接口连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "登录接口返回内容无法解析。", {}
    except Exception as exc:
        return False, f"登录失败：{exc}", {}

    if not payload.get("success"):
        return False, str(payload.get("message") or "账号或密码错误。"), {}
    data = payload.get("data") or {}
    return True, "登录成功。", data


def activate_deployer(user: dict, cookie_jar: http.cookiejar.CookieJar) -> tuple[bool, str, dict]:
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        return False, "登录返回缺少用户 ID，无法申请部署授权。", {}
    try:
        payload = open_json_with_cookies(
            cookie_jar,
            DEPLOYER_ACTIVATE_URL,
            "POST",
            {
                "device_id": device_fingerprint(),
                "platform": current_platform_for_license(),
                "app_version": APP_VERSION,
            },
            {"New-Api-User": user_id},
        )
    except HTTPError as exc:
        return False, f"部署授权接口返回错误：HTTP {exc.code}", {}
    except URLError as exc:
        return False, f"部署授权接口连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "部署授权接口返回内容无法解析。", {}
    except Exception as exc:
        return False, f"部署授权失败：{exc}", {}
    if not payload.get("success"):
        return False, str(payload.get("message") or "部署授权被拒绝。"), {}
    data = payload.get("data") or {}
    token = str(data.get("token") or "")
    if not token:
        return False, "部署授权返回缺少 token。", {}
    return True, "部署授权已通过。", data


def fetch_deployer_manifest(user: dict, cookie_jar: http.cookiejar.CookieJar, deployer_token: str) -> tuple[bool, str, dict]:
    user_id = str(user.get("id") or "").strip()
    if not user_id or not deployer_token:
        return False, "缺少部署授权，请重新登录。", {}
    try:
        payload = open_json_with_cookies(
            cookie_jar,
            DEPLOYER_MANIFEST_URL,
            "GET",
            None,
            {"New-Api-User": user_id, "X-Panghu-Deployer-Token": deployer_token},
        )
    except HTTPError as exc:
        return False, f"部署清单接口返回错误：HTTP {exc.code}", {}
    except URLError as exc:
        return False, f"部署清单接口连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "部署清单接口返回内容无法解析。", {}
    except Exception as exc:
        return False, f"部署清单获取失败：{exc}", {}
    if not payload.get("success"):
        return False, str(payload.get("message") or "部署清单被拒绝。"), {}
    return True, "部署清单校验通过。", payload.get("data") or {}


def manifest_allowed_agents(manifest: dict) -> list[str]:
    agents = manifest.get("agents") or []
    allowed: list[str] = []
    if isinstance(agents, list):
        for item in agents:
            if isinstance(item, dict) and item.get("id"):
                allowed.append(str(item["id"]))
    return allowed


def parse_temporary_openai_access_config(manifest: dict) -> TemporaryOpenAIAccessConfig | None:
    raw = manifest.get("temporary_openai_access")
    if not isinstance(raw, dict) or not raw.get("enabled"):
        return None
    proxy = str(raw.get("proxy") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9.-]+:\d{2,5}", proxy):
        return None
    host, port_text = proxy.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError:
        return None
    if not host or port < 1 or port > 65535:
        return None
    duration = raw.get("duration_seconds", TEMP_OPENAI_ACCESS_SECONDS)
    try:
        duration_seconds = int(duration)
    except (TypeError, ValueError):
        duration_seconds = TEMP_OPENAI_ACCESS_SECONDS
    duration_seconds = max(60, min(duration_seconds, TEMP_OPENAI_ACCESS_MAX_SECONDS))
    return TemporaryOpenAIAccessConfig(proxy=proxy, duration_seconds=duration_seconds)


def build_openai_access_pac(proxy: str, fallback: str = "DIRECT") -> str:
    return f"""function FindProxyForURL(url, host) {{
  host = host.toLowerCase();
  if (
    shExpMatch(host, "openai.com") ||
    shExpMatch(host, "*.openai.com") ||
    shExpMatch(host, "chatgpt.com") ||
    shExpMatch(host, "*.chatgpt.com") ||
    shExpMatch(host, "auth0.openai.com") ||
    shExpMatch(host, "cdn.openai.com") ||
    shExpMatch(host, "*.oaistatic.com") ||
    shExpMatch(host, "*.oaiusercontent.com")
  ) {{
    return "PROXY {proxy}; DIRECT";
  }}
  return "{fallback}";
}}
"""


def build_windows_temp_openai_access_script() -> str:
    return r'''
param(
    [Parameter(Mandatory=$true)][string]$PacPath,
    [int]$Seconds = 600,
    [switch]$RestoreOnly
)
$ErrorActionPreference = "Stop"
$internetSettings = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
$statePath = "$PacPath.state.json"
$restoreTaskName = "PanghuAI-OpenAI-Access-Restore-" + [IO.Path]::GetFileNameWithoutExtension($PacPath)
$scriptSelf = $MyInvocation.MyCommand.Path
$refreshType = @"
using System;
using System.Runtime.InteropServices;
public static class NativeInternetOptions {
    [DllImport("wininet.dll", SetLastError=true)]
    public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
}
"@
try {
    Add-Type -TypeDefinition $refreshType -ErrorAction SilentlyContinue
} catch {}

function Update-InternetProxySettings {
    try {
        [NativeInternetOptions]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null
        [NativeInternetOptions]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0) | Out-Null
    } catch {}
}

function Get-InternetProxyState {
    $item = Get-ItemProperty -Path $internetSettings
    return [ordered]@{
        ProxyEnable = if ($null -ne $item.ProxyEnable) { [int]$item.ProxyEnable } else { $null }
        ProxyServer = if ($null -ne $item.ProxyServer) { [string]$item.ProxyServer } else { $null }
        ProxyOverride = if ($null -ne $item.ProxyOverride) { [string]$item.ProxyOverride } else { $null }
        AutoConfigURL = if ($null -ne $item.AutoConfigURL) { [string]$item.AutoConfigURL } else { $null }
    }
}

function Set-InternetProxyState($state) {
    if ($null -ne $state.ProxyEnable) {
        Set-ItemProperty -Path $internetSettings -Name ProxyEnable -Value ([int]$state.ProxyEnable)
    } else {
        Remove-ItemProperty -Path $internetSettings -Name ProxyEnable -ErrorAction SilentlyContinue
    }
    foreach ($name in @("ProxyServer", "ProxyOverride", "AutoConfigURL")) {
        if ($null -ne $state.$name -and [string]$state.$name -ne "") {
            Set-ItemProperty -Path $internetSettings -Name $name -Value ([string]$state.$name)
        } else {
            Remove-ItemProperty -Path $internetSettings -Name $name -ErrorAction SilentlyContinue
        }
    }
}

function Restore-InternetProxyState {
    if (Test-Path -LiteralPath $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        Set-InternetProxyState $state
        Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
    }
    Update-InternetProxySettings
    Unregister-ScheduledTask -TaskName $restoreTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $PacPath -Force -ErrorAction SilentlyContinue
}

function Register-FallbackRestoreTask {
    if (-not $scriptSelf) {
        return
    }
    $runAt = (Get-Date).AddSeconds([Math]::Max(60, $Seconds + 15))
    $argument = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptSelf`" -PacPath `"$PacPath`" -RestoreOnly"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
    $trigger = New-ScheduledTaskTrigger -Once -At $runAt
    Register-ScheduledTask -TaskName $restoreTaskName -Action $action -Trigger $trigger -Description "PanghuAI temporary OpenAI access restore" -Force | Out-Null
}

if ($RestoreOnly) {
    Restore-InternetProxyState
    exit 0
}

try {
    Get-InternetProxyState | ConvertTo-Json -Compress | Set-Content -LiteralPath $statePath -Encoding UTF8
    Register-FallbackRestoreTask
    $pacUrl = (New-Object System.Uri($PacPath)).AbsoluteUri
    Set-ItemProperty -Path $internetSettings -Name AutoConfigURL -Value $pacUrl
    Set-ItemProperty -Path $internetSettings -Name ProxyEnable -Value 0
    Update-InternetProxySettings
    Start-Sleep -Seconds $Seconds
} finally {
    Restore-InternetProxyState
}
'''


def build_macos_temp_openai_access_script() -> str:
    return r'''#!/bin/zsh
set -euo pipefail

PAC_PATH=""
SECONDS_VALUE="600"
RESTORE_ONLY="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pac)
      PAC_PATH="$2"
      shift 2
      ;;
    --seconds)
      SECONDS_VALUE="$2"
      shift 2
      ;;
    --restore-only)
      RESTORE_ONLY="1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [[ -z "$PAC_PATH" ]]; then
  exit 2
fi

STATE_PATH="${PAC_PATH}.state"
SCRIPT_SELF="$0"
LAUNCH_DAEMON_DIR="/Library/LaunchDaemons"
LAUNCH_DAEMON_LABEL="cc.panghuai.openai-access-restore-$(basename "$PAC_PATH" .pac)"
LAUNCH_DAEMON_PLIST="$LAUNCH_DAEMON_DIR/${LAUNCH_DAEMON_LABEL}.plist"
PAC_URL="file://${PAC_PATH}"

networksetup_path="/usr/sbin/networksetup"
scutil_path="/usr/sbin/scutil"
launchctl_path="/bin/launchctl"

list_services() {
  "$networksetup_path" -listallnetworkservices 2>/dev/null | sed '1d;s/^\*//'
}

refresh_proxy_settings() {
  "$scutil_path" --proxy >/dev/null 2>&1 || true
}

save_state() {
  : > "$STATE_PATH"
  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    auto_enabled="$("$networksetup_path" -getautoproxyurl "$service" 2>/dev/null | awk -F': ' '/Enabled:/ {print $2; exit}')"
    auto_url="$("$networksetup_path" -getautoproxyurl "$service" 2>/dev/null | awk -F': ' '/URL:/ {print $2; exit}')"
    web_enabled="$("$networksetup_path" -getwebproxy "$service" 2>/dev/null | awk -F': ' '/Enabled:/ {print $2; exit}')"
    secure_enabled="$("$networksetup_path" -getsecurewebproxy "$service" 2>/dev/null | awk -F': ' '/Enabled:/ {print $2; exit}')"
    printf '%s\t%s\t%s\t%s\t%s\n' "$service" "${auto_enabled:-No}" "${auto_url:-}" "${web_enabled:-No}" "${secure_enabled:-No}" >> "$STATE_PATH"
  done < <(list_services)
}

restore_state() {
  if [[ -f "$STATE_PATH" ]]; then
    while IFS=$'\t' read -r service auto_enabled auto_url web_enabled secure_enabled; do
      [[ -z "$service" ]] && continue
      if [[ -n "${auto_url:-}" ]]; then
        "$networksetup_path" -setautoproxyurl "$service" "$auto_url" >/dev/null 2>&1 || true
      fi
      if [[ "${auto_enabled:-No}" == "Yes" ]]; then
        "$networksetup_path" -setautoproxystate "$service" on >/dev/null 2>&1 || true
      else
        "$networksetup_path" -setautoproxystate "$service" off >/dev/null 2>&1 || true
      fi
      if [[ "${web_enabled:-No}" == "Yes" ]]; then
        "$networksetup_path" -setwebproxystate "$service" on >/dev/null 2>&1 || true
      else
        "$networksetup_path" -setwebproxystate "$service" off >/dev/null 2>&1 || true
      fi
      if [[ "${secure_enabled:-No}" == "Yes" ]]; then
        "$networksetup_path" -setsecurewebproxystate "$service" on >/dev/null 2>&1 || true
      else
        "$networksetup_path" -setsecurewebproxystate "$service" off >/dev/null 2>&1 || true
      fi
    done < "$STATE_PATH"
    rm -f "$STATE_PATH"
  fi
  if [[ -f "$LAUNCH_DAEMON_PLIST" ]]; then
    "$launchctl_path" bootout system "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
    "$launchctl_path" unload "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
    rm -f "$LAUNCH_DAEMON_PLIST"
  fi
  rm -f "$PAC_PATH"
  refresh_proxy_settings
}

register_fallback_restore() {
  mkdir -p "$LAUNCH_DAEMON_DIR"
  cat > "$LAUNCH_DAEMON_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LAUNCH_DAEMON_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>${SCRIPT_SELF}</string>
    <string>--pac</string>
    <string>${PAC_PATH}</string>
    <string>--restore-only</string>
  </array>
  <key>StartInterval</key>
  <integer>$((SECONDS_VALUE + 15))</integer>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST
  chown root:wheel "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
  chmod 644 "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
  "$launchctl_path" bootstrap system "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || "$launchctl_path" load "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
}

enable_pac() {
  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    "$networksetup_path" -setautoproxyurl "$service" "$PAC_URL" >/dev/null 2>&1 || true
    "$networksetup_path" -setautoproxystate "$service" on >/dev/null 2>&1 || true
    "$networksetup_path" -setwebproxystate "$service" off >/dev/null 2>&1 || true
    "$networksetup_path" -setsecurewebproxystate "$service" off >/dev/null 2>&1 || true
  done < <(list_services)
  refresh_proxy_settings
}

if [[ "$RESTORE_ONLY" == "1" ]]; then
  restore_state
  exit 0
fi

trap restore_state EXIT INT TERM
save_state
register_fallback_restore
enable_pac
/bin/sleep "$SECONDS_VALUE"
'''


def start_temporary_openai_access(config: TemporaryOpenAIAccessConfig | None, log) -> bool:
    if not config:
        return False
    system = platform.system()
    if system not in {"Windows", "Darwin"}:
        log("临时 OpenAI 访问窗口当前只支持 Windows 和 Mac，其他系统不会改动系统代理。")
        return False
    runtime_dir = app_data_dir() / "temporary-openai-access"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    active_states = list(runtime_dir.glob("*.state.json")) + list(runtime_dir.glob("*.state"))
    if active_states:
        log("检测到已有 OpenAI 官网临时访问窗口，本次不重复改动系统代理。")
        return True
    suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    pac_path = runtime_dir / f"openai-access-{suffix}.pac"
    write_text(pac_path, build_openai_access_pac(config.proxy))
    if system == "Windows":
        script_path = runtime_dir / "restore-openai-access.ps1"
        write_text(script_path, build_windows_temp_openai_access_script())
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-PacPath",
            str(pac_path),
            "-Seconds",
            str(config.duration_seconds),
        ]
    else:
        script_path = runtime_dir / "restore-openai-access.command"
        write_text(script_path, build_macos_temp_openai_access_script())
        try:
            script_path.chmod(0o755)
        except Exception:
            pass
        shell_command = " ".join(
            [
                shlex.quote("/bin/zsh"),
                shlex.quote(str(script_path)),
                "--pac",
                shlex.quote(str(pac_path)),
                "--seconds",
                shlex.quote(str(config.duration_seconds)),
            ]
        )
        command = [
            "osascript",
            "-e",
            "do shell script " + json.dumps(shell_command) + " with administrator privileges",
        ]
    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(command, **kwargs)
    except Exception as exc:
        log(f"临时 OpenAI 访问窗口启动失败：{exc}")
        return False
    minutes = max(1, config.duration_seconds // 60)
    log(f"已开启 OpenAI 官网临时访问窗口：约 {minutes} 分钟后自动关闭并恢复系统代理。")
    return True


def open_path(path: Path) -> None:
    if platform.system() == "Windows":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_url(url: str) -> None:
    webbrowser.open(url)


def normalize_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lower().lstrip("v")
    parts: list[int] = []
    for item in re.split(r"[^0-9]+", cleaned):
        if item:
            parts.append(int(item))
    return tuple(parts or [0])


def downloads_dir() -> Path:
    path = Path.home() / "Downloads"
    if path.exists():
        return path
    return Path.home() / "下载"


def current_mac_package_suffix() -> str:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "AppleSilicon"
    if machine in {"x86_64", "amd64"}:
        return "Intel"
    return machine or "Unknown"


def release_asset_name_for_current_system() -> str:
    if current_system_id() != "mac":
        return WINDOWS_RELEASE_ASSET_NAME
    return MAC_APPLE_SILICON_RELEASE_ASSET_NAME if current_mac_package_suffix() == "AppleSilicon" else MAC_INTEL_RELEASE_ASSET_NAME


def release_asset_aliases_for_current_system() -> tuple[str, ...]:
    if current_system_id() != "mac":
        return WINDOWS_RELEASE_ASSET_ALIASES
    if current_mac_package_suffix() == "AppleSilicon":
        return MAC_APPLE_SILICON_RELEASE_ASSET_ALIASES
    return MAC_INTEL_RELEASE_ASSET_ALIASES


def public_manifest_asset_url(payload: dict) -> str:
    if current_system_id() == "mac":
        if current_mac_package_suffix() == "AppleSilicon":
            return str(
                payload.get("mac_apple_silicon_zip_url")
                or payload.get("mac_arm64_zip_url")
                or payload.get("mac_zip_url")
                or payload.get("mac_download_url")
                or ""
            )
        return str(payload.get("mac_intel_zip_url") or payload.get("mac_x64_zip_url") or payload.get("mac_x86_64_zip_url") or "")
    return str(payload.get("windows_zip_url") or payload.get("download_url") or "")


def platform_label_for_update() -> str:
    if current_system_id() == "mac":
        return f"Mac {current_mac_package_suffix()}"
    return "Windows"


@dataclass
class UpdateInfo:
    latest_tag: str
    asset_url: str
    release_url: str
    asset_name: str
    platform_label: str


def find_available_update() -> tuple[UpdateInfo | None, str, str | None]:
    try:
        req = Request(PUBLIC_UPDATE_MANIFEST_URL, headers={"Accept": "application/json", "User-Agent": HTTP_USER_AGENT})
        with trusted_urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        payload = {}

    if payload:
        latest_tag = str(payload.get("version") or payload.get("tag_name") or "").strip()
        release_url = str(payload.get("html_url") or payload.get("release_url") or DEFAULT_BASE_URL)
        asset_url = public_manifest_asset_url(payload)
        if not latest_tag:
            return None, "检查更新失败：公开更新清单缺少版本号。", release_url
        if normalize_version(latest_tag) <= normalize_version(APP_VERSION):
            return None, f"当前已是最新版本：{APP_VERSION}", release_url
        if not asset_url:
            return None, f"发现新版本 {latest_tag}，但公开更新清单缺少 {platform_label_for_update()} 下载地址。", release_url
        info = UpdateInfo(latest_tag, asset_url, release_url, release_asset_name_for_current_system(), platform_label_for_update())
        return info, f"发现新版本 {latest_tag}。", release_url

    req = Request(GITHUB_RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": HTTP_USER_AGENT})
    try:
        with trusted_urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return None, f"检查更新失败：{exc}", None

    latest_tag = str(payload.get("tag_name") or "").strip()
    release_url = str(payload.get("html_url") or "https://github.com/dashuaiisme/panghu-codex-installer/releases")
    if not latest_tag:
        return None, "检查更新失败：GitHub Release 没有版本号。", release_url
    if normalize_version(latest_tag) <= normalize_version(APP_VERSION):
        return None, f"当前已是最新版本：{APP_VERSION}", release_url

    asset_url = ""
    for asset in payload.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        if name in release_asset_aliases_for_current_system():
            asset_url = str(asset.get("browser_download_url") or "")
            break
    if not asset_url:
        return None, f"发现新版本 {latest_tag}，但未找到 {platform_label_for_update()} 更新包，已打开发布页。", release_url

    info = UpdateInfo(latest_tag, asset_url, release_url, release_asset_name_for_current_system(), platform_label_for_update())
    return info, f"发现新版本 {latest_tag}。", release_url


def download_update_package(update: UpdateInfo, log) -> Path:
    target_dir = downloads_dir() / "胖虎AI工具更新"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{update.latest_tag}-{update.asset_name}"
    log(f"开始下载 {update.platform_label} 更新包：{update.latest_tag}")
    download_with_trusted_certs(update.asset_url, target)
    return target


def check_and_download_update(log) -> tuple[bool, str, Path | None, str | None]:
    update, msg, release_url = find_available_update()
    if update is None:
        return False, msg, None, release_url
    try:
        target = download_update_package(update, log)
    except Exception as exc:
        return False, f"下载更新失败：{exc}", None, update.release_url
    return True, f"新版本 {update.latest_tag} 已下载。", target, update.release_url


def update_script_path() -> Path:
    root = Path(tempfile.gettempdir()) / "PanghuAI-Agent-Deployer-Updater"
    root.mkdir(parents=True, exist_ok=True)
    return root / ("apply-update.ps1" if platform.system() == "Windows" else "apply-update.sh")


def powershell_single_quoted(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def mac_app_bundle_path() -> Path | None:
    executable = Path(sys.executable).resolve()
    for parent in (executable, *executable.parents):
        if parent.suffix == ".app":
            return parent
    return None


def app_update_root() -> Path:
    if platform.system() == "Darwin":
        bundle = mac_app_bundle_path()
        if bundle:
            return bundle
    return app_root()


def app_launch_target() -> Path:
    if platform.system() == "Darwin":
        bundle = mac_app_bundle_path()
        if bundle:
            return bundle
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def build_windows_update_script(zip_path: Path, app_dir: Path, launch_target: Path, pid: int) -> str:
    return f"""$ErrorActionPreference = "Stop"
$zipPath = {powershell_single_quoted(zip_path)}
$appDir = {powershell_single_quoted(app_dir)}
$launchTarget = {powershell_single_quoted(launch_target)}
$pidToWait = {pid}
$staging = Join-Path $env:TEMP ("PanghuAI-Agent-Deployer-Update-" + [guid]::NewGuid().ToString("N"))
try {{
    Wait-Process -Id $pidToWait -Timeout 30 -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 800
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $staging -Force
    $payload = Get-ChildItem -LiteralPath $staging -Directory | Select-Object -First 1
    if ($null -eq $payload) {{ throw "更新包里没有找到程序目录。" }}
    Copy-Item -Path (Join-Path $payload.FullName "*") -Destination $appDir -Recurse -Force
    Start-Process -FilePath $launchTarget
}} finally {{
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
}}
"""


def build_macos_update_script(zip_path: Path, app_dir: Path, launch_target: Path, pid: int) -> str:
    return f"""#!/bin/zsh
set -euo pipefail
ZIP_PATH={shlex.quote(str(zip_path))}
APP_DIR={shlex.quote(str(app_dir))}
LAUNCH_TARGET={shlex.quote(str(launch_target))}
PID_TO_WAIT={pid}
STAGING="$(mktemp -d "${{TMPDIR:-/tmp}}/panghuai-agent-update.XXXXXX")"
cleanup() {{
  rm -rf "$STAGING"
}}
trap cleanup EXIT
while kill -0 "$PID_TO_WAIT" >/dev/null 2>&1; do
  sleep 0.5
done
ditto -x -k "$ZIP_PATH" "$STAGING"
PAYLOAD="$(find "$STAGING" -maxdepth 1 -name '*.app' -type d | head -n 1)"
if [ -z "$PAYLOAD" ]; then
  echo "更新包里没有找到 app。"
  exit 1
fi
rm -rf "$APP_DIR"
cp -R "$PAYLOAD" "$APP_DIR"
open "$LAUNCH_TARGET"
"""


def start_online_update(zip_path: Path, log) -> None:
    app_dir = app_update_root()
    launch_target = app_launch_target()
    pid = os.getpid()
    script_path = update_script_path()
    if platform.system() == "Windows":
        script = build_windows_update_script(zip_path, app_dir, launch_target, pid)
        write_text(script_path, script)
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)])
    elif platform.system() == "Darwin":
        script = build_macos_update_script(zip_path, app_dir, launch_target, pid)
        write_text(script_path, script)
        script_path.chmod(0o755)
        subprocess.Popen(["/bin/zsh", str(script_path)])
    else:
        raise RuntimeError("当前系统暂不支持自动覆盖更新。")
    log("在线更新程序已启动，本工具即将退出并由更新程序覆盖安装。")


def open_codex_download_page() -> None:
    if platform.system() == "Windows":
        open_url(CODEX_WINDOWS_STORE_URL)
    else:
        open_url(CODEX_DOWNLOAD_URL)


def find_official_codex_package() -> Path | None:
    roots = [app_root(), app_root() / "offline", app_root() / "codex-official"]
    candidates: list[tuple[int, float, Path]] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for child in root.iterdir():
            if child.is_file() and child.suffix.lower() in OFFICIAL_PACKAGE_SUFFIXES:
                name = child.name.lower()
                score = 0
                if "codex" in name:
                    score += 2
                if "openai" in name:
                    score += 1
                candidates.append((score, child.stat().st_mtime, child))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def validate_official_package_signature(package_path: Path) -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "当前系统不支持 Windows Codex 安装包签名校验。"
    safe_path = str(package_path).replace("'", "''")
    command = (
        "$sig = Get-AuthenticodeSignature -LiteralPath "
        f"'{safe_path}'; "
        "[pscustomobject]@{"
        "Status=$sig.Status.ToString();"
        "Subject=if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{''};"
        "Issuer=if($sig.SignerCertificate){$sig.SignerCertificate.Issuer}else{''}"
        "} | ConvertTo-Json -Compress"
    )
    ok, output = run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        timeout=30,
    )
    if not ok:
        return False, f"签名校验失败：{output}"
    try:
        data = json.loads(output.strip())
    except json.JSONDecodeError:
        return False, "签名校验失败：无法解析 Windows 签名信息。"
    status = str(data.get("Status", ""))
    subject = str(data.get("Subject", ""))
    issuer = str(data.get("Issuer", ""))
    if status != "Valid":
        return False, f"签名无效：{status or '未知状态'}"
    signer_text = f"{subject} {issuer}".lower()
    name_text = package_path.name.lower()
    if "openai" not in signer_text and "microsoft" not in signer_text:
        return False, f"签名发布者不是 OpenAI/Microsoft：{subject or issuer or '未知发布者'}"
    if "microsoft" in signer_text and "openai" not in name_text and "codex" not in name_text:
        return False, "Microsoft 签名包文件名未包含 OpenAI/Codex，已拒绝安装。"
    return True, f"签名校验通过：{subject or issuer}"


def install_official_package(package_path: Path) -> tuple[bool, str]:
    signature_ok, signature_msg = validate_official_package_signature(package_path)
    if not signature_ok:
        return False, signature_msg
    suffix = package_path.suffix.lower()
    safe_path = str(package_path).replace("'", "''")
    if suffix == ".appinstaller":
        install_command = f"Add-AppxPackage -AppInstallerFile '{safe_path}'"
    else:
        install_command = f"Add-AppxPackage -Path '{safe_path}'"
    return run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", install_command],
        timeout=600,
    )


def install_with_winget() -> tuple[bool, str]:
    if not shutil.which("winget"):
        return False, "未检测到 winget，无法自动调用 Microsoft Store 命令行安装。"
    return run_command(
        [
            "winget",
            "install",
            "Codex",
            "-s",
            "msstore",
            "--accept-source-agreements",
            "--accept-package-agreements",
        ],
        timeout=900,
    )


def wait_for_codex_ready(timeout_seconds: int = 90, require_windows_app: bool = False) -> tuple[bool, str]:
    deadline = time.time() + timeout_seconds
    last_version = ""
    last_package = ""
    while time.time() < deadline:
        cli_ok, version = codex_command_exists()
        package_ok, package = codex_app_package_exists()
        last_version = version or last_version
        last_package = package or last_package
        if require_windows_app and platform.system() == "Windows":
            if package_ok:
                return True, "已检测到 Codex Windows App 本体：" + (package or "已安装")
        elif cli_ok or package_ok:
            details = [item for item in (version, package) if item]
            return True, "已检测到 Codex：" + ("；".join(details) if details else "已安装")
        time.sleep(3)
    return False, f"等待 Codex 安装完成超时。{last_version or last_package}".strip()


def install_codex_app(log) -> bool:
    log("开始检测 Codex 客户端。")
    cli_ok, version = codex_command_exists()
    package_ok, package = codex_app_package_exists()
    if package_ok:
        if cli_ok:
            log(f"已检测到 Codex CLI：{version or '已安装'}")
        log(f"已检测到 Codex Windows App 本体：{package}")
        create_codex_shortcuts(log)
        log("最近安装：Codex 客户端。可从桌面快捷方式或开始菜单打开。")
        return True
    if cli_ok:
        log(f"已检测到 Codex CLI：{version or '已安装'}")
        if platform.system() != "Windows":
            return True
        log("未检测到 Codex Windows App 本体，将继续安装/修复 App。")

    if platform.system() != "Windows":
        log("当前系统没有可确认的自动客户端安装路径，已打开 Codex 官方入口。")
        open_codex_download_page()
        return False

    package_path = find_official_codex_package()
    if package_path:
        log(f"发现官方离线包：{package_path}")
        signature_ok, signature_msg = validate_official_package_signature(package_path)
        log(signature_msg)
        if signature_ok:
            ok, msg = install_official_package(package_path)
            log(msg)
            if ok:
                ready, ready_msg = wait_for_codex_ready(require_windows_app=True)
                log(ready_msg)
                if ready:
                    create_codex_shortcuts(log)
                    log("最近安装：Codex 客户端。可从桌面快捷方式或开始菜单打开。")
                return ready
        else:
            log("离线包未通过签名校验，将尝试 Microsoft Store 命令行安装。")
    else:
        log("未发现官方离线包，将尝试 Microsoft Store 命令行安装。")

    ok, msg = install_with_winget()
    log(msg)
    if ok:
        ready, ready_msg = wait_for_codex_ready(require_windows_app=True)
        log(ready_msg)
        if ready:
            create_codex_shortcuts(log)
            log("最近安装：Codex 客户端。可从桌面快捷方式或开始菜单打开。")
        return ready

    log("自动安装失败，已打开官方 Codex 下载页，请按页面提示安装。")
    open_codex_download_page()
    return False


def install_codex_cli(log) -> bool:
    exists, version = codex_command_exists()
    if exists:
        log(f"Codex CLI 已安装：{version or '已安装'}")
        return True
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "irm https://chatgpt.com/codex/install.ps1 | iex",
        ]
    else:
        command = ["/bin/bash", "-lc", "curl -fsSL https://chatgpt.com/codex/install.sh | sh"]
    ok, output = run_command(command, timeout=900)
    log(output)
    return ok


def install_claude_code_cli(log) -> bool:
    if not shutil.which("npm"):
        log("未检测到 npm，已打开 ClaudeCode 官方安装文档。")
        open_url(CLAUDE_CODE_DOCS_URL)
        return False
    ok, output = run_command(["npm", "install", "-g", "@anthropic-ai/claude-code"], timeout=900)
    log(output)
    return ok


def install_openclaw_cli(log) -> bool:
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "iwr -useb https://openclaw.ai/install.ps1 | iex",
        ]
    else:
        command = ["/bin/bash", "-lc", "curl -fsSL https://openclaw.ai/install.sh | sh"]
    ok, output = run_command(command, timeout=900)
    log(output)
    return ok


def install_hermes_cli(log) -> bool:
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "iwr -useb https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex",
        ]
    else:
        command = [
            "/bin/bash",
            "-lc",
            "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | sh",
        ]
    ok, output = run_command(command, timeout=900)
    log(output)
    return ok


def codex_thread_url(workdir: Path) -> str:
    return "codex://threads/new?path=" + quote(str(workdir), safe="")


def open_codex_app(workdir: Path) -> tuple[bool, str]:
    package_ok, _ = codex_app_package_exists()
    if package_ok:
        webbrowser.open(codex_thread_url(workdir))
        return True, "已尝试通过 Codex App 官方链接打开工作区。"
    exists, _ = codex_command_exists()
    if not exists:
        return False, "未检测到 Codex App 本体或 codex 命令，请手动打开 Codex App。"
    try:
        subprocess.Popen(["codex", "app"], cwd=str(workdir))
        return True, "已尝试打开 Codex App。"
    except Exception as exc:
        return False, f"自动打开 Codex App 失败：{exc}"


def install_codex_config(
    api_key: str,
    base_url: str,
    model: str,
    skip_test: bool,
    open_app: bool,
    log,
    temporary_openai_access: TemporaryOpenAIAccessConfig | None = None,
    mode: CodexConfigMode = CodexConfigMode.DIRECT_API,
) -> bool:
    if not api_key.strip():
        raise ValueError("请先输入胖虎AI API Key。")
    if not model.strip():
        raise ValueError("模型不能为空。")

    api_key = api_key.strip()
    base_url = DEFAULT_BASE_URL
    model = model.strip()
    home = codex_home()
    workdir = workspace_root()
    config_path = home / "config.toml"
    auth_path = codex_auth_path()
    global_agents = home / "AGENTS.md"
    workspace_agents = workdir / "AGENTS.md"

    mode_label = "双态模式配置" if mode == CodexConfigMode.DUAL_STATE else "普通直接 API 配置"
    log(f"开始应用 Codex 胖虎AI{mode_label}。")
    home.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)

    existed_before = {
        config_path: config_path.exists(),
        auth_path: auth_path.exists(),
        global_agents: global_agents.exists(),
        workspace_agents: workspace_agents.exists(),
    }
    backups = {
        config_path: backup_file(config_path),
        auth_path: backup_file(auth_path),
        global_agents: backup_file(global_agents),
        workspace_agents: backup_file(workspace_agents),
    }
    for target, backup in backups.items():
        if backup:
            log(f"已备份旧文件：{backup}")
        else:
            log(f"将创建新文件：{target}")

    old_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    old_auth = auth_path.read_text(encoding="utf-8") if auth_path.exists() else ""
    if mode == CodexConfigMode.DUAL_STATE:
        new_config = build_dual_state_config(api_key, base_url, model)
        new_auth = build_dual_state_auth_json(old_auth, api_key)
    else:
        new_config = merge_config(old_config, api_key, base_url, model)
        new_auth = build_direct_api_auth_json(old_auth, api_key)
    write_text(config_path, new_config)
    write_text(auth_path, new_auth)
    for agents_path in (global_agents, workspace_agents):
        old_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
        write_text(agents_path, merge_agents_rules(old_agents))
    log(f"已写入 Codex 配置：{config_path}")
    log(f"已写入 Codex 登录授权文件：{auth_path}")
    log(f"接口地址：{CODEX_BASE_URL}")
    log(f"模型：{model}")
    log(f"Key：{mask_key(api_key)}")
    if mode == CodexConfigMode.DUAL_STATE:
        log("配置生效提示：配置写完后，请先完全退出 Codex，再重新打开 Codex；否则 Codex 可能继续使用旧配置。")
        log("双态模式需要用户重新打开后自行登录自己的 ChatGPT 账号；登录态来自用户账号，模型消耗走胖虎AI API Key。")
    else:
        log("普通模式提示：已写入直接 API 配置；配置写完后，请先完全退出 Codex，再重新打开 Codex。")

    ok = True
    if skip_test:
        log("已跳过接口测试。")
    else:
        ok, msg = test_api(base_url, api_key)
        log(msg)
        if not ok:
            for target, backup in backups.items():
                restore_backup(target, backup, existed_before[target])
            log("接口测试失败，已自动恢复本次写入前的配置备份。")

    if open_app:
        start_temporary_openai_access(temporary_openai_access, log)
        _, msg = open_codex_app(workdir)
        log(msg)

    return ok


def build_agent_setup_guide_content(selected: list[tuple[AgentSpec, str]], api_key: str) -> str:
    names = "、".join(f"{agent.name}({mode})" for agent, mode in selected)
    return f"""胖虎AI Agent 配置说明

已选择 Agent：{names}
胖虎AI接口地址：{DEFAULT_BASE_URL}
胖虎AI API Key：{mask_key(api_key)}

说明：
1. Codex 默认由本工具写入普通直接 API 配置。
2. 配置写完后，请先完全退出 Codex，再重新打开 Codex；只有完全退出后重新打开，新的配置才会生效。
3. 普通配置方式无需登录 ChatGPT 账号，也可以正常使用 Codex。
4. 只有点击“双态配置”时，才需要用户重新打开 Codex 后自行登录自己的 ChatGPT 账号。
5. 双态模式下，Codex 会保持用户自己的账号登录态，同时模型调用消耗胖虎AI API Key。本工具不代替登录、不保存 ChatGPT 账号密码。
6. ClaudeCode 只负责官方安装，不写入配置；请按 ClaudeCode 官方流程自行登录或配置。
7. OpenClaw / Hermes 当前版本先安装并提供说明；如果官方客户端要求在界面里粘贴 Key，请使用胖虎AI接口和你刚才在本工具里填写的 API Key。
8. 本工具不会把 API Key 明文写入日志。
"""


def login_help_text() -> str:
    return "\n".join(
        [
            "这里登录的是胖虎AI账号，不是 ChatGPT 账号。",
            "",
            "没有胖虎AI账号时，先点击“去胖虎AI注册账号”完成注册，再回到本工具登录。",
            "",
            "该配置方式无需登录 ChatGPT 账号，也可以正常使用 Codex。普通客户只需要胖虎AI账号和胖虎AI API Key。",
            "",
            "如果客户后续明确需要保留自己的 ChatGPT 登录态，再到第四步使用“双态配置”。",
        ]
    )


def key_creation_help_text() -> str:
    return "\n".join(
        [
            "API Key 是胖虎AI给 Codex 或其他 Agent 使用的调用令牌，不是登录密码。",
            "",
            "推荐流程：",
            "1. 先注册并登录胖虎AI账号。",
            "2. 新账号先充值或确认账户里有余额。",
            "3. 点击“打开 API Key 创建页面”。",
            "4. 在网站里新建 Key，复制完整的 sk- 开头内容。",
            "5. 粘贴到本工具的 API Key 输入框。",
            "6. 点击“保存并测试 Key”。",
            "",
            "常见错误：",
            "- 不要填写手机号、邮箱、登录密码或 ChatGPT 密码。",
            "- 测试不通过时，先检查 Key 是否复制完整、账户是否有余额、接口地址是否保持默认。",
            "- 刚注册但未充值的账号，即使创建了 Key，也可能因为余额不足而测试失败。",
        ]
    )


def environment_help_text() -> str:
    return "\n".join(
        [
            "环境检测会识别当前电脑系统、基础命令和已经安装的 Agent。",
            "",
            "如果检测到 ccswitch、codex++、CCR 等第三方配置工具，本工具会阻止继续安装。",
            "",
            "原因：这些工具可能改写 Codex 或 ClaudeCode 的配置，导致胖虎AI写入的接口、Key、模型被覆盖。",
            "",
            "处理方式：按提示先卸载或禁用风险工具，再重新点击“检测环境”。",
        ]
    )


def agent_choice_help_text() -> str:
    return "\n".join(
        [
            "普通客户建议默认选择 Codex。",
            "",
            "Agent 差异：",
            "- Codex：可由本工具写入胖虎AI API Key、接口、模型和中文规则。",
            "- ClaudeCode：只安装，不写 Key，不改 ClaudeCode 账号或配置。",
            "- OpenClaw / Hermes：优先打开官方入口，当前版本先安装并生成中文配置说明。",
            "",
            "CLI 适合命令行用户；客户端适合希望打开官方桌面入口的用户。",
        ]
    )


def codex_action_help_text() -> str:
    return "\n".join(
        [
            "一键部署（普通）：普通模式。第一次安装 Agent 时使用，会安装所选 Agent，并写入直接 API 配置。",
            "双态配置：需要同时保留 ChatGPT 登录态并消耗胖虎AI API Key 时使用，不安装 Agent。",
            "仅修复 Codex 配置：Agent 已经装好、只是换 Key 或配置损坏时使用，不会重新安装 Agent。",
            "恢复最近备份：配置异常时退回写入前的最近备份。",
            "复制日志：出问题时把日志发给客服排查。",
            "打开工作区：查看本工具生成的配置说明和工作资料。",
            "打开配置目录：查看 Codex 的 config.toml、auth.json 和备份文件。",
            "重要：任何模式配置写完后都必须完全退出 Codex，再重新打开；只有双态模式需要用户重开后自行登录 ChatGPT 账号。",
        ]
    )


def codex_action_summary_text() -> str:
    return "\n".join(
        [
            "普通客户点“一键部署（普通）”。",
            "需要登录态共存时，才点“双态配置”。",
            "只要修改过 Codex 配置，都要完全退出 Codex 后重新打开。",
        ]
    )


def write_agent_setup_guide(selected: list[tuple[AgentSpec, str]], api_key: str, log) -> None:
    guide = workspace_root() / "胖虎AI-Agent配置说明.txt"
    content = build_agent_setup_guide_content(selected, api_key)
    write_text(guide, content)
    log(f"已生成配置说明：{guide}")


def install_agent(agent: AgentSpec, mode_id: str, log) -> bool:
    log(f"开始处理 {agent.name} / {mode_id}。")
    if agent.id == "codex" and mode_id == "cli":
        ok = install_codex_cli(log)
    elif agent.id == "codex" and mode_id == "client":
        ok = install_codex_app(log)
    elif agent.id == "claude_code" and mode_id == "cli":
        ok = install_claude_code_cli(log)
    elif agent.id == "claude_code" and mode_id == "client":
        open_url(CLAUDE_CODE_DOCS_URL)
        log("ClaudeCode 没有在本工具中伪造客户端安装，已打开官方入口。")
        ok = False
    elif agent.id == "openclaw" and mode_id == "cli":
        ok = install_openclaw_cli(log)
    elif agent.id == "openclaw" and mode_id == "client":
        open_url(OPENCLAW_DOCS_URL)
        log("已打开 OpenClaw 官方客户端/Hub 入口。")
        ok = False
    elif agent.id == "hermes" and mode_id == "cli":
        ok = install_hermes_cli(log)
    elif agent.id == "hermes" and mode_id == "client":
        open_url(HERMES_DOCS_URL)
        log("已打开 Hermes 官方安装文档。")
        ok = False
    else:
        log("未知 Agent 或安装方式。")
        return False

    verified, version = version_for(agent.verify_command)
    if verified:
        log(f"{agent.name} 检测通过：{version or '已安装'}")
        return True
    if ok:
        log(f"{agent.name} 安装命令已执行，但当前 PATH 暂未检测到命令，可能需要重开终端或重启软件。")
        return True
    return False


def detect_environment() -> list[str]:
    system = current_system_id()
    lines = [
        f"系统：{platform.system()} {platform.release()}",
        f"架构：{platform.machine()}",
        f"识别结果：{'Windows' if system == 'windows' else 'Mac' if system == 'mac' else '其他系统'}",
    ]
    for command in ("powershell", "winget", "npm", "node"):
        exists, path = command_exists(command)
        lines.append(f"{command}: {'已找到 ' + path if exists else '未找到'}")
    lines.extend(agent_install_status_lines())
    lines.extend(risk_plugin_report_lines(detect_risk_plugins()))
    return lines


class InstallerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(APP_NAME)
        root.geometry("900x800")
        root.minsize(820, 700)
        root.configure(bg=APP_BG)
        self.ui_images: list[tk.PhotoImage] = []
        self.set_window_icon()

        self.cookie_jar = http.cookiejar.CookieJar()
        self.logged_in_user: dict | None = None
        self.deployer_auth: dict | None = None
        self.deployer_manifest: dict | None = None
        self.saved_key_ok = False
        self.saved_key_signature: tuple[str, str, str, bool] | None = None
        self.environment_checked = False
        self.environment_ok = False
        self.worker_running = False
        self.auto_update_checked = False
        self.app_closed = False
        self.after_handles: set[str] = set()
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

        self.login_username = tk.StringVar()
        self.login_password = tk.StringVar()
        self.api_key = tk.StringVar()
        self.base_url = tk.StringVar(value=DEFAULT_BASE_URL)
        self.model = tk.StringVar(value=DEFAULT_MODEL)
        self.show_key = tk.BooleanVar(value=False)
        self.skip_test = tk.BooleanVar(value=False)
        self.open_app = tk.BooleanVar(value=True)
        self.selected_system = tk.StringVar(value=current_system_id())
        self.status = tk.StringVar(value="状态：请先登录胖虎AI账号")
        self.step = tk.IntVar(value=1)
        self.agent_enabled: dict[str, tk.BooleanVar] = {}
        self.agent_mode: dict[str, tk.StringVar] = {}
        for variable in (self.api_key, self.model, self.skip_test):
            variable.trace_add("write", self.mark_key_dirty)
        self.selected_system.trace_add("write", self.mark_environment_dirty)

        self.load_profile_into_ui()
        self._build_ui()
        self.apply_restored_login_state()
        self.log("系统提示：请先登录胖虎AI账号。登录后再填写 Key、检测环境并安装 Agent。", replace=True)

    def set_window_icon(self) -> None:
        ico = asset_path("panghu-avatar.ico")
        png = asset_path("panghu-avatar-64.png")
        try:
            if ico.exists() and platform.system() == "Windows":
                self.root.iconbitmap(str(ico))
            if png.exists():
                self.window_icon = tk.PhotoImage(file=str(png))
                self.root.iconphoto(True, self.window_icon)
        except Exception:
            self.window_icon = None

    def load_ui_image(self, name: str) -> tk.PhotoImage | None:
        path = asset_path(name)
        if not path.exists():
            return None
        try:
            image = tk.PhotoImage(file=str(path))
            self.ui_images.append(image)
            return image
        except Exception:
            return None

    def load_profile_into_ui(self) -> None:
        profile = load_saved_profile()
        if not profile:
            return
        self.login_username.set(str(profile.get("username") or ""))
        self.api_key.set(str(profile.get("api_key") or ""))
        self.base_url.set(DEFAULT_BASE_URL)
        self.model.set(str(profile.get("model") or DEFAULT_MODEL))
        self.skip_test.set(bool(profile.get("skip_test")))
        self.open_app.set(bool(profile.get("open_app", True)))
        user = profile.get("user")
        deployer_auth = profile.get("deployer_auth")
        if isinstance(user, dict) and isinstance(deployer_auth, dict) and deployer_auth.get("token"):
            self.logged_in_user = user
            self.deployer_auth = deployer_auth

    def apply_restored_login_state(self) -> None:
        if not self.logged_in_user or not self.deployer_auth:
            return
        username = str(self.logged_in_user.get("username") or self.login_username.get() or "")
        display_username = username if len(username) <= 20 else f"{username[:17]}..."
        self.user_label.configure(text=f"已登录：{display_username}")
        self.show_wizard()
        self.status.set("状态：已恢复上次登录，可继续使用")
        self.run_later(1200, self.start_auto_update_check)

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
        style.configure("TEntry", fieldbackground="#fffaf3", bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        style.configure("TCombobox", fieldbackground="#fffaf3", bordercolor=BORDER)
        style.configure("TCheckbutton", background=CARD_BG, foreground=INK)
        style.configure("TRadiobutton", background=CARD_BG, foreground=INK)

        self.container = tk.Frame(self.root, bg=APP_BG, padx=8, pady=12)
        self.container.pack(fill="both", expand=True)

        self.header = tk.Frame(self.container, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER)
        self.header.pack(fill="x")
        top_row = tk.Frame(self.header, bg=CARD_BG, height=78)
        top_row.pack(fill="x")
        top_row.pack_propagate(False)
        top_row.grid_columnconfigure(0, weight=1)
        brand_area = tk.Frame(top_row, bg=CARD_BG)
        brand_area.grid(row=0, column=0, sticky="nsew", padx=(20, 18), pady=10)
        avatar = self.load_ui_image("panghu-avatar-64.png")
        if avatar:
            tk.Label(brand_area, image=avatar, bg=CARD_BG).pack(side="left", anchor="center", padx=(0, 14))
        brand_text = tk.Frame(brand_area, bg=CARD_BG)
        brand_text.pack(side="left", anchor="center")
        tk.Label(
            brand_text,
            text="胖虎AI",
            font=("Microsoft YaHei UI", 10, "bold"),
            fg=PRIMARY,
            bg=CARD_BG,
        ).pack(anchor="w")
        tk.Label(
            brand_text,
            text="多 Agent 一键部署工具",
            font=("Microsoft YaHei UI", 17, "bold"),
            fg=INK,
            bg=CARD_BG,
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            brand_text,
            text="登录胖虎AI账号后，按流程完成 Agent 安装与本机配置。",
            font=("Microsoft YaHei UI", 9),
            fg=MUTED,
            bg=CARD_BG,
        ).pack(anchor="w", pady=(5, 0))

        self.user_label = tk.Label(
            brand_area,
            text="未登录",
            bg=GOLD_SOFT,
            fg="#8a5b00",
            padx=12,
            pady=6,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.user_label.pack(side="left", anchor="center", padx=(18, 0))

        support_bar = tk.Frame(self.header, bg=INFO_BG, height=32)
        support_bar.pack(fill="x")
        support_bar.pack_propagate(False)
        tk.Frame(support_bar, bg=BORDER, height=1).pack(fill="x")
        tk.Label(
            support_bar,
            text="客服微信：panghuwanAI  ·  Plus / Pro 代充  ·  国外手机验证",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="left", padx=22, pady=(7, 0))

        self.body = tk.Frame(self.container, bg=APP_BG)
        self.body.pack(fill="both", expand=True, pady=(12, 0))

        self.login_frame = tk.Frame(self.body, bg=APP_BG, relief="flat", highlightthickness=0)
        self.login_frame.pack(fill="both", expand=True, ipady=0)
        self._build_login_frame(self.login_frame)

        self.wizard_frame = tk.Frame(self.body, bg=APP_BG)
        self._build_wizard_frame(self.wizard_frame)

        self.log_box = tk.Text(
            self.container,
            height=1,
            bg=CARD_BG,
            fg=MUTED,
            insertbackground=MUTED,
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=4,
            wrap="word",
            font=("Microsoft YaHei UI", 9),
        )
        self.log_box.pack(fill="x", expand=False, pady=(8, 0))
        self.log_box.configure(state="disabled")

        footer = tk.Frame(self.container, bg=APP_BG)
        footer.pack(fill="x", pady=(6, 0))
        tk.Label(footer, textvariable=self.status, bg=APP_BG, fg=MUTED).pack(side="left", anchor="w")
        self.update_button = self._text_button(footer, "检查更新", self.start_update_check)
        self.update_button.pack(side="right")

    def _button(self, parent: tk.Widget, text: str, command, kind: str = "secondary") -> tk.Button:
        if kind == "primary":
            bg, fg, active = PRIMARY, "#ffffff", PRIMARY_DARK
        elif kind == "success":
            bg, fg, active = ACCENT, "#ffffff", "#08745b"
        else:
            bg, fg, active = LOCKED_BG, INK, "#e0d5c8"
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
        )

    def _show_help(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def _grid_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        kind: str,
        row: int,
        column: int,
        columnspan: int = 1,
    ) -> tk.Button:
        button = self._button(parent, text, command, kind)
        button.grid(row=row, column=column, columnspan=columnspan, sticky="ew", padx=(0, 8), pady=(0, 10))
        return button

    def _text_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=CARD_BG,
            fg=PRIMARY,
            activebackground=INFO_BG,
            activeforeground=PRIMARY_DARK,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "bold"),
        )

    def _notice_strip(
        self,
        parent: tk.Widget,
        title: str,
        body: str,
        tone: str = "info",
        button_text: str | None = None,
        command=None,
        compact: bool = False,
    ) -> tk.Frame:
        palette = {
            "info": (INFO_BG, PRIMARY_DARK, MUTED, BORDER),
            "success": (SUCCESS_BG, "#1f6b55", "#34594d", "#c6e8d3"),
            "warning": (WARNING_BG, "#9a4b18", "#71411c", "#f1c995"),
        }
        bg, title_fg, body_fg, border = palette.get(tone, palette["info"])
        box = tk.Frame(parent, bg=bg, padx=10 if compact else 12, pady=6 if compact else 9, highlightthickness=1, highlightbackground=border)
        box.pack(fill="x")
        header = tk.Frame(box, bg=bg)
        header.pack(fill="x")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text=title,
            bg=bg,
            fg=title_fg,
            font=("Microsoft YaHei UI", 9 if compact else 10, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text=body,
            bg=bg,
            fg=body_fg,
            wraplength=420 if compact else 520,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9 if compact else 10),
        ).grid(row=1 if compact else 0, column=0 if compact else 1, sticky="ew", padx=(0 if compact else 10, 8), pady=(2 if compact else 0, 0))
        if button_text and command:
            tk.Button(
                header,
                text=button_text,
                command=command,
                bg=bg,
                fg=PRIMARY,
                activebackground=bg,
                activeforeground=PRIMARY_DARK,
                relief="flat",
                bd=0,
                padx=6 if compact else 8,
                pady=0,
                cursor="hand2",
                font=("Microsoft YaHei UI", 9, "bold"),
            ).grid(row=0, column=1 if compact else 2, sticky="ne")
        return box

    def _sync_wraplength(self, label: tk.Label, padding: int = 60, max_width: int = 360) -> None:
        def update(event) -> None:
            label.configure(wraplength=min(max_width, max(260, event.width - padding)))

        label.master.bind("<Configure>", update, add="+")

    def _build_login_frame(self, parent: tk.Frame) -> None:
        parent.configure(padx=0, pady=0)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        login_card = tk.Frame(parent, bg=CARD_BG, padx=24, pady=26, highlightthickness=1, highlightbackground=BORDER)
        login_card.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            login_card,
            text="登录胖虎AI账号",
            font=("Microsoft YaHei UI", 19, "bold"),
            bg=CARD_BG,
            fg=INK,
        ).pack(anchor="w")
        tk.Label(
            login_card,
            text="使用胖虎AI账号登录工具，登录后再创建 Key 并配置本机 Agent。",
            bg=CARD_BG,
            fg=MUTED,
        ).pack(anchor="w", pady=(8, 12))
        self._notice_strip(
            login_card,
            "账号说明",
            "无需 ChatGPT 账号；注册胖虎AI账号即可登录工具并配置 Codex。",
            "info",
            "查看说明",
            lambda: self._show_help("账号说明", login_help_text()),
            compact=True,
        ).pack_configure(pady=(0, 16))

        fields = tk.Frame(login_card, bg=CARD_BG)
        fields.pack(fill="x")
        account = tk.Frame(fields, bg=CARD_BG)
        account.pack(fill="x")
        tk.Label(account, text="用户名或邮箱", bg=CARD_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        ttk.Entry(account, textvariable=self.login_username, font=("Microsoft YaHei UI", 11)).pack(fill="x", ipady=7, pady=(6, 0))

        password = tk.Frame(fields, bg=CARD_BG)
        password.pack(fill="x", pady=(12, 0))
        tk.Label(password, text="密码", bg=CARD_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        ttk.Entry(password, textvariable=self.login_password, show="*", font=("Microsoft YaHei UI", 11)).pack(fill="x", ipady=7, pady=(6, 0))

        buttons = tk.Frame(login_card, bg=CARD_BG)
        buttons.pack(fill="x", pady=(20, 0))
        self.login_button = self._button(buttons, "登录并激活工具", self.start_login, "primary")
        self.login_button.pack(side="left")
        self._button(buttons, "去胖虎AI注册账号", lambda: open_url(REGISTER_URL)).pack(side="left", padx=(12, 0))

        flow_strip = tk.Frame(login_card, bg=INFO_BG, padx=10, pady=8, highlightthickness=1, highlightbackground=BORDER)
        flow_strip.pack(fill="x", pady=(20, 0))
        tk.Label(
            flow_strip,
            text="使用流程",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            flow_strip,
            text="登录胖虎AI账号 -> 创建 Key -> 检测系统 -> 选择 Agent -> 一键部署",
            bg=INFO_BG,
            fg=MUTED,
            wraplength=760,
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left", padx=(12, 0))

        tk.Frame(login_card, bg=BORDER, height=1).pack(fill="x", pady=(22, 14))
        tk.Label(
            login_card,
            text="支持系统：Windows / Mac",
            bg=CARD_BG,
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            login_card,
            text="支持 Agent：Codex、ClaudeCode、OpenClaw、Hermes。安装来源全部使用官方在线入口。",
            bg=CARD_BG,
            fg=MUTED,
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))
        tk.Label(
            login_card,
            text="安全说明：密码只用于登录验证；API Key 只写入本机 Agent 配置，日志会自动隐藏明文 Key。",
            bg=CARD_BG,
            fg=MUTED,
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

    def _build_wizard_frame(self, parent: tk.Frame) -> None:
        shell = tk.Frame(parent, bg=APP_BG)
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(shell, bg=CARD_BG, width=180, padx=9, pady=14, highlightthickness=1, highlightbackground=BORDER)
        sidebar.pack(side="left", fill="y", padx=(0, 8))
        sidebar.pack_propagate(False)
        tk.Label(
            sidebar,
            text="部署流程",
            bg=CARD_BG,
            fg=INK,
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            sidebar,
            text="按顺序完成，每一步通过后才开放下一步。",
            bg=CARD_BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            wraplength=150,
            justify="left",
        ).pack(anchor="w", pady=(4, 12))

        self.step_buttons: dict[int, tk.Button] = {}
        for idx, title, subtitle in (
            (1, "创建 Key", "验证胖虎AI接口"),
            (2, "检测系统", "确认电脑环境"),
            (3, "选择 Agent", "选择 CLI 或客户端"),
            (4, "安装配置", "执行安装和应用"),
        ):
            btn = self._step_button(sidebar, idx, title, subtitle)
            btn.pack(fill="x", pady=(0, 8))
            self.step_buttons[idx] = btn
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", pady=(4, 12))
        self.flow_status_label = tk.Label(
            sidebar,
            text="当前状态：请先保存并测试 Key。",
            bg=CARD_BG,
            fg=MUTED,
            wraplength=150,
            justify="left",
            anchor="nw",
            font=("Microsoft YaHei UI", 9),
        )
        self.flow_status_label.pack(fill="x", anchor="w")

        panel = tk.Frame(shell, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER)
        panel.pack(side="left", fill="both", expand=True)
        self.steps_host = tk.Frame(panel, bg=CARD_BG, padx=12, pady=18)
        self.steps_host.pack(fill="both", expand=True)
        self.step_frames: dict[int, tk.Frame] = {}
        self.step_canvases: dict[int, tk.Canvas] = {}
        self.step_hint_labels: dict[int, tk.Label] = {}
        self.step_next_buttons: dict[int, tk.Button] = {}
        self._build_step_1()
        self._build_step_2()
        self._build_step_3()
        self._build_step_4()

        for canvas in self.step_canvases.values():
            canvas.place(in_=self.steps_host, x=0, y=0, relwidth=1, relheight=1)
        self.refresh_steps()

    def _create_step_frame(self, idx: int) -> tk.Frame:
        viewport = tk.Frame(self.steps_host, bg=CARD_BG)
        canvas = tk.Canvas(viewport, bg=CARD_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CARD_BG)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def sync_scroll_region(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_content_width(event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_content_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.step_canvases[idx] = viewport
        self.step_frames[idx] = content
        return content

    def _step_button(self, parent: tk.Frame, idx: int, title: str, subtitle: str) -> tk.Button:
        def activate() -> None:
            self.go_to_step(idx)

        return tk.Button(
            parent,
            text=f"{idx}. {title}\n未开始 · {subtitle}",
            command=activate,
            anchor="w",
            justify="left",
            bg=PANEL_BG,
            fg=INK,
            activebackground="#e7f3f0",
            activeforeground=INK,
            relief="flat",
            bd=0,
            padx=9,
            pady=8,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "bold"),
        )

    def _step_title(
        self,
        parent: tk.Frame,
        title: str,
        desc: str,
        help_title: str | None = None,
        help_text: str | None = None,
    ) -> None:
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x")
        tk.Label(row, text=title, font=("Microsoft YaHei UI", 17, "bold"), bg=CARD_BG, fg=INK).pack(side="left", anchor="w")
        if help_title and help_text:
            self._text_button(row, "查看详细说明", lambda: self._show_help(help_title, help_text)).pack(side="right")
        desc_label = tk.Label(parent, text=desc, bg=CARD_BG, fg=MUTED, wraplength=520, justify="left")
        desc_label.pack(anchor="w", fill="x", pady=(7, 14))
        self._sync_wraplength(desc_label, 20, 360)

    def _step_hint(self, parent: tk.Frame, idx: int) -> None:
        label = tk.Label(
            parent,
            text="",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            padx=10,
            pady=7,
            wraplength=500,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        label.pack(fill="x", pady=(0, 12))
        self._sync_wraplength(label, 28, 360)
        self.step_hint_labels[idx] = label

    def _field_label(self, parent: tk.Frame, text: str, bg: str = CARD_BG) -> None:
        tk.Label(parent, text=text, bg=bg, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")

    def _build_step_1(self) -> None:
        frame = self._create_step_frame(1)
        self._step_title(
            frame,
            "第一步：创建并保存胖虎AI API Key",
            "API Key 是胖虎AI给 Agent 使用的调用令牌，不是登录密码。",
            "API Key 创建说明",
            key_creation_help_text(),
        )
        self._step_hint(frame, 1)

        guide = self._notice_strip(
            frame,
            "创建前确认",
            "新注册账号需要先充值或确保账户有余额；余额不足时，Key 即使创建成功也可能测试失败。",
            "warning",
            "创建 Key 详细步骤",
            lambda: self._show_help("API Key 创建说明", key_creation_help_text()),
            compact=True,
        )
        open_row = tk.Frame(guide, bg=WARNING_BG)
        open_row.pack(fill="x", pady=(10, 0))
        self._button(open_row, "打开 API Key 创建页面", lambda: open_url(KEY_CREATE_URL), "secondary").pack(side="left")

        key_row = tk.Frame(frame, bg=CARD_BG)
        key_row.pack(fill="x", pady=(18, 0))
        self._field_label(key_row, "胖虎AI API Key")
        entry_row = tk.Frame(key_row, bg=CARD_BG)
        entry_row.pack(fill="x", pady=(6, 0))
        self.key_entry = ttk.Entry(entry_row, textvariable=self.api_key, show="*", font=("Microsoft YaHei UI", 11))
        self.key_entry.pack(side="left", fill="x", expand=True, ipady=7)
        ttk.Checkbutton(entry_row, text="显示", variable=self.show_key, command=self.toggle_key).pack(
            side="left", padx=(10, 0)
        )

        form = tk.Frame(frame, bg=CARD_BG)
        form.pack(fill="x", pady=(14, 0))
        base_frame = tk.Frame(form, bg=CARD_BG)
        base_frame.pack(fill="x")
        self._field_label(base_frame, "接口地址")
        self.base_url_entry = ttk.Entry(
            base_frame,
            textvariable=self.base_url,
            font=("Microsoft YaHei UI", 11),
            state="readonly",
        )
        self.base_url_entry.pack(fill="x", ipady=7, pady=(6, 0))
        model_frame = tk.Frame(form, bg=CARD_BG)
        model_frame.pack(fill="x", pady=(12, 0))
        self._field_label(model_frame, "默认模型")
        ttk.Combobox(model_frame, textvariable=self.model, values=["gpt-5.5", "gpt-5.4", "gpt-4.1"]).pack(
            fill="x", ipady=5, pady=(6, 0)
        )

        options = tk.Frame(frame, bg=CARD_BG)
        options.pack(fill="x", pady=(18, 0))
        ttk.Checkbutton(options, text="跳过接口测试", variable=self.skip_test).pack(side="left")
        self._button(options, "保存并测试 Key", self.start_save_key, "primary").pack(side="left", padx=(16, 0))
        self.step_next_buttons[1] = self._button(options, "下一步：检测系统", lambda: self.go_to_step(2), "secondary")
        self.step_next_buttons[1].pack(side="right")

    def _build_step_2(self) -> None:
        frame = self._create_step_frame(2)
        self._step_title(
            frame,
            "第二步：选择系统并检测环境",
            "自动识别当前电脑系统，并检查是否存在会改写配置的风险工具。",
            "环境检测说明",
            environment_help_text(),
        )
        self._step_hint(frame, 2)
        self._notice_strip(
            frame,
            "检测说明",
            "如果提示存在 ccswitch、codex++、CCR 等工具，请先按提示处理，再继续安装配置。",
            "info",
            compact=True,
        ).pack_configure(pady=(0, 12))
        choices = tk.Frame(frame, bg=PANEL_BG, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
        choices.pack(fill="x")
        ttk.Radiobutton(choices, text="自动识别", value=current_system_id(), variable=self.selected_system).pack(
            side="left", padx=(0, 16)
        )
        ttk.Radiobutton(choices, text="Windows", value="windows", variable=self.selected_system).pack(
            side="left", padx=(0, 16)
        )
        ttk.Radiobutton(choices, text="Mac", value="mac", variable=self.selected_system).pack(side="left")
        self._button(choices, "检测环境", self.run_environment_check, "primary").pack(side="right")
        self.env_text = tk.Text(
            frame,
            height=15,
            bg="#2d241d",
            fg="#f7eadb",
            insertbackground="#f7eadb",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            wrap="word",
            font=("Cascadia Mono", 9),
        )
        self.env_text.pack(fill="both", expand=True, pady=(14, 0))
        self.env_text.configure(state="disabled")
        nav = tk.Frame(frame, bg=CARD_BG)
        nav.pack(fill="x", pady=(12, 0))
        self.step_next_buttons[2] = self._button(nav, "下一步：选择 Agent", lambda: self.go_to_step(3), "secondary")
        self.step_next_buttons[2].pack(side="right")

    def _agent_card_copy(self, agent: AgentSpec) -> tuple[str, str]:
        copies = {
            "codex": ("官方 Codex Agent，可应用胖虎AI配置。", "可写入 Key、接口、模型和中文规则。"),
            "claude_code": ("Claude Code，只安装不写配置。", "不写 Key，不改账号或 ClaudeCode 配置。"),
            "openclaw": ("OpenClaw，官方入口安装。", "安全路径未确认时，仅生成中文配置指引。"),
            "hermes": ("Hermes，官方入口安装。", "安全路径未确认时，仅生成中文配置指引。"),
        }
        return copies.get(agent.id, (agent.description, agent.config_note))

    def _build_step_3(self) -> None:
        frame = self._create_step_frame(3)
        self._step_title(
            frame,
            "第三步：选择 Agent 和安装方式",
            "普通客户建议默认选择 Codex；其他 Agent 按官方入口安装或生成说明。",
            "Agent 选择说明",
            agent_choice_help_text(),
        )
        self._step_hint(frame, 3)
        self._notice_strip(
            frame,
            "配置范围",
            "Codex 可自动写入胖虎AI配置；ClaudeCode 只安装不写 Key；OpenClaw 和 Hermes 当前先安装并提供中文说明。",
            "info",
            compact=True,
        ).pack_configure(pady=(0, 12))

        list_frame = tk.Frame(frame, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)
        list_frame.grid_columnconfigure(0, weight=1)
        for index, agent in enumerate(AGENTS):
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=14, pady=10, highlightthickness=1, highlightbackground=BORDER)
            row.grid(row=index, column=0, sticky="ew", pady=(0, 8))
            row.grid_columnconfigure(0, minsize=140)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, minsize=160)
            enabled = tk.BooleanVar(value=agent.id == "codex")
            mode = tk.StringVar(value="cli")
            enabled.trace_add("write", self.mark_agent_selection_changed)
            mode.trace_add("write", self.mark_agent_selection_changed)
            self.agent_enabled[agent.id] = enabled
            self.agent_mode[agent.id] = mode
            card_description, _card_note = self._agent_card_copy(agent)
            header = tk.Frame(row, bg=PANEL_BG)
            header.grid(row=0, column=0, sticky="nw", padx=(0, 12))
            tk.Checkbutton(
                header,
                text=f"选择 {agent.name}",
                variable=enabled,
                indicatoron=False,
                bg=LOCKED_BG,
                fg=INK,
                activebackground="#e4d8ca",
                activeforeground=INK,
                selectcolor=SUCCESS_BG,
                relief="flat",
                bd=0,
                padx=10,
                pady=4,
                cursor="hand2",
                font=("Microsoft YaHei UI", 9, "bold"),
            ).pack(anchor="w")
            tk.Label(
                header,
                text="可配置" if agent.id == "codex" else "仅安装" if agent.id == "claude_code" else "先安装",
                bg=GOLD_SOFT if agent.id == "codex" else LOCKED_BG,
                fg="#8a5b00" if agent.id == "codex" else MUTED,
                padx=9,
                pady=4,
                font=("Microsoft YaHei UI", 9, "bold"),
            ).pack(anchor="w", pady=(4, 0))
            text_area = tk.Frame(row, bg=PANEL_BG)
            text_area.grid(row=0, column=1, sticky="ew", padx=(0, 12))
            tk.Label(
                text_area,
                text=card_description,
                bg=PANEL_BG,
                fg=INK,
                font=("Microsoft YaHei UI", 9, "bold"),
                wraplength=280,
                justify="left",
            ).pack(anchor="w")
            mode_area = tk.Frame(row, bg=PANEL_BG)
            mode_area.grid(row=0, column=2, sticky="e")
            tk.Label(mode_area, text="安装方式", bg=PANEL_BG, fg=MUTED, font=("Microsoft YaHei UI", 9, "bold")).pack(
                side="left", padx=(0, 8)
            )
            for item in agent.modes:
                tk.Radiobutton(
                    mode_area,
                    text=item.label,
                    value=item.id,
                    variable=mode,
                    indicatoron=False,
                    bg=CARD_BG,
                    fg=INK,
                    activebackground=LOCKED_BG,
                    activeforeground=INK,
                    selectcolor=SUCCESS_BG,
                    relief="flat",
                    bd=0,
                    padx=9,
                    pady=4,
                    cursor="hand2",
                    font=("Microsoft YaHei UI", 9, "bold"),
                ).pack(side="left", padx=(0, 6))
        nav = tk.Frame(frame, bg=CARD_BG)
        nav.pack(fill="x", pady=(8, 0))
        self.step_next_buttons[3] = self._button(nav, "下一步：安装配置", lambda: self.go_to_step(4), "secondary")
        self.step_next_buttons[3].pack(side="right")

    def _build_step_4(self) -> None:
        frame = self._create_step_frame(4)
        self._step_title(
            frame,
            "第四步：一键安装并应用配置",
            "普通客户点一键部署（普通）；只有需要 ChatGPT 登录态共存时，才使用双态模式。",
            "按钮功能说明",
            codex_action_help_text(),
        )
        self._step_hint(frame, 4)
        confirm_row = tk.Frame(frame, bg=CARD_BG)
        confirm_row.pack(fill="x")
        confirm_row.grid_columnconfigure(0, weight=1, uniform="confirm")
        confirm_row.grid_columnconfigure(1, weight=1, uniform="confirm")
        summary = tk.Frame(confirm_row, bg=PANEL_BG, padx=10, pady=7, highlightthickness=1, highlightbackground=BORDER)
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(summary, text="执行前确认", bg=PANEL_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        summary_body = tk.Label(
            summary,
            text="保存有效 Key 后才会写配置；开始前会再查第三方配置工具。",
            bg=PANEL_BG,
            fg=MUTED,
            wraplength=240,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        summary_body.pack(fill="x", pady=(3, 0))
        restart = tk.Frame(confirm_row, bg=WARNING_BG, padx=10, pady=7, highlightthickness=1, highlightbackground="#f1c995")
        restart.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(restart, text="重启生效", bg=WARNING_BG, fg="#9a4b18", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        restart_body = tk.Label(
            restart,
            text="只要改了 Codex 配置，都必须完全退出 Codex 后重新打开。",
            bg=WARNING_BG,
            fg="#71411c",
            wraplength=240,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        restart_body.pack(fill="x", pady=(3, 0))
        ttk.Checkbutton(frame, text="完成后打开 Codex App，并临时打开 OpenAI 官网访问窗口", variable=self.open_app).pack(
            anchor="w", pady=(8, 0)
        )

        actions = tk.Frame(frame, bg=CARD_BG)
        actions.pack(fill="x", pady=(10, 0))
        for col in range(2):
            actions.grid_columnconfigure(col, weight=1, uniform="actions")
        self.deploy_button = self._grid_button(actions, "一键部署（普通）", self.start_deploy, "success", 0, 0)
        self.dual_state_button = self._grid_button(actions, "双态配置", self.start_dual_state_config, "primary", 0, 1)
        self.config_button = self._grid_button(actions, "仅修复 Codex 配置", self.start_config_only, "primary", 1, 0, 2)
        aux_actions = tk.Frame(frame, bg=CARD_BG)
        aux_actions.pack(fill="x", pady=(0, 0))
        for col in range(2):
            aux_actions.grid_columnconfigure(col, weight=1, uniform="actions2")
        self.restore_button = self._grid_button(aux_actions, "恢复最近备份", self.restore_backups, "secondary", 0, 0)
        self._grid_button(aux_actions, "复制日志", self.copy_logs, "secondary", 0, 1)
        self._grid_button(aux_actions, "打开工作区", self.open_workspace, "secondary", 1, 0)
        self._grid_button(aux_actions, "打开配置目录", self.open_config_dir, "secondary", 1, 1)

        help_box = tk.Frame(frame, bg=INFO_BG, padx=10, pady=7, highlightthickness=1, highlightbackground=BORDER)
        help_box.pack(fill="x", pady=(10, 0))
        help_box.grid_columnconfigure(0, weight=1)
        tk.Label(
            help_box,
            text="按钮功能",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w")
        help_body = tk.Label(
            help_box,
            text="普通客户点“一键部署（普通）”；需要登录态共存才点“双态配置”。",
            bg=INFO_BG,
            fg=MUTED,
            wraplength=420,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        help_body.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        self._sync_wraplength(help_body, 130, 330)
        self._text_button(help_box, "查看全部按钮说明", lambda: self._show_help("按钮功能说明", codex_action_help_text())).grid(
            row=0, column=1, rowspan=2, sticky="ne", padx=(12, 0)
        )

    def has_valid_key(self) -> bool:
        return self.saved_key_ok and self.saved_key_signature == self.current_key_signature()

    def agents_ready(self) -> bool:
        return bool(self.selected_agents())

    def first_missing_step(self) -> tuple[int, str] | None:
        if not self.has_valid_key():
            return 1, "第一步还没完成：请填写胖虎AI API Key，并点击“保存并测试 Key”。"
        if not self.environment_ok:
            return 2, "第二步还没完成：请点击“检测环境”，并处理所有风险提示。"
        if not self.agents_ready():
            return 3, "第三步还没完成：请至少选择一个 Agent。"
        return None

    def can_access_step(self, idx: int) -> bool:
        if idx <= 1:
            return True
        if idx == 2:
            return self.has_valid_key()
        if idx == 3:
            return self.has_valid_key() and self.environment_ok
        if idx == 4:
            return self.first_missing_step() is None
        return False

    def go_to_step(self, idx: int) -> None:
        if self.can_access_step(idx):
            self.step.set(idx)
            self.refresh_steps()
            return
        missing = self.first_missing_step()
        if missing:
            target_step, message = missing
            self.step.set(target_step)
            self.refresh_steps()
            messagebox.showwarning("暂时不能进入下一步", message)

    def step_button_copy(self, idx: int) -> tuple[str, str, str]:
        copies = {
            1: ("创建 Key", "验证胖虎AI接口"),
            2: ("检测系统", "确认电脑环境"),
            3: ("选择 Agent", "选择 CLI 或客户端"),
            4: ("安装配置", "执行安装和应用"),
        }
        title, subtitle = copies[idx]
        if idx == 1:
            status = "已完成" if self.has_valid_key() else "待完成"
        elif idx == 2:
            status = "已完成" if self.environment_ok else "可继续" if self.can_access_step(2) else "未解锁"
        elif idx == 3:
            status = "已完成" if self.agents_ready() and self.can_access_step(3) else "可继续" if self.can_access_step(3) else "未解锁"
        else:
            status = "可执行" if self.can_access_step(4) else "未解锁"
        return title, subtitle, status

    def current_flow_message(self) -> str:
        missing = self.first_missing_step()
        if not missing:
            return "当前状态：前 3 步已完成，可以执行安装或配置。"
        return f"当前状态：{missing[1]}"

    def update_step_hints(self) -> None:
        hint_data = {
            1: (
                "已完成：Key 已保存并通过当前配置校验，可以进入第二步。"
                if self.has_valid_key()
                else "待完成：请创建或填写胖虎AI API Key，并点击“保存并测试 Key”。新账号请先充值，余额不足会导致测试失败。"
            ),
            2: (
                "已完成：环境检测通过，可以进入第三步。"
                if self.environment_ok
                else "待完成：第一步完成后点击“检测环境”。如果发现 ccswitch、codex++、CCR，请先处理后再继续。"
            ),
            3: (
                f"已完成：已选择 {len(self.selected_agents())} 个 Agent，可以进入第四步。"
                if self.agents_ready()
                else "待完成：至少选择一个 Agent。普通客户建议保留 Codex。"
            ),
            4: (
                "可执行：前 3 步已完成。普通客户点“一键部署（普通）”；需要登录态共存才点“双态配置”。"
                if self.can_access_step(4)
                else "未解锁：请先完成 Key 保存、环境检测和 Agent 选择。"
            ),
        }
        for idx, label in getattr(self, "step_hint_labels", {}).items():
            ready = idx == 1 and self.has_valid_key() or idx == 2 and self.environment_ok or idx == 3 and self.agents_ready() or idx == 4 and self.can_access_step(4)
            label.configure(
                text=hint_data[idx],
                bg=SUCCESS_BG if ready else INFO_BG,
                fg="#1f6b55" if ready else PRIMARY_DARK,
            )

    def refresh_steps(self) -> None:
        for idx, frame in self.step_canvases.items():
            if idx == self.step.get():
                frame.lift()
                canvas = frame.winfo_children()[0] if frame.winfo_children() else None
                if isinstance(canvas, tk.Canvas):
                    canvas.yview_moveto(0)
        for idx, button in getattr(self, "step_buttons", {}).items():
            active = idx == self.step.get()
            title, subtitle, status = self.step_button_copy(idx)
            locked = not self.can_access_step(idx)
            button.configure(
                text=f"{idx}. {title}\n{status} · {subtitle}",
                bg=PRIMARY if active else LOCKED_BG if locked else PANEL_BG,
                fg="#ffffff" if active else MUTED if locked else INK,
                activebackground=PRIMARY,
                activeforeground="#ffffff",
                state="normal" if not self.worker_running else "disabled",
            )
        if hasattr(self, "flow_status_label"):
            self.flow_status_label.configure(text=self.current_flow_message())
        self.update_step_hints()
        for idx, button in getattr(self, "step_next_buttons", {}).items():
            button.configure(state="normal" if self.can_access_step(idx + 1) and not self.worker_running else "disabled")
        ready_for_step_4 = self.can_access_step(4) and not self.worker_running
        for button in (getattr(self, "deploy_button", None), getattr(self, "dual_state_button", None), getattr(self, "config_button", None)):
            if button:
                button.configure(state="normal" if ready_for_step_4 else "disabled")
        for button in (getattr(self, "restore_button", None), getattr(self, "update_button", None), getattr(self, "login_button", None)):
            if button:
                button.configure(state="disabled" if self.worker_running else "normal")

    def toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key.get() else "*")

    def log(self, message: str, replace: bool = False) -> None:
        safe = sanitize_log_text(message, self.api_key.get().strip())
        self.log_box.configure(state="normal")
        if replace:
            self.log_box.delete("1.0", "end")
            self.log_box.insert("end", safe)
        else:
            now = time.strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{now}] {safe}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.root.update_idletasks()

    def close_app(self) -> None:
        self.app_closed = True
        for handle in list(getattr(self, "after_handles", set())):
            try:
                self.root.after_cancel(handle)
            except tk.TclError:
                pass
        self.after_handles.clear()
        self.root.destroy()

    def run_on_ui(self, callback) -> None:
        if self.app_closed:
            return
        try:
            self.root.after(0, callback)
        except RuntimeError:
            self.app_closed = True

    def run_later(self, delay_ms: int, callback) -> None:
        if self.app_closed:
            return

        def wrapped() -> None:
            if self.app_closed:
                return
            self.after_handles.discard(handle)
            callback()

        try:
            handle = self.root.after(delay_ms, wrapped)
            self.after_handles.add(handle)
        except RuntimeError:
            self.app_closed = True

    def log_from_worker(self, message: str) -> None:
        self.run_on_ui(lambda: self.log(message))

    def set_status_from_worker(self, message: str) -> None:
        self.run_on_ui(lambda: self.status.set(message))

    def show_info_from_worker(self, title: str, message: str) -> None:
        self.run_on_ui(lambda: messagebox.showinfo(title, message))

    def show_warning_from_worker(self, title: str, message: str) -> None:
        self.run_on_ui(lambda: messagebox.showwarning(title, message))

    def show_error_from_worker(self, title: str, message: str) -> None:
        self.run_on_ui(lambda: messagebox.showerror(title, message))

    def set_busy(self, busy: bool) -> None:
        self.worker_running = busy
        self.refresh_steps()

    def current_key_signature(self) -> tuple[str, str, str, bool]:
        return (
            self.api_key.get().strip(),
            DEFAULT_BASE_URL,
            self.model.get().strip(),
            self.skip_test.get(),
        )

    def mark_key_dirty(self, *_args) -> None:
        if self.saved_key_ok or self.saved_key_signature:
            self.saved_key_ok = False
            self.saved_key_signature = None
            self.status.set("状态：Key 已修改，请重新保存")
            self.refresh_steps()

    def mark_environment_dirty(self, *_args) -> None:
        if self.environment_checked or self.environment_ok:
            self.environment_checked = False
            self.environment_ok = False
            self.status.set("状态：系统选择已修改，请重新检测环境")
            self.refresh_steps()

    def mark_agent_selection_changed(self, *_args) -> None:
        self.refresh_steps()

    def start_login(self) -> None:
        if self.worker_running:
            return
        username = self.login_username.get()
        password = self.login_password.get()
        self.set_busy(True)
        self.status.set("状态：正在登录胖虎AI...")
        threading.Thread(target=self._login_worker, args=(username, password), daemon=True).start()

    def _login_worker(self, username: str, password: str) -> None:
        try:
            ok, msg, data = login_panghuai(username, password, self.cookie_jar)
            self.log_from_worker(msg)
            if not ok:
                self.set_status_from_worker("状态：登录失败")
                self.show_error_from_worker("登录失败", msg)
                return
            auth_ok, auth_msg, auth_data = activate_deployer(data, self.cookie_jar)
            self.log_from_worker(auth_msg)
            if not auth_ok:
                self.set_status_from_worker("状态：部署授权失败")
                self.show_error_from_worker("部署授权失败", auth_msg)
                return
            self.logged_in_user = data
            self.deployer_auth = auth_data
            display_name = str(data.get("username") or username)
            save_profile_data({"username": display_name, "user": data, "deployer_auth": auth_data})
            display_username = display_name if len(display_name) <= 20 else f"{display_name[:17]}..."
            self.run_on_ui(lambda: self.user_label.configure(text=f"已登录：{display_username}"))
            self.run_on_ui(self.show_wizard)
            self.run_later(1200, self.start_auto_update_check)
            self.set_status_from_worker("状态：已登录，请按步骤部署")
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_auto_update_check(self) -> None:
        if self.worker_running or self.auto_update_checked:
            return
        self.auto_update_checked = True
        threading.Thread(target=lambda: self._update_worker(auto=True), daemon=True).start()

    def start_update_check(self) -> None:
        if self.worker_running:
            return
        self.set_busy(True)
        self.status.set("状态：正在检查更新...")
        threading.Thread(target=lambda: self._update_worker(auto=False), daemon=True).start()

    def _update_worker(self, auto: bool = False) -> None:
        try:
            update, msg, release_url = find_available_update()
            self.log_from_worker(msg)
            if update:
                self.set_status_from_worker(f"状态：发现新版本 {update.latest_tag}")
                self.run_on_ui(lambda: self.prompt_online_update(update, auto))
            elif release_url and "未找到" in msg and "更新包" in msg:
                self.set_status_from_worker("状态：发现新版本，请到发布页下载")
                self.run_on_ui(lambda: open_url(release_url))
                if not auto:
                    self.show_warning_from_worker("发现新版本", msg)
            elif "当前已是最新版本" in msg:
                self.set_status_from_worker("状态：当前已是最新版本")
                if not auto:
                    self.show_info_from_worker("检查更新", msg)
            else:
                self.set_status_from_worker("状态：检查更新失败")
                if not auto:
                    self.show_warning_from_worker("检查更新", msg)
        finally:
            if not auto:
                self.run_on_ui(lambda: self.set_busy(False))

    def prompt_online_update(self, update: UpdateInfo, auto: bool) -> None:
        if self.worker_running and auto:
            return
        message = (
            f"发现新版本 {update.latest_tag}（当前 {APP_VERSION}）。\n\n"
            "是否现在在线更新？\n\n"
            "工具会下载对应系统安装包，自动覆盖当前程序并重新打开。"
            "你的登录状态、API Key、Codex 配置和工作区资料都会保留。"
        )
        if not messagebox.askyesno("发现新版本", message):
            if auto:
                self.status.set("状态：已跳过本次自动更新")
            else:
                self.set_busy(False)
            return
        self.set_busy(True)
        self.status.set("状态：正在下载在线更新包...")
        threading.Thread(target=self._download_and_apply_update_worker, args=(update,), daemon=True).start()

    def _download_and_apply_update_worker(self, update: UpdateInfo) -> None:
        try:
            path = download_update_package(update, self.log_from_worker)
            self.log_from_worker(f"更新包已下载：{path}")
            self.set_status_from_worker("状态：准备在线更新")
            self.run_on_ui(lambda: self.confirm_and_start_online_update(path))
        except Exception as exc:
            self.set_status_from_worker("状态：在线更新失败")
            self.show_warning_from_worker("在线更新失败", str(exc))
            self.run_on_ui(lambda: self.set_busy(False))

    def confirm_and_start_online_update(self, path: Path) -> None:
        try:
            start_online_update(path, self.log)
            messagebox.showinfo("开始在线更新", "更新程序已启动。本工具将退出，更新完成后会自动重新打开。")
            self.run_later(200, self.close_app)
        except Exception as exc:
            self.set_busy(False)
            messagebox.showerror("在线更新失败", str(exc))

    def show_wizard(self) -> None:
        self.login_frame.pack_forget()
        self.wizard_frame.pack(fill="both", expand=True)
        self.step.set(1)
        self.refresh_steps()

    def start_save_key(self) -> None:
        if self.worker_running:
            return
        if not self.logged_in_user:
            messagebox.showwarning("请先登录", "请先登录胖虎AI账号。")
            return
        if not self.deployer_auth:
            messagebox.showwarning("缺少部署授权", "请重新登录胖虎AI账号获取部署授权。")
            return
        api_key = self.api_key.get()
        self.base_url.set(DEFAULT_BASE_URL)
        base_url = DEFAULT_BASE_URL
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        self.set_busy(True)
        self.status.set("状态：正在测试 API Key...")
        threading.Thread(target=self._save_key_worker, args=(api_key, base_url, model, skip_test, open_app), daemon=True).start()

    def _save_key_worker(self, api_key: str, base_url: str, model: str, skip_test: bool, open_app: bool) -> None:
        try:
            base_url = DEFAULT_BASE_URL
            if not api_key.strip():
                raise ValueError("请先填写胖虎AI API Key。")
            if skip_test:
                ok, msg = True, "已保存 Key，接口测试被跳过。"
            else:
                base_url = DEFAULT_BASE_URL
                ok, msg = test_api(base_url, api_key)
            self.log_from_worker(msg)
            self.saved_key_ok = ok
            if ok:
                self.saved_key_signature = (api_key.strip(), DEFAULT_BASE_URL, model.strip(), skip_test)
                save_profile_data(
                    {
                        "api_key": api_key.strip(),
                        "base_url": DEFAULT_BASE_URL,
                        "model": model.strip(),
                        "skip_test": skip_test,
                        "open_app": open_app,
                    }
                )
                self.set_status_from_worker("状态：Key 已保存")
                self.run_on_ui(lambda: self.step.set(2))
                self.run_on_ui(self.refresh_steps)
            else:
                self.set_status_from_worker("状态：Key 测试失败")
                self.show_warning_from_worker("Key 测试失败", msg)
        except Exception as exc:
            self.set_status_from_worker("状态：Key 保存失败")
            self.show_error_from_worker("Key 保存失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def run_environment_check(self) -> None:
        if not self.has_valid_key():
            messagebox.showwarning("请先完成第一步", "请先保存并测试胖虎AI API Key，再检测环境。")
            self.step.set(1)
            self.refresh_steps()
            return
        lines = detect_environment()
        self.env_text.configure(state="normal")
        self.env_text.delete("1.0", "end")
        self.env_text.insert("end", "\n".join(lines))
        self.env_text.configure(state="disabled")
        for line in lines:
            self.log(line)
        self.environment_checked = True
        risk_findings = detect_risk_plugins()
        self.environment_ok = not risk_findings
        if self.environment_ok:
            self.status.set("状态：环境检测通过")
            self.step.set(3)
        else:
            self.status.set("状态：发现第三方配置插件，请先处理")
            messagebox.showwarning("环境检测未通过", format_risk_plugin_block_message(risk_findings))
        self.refresh_steps()

    def selected_agents(self) -> list[tuple[AgentSpec, str]]:
        selected = []
        for agent in AGENTS:
            if self.agent_enabled[agent.id].get():
                selected.append((agent, self.agent_mode[agent.id].get()))
        return selected

    def validate_config_ready(self) -> tuple[bool, tuple[str, str, str, bool] | None]:
        if self.worker_running:
            return False, None
        if not self.logged_in_user:
            messagebox.showwarning("请先登录", "请先登录胖虎AI账号。")
            return False, None
        if not self.deployer_auth:
            messagebox.showwarning("缺少部署授权", "请重新登录胖虎AI账号获取部署授权。")
            return False, None
        current_key_signature = self.current_key_signature()
        if not current_key_signature[0]:
            messagebox.showwarning("请先填写 Key", "请先在第一步填写胖虎AI API Key。")
            self.step.set(1)
            self.refresh_steps()
            return False, None
        if not self.saved_key_ok or self.saved_key_signature != current_key_signature:
            messagebox.showwarning("请先保存 Key", "请先在第一步保存当前胖虎AI API Key，然后再开始部署。")
            self.step.set(1)
            self.refresh_steps()
            return False, None
        return True, current_key_signature

    def validate_system_and_risk_plugins(self) -> bool:
        actual_system = current_system_id()
        if self.selected_system.get() != actual_system:
            readable = {"windows": "Windows", "mac": "Mac", "other": "其他系统"}
            messagebox.showwarning(
                "系统选择不一致",
                f"当前电脑识别为 {readable.get(actual_system, actual_system)}，"
                f"但你选择的是 {readable.get(self.selected_system.get(), self.selected_system.get())}。请回到第二步选择当前电脑系统。",
            )
            self.step.set(2)
            self.refresh_steps()
            return False
        risk_findings = detect_risk_plugins()
        if risk_findings:
            for line in risk_plugin_report_lines(risk_findings):
                self.log(line)
            messagebox.showwarning("请先卸载第三方插件", format_risk_plugin_block_message(risk_findings))
            self.status.set("状态：发现第三方配置插件，请先卸载后再部署")
            self.step.set(2)
            self.refresh_steps()
            return False
        return True

    def start_deploy(self) -> None:
        ok, _current_key_signature = self.validate_config_ready()
        if not ok:
            return
        if not self.can_access_step(4):
            self.go_to_step(4)
            return
        selected = self.selected_agents()
        if not selected:
            messagebox.showwarning("请选择 Agent", "请至少选择一个 Agent。")
            return
        if not self.validate_system_and_risk_plugins():
            return
        user = dict(self.logged_in_user or {})
        deployer_auth = dict(self.deployer_auth or {})
        api_key = self.api_key.get()
        self.base_url.set(DEFAULT_BASE_URL)
        base_url = DEFAULT_BASE_URL
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        self.set_busy(True)
        self.status.set("状态：正在部署 Agent...")
        threading.Thread(
            target=self._deploy_worker,
            args=(selected, user, deployer_auth, api_key, base_url, model, skip_test, open_app),
            daemon=True,
        ).start()

    def start_config_only(self) -> None:
        self.start_config_for_mode(CodexConfigMode.DIRECT_API)

    def start_dual_state_config(self) -> None:
        self.start_config_for_mode(CodexConfigMode.DUAL_STATE)

    def start_config_for_mode(self, mode: CodexConfigMode) -> None:
        ok, _current_key_signature = self.validate_config_ready()
        if not ok:
            return
        if not self.can_access_step(4):
            self.go_to_step(4)
            return
        if not self.validate_system_and_risk_plugins():
            return
        user = dict(self.logged_in_user or {})
        deployer_auth = dict(self.deployer_auth or {})
        api_key = self.api_key.get()
        self.base_url.set(DEFAULT_BASE_URL)
        base_url = DEFAULT_BASE_URL
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        if mode == CodexConfigMode.DUAL_STATE:
            status = "状态：正在写入 Codex 双态模式配置..."
            target = self._config_only_worker
        else:
            status = "状态：正在修复 Codex 普通配置..."
            target = self._config_only_worker
        self.set_busy(True)
        self.status.set(status)
        threading.Thread(
            target=target,
            args=(user, deployer_auth, api_key, base_url, model, skip_test, open_app, mode),
            daemon=True,
        ).start()

    def _config_only_worker(
        self,
        user: dict,
        deployer_auth: dict,
        api_key: str,
        base_url: str,
        model: str,
        skip_test: bool,
        open_app: bool,
        mode: CodexConfigMode,
    ) -> None:
        try:
            temporary_access = self.fetch_temporary_openai_access(user, deployer_auth)
            ok = install_codex_config(
                api_key,
                base_url,
                model,
                skip_test,
                open_app,
                self.log_from_worker,
                temporary_access,
                mode,
            )
            if ok:
                self.set_status_from_worker("状态：Codex 配置修复完成")
                if mode == CodexConfigMode.DUAL_STATE:
                    message = (
                        "Codex 双态模式配置已写入，不会重新安装 Agent。\n\n"
                        "请先完全退出 Codex，再重新打开 Codex；新的配置只有重开后才会生效。\n\n"
                        "双态模式需要用户重新打开后自行登录自己的 ChatGPT 账号。登录态来自用户账号，模型消耗走胖虎AI API Key。"
                    )
                else:
                    message = (
                        "Codex 普通直接 API 配置已重新写入，不会重新安装 Agent。\n\n"
                        "请先完全退出 Codex，再重新打开 Codex；新的配置只有重开后才会生效。"
                    )
                self.show_info_from_worker("配置完成", message)
            else:
                self.set_status_from_worker("状态：Codex 配置测试失败，已恢复备份")
                self.show_warning_from_worker("配置测试失败", "配置写入后接口测试失败，已自动恢复备份。请检查 Key、余额或网络。")
        except Exception as exc:
            self.set_status_from_worker("状态：Codex 配置修复失败")
            self.log_from_worker(f"Codex 配置修复失败：{exc}")
            self.show_error_from_worker("配置修复失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def _deploy_worker(
        self,
        selected: list[tuple[AgentSpec, str]],
        user: dict,
        deployer_auth: dict,
        api_key: str,
        base_url: str,
        model: str,
        skip_test: bool,
        open_app: bool,
    ) -> None:
        try:
            token = str(deployer_auth.get("token") or "")
            ok, msg, manifest = fetch_deployer_manifest(user, self.cookie_jar, token)
            self.log_from_worker(msg)
            if not ok:
                raise RuntimeError(msg)
            self.deployer_manifest = manifest
            allowed_agents = set(manifest_allowed_agents(manifest))
            blocked = [agent.name for agent, _ in selected if agent.id not in allowed_agents]
            if blocked:
                raise RuntimeError("当前账号未授权安装：" + "、".join(blocked))
            temporary_access = parse_temporary_openai_access_config(manifest)
            self.log_from_worker("开始普通一键部署：" + "、".join(f"{a.name}/{m}" for a, m in selected))
            success_count = 0
            for agent, mode in selected:
                if install_agent(agent, mode, self.log_from_worker):
                    success_count += 1
            if any(agent.id == "codex" for agent, _ in selected):
                ok = install_codex_config(
                    api_key,
                    base_url,
                    model,
                    skip_test,
                    open_app,
                    self.log_from_worker,
                    temporary_access,
                )
                if ok:
                    self.log_from_worker("Codex 胖虎AI配置已应用。")
            write_agent_setup_guide(selected, api_key, self.log_from_worker)
            self.set_status_from_worker(f"状态：部署完成，成功处理 {success_count}/{len(selected)} 个 Agent")
            self.show_info_from_worker("部署完成", "Agent 部署流程已完成，请查看日志确认每个 Agent 的状态。")
        except Exception as exc:
            self.set_status_from_worker("状态：部署失败")
            self.log_from_worker(f"部署失败：{exc}")
            self.show_error_from_worker("部署失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def fetch_temporary_openai_access(
        self,
        user: dict,
        deployer_auth: dict,
    ) -> TemporaryOpenAIAccessConfig | None:
        token = str(deployer_auth.get("token") or "")
        ok, msg, manifest = fetch_deployer_manifest(user, self.cookie_jar, token)
        self.log_from_worker(msg)
        if not ok:
            self.log_from_worker("未能刷新部署清单，本次只修复 Codex 配置，不开启 OpenAI 官网临时访问窗口。")
            return None
        self.deployer_manifest = manifest
        return parse_temporary_openai_access_config(manifest)

    def open_workspace(self) -> None:
        path = workspace_root()
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def open_config_dir(self) -> None:
        path = codex_home()
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def restore_backups(self) -> None:
        if self.worker_running:
            return
        ok = restore_latest_backups(self.log)
        if ok:
            self.status.set("状态：已恢复最近备份")
            messagebox.showinfo("恢复备份", "已恢复找到的最近备份。")
        else:
            self.status.set("状态：未找到可恢复备份")
            messagebox.showwarning("恢复备份", "未找到可恢复的配置备份。")

    def copy_logs(self) -> None:
        text = self.log_box.get("1.0", "end").strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status.set("状态：日志已复制")


def self_test() -> None:
    assert APP_VERSION == "1.0.15"
    assert any(agent.id == "codex" for agent in AGENTS)
    assert any(agent.id == "claude_code" for agent in AGENTS)
    assert any(spec.id == "ccswitch" for spec in RISK_PLUGIN_SPECS)
    assert any(spec.id == "codex_plus_plus" for spec in RISK_PLUGIN_SPECS)
    assert LOGIN_URL.endswith("/api/user/login?turnstile=")
    assert DEPLOYER_ACTIVATE_URL.endswith("/api/deployer/activate")
    assert manifest_allowed_agents({"agents": [{"id": "codex"}, {"id": "hermes"}]}) == ["codex", "hermes"]
    assert process_text_contains_alias("node ccr start", "ccr")
    assert not process_text_contains_alias("screenrecorder.exe", "ccr")
    assert "sk-test-secret-123456" not in sanitize_log_text("Key sk-test-secret-123456", "sk-test-secret-123456")
    assert "刚才在本工具里填写的 API Key" in build_agent_setup_guide_content([], "sk-test-secret-123456")
    assert "无需登录 ChatGPT 账号" in login_help_text()
    assert "新账号先充值或确认账户里有余额" in key_creation_help_text()
    action_help = codex_action_help_text()
    assert "一键部署（普通）：普通模式。第一次安装 Agent 时使用" in action_help
    assert "双态配置：需要同时保留 ChatGPT 登录态并消耗胖虎AI API Key" in action_help
    assert "仅修复 Codex 配置：Agent 已经装好" in action_help
    assert "恢复最近备份：配置异常时退回" in action_help
    assert "任何模式配置写完后都必须完全退出 Codex" in action_help
    assert "只要修改过 Codex 配置，都要完全退出 Codex 后重新打开" in codex_action_summary_text()
    assert "已禁止继续安装" in "\n".join(risk_plugin_report_lines([RiskPluginFinding("CCSwitch", "命令", "ccswitch", "")]))
    config = build_config("sk-test", DEFAULT_BASE_URL, DEFAULT_MODEL)
    expected_config = '''model_provider = "panghuAI"
model = "gpt-5.4"
review_model = "gpt-5.4"
model_reasoning_effort = "xhigh"
disable_response_storage = true
network_access = "enabled"
windows_wsl_setup_acknowledged = true
model_context_window = 1000000
model_auto_compact_token_limit =600000

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
requires_openai_auth = true
'''
    assert config == expected_config
    assert merge_config("old = true\n[desktop]\nappearanceTheme = \"light\"\n", "sk-test", "bad", "bad") == expected_config
    assert build_config("sk-test", "https://bad.example", DEFAULT_MODEL) == expected_config
    bad_url_dual_config = build_dual_state_config("sk-test", "https://bad.example", DEFAULT_MODEL)
    assert "https://bad.example" not in bad_url_dual_config
    assert 'base_url = "https://aitokenapi.cc/v1"' in bad_url_dual_config
    assert "experimental_bearer_token" not in config
    dual_config = build_dual_state_config("sk-test", DEFAULT_BASE_URL, DEFAULT_MODEL)
    assert 'experimental_bearer_token = "sk-test"' in dual_config
    direct_auth = json.loads(build_direct_api_auth_json("", "sk-test"))
    assert direct_auth == {"OPENAI_API_KEY": "sk-test"}
    existing_auth = json.dumps(
        {
            "auth_mode": "apikey",
            "OPENAI_API_KEY": "old-key",
            "tokens": {"access_token": "keep-access", "refresh_token": "keep-refresh"},
            "last_refresh": "2026-06-18T00:00:00Z",
        }
    )
    auth = json.loads(build_dual_state_auth_json(existing_auth, "sk-test"))
    assert auth["auth_mode"] == "chatgpt"
    assert auth["OPENAI_API_KEY"] is None
    assert auth["tokens"]["access_token"] == "keep-access"
    assert auth["tokens"]["refresh_token"] == "keep-refresh"
    assert auth["last_refresh"] == "2026-06-18T00:00:00Z"
    assert normalize_version("v1.2.3") > normalize_version("1.0.9")
    merged = merge_agents_rules("# old")
    assert PANGHU_AGENTS_START in merged and PANGHU_AGENTS_END in merged
    temporary_config = parse_temporary_openai_access_config(
        {"temporary_openai_access": {"enabled": True, "proxy": "aitokenapi.cc:80", "duration_seconds": 999}}
    )
    assert temporary_config is not None
    assert temporary_config.proxy == "aitokenapi.cc:80"
    assert temporary_config.duration_seconds == 600
    assert parse_temporary_openai_access_config({"temporary_openai_access": {"enabled": True, "proxy": "bad/proxy"}}) is None
    pac = build_openai_access_pac("aitokenapi.cc:80", "DIRECT")
    assert 'shExpMatch(host, "*.openai.com")' in pac
    assert 'shExpMatch(host, "*.chatgpt.com")' in pac
    assert "return \"PROXY aitokenapi.cc:80; DIRECT\";" in pac
    update = UpdateInfo("v9.9.9", "https://example.com/update.zip", "https://example.com/release", "AI.Agent.-Windows.zip", "Windows")
    assert update.asset_name == "AI.Agent.-Windows.zip"
    win_update_script = build_windows_update_script(Path("C:/tmp/update.zip"), Path("C:/App"), Path("C:/App/app.exe"), 1234)
    assert "Wait-Process -Id $pidToWait" in win_update_script
    assert "Expand-Archive" in win_update_script
    assert "Copy-Item -Path" in win_update_script
    assert "Start-Process -FilePath $launchTarget" in win_update_script
    mac_update_script = build_macos_update_script(Path("/tmp/update.zip"), Path("/Applications/App.app"), Path("/Applications/App.app"), 1234)
    assert "while kill -0" in mac_update_script
    assert "ditto -x -k" in mac_update_script
    assert 'rm -rf "$APP_DIR"' in mac_update_script
    assert "cp -R" in mac_update_script
    assert "open \"$LAUNCH_TARGET\"" in mac_update_script
    restore_script = build_windows_temp_openai_access_script()
    assert "Start-Sleep -Seconds $Seconds" in restore_script
    assert "Restore-InternetProxyState" in restore_script
    assert "AutoConfigURL" in restore_script
    assert "Register-ScheduledTask" in restore_script
    assert "-RestoreOnly" in restore_script
    assert "if ($RestoreOnly)" in restore_script
    assert "InternetSetOption" in restore_script
    mac_restore_script = build_macos_temp_openai_access_script()
    assert "networksetup" in mac_restore_script
    assert "setautoproxyurl" in mac_restore_script
    assert "LaunchDaemons" in mac_restore_script
    assert "restore_state" in mac_restore_script
    assert "SECONDS_VALUE" in mac_restore_script
    original_system = platform.system
    original_machine = platform.machine
    try:
        platform.system = lambda: "Darwin"  # type: ignore[method-assign]
        platform.machine = lambda: "arm64"  # type: ignore[method-assign]
        assert current_mac_package_suffix() == "AppleSilicon"
        assert release_asset_name_for_current_system().endswith("-Mac-AppleSilicon.zip")
        assert public_manifest_asset_url({"mac_apple_silicon_zip_url": "arm", "mac_intel_zip_url": "intel"}) == "arm"
        platform.machine = lambda: "x86_64"  # type: ignore[method-assign]
        assert current_mac_package_suffix() == "Intel"
        assert release_asset_name_for_current_system().endswith("-Mac-Intel.zip")
        assert public_manifest_asset_url({"mac_apple_silicon_zip_url": "arm", "mac_intel_zip_url": "intel"}) == "intel"
        assert public_manifest_asset_url({"mac_zip_url": "legacy"}) == ""
    finally:
        platform.system = original_system  # type: ignore[method-assign]
        platform.machine = original_machine  # type: ignore[method-assign]
    print("UI self-test OK")


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

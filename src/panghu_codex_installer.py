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
import threading
import time
import tkinter as tk
import uuid
import webbrowser
from dataclasses import dataclass
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
APP_VERSION = "1.0.12"
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
APP_BG = "#edf3f8"
CARD_BG = "#ffffff"
PANEL_BG = "#f8fbfd"
INK = "#102033"
MUTED = "#607086"
PRIMARY = "#155e75"
PRIMARY_DARK = "#0f3f50"
ACCENT = "#0f9f7a"
BORDER = "#d7e2ea"
WARNING_BG = "#fff7ed"
GOLD = "#d6a648"
GOLD_SOFT = "#fff8e5"


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
        "base_url": str(current.get("base_url") or DEFAULT_BASE_URL),
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
    payload = {"OPENAI_API_KEY": api_key.strip()}
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


def check_and_download_update(log) -> tuple[bool, str, Path | None, str | None]:
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
            return False, "检查更新失败：公开更新清单缺少版本号。", None, release_url
        if normalize_version(latest_tag) <= normalize_version(APP_VERSION):
            return False, f"当前已是最新版本：{APP_VERSION}", None, release_url
        if not asset_url:
            return False, f"发现新版本 {latest_tag}，但公开更新清单缺少 {platform_label_for_update()} 下载地址。", None, release_url
        target_dir = downloads_dir() / "胖虎AI工具更新"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{latest_tag}-{release_asset_name_for_current_system()}"
        log(f"发现新版本 {latest_tag}，开始下载更新包。")
        try:
            download_with_trusted_certs(asset_url, target)
        except Exception as exc:
            return False, f"下载更新失败：{exc}", None, release_url
        return True, f"新版本 {latest_tag} 已下载。请关闭本工具后解压覆盖旧版本。", target, release_url

    req = Request(GITHUB_RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": HTTP_USER_AGENT})
    try:
        with trusted_urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return False, f"检查更新失败：{exc}", None, None

    latest_tag = str(payload.get("tag_name") or "").strip()
    release_url = str(payload.get("html_url") or "https://github.com/dashuaiisme/panghu-codex-installer/releases")
    if not latest_tag:
        return False, "检查更新失败：GitHub Release 没有版本号。", None, release_url
    if normalize_version(latest_tag) <= normalize_version(APP_VERSION):
        return False, f"当前已是最新版本：{APP_VERSION}", None, release_url

    asset_url = ""
    for asset in payload.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        if name in release_asset_aliases_for_current_system():
            asset_url = str(asset.get("browser_download_url") or "")
            break
    if not asset_url:
        return False, f"发现新版本 {latest_tag}，但未找到 {platform_label_for_update()} 更新包，已打开发布页。", None, release_url

    target_dir = downloads_dir() / "胖虎AI工具更新"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{latest_tag}-{release_asset_name_for_current_system()}"
    log(f"发现新版本 {latest_tag}，开始下载更新包。")
    try:
        download_with_trusted_certs(asset_url, target)
    except Exception as exc:
        return False, f"下载更新失败：{exc}", None, release_url
    return True, f"新版本 {latest_tag} 已下载。请关闭本工具后解压覆盖旧版本。", target, release_url


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
) -> bool:
    if not api_key.strip():
        raise ValueError("请先输入胖虎AI API Key。")
    if not base_url.strip():
        raise ValueError("接口地址不能为空。")
    if not model.strip():
        raise ValueError("模型不能为空。")

    api_key = api_key.strip()
    base_url = base_url.strip()
    model = model.strip()
    home = codex_home()
    workdir = workspace_root()
    config_path = home / "config.toml"
    auth_path = codex_auth_path()
    global_agents = home / "AGENTS.md"
    workspace_agents = workdir / "AGENTS.md"

    log("开始应用 Codex 胖虎AI配置。")
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
    write_text(config_path, merge_config(old_config, api_key, base_url, model))
    write_text(auth_path, build_auth_json(old_auth, api_key))
    for agents_path in (global_agents, workspace_agents):
        old_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
        write_text(agents_path, merge_agents_rules(old_agents))
    log(f"已写入 Codex 配置：{config_path}")
    log(f"已写入 Codex 登录授权文件：{auth_path}")
    log(f"接口地址：{CODEX_BASE_URL}")
    log(f"模型：{model}")
    log(f"Key：{mask_key(api_key)}")

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
1. Codex 已由本工具自动写入配置。
2. ClaudeCode 只负责官方安装，不写入配置；请按 ClaudeCode 官方流程自行登录或配置。
3. OpenClaw / Hermes 当前版本先安装并提供说明；如果官方客户端要求在界面里粘贴 Key，请使用胖虎AI接口和你刚才在本工具里填写的 API Key。
4. 本工具不会把 API Key 明文写入日志。
"""


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
        root.geometry("1120x860")
        root.minsize(1040, 740)
        root.configure(bg=APP_BG)
        self.ui_images: list[tk.PhotoImage] = []
        self.set_window_icon()

        self.cookie_jar = http.cookiejar.CookieJar()
        self.logged_in_user: dict | None = None
        self.deployer_auth: dict | None = None
        self.deployer_manifest: dict | None = None
        self.saved_key_ok = False
        self.saved_key_signature: tuple[str, str, str, bool] | None = None
        self.worker_running = False

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
        for variable in (self.api_key, self.base_url, self.model, self.skip_test):
            variable.trace_add("write", self.mark_key_dirty)

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
        self.base_url.set(str(profile.get("base_url") or DEFAULT_BASE_URL))
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

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        style.configure("TCombobox", fieldbackground="#ffffff", bordercolor=BORDER)
        style.configure("TCheckbutton", background=CARD_BG, foreground=INK)
        style.configure("TRadiobutton", background=CARD_BG, foreground=INK)

        self.container = tk.Frame(self.root, bg=APP_BG, padx=24, pady=20)
        self.container.pack(fill="both", expand=True)

        self.header = tk.Frame(self.container, bg="#ffffff", highlightthickness=1, highlightbackground=BORDER)
        self.header.pack(fill="x")
        top_row = tk.Frame(self.header, bg="#ffffff", height=92)
        top_row.pack(fill="x")
        top_row.pack_propagate(False)
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=0)
        brand_area = tk.Frame(top_row, bg="#ffffff")
        brand_area.grid(row=0, column=0, sticky="nsew", padx=(22, 18), pady=14)
        avatar = self.load_ui_image("panghu-avatar-64.png")
        if avatar:
            tk.Label(brand_area, image=avatar, bg="#ffffff").pack(side="left", anchor="center", padx=(0, 14))
        brand_text = tk.Frame(brand_area, bg="#ffffff")
        brand_text.pack(side="left", anchor="center")
        tk.Label(
            brand_text,
            text="胖虎AI",
            font=("Microsoft YaHei UI", 10, "bold"),
            fg=PRIMARY,
            bg="#ffffff",
        ).pack(anchor="w")
        tk.Label(
            brand_text,
            text="多 Agent 一键部署工具",
            font=("Microsoft YaHei UI", 21, "bold"),
            fg=INK,
            bg="#ffffff",
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            brand_text,
            text="登录胖虎AI账号后，按流程完成 Agent 安装与本机配置。",
            font=("Microsoft YaHei UI", 9),
            fg=MUTED,
            bg="#ffffff",
        ).pack(anchor="w", pady=(5, 0))

        action_area = tk.Frame(top_row, bg="#ffffff")
        action_area.grid(row=0, column=1, sticky="e", padx=(0, 22), pady=24)
        self.update_button = tk.Button(
            action_area,
            text="检查更新",
            command=self.start_update_check,
            bg="#eef5f8",
            fg=PRIMARY_DARK,
            activebackground="#d2e3eb",
            activeforeground=PRIMARY_DARK,
            relief="flat",
            bd=0,
            padx=16,
            pady=7,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.update_button.pack(side="left")
        self.user_label = tk.Label(
            action_area,
            text="未登录",
            bg=GOLD_SOFT,
            fg="#8a5b00",
            padx=15,
            pady=7,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.user_label.pack(side="left", padx=(10, 0))

        support_bar = tk.Frame(self.header, bg="#f7fbfd", height=36)
        support_bar.pack(fill="x")
        support_bar.pack_propagate(False)
        tk.Frame(support_bar, bg=BORDER, height=1).pack(fill="x")
        tk.Label(
            support_bar,
            text="客服微信：panghuwanAI  ·  Plus / Pro 代充  ·  国外手机验证",
            bg="#f7fbfd",
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="left", padx=22, pady=(7, 0))

        self.body = tk.Frame(self.container, bg=APP_BG)
        self.body.pack(fill="both", expand=True, pady=(14, 0))

        self.login_frame = tk.Frame(self.body, bg=APP_BG, relief="flat", highlightthickness=0)
        self.login_frame.pack(fill="both", expand=True, ipady=0)
        self._build_login_frame(self.login_frame)

        self.wizard_frame = tk.Frame(self.body, bg=APP_BG)
        self._build_wizard_frame(self.wizard_frame)

        self.log_box = tk.Text(
            self.container,
            height=2,
            bg="#ffffff",
            fg="#33536a",
            insertbackground="#33536a",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=6,
            wrap="word",
            font=("Microsoft YaHei UI", 9),
        )
        self.log_box.pack(fill="both", expand=False, pady=(10, 0))
        self.log_box.configure(state="disabled")

        tk.Label(self.container, textvariable=self.status, bg=APP_BG, fg=MUTED).pack(anchor="w", pady=(8, 0))

    def _button(self, parent: tk.Widget, text: str, command, kind: str = "secondary") -> tk.Button:
        if kind == "primary":
            bg, fg, active = PRIMARY, "#ffffff", PRIMARY_DARK
        elif kind == "success":
            bg, fg, active = ACCENT, "#ffffff", "#08745b"
        else:
            bg, fg, active = "#e7eef3", INK, "#d3e0e8"
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
            padx=18,
            pady=9,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
        )

    def _build_login_frame(self, parent: tk.Frame) -> None:
        parent.configure(padx=0, pady=0)
        login_card = tk.Frame(parent, bg=CARD_BG, padx=30, pady=28, highlightthickness=1, highlightbackground=BORDER)
        login_card.pack(side="left", fill="both", expand=True, padx=(0, 14))
        tk.Label(
            login_card,
            text="登录胖虎AI账号",
            font=("Microsoft YaHei UI", 19, "bold"),
            bg=CARD_BG,
            fg=INK,
        ).pack(anchor="w")
        tk.Label(
            login_card,
            text="只有胖虎AI注册用户可以使用部署工具；没有账号请先注册。",
            bg=CARD_BG,
            fg=MUTED,
        ).pack(anchor="w", pady=(8, 20))

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

        tk.Frame(login_card, bg=BORDER, height=1).pack(fill="x", pady=(26, 14))
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

        guide_card = tk.Frame(parent, bg="#ffffff", padx=26, pady=24, width=340, highlightthickness=1, highlightbackground=BORDER)
        guide_card.pack(side="left", fill="y")
        guide_card.pack_propagate(False)
        tk.Label(guide_card, text="客户使用流程", font=("Microsoft YaHei UI", 17, "bold"), bg="#ffffff", fg=INK).pack(anchor="w")
        tk.Label(
            guide_card,
            text="按顺序完成，软件会提示下一步。",
            bg="#ffffff",
            fg=MUTED,
            wraplength=275,
            justify="left",
        ).pack(anchor="w", pady=(5, 16))
        for idx, (title, desc) in enumerate((
            ("创建 Key", "填写胖虎AI API Key"),
            ("检测系统", "识别 Windows / Mac 和依赖环境"),
            ("选择 Agent", "选择要安装的 Agent 和安装方式"),
            ("一键部署", "安装完成后应用安全配置"),
        )):
            item = tk.Frame(guide_card, bg="#ffffff")
            item.pack(fill="x", pady=(0, 12))
            tk.Label(
                item,
                text=str(idx + 1),
                bg=GOLD,
                fg=PRIMARY_DARK,
                width=3,
                pady=3,
                font=("Microsoft YaHei UI", 9, "bold"),
            ).pack(side="left", anchor="n", padx=(0, 12))
            copy = tk.Frame(item, bg="#ffffff")
            copy.pack(side="left", fill="x", expand=True)
            tk.Label(copy, text=title, bg="#ffffff", fg=INK, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w")
            tk.Label(copy, text=desc, bg="#ffffff", fg=MUTED, wraplength=245, justify="left").pack(anchor="w", pady=(3, 0))
            if idx < 3:
                tk.Frame(guide_card, bg="#e7eef3", height=1).pack(fill="x", pady=(0, 12))

    def _build_wizard_frame(self, parent: tk.Frame) -> None:
        shell = tk.Frame(parent, bg=APP_BG)
        shell.pack(fill="both", expand=True)

        rail = tk.Frame(shell, bg=PRIMARY_DARK, width=220)
        rail.pack(side="left", fill="y", padx=(0, 16))
        rail.pack_propagate(False)
        tk.Label(rail, text="部署流程", bg=PRIMARY_DARK, fg="#ffffff", font=("Microsoft YaHei UI", 16, "bold")).pack(
            anchor="w", padx=22, pady=(24, 4)
        )
        tk.Label(
            rail,
            text="按顺序完成 Key、环境、Agent 和配置应用。",
            bg=PRIMARY_DARK,
            fg="#bdebe2",
            wraplength=190,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 18))

        self.step_buttons: dict[int, tk.Button] = {}
        for idx, title, subtitle in (
            (1, "创建 Key", "验证胖虎AI接口"),
            (2, "检测系统", "确认电脑环境"),
            (3, "选择 Agent", "选择 CLI 或客户端"),
            (4, "安装配置", "执行安装和应用"),
        ):
            btn = self._step_button(rail, idx, title, subtitle)
            btn.pack(fill="x", padx=16, pady=(0, 10))
            self.step_buttons[idx] = btn

        panel = tk.Frame(shell, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER)
        panel.pack(side="left", fill="both", expand=True)
        self.steps_host = tk.Frame(panel, bg=CARD_BG, padx=22, pady=20)
        self.steps_host.pack(fill="both", expand=True)
        self.step_frames: dict[int, tk.Frame] = {}
        self._build_step_1()
        self._build_step_2()
        self._build_step_3()
        self._build_step_4()

        for frame in self.step_frames.values():
            frame.place(in_=self.steps_host, x=0, y=0, relwidth=1, relheight=1)
        self.refresh_steps()

    def _step_button(self, parent: tk.Frame, idx: int, title: str, subtitle: str) -> tk.Button:
        text = f"{idx}. {title}\n{subtitle}"

        def activate() -> None:
            self.step.set(idx)
            self.refresh_steps()

        return tk.Button(
            parent,
            text=text,
            command=activate,
            anchor="w",
            justify="left",
            bg=PRIMARY_DARK,
            fg="#c8f3ea",
            activebackground=PRIMARY,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=12,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
        )

    def _step_title(self, parent: tk.Frame, title: str, desc: str) -> None:
        tk.Label(parent, text=title, font=("Microsoft YaHei UI", 17, "bold"), bg=CARD_BG, fg=INK).pack(anchor="w")
        tk.Label(parent, text=desc, bg=CARD_BG, fg=MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(7, 16))

    def _field_label(self, parent: tk.Frame, text: str, bg: str = CARD_BG) -> None:
        tk.Label(parent, text=text, bg=bg, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")

    def _build_step_1(self) -> None:
        frame = tk.Frame(self.steps_host, bg=CARD_BG, padx=4, pady=2)
        self.step_frames[1] = frame
        self._step_title(
            frame,
            "第一步：创建并保存胖虎AI API Key",
            "客户先去胖虎AI控制台创建 Key，再粘贴到这里。软件会用 /v1/models 做一次可用性验证。",
        )

        guide = tk.Frame(frame, bg=WARNING_BG, padx=16, pady=13, highlightthickness=1, highlightbackground="#fed7aa")
        guide.pack(fill="x")
        tk.Label(guide, text="操作路径", bg=WARNING_BG, fg="#9a3412", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        tk.Label(
            guide,
            text="点击按钮打开胖虎AI登录页；如果浏览器没有登录，网站会先要求登录，然后进入 Key 创建页面。",
            bg=WARNING_BG,
            fg="#7c2d12",
            wraplength=560,
            justify="left",
        ).pack(side="left", anchor="w", pady=(5, 0))
        self._button(guide, "打开 API Key 创建页面", lambda: open_url(KEY_CREATE_URL), "secondary").pack(
            side="right", padx=(14, 0)
        )

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
        base_frame.pack(side="left", fill="x", expand=True, padx=(0, 16))
        self._field_label(base_frame, "接口地址")
        ttk.Entry(base_frame, textvariable=self.base_url, font=("Microsoft YaHei UI", 11)).pack(fill="x", ipady=7, pady=(6, 0))
        model_frame = tk.Frame(form, bg=CARD_BG, width=220)
        model_frame.pack(side="left", fill="x")
        self._field_label(model_frame, "默认模型")
        ttk.Combobox(model_frame, textvariable=self.model, values=["gpt-5.5", "gpt-5.4", "gpt-4.1"]).pack(
            fill="x", ipady=5, pady=(6, 0)
        )

        options = tk.Frame(frame, bg=CARD_BG)
        options.pack(fill="x", pady=(18, 0))
        ttk.Checkbutton(options, text="跳过接口测试", variable=self.skip_test).pack(side="left")
        self._button(options, "保存并测试 Key", self.start_save_key, "primary").pack(side="left", padx=(16, 0))

    def _build_step_2(self) -> None:
        frame = tk.Frame(self.steps_host, bg=CARD_BG, padx=4, pady=2)
        self.step_frames[2] = frame
        self._step_title(
            frame,
            "第二步：选择系统并检测环境",
            "自动识别客户电脑系统，检查基础环境，并拦截 ccswitch、codex++、CCR 等可能改坏配置的第三方工具。",
        )
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
            bg="#07151c",
            fg="#d7f9ea",
            insertbackground="#d7f9ea",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            wrap="word",
            font=("Cascadia Mono", 9),
        )
        self.env_text.pack(fill="both", expand=True, pady=(14, 0))
        self.env_text.configure(state="disabled")

    def _agent_card_copy(self, agent: AgentSpec) -> tuple[str, str]:
        copies = {
            "codex": ("官方 Codex Agent，可应用胖虎AI配置。", "可写入 Key、接口、模型和中文规则。"),
            "claude_code": ("Claude Code，只安装不写配置。", "不写 Key，不改账号或 ClaudeCode 配置。"),
            "openclaw": ("OpenClaw，官方入口安装。", "安全路径未确认时，仅生成中文配置指引。"),
            "hermes": ("Hermes，官方入口安装。", "安全路径未确认时，仅生成中文配置指引。"),
        }
        return copies.get(agent.id, (agent.description, agent.config_note))

    def _build_step_3(self) -> None:
        frame = tk.Frame(self.steps_host, bg=CARD_BG, padx=4, pady=2)
        self.step_frames[3] = frame
        self._step_title(
            frame,
            "第三步：选择 Agent 和安装方式",
            "ClaudeCode 只安装不配置；其他 Agent 只有在官方路径明确、安全可写时才自动应用胖虎AI配置。",
        )

        list_frame = tk.Frame(frame, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)
        list_frame.grid_columnconfigure(0, weight=1)
        for index, agent in enumerate(AGENTS):
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=10, pady=8, highlightthickness=1, highlightbackground=BORDER)
            row.grid(row=index, column=0, sticky="ew", pady=(0, 7))
            row.grid_columnconfigure(1, weight=1)
            enabled = tk.BooleanVar(value=agent.id == "codex")
            mode = tk.StringVar(value="cli")
            self.agent_enabled[agent.id] = enabled
            self.agent_mode[agent.id] = mode
            card_description, _card_note = self._agent_card_copy(agent)
            header = tk.Frame(row, bg=PANEL_BG)
            header.grid(row=0, column=0, sticky="nw", padx=(0, 14))
            tk.Checkbutton(
                header,
                text=f"选择 {agent.name}",
                variable=enabled,
                indicatoron=False,
                bg="#e6f0f5",
                fg=INK,
                activebackground="#d9e9ef",
                activeforeground=INK,
                selectcolor="#d8f3e9",
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
                bg=GOLD_SOFT if agent.id == "codex" else "#e7eef3",
                fg="#8a5b00" if agent.id == "codex" else MUTED,
                padx=9,
                pady=4,
                font=("Microsoft YaHei UI", 9, "bold"),
            ).pack(anchor="w", pady=(4, 0))
            text_area = tk.Frame(row, bg=PANEL_BG)
            text_area.grid(row=0, column=1, sticky="ew")
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
            mode_area.grid(row=0, column=2, sticky="ne", padx=(12, 0))
            tk.Label(mode_area, text="安装方式", bg=PANEL_BG, fg=MUTED, font=("Microsoft YaHei UI", 9, "bold")).pack(
                anchor="e", pady=(0, 5)
            )
            for item in agent.modes:
                tk.Radiobutton(
                    mode_area,
                    text=item.label,
                    value=item.id,
                    variable=mode,
                    indicatoron=False,
                    bg="#ffffff",
                    fg=INK,
                    activebackground="#e7eef3",
                    activeforeground=INK,
                    selectcolor="#d8f3e9",
                    relief="flat",
                    bd=0,
                    padx=9,
                    pady=4,
                    cursor="hand2",
                    font=("Microsoft YaHei UI", 9, "bold"),
                ).pack(side="left", padx=(0, 6))

    def _build_step_4(self) -> None:
        frame = tk.Frame(self.steps_host, bg=CARD_BG, padx=4, pady=2)
        self.step_frames[4] = frame
        self._step_title(
            frame,
            "第四步：一键安装并应用配置",
            "安装只调用官方在线入口。开始前会再次检查第三方配置插件，发现风险工具会先要求卸载。",
        )
        summary = tk.Frame(frame, bg=PANEL_BG, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER)
        summary.pack(fill="x")
        tk.Label(summary, text="执行前确认", bg=PANEL_BG, fg=INK, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w")
        tk.Label(
            summary,
            text=(
                "未保存有效 Key 时不会进入配置应用。若发现 ccswitch、codex++、CCR 等工具，会停止安装并提示先卸载，"
                "防止它们改坏 Agent 配置。"
            ),
            bg=PANEL_BG,
            fg=MUTED,
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(7, 0))
        ttk.Checkbutton(frame, text="完成后尝试打开 Codex App，并按授权临时打开 OpenAI 官网访问窗口", variable=self.open_app).pack(
            anchor="w"
        )

        actions = tk.Frame(frame, bg=CARD_BG)
        actions.pack(fill="x", pady=(14, 0))

        primary_actions = tk.Frame(actions, bg=CARD_BG)
        primary_actions.pack(fill="x")
        self.deploy_button = self._button(primary_actions, "开始一键部署", self.start_deploy, "success")
        self.deploy_button.pack(side="left")
        self.config_button = self._button(primary_actions, "仅修复 Codex 配置", self.start_config_only, "primary")
        self.config_button.pack(side="left", padx=(10, 0))
        self.restore_button = self._button(primary_actions, "恢复最近备份", self.restore_backups, "secondary")
        self.restore_button.pack(side="left", padx=(10, 0))

        utility_actions = tk.Frame(actions, bg=CARD_BG)
        utility_actions.pack(fill="x", pady=(10, 0))
        self._button(utility_actions, "复制日志", self.copy_logs, "secondary").pack(side="left")
        self._button(utility_actions, "打开工作区", self.open_workspace, "secondary").pack(side="left", padx=(10, 0))
        self._button(utility_actions, "打开配置目录", self.open_config_dir, "secondary").pack(side="left", padx=(10, 0))

        help_box = tk.Frame(frame, bg="#f5f8fb", padx=12, pady=8, highlightthickness=1, highlightbackground=BORDER)
        help_box.pack(fill="x", pady=(14, 0))
        tk.Label(
            help_box,
            text=(
                "提示：首次安装用“一键部署”；只换 Key 或配置损坏用“仅修复”；撤回写入用“恢复备份”；"
                "如果账号被授权临时访问 OpenAI 官网，打开 Codex 后会自动启用 10 分钟，到点恢复。"
            ),
            bg="#f5f8fb",
            fg=MUTED,
            wraplength=760,
            justify="left",
        ).pack(anchor="w")

    def refresh_steps(self) -> None:
        for idx, frame in self.step_frames.items():
            if idx == self.step.get():
                frame.lift()
        for idx, button in getattr(self, "step_buttons", {}).items():
            active = idx == self.step.get()
            button.configure(
                bg=PRIMARY if active else PRIMARY_DARK,
                fg="#ffffff" if active else "#c8f3ea",
                activebackground=PRIMARY,
                activeforeground="#ffffff",
            )

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

    def log_from_worker(self, message: str) -> None:
        self.root.after(0, lambda: self.log(message))

    def set_status_from_worker(self, message: str) -> None:
        self.root.after(0, lambda: self.status.set(message))

    def show_info_from_worker(self, title: str, message: str) -> None:
        self.root.after(0, lambda: messagebox.showinfo(title, message))

    def show_warning_from_worker(self, title: str, message: str) -> None:
        self.root.after(0, lambda: messagebox.showwarning(title, message))

    def show_error_from_worker(self, title: str, message: str) -> None:
        self.root.after(0, lambda: messagebox.showerror(title, message))

    def set_busy(self, busy: bool) -> None:
        self.worker_running = busy
        state = "disabled" if busy else "normal"
        for button in (self.login_button, self.deploy_button, self.config_button, self.restore_button, self.update_button):
            button.configure(state=state)

    def current_key_signature(self) -> tuple[str, str, str, bool]:
        return (
            self.api_key.get().strip(),
            self.base_url.get().strip(),
            self.model.get().strip(),
            self.skip_test.get(),
        )

    def mark_key_dirty(self, *_args) -> None:
        if self.saved_key_ok or self.saved_key_signature:
            self.saved_key_ok = False
            self.saved_key_signature = None
            self.status.set("状态：Key 已修改，请重新保存")

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
            self.root.after(0, lambda: self.user_label.configure(text=f"已登录：{display_username}"))
            self.root.after(0, self.show_wizard)
            self.set_status_from_worker("状态：已登录，请按步骤部署")
        finally:
            self.root.after(0, lambda: self.set_busy(False))

    def start_update_check(self) -> None:
        if self.worker_running:
            return
        self.set_busy(True)
        self.status.set("状态：正在检查更新...")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self) -> None:
        try:
            ok, msg, path, release_url = check_and_download_update(self.log_from_worker)
            self.log_from_worker(msg)
            if ok and path:
                self.set_status_from_worker("状态：更新包已下载")
                self.root.after(0, lambda: open_path(path.parent))
                self.show_info_from_worker("更新已下载", f"{msg}\n\n位置：{path}")
            elif release_url and "未找到" in msg and "更新包" in msg:
                self.set_status_from_worker("状态：发现新版本，请到发布页下载")
                self.root.after(0, lambda: open_url(release_url))
                self.show_warning_from_worker("发现新版本", msg)
            elif "当前已是最新版本" in msg:
                self.set_status_from_worker("状态：当前已是最新版本")
                self.show_info_from_worker("检查更新", msg)
            else:
                self.set_status_from_worker("状态：检查更新失败")
                self.show_warning_from_worker("检查更新", msg)
        finally:
            self.root.after(0, lambda: self.set_busy(False))

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
        base_url = self.base_url.get()
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        self.set_busy(True)
        self.status.set("状态：正在测试 API Key...")
        threading.Thread(target=self._save_key_worker, args=(api_key, base_url, model, skip_test, open_app), daemon=True).start()

    def _save_key_worker(self, api_key: str, base_url: str, model: str, skip_test: bool, open_app: bool) -> None:
        try:
            if not api_key.strip():
                raise ValueError("请先填写胖虎AI API Key。")
            if skip_test:
                ok, msg = True, "已保存 Key，接口测试被跳过。"
            else:
                ok, msg = test_api(base_url, api_key)
            self.log_from_worker(msg)
            self.saved_key_ok = ok
            if ok:
                self.saved_key_signature = (api_key.strip(), base_url.strip(), model.strip(), skip_test)
                save_profile_data(
                    {
                        "api_key": api_key.strip(),
                        "base_url": base_url.strip(),
                        "model": model.strip(),
                        "skip_test": skip_test,
                        "open_app": open_app,
                    }
                )
                self.set_status_from_worker("状态：Key 已保存")
                self.root.after(0, lambda: self.step.set(2))
                self.root.after(0, self.refresh_steps)
            else:
                self.set_status_from_worker("状态：Key 测试失败")
                self.show_warning_from_worker("Key 测试失败", msg)
        except Exception as exc:
            self.set_status_from_worker("状态：Key 保存失败")
            self.show_error_from_worker("Key 保存失败", str(exc))
        finally:
            self.root.after(0, lambda: self.set_busy(False))

    def run_environment_check(self) -> None:
        lines = detect_environment()
        self.env_text.configure(state="normal")
        self.env_text.delete("1.0", "end")
        self.env_text.insert("end", "\n".join(lines))
        self.env_text.configure(state="disabled")
        for line in lines:
            self.log(line)
        self.status.set("状态：环境检测完成")

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
        selected = self.selected_agents()
        if not selected:
            messagebox.showwarning("请选择 Agent", "请至少选择一个 Agent。")
            return
        if not self.validate_system_and_risk_plugins():
            return
        user = dict(self.logged_in_user or {})
        deployer_auth = dict(self.deployer_auth or {})
        api_key = self.api_key.get()
        base_url = self.base_url.get()
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
        ok, _current_key_signature = self.validate_config_ready()
        if not ok:
            return
        if not self.validate_system_and_risk_plugins():
            return
        user = dict(self.logged_in_user or {})
        deployer_auth = dict(self.deployer_auth or {})
        api_key = self.api_key.get()
        base_url = self.base_url.get()
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        self.set_busy(True)
        self.status.set("状态：正在修复 Codex 配置...")
        threading.Thread(
            target=self._config_only_worker,
            args=(user, deployer_auth, api_key, base_url, model, skip_test, open_app),
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
            )
            if ok:
                self.set_status_from_worker("状态：Codex 配置修复完成")
                self.show_info_from_worker("配置完成", "Codex 配置已重新写入，不会重新安装 Agent。")
            else:
                self.set_status_from_worker("状态：Codex 配置测试失败，已恢复备份")
                self.show_warning_from_worker("配置测试失败", "配置写入后接口测试失败，已自动恢复备份。请检查 Key、余额或网络。")
        except Exception as exc:
            self.set_status_from_worker("状态：Codex 配置修复失败")
            self.log_from_worker(f"Codex 配置修复失败：{exc}")
            self.show_error_from_worker("配置修复失败", str(exc))
        finally:
            self.root.after(0, lambda: self.set_busy(False))

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
            self.log_from_worker("开始一键部署：" + "、".join(f"{a.name}/{m}" for a, m in selected))
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
            self.root.after(0, lambda: self.set_busy(False))

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
    assert APP_VERSION == "1.0.12"
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
    assert "experimental_bearer_token" not in config
    auth = json.loads(build_auth_json("", "sk-test"))
    assert list(auth.keys()) == ["OPENAI_API_KEY"]
    assert auth["OPENAI_API_KEY"] == "sk-test"
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

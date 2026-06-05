import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


APP_NAME = "胖虎AI Codex 一键安装工具"
DEFAULT_BASE_URL = "https://aitokenapi.cc"
DEFAULT_MODEL = "gpt-5.5"
CODEX_WINDOWS_STORE_URL = "https://get.microsoft.com/installer/download/9PLM9XGG6VKS?cid=website_cta_psi"
CODEX_DOWNLOAD_URL = "https://developers.openai.com/codex/"
OFFICIAL_PACKAGE_SUFFIXES = (".msixbundle", ".msix", ".appx", ".appxbundle", ".appinstaller")
PANGHU_AGENTS_START = "<!-- PANGHUAI_CODEX_RULES_START -->"
PANGHU_AGENTS_END = "<!-- PANGHUAI_CODEX_RULES_END -->"


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return "******"
    return f"{value[:6]}...{value[-4:]}"


def codex_home() -> Path:
    return Path.home() / ".codex"


def workspace_root() -> Path:
    return Path.home() / "Documents" / "胖虎AI-Codex工作区"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def codex_command_exists() -> tuple[bool, str]:
    exe = shutil.which("codex")
    if not exe:
        return False, ""
    try:
        result = subprocess.run(
            ["codex", "--version"],
            text=True,
            capture_output=True,
            timeout=8,
        )
        version = (result.stdout or result.stderr).strip()
        return True, version
    except Exception:
        return True, ""


def codex_app_package_exists() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, ""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1 -ExpandProperty PackageFullName",
            ],
            text=True,
            capture_output=True,
            timeout=12,
        )
        package = (result.stdout or "").strip()
        return bool(package), package
    except Exception:
        return False, ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    safe_base_url = toml_escape(base_url.rstrip("/"))
    safe_model = toml_escape(model)
    safe_api_key = toml_escape(api_key)
    safe_workspace = str(workspace_root()).lower().replace("\\", "\\\\")
    return f'''model_provider = "panghuai"
model = "{safe_model}"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "workspace-write"

[model_providers.panghuai]
name = "胖虎AI中转"
base_url = "{safe_base_url}"
wire_api = "responses"
experimental_bearer_token = "{safe_api_key}"
requires_openai_auth = true

[projects.'{safe_workspace}']
trust_level = "trusted"

[desktop]
appearanceTheme = "dark"
conversationDetailMode = "STEPS_PROSE"
'''


def chinese_rules() -> str:
    return """# 胖虎AI Codex 客户默认规则

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
    if not existing.strip():
        return build_config(api_key, base_url, model)

    safe_base_url = toml_escape(base_url.rstrip("/"))
    safe_model = toml_escape(model)
    safe_api_key = toml_escape(api_key)
    safe_workspace = str(workspace_root()).lower().replace("\\", "\\\\")
    lines = existing.splitlines()
    lines = remove_sections(lines, {"model_providers.panghuai", f"projects.'{safe_workspace}'"})
    lines = update_top_level_keys(
        lines,
        [
            'model_provider = "panghuai"',
            f'model = "{safe_model}"',
            'model_reasoning_effort = "medium"',
            'approval_policy = "never"',
            'sandbox_mode = "workspace-write"',
        ],
        {"model_provider", "model", "model_reasoning_effort", "approval_policy", "sandbox_mode"},
    )
    lines = update_or_append_section(
        lines,
        "desktop",
        ['appearanceTheme = "dark"', 'conversationDetailMode = "STEPS_PROSE"'],
        {"appearanceTheme", "conversationDetailMode"},
    )
    while lines and not lines[-1].strip():
        lines.pop()
    lines.extend(
        [
            "",
            "[model_providers.panghuai]",
            'name = "胖虎AI中转"',
            f'base_url = "{safe_base_url}"',
            'wire_api = "responses"',
            f'experimental_bearer_token = "{safe_api_key}"',
            "requires_openai_auth = true",
            "",
            f"[projects.'{safe_workspace}']",
            'trust_level = "trusted"',
        ]
    )
    return "\n".join(lines) + "\n"


def test_api(base_url: str, api_key: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/v1/models"
    req = Request(url, headers={"Authorization": f"Bearer {api_key}"}, method="GET")
    try:
        with urlopen(req, timeout=20) as resp:
            return True, f"接口连通正常：HTTP {resp.status}"
    except HTTPError as exc:
        return False, f"接口返回错误：HTTP {exc.code}"
    except URLError as exc:
        return False, f"接口连接失败：{exc.reason}"
    except Exception as exc:
        return False, f"接口测试失败：{exc}"


def open_path(path: Path) -> None:
    if platform.system() == "Windows":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_codex_download_page() -> None:
    if platform.system() == "Windows":
        webbrowser.open(CODEX_WINDOWS_STORE_URL)
    else:
        webbrowser.open(CODEX_DOWNLOAD_URL)


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
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return False, f"签名校验失败：{detail or f'退出码 {result.returncode}'}"
    try:
        data = json.loads((result.stdout or "").strip())
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
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", install_command],
        text=True,
        capture_output=True,
        timeout=600,
    )
    if result.returncode == 0:
        return True, "官方离线包安装命令已完成。"
    detail = (result.stderr or result.stdout or "").strip()
    return False, f"官方离线包安装失败：{detail or f'退出码 {result.returncode}'}"


def install_with_winget() -> tuple[bool, str]:
    if not shutil.which("winget"):
        return False, "未检测到 winget，无法自动调用 Microsoft Store 命令行安装。"
    result = subprocess.run(
        [
            "winget",
            "install",
            "Codex",
            "-s",
            "msstore",
            "--accept-source-agreements",
            "--accept-package-agreements",
        ],
        text=True,
        capture_output=True,
        timeout=900,
    )
    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode == 0:
        return True, "Microsoft Store 命令行安装已完成。"
    return False, f"winget 安装失败：{output or f'退出码 {result.returncode}'}"


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
                details = []
                if version:
                    details.append(version)
                if package:
                    details.append(package)
                return True, "已检测到 Codex Windows App 本体：" + ("；".join(details) if details else "已安装")
        elif cli_ok or package_ok:
            details = []
            if version:
                details.append(version)
            if package:
                details.append(package)
            return True, "已检测到 Codex：" + ("；".join(details) if details else "已安装")
        time.sleep(3)
    detail = last_version or last_package
    return False, f"等待 Codex 安装完成超时。{detail}".strip()


def install_codex_app(log) -> bool:
    log("开始检测 Codex 本体。")
    cli_ok, version = codex_command_exists()
    package_ok, package = codex_app_package_exists()
    if package_ok:
        if cli_ok:
            log(f"已检测到 Codex CLI：{version or '已安装'}")
        log(f"已检测到 Codex Windows App 本体：{package}")
        return True
    if cli_ok:
        log(f"已检测到 Codex CLI：{version or '已安装'}")
        if platform.system() == "Windows":
            log("未检测到 Codex Windows App 本体，将继续安装/修复 App。")
        else:
            return True

    if platform.system() != "Windows":
        log("当前系统暂不支持自动安装 Codex 本体，请从官方入口手动安装。")
        open_codex_download_page()
        return False

    package_path = find_official_codex_package()
    if package_path:
        log(f"发现官方离线包：{package_path}")
        signature_ok, signature_msg = validate_official_package_signature(package_path)
        log(signature_msg)
        if not signature_ok:
            log("离线包未通过签名校验，将尝试 Microsoft Store 命令行安装。")
            package_path = None
    if package_path:
        ok, msg = install_official_package(package_path)
        log(msg)
        if ok:
            ready, ready_msg = wait_for_codex_ready(require_windows_app=True)
            log(ready_msg)
            return ready
        log("离线包安装失败，将尝试 Microsoft Store 命令行安装。")
    else:
        log("未发现官方离线包，将尝试 Microsoft Store 命令行安装。")
        log("可把官方签名的 Codex 安装包放在本工具同目录、offline 或 codex-official 文件夹。")

    ok, msg = install_with_winget()
    log(msg)
    if ok:
        ready, ready_msg = wait_for_codex_ready(require_windows_app=True)
        log(ready_msg)
        return ready

    log("自动安装失败，已打开官方 Codex 下载页，请按页面提示安装。")
    open_codex_download_page()
    return False


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
    global_agents = home / "AGENTS.md"
    workspace_agents = workdir / "AGENTS.md"

    log("开始配置胖虎AI Codex。")

    exists, version = codex_command_exists()
    if exists:
        log(f"已检测到 Codex：{version or '已安装'}")
    else:
        log("未检测到 codex 命令。配置仍会写入，稍后安装 Codex App 后可继续使用。")

    home.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)
    log(f"配置目录：{home}")
    log(f"默认工作区：{workdir}")

    existed_before = {
        config_path: config_path.exists(),
        global_agents: global_agents.exists(),
        workspace_agents: workspace_agents.exists(),
    }
    backups = {
        config_path: backup_file(config_path),
        global_agents: backup_file(global_agents),
        workspace_agents: backup_file(workspace_agents),
    }
    if backups[config_path]:
        log(f"已备份旧配置：{backups[config_path]}")
    else:
        log("未发现旧配置，将创建新配置。")
    for agents_path in (global_agents, workspace_agents):
        if backups[agents_path]:
            log(f"已备份旧中文规则文件：{backups[agents_path]}")

    old_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    write_text(config_path, merge_config(old_config, api_key, base_url, model))
    for agents_path in (global_agents, workspace_agents):
        old_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
        write_text(agents_path, merge_agents_rules(old_agents))
    log(f"已写入 Codex 配置：{config_path}")
    log(f"接口地址：{base_url}")
    log(f"模型：{model}")
    log(f"Key：{mask_key(api_key)}")
    log("已写入中文回答规则。")

    ok = True
    if skip_test:
        log("已跳过接口测试。")
    else:
        log("正在测试胖虎AI接口...")
        ok, msg = test_api(base_url, api_key)
        log(msg)
        if not ok:
            log("常见原因：Key 填错、余额不足、客户网络不通、后台账号池未分配。")
            for target, backup in backups.items():
                restore_backup(target, backup, existed_before[target])
            log("接口测试失败，已自动恢复本次写入前的配置备份。")

    if open_app:
        _, msg = open_codex_app(workdir)
        log(msg)

    log(f"配置完成。以后请使用工作区：{workdir}")
    return ok


class InstallerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(APP_NAME)
        root.geometry("820x660")
        root.minsize(760, 600)
        root.configure(bg="#f8fafc")

        self.api_key = tk.StringVar()
        self.base_url = tk.StringVar(value=DEFAULT_BASE_URL)
        self.model = tk.StringVar(value=DEFAULT_MODEL)
        self.show_key = tk.BooleanVar(value=False)
        self.skip_test = tk.BooleanVar(value=False)
        self.open_app = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="状态：等待配置")
        self.worker_running = False

        self._build_ui()
        self.log("请粘贴胖虎AI API Key，然后点击“一键配置”。")
        self.log("如客户还没装 Codex，可先点“安装/修复 Codex 本体”。")
        self.log(f"默认接口：{DEFAULT_BASE_URL}")
        self.log(f"默认模型：{DEFAULT_MODEL}")

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 11, "bold"))

        container = tk.Frame(self.root, bg="#f8fafc", padx=28, pady=24)
        container.pack(fill="both", expand=True)

        title = tk.Label(
            container,
            text=APP_NAME,
            font=("Microsoft YaHei UI", 22, "bold"),
            fg="#0f172a",
            bg="#f8fafc",
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            container,
            text="输入胖虎AI API Key，自动配置 Codex 中转、默认工作区和中文回答规则。",
            font=("Microsoft YaHei UI", 10),
            fg="#475569",
            bg="#f8fafc",
        )
        subtitle.pack(anchor="w", pady=(6, 22))

        key_row = tk.Frame(container, bg="#f8fafc")
        key_row.pack(fill="x")
        tk.Label(key_row, text="胖虎AI API Key", bg="#f8fafc", fg="#0f172a").pack(anchor="w")
        key_input_row = tk.Frame(key_row, bg="#f8fafc")
        key_input_row.pack(fill="x", pady=(6, 14))
        self.key_entry = ttk.Entry(key_input_row, textvariable=self.api_key, show="*")
        self.key_entry.pack(side="left", fill="x", expand=True)
        ttk.Checkbutton(
            key_input_row,
            text="显示",
            variable=self.show_key,
            command=self.toggle_key,
        ).pack(side="left", padx=(10, 0))

        fields = tk.Frame(container, bg="#f8fafc")
        fields.pack(fill="x")

        base_frame = tk.Frame(fields, bg="#f8fafc")
        base_frame.pack(side="left", fill="x", expand=True, padx=(0, 18))
        tk.Label(base_frame, text="接口地址", bg="#f8fafc", fg="#0f172a").pack(anchor="w")
        ttk.Entry(base_frame, textvariable=self.base_url).pack(fill="x", pady=(6, 14))

        model_frame = tk.Frame(fields, bg="#f8fafc", width=220)
        model_frame.pack(side="left", fill="x")
        tk.Label(model_frame, text="模型", bg="#f8fafc", fg="#0f172a").pack(anchor="w")
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model,
            values=["gpt-5.5", "gpt-5.4", "gpt-4.1"],
        )
        model_combo.pack(fill="x", pady=(6, 14))

        checks = tk.Frame(container, bg="#f8fafc")
        checks.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(checks, text="跳过接口测试", variable=self.skip_test).pack(side="left")
        ttk.Checkbutton(checks, text="配置完成后打开 Codex App", variable=self.open_app).pack(
            side="left", padx=(24, 0)
        )

        buttons = tk.Frame(container, bg="#f8fafc")
        buttons.pack(fill="x", pady=(4, 14))
        self.install_button = ttk.Button(
            buttons,
            text="一键配置",
            style="Primary.TButton",
            command=self.start_install,
        )
        self.install_button.pack(side="left", ipadx=20, ipady=7)
        self.codex_app_button = ttk.Button(
            buttons,
            text="安装/修复 Codex 本体",
            command=self.start_codex_app_install,
        )
        self.codex_app_button.pack(side="left", padx=(14, 0), ipadx=12, ipady=7)
        ttk.Button(buttons, text="打开官方下载页", command=open_codex_download_page).pack(
            side="left", padx=(14, 0), ipadx=12, ipady=7
        )

        file_buttons = tk.Frame(container, bg="#f8fafc")
        file_buttons.pack(fill="x", pady=(0, 14))
        ttk.Button(file_buttons, text="打开工作区", command=self.open_workspace).pack(
            side="left", padx=(14, 0), ipadx=12, ipady=7
        )
        ttk.Button(file_buttons, text="打开配置目录", command=self.open_config_dir).pack(
            side="left", padx=(14, 0), ipadx=12, ipady=7
        )
        self.restore_button = ttk.Button(file_buttons, text="恢复最近备份", command=self.restore_backups)
        self.restore_button.pack(side="left", padx=(14, 0), ipadx=12, ipady=7)
        ttk.Button(file_buttons, text="复制日志", command=self.copy_logs).pack(
            side="left", padx=(14, 0), ipadx=12, ipady=7
        )

        note = tk.Label(
            container,
            text="提示：本工具只安装官方签名 Codex 或打开官方入口；不内置、修改或伪装 Codex 本体文件。",
            font=("Microsoft YaHei UI", 9),
            fg="#64748b",
            bg="#f8fafc",
        )
        note.pack(anchor="w", pady=(0, 8))

        self.log_box = tk.Text(
            container,
            height=13,
            bg="#ffffff",
            fg="#0f172a",
            relief="solid",
            borderwidth=1,
            wrap="word",
            font=("Consolas", 10),
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

        tk.Label(
            container,
            textvariable=self.status,
            bg="#f8fafc",
            fg="#475569",
        ).pack(anchor="w", pady=(10, 0))

    def toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key.get() else "*")

    def log(self, message: str) -> None:
        now = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{now}] {message}\n")
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
        self.install_button.configure(state=state)
        self.codex_app_button.configure(state=state)
        self.restore_button.configure(state=state)

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

    def start_install(self) -> None:
        if self.worker_running:
            return
        self.set_busy(True)
        self.status.set("状态：正在配置...")
        thread = threading.Thread(target=self._install_worker, daemon=True)
        thread.start()

    def start_codex_app_install(self) -> None:
        if self.worker_running:
            return
        self.set_busy(True)
        self.status.set("状态：正在安装/检测 Codex 本体...")
        thread = threading.Thread(target=self._codex_app_install_worker, daemon=True)
        thread.start()

    def _install_worker(self) -> None:
        try:
            ok = install_codex_config(
                self.api_key.get(),
                self.base_url.get(),
                self.model.get(),
                self.skip_test.get(),
                self.open_app.get(),
                self.log_from_worker,
            )
            self.set_status_from_worker("状态：配置完成")
            if ok:
                self.show_info_from_worker("胖虎AI Codex", "配置完成。以后请使用：文档/胖虎AI-Codex工作区")
            else:
                self.show_warning_from_worker(
                    "胖虎AI Codex",
                    "配置已写入，但接口测试失败。请根据日志检查 Key、余额、网络或后台账号池。",
                )
        except Exception as exc:
            self.set_status_from_worker("状态：配置失败")
            self.log_from_worker(f"配置失败：{exc}")
            self.show_error_from_worker("配置失败", str(exc))
        finally:
            self.root.after(0, lambda: self.set_busy(False))

    def _codex_app_install_worker(self) -> None:
        try:
            ok = install_codex_app(self.log_from_worker)
            if ok:
                self.set_status_from_worker("状态：Codex 本体已就绪")
                self.show_info_from_worker("Codex 本体", "Codex 已安装或已检测到。现在可以继续一键配置胖虎AI。")
            else:
                self.set_status_from_worker("状态：Codex 本体需要手动处理")
                self.show_warning_from_worker(
                    "Codex 本体",
                    "自动安装未完成。已打开官方入口，请按日志提示继续安装。",
                )
        except Exception as exc:
            self.set_status_from_worker("状态：Codex 本体安装失败")
            self.log_from_worker(f"Codex 本体安装失败：{exc}")
            self.show_error_from_worker("Codex 本体安装失败", str(exc))
        finally:
            self.root.after(0, lambda: self.set_busy(False))


def main() -> int:
    if "--self-test" in sys.argv:
        print("UI self-test OK")
        return 0
    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

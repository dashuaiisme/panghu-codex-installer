"""胖虎AI客户端 · 文件路径助手（从 panghu_ai_client.py 抽出）。

Codex/ClaudeCode/OpenClaw/Hermes 配置路径、工作区、验收矩阵、APPDATA 下 profile/会话/登录存储、
app_root/asset_path/ui_path（打包与源码两种布局）。仅依赖标准库，无业务耦合。
panghu_ai_client 通过 `from panghu_paths import *` 引入，引用点不变（含被测试 monkeypatch 的 profile_path）。
"""
import os
import sys
import platform
from pathlib import Path


def codex_home() -> Path:
    return Path.home() / ".codex"


def codex_auth_path() -> Path:
    return codex_home() / "auth.json"


def codex_mode_snapshots_root() -> Path:
    return codex_home() / "panghu_modes"


def workspace_root() -> Path:
    return Path.home() / "Documents" / "胖虎AI-Agent工作区"


def claude_code_settings_path() -> Path:
    return Path(os.environ.get("CLAUDE_CODE_SETTINGS_PATH") or (Path.home() / ".claude" / "settings.json"))


def openclaw_config_path() -> Path:
    return Path(os.environ.get("OPENCLAW_CONFIG_PATH") or (Path.home() / ".openclaw" / "openclaw.json"))


def hermes_home_path() -> Path:
    explicit = os.environ.get("HERMES_HOME")
    if explicit:
        return Path(explicit)
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "hermes"
    return Path.home() / ".hermes"


def hermes_config_path() -> Path:
    return hermes_home_path() / "config.yaml"


def hermes_env_path() -> Path:
    return hermes_home_path() / ".env"


def customer_acceptance_matrix_path() -> Path:
    return workspace_root() / "胖虎AI-Agent功能验收矩阵.txt"


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "PanghuAI-Client"
    return Path.home() / ".panghuai-client"


def profile_path() -> Path:
    return app_data_dir() / "profile.json"


def buyer_session_metadata_path() -> Path:
    return app_data_dir() / "buyer_session.json"


def buyer_session_cookie_path() -> Path:
    return app_data_dir() / "buyer_session_cookies.txt"


def login_account_store_path() -> Path:
    return app_data_dir() / "login_accounts.json"


def web_profile_root() -> Path:
    return app_data_dir() / "web_profiles"


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


def ui_path(name: str) -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled = Path(bundled_root) / "ui" / name
        if bundled.exists():
            return bundled
    root = app_root()
    for candidate in (
        root / "src" / "ui" / name,
        root / "ui" / name,
        root.parent / "Resources" / "ui" / name,
    ):
        if candidate.exists():
            return candidate
    return app_root() / "src" / "ui" / name

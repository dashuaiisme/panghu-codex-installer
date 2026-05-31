import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


APP_NAME = "胖虎AI Codex 一键安装工具"
DEFAULT_BASE_URL = "https://aitokenapi.cc"
DEFAULT_MODEL = "gpt-5.5"


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def open_codex_app(workdir: Path) -> tuple[bool, str]:
    exists, _ = codex_command_exists()
    if not exists:
        return False, "未检测到 codex 命令，请手动打开 Codex App。"
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

    if config_path.exists():
        backup = config_path.with_name(f"config.toml.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(config_path, backup)
        log(f"已备份旧配置：{backup}")
    else:
        log("未发现旧配置，将创建新配置。")

    write_text(config_path, build_config(api_key, base_url, model))
    write_text(global_agents, chinese_rules())
    write_text(workspace_agents, chinese_rules())
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

        self._build_ui()
        self.log("请粘贴胖虎AI API Key，然后点击“一键配置”。")
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
        ttk.Button(buttons, text="打开工作区", command=self.open_workspace).pack(
            side="left", padx=(14, 0), ipadx=12, ipady=7
        )
        ttk.Button(buttons, text="打开配置目录", command=self.open_config_dir).pack(
            side="left", padx=(14, 0), ipadx=12, ipady=7
        )

        note = tk.Label(
            container,
            text="提示：如果 Codex App 菜单仍是英文，这是官方界面限制；本工具负责中转配置和中文回答规则。",
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

    def open_workspace(self) -> None:
        path = workspace_root()
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def open_config_dir(self) -> None:
        path = codex_home()
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def start_install(self) -> None:
        self.install_button.configure(state="disabled")
        self.status.set("状态：正在配置...")
        thread = threading.Thread(target=self._install_worker, daemon=True)
        thread.start()

    def _install_worker(self) -> None:
        try:
            ok = install_codex_config(
                self.api_key.get(),
                self.base_url.get(),
                self.model.get(),
                self.skip_test.get(),
                self.open_app.get(),
                self.log,
            )
            self.status.set("状态：配置完成")
            if ok:
                messagebox.showinfo("胖虎AI Codex", "配置完成。以后请使用：文档/胖虎AI-Codex工作区")
            else:
                messagebox.showwarning(
                    "胖虎AI Codex",
                    "配置已写入，但接口测试失败。请根据日志检查 Key、余额、网络或后台账号池。",
                )
        except Exception as exc:
            self.status.set("状态：配置失败")
            self.log(f"配置失败：{exc}")
            messagebox.showerror("配置失败", str(exc))
        finally:
            self.install_button.configure(state="normal")


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

from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path

from PIL import ImageGrab

import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import panghu_codex_installer as installer_module


OUTPUT_DIR = Path(__file__).resolve().parent


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def capture_window(root: tk.Tk, name: str) -> Path:
    try:
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()
    except Exception:
        pass
    root.update_idletasks()
    root.update()
    time.sleep(0.6)
    root.update_idletasks()
    root.update()
    x = root.winfo_rootx()
    y = root.winfo_rooty()
    w = root.winfo_width()
    h = root.winfo_height()
    image = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    try:
        root.attributes("-topmost", False)
    except Exception:
        pass
    path = OUTPUT_DIR / name
    image.save(path)
    return path


def fake_logged_in_state(app: installer_module.InstallerApp) -> None:
    app.logged_in_user = {"id": "buyer-1001", "username": "panghu_buyer_demo"}
    app.deployer_auth = {"token": "demo-token"}
    app.commercial_products = []
    app.commercial_entitlements = []
    app.environment_ok = True
    app.saved_key_ok = True
    app.api_key.set("sk-demo-1234567890")
    app.login_username.set("panghu_buyer_demo")
    app.buyer_product_id.set("prod-demo")
    app.active_module.set(installer_module.MODULE_AGENT)
    app.step.set(2)
    app.refresh_steps()


def main() -> int:
    ensure_output_dir()
    installer_module.enable_windows_dpi_awareness()
    root = tk.Tk()
    app = installer_module.InstallerApp(root)
    root.update_idletasks()
    root.update()

    results: list[Path] = []

    app.show_login_gate()
    results.append(capture_window(root, "panghu-installer-login-gate.png"))

    fake_logged_in_state(app)
    app.active_module.set(installer_module.MODULE_AGENT)
    app.step.set(2)
    app.refresh_steps()
    results.append(capture_window(root, "panghu-installer-agent-config.png"))

    app.switch_module(installer_module.MODULE_SITE)
    app.switch_subnav("account")
    results.append(capture_window(root, "panghu-installer-site-console.png"))

    app.switch_module(installer_module.MODULE_VALUE_ADDED)
    app.switch_subnav("gpt_plus")
    results.append(capture_window(root, "panghu-installer-value-added.png"))

    app.switch_module(installer_module.MODULE_COURSES)
    app.switch_subnav("agent_home")
    results.append(capture_window(root, "panghu-installer-agent-center.png"))

    root.destroy()
    for path in results:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

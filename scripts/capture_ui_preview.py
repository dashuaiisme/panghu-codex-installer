from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
HTML = ROOT / "src" / "ui" / "index.html"


def file_url(path: Path, query: str = "") -> str:
    # Resolve absolute path to file:// URL. Note that relative resource paths
    # (e.g. "../../assets/panghu-avatar-64.png") in index.html are preserved
    # and correctly loaded relative to the file URL by the webview.
    url = "file:///" + quote(str(path.resolve()).replace("\\", "/"), safe="/:._-")
    return f"{url}?{query}" if query else url


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def playwright_cmd() -> str:
    cmd = shutil.which("npx.cmd") or shutil.which("npx")
    if not cmd:
        raise RuntimeError("未找到 npx，无法调用 Playwright 截图。")
    return cmd


def capture(url: str, output_name: str, viewport: str = "2048,1152") -> Path:
    out = OUTPUT_DIR / output_name
    selector = "#consoleLayout" if "preview=agent" in url else "#loginGate"
    cmdline = (
        f'"{playwright_cmd()}" playwright screenshot --viewport-size={viewport} '
        f'--wait-for-selector "{selector}" '
        f'"{url}" "{out}"'
    )
    subprocess.run(cmdline, cwd=ROOT, check=True, shell=True)
    return out


def main() -> int:
    ensure_output_dir()
    if not HTML.exists():
        raise FileNotFoundError(f"前端入口不存在：{HTML}")

    captures = [
        (file_url(HTML), "panghu-installer-login-gate.png", "2048,1152"),
        (file_url(HTML, "preview=agent&step=2"), "panghu-installer-agent-config.png", "2048,1152"),
        (
            file_url(HTML, "preview=agent&step=2&module=site&subnav=account"),
            "panghu-installer-site-console.png",
            "2048,1152",
        ),
        (
            file_url(HTML, "preview=agent&step=2&module=value_added&subnav=gpt_plus"),
            "panghu-installer-value-added.png",
            "2048,1152",
        ),
        (
            file_url(HTML, "preview=agent&step=2&module=courses&subnav=agent_home"),
            "panghu-installer-agent-center.png",
            "2048,1152",
        ),
        (
            file_url(HTML, "preview=agent&step=2"),
            "panghu-installer-agent-config-1365.png",
            "1365,768",
        ),
    ]

    results = [capture(url, name, vp) for url, name, vp in captures]
    for path in results:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

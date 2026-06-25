from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent
HTML = ROOT / "src" / "ui" / "index.html"


def file_url(path: Path, query: str = "") -> str:
    url = "file:///" + quote(str(path.resolve()).replace("\\", "/"), safe="/:._-")
    return f"{url}?{query}" if query else url


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def playwright_cmd() -> str:
    cmd = shutil.which("npx.cmd") or shutil.which("npx")
    if not cmd:
        raise RuntimeError("未找到 npx，无法调用 Playwright 截图。")
    return cmd


def capture(url: str, output_name: str) -> Path:
    out = OUTPUT_DIR / output_name
    cmdline = (
        f'"{playwright_cmd()}" playwright screenshot --viewport-size=2048,1152 '
        f'"{url}" "{out}"'
    )
    subprocess.run(cmdline, cwd=ROOT, check=True, shell=True)
    return out


def main() -> int:
    ensure_output_dir()
    if not HTML.exists():
        raise FileNotFoundError(f"前端入口不存在：{HTML}")

    captures = [
        (file_url(HTML), "panghu-installer-login-gate.png"),
        (file_url(HTML, "preview=agent&step=2"), "panghu-installer-agent-config.png"),
        (
            file_url(HTML, "preview=agent&step=2&module=site&subnav=account"),
            "panghu-installer-site-console.png",
        ),
        (
            file_url(HTML, "preview=agent&step=2&module=value_added&subnav=gpt_plus"),
            "panghu-installer-value-added.png",
        ),
        (
            file_url(HTML, "preview=agent&step=2&module=courses&subnav=agent_home"),
            "panghu-installer-agent-center.png",
        ),
    ]

    results = [capture(url, name) for url, name in captures]
    for path in results:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

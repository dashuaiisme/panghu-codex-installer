import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import panghu_codex_installer as installer  # noqa: E402


CUSTOMER_WEB_FLOW_MODULES = {
    installer.MODULE_SITE,
    installer.MODULE_VALUE_ADDED,
    installer.MODULE_COURSES,
}
LOCAL_ACCEPTANCE_INVITE_CODE = "LOCAL-ACCEPTANCE"


def public_customer_domain_allowed(url: str) -> bool:
    parsed = urlparse(url)
    public_host = urlparse(installer.DEFAULT_BASE_URL).hostname or ""
    host = parsed.hostname or ""
    return parsed.scheme == "https" and (host == public_host or host.endswith(f".{public_host}"))


def page_entry_status(page: dict[str, object], runtime_webview_loaded: bool) -> tuple[str, list[str]]:
    gaps: list[str] = []
    url = str(page["url"])
    title = str(page["title"])
    requires_customer_web_flow = bool(page["requires_customer_web_flow"])

    if not public_customer_domain_allowed(url):
        gaps.append(f"{title} 不在公共域名下：{url}")
    if requires_customer_web_flow and not str(page["embedded_title"]):
        gaps.append(f"{title} 缺少内置页面标题映射：{url}")
    if requires_customer_web_flow and not runtime_webview_loaded:
        gaps.append(f"{title} 需要 customer_web_flow，但当前 pywebview runtime 未加载。")
    return ("blocked" if gaps else "ready"), gaps


def build_report() -> dict:
    runtime_webview_loaded = installer.embedded_webview_available()
    pages = []
    pages.append(
        {
            "module": "login_gate",
            "item": "register",
            "title": "登录闸口注册",
            "url": installer.build_register_url(LOCAL_ACCEPTANCE_INVITE_CODE),
            "note": "未登录客户填写代理邀请码后，通过内置浏览器打开胖虎AI网站注册页。",
            "embedded_title": installer.embedded_customer_page_title(
                installer.build_register_url(LOCAL_ACCEPTANCE_INVITE_CODE)
            ),
            "requires_customer_web_flow": True,
            "runtime_webview_loaded": runtime_webview_loaded,
        }
    )
    for module_id, page_map in installer.MODULE_PAGE_META.items():
        for item_id, (title, url, note) in page_map.items():
            requires_customer_web_flow = module_id in CUSTOMER_WEB_FLOW_MODULES
            pages.append(
                {
                    "module": module_id,
                    "item": item_id,
                    "title": title,
                    "url": url,
                    "note": note,
                    "embedded_title": installer.embedded_customer_page_title(url),
                    "requires_customer_web_flow": requires_customer_web_flow,
                    "runtime_webview_loaded": runtime_webview_loaded,
                }
            )

    report = {
        "public_domain": installer.DEFAULT_BASE_URL,
        "pywebview_importable": importlib.util.find_spec("webview") is not None,
        "runtime_webview_loaded": runtime_webview_loaded,
        "pages": pages,
        "blocking_gaps": [],
    }

    if not report["runtime_webview_loaded"]:
        report["blocking_gaps"].append(
            "当前运行环境未加载 pywebview；客户网站页面会被阻断且不打开系统浏览器，不能声明完全内置浏览器闭环。"
        )

    for page in pages:
        entry_status, page_gaps = page_entry_status(page, runtime_webview_loaded)
        page["entry_status"] = entry_status
        page["blocking_gaps"] = page_gaps
        report["blocking_gaps"].extend(page_gaps)

    report["web_entry_status"] = "blocked" if report["blocking_gaps"] else "ready"
    return report


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["blocking_gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

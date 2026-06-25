import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import panghu_codex_installer as installer  # noqa: E402


def main() -> int:
    pages = []
    for module_id, page_map in installer.MODULE_PAGE_META.items():
        for item_id, (title, url, note) in page_map.items():
            pages.append(
                {
                    "module": module_id,
                    "item": item_id,
                    "title": title,
                    "url": url,
                    "note": note,
                    "embedded_title": installer.embedded_customer_page_title(url),
                    "requires_customer_web_flow": module_id
                    in {
                        installer.MODULE_SITE,
                        installer.MODULE_VALUE_ADDED,
                        installer.MODULE_COURSES,
                    },
                }
            )

    report = {
        "public_domain": installer.DEFAULT_BASE_URL,
        "pywebview_importable": importlib.util.find_spec("webview") is not None,
        "runtime_webview_loaded": installer.embedded_webview_available(),
        "pages": pages,
        "blocking_gaps": [],
    }

    if not report["runtime_webview_loaded"]:
        report["blocking_gaps"].append(
            "当前运行环境未加载 pywebview；客户网站页面会回退到系统浏览器，不能声明完全内置浏览器闭环。"
        )

    for page in pages:
        if page["requires_customer_web_flow"] and not page["embedded_title"]:
            report["blocking_gaps"].append(f"{page['title']} 缺少内置页面标题映射：{page['url']}")
        if not str(page["url"]).startswith(installer.DEFAULT_BASE_URL):
            report["blocking_gaps"].append(f"{page['title']} 不在公共域名下：{page['url']}")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["blocking_gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

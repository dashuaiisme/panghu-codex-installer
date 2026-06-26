import http.cookiejar
import json
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import panghu_codex_installer as pci


def make_cookie(name: str, value: str, rest: dict | None = None) -> http.cookiejar.Cookie:
    return http.cookiejar.Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain="aitokenapi.cc",
        domain_specified=True,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=True,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest=rest or {},
        rfc2109=False,
    )


class InstallerBackendTests(unittest.TestCase):
    def test_profile_payload_keeps_only_safe_persistent_fields(self) -> None:
        original_profile_path = pci.profile_path
        with TemporaryDirectory() as temp_dir:
            temp_profile = Path(temp_dir) / "profile.json"
            try:
                pci.profile_path = lambda: temp_profile  # type: ignore[assignment]
                pci.save_profile_data(
                    {
                        "username": "buyer@example.com",
                        "api_key": "sk-live",
                        "model": "gpt-5.4",
                        "skip_test": True,
                        "open_app": False,
                        "user": {"id": "buyer-1"},
                        "deployer_auth": {"token": "deploy-secret"},
                        "login_token": "login-secret",
                        "refresh_token": "refresh-secret",
                        "rebate": {"rate": "10%"},
                    }
                )
                payload = json.loads(temp_profile.read_text(encoding="utf-8"))
            finally:
                pci.profile_path = original_profile_path  # type: ignore[assignment]

        self.assertEqual(payload["username"], "buyer@example.com")
        self.assertEqual(payload["api_key"], "sk-live")
        self.assertEqual(payload["base_url"], pci.DEFAULT_BASE_URL)
        self.assertEqual(payload["model"], "gpt-5.4")
        self.assertTrue(payload["skip_test"])
        self.assertFalse(payload["open_app"])
        self.assertEqual(payload.get("user"), {})
        self.assertEqual(payload.get("deployer_auth"), {})
        self.assertNotIn("login_token", payload)
        self.assertNotIn("refresh_token", payload)
        self.assertNotIn("rebate", payload)

    def test_buyer_session_cookie_and_metadata_persist_outside_profile_json(self) -> None:
        original_cookie_path = pci.buyer_session_cookie_path
        original_metadata_path = pci.buyer_session_metadata_path
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            try:
                pci.buyer_session_cookie_path = lambda: temp_root / "cookies.txt"  # type: ignore[assignment]
                pci.buyer_session_metadata_path = lambda: temp_root / "buyer_session.json"  # type: ignore[assignment]
                jar = pci.load_buyer_cookie_jar()
                jar.set_cookie(make_cookie("session", "abc123"))

                pci.save_buyer_session_state(
                    {
                        "id": "buyer-1",
                        "username": "buyer@example.com",
                        "role": "buyer",
                        "password": "should-not-save",
                        "token": "should-not-save",
                    },
                    jar,
                )

                restored_jar = pci.load_buyer_cookie_jar()
                restored_user = pci.load_buyer_session_user()
                metadata_text = (temp_root / "buyer_session.json").read_text(encoding="utf-8")
            finally:
                pci.buyer_session_cookie_path = original_cookie_path  # type: ignore[assignment]
                pci.buyer_session_metadata_path = original_metadata_path  # type: ignore[assignment]

        self.assertEqual(restored_user["id"], "buyer-1")
        self.assertEqual(restored_user["username"], "buyer@example.com")
        self.assertNotIn("should-not-save", metadata_text)
        self.assertTrue(any(cookie.name == "session" and cookie.value == "abc123" for cookie in restored_jar))

    def test_webview_cookie_bridge_uses_current_panghu_login_cookie(self) -> None:
        jar = http.cookiejar.CookieJar()
        jar.set_cookie(make_cookie("session", "abc123"))

        script = pci.build_webview_cookie_bridge_script(jar)

        self.assertIn("document.cookie", script)
        self.assertIn("session=abc123", script)
        self.assertIn("SameSite=Lax", script)
        self.assertIn("Secure", script)

    def test_webview_cookie_bridge_does_not_fake_httponly_cookie(self) -> None:
        jar = http.cookiejar.CookieJar()
        jar.set_cookie(make_cookie("session", "abc123", rest={"HttpOnly": None}))

        self.assertEqual(pci.build_webview_cookie_bridge_script(jar), "")

    def test_customer_page_open_passes_cookie_jar_to_embedded_webview(self) -> None:
        jar = http.cookiejar.CookieJar()
        jar.set_cookie(make_cookie("session", "abc123"))
        captured: dict[str, object] = {}
        original_try = pci.try_open_embedded_webview
        original_browser = pci.webbrowser.open
        try:
            def fake_try(url, title="", cookie_jar=None, log=None, storage_path=None):  # type: ignore[no-untyped-def]
                captured["url"] = url
                captured["title"] = title
                captured["cookie_jar"] = cookie_jar
                captured["log"] = log
                captured["storage_path"] = storage_path
                return True

            pci.try_open_embedded_webview = fake_try  # type: ignore[assignment]
            pci.webbrowser.open = lambda _url: (_ for _ in ()).throw(AssertionError("should not use browser fallback"))  # type: ignore[assignment]
            result = pci.open_customer_page(pci.KEY_CREATE_URL, cookie_jar=jar, log=lambda _message: None)
        finally:
            pci.try_open_embedded_webview = original_try  # type: ignore[assignment]
            pci.webbrowser.open = original_browser  # type: ignore[assignment]

        self.assertTrue(result.ok)
        self.assertEqual(result.method, "embedded_webview")
        self.assertIs(captured["cookie_jar"], jar)
        self.assertIn("桥接本次胖虎AI登录态", result.message)

    def test_try_open_embedded_webview_injects_cookie_before_loading_target_page(self) -> None:
        jar = http.cookiejar.CookieJar()
        jar.set_cookie(make_cookie("session", "abc123"))
        done = threading.Event()
        calls: list[tuple[str, object]] = []

        class LoadedEvent:
            def __init__(self) -> None:
                self.handler = None

            def __iadd__(self, handler):  # type: ignore[no-untyped-def]
                self.handler = handler
                return self

        class FakeWindow:
            def __init__(self) -> None:
                self.events = type("Events", (), {"loaded": LoadedEvent()})()

            def evaluate_js(self, script: str) -> None:
                calls.append(("evaluate_js", script))

            def load_url(self, url: str) -> None:
                calls.append(("load_url", url))
                done.set()

        class FakeWebview:
            window = FakeWindow()

            @staticmethod
            def create_window(title, url, **kwargs):  # type: ignore[no-untyped-def]
                calls.append(("create_window", (title, url, kwargs)))
                return FakeWebview.window

            @staticmethod
            def start(**kwargs):  # type: ignore[no-untyped-def]
                calls.append(("start", kwargs))
                FakeWebview.window.events.loaded.handler()

        original_webview = pci.webview
        try:
            pci.webview = FakeWebview()  # type: ignore[assignment]
            self.assertTrue(pci.try_open_embedded_webview(pci.CONSOLE_URL, title="控制台", cookie_jar=jar))
            self.assertTrue(done.wait(timeout=2))
        finally:
            pci.webview = original_webview

        self.assertEqual(calls[0][0], "create_window")
        self.assertEqual(calls[0][1][1], pci.PANGHU_HOME_URL)
        self.assertEqual(calls[1][0], "start")
        self.assertFalse(calls[1][1]["private_mode"])
        self.assertIn("storage_path", calls[1][1])
        self.assertEqual(calls[2][0], "evaluate_js")
        self.assertIn("session=abc123", calls[2][1])
        self.assertEqual(calls[3], ("load_url", pci.CONSOLE_URL))


if __name__ == "__main__":
    unittest.main()

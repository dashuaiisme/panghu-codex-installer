import http.cookiejar
import json
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import panghu_ai_client as pci


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
    def test_register_url_preserves_agent_invite_for_new_account_registration(self) -> None:
        self.assertEqual(pci.build_register_url(""), pci.REGISTER_URL)
        self.assertEqual(
            pci.build_register_url("INVITE-ABC"),
            "https://aitokenapi.cc/register?invite=INVITE-ABC",
        )
        self.assertEqual(
            pci.build_register_url("https://aitokenapi.cc/register?invite=agent%201"),
            "https://aitokenapi.cc/register?invite=agent%201",
        )
        self.assertEqual(
            pci.build_register_url("https://aitokenapi.cc/invite/agent-l1"),
            "https://aitokenapi.cc/register?invite=agent-l1",
        )
        self.assertEqual(
            pci.build_register_url("https://aitokenapi.cc/register?aff=AFF-001"),
            "https://aitokenapi.cc/register?invite=AFF-001",
        )
        self.assertEqual(
            pci.build_register_url("aff_code=AFF-002"),
            "https://aitokenapi.cc/register?invite=AFF-002",
        )

    def test_official_client_requires_webview_ui_and_never_business_tkinter_fallback(self) -> None:
        original_webview = pci.webview
        original_ui_path = pci.ui_path
        try:
            pci.webview = None
            pci.ui_path = lambda _name: Path("src/ui/index.html")  # type: ignore[assignment]

            with self.assertRaisesRegex(RuntimeError, "不能回退到旧 Tkinter 业务界面"):
                pci.require_webview_runtime_and_ui()

            pci.webview = object()
            pci.ui_path = lambda _name: Path("missing-ui-index.html")  # type: ignore[assignment]

            with self.assertRaisesRegex(RuntimeError, "正式界面缺失"):
                pci.require_webview_runtime_and_ui()
        finally:
            pci.webview = original_webview
            pci.ui_path = original_ui_path  # type: ignore[assignment]

    def test_login_account_store_keeps_email_flags_and_encrypted_password_outside_profile(self) -> None:
        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            try:
                pci.login_account_store_path = lambda: temp_root / "login_accounts.json"  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]

                pci.save_login_account_state(
                    "buyer@example.com",
                    password="secret-password",
                    remember_password=True,
                    auto_login=True,
                )

                saved_text = (temp_root / "login_accounts.json").read_text(encoding="utf-8")
                state = pci.load_login_account_state()
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertNotIn("secret-password", saved_text)
        self.assertNotIn('"password"', saved_text)
        self.assertIn('"protected_password"', saved_text)
        self.assertEqual(state["last_username"], "buyer@example.com")
        self.assertEqual(state["accounts"][0]["username"], "buyer@example.com")
        self.assertTrue(state["accounts"][0]["remember_password"])
        self.assertTrue(state["accounts"][0]["auto_login"])
        self.assertEqual(state["accounts"][0]["password"], "secret-password")

    def test_login_account_public_state_hides_decrypted_passwords(self) -> None:
        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            try:
                pci.login_account_store_path = lambda: temp_root / "login_accounts.json"  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]

                pci.save_login_account_state("buyer@example.com", "secret-password", True, True)

                public_state = pci.load_login_account_public_state()
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertEqual(public_state["accounts"][0]["username"], "buyer@example.com")
        self.assertTrue(public_state["accounts"][0]["has_password"])
        self.assertNotIn("password", public_state["accounts"][0])
        self.assertNotIn("secret-password", json.dumps(public_state, ensure_ascii=False))

    def test_login_account_store_removes_selected_account_and_password_blob(self) -> None:
        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            try:
                pci.login_account_store_path = lambda: temp_root / "login_accounts.json"  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]
                pci.save_login_account_state("first@example.com", "first-pass", True, True)
                pci.save_login_account_state("second@example.com", "second-pass", True, False)

                pci.remove_login_account_state("second@example.com")

                saved_text = (temp_root / "login_accounts.json").read_text(encoding="utf-8")
                state = pci.load_login_account_state()
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertEqual([account["username"] for account in state["accounts"]], ["first@example.com"])
        self.assertEqual(state["last_username"], "first@example.com")
        self.assertNotIn("second@example.com", saved_text)
        self.assertNotIn("second-pass", saved_text)

    def test_login_account_store_drops_legacy_plaintext_password_field(self) -> None:
        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            store_path = temp_root / "login_accounts.json"
            store_path.write_text(
                json.dumps(
                    {
                        "last_username": "buyer@example.com",
                        "accounts": [
                            {
                                "username": "buyer@example.com",
                                "remember_password": True,
                                "auto_login": True,
                                "password": "plain-secret",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            try:
                pci.login_account_store_path = lambda: store_path  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]

                state = pci.load_login_account_state()
                pci.save_login_account_state("buyer@example.com", "", True, True)
                saved_text = store_path.read_text(encoding="utf-8")
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertFalse(state["accounts"][0]["remember_password"])
        self.assertFalse(state["accounts"][0]["auto_login"])
        self.assertEqual(state["accounts"][0]["password"], "")
        self.assertNotIn("plain-secret", saved_text)
        self.assertNotIn('"password"', saved_text)

    def test_login_account_store_migrates_legacy_protected_password_field_only(self) -> None:
        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            store_path = temp_root / "login_accounts.json"
            store_path.write_text(
                json.dumps(
                    {
                        "last_username": "buyer@example.com",
                        "accounts": [
                            {
                                "username": "buyer@example.com",
                                "remember_password": True,
                                "auto_login": True,
                                "password": "enc:terces",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            try:
                pci.login_account_store_path = lambda: store_path  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]

                state = pci.load_login_account_state()
                pci.save_login_account_state("buyer@example.com", "", True, True)
                saved_text = store_path.read_text(encoding="utf-8")
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertEqual(state["accounts"][0]["password"], "secret")
        self.assertNotIn('"password"', saved_text)
        self.assertIn('"protected_password"', saved_text)
        self.assertIn("enc:terces", saved_text)

    def test_login_account_store_drops_unreadable_protected_password_blob(self) -> None:
        original_account_path = pci.login_account_store_path
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            store_path = temp_root / "login_accounts.json"
            store_path.write_text(
                json.dumps(
                    {
                        "last_username": "buyer@example.com",
                        "accounts": [
                            {
                                "username": "buyer@example.com",
                                "remember_password": True,
                                "auto_login": True,
                                "protected_password": "enc:broken",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            try:
                pci.login_account_store_path = lambda: store_path  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda _value: ""  # type: ignore[assignment]

                state = pci.load_login_account_state()
                public_state = pci.load_login_account_public_state()
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertFalse(state["accounts"][0]["remember_password"])
        self.assertFalse(state["accounts"][0]["auto_login"])
        self.assertEqual(state["accounts"][0]["password"], "")
        self.assertFalse(public_state["accounts"][0]["has_password"])

    def test_webview_select_login_account_returns_public_account_only(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def set(self, value) -> None:
                self.value = value

            def get(self):
                return self.value

        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            try:
                pci.login_account_store_path = lambda: temp_root / "login_accounts.json"  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]
                pci.save_login_account_state("buyer@example.com", "secret-password", True, True, "buyer-1")
                app = pci.InstallerApp.__new__(pci.InstallerApp)
                app.login_username = FakeVar("")
                app.login_password = FakeVar("typed-secret")
                app.sync_called = False
                app.sync_webview_state = lambda: setattr(app, "sync_called", True)

                result = pci.WebviewApi(app).select_login_account("buyer@example.com")
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertTrue(result["success"])
        self.assertEqual(app.login_username.get(), "buyer@example.com")
        self.assertEqual(app.login_password.get(), "")
        self.assertTrue(app.sync_called)
        self.assertTrue(result["account"]["has_password"])
        self.assertNotIn("password", result["account"])
        self.assertNotIn("secret-password", json.dumps(result, ensure_ascii=False))

    def test_webview_logout_disables_current_auto_login_without_removing_saved_password(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def set(self, value) -> None:
                self.value = value

            def get(self):
                return self.value

        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            try:
                pci.login_account_store_path = lambda: temp_root / "login_accounts.json"  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]
                pci.save_login_account_state("buyer@example.com", "secret-password", True, True, "buyer-1")
                app = pci.InstallerApp.__new__(pci.InstallerApp)
                app.login_username = FakeVar("buyer@example.com")
                app.login_password = FakeVar("typed-secret")
                app.step = FakeVar(9)
                app.status = FakeVar("")
                app.cookie_jar = http.cookiejar.CookieJar()
                app.logged_in_user = {"id": "buyer-1", "username": "buyer@example.com"}
                app.deployer_auth = {"token": "deploy-token"}
                app.commercial_contexts = {"target_buyer_context": {"buyer_user_id": "buyer-1"}}
                app.sync_called = False
                app.sync_webview_state = lambda: setattr(app, "sync_called", True)

                with patch.object(pci, "clear_buyer_session_state") as clear_session, \
                     patch.object(pci, "load_buyer_cookie_jar", return_value=http.cookiejar.CookieJar()):
                    result = pci.WebviewApi(app).logout()

                state = pci.load_login_account_state()
                saved_text = (temp_root / "login_accounts.json").read_text(encoding="utf-8")
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertTrue(result)
        clear_session.assert_called_once()
        self.assertTrue(app.sync_called)
        self.assertIsNone(app.logged_in_user)
        self.assertIsNone(app.deployer_auth)
        self.assertIsNone(app.commercial_contexts)
        self.assertEqual(app.login_password.get(), "")
        self.assertEqual(app.step.get(), 1)
        self.assertTrue(state["accounts"][0]["remember_password"])
        self.assertFalse(state["accounts"][0]["auto_login"])
        self.assertEqual(state["accounts"][0]["password"], "secret-password")
        self.assertIn('"protected_password"', saved_text)
        self.assertNotIn("secret-password", saved_text)

    def test_webview_remove_current_login_account_clears_live_session_and_returns_gate(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def set(self, value) -> None:
                self.value = value

            def get(self):
                return self.value

        original_account_path = pci.login_account_store_path
        original_protect = pci.protect_local_secret
        original_unprotect = pci.unprotect_local_secret
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            try:
                pci.login_account_store_path = lambda: temp_root / "login_accounts.json"  # type: ignore[assignment]
                pci.protect_local_secret = lambda value: "enc:" + value[::-1]  # type: ignore[assignment]
                pci.unprotect_local_secret = lambda value: value[4:][::-1] if value.startswith("enc:") else ""  # type: ignore[assignment]
                pci.save_login_account_state("buyer@example.com", "secret-password", True, True, "buyer-1")
                app = pci.InstallerApp.__new__(pci.InstallerApp)
                app.login_username = FakeVar("buyer@example.com")
                app.login_password = FakeVar("typed-secret")
                app.step = FakeVar(4)
                app.status = FakeVar("")
                app.cookie_jar = http.cookiejar.CookieJar()
                app.logged_in_user = {"id": "buyer-1", "username": "buyer@example.com"}
                app.deployer_auth = {"token": "deploy-token"}
                app.commercial_contexts = {"target_buyer_context": {"buyer_user_id": "buyer-1"}}
                app.sync_called = False
                app.sync_webview_state = lambda: setattr(app, "sync_called", True)

                with patch.object(pci, "clear_buyer_session_state") as clear_session, \
                     patch.object(pci, "load_buyer_cookie_jar", return_value=http.cookiejar.CookieJar()):
                    result = pci.WebviewApi(app).remove_login_account("buyer@example.com")

                state = pci.load_login_account_state()
            finally:
                pci.login_account_store_path = original_account_path  # type: ignore[assignment]
                pci.protect_local_secret = original_protect  # type: ignore[assignment]
                pci.unprotect_local_secret = original_unprotect  # type: ignore[assignment]

        self.assertTrue(result["success"])
        clear_session.assert_called_once()
        self.assertEqual(state["accounts"], [])
        self.assertEqual(app.login_password.get(), "")
        self.assertEqual(app.step.get(), 1)
        self.assertIsNone(app.logged_in_user)
        self.assertIsNone(app.deployer_auth)
        self.assertIsNone(app.commercial_contexts)
        self.assertTrue(app.sync_called)

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

    def test_start_restore_saved_session_prefers_saved_buyer_cookie_session_before_password_login(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def set(self, value) -> None:
                self.value = value

            def get(self):
                return self.value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.logged_in_user = None
        app.deployer_auth = None
        app.login_username = FakeVar("")
        app.login_password = FakeVar("")
        app.remember_password = FakeVar(False)
        app.auto_login = FakeVar(False)
        app.cookie_jar = http.cookiejar.CookieJar()
        app.log_messages = []
        app.busy_values = []
        app.thread_args = None
        app.log = lambda message, replace=False: app.log_messages.append(message)
        app.set_busy = lambda value: app.busy_values.append(value)
        app.status = FakeVar("")

        def fake_worker(user):
            app.thread_args = user

        app._restore_saved_session_worker = fake_worker

        with patch.object(pci, "load_login_account_state", return_value={"last_username": "", "accounts": []}), \
             patch.object(pci, "load_buyer_session_user", return_value={"id": "buyer-1", "username": "buyer@example.com", "role": "buyer"}), \
             patch.object(pci.threading.Thread, "start", lambda self: self._target(*self._args, **self._kwargs)), \
             patch.object(pci, "clear_buyer_session_state") as clear_session:
            app.start_restore_saved_session()

        clear_session.assert_not_called()
        self.assertEqual(app.thread_args["id"], "buyer-1")
        self.assertIn("保存的胖虎AI登录态", "".join(app.log_messages))

    def test_webview_state_does_not_push_full_api_key_from_backend(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.logged_in_user = {"id": "buyer-1"}
        app.deployer_auth = {"token": "deploy-secret"}
        app.api_key = FakeVar("sk-live-secret-token")
        app.skip_test = FakeVar(False)
        app.saved_key_ok = True
        app.environment_checked = False
        app.environment_ok = False
        app.worker_running = False
        app.step = FakeVar(1)
        app.active_subnav = FakeVar("1")
        app.active_module = FakeVar("agent")
        app.login_username = FakeVar("buyer@example.com")
        app.agent_enabled = {agent.id: FakeVar(False) for agent in pci.AGENTS}
        app.agent_mode = {agent.id: FakeVar("cli") for agent in pci.AGENTS}
        app.webview_logs = pci.empty_flow_logs()
        app._commercial_metric_values = lambda: {"remaining": "以服务端为准", "valid_until": "以服务端为准", "device_limit": "以服务端为准"}
        app.selected_agents = lambda: []
        app.can_access_step = lambda _idx: False

        state = pci.WebviewApi(app).get_initial_state()

        self.assertEqual(state["apiKeyValue"], "")
        self.assertNotIn("sk-live-secret-token", json.dumps(state, ensure_ascii=False))

    def test_webview_state_filters_agent_center_internal_summary_fields(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.logged_in_user = {"id": "buyer-1"}
        app.deployer_auth = {"token": "deploy-secret"}
        app.api_key = FakeVar("")
        app.skip_test = FakeVar(False)
        app.saved_key_ok = False
        app.environment_checked = False
        app.environment_ok = False
        app.worker_running = False
        app.step = FakeVar(1)
        app.active_subnav = FakeVar("agent_home")
        app.active_module = FakeVar("courses")
        app.login_username = FakeVar("buyer@example.com")
        app.agent_enabled = {agent.id: FakeVar(False) for agent in pci.AGENTS}
        app.agent_mode = {agent.id: FakeVar("cli") for agent in pci.AGENTS}
        app.webview_logs = pci.empty_flow_logs()
        app.commercial_entitlements = []
        app.buyer_purchase_statuses = {}
        app.communication_software_link_offering_data = {}
        app.communication_software_link_order_statuses = {}
        app.communication_software_link_service_product_id = FakeVar("")
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_agent_id = FakeVar("")
        app.communication_software_link_channel = FakeVar("")
        app.communication_software_link_agent_source = FakeVar("")
        app.communication_software_link_gateway_mode = FakeVar("")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app.agent_center_live_data = {
            "enabled": True,
            "status": "active",
            "upgrade_label": "申请升级",
            "invite_url": "https://aitokenapi.cc/invite/abc",
            "join_page_url": "https://aitokenapi.cc/agent/join",
            "backend_url": "https://aitokenapi.cc/agent/center",
            "rules_url": "https://aitokenapi.cc/agent/rules",
            "settlement_status": "available",
            "last_synced_at": "2026-06-29T10:00:00+08:00",
            "summary": {
                "downstream_count": 1,
                "token_commission_cents": 2,
                "activation_commission_cents": 3,
                "agent_install_commission_cents": 4,
                "available_settlement_cents": 5,
                "pending_settlement_cents": 6,
                "frozen_cents": 7,
                "commission_ratio": "50%",
                "admin_note": "internal",
            },
            "benefits": ["可绑定买家"],
            "boundaries": ["收益以后台结算为准"],
        }
        app._commercial_metric_values = lambda: {"remaining": "以服务端为准", "valid_until": "以服务端为准", "device_limit": "以服务端为准"}
        app.selected_agents = lambda: []
        app.can_access_step = lambda _idx: False

        state = pci.WebviewApi(app).get_initial_state()

        self.assertEqual(state["agentCenter"]["backend_url"], "https://aitokenapi.cc/agent/center")
        self.assertEqual(state["agentCenter"]["benefits"], ["可绑定买家"])
        summary = state["agentCenter"]["summary"]
        self.assertEqual(summary["downstream_count"], 1)
        self.assertNotIn("commission_ratio", summary)
        self.assertNotIn("admin_note", summary)

    def test_webview_initial_state_includes_value_added_services_from_backend(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.logged_in_user = {"id": "buyer-1"}
        app.deployer_auth = {"token": "deploy-secret"}
        app.api_key = FakeVar("")
        app.skip_test = FakeVar(False)
        app.saved_key_ok = False
        app.environment_checked = False
        app.environment_ok = False
        app.worker_running = False
        app.step = FakeVar(1)
        app.active_subnav = FakeVar("1")
        app.active_module = FakeVar("value_added")
        app.login_username = FakeVar("buyer@example.com")
        app.agent_enabled = {agent.id: FakeVar(False) for agent in pci.AGENTS}
        app.agent_mode = {agent.id: FakeVar("cli") for agent in pci.AGENTS}
        app.webview_logs = pci.empty_flow_logs()
        app.commercial_entitlements = []
        app.buyer_purchase_statuses = {}
        app.agent_center_live_data = {}
        app.deployer_manifest = {}
        app.communication_software_link_offering_data = {}
        app.communication_software_link_order_statuses = {}
        app.communication_software_link_service_product_id = FakeVar("")
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_agent_id = FakeVar("")
        app.communication_software_link_channel = FakeVar("")
        app.communication_software_link_agent_source = FakeVar("")
        app.communication_software_link_gateway_mode = FakeVar("")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app._commercial_metric_values = lambda: {"remaining": "以服务端为准", "valid_until": "以服务端为准", "device_limit": "以服务端为准"}
        app.selected_agents = lambda: []
        app.can_access_step = lambda _idx: False
        app.current_value_added_services_state = lambda: [
            {
                "service_id": "communication_software_link",
                "title": "连接通讯软件",
                "status": "available",
            }
        ]

        state = pci.WebviewApi(app).get_initial_state()

        self.assertEqual(state["valueAddedServices"][0]["service_id"], "communication_software_link")

    def test_webview_payload_accepts_frontend_camel_case_for_communication_link(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.communication_software_link_service_product_id = FakeVar("")
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_agent_id = FakeVar("")
        app.communication_software_link_channel = FakeVar("")
        app.communication_software_link_agent_source = FakeVar("")
        app.communication_software_link_platform_account_id = FakeVar("")
        app.communication_software_link_platform_chat_id = FakeVar("")
        app.communication_software_link_gateway_mode = FakeVar("")
        app.communication_software_link_test_prompt = FakeVar("")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")

        pci.WebviewApi(app)._apply_communication_software_link_payload(
            {
                "serviceProductId": "svc-link",
                "orderId": "svc-ord-1",
                "sessionId": "csl-1",
                "agentId": "hermes",
                "agentSource": "existing_local_agent",
                "platformAccountId": "bot-1",
                "platformChatId": "chat-1",
                "gatewayMode": "official_bot",
                "testPrompt": "ping",
                "state": {
                    "sourceEventId": "evt-1",
                    "inboundPlatformMessageId": "in-msg-1",
                    "outboundPlatformMessageId": "out-msg-1",
                    "agentResponseDigest": "sha256:reply",
                    "evidenceUrl": "https://aitokenapi.cc/evidence/evt-1",
                },
            }
        )

        self.assertEqual(app.communication_software_link_service_product_id.get(), "svc-link")
        self.assertEqual(app.communication_software_link_order_id.get(), "svc-ord-1")
        self.assertEqual(app.communication_software_link_session_id.get(), "csl-1")
        self.assertEqual(app.communication_software_link_agent_id.get(), "hermes")
        self.assertEqual(app.communication_software_link_agent_source.get(), "existing_local_agent")
        self.assertEqual(app.communication_software_link_platform_account_id.get(), "bot-1")
        self.assertEqual(app.communication_software_link_platform_chat_id.get(), "chat-1")
        self.assertEqual(app.communication_software_link_gateway_mode.get(), "official_bot")
        self.assertEqual(app.communication_software_link_test_prompt.get(), "ping")
        self.assertEqual(app.communication_software_link_source_event_id.get(), "evt-1")
        self.assertEqual(app.communication_software_link_inbound_message_id.get(), "in-msg-1")
        self.assertEqual(app.communication_software_link_outbound_message_id.get(), "out-msg-1")
        self.assertEqual(app.communication_software_link_response_digest.get(), "sha256:reply")
        self.assertEqual(app.communication_software_link_evidence_url.get(), "https://aitokenapi.cc/evidence/evt-1")

    def test_communication_software_link_state_keeps_real_service_boundary_visible(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.communication_software_link_order_id = FakeVar("svc-ord-1")
        app.communication_software_link_session_id = FakeVar("csl-1")
        app.communication_software_link_source_event_id = FakeVar("evt-1")
        app.communication_software_link_inbound_message_id = FakeVar("in-msg-1")
        app.communication_software_link_outbound_message_id = FakeVar("out-msg-1")
        app.communication_software_link_response_digest = FakeVar("sha256:reply")
        app.communication_software_link_evidence_url = FakeVar("https://aitokenapi.cc/evidence/evt-1")
        app.communication_software_link_order_statuses = {
            "svc-ord-1": {
                "order_status": "delivered",
                "communication_software_link_status": "acceptance_submitted",
            }
        }

        state = app.current_communication_software_link_state()

        self.assertEqual(state["order"]["order_status"], "delivered")
        self.assertEqual(state["realServiceStatus"], "server_required")
        self.assertFalse(state["clientMayClaimDeliveryComplete"])
        self.assertIn("服务端真实验收", state["deliveryBoundary"])

    def test_communication_software_link_state_consumes_server_closure_fields_without_local_completion_claim(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app.communication_software_link_order_statuses = {}

        app._apply_communication_software_link_state_fields(
            {
                "order_id": "svc-ord-1",
                "session_id": "csl-1",
                "status": "connected",
                "real_service_status": "pending_authorization",
                "platform_callback_status": "accepted",
                "runtime_adapter_status": "success",
                "acceptance_status": "server_recorded",
            }
        )

        state = app.current_communication_software_link_state()

        self.assertEqual(state["realServiceStatus"], "pending_authorization")
        self.assertEqual(state["platformCallbackStatus"], "accepted")
        self.assertEqual(state["runtimeAdapterStatus"], "success")
        self.assertEqual(state["acceptanceStatus"], "server_recorded")
        self.assertFalse(state["clientMayClaimDeliveryComplete"])
        self.assertEqual(state["order"]["real_service_status"], "pending_authorization")
        self.assertEqual(state["order"]["platform_callback_status"], "accepted")

    def test_communication_software_link_refresh_worker_respects_server_false_completion_gate(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.communication_software_link_order_id = FakeVar("svc-ord-1")
        app.communication_software_link_session_id = FakeVar("csl-1")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app.communication_software_link_order_statuses = {
            "svc-ord-1": {
                "order_id": "svc-ord-1",
                "session_id": "csl-1",
                "client_may_claim_delivery_complete": True,
            }
        }
        app.log_from_worker = lambda _line: None
        app.run_on_ui = lambda callback: callback()
        app.refresh_steps = lambda: None
        app.sync_webview_state = lambda: None
        app.set_status_from_worker = lambda _text: None
        app.set_busy = lambda _busy: None
        app.show_error_from_worker = lambda _title, message: self.fail(message)

        class FakeRequest:
            pass

        with patch.object(
            pci,
            "execute_commercial_api_with_trusted_certs",
            return_value=(
                {
                    "order_id": "svc-ord-1",
                    "session_id": "csl-1",
                    "status": "connected",
                    "real_service_status": "pending_authorization",
                    "platform_callback_status": "accepted",
                    "runtime_adapter_status": "success",
                    "acceptance_status": "server_recorded",
                    "client_may_claim_delivery_complete": False,
                },
                "session refreshed",
            ),
        ):
            app._communication_software_link_generic_worker("会话状态已刷新", FakeRequest())

        state = app.current_communication_software_link_state()

        self.assertEqual(state["realServiceStatus"], "pending_authorization")
        self.assertEqual(state["platformCallbackStatus"], "accepted")
        self.assertEqual(state["runtimeAdapterStatus"], "success")
        self.assertEqual(state["acceptanceStatus"], "server_recorded")
        self.assertFalse(state["clientMayClaimDeliveryComplete"])

    def test_communication_software_link_web_state_carries_real_service_boundary(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.communication_software_link_offering_data = {"product_id": "svc-communication-software-link"}
        app.communication_software_link_service_product_id = FakeVar("svc-communication-software-link")
        app.communication_software_link_order_id = FakeVar("svc-ord-1")
        app.communication_software_link_session_id = FakeVar("csl-1")
        app.communication_software_link_agent_id = FakeVar("codex")
        app.communication_software_link_channel = FakeVar("feishu")
        app.communication_software_link_agent_source = FakeVar("existing_local_agent")
        app.communication_software_link_platform_account_id = FakeVar("bot-account-1")
        app.communication_software_link_platform_chat_id = FakeVar("chat-1")
        app.communication_software_link_gateway_mode = FakeVar("official_bot")
        app.communication_software_link_test_prompt = FakeVar("请回复连接通讯软件验收成功")
        app.communication_software_link_source_event_id = FakeVar("evt-1")
        app.communication_software_link_inbound_message_id = FakeVar("in-msg-1")
        app.communication_software_link_outbound_message_id = FakeVar("out-msg-1")
        app.communication_software_link_response_digest = FakeVar("sha256:reply")
        app.communication_software_link_evidence_url = FakeVar("https://aitokenapi.cc/evidence/evt-1")
        app.communication_software_link_order_statuses = {
            "svc-ord-1": {
                "order_status": "delivered",
                "communication_software_link_status": "acceptance_submitted",
            }
        }

        web_state = app.current_communication_software_link_web_state()

        self.assertEqual(web_state["platformAccountId"], "bot-account-1")
        self.assertEqual(web_state["platformChatId"], "chat-1")
        self.assertEqual(web_state["testPrompt"], "请回复连接通讯软件验收成功")
        self.assertEqual(web_state["state"]["realServiceStatus"], "server_required")
        self.assertFalse(web_state["state"]["clientMayClaimDeliveryComplete"])
        self.assertIn("服务端真实验收", web_state["state"]["deliveryBoundary"])

    def test_local_communication_link_runtime_adapter_builds_acceptance_evidence(self) -> None:
        evidence = pci.build_local_communication_software_link_acceptance_evidence(
            session_id="csl-1",
            order_id="svc-ord-1",
            agent_id="hermes",
            channel="feishu",
            platform_chat_id="chat-1",
            test_prompt="请回复连接通讯软件验收成功",
            agent_response="连接通讯软件验收成功",
        )

        self.assertEqual(evidence["session_id"], "csl-1")
        self.assertEqual(evidence["order_id"], "svc-ord-1")
        self.assertEqual(evidence["status"], "local_runtime_verified")
        self.assertTrue(evidence["source_event_id"].startswith("csl-local-"))
        self.assertTrue(evidence["inbound_platform_message_id"].startswith("local-feishu-in-"))
        self.assertTrue(evidence["outbound_platform_message_id"].startswith("local-feishu-out-"))
        self.assertTrue(evidence["agent_response_digest"].startswith("sha256:"))
        self.assertIn("csl-1", evidence["evidence_url"])

    def test_local_communication_link_runtime_worker_keeps_real_service_boundary_in_status(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.communication_software_link_order_id = FakeVar("svc-ord-1")
        app.communication_software_link_session_id = FakeVar("csl-1")
        app.communication_software_link_agent_id = FakeVar("hermes")
        app.communication_software_link_channel = FakeVar("feishu")
        app.communication_software_link_platform_chat_id = FakeVar("chat-1")
        app.communication_software_link_test_prompt = FakeVar("请回复连接通讯软件验收成功")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app.communication_software_link_order_statuses = {}
        app._run_local_communication_software_link_runtime_probe = lambda _agent_id: "连接通讯软件验收成功"
        app.log_from_worker = lambda _line: None
        app.run_on_ui = lambda callback: callback()
        app.refresh_steps = lambda: None
        app.sync_webview_state = lambda: None
        app.set_busy = lambda _busy: None
        app.show_error_from_worker = lambda _title, message: self.fail(message)
        statuses: list[str] = []
        app.set_status_from_worker = statuses.append

        app._communication_software_link_local_runtime_worker()

        self.assertTrue(statuses)
        self.assertNotIn("可提交服务端真实验收", statuses[-1])
        self.assertIn("等待真实平台回调与服务端验收记录", statuses[-1])

    def test_communication_software_link_one_click_connect_runs_local_precheck_without_claiming_acceptance(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        class FakeUser:
            def __init__(self, user_id, token="token") -> None:
                self.user_id = user_id
                self.token = token

        class FakeContexts:
            target_buyer = FakeUser("buyer-1")
            operator = FakeUser("buyer-1")

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.commercial_contexts = FakeContexts()
        app.deployer_auth = {"token": "buyer-token"}
        app.communication_software_link_order_statuses = {}
        app.communication_software_link_service_product_id = FakeVar("svc-link")
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_agent_id = FakeVar("hermes")
        app.communication_software_link_channel = FakeVar("feishu")
        app.communication_software_link_agent_source = FakeVar("existing_local_agent")
        app.communication_software_link_platform_account_id = FakeVar("bot-1")
        app.communication_software_link_platform_chat_id = FakeVar("chat-1")
        app.communication_software_link_gateway_mode = FakeVar("official_bot")
        app.communication_software_link_test_prompt = FakeVar("请回复连接通讯软件验收成功")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app.log_from_worker = lambda _line: None
        app.run_on_ui = lambda callback: callback()
        app.refresh_steps = lambda: None
        app.sync_webview_state = lambda: None
        app.set_status_from_worker = lambda _text: None

        requests = []

        def fake_execute(request):
            requests.append(request)
            if request.url.endswith("/api/communication-software-link/orders"):
                return {
                    "order_id": "svc-ord-1",
                    "status": "paid",
                    "charge_status": "paid",
                }, "order created"
            if request.url.endswith("/api/communication-software-link/sessions"):
                return {
                    "order_id": "svc-ord-1",
                    "session_id": "csl-1",
                    "status": "configured",
                }, "session created"
            if request.url.endswith("/api/communication-software-link/sessions/csl-1/test"):
                return {"session_id": "csl-1", "status": "test_accepted"}, "test accepted"
            if request.url.endswith("/api/communication-software-link/sessions/csl-1/acceptance"):
                self.fail("local runtime precheck must not submit real service acceptance")
            self.fail(f"unexpected request url: {request.url}")

        with patch.object(pci, "execute_commercial_api_with_trusted_certs", side_effect=fake_execute), patch.object(
            pci, "run_agent_dialogue_probe", return_value=(True, "连接通讯软件验收成功")
        ):
            result = app.run_communication_software_link_one_click_connect()

        self.assertEqual(result["status"], "local_runtime_precheck_passed")
        self.assertFalse(result["client_may_claim_delivery_complete"])
        self.assertEqual(app.communication_software_link_order_id.get(), "svc-ord-1")
        self.assertEqual(app.communication_software_link_session_id.get(), "csl-1")
        self.assertTrue(app.communication_software_link_source_event_id.get().startswith("csl-local-"))
        self.assertEqual(
            [request.method for request in requests],
            ["POST", "POST", "POST"],
        )
        self.assertTrue(requests[0].url.endswith("/orders"))
        self.assertTrue(requests[1].url.endswith("/sessions"))
        self.assertTrue(requests[2].url.endswith("/test"))

    def test_communication_software_link_one_click_starts_platform_auth_when_phone_binding_missing(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        class FakeUser:
            def __init__(self, user_id, token="token") -> None:
                self.user_id = user_id
                self.token = token

        class FakeContexts:
            target_buyer = FakeUser("buyer-1")
            operator = FakeUser("buyer-1")

        app = pci.InstallerApp.__new__(pci.InstallerApp)
        app.commercial_contexts = FakeContexts()
        app.deployer_auth = {"token": "buyer-token"}
        app.communication_software_link_order_statuses = {}
        app.communication_software_link_service_product_id = FakeVar("svc-link")
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_agent_id = FakeVar("hermes")
        app.communication_software_link_channel = FakeVar("feishu")
        app.communication_software_link_agent_source = FakeVar("existing_local_agent")
        app.communication_software_link_platform_account_id = FakeVar("")
        app.communication_software_link_platform_chat_id = FakeVar("")
        app.communication_software_link_gateway_mode = FakeVar("official_bot")
        app.communication_software_link_test_prompt = FakeVar("请回复连接通讯软件验收成功")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app.log_from_worker = lambda _line: None
        app.run_on_ui = lambda callback: callback()
        app.refresh_steps = lambda: None
        app.sync_webview_state = lambda: None
        app.set_status_from_worker = lambda _text: None
        opened_urls = []
        app.open_communication_software_link_platform_auth_url = opened_urls.append

        requests = []

        def fake_execute(request):
            requests.append(request)
            if request.url.endswith("/api/communication-software-link/orders"):
                return {
                    "order_id": "svc-ord-1",
                    "status": "paid",
                    "charge_status": "paid",
                }, "order created"
            if request.url.endswith("/api/communication-software-link/platform-auth"):
                body = request.body or {}
                self.assertEqual(body["order_id"], "svc-ord-1")
                self.assertEqual(body["channel"], "feishu")
                return {
                    "auth_session_id": "pauth-1",
                    "authorization_url": "https://aitokenapi.cc/communication-software-link/platform-auth/pauth-1",
                    "status": "waiting_scan",
                }, "platform auth created"
            if request.url.endswith("/api/communication-software-link/platform-auth/pauth-1"):
                return {
                    "auth_session_id": "pauth-1",
                    "status": "authorized",
                    "platform_account_id": "feishu-bot-1",
                    "platform_chat_id": "chat-1",
                    "gateway_mode": "official_bot",
                }, "platform auth authorized"
            if request.url.endswith("/api/communication-software-link/sessions"):
                body = request.body or {}
                self.assertEqual(body["platform_account_id"], "feishu-bot-1")
                self.assertEqual(body["platform_chat_id"], "chat-1")
                return {
                    "order_id": "svc-ord-1",
                    "session_id": "csl-1",
                    "status": "configured",
                }, "session created"
            if request.url.endswith("/api/communication-software-link/sessions/csl-1/test"):
                return {"session_id": "csl-1", "status": "test_accepted"}, "test accepted"
            if request.url.endswith("/api/communication-software-link/sessions/csl-1/acceptance"):
                self.fail("platform authorization plus local runtime precheck must not submit real service acceptance")
            self.fail(f"unexpected request url: {request.url}")

        with patch.object(pci, "execute_commercial_api_with_trusted_certs", side_effect=fake_execute), patch.object(
            pci, "run_agent_dialogue_probe", return_value=(True, "连接通讯软件验收成功")
        ):
            result = app.run_communication_software_link_one_click_connect()

        self.assertEqual(result["status"], "local_runtime_precheck_passed")
        self.assertFalse(result["client_may_claim_delivery_complete"])
        self.assertEqual(app.communication_software_link_platform_account_id.get(), "feishu-bot-1")
        self.assertEqual(app.communication_software_link_platform_chat_id.get(), "chat-1")
        self.assertEqual(opened_urls, ["https://aitokenapi.cc/communication-software-link/platform-auth/pauth-1"])
        self.assertEqual(
            [request.url.rsplit("/api/communication-software-link/", 1)[-1] for request in requests[:4]],
            ["orders", "platform-auth", "platform-auth/pauth-1", "sessions"],
        )

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
        with TemporaryDirectory() as temp_dir:
            try:
                pci.webview = FakeWebview()  # type: ignore[assignment]
                self.assertTrue(
                    pci.try_open_embedded_webview(
                        pci.CONSOLE_URL,
                        title="控制台",
                        cookie_jar=jar,
                        storage_path=Path(temp_dir) / "buyer-webview",
                    )
                )
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

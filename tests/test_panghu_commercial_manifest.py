import sys
import unittest
import json
import base64
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import panghu_ai_client as installer_module  # noqa: E402
from panghu_ai_client import (  # noqa: E402
    CodexConfigMode,
    InstallerApp,
    UserContext,
    KEY_CREATE_URL,
    build_real_task_probe_payload,
    build_commercial_config_session_reserve_preview,
    codex_config_session_reserve_from_manifest,
    commercial_mode_key_for_config_mode,
    commercial_mode_key_for_deployment,
    deployment_commercial_contexts,
    ensure_commercial_web_profile_dir,
    execute_config_session_complete,
    execute_config_session_fail,
    execute_config_session_reserve,
    commercial_api_request_with_auth,
    operator_auth_token,
    execute_api_key_owner_verify,
    cleanup_ephemeral_web_profile,
    cleanup_legacy_ephemeral_web_profiles,
    agent_center_summary_text,
    sanitize_worker_message,
    manifest_commercial_entitlements,
    manifest_has_commercial_controls,
    load_commercial_manifest_public_key,
    DEFAULT_BASE_URL,
)
from commercial_core import CommercialProduct, DeliveryScope, EntitlementContract, create_commercial_web_profile  # noqa: E402
from commercial_core import build_customer_purchase_product_lines  # noqa: E402
from commercial_core import canonical_commercial_manifest_payload  # noqa: E402
from commercial_core import BuyerSelfServiceNode, NodeStatus  # noqa: E402

def sign_manifest_for_test(manifest: dict) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    manifest["manifest_signature_algorithm"] = "ed25519"
    manifest["manifest_key_id"] = "test-key-1"
    manifest["manifest_issued_at"] = "2026-06-21T00:00:00+08:00"
    signature = private_key.sign(canonical_commercial_manifest_payload(manifest))
    manifest["manifest_signature"] = "ed25519:" + base64.b64encode(signature).decode("ascii")
    return public_key_pem


class PanghuCommercialManifestTests(unittest.TestCase):
    def test_commercial_manifest_public_key_defaults_to_empty_without_build_injection(self) -> None:
        generated = SRC / "commercial_manifest_public_key.py"
        original = generated.read_text(encoding="utf-8") if generated.exists() else None
        if generated.exists():
            generated.unlink()
        sys.modules.pop("commercial_manifest_public_key", None)
        importlib.invalidate_caches()
        try:
            self.assertEqual(load_commercial_manifest_public_key(), "")
        finally:
            sys.modules.pop("commercial_manifest_public_key", None)
            importlib.invalidate_caches()
            if original is not None:
                generated.write_text(original, encoding="utf-8")

    def test_manifest_commercial_controls_only_enable_gate_when_commercial_fields_exist(self) -> None:
        self.assertFalse(manifest_has_commercial_controls({"agents": [{"id": "codex"}]}))
        self.assertTrue(manifest_has_commercial_controls({"products": []}))
        self.assertTrue(manifest_has_commercial_controls({"entitlements": []}))
        self.assertTrue(manifest_has_commercial_controls({"agent_center": {"enabled": True}}))
        self.assertTrue(manifest_has_commercial_controls({"value_added_services": []}))

    def test_manifest_entitlements_skip_unknown_delivery_scope_instead_of_defaulting(self) -> None:
        entitlements = manifest_commercial_entitlements(
            {
                "entitlements": [
                    {
                        "entitlement_id": "ent-1",
                        "buyer_user_id": "buyer-1",
                        "agent_id": "codex",
                        "mode_key": "direct_api",
                        "remaining_uses": 1,
                        "valid_until": "2026-12-31",
                        "delivery_scope": "future-server-scope",
                        "device_limit": 1,
                        "status": "active",
                    }
                ]
            }
        )

        self.assertEqual(entitlements, [])

    def test_packaged_self_test_covers_payment_status_unlock_guard(self) -> None:
        source = (SRC / "panghu_ai_client.py").read_text(encoding="utf-8")

        self.assertIn('parse_payment_status_data({"order_id": "ord-selftest", "payment_status": "paid"})', source)
        self.assertIn('not paid_without_entitlement["ready_for_delivery"]', source)
        self.assertIn('completed_with_entitlement["ready_for_delivery"]', source)

    def test_manifest_entitlements_skip_invalid_numeric_contract_fields(self) -> None:
        entitlements = manifest_commercial_entitlements(
            {
                "entitlements": [
                    {
                        "entitlement_id": "ent-bad",
                        "buyer_user_id": "buyer-1",
                        "agent_id": "codex",
                        "mode_key": "direct_api",
                        "remaining_uses": "not-a-number",
                        "valid_until": "2026-12-31",
                        "delivery_scope": "full_config",
                        "device_limit": 1,
                        "status": "active",
                    }
                ]
            }
        )

        self.assertEqual(entitlements, [])

    def test_manifest_entitlements_skip_non_positive_usage_and_device_limits(self) -> None:
        base_entitlement = {
            "entitlement_id": "ent-bad",
            "buyer_user_id": "buyer-1",
            "agent_id": "codex",
            "mode_key": "direct_api",
            "remaining_uses": 1,
            "valid_until": "2026-12-31",
            "delivery_scope": "full_config",
            "device_limit": 1,
            "status": "active",
        }

        for field, value in {"remaining_uses": -1, "device_limit": 0}.items():
            entitlement = dict(base_entitlement)
            entitlement[field] = value

            entitlements = manifest_commercial_entitlements({"entitlements": [entitlement]})

            self.assertEqual(entitlements, [], field)

    def test_manifest_entitlements_accept_explicit_unlimited_usage_flag(self) -> None:
        entitlements = manifest_commercial_entitlements(
            {
                "entitlements": [
                    {
                        "entitlement_id": "ent-unlimited",
                        "buyer_user_id": "buyer-1",
                        "agent_id": "codex",
                        "mode_key": "direct_api",
                        "remaining_uses": 0,
                        "is_unlimited": True,
                        "valid_until": "2026-12-31",
                        "delivery_scope": "full_config",
                        "device_limit": 1,
                        "status": "active",
                    }
                ]
            }
        )

        self.assertEqual(len(entitlements), 1)
        self.assertTrue(entitlements[0].is_unlimited)
        self.assertEqual(entitlements[0].remaining_uses, 0)

    def test_manifest_entitlements_skip_missing_required_contract_fields(self) -> None:
        base_entitlement = {
            "entitlement_id": "ent-1",
            "buyer_user_id": "buyer-1",
            "agent_id": "codex",
            "mode_key": "direct_api",
            "remaining_uses": 1,
            "valid_until": "2026-12-31",
            "delivery_scope": "full_config",
            "device_limit": 1,
            "status": "active",
        }

        for required_field in ("buyer_user_id", "agent_id", "mode_key", "valid_until", "delivery_scope", "status"):
            entitlement = dict(base_entitlement)
            entitlement[required_field] = ""

            entitlements = manifest_commercial_entitlements({"entitlements": [entitlement]})

            self.assertEqual(entitlements, [], required_field)

    def test_manifest_entitlements_preserve_paid_and_trial_sources(self) -> None:
        entitlements = manifest_commercial_entitlements(
            {
                "entitlements": [
                    {
                        "entitlement_id": "ent-paid",
                        "buyer_user_id": "buyer-1",
                        "agent_id": "codex",
                        "mode_key": "direct_api",
                        "remaining_uses": 1,
                        "valid_until": "2026-12-31",
                        "delivery_scope": "full_config",
                        "device_limit": 1,
                        "status": "active",
                        "source": "paid",
                    },
                    {
                        "entitlement_id": "ent-trial",
                        "buyer_user_id": "buyer-1",
                        "agent_id": "codex",
                        "mode_key": "direct_api",
                        "remaining_uses": 1,
                        "valid_until": "2026-12-31",
                        "delivery_scope": "full_config",
                        "device_limit": 1,
                        "status": "active",
                        "source": "trial",
                    },
                ]
            }
        )

        self.assertEqual([entitlement.source for entitlement in entitlements], ["paid", "trial"])

    def test_codex_install_mode_and_config_mode_use_different_commercial_keys(self) -> None:
        self.assertEqual(commercial_mode_key_for_deployment("codex", "cli"), "direct_api")
        self.assertEqual(commercial_mode_key_for_deployment("openclaw", "cli"), "cli")
        self.assertEqual(commercial_mode_key_for_config_mode(CodexConfigMode.DIRECT_API), "direct_api")
        self.assertEqual(commercial_mode_key_for_config_mode(CodexConfigMode.DUAL_STATE), "dual_state")

    def test_deployment_context_uses_logged_in_buyer_only(self) -> None:
        contexts = deployment_commercial_contexts({"id": "login-buyer", "username": "本人"})

        self.assertEqual(contexts.operator.user_id, "login-buyer")
        self.assertEqual(contexts.target_buyer.user_id, "login-buyer")

    def test_deployment_context_falls_back_to_logged_in_buyer(self) -> None:
        contexts = deployment_commercial_contexts({"id": "buyer-self", "username": "本人"})

        self.assertEqual(contexts.operator.user_id, "buyer-self")
        self.assertEqual(contexts.target_buyer.user_id, "buyer-self")

    def test_ephemeral_web_profile_cleanup_does_not_delete_buyer_profile(self) -> None:
        root = ROOT / "tmp-test-web-profiles"
        if root.exists():
            import shutil
            shutil.rmtree(root)
        buyer_contexts = deployment_commercial_contexts({"id": "buyer-self", "username": "本人"})
        buyer_profile = create_commercial_web_profile(buyer_contexts, str(root))
        buyer_path = ensure_commercial_web_profile_dir(buyer_profile)
        (buyer_path / "cookie.txt").write_text("buyer", encoding="utf-8")

        cleanup_ephemeral_web_profile(buyer_profile)

        self.assertTrue(buyer_path.exists())
        import shutil
        shutil.rmtree(root)

    def test_legacy_ephemeral_web_profile_cleanup_removes_only_old_agent_assist_dirs(self) -> None:
        root = ROOT / "tmp-test-agent-assist-cleanup"
        if root.exists():
            import shutil
            shutil.rmtree(root)
        buyer_contexts = deployment_commercial_contexts({"id": "buyer-self", "username": "本人"})
        buyer_path = ensure_commercial_web_profile_dir(create_commercial_web_profile(buyer_contexts, str(root)))
        (buyer_path / "cookie.txt").write_text("buyer", encoding="utf-8")

        real_path = root / "agent-assist-real"
        real_path.mkdir(parents=True)
        (real_path / "cookie.txt").write_text("real", encoding="utf-8")
        placeholder_path = root / "agent-assist-placeholder"
        placeholder_path.mkdir(parents=True)
        (placeholder_path / "cookie.txt").write_text("placeholder", encoding="utf-8")

        cleanup_legacy_ephemeral_web_profiles(str(root))

        self.assertTrue(buyer_path.exists())
        self.assertFalse(real_path.exists())
        self.assertFalse(placeholder_path.exists())
        import shutil
        shutil.rmtree(root)

    def test_codex_config_session_reserve_from_manifest_uses_mode_specific_entitlement(self) -> None:
        manifest = {
            "agents": [{"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True}],
            "entitlements": [
                {
                    "entitlement_id": "ent-dual",
                    "buyer_user_id": "buyer-1",
                    "agent_id": "codex",
                    "mode_key": "dual_state",
                    "remaining_uses": 1,
                    "valid_until": "2026-12-31",
                    "delivery_scope": "full_config",
                    "device_limit": 1,
                    "status": "active",
                }
            ],
        }
        public_key_pem = sign_manifest_for_test(manifest)
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"success": True, "data": {"config_session_id": "cfg-dual"}}, ensure_ascii=False).encode("utf-8")

        def opener(req, _timeout):
            captured["authorization"] = req.headers.get("Authorization")
            return FakeResponse()

        session_id, summary = codex_config_session_reserve_from_manifest(
            manifest=manifest,
            mode=CodexConfigMode.DUAL_STATE,
            contexts=contexts,
            diagnostic_code="PH-CFG-1",
            opener=opener,
            public_key_pem=public_key_pem,
            deployer_auth={"token": "buyer-token"},
        )

        self.assertEqual(session_id, "cfg-dual")
        self.assertEqual(captured["authorization"], "Bearer buyer-token")
        self.assertIn("reserve", summary)

    def test_codex_config_session_reserve_rejects_unsigned_commercial_manifest(self) -> None:
        manifest = {
            "agents": [{"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True}],
            "entitlements": [
                {
                    "entitlement_id": "ent-dual",
                    "buyer_user_id": "buyer-1",
                    "agent_id": "codex",
                    "mode_key": "dual_state",
                    "remaining_uses": 1,
                    "valid_until": "2026-12-31",
                    "delivery_scope": "full_config",
                    "device_limit": 1,
                    "status": "active",
                }
            ],
        }
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})

        with self.assertRaisesRegex(RuntimeError, "签名"):
            codex_config_session_reserve_from_manifest(
                manifest=manifest,
                mode=CodexConfigMode.DUAL_STATE,
                contexts=contexts,
                diagnostic_code="PH-CFG-1",
                opener=lambda _req, _timeout: None,
            )

    def test_config_session_reserve_preview_requires_real_entitlement_id(self) -> None:
        with self.assertRaises(ValueError):
            build_commercial_config_session_reserve_preview(
                entitlement_id="",
                buyer_user_id="buyer-1",
                operator_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                diagnostic_code="PH-CFG-1",
            )

        request = build_commercial_config_session_reserve_preview(
            entitlement_id="ent-real",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            diagnostic_code="PH-CFG-1",
        )

        self.assertEqual(request.body["entitlement_id"], "ent-real")
        self.assertNotEqual(request.body["entitlement_id"], "pending-server-entitlement")

    def test_config_session_reserve_preview_idempotency_key_is_stable_for_same_attempt(self) -> None:
        first = build_commercial_config_session_reserve_preview(
            entitlement_id="ent-real",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            diagnostic_code="PH-CFG-1",
        )
        second = build_commercial_config_session_reserve_preview(
            entitlement_id="ent-real",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            diagnostic_code="PH-CFG-1",
        )
        different_attempt = build_commercial_config_session_reserve_preview(
            entitlement_id="ent-real",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            diagnostic_code="PH-CFG-2",
        )

        self.assertEqual(first.headers["Idempotency-Key"], second.headers["Idempotency-Key"])
        self.assertNotEqual(first.headers["Idempotency-Key"], different_attempt.headers["Idempotency-Key"])
        self.assertTrue(first.headers["Idempotency-Key"].startswith("cfg-reserve-"))

    def test_execute_config_session_reserve_requires_server_session_id(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"success": True, "data": {"config_session_id": "cfg-real"}},
                    ensure_ascii=False,
                ).encode("utf-8")

        def opener(_req, _timeout):
            return FakeResponse()

        session_id, summary = execute_config_session_reserve(
            entitlement_id="ent-real",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            diagnostic_code="PH-CFG-1",
            opener=opener,
        )

        self.assertEqual(session_id, "cfg-real")
        self.assertIn("reserve", summary)

    def test_commercial_api_request_with_auth_uses_logged_in_buyer_token(self) -> None:
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})
        request = commercial_api_request_with_auth(
            "reserve",
            contexts,
            deployer_auth={"token": "buyer-token"},
            entitlement_id="ent-1",
            agent_id="codex",
            mode_key="direct_api",
            diagnostic_code="PH-CFG-1",
        )

        self.assertEqual(request.headers["Authorization"], "Bearer buyer-token")
        self.assertEqual(request.body["buyer_user_id"], "buyer-1")
        self.assertEqual(request.body["operator_user_id"], "buyer-1")

    def test_commercial_api_actions_all_use_logged_in_buyer_token(self) -> None:
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})

        cases = [
            ("api_key_owner_verify", {"api_key": "sk-test"}),
            ("order_create", {"product_id": "prod-1"}),
            ("payment_poll", {"order_id": "ord-1"}),
            ("entitlement_query", {}),
            ("agent_center", {}),
            ("agent_downstreams", {"cursor": "page-1"}),
            ("agent_commissions", {"event_type": "tool_order_paid"}),
            ("agent_public_offering", {}),
            ("agent_apply", {"product_id": "agent-l1-free"}),
            ("referral_bind", {"invite_code": "https://aitokenapi.cc/register?invite=INVITE1"}),
            ("agent_settlement", {"requested_cents": 1000}),
            ("communication_software_link_offering", {}),
            (
                "communication_software_link_order_create",
                {
                    "service_product_id": "svc-communication-software-link",
                    "agent_id": "hermes",
                    "channel": "feishu",
                    "agent_source": "existing_local_agent",
                },
            ),
            ("communication_software_link_order_get", {"order_id": "svc-ord-1"}),
            (
                "communication_software_link_session_create",
                {
                    "order_id": "svc-ord-1",
                    "agent_id": "hermes",
                    "channel": "feishu",
                    "platform_account_id": "bot-1",
                    "platform_chat_id": "chat-1",
                    "gateway_mode": "official_bot",
                    "agent_source": "existing_local_agent",
                },
            ),
            ("communication_software_link_session_get", {"session_id": "csl-1"}),
            (
                "communication_software_link_platform_auth_create",
                {
                    "order_id": "svc-ord-1",
                    "agent_id": "hermes",
                    "channel": "feishu",
                    "gateway_mode": "official_bot",
                    "platform_chat_hint": "chat-1",
                },
            ),
            ("communication_software_link_platform_auth_get", {"auth_session_id": "pauth-1"}),
            ("communication_software_link_session_test", {"session_id": "csl-1", "test_prompt": "ping"}),
            (
                "communication_software_link_session_acceptance",
                {
                    "session_id": "csl-1",
                    "source_event_id": "evt-1",
                    "inbound_platform_message_id": "in-msg-1",
                    "outbound_platform_message_id": "out-msg-1",
                    "test_prompt": "ping",
                    "agent_response_digest": "sha256:reply",
                    "evidence_url": "https://aitokenapi.cc/evidence/evt-1",
                },
            ),
            ("communication_software_link_session_disable", {"session_id": "csl-1"}),
            (
                "complete",
                {
                    "config_session_id": "cfg-1",
                    "diagnostic_code": "PH-CFG-1",
                },
            ),
            (
                "fail",
                {
                    "config_session_id": "cfg-1",
                    "diagnostic_code": "PH-CFG-1",
                    "failure_reason": "验收失败",
                },
            ),
        ]

        for action, kwargs in cases:
            with self.subTest(action=action):
                request = commercial_api_request_with_auth(
                    action,
                    contexts,
                    deployer_auth={"token": "buyer-token"},
                    **kwargs,
                )

                self.assertEqual(request.headers["Authorization"], "Bearer buyer-token")
                if "operator_user_id" in request.body:
                    self.assertEqual(request.body["operator_user_id"], "buyer-1")
                if "buyer_user_id" in request.body:
                    self.assertEqual(request.body["buyer_user_id"], "buyer-1")
                if action in {"agent_apply", "referral_bind", "agent_settlement"}:
                    self.assertIn("Idempotency-Key", request.headers)
                if action == "referral_bind":
                    self.assertEqual(request.body["invite_code"], "INVITE1")

    def test_commercial_api_request_rejects_legacy_buyer_bind_action(self) -> None:
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})

        with self.assertRaisesRegex(ValueError, "Unknown commercial api action"):
            commercial_api_request_with_auth(
                "buyer_bind",
                contexts,
                deployer_auth={"token": "buyer-token"},
                invite_code="INVITE1",
            )

    def test_desktop_commercial_dispatcher_does_not_expose_admin_agent_actions(self) -> None:
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})

        forbidden_actions = [
            "admin_agent_product_update",
            "admin_agent_policy_update",
            "admin_agent_marketing_update",
            "admin_agent_application_review",
            "admin_agent_settlement_action",
            "admin_agent_ledger_action",
            "admin_communication_software_link_product_update",
            "admin_communication_software_link_channel_policy_update",
            "admin_communication_software_link_session_action",
            "admin_communication_software_link_order_action",
        ]

        for action in forbidden_actions:
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "Unknown commercial api action"):
                commercial_api_request_with_auth(
                    action,
                    contexts,
                    deployer_auth={"token": "buyer-token"},
                )

    def test_legacy_agent_assist_context_factory_is_not_available(self) -> None:
        self.assertFalse(hasattr(installer_module, "create_agent_assist_contexts"))
        self.assertFalse(hasattr(installer_module, "AgentAssistDraft"))

    def test_order_create_idempotency_key_is_stable_for_same_assist_context(self) -> None:
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})

        first = commercial_api_request_with_auth(
            "order_create",
            contexts,
            deployer_auth={"token": "buyer-token"},
            product_id="prod-codex",
        )
        second = commercial_api_request_with_auth(
            "order_create",
            contexts,
            deployer_auth={"token": "buyer-token"},
            product_id="prod-codex",
        )
        different_product = commercial_api_request_with_auth(
            "order_create",
            contexts,
            deployer_auth={"token": "buyer-token"},
            product_id="prod-other",
        )

        self.assertEqual(first.headers["Idempotency-Key"], second.headers["Idempotency-Key"])
        self.assertNotEqual(first.headers["Idempotency-Key"], different_product.headers["Idempotency-Key"])
        self.assertTrue(first.headers["Idempotency-Key"].startswith("order-"))

    def test_execute_config_session_complete_uses_real_server_session_id(self) -> None:
        captured_headers = []
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"success": True, "data": {"status": "completed"}}, ensure_ascii=False).encode("utf-8")

        def opener(req, _timeout):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured_headers.append(req.headers["Idempotency-key"])
            return FakeResponse()

        with self.assertRaises(ValueError):
            execute_config_session_complete("", "PH-CFG-1", opener=opener)

        _data, summary = execute_config_session_complete("cfg-real", "PH-CFG-1", opener=opener)
        execute_config_session_complete("cfg-real", "PH-CFG-1", opener=opener)

        self.assertEqual(captured["body"]["config_session_id"], "cfg-real")
        self.assertTrue(captured["body"]["real_task_verified"])
        self.assertEqual(captured_headers[0], captured_headers[1])
        self.assertIn("complete", summary)

    def test_execute_config_session_fail_never_deducts_entitlement(self) -> None:
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"success": True, "data": {"status": "failed"}}, ensure_ascii=False).encode("utf-8")

        def opener(req, _timeout):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResponse()

        _data, summary = execute_config_session_fail("cfg-real", "PH-CFG-1", "真实任务失败", opener=opener)

        self.assertEqual(captured["body"]["config_session_id"], "cfg-real")
        self.assertFalse(captured["body"]["deduct_entitlement"])
        self.assertIn("fail", summary)

    def test_fail_unfinished_config_sessions_marks_only_reserved_unfinished_sessions_failed(self) -> None:
        captured = []
        original_fail = installer_module.execute_config_session_fail
        try:
            installer_module.execute_config_session_fail = (
                lambda session_id, diagnostic_code, reason, opener=None, contexts=None, deployer_auth=None:
                (captured.append((session_id, diagnostic_code, reason, contexts, deployer_auth)) or ({}, "failed"))
            )

            summaries = installer_module.fail_unfinished_config_sessions(
                config_session_ids={
                    ("codex", "direct_api"): "cfg-complete",
                    ("openclaw", "cli"): "cfg-open",
                },
                completed_session_keys={("codex", "direct_api")},
                diagnostic_code="PH-CFG-1",
                reason="部署异常中断，未形成完整交付。",
                opener=lambda _req, _timeout: None,
                contexts="contexts",
                deployer_auth={"token": "buyer-token"},
            )
        finally:
            installer_module.execute_config_session_fail = original_fail

        self.assertEqual(captured, [("cfg-open", "PH-CFG-1", "部署异常中断，未形成完整交付。", "contexts", {"token": "buyer-token"})])
        self.assertEqual(summaries, ["openclaw/cli：failed"])

    def test_fail_unfinished_config_sessions_keeps_original_flow_when_cleanup_api_fails(self) -> None:
        original_fail = installer_module.execute_config_session_fail
        try:
            installer_module.execute_config_session_fail = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("cleanup network failed")
            )

            summaries = installer_module.fail_unfinished_config_sessions(
                config_session_ids={("codex", "direct_api"): "cfg-open"},
                completed_session_keys=set(),
                diagnostic_code="PH-CFG-1",
                reason="部署异常中断，未形成完整交付。",
                opener=lambda _req, _timeout: None,
                contexts="contexts",
                deployer_auth={"token": "buyer-token"},
            )
        finally:
            installer_module.execute_config_session_fail = original_fail

        self.assertEqual(summaries, ["codex/direct_api：失败兜底提交异常：cleanup network failed"])

    def test_execute_api_key_owner_verify_requires_target_buyer_owner(self) -> None:
        contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "本人"})
        responses = [
            {"success": True, "data": {"owner_user_id": "buyer-1"}},
            {"success": True, "data": {"owner_user_id": "agent-1"}},
        ]
        captured = []

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

        def opener(req, _timeout):
            captured.append(json.loads(req.data.decode("utf-8")))
            return FakeResponse(responses.pop(0))

        summary = execute_api_key_owner_verify("sk-live-secret", contexts, opener=opener, deployer_auth={"token": "buyer-token"})

        self.assertIn("归属已确认", summary)
        self.assertEqual(captured[0]["target_buyer_user_id"], "buyer-1")
        self.assertEqual(captured[0]["operator_user_id"], "buyer-1")
        with self.assertRaisesRegex(ValueError, "目标买家"):
            execute_api_key_owner_verify("sk-live-secret", contexts, opener=opener, deployer_auth={"token": "buyer-token"})

    def test_save_key_worker_uses_logged_in_buyer_context_for_profile_save(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.logged_in_user = {"id": "login-buyer", "username": "登录用户"}
        app.deployer_auth = {"token": "buyer-token"}
        app.saved_key_ok = False
        app.saved_key_signature = None
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda _message: None
        app.show_warning_from_worker = lambda _title, _message: None
        app.show_error_from_worker = lambda _title, _message: None
        app.refresh_steps = lambda: None
        app.set_busy = lambda _busy: None
        app.run_on_ui = lambda callback: callback()

        class Step:
            def set(self, _value):
                return None

        app.step = Step()
        captured = {}
        original_verify = installer_module.execute_api_key_owner_verify
        original_save = installer_module.save_profile_data
        try:
            installer_module.execute_api_key_owner_verify = lambda _api_key, _contexts, opener=None, deployer_auth=None: "归属已确认"
            installer_module.save_profile_data = lambda data, contexts=None: captured.update({"data": data, "contexts": contexts})

            app._save_key_worker("sk-live-secret", "https://aitokenapi.cc", "gpt-5.4", True, False)
        finally:
            installer_module.execute_api_key_owner_verify = original_verify
            installer_module.save_profile_data = original_save

        self.assertEqual(captured["contexts"].operator.user_id, "login-buyer")
        self.assertEqual(captured["contexts"].target_buyer.user_id, "login-buyer")
        self.assertEqual(captured["data"]["api_key"], "sk-live-secret")

    def test_legacy_agent_assist_workers_are_removed(self) -> None:
        source = (SRC / "panghu_ai_client.py").read_text(encoding="utf-8")

        self.assertNotIn("def _agent_assist_login_worker", source)
        self.assertNotIn("def _agent_create_order_worker", source)
        self.assertNotIn("def _agent_poll_payment_worker", source)
        self.assertNotIn("def clear_agent_assist_session", source)

    def test_load_profile_into_ui_hides_legacy_agentish_username_without_restoring_session(self) -> None:
        app = InstallerApp.__new__(InstallerApp)

        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def set(self, value) -> None:
                self.value = value

        app.login_username = FakeVar()
        app.api_key = FakeVar()
        app.base_url = FakeVar()
        app.model = FakeVar()
        app.skip_test = FakeVar()
        app.open_app = FakeVar()
        app.logged_in_user = None
        app.deployer_auth = None
        app.commercial_contexts = None

        original_load = installer_module.load_saved_profile
        try:
            installer_module.load_saved_profile = lambda: {
                "username": "agent@example.com",
                "user": {"id": "agent-1", "role": "agent", "username": "agent@example.com"},
                "deployer_auth": {"token": "agent-secret-token", "role": "agent"},
                "api_key": "sk-buyer-live",
                "model": "gpt-5.4",
            }

            app.load_profile_into_ui()
        finally:
            installer_module.load_saved_profile = original_load

        self.assertEqual(app.login_username.value, "")
        self.assertEqual(app.logged_in_user, None)
        self.assertEqual(app.deployer_auth, None)
        self.assertEqual(app.commercial_contexts, None)
        self.assertEqual(app.api_key.value, "sk-buyer-live")

    def test_load_profile_into_ui_does_not_restore_buyer_session_from_profile_json(self) -> None:
        app = InstallerApp.__new__(InstallerApp)

        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def set(self, value) -> None:
                self.value = value

            def get(self):
                return self.value

        class FakeLabel:
            def __init__(self) -> None:
                self.text = ""

            def configure(self, **kwargs):
                if "text" in kwargs:
                    self.text = kwargs["text"]

        app.login_username = FakeVar()
        app.api_key = FakeVar()
        app.base_url = FakeVar()
        app.model = FakeVar()
        app.skip_test = FakeVar()
        app.open_app = FakeVar()
        app.status = FakeVar()
        app.user_label = FakeLabel()
        app.logged_in_user = None
        app.deployer_auth = None
        app.commercial_contexts = None

        original_load = installer_module.load_saved_profile
        try:
            installer_module.load_saved_profile = lambda: {
                "username": "buyer@example.com",
                "user": {"id": "buyer-1", "role": "buyer", "username": "buyer@example.com"},
                "deployer_auth": {"token": "buyer-secret-token", "role": "buyer"},
                "api_key": "sk-buyer-live",
                "model": "gpt-5.4",
            }

            app.load_profile_into_ui()
            app.apply_restored_login_state()
        finally:
            installer_module.load_saved_profile = original_load

        self.assertEqual(app.login_username.value, "buyer@example.com")
        self.assertEqual(app.logged_in_user, None)
        self.assertEqual(app.deployer_auth, None)
        self.assertEqual(app.commercial_contexts, None)
        self.assertEqual(app.user_label.text, "上次账号：buyer@example.com")
        self.assertIn("账号提示", app.status.value)

    def test_save_profile_data_does_not_persist_restorable_login_identity(self) -> None:
        original_profile_path = installer_module.profile_path
        with TemporaryDirectory() as temp_dir:
            temp_profile = Path(temp_dir) / "profile.json"
            try:
                installer_module.profile_path = lambda: temp_profile
                installer_module.save_profile_data(
                    {
                        "username": "buyer@example.com",
                        "user": {"id": "buyer-1", "role": "buyer", "username": "buyer@example.com"},
                        "deployer_auth": {"token": "buyer-secret-token", "role": "buyer"},
                        "api_key": "sk-buyer-live",
                        "model": "gpt-5.4",
                        "skip_test": True,
                        "open_app": False,
                    },
                    installer_module.create_buyer_contexts(
                        UserContext(user_id="buyer-1", display_name="buyer@example.com", role="buyer")
                    ),
                )
                saved = json.loads(temp_profile.read_text(encoding="utf-8"))
            finally:
                installer_module.profile_path = original_profile_path

        self.assertEqual(saved["username"], "buyer@example.com")
        self.assertEqual(saved["user"], {})
        self.assertEqual(saved["deployer_auth"], {})
        self.assertEqual(saved["api_key"], "sk-buyer-live")
        self.assertEqual(saved["model"], "gpt-5.4")
        self.assertTrue(saved["skip_test"])
        self.assertFalse(saved["open_app"])

    def test_legacy_agent_assist_fields_are_not_initialized_on_app(self) -> None:
        source = (SRC / "panghu_ai_client.py").read_text(encoding="utf-8")

        self.assertNotIn("self.agent_assist_draft", source)
        self.assertNotIn("self.agent_assist_statuses", source)
        self.assertNotIn("self.agent_assist_product_id", source)

    def test_customer_purchase_product_lines_show_price_uses_device_and_expiry(self) -> None:
        products = [
            CommercialProduct(
                product_id="prod-codex",
                title="Codex 普通配置 10 次",
                agent_id="codex",
                mode_key=CodexConfigMode.DIRECT_API.value,
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=10,
                valid_until="2026-12-31T23:59:59+08:00",
                includes_dual_state=False,
                device_limit=2,
                is_listed=True,
            ),
            CommercialProduct(
                product_id="hidden",
                title="隐藏商品",
                agent_id="codex",
                mode_key=CodexConfigMode.DIRECT_API.value,
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=1,
                currency="CNY",
                remaining_uses=1,
                valid_until="2026-12-31T23:59:59+08:00",
                includes_dual_state=False,
                device_limit=1,
                is_listed=False,
            ),
        ]

        lines = build_customer_purchase_product_lines(products)

        self.assertEqual(len(lines), 1)
        self.assertIn("Codex 普通配置 10 次", lines[0])
        self.assertIn("¥99.00", lines[0])
        self.assertIn("10次", lines[0])
        self.assertIn("2台设备", lines[0])
        self.assertIn("2026-12-31", lines[0])

    def test_buyer_self_service_order_uses_logged_in_buyer_context_and_surfaces_payment(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.worker_running = False
        app.commercial_contexts = installer_module.create_buyer_contexts(
            UserContext(user_id="buyer-1", display_name="买家", role="buyer", token="buyer-token")
        )
        app.commercial_products = [
            CommercialProduct(
                product_id="prod-codex",
                title="Codex 普通配置 10 次",
                agent_id="codex",
                mode_key=CodexConfigMode.DIRECT_API.value,
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=10,
                valid_until="2026-12-31T23:59:59+08:00",
                includes_dual_state=False,
                device_limit=2,
                is_listed=True,
            )
        ]
        app.buyer_product_id = type("Var", (), {"get": lambda _self: "prod-codex"})()
        app.buyer_order_id = type("Var", (), {"set": lambda _self, value: setattr(app, "buyer_order_id_value", value)})()
        app.set_busy = lambda _busy: None
        app.buyer_purchase_statuses = {}
        app.refresh_buyer_purchase_status = lambda: None
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda message: setattr(app, "last_status", message)
        app.run_on_ui = lambda callback: callback()
        app.show_error_from_worker = lambda _title, _message: None
        infos = []
        app.show_info_from_worker = lambda title, message: infos.append((title, message))
        captured = {}
        original_request = installer_module.commercial_api_request_with_auth
        original_execute = installer_module.execute_commercial_api_with_trusted_certs
        original_thread = installer_module.threading.Thread

        class ImmediateThread:
            def __init__(self, target, args=(), daemon=None):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        try:
            def fake_request(action, contexts, **kwargs):
                captured["action"] = action
                captured["operator"] = contexts.operator.user_id
                captured["target"] = contexts.target_buyer.user_id
                captured["product_id"] = kwargs["product_id"]
                return object()

            installer_module.commercial_api_request_with_auth = fake_request
            installer_module.execute_commercial_api_with_trusted_certs = lambda _request: (
                {"order_id": "ord-buyer", "payment_url": "https://aitokenapi.cc/pay/ord-buyer"},
                "订单已创建",
            )
            installer_module.threading.Thread = ImmediateThread

            app.start_buyer_create_order()
        finally:
            installer_module.commercial_api_request_with_auth = original_request
            installer_module.execute_commercial_api_with_trusted_certs = original_execute
            installer_module.threading.Thread = original_thread

        self.assertEqual(captured["action"], "order_create")
        self.assertEqual(captured["operator"], "buyer-1")
        self.assertEqual(captured["target"], "buyer-1")
        self.assertEqual(captured["product_id"], "prod-codex")
        self.assertEqual(app.buyer_order_id_value, "ord-buyer")
        self.assertIn("付款链接", infos[0][1])
        self.assertEqual(app.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT], NodeStatus.NEEDS_MANUAL)

    def test_buyer_self_service_order_supports_non_codex_agent_product(self) -> None:
        # Regression: start_buyer_create_order used to hardcode agent_id="codex" /
        # mode_key=direct_api, so ordering any other agent's entitlement returned
        # "商品不匹配" and no order was created. The agent/mode must come from the
        # product snapshot instead.
        app = InstallerApp.__new__(InstallerApp)
        app.worker_running = False
        app.commercial_contexts = installer_module.create_buyer_contexts(
            UserContext(user_id="buyer-1", display_name="买家", role="buyer", token="buyer-token")
        )
        app.commercial_products = [
            CommercialProduct(
                product_id="prod-hermes",
                title="Hermes CLI 配置 10 次",
                agent_id="hermes",
                mode_key="cli",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=10,
                valid_until="2026-12-31T23:59:59+08:00",
                includes_dual_state=False,
                device_limit=2,
                is_listed=True,
            )
        ]
        app.buyer_product_id = type("Var", (), {"get": lambda _self: "prod-hermes"})()
        app.buyer_order_id = type("Var", (), {"set": lambda _self, value: setattr(app, "buyer_order_id_value", value)})()
        app.set_busy = lambda _busy: None
        app.buyer_purchase_statuses = {}
        app.refresh_buyer_purchase_status = lambda: None
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda message: setattr(app, "last_status", message)
        app.run_on_ui = lambda callback: callback()
        app.show_error_from_worker = lambda _title, _message: None
        infos = []
        app.show_info_from_worker = lambda title, message: infos.append((title, message))
        warnings = []
        app.notify_warning = lambda title, message: warnings.append((title, message))
        captured = {}
        original_request = installer_module.commercial_api_request_with_auth
        original_execute = installer_module.execute_commercial_api_with_trusted_certs
        original_thread = installer_module.threading.Thread

        class ImmediateThread:
            def __init__(self, target, args=(), daemon=None):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        try:
            def fake_request(action, contexts, **kwargs):
                captured["action"] = action
                captured["product_id"] = kwargs["product_id"]
                return object()

            installer_module.commercial_api_request_with_auth = fake_request
            installer_module.execute_commercial_api_with_trusted_certs = lambda _request: (
                {"order_id": "ord-hermes", "payment_url": "https://aitokenapi.cc/pay/ord-hermes"},
                "订单已创建",
            )
            installer_module.threading.Thread = ImmediateThread

            app.start_buyer_create_order()
        finally:
            installer_module.commercial_api_request_with_auth = original_request
            installer_module.execute_commercial_api_with_trusted_certs = original_execute
            installer_module.threading.Thread = original_thread

        self.assertEqual(warnings, [])
        self.assertEqual(captured["action"], "order_create")
        self.assertEqual(captured["product_id"], "prod-hermes")
        self.assertEqual(app.buyer_order_id_value, "ord-hermes")
        self.assertEqual(app.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT], NodeStatus.NEEDS_MANUAL)

    def _payment_flow_app(self):
        app = InstallerApp.__new__(InstallerApp)
        app.worker_running = False
        app.commercial_contexts = installer_module.create_buyer_contexts(
            UserContext(user_id="buyer-1", display_name="买家", role="buyer", token="buyer-token")
        )
        app.commercial_products = [
            CommercialProduct(
                product_id="prod-codex",
                title="Codex 普通配置 10 次",
                agent_id="codex",
                mode_key=CodexConfigMode.DIRECT_API.value,
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=10,
                valid_until="2099-12-31T23:59:59+08:00",
                includes_dual_state=False,
                device_limit=2,
                is_listed=True,
            )
        ]
        app.buyer_product_id = type("Var", (), {"get": lambda _self: "prod-codex"})()
        app.buyer_order_id = type(
            "Var", (), {"set": lambda _self, v: setattr(app, "boid", v), "get": lambda _self: getattr(app, "boid", "")}
        )()
        app.buyer_purchase_statuses = {}
        app.refresh_buyer_purchase_status = lambda: None
        app.sync_webview_state = lambda: None
        app.run_on_ui = lambda cb: cb()
        app.log_from_worker = lambda _m: None
        return app

    def _with_stubbed_commercial_api(self, response):
        original_request = installer_module.commercial_api_request_with_auth
        original_execute = installer_module.execute_commercial_api_with_trusted_certs
        installer_module.commercial_api_request_with_auth = lambda action, contexts, **kw: {"action": action, **kw}
        installer_module.execute_commercial_api_with_trusted_certs = lambda _r: (response, "服务端已处理")
        return original_request, original_execute

    def test_create_buyer_payment_order_returns_wap_url_and_qr(self) -> None:
        app = self._payment_flow_app()
        wap = "https://openapi.alipay.com/gateway.do?method=alipay.trade.wap.pay&product_code=QUICK_WAP_WAY"
        orig = self._with_stubbed_commercial_api({"order_id": "ord-1", "payment_url": wap})
        try:
            result = app.create_buyer_payment_order()
        finally:
            installer_module.commercial_api_request_with_auth, installer_module.execute_commercial_api_with_trusted_certs = orig
        self.assertTrue(result["success"])
        self.assertEqual(result["order_id"], "ord-1")
        self.assertEqual(result["payment_url"], wap)
        self.assertTrue(result["qr_data_url"].startswith("data:image/png;base64,"))
        self.assertEqual(app.boid, "ord-1")
        self.assertEqual(app.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT], NodeStatus.NEEDS_MANUAL)

    def test_create_buyer_payment_order_requires_payment_url(self) -> None:
        app = self._payment_flow_app()
        orig = self._with_stubbed_commercial_api({"order_id": "ord-1"})  # no payment_url
        try:
            result = app.create_buyer_payment_order()
        finally:
            installer_module.commercial_api_request_with_auth, installer_module.execute_commercial_api_with_trusted_certs = orig
        self.assertFalse(result["success"])
        self.assertIn("支付链接", result["message"])

    def test_query_buyer_payment_status_ready_when_paid_and_active(self) -> None:
        app = self._payment_flow_app()
        orig = self._with_stubbed_commercial_api(
            {"order_id": "ord-1", "payment_status": "paid", "entitlement_id": "ent-9", "entitlement_status": "active"}
        )
        try:
            result = app.query_buyer_payment_status("ord-1")
        finally:
            installer_module.commercial_api_request_with_auth, installer_module.execute_commercial_api_with_trusted_certs = orig
        self.assertTrue(result["success"])
        self.assertTrue(result["ready_for_delivery"])
        self.assertEqual(result["payment_status"], "paid")
        self.assertEqual(app.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT], NodeStatus.PASS)

    def test_query_buyer_payment_status_pending_when_created(self) -> None:
        app = self._payment_flow_app()
        orig = self._with_stubbed_commercial_api({"order_id": "ord-1", "payment_status": "created"})
        try:
            result = app.query_buyer_payment_status("ord-1")
        finally:
            installer_module.commercial_api_request_with_auth, installer_module.execute_commercial_api_with_trusted_certs = orig
        self.assertTrue(result["success"])
        self.assertFalse(result["ready_for_delivery"])
        self.assertEqual(result["payment_status"], "created")

    def test_refresh_recommended_agent_product_only_fills_buyer_product_field(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.commercial_products = [
            CommercialProduct(
                product_id="prod-codex",
                title="Codex 普通配置 10 次",
                agent_id="codex",
                mode_key=CodexConfigMode.DIRECT_API.value,
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=10,
                valid_until="2026-12-31T23:59:59+08:00",
                includes_dual_state=False,
                device_limit=2,
                is_listed=True,
            )
        ]

        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        app.buyer_product_id = FakeVar("")

        app.refresh_recommended_agent_product()

        self.assertEqual(app.buyer_product_id.value, "prod-codex")

    def test_communication_software_link_get_order_caches_payment_state_for_session_guard(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        class ImmediateThread:
            def __init__(self, target, args=(), daemon=None):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        app = InstallerApp.__new__(InstallerApp)
        app.worker_running = False
        app.commercial_contexts = installer_module.create_buyer_contexts(
            UserContext(user_id="buyer-1", display_name="买家", role="buyer", token="buyer-token")
        )
        app.deployer_auth = {"token": "deploy-token"}
        app.communication_software_link_order_id = FakeVar("svc-ord-1")
        app.communication_software_link_order_statuses = {}
        app.set_busy = lambda _busy: None
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda message: setattr(app, "last_status", message)
        app.run_on_ui = lambda callback: callback()
        app.show_error_from_worker = lambda _title, _message: None

        original_request = installer_module.commercial_api_request_with_auth
        original_execute = installer_module.execute_commercial_api_with_trusted_certs
        original_thread = installer_module.threading.Thread
        try:
            installer_module.commercial_api_request_with_auth = lambda *_args, **_kwargs: object()
            installer_module.execute_commercial_api_with_trusted_certs = lambda _request: (
                {"order_id": "svc-ord-1", "status": "paid", "charge_status": "paid", "payment_id": "pay-1"},
                "订单已支付",
            )
            installer_module.threading.Thread = ImmediateThread

            app.start_communication_software_link_get_order()
        finally:
            installer_module.commercial_api_request_with_auth = original_request
            installer_module.execute_commercial_api_with_trusted_certs = original_execute
            installer_module.threading.Thread = original_thread

        self.assertTrue(app.communication_software_link_order_statuses["svc-ord-1"]["session_allowed"])
        self.assertEqual(app.communication_software_link_order_statuses["svc-ord-1"]["payment_id"], "pay-1")
        self.assertEqual(app.last_status, "状态：连接通讯软件订单状态已刷新")

    def test_communication_software_link_create_order_surfaces_server_confirmation_boundary(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        app = InstallerApp.__new__(InstallerApp)
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_order_statuses = {}
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda message: setattr(app, "last_status", message)
        app.run_on_ui = lambda callback: callback()
        app.show_error_from_worker = lambda _title, _message: None
        app.sync_webview_state = lambda: None
        app.set_busy = lambda _busy: None
        infos = []
        app.show_info_from_worker = lambda title, message: infos.append((title, message))

        original_execute = installer_module.execute_commercial_api_with_trusted_certs
        try:
            installer_module.execute_commercial_api_with_trusted_certs = lambda _request: (
                {"order_id": "svc-ord-1", "status": "created", "payment_url": "https://aitokenapi.cc/pay/svc-ord-1"},
                "订单已创建",
            )
            app._communication_software_link_create_order_worker(object())
        finally:
            installer_module.execute_commercial_api_with_trusted_certs = original_execute

        self.assertEqual(app.communication_software_link_order_id.get(), "svc-ord-1")
        self.assertEqual(app.last_status, "状态：连接通讯软件订单创建请求已受理，支付/人工确认状态以服务端返回为准")
        self.assertEqual(infos[0][0], "连接通讯软件订单创建请求已受理")

    def test_communication_software_link_create_session_blocks_until_order_payment_or_manual_review_confirmed(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

        app = InstallerApp.__new__(InstallerApp)
        app.worker_running = False
        app.commercial_contexts = installer_module.create_buyer_contexts(
            UserContext(user_id="buyer-1", display_name="买家", role="buyer", token="buyer-token")
        )
        app.deployer_auth = {"token": "deploy-token"}
        app.communication_software_link_order_id = FakeVar("svc-ord-1")
        app.communication_software_link_order_statuses = {"svc-ord-1": {"session_allowed": False}}
        warnings = []

        original_warning = installer_module.messagebox.showwarning
        try:
            installer_module.messagebox.showwarning = lambda title, message: warnings.append((title, message))
            app.start_communication_software_link_create_session()
        finally:
            installer_module.messagebox.showwarning = original_warning

        self.assertEqual(warnings[0][0], "订单未确认")
        self.assertIn("已支付", warnings[0][1])

    def test_communication_software_link_create_session_allows_paid_order_status(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        class ImmediateThread:
            def __init__(self, target, args=(), daemon=None):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        app = InstallerApp.__new__(InstallerApp)
        app.worker_running = False
        app.commercial_contexts = installer_module.create_buyer_contexts(
            UserContext(user_id="buyer-1", display_name="买家", role="buyer", token="buyer-token")
        )
        app.deployer_auth = {"token": "deploy-token"}
        app.communication_software_link_order_id = FakeVar("svc-ord-1")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_agent_id = FakeVar("hermes")
        app.communication_software_link_channel = FakeVar("feishu")
        app.communication_software_link_agent_source = FakeVar("existing_local_agent")
        app.communication_software_link_platform_account_id = FakeVar("bot-account-1")
        app.communication_software_link_platform_chat_id = FakeVar("chat-1")
        app.communication_software_link_gateway_mode = FakeVar("official_bot")
        app.communication_software_link_order_statuses = {"svc-ord-1": {"session_allowed": True}}
        app.set_busy = lambda _busy: None
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda message: setattr(app, "last_status", message)
        app.run_on_ui = lambda callback: callback()
        app.show_error_from_worker = lambda _title, _message: None
        app.refresh_steps = lambda: None
        captured = {}

        original_request = installer_module.commercial_api_request_with_auth
        original_execute = installer_module.execute_commercial_api_with_trusted_certs
        original_thread = installer_module.threading.Thread
        try:
            def fake_request(action, contexts, **kwargs):
                captured["action"] = action
                captured["kwargs"] = kwargs
                return object()

            installer_module.commercial_api_request_with_auth = fake_request
            installer_module.execute_commercial_api_with_trusted_certs = lambda _request: (
                {"session_id": "csl-1"},
                "会话已创建",
            )
            installer_module.threading.Thread = ImmediateThread

            app.start_communication_software_link_create_session()
        finally:
            installer_module.commercial_api_request_with_auth = original_request
            installer_module.execute_commercial_api_with_trusted_certs = original_execute
            installer_module.threading.Thread = original_thread

        self.assertEqual(captured["action"], "communication_software_link_session_create")
        self.assertEqual(captured["kwargs"]["order_id"], "svc-ord-1")
        self.assertEqual(app.communication_software_link_session_id.get(), "csl-1")
        self.assertEqual(app.last_status, "状态：连接通讯软件配置会话创建请求已受理，最终会话状态以服务端返回为准")

    def test_communication_software_link_workers_backfill_server_state_fields(self) -> None:
        class FakeVar:
            def __init__(self, value="") -> None:
                self.value = value

            def get(self):
                return self.value

            def set(self, value) -> None:
                self.value = value

        app = InstallerApp.__new__(InstallerApp)
        app.communication_software_link_order_id = FakeVar("")
        app.communication_software_link_session_id = FakeVar("")
        app.communication_software_link_source_event_id = FakeVar("")
        app.communication_software_link_inbound_message_id = FakeVar("")
        app.communication_software_link_outbound_message_id = FakeVar("")
        app.communication_software_link_response_digest = FakeVar("")
        app.communication_software_link_evidence_url = FakeVar("")
        app.communication_software_link_order_statuses = {"svc-ord-1": {"session_allowed": True}}
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda message: setattr(app, "last_status", message)
        app.run_on_ui = lambda callback: callback()
        app.show_error_from_worker = lambda _title, _message: None
        app.refresh_steps = lambda: None
        app.set_busy = lambda _busy: None

        responses = iter(
            [
                (
                    {
                        "service_order_id": "svc-ord-1",
                        "communication_software_link_session_id": "csl-1",
                        "session_status": "ready",
                    },
                    "会话已创建",
                ),
                (
                    {
                        "order_id": "svc-ord-1",
                        "session_id": "csl-1",
                        "status": "acceptance_submitted",
                        "source_event_id": "evt-1",
                        "inbound_platform_message_id": "in-msg-1",
                        "outbound_platform_message_id": "out-msg-1",
                        "agent_response_digest": "sha256:reply",
                        "evidence_url": "https://aitokenapi.cc/evidence/evt-1",
                    },
                    "验收证据已提交",
                ),
            ]
        )

        original_execute = installer_module.execute_commercial_api_with_trusted_certs
        try:
            installer_module.execute_commercial_api_with_trusted_certs = lambda _request: next(responses)
            app._communication_software_link_create_session_worker(object())
            app._communication_software_link_generic_worker("验收证据已提交", object())
        finally:
            installer_module.execute_commercial_api_with_trusted_certs = original_execute

        self.assertEqual(app.communication_software_link_order_id.get(), "svc-ord-1")
        self.assertEqual(app.communication_software_link_session_id.get(), "csl-1")
        self.assertEqual(app.communication_software_link_source_event_id.get(), "evt-1")
        self.assertEqual(app.communication_software_link_inbound_message_id.get(), "in-msg-1")
        self.assertEqual(app.communication_software_link_outbound_message_id.get(), "out-msg-1")
        self.assertEqual(app.communication_software_link_response_digest.get(), "sha256:reply")
        self.assertEqual(app.communication_software_link_evidence_url.get(), "https://aitokenapi.cc/evidence/evt-1")
        self.assertEqual(app.communication_software_link_order_statuses["svc-ord-1"]["session_id"], "csl-1")
        self.assertEqual(app.communication_software_link_order_statuses["svc-ord-1"]["communication_software_link_status"], "acceptance_submitted")
        self.assertEqual(app.last_status, "状态：连接通讯软件验收证据提交请求已受理，等待服务端真实验收")

    def test_buyer_purchase_status_shows_key_creation_gap_and_balance_hint_when_no_products(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.commercial_products = []
        app.buyer_purchase_statuses = {}

        class FakeLabel:
            def __init__(self):
                self.text = ""

            def configure(self, **kwargs):
                self.text = kwargs.get("text", self.text)

        app.buyer_product_summary_label = FakeLabel()
        app.buyer_purchase_status_label = FakeLabel()

        app.refresh_buyer_purchase_status()

        self.assertIn("不能在本工具内创建订单", app.buyer_product_summary_label.text)
        self.assertIn("打开 API Key 创建页面", app.buyer_purchase_status_label.text)
        self.assertIn("余额不足", app.buyer_purchase_status_label.text)

    def test_open_url_prefers_embedded_webview_for_key_and_payment_pages(self) -> None:
        opened = {}
        original_try = installer_module.try_open_embedded_webview
        original_browser = installer_module.webbrowser.open
        try:
            installer_module.try_open_embedded_webview = (
                lambda url, title="", **_kwargs: opened.setdefault("embedded", (url, title)) or True
            )
            installer_module.webbrowser.open = lambda url: opened.setdefault("browser", url) or True

            result = installer_module.open_url(KEY_CREATE_URL)
        finally:
            installer_module.try_open_embedded_webview = original_try
            installer_module.webbrowser.open = original_browser

        self.assertEqual(opened["embedded"][0], KEY_CREATE_URL)
        self.assertNotIn("browser", opened)
        self.assertTrue(result.ok)
        self.assertEqual(result.method, "embedded_webview")
        self.assertIn("WebView", result.message)

    def test_open_url_blocks_customer_site_when_embedded_webview_unavailable(self) -> None:
        opened = {}
        original_try = installer_module.try_open_embedded_webview
        original_browser = installer_module.webbrowser.open
        original_webview = installer_module.webview
        try:
            installer_module.webview = None
            installer_module.try_open_embedded_webview = lambda _url, title="", **_kwargs: False
            installer_module.webbrowser.open = lambda url: opened.setdefault("browser", url) or True

            result = installer_module.open_url("https://aitokenapi.cc/pay/demo")
        finally:
            installer_module.try_open_embedded_webview = original_try
            installer_module.webbrowser.open = original_browser
            installer_module.webview = original_webview

        self.assertNotIn("browser", opened)
        self.assertFalse(result.ok)
        self.assertEqual(result.method, "embedded_webview_blocked")
        self.assertIn("未加载 pywebview", result.message)

    def test_customer_instruction_does_not_claim_system_browser_fallback_for_customer_site(self) -> None:
        source = (ROOT / "docs" / "发送客户说明.txt").read_text(encoding="utf-8")

        self.assertNotIn("回退到系统浏览器", source)
        self.assertIn("阻断", source)
        self.assertIn("不能算完成内嵌网页闭环", source)

    def test_ui_does_not_hydrate_backend_api_key_into_dom_value(self) -> None:
        ui_shell = ROOT / "src" / "ui" / "index.html"
        py_source = (ROOT / "src" / "panghu_ai_client.py").read_text(encoding="utf-8")

        self.assertTrue(ui_shell.exists())
        self.assertIn('"apiKeyValue": ""', py_source)
        self.assertIn('"apiKeyPresent": bool(self.app.api_key.get().strip())', py_source)
        self.assertIn('"apiKeyMasked": mask_key(self.app.api_key.get().strip())', py_source)
        self.assertNotIn('"apiKeyValue": self.app.api_key.get()', py_source)
        self.assertNotIn('"apiKeyValue": self.api_key.get()', py_source)

    def test_login_entry_is_unified_and_not_buyer_agent_mode_split(self) -> None:
        source = (ROOT / "src" / "panghu_ai_client.py").read_text(encoding="utf-8")

        login_source = source[source.index("def _build_login_frame") : source.index("def _build_buyer_purchase_panel")]
        self.assertIn("登录胖虎AI账号", login_source)
        self.assertIn("登录并激活工具", login_source)
        self.assertNotIn("买家模式", login_source)
        self.assertNotIn("代理模式", login_source)
        self.assertNotIn("代理远程协助临时会话", login_source)
        self.assertNotIn("_build_agent_assist_panel(login_card)", login_source)

    def test_legacy_agent_assist_is_not_customer_visible_or_delivery_owner(self) -> None:
        source = (ROOT / "src" / "panghu_ai_client.py").read_text(encoding="utf-8")

        forbidden_customer_terms = [
            "买家模式",
            "代理模式",
            "代理远程协助临时会话",
            "绑定目标买家",
            "退出并清空代理资料",
        ]
        for term in forbidden_customer_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

        contexts = deployment_commercial_contexts({"id": "buyer-self", "username": "本人"})
        self.assertEqual(contexts.operator.user_id, "buyer-self")
        self.assertEqual(contexts.target_buyer.user_id, "buyer-self")

    def test_top_modules_and_side_nav_contract(self) -> None:
        self.assertEqual(
            [title for _module_id, title, _subtitle in installer_module.TOP_MODULES],
            ["配置Agent", "胖虎AI网站", "增值业务", "代理中心"],
        )
        self.assertEqual(
            [title for _item_id, title, _subtitle in installer_module.MODULE_SIDE_NAV_ITEMS[installer_module.MODULE_AGENT]],
            [title for _idx, title, _subtitle in installer_module.FLOW_STEPS],
        )
        for module_id in (installer_module.MODULE_SITE, installer_module.MODULE_VALUE_ADDED, installer_module.MODULE_COURSES):
            self.assertNotEqual(
                [title for _item_id, title, _subtitle in installer_module.MODULE_SIDE_NAV_ITEMS[module_id]],
                [title for _idx, title, _subtitle in installer_module.FLOW_STEPS],
            )
        self.assertEqual(installer_module.MODULE_SIDE_NAV_ITEMS[installer_module.MODULE_SITE][0][0], "account")
        self.assertEqual(installer_module.MODULE_SIDE_NAV_ITEMS[installer_module.MODULE_SITE][0][1], "控制台")
        self.assertEqual(installer_module.MODULE_PAGE_META[installer_module.MODULE_SITE]["account"][1], installer_module.DEFAULT_BASE_URL + "/console")
        self.assertEqual(
            [title for _item_id, title, _subtitle in installer_module.MODULE_SIDE_NAV_ITEMS[installer_module.MODULE_COURSES]],
            ["代理总览", "下游客户", "token 返佣", "激活返佣", "安装返佣", "工具代理后端", "招商介绍", "代理规则"],
        )
        for item_id, _title, _subtitle in installer_module.MODULE_SIDE_NAV_ITEMS[installer_module.MODULE_COURSES]:
            self.assertIn(item_id, installer_module.MODULE_PAGE_META[installer_module.MODULE_COURSES])
            self.assertIn(item_id, installer_module.MODULE_ACTION_CARDS[installer_module.MODULE_COURSES])

    def test_login_gate_and_wizard_switch_visibility(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.logged_in_user = None
        app.deployer_auth = None

        class FakeWidget:
            def __init__(self):
                self.visible = False
                self.text = None

            def pack(self, **_kwargs):
                self.visible = True

            def pack_forget(self):
                self.visible = False

            def winfo_ismapped(self):
                return self.visible

            def configure(self, **kwargs):
                if "text" in kwargs:
                    self.text = kwargs["text"]

        app.console_outer = FakeWidget()
        app.console_shell = FakeWidget()
        app.log_shell = FakeWidget()
        app.gate_shell = FakeWidget()
        app.topbar_remaining_label = FakeWidget()
        app.update_button = FakeWidget()
        app.topbar_account_label = FakeWidget()

        app.show_login_gate()
        self.assertTrue(app.gate_shell.visible)
        self.assertFalse(app.console_outer.visible)
        self.assertFalse(app.console_shell.visible)
        self.assertFalse(app.log_shell.visible)
        self.assertFalse(app.topbar_remaining_label.visible)
        self.assertFalse(app.update_button.visible)
        self.assertEqual(app.topbar_account_label.text, "账号：未登录")

        app.logged_in_user = {"username": "buyer-demo"}
        app.deployer_auth = {"token": "token-demo"}
        app.show_wizard()
        self.assertFalse(app.gate_shell.visible)
        self.assertTrue(app.console_outer.visible)
        self.assertTrue(app.console_shell.visible)
        self.assertTrue(app.log_shell.visible)
        self.assertTrue(app.topbar_remaining_label.visible)
        self.assertTrue(app.update_button.visible)

    def test_wizard_shell_packs_log_before_console(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        calls = []

        class FakeWidget:
            def __init__(self, name):
                self.name = name
                self.visible = False

            def pack(self, **_kwargs):
                self.visible = True
                calls.append(self.name)

            def pack_forget(self):
                self.visible = False

            def winfo_ismapped(self):
                return self.visible

        app.gate_shell = FakeWidget("gate")
        app.log_shell = FakeWidget("log")
        app.console_outer = FakeWidget("console_outer")
        app.console_shell = FakeWidget("console_shell")
        app.topbar_domain_label = FakeWidget("domain")
        app.topbar_remaining_label = FakeWidget("remaining")
        app.update_button = FakeWidget("update")
        app._sync_surface_layouts = lambda: None

        app._show_wizard_shell()

        self.assertEqual(calls[:3], ["log", "console_outer", "console_shell"])

    def test_ui_layout_contracts_prevent_visual_regression(self) -> None:
        source = (ROOT / "src" / "panghu_ai_client.py").read_text(encoding="utf-8")
        self.assertIn('root.geometry("1400x900")', source)
        self.assertIn("LEFT_PANEL_WIDTH = 220", source)
        self.assertIn("RIGHT_PANEL_WIDTH = 300", source)
        self.assertIn("grid_columnconfigure(0, minsize=LEFT_PANEL_WIDTH)", source)
        self.assertIn("grid_columnconfigure(2, minsize=RIGHT_PANEL_WIDTH)", source)
        self.assertIn("width=RIGHT_PANEL_WIDTH", source)
        self.assertIn('PRIMARY = "#0071e3"', source)
        self.assertIn("SIDEBAR_BG", source)
        self.assertIn("login_card = tk.Frame(login_shell, bg=CARD_BG, padx=40, pady=35", source)
        self.assertIn("self.login_card = login_card", source)
        self.assertIn("show_login_gate", source)
        self.assertIn("内置网站服务区", source)
        self.assertIn("[title for _module_id, title, _subtitle in TOP_MODULES]", source)
        self.assertIn("def _build_module_nav", source)
        self.assertIn("def switch_module", source)
        self.assertIn("def _build_non_agent_module_frame", source)
        self.assertNotIn("login_card.pack_propagate(False)", source)
        self.assertNotIn("height=548", source)
        self.assertIn("def enable_windows_dpi_awareness()", source)
        self.assertIn("canvas.update_idletasks()", source)

    def test_customer_web_modules_keep_delivery_right_rail_visible(self) -> None:
        ui_shell = ROOT / "src" / "ui" / "index.html"
        source = (ROOT / "src" / "panghu_ai_client.py").read_text(encoding="utf-8")

        self.assertTrue(ui_shell.exists())
        self.assertIn("MODULE_SITE", source)
        self.assertIn("MODULE_VALUE_ADDED", source)
        self.assertIn("MODULE_COURSES", source)
        self.assertIn("def _build_non_agent_module_frame", source)
        self.assertIn("MODULE_PAGE_META", source)
        self.assertIn("MODULE_ACTION_CARDS", source)
        self.assertIn("网站服务端", source)
        self.assertIn("服务端商品", source)
        self.assertIn("agent_center", source)

    def test_webview_backend_bridge_contracts_are_not_dead_buttons(self) -> None:
        py_source = (ROOT / "src" / "panghu_ai_client.py").read_text(encoding="utf-8")
        html = (ROOT / "src" / "ui" / "index.html").read_text(encoding="utf-8")

        self.assertTrue((ROOT / "src" / "ui" / "index.html").exists())
        self.assertIn("def start_official_chatgpt_config(self):", py_source)
        self.assertNotIn("def start_official_mode_config(self):", py_source)
        self.assertIn("def refresh_agent_center(self):", py_source)
        self.assertIn("def refresh_agent_center_detail(self):", py_source)
        self.assertIn("def refresh_agent_center(self):", py_source)
        self.assertIn("def refresh_agent_center_detail(self):", py_source)
        self.assertIn("def current_agent_center_state(self) -> dict:", py_source)
        self.assertIn('"agentCenter": agent_center_state', py_source)
        self.assertIn('"buyerPurchase": self.app.current_buyer_purchase_state()', py_source)
        self.assertIn('"buyerPurchase": self.current_buyer_purchase_state()', py_source)
        self.assertIn('"communicationSoftwareLink": self.app.current_communication_software_link_web_state()', py_source)
        self.assertIn('"communicationSoftwareLink": self.current_communication_software_link_web_state()', py_source)
        self.assertIn('"state": self.current_communication_software_link_state()', py_source)
        self.assertIn("parse_agent_center_snapshot_data", py_source)
        self.assertIn("self.agent_center_live_data = parse_agent_center_snapshot_data(center)", py_source)
        self.assertIn("valueAddedServices", py_source)
        self.assertIn("manifest_value_added_services", py_source)
        self.assertIn("self.value_added_services = manifest_value_added_services(manifest)", py_source)
        self.assertIn('return {"success": True, "accepted": True, "message": message}', py_source)
        self.assertIn("def current_communication_software_link_web_state(self) -> dict:", py_source)
        self.assertIn("def communication_software_link_one_click_connect(self, payload=None):", py_source)
        self.assertIn("def start_communication_software_link_one_click_connect(self) -> None:", py_source)
        self.assertIn("def run_communication_software_link_one_click_connect(self) -> dict[str, str]:", py_source)
        self.assertIn('["开始部署与配置","start_deploy"]', html)
        self.assertIn("window.pywebview.api.${api}()", html)
        self.assertIn("function setAgentMode(id, mode)", html)
        self.assertIn("window.pywebview.api.set_agent_mode(id, mode)", html)
        self.assertIn("agentModeOptions", html)
        self.assertIn("state.agentMode", html)
        self.assertIn("communication_software_link_one_click_connect", html)
        self.assertIn("submitCSLOneClickConnect", html)
        self.assertIn("window.pywebview.api.communication_software_link_one_click_connect(state.communicationSoftwareLink)", html)
        self.assertIn("一键连接并本地预检", html)
        self.assertIn("本地预检不能替代通讯软件平台回调", html)
        self.assertNotIn("一键连接并提交验收", html)
        self.assertNotIn("一键连接已受理：将按订单、配置会话、测试、Runtime 证据和服务端验收顺序执行", py_source)
        self.assertIn("communication_software_link_run_local_runtime_test", html)
        self.assertIn("communication_software_link_disable(state.communicationSoftwareLink)", html)
        self.assertNotIn("communication_software_link_disable({ order_id:", html)
        self.assertIn('id="cslServiceProductId"', html)
        self.assertIn('id="cslAgentId"', html)
        self.assertIn('id="cslPlatformAccountId"', html)
        self.assertIn('id="cslPlatformChatId"', html)
        self.assertIn('id="cslGatewayMode"', html)
        self.assertIn('id="cslTestPrompt"', html)
        self.assertIn("serviceProductId:", html)
        self.assertIn("platformAccountId:", html)
        self.assertIn("testPrompt:", html)

    def test_webview_communication_software_link_guides_buyer_robot_setup_without_completion_claim(self) -> None:
        html = (ROOT / "src" / "ui" / "index.html").read_text(encoding="utf-8")

        self.assertIn("打开官方页面创建/配置机器人，复制机器人 ID、群聊/会话 ID、验签密钥或回调设置回到本客户端", html)
        self.assertIn("https://open.feishu.cn/app?lang=zh-CN", html)
        self.assertIn("https://open.dingtalk.com/document/robots/custom-robot-access", html)
        self.assertIn("https://bot.qq.com/", html)
        self.assertIn("https://work.weixin.qq.com/", html)
        self.assertIn("platform_account_id", html)
        self.assertIn("platform_chat_id", html)
        self.assertIn("gateway_mode", html)
        self.assertIn("回调地址", html)
        self.assertIn("验签密钥", html)
        self.assertIn("敏感信息只发送给服务端", html)
        self.assertIn("不要在本客户端输入官方账号密码", html)
        self.assertIn("本地不会硬编码真实接入成功", html)
        self.assertNotIn("真实接入已完成", html)
        self.assertNotIn("可提交服务端真实验收", html)

    def test_webview_customer_asset_does_not_ship_demo_accounts_or_fake_agent_center_sync(self) -> None:
        html = (ROOT / "src" / "ui" / "index.html").read_text(encoding="utf-8")

        forbidden_literals = [
            "test_buyer@gmail.com",
            "agent_master",
            "120次",
            "3台",
            "已完成检验",
            "通道激活",
            "已连接",
            "已建立确权数据通道",
            "连接检测</td><td class=\"ok\"",
            "服务端快照已返回",
            "账目同步连接已建立",
        ]

        for literal in forbidden_literals:
            self.assertNotIn(literal, html)

    def test_value_added_services_frontend_is_manifest_driven_when_server_catalog_exists(self) -> None:
        html = (ROOT / "src" / "ui" / "index.html").read_text(encoding="utf-8")

        self.assertIn("valueAddedServices: []", html)
        self.assertIn("function valueAddedServiceMap()", html)
        self.assertIn("function currentSubnavItems(mod)", html)
        self.assertIn("function currentPageMeta(mod, key)", html)
        self.assertIn("客户端只打开服务端入口，不保存短信、Session Token 或履约密钥", html)

    def test_online_update_start_failure_message_is_sanitized(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.set_busy = lambda _busy: None
        errors = []
        original_start = installer_module.start_online_update
        original_showerror = installer_module.messagebox.showerror
        try:
            installer_module.start_online_update = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("token secret-token api_key=sk-live-secret order_id=ord-real")
            )
            installer_module.messagebox.showerror = lambda title, message: errors.append((title, message))

            app.confirm_and_start_online_update(Path("update.zip"))
        finally:
            installer_module.start_online_update = original_start
            installer_module.messagebox.showerror = original_showerror

        self.assertEqual(errors[0][0], "在线更新失败")
        self.assertNotIn("secret-token", errors[0][1])
        self.assertNotIn("sk-live-secret", errors[0][1])
        self.assertNotIn("ord-real", errors[0][1])
        self.assertIn("***", errors[0][1])

    def test_config_only_worker_error_message_includes_diagnostic_code(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.cookie_jar = None
        app.next_diagnostic_code = lambda: "PH-CFG-ERR-CONFIG"
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda _message: None
        app.run_on_ui = lambda callback: callback()
        app.set_busy = lambda _busy: None
        captured_errors = []
        app.show_error_from_worker = lambda title, message: captured_errors.append((title, message))
        original_fetch = installer_module.fetch_deployer_manifest
        original_fail_cleanup = installer_module.fail_unfinished_config_sessions
        try:
            installer_module.fetch_deployer_manifest = lambda *_args, **_kwargs: (
                False,
                "token secret-token api_key=sk-live-secret",
                {},
            )
            installer_module.fail_unfinished_config_sessions = lambda *_args, **_kwargs: []

            app._config_only_worker(
                user={"id": "buyer-1"},
                deployer_auth={"token": "buyer-token"},
                contexts="contexts",
                api_key="sk-live-secret",
                base_url="https://aitokenapi.cc",
                model="gpt-5.4",
                skip_test=True,
                open_app=False,
                mode=installer_module.CodexConfigMode.DIRECT_API,
            )
        finally:
            installer_module.fetch_deployer_manifest = original_fetch
            installer_module.fail_unfinished_config_sessions = original_fail_cleanup

        self.assertEqual(captured_errors[0][0], "配置修复失败")
        self.assertIn("PH-CFG-ERR-CONFIG", captured_errors[0][1])
        self.assertNotIn("secret-token", captured_errors[0][1])
        self.assertNotIn("sk-live-secret", captured_errors[0][1])

    def test_deploy_worker_error_message_includes_diagnostic_code(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.cookie_jar = None
        app.next_diagnostic_code = lambda: "PH-CFG-ERR-DEPLOY"
        app.log_from_worker = lambda _message: None
        app.set_status_from_worker = lambda _message: None
        app.run_on_ui = lambda callback: callback()
        app.set_busy = lambda _busy: None
        captured_errors = []
        app.show_error_from_worker = lambda title, message: captured_errors.append((title, message))
        contexts = deployment_commercial_contexts({"id": "buyer-1"})
        original_fetch = installer_module.fetch_deployer_manifest
        original_fail_cleanup = installer_module.fail_unfinished_config_sessions
        try:
            installer_module.fetch_deployer_manifest = lambda *_args, **_kwargs: (
                False,
                "order_id=ord-secret token secret-token",
                {},
            )
            installer_module.fail_unfinished_config_sessions = lambda *_args, **_kwargs: []

            app._deploy_worker(
                selected=[(installer_module.AGENTS[0], "cli")],
                user={"id": "buyer-1"},
                deployer_auth={"token": "buyer-token"},
                contexts=contexts,
                api_key="sk-live-secret",
                base_url="https://aitokenapi.cc",
                model="gpt-5.4",
                skip_test=True,
                open_app=False,
            )
        finally:
            installer_module.fetch_deployer_manifest = original_fetch
            installer_module.fail_unfinished_config_sessions = original_fail_cleanup

        self.assertEqual(captured_errors[0][0], "部署失败")
        self.assertIn("PH-CFG-ERR-DEPLOY", captured_errors[0][1])
        self.assertNotIn("ord-secret", captured_errors[0][1])
        self.assertNotIn("secret-token", captured_errors[0][1])

    def test_deploy_worker_logs_non_codex_config_plan_without_success_commit(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.cookie_jar = None
        app.next_diagnostic_code = lambda: "PH-CFG-OPENCLAW"
        logs = []
        app.log_from_worker = logs.append
        app.set_status_from_worker = lambda _message: None
        app.run_on_ui = lambda callback: callback()
        app.set_busy = lambda _busy: None
        app.show_error_from_worker = lambda _title, _message: None
        app.show_info_from_worker = lambda _title, _message: None
        app.deployer_manifest = {}
        app.commercial_capabilities = {}
        app.commercial_products = []
        app.commercial_entitlements = []
        app.refresh_commercial_summary = lambda: None
        contexts = deployment_commercial_contexts({"id": "buyer-1"})
        openclaw = next(agent for agent in installer_module.AGENTS if agent.id == "openclaw")

        original_fetch = installer_module.fetch_deployer_manifest
        original_trust = installer_module.ensure_commercial_manifest_trusted
        original_install = installer_module.install_agent
        original_apply_config = installer_module.apply_agent_config
        original_version = installer_module.version_for
        original_reserve = installer_module.execute_config_session_reserve
        original_fail = installer_module.execute_config_session_fail
        try:
            installer_module.fetch_deployer_manifest = lambda *_args, **_kwargs: (
                True,
                "manifest ok",
                {
                    "agents": [{"id": "openclaw", "delivery_scope": "full_config", "full_config_allowed": True}],
                    "entitlements": [
                        {
                            "entitlement_id": "ent-openclaw",
                            "buyer_user_id": "buyer-1",
                            "agent_id": "openclaw",
                            "mode_key": "cli",
                            "valid_until": "2099-01-01",
                            "delivery_scope": "full_config",
                            "status": "active",
                            "remaining_uses": 1,
                            "device_limit": 1,
                        }
                    ],
                },
            )
            installer_module.ensure_commercial_manifest_trusted = lambda _manifest: None
            installer_module.install_agent = lambda _agent, _mode, _log: True
            installer_module.apply_agent_config = lambda _agent, _mode, _api_key, _model, _log: True
            installer_module.version_for = lambda _command: (False, "")
            installer_module.execute_config_session_reserve = lambda **_kwargs: ("cfg-openclaw", "reserved")
            installer_module.execute_config_session_fail = lambda *args, **_kwargs: ({}, "failed-without-deduct")

            app._deploy_worker(
                selected=[(openclaw, "cli")],
                user={"id": "buyer-1"},
                deployer_auth={"token": "buyer-token"},
                contexts=contexts,
                api_key="sk-live-secret",
                base_url="https://aitokenapi.cc",
                model="gpt-5.4",
                skip_test=True,
                open_app=False,
            )
        finally:
            installer_module.fetch_deployer_manifest = original_fetch
            installer_module.ensure_commercial_manifest_trusted = original_trust
            installer_module.install_agent = original_install
            installer_module.apply_agent_config = original_apply_config
            installer_module.version_for = original_version
            installer_module.execute_config_session_reserve = original_reserve
            installer_module.execute_config_session_fail = original_fail

        log_text = "\n".join(logs)
        self.assertIn("openclaw/cli：写入胖虎AI网关 https://aitokenapi.cc/v1", log_text)
        self.assertIn("第三方通道默认跳过", log_text)
        self.assertIn("最小对话验证", log_text)
        self.assertIn("未形成完整交付；已提交失败且不扣次", log_text)

    def test_deploy_worker_completes_non_codex_only_after_dialogue_probe_passes(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.cookie_jar = None
        app.next_diagnostic_code = lambda: "PH-CFG-HERMES"
        logs = []
        app.log_from_worker = logs.append
        app.set_status_from_worker = lambda _message: None
        app.run_on_ui = lambda callback: callback()
        app.set_busy = lambda _busy: None
        app.show_error_from_worker = lambda _title, _message: None
        app.show_info_from_worker = lambda _title, _message: None
        app.deployer_manifest = {}
        app.commercial_capabilities = {}
        app.commercial_products = []
        app.commercial_entitlements = []
        app.refresh_commercial_summary = lambda: None
        contexts = deployment_commercial_contexts({"id": "buyer-1"})
        hermes = next(agent for agent in installer_module.AGENTS if agent.id == "hermes")
        completed = []
        failed = []

        original_fetch = installer_module.fetch_deployer_manifest
        original_trust = installer_module.ensure_commercial_manifest_trusted
        original_install = installer_module.install_agent
        original_apply_config = installer_module.apply_agent_config
        original_version = installer_module.version_for
        original_probe = installer_module.run_agent_dialogue_probe
        original_reserve = installer_module.execute_config_session_reserve
        original_complete = installer_module.execute_config_session_complete
        original_fail = installer_module.execute_config_session_fail
        try:
            installer_module.fetch_deployer_manifest = lambda *_args, **_kwargs: (
                True,
                "manifest ok",
                {
                    "agents": [{"id": "hermes", "delivery_scope": "full_config", "full_config_allowed": True}],
                    "entitlements": [
                        {
                            "entitlement_id": "ent-hermes",
                            "buyer_user_id": "buyer-1",
                            "agent_id": "hermes",
                            "mode_key": "cli",
                            "valid_until": "2099-01-01",
                            "delivery_scope": "full_config",
                            "status": "active",
                            "remaining_uses": 1,
                            "device_limit": 1,
                        }
                    ],
                },
            )
            installer_module.ensure_commercial_manifest_trusted = lambda _manifest: None
            installer_module.install_agent = lambda _agent, _mode, _log: True
            installer_module.apply_agent_config = lambda _agent, _mode, _api_key, _model, _log: True
            installer_module.version_for = lambda _command: (True, "hermes 1.0")
            installer_module.run_agent_dialogue_probe = lambda _agent, _mode, _model: (True, "胖虎AI配置验证成功")
            installer_module.execute_config_session_reserve = lambda **_kwargs: ("cfg-hermes", "reserved")
            installer_module.execute_config_session_complete = lambda *args, **_kwargs: (
                completed.append(args[0]),
                "completed-with-deduct",
            )
            installer_module.execute_config_session_fail = lambda *args, **_kwargs: (
                failed.append(args[0]),
                "failed-without-deduct",
            )

            app._deploy_worker(
                selected=[(hermes, "cli")],
                user={"id": "buyer-1"},
                deployer_auth={"token": "buyer-token"},
                contexts=contexts,
                api_key="sk-live-secret",
                base_url="https://aitokenapi.cc",
                model="gpt-5.4",
                skip_test=True,
                open_app=False,
            )
        finally:
            installer_module.fetch_deployer_manifest = original_fetch
            installer_module.ensure_commercial_manifest_trusted = original_trust
            installer_module.install_agent = original_install
            installer_module.apply_agent_config = original_apply_config
            installer_module.version_for = original_version
            installer_module.run_agent_dialogue_probe = original_probe
            installer_module.execute_config_session_reserve = original_reserve
            installer_module.execute_config_session_complete = original_complete
            installer_module.execute_config_session_fail = original_fail

        log_text = "\n".join(logs)
        self.assertEqual(completed, ["cfg-hermes"])
        self.assertEqual(failed, [])
        self.assertIn("Hermes/cli 启动检测通过", log_text)
        self.assertIn("最小对话已通过；商业交付成功已提交", log_text)

    def test_deploy_worker_does_not_complete_client_scope_with_cli_probe(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        app.cookie_jar = None
        app.next_diagnostic_code = lambda: "PH-CFG-HERMES-CLIENT"
        logs = []
        app.log_from_worker = logs.append
        app.set_status_from_worker = lambda _message: None
        app.run_on_ui = lambda callback: callback()
        app.set_busy = lambda _busy: None
        app.show_error_from_worker = lambda _title, _message: None
        app.show_info_from_worker = lambda _title, _message: None
        app.deployer_manifest = {}
        app.commercial_capabilities = {}
        app.commercial_products = []
        app.commercial_entitlements = []
        app.value_added_services = []
        app.refresh_commercial_summary = lambda: None
        contexts = deployment_commercial_contexts({"id": "buyer-1"})
        hermes = next(agent for agent in installer_module.AGENTS if agent.id == "hermes")
        completed = []
        failed = []

        original_fetch = installer_module.fetch_deployer_manifest
        original_trust = installer_module.ensure_commercial_manifest_trusted
        original_install = installer_module.install_agent
        original_apply_config = installer_module.apply_agent_config
        original_version = installer_module.version_for
        original_probe = installer_module.run_agent_dialogue_probe
        original_reserve = installer_module.execute_config_session_reserve
        original_complete = installer_module.execute_config_session_complete
        original_fail = installer_module.execute_config_session_fail
        original_write_guide = installer_module.write_agent_setup_guide
        original_write_matrix = installer_module.write_customer_agent_acceptance_matrix
        try:
            installer_module.fetch_deployer_manifest = lambda *_args, **_kwargs: (
                True,
                "manifest ok",
                {
                    "agents": [{"id": "hermes", "delivery_scope": "full_config", "full_config_allowed": True}],
                    "entitlements": [
                        {
                            "entitlement_id": "ent-hermes-client",
                            "buyer_user_id": "buyer-1",
                            "agent_id": "hermes",
                            "mode_key": "client",
                            "valid_until": "2099-01-01",
                            "delivery_scope": "full_config",
                            "status": "active",
                            "remaining_uses": 1,
                            "device_limit": 1,
                        }
                    ],
                },
            )
            installer_module.ensure_commercial_manifest_trusted = lambda _manifest: None
            installer_module.install_agent = lambda _agent, _mode, _log: True
            installer_module.apply_agent_config = lambda _agent, _mode, _api_key, _model, _log: True
            installer_module.version_for = lambda _command: (True, "hermes cli 1.0")
            installer_module.run_agent_dialogue_probe = lambda _agent, _mode, _model: (True, "胖虎AI配置验证成功")
            installer_module.execute_config_session_reserve = lambda **_kwargs: ("cfg-hermes-client", "reserved")
            installer_module.execute_config_session_complete = lambda *args, **_kwargs: (
                completed.append(args[0]),
                "completed-with-deduct",
            )
            installer_module.execute_config_session_fail = lambda *args, **_kwargs: (
                failed.append(args[0]),
                "failed-without-deduct",
            )
            installer_module.write_agent_setup_guide = lambda *_args, **_kwargs: Path("NOOP")
            installer_module.write_customer_agent_acceptance_matrix = lambda *_args, **_kwargs: Path("NOOP")

            app._deploy_worker(
                selected=[(hermes, "client")],
                user={"id": "buyer-1"},
                deployer_auth={"token": "buyer-token"},
                contexts=contexts,
                api_key="sk-live-secret",
                base_url="https://aitokenapi.cc",
                model="gpt-5.4",
                skip_test=True,
                open_app=False,
            )
        finally:
            installer_module.fetch_deployer_manifest = original_fetch
            installer_module.ensure_commercial_manifest_trusted = original_trust
            installer_module.install_agent = original_install
            installer_module.apply_agent_config = original_apply_config
            installer_module.version_for = original_version
            installer_module.run_agent_dialogue_probe = original_probe
            installer_module.execute_config_session_reserve = original_reserve
            installer_module.execute_config_session_complete = original_complete
            installer_module.execute_config_session_fail = original_fail
            installer_module.write_agent_setup_guide = original_write_guide
            installer_module.write_customer_agent_acceptance_matrix = original_write_matrix

        log_text = "\n".join(logs)
        self.assertEqual(completed, [])
        self.assertEqual(failed, ["cfg-hermes-client"])
        self.assertIn("只销售 CLI 交付；client scope 不适用", log_text)
        self.assertNotIn("Hermes/client 最小对话已通过；商业交付成功已提交", log_text)

    def _run_client_scope_deploy(self, agent_id: str, session_id: str, client_ok: bool, client_message: str):
        """驱动 _deploy_worker 跑一个 client-scope 交付，返回 (completed, failed, log_text)。

        产品决策：官方客户端已安装 + 配置写入 = 客户端交付合格并扣次（不做联网对话验收）。
        """
        app = InstallerApp.__new__(InstallerApp)
        app.cookie_jar = None
        app.next_diagnostic_code = lambda: f"PH-CFG-{agent_id.upper()}-CLIENT"
        logs = []
        app.log_from_worker = logs.append
        app.set_status_from_worker = lambda _message: None
        app.run_on_ui = lambda callback: callback()
        app.set_busy = lambda _busy: None
        app.show_error_from_worker = lambda _title, _message: None
        app.show_info_from_worker = lambda _title, _message: None
        app.deployer_manifest = {}
        app.commercial_capabilities = {}
        app.commercial_products = []
        app.commercial_entitlements = []
        app.value_added_services = []
        app.refresh_commercial_summary = lambda: None
        # anthropic/gemini 格式 key 不会从 api_key 兜底，需按格式提供，否则配置写入会被跳过。
        app.deploy_keys = {
            "openai": {"key": "sk-openai-x", "model": "gpt-5.5"},
            "anthropic": {"key": "sk-ant-x", "model": "claude-opus-4.8"},
            "gemini": {"key": "AIza-gemini-x", "model": "gemini-3.5"},
        }
        contexts = deployment_commercial_contexts({"id": "buyer-1"})
        agent = next(a for a in installer_module.AGENTS if a.id == agent_id)
        completed = []
        failed = []

        originals = {
            name: getattr(installer_module, name)
            for name in (
                "fetch_deployer_manifest",
                "ensure_commercial_manifest_trusted",
                "install_agent",
                "apply_agent_config",
                "version_for",
                "run_agent_dialogue_probe",
                "verify_agent_client_scope",
                "execute_config_session_reserve",
                "execute_config_session_complete",
                "execute_config_session_fail",
                "write_agent_setup_guide",
                "write_customer_agent_acceptance_matrix",
            )
        }
        try:
            installer_module.fetch_deployer_manifest = lambda *_a, **_k: (
                True,
                "manifest ok",
                {
                    "agents": [{"id": agent_id, "delivery_scope": "full_config", "full_config_allowed": True}],
                    "entitlements": [
                        {
                            "entitlement_id": f"ent-{agent_id}-client",
                            "buyer_user_id": "buyer-1",
                            "agent_id": agent_id,
                            "mode_key": "client",
                            "valid_until": "2099-01-01",
                            "delivery_scope": "full_config",
                            "status": "active",
                            "remaining_uses": 1,
                            "device_limit": 1,
                        }
                    ],
                },
            )
            installer_module.ensure_commercial_manifest_trusted = lambda _manifest: None
            installer_module.install_agent = lambda _agent, _mode, _log: True
            installer_module.apply_agent_config = lambda _agent, _mode, _api_key, _model, _log: True
            installer_module.version_for = lambda _command: (True, "client 1.0")
            installer_module.run_agent_dialogue_probe = lambda _agent, _mode, _model: (True, "不应被调用")
            installer_module.verify_agent_client_scope = lambda _agent, _mode: (client_ok, client_message)
            installer_module.execute_config_session_reserve = lambda **_k: (session_id, "reserved")
            installer_module.execute_config_session_complete = lambda *a, **_k: (completed.append(a[0]), "completed-with-deduct")
            installer_module.execute_config_session_fail = lambda *a, **_k: (failed.append(a[0]), "failed-without-deduct")
            installer_module.write_agent_setup_guide = lambda *_a, **_k: Path("NOOP")
            installer_module.write_customer_agent_acceptance_matrix = lambda *_a, **_k: Path("NOOP")

            app._deploy_worker(
                selected=[(agent, "client")],
                user={"id": "buyer-1"},
                deployer_auth={"token": "buyer-token"},
                contexts=contexts,
                api_key="sk-live-secret",
                base_url="https://aitokenapi.cc",
                model="gpt-5.4",
                skip_test=True,
                open_app=False,
            )
        finally:
            for name, value in originals.items():
                setattr(installer_module, name, value)

        return completed, failed, "\n".join(logs)

    def test_deploy_worker_completes_client_scope_when_official_client_installed(self) -> None:
        # 官方客户端已检测到 + 配置写入 → 客户端交付合格并扣次。
        completed, failed, log_text = self._run_client_scope_deploy(
            "claude_code",
            "cfg-claude-client",
            client_ok=True,
            client_message="ClaudeCode/client 官方客户端已检测到（Claude Desktop）。",
        )
        self.assertEqual(completed, ["cfg-claude-client"])
        self.assertEqual(failed, [])
        self.assertIn("客户端交付已完成（安装+配置）；已提交成功并扣次", log_text)
        self.assertIn("官方客户端已安装并写入胖虎AI网关配置", log_text)

    def test_deploy_worker_fails_client_scope_when_official_client_missing(self) -> None:
        # 官方客户端未检测到 → 不扣次、判失败。
        completed, failed, log_text = self._run_client_scope_deploy(
            "gemini_agy",
            "cfg-gemini-client",
            client_ok=False,
            client_message="Gemini / agy/client client scope 需要官方客户端；当前未检测到：未安装 Antigravity。",
        )
        self.assertEqual(completed, [])
        self.assertEqual(failed, ["cfg-gemini-client"])
        self.assertIn("客户端未形成完整交付；已提交失败且不扣次", log_text)

    def test_agent_center_summary_text_uses_server_manifest_only(self) -> None:
        text = agent_center_summary_text(
            {
                "agent_center": {
                    "enabled": True,
                    "current_level": "L1",
                    "upgrade_label": "申请升级",
                    "invite_url": "https://aitokenapi.cc/invite/abc",
                    "commission_ratio": "50%",
                    "benefits": ["可绑定买家"],
                    "boundaries": ["以后台结算为准"],
                }
            }
        )

        self.assertIn("当前等级：L1", text)
        self.assertIn("邀请入口：已开放", text)
        self.assertNotIn("50%", text)
        self.assertIn("暂未开放", agent_center_summary_text({}))

    def test_real_task_probe_payload_is_minimal_and_customer_safe(self) -> None:
        url, payload = build_real_task_probe_payload("https://aitokenapi.cc", "gpt-5.4")

        self.assertEqual(url, "https://aitokenapi.cc/v1/chat/completions")
        self.assertEqual(payload["model"], "gpt-5.4")
        self.assertEqual(payload["max_tokens"], 16)
        self.assertIn("胖虎AI", payload["messages"][0]["content"])

    def test_worker_message_sanitizer_masks_commercial_sensitive_text(self) -> None:
        text = sanitize_worker_message(
            "代理 agent@example.com 手机 13800138000 token secret-token "
            "api_key=sk-live-secret order_id=ord-real invite_code INVITE-SECRET "
            "config_session_id cfg-real"
        )

        self.assertNotIn("agent@example.com", text)
        self.assertNotIn("13800138000", text)
        self.assertNotIn("secret-token", text)
        self.assertNotIn("sk-live-secret", text)
        self.assertNotIn("ord-real", text)
        self.assertNotIn("INVITE-SECRET", text)
        self.assertNotIn("cfg-real", text)
        self.assertIn("***", text)

    def test_copy_logs_sanitizes_clipboard_text(self) -> None:
        class FakeLogBox:
            def get(self, _start: str, _end: str) -> str:
                return (
                    "客户 user@example.com 手机 13800138000 "
                    "api_key=sk-live-secret token secret-token "
                    "order_id=ord-real invite_code INVITE-SECRET "
                    "config_session_id cfg-real"
                )

        class FakeRoot:
            def __init__(self) -> None:
                self.clipboard = ""

            def clipboard_clear(self) -> None:
                self.clipboard = ""

            def clipboard_append(self, text: str) -> None:
                self.clipboard = text

        class FakeStatus:
            def __init__(self) -> None:
                self.value = ""

            def set(self, value: str) -> None:
                self.value = value

        app = InstallerApp.__new__(InstallerApp)
        app.log_box = FakeLogBox()
        app.root = FakeRoot()
        app.status = FakeStatus()

        app.copy_logs()

        copied = app.root.clipboard
        self.assertNotIn("user@example.com", copied)
        self.assertNotIn("13800138000", copied)
        self.assertNotIn("sk-live-secret", copied)
        self.assertNotIn("secret-token", copied)
        self.assertNotIn("ord-real", copied)
        self.assertNotIn("INVITE-SECRET", copied)
        self.assertNotIn("cfg-real", copied)
        self.assertIn("***", copied)
        self.assertEqual(app.status.value, "状态：日志已复制")

    def test_customer_acceptance_matrix_path_is_in_workspace(self) -> None:
        path = installer_module.customer_acceptance_matrix_path()

        self.assertEqual(path.name, "胖虎AI-Agent功能验收矩阵.txt")
        self.assertIn("胖虎AI-Agent工作区", str(path))

    def test_open_acceptance_matrix_warns_until_report_exists_then_opens_file(self) -> None:
        app = InstallerApp.__new__(InstallerApp)
        opened = []
        warnings = []

        original_path = installer_module.customer_acceptance_matrix_path
        original_open_path = installer_module.open_path
        original_showwarning = installer_module.messagebox.showwarning
        with TemporaryDirectory() as temp_dir:
            matrix_path = Path(temp_dir) / "胖虎AI-Agent功能验收矩阵.txt"
            try:
                installer_module.customer_acceptance_matrix_path = lambda: matrix_path
                installer_module.open_path = lambda path: opened.append(path)
                installer_module.messagebox.showwarning = lambda title, message: warnings.append((title, message))

                app.open_acceptance_matrix()
                matrix_path.write_text("客户可见功能验收矩阵\n", encoding="utf-8")
                app.open_acceptance_matrix()
            finally:
                installer_module.customer_acceptance_matrix_path = original_path
                installer_module.open_path = original_open_path
                installer_module.messagebox.showwarning = original_showwarning

        self.assertEqual(warnings[0][0], "功能验收矩阵")
        self.assertIn("还没有生成验收矩阵", warnings[0][1])
        self.assertEqual(opened, [matrix_path])


if __name__ == "__main__":
    unittest.main()

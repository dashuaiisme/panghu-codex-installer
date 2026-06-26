import sys
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from commercial_api import (  # noqa: E402
    CommercialApiContract,
    build_api_key_owner_verify_request,
    build_config_session_complete_request,
    build_config_session_fail_request,
    build_config_session_reserve_request,
    build_entitlement_query_request,
    build_order_create_request,
    build_payment_poll_request,
    build_urllib_request_parts,
    execute_commercial_api_request,
    with_operator_auth,
    mask_business_identifier,
    parse_config_session_reserve_data,
    parse_payment_status_data,
    parse_api_envelope,
    sanitize_commercial_text,
    sanitize_commercial_api_payload,
    stable_config_session_idempotency_key,
)


class CommercialApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = CommercialApiContract(base_url="https://aitokenapi.cc")

    def test_contract_endpoints_are_public_customer_domain_only(self) -> None:
        self.assertEqual(self.contract.entitlements_url, "https://aitokenapi.cc/api/deployer/entitlements")
        self.assertEqual(self.contract.api_key_owner_verify_url, "https://aitokenapi.cc/api/deployer/api-keys/verify-owner")
        self.assertNotIn("api.aitokenapi.cc", self.contract.entitlements_url)
        self.assertNotIn("api.aitokenapi.cc", self.contract.api_key_owner_verify_url)

    def test_legacy_buyer_bind_endpoint_is_not_exposed_on_client_contract(self) -> None:
        self.assertFalse(hasattr(self.contract, "buyer_bind_url"))
        self.assertFalse(hasattr(self.contract, "agent_assist_login_url"))

    def test_operator_auth_header_is_added_without_exposing_token_in_payload_summary(self) -> None:
        request = with_operator_auth(
            build_entitlement_query_request(self.contract, buyer_user_id="buyer-1", operator_user_id="buyer-1"),
            token="secret-operator-token",
        )

        self.assertEqual(request.headers["Authorization"], "Bearer secret-operator-token")
        safe_payload = sanitize_commercial_api_payload({"headers": request.headers})
        self.assertNotIn("secret-operator-token", str(safe_payload))

    def test_entitlement_order_payment_and_config_session_requests_carry_required_context(self) -> None:
        entitlement = build_entitlement_query_request(self.contract, buyer_user_id="buyer-1", operator_user_id="agent-1")
        order = build_order_create_request(
            self.contract,
            product_id="prod-1",
            buyer_user_id="buyer-1",
            operator_user_id="agent-1",
            idempotency_key="idem-1",
        )
        payment = build_payment_poll_request(self.contract, order_id="order-1", buyer_user_id="buyer-1")
        config = build_config_session_reserve_request(
            self.contract,
            entitlement_id="ent-1",
            buyer_user_id="buyer-1",
            operator_user_id="agent-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-1",
            diagnostic_code="PH-CFG-1",
            idempotency_key="idem-2",
        )

        self.assertEqual(entitlement.query["buyer_user_id"], "buyer-1")
        self.assertEqual(order.body["target_buyer_user_id"], "buyer-1")
        self.assertEqual(order.headers["Idempotency-Key"], "idem-1")
        self.assertEqual(payment.query["order_id"], "order-1")
        self.assertEqual(config.body["diagnostic_code"], "PH-CFG-1")
        self.assertEqual(config.headers["Idempotency-Key"], "idem-2")

    def test_api_key_owner_verify_request_targets_buyer_without_logging_raw_key(self) -> None:
        request = build_api_key_owner_verify_request(
            self.contract,
            api_key="sk-live-secret-token",
            target_buyer_user_id="buyer-1",
            operator_user_id="agent-1",
        )

        self.assertTrue(request.url.endswith("/api/deployer/api-keys/verify-owner"))
        self.assertEqual(request.body["api_key"], "sk-live-secret-token")
        self.assertEqual(request.body["target_buyer_user_id"], "buyer-1")
        self.assertEqual(request.body["operator_user_id"], "agent-1")
        safe_payload = sanitize_commercial_api_payload(request.body)
        self.assertNotIn("sk-live-secret-token", str(safe_payload))
        self.assertNotIn("buyer-1", str(safe_payload))

    def test_config_session_complete_and_fail_requests_are_separate_contracts(self) -> None:
        complete = build_config_session_complete_request(
            self.contract,
            config_session_id="cfg-1",
            diagnostic_code="PH-CFG-1",
            real_task_verified=True,
            idempotency_key="idem-complete",
        )
        failed = build_config_session_fail_request(
            self.contract,
            config_session_id="cfg-1",
            diagnostic_code="PH-CFG-1",
            failure_reason="真实任务失败",
            idempotency_key="idem-fail",
        )

        self.assertTrue(complete.url.endswith("/api/deployer/config-sessions/complete"))
        self.assertEqual(complete.body["real_task_verified"], True)
        self.assertEqual(complete.headers["Idempotency-Key"], "idem-complete")
        self.assertTrue(failed.url.endswith("/api/deployer/config-sessions/fail"))
        self.assertEqual(failed.body["deduct_entitlement"], False)
        self.assertEqual(failed.headers["Idempotency-Key"], "idem-fail")

    def test_config_session_idempotency_key_is_stable_per_session_and_action(self) -> None:
        first = stable_config_session_idempotency_key("complete", "cfg-1", "PH-CFG-1")
        retry = stable_config_session_idempotency_key("complete", "cfg-1", "PH-CFG-1")
        failed = stable_config_session_idempotency_key("fail", "cfg-1", "PH-CFG-1")

        self.assertEqual(first, retry)
        self.assertNotEqual(first, failed)
        self.assertNotIn("cfg-1", first)
        self.assertNotIn("PH-CFG-1", first)

    def test_request_parts_encode_query_body_and_mask_sensitive_payload(self) -> None:
        request = build_api_key_owner_verify_request(
            self.contract,
            api_key="sk-secret",
            target_buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
        )

        url, headers, body = build_urllib_request_parts(request)
        safe_payload = sanitize_commercial_api_payload(request.body)

        self.assertEqual(url, self.contract.api_key_owner_verify_url)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIsNotNone(body)
        self.assertEqual(safe_payload["api_key"], "***")
        self.assertNotIn("sk-secret", str(safe_payload))

    def test_commercial_api_payload_masks_customer_and_commercial_ids_in_logs(self) -> None:
        safe_payload = sanitize_commercial_api_payload(
            {
                "entitlement_id": "ent-real",
                "buyer_user_id": "buyer-1",
                "operator_user_id": "agent-1",
                "target_buyer_user_id": "buyer-2",
                "order_id": "order-1",
                "config_session_id": "cfg-real",
                "diagnostic_code": "PH-CFG-1",
            }
        )

        self.assertEqual(safe_payload["diagnostic_code"], "PH-CFG-1")
        self.assertNotIn("ent-real", str(safe_payload))
        self.assertNotIn("buyer-1", str(safe_payload))
        self.assertNotIn("cfg-real", str(safe_payload))

    def test_mask_business_identifier_keeps_short_hint_without_full_value(self) -> None:
        masked = mask_business_identifier("cfg-real-session-123")

        self.assertTrue(masked.startswith("cfg-"))
        self.assertNotIn("real-session", masked)
        self.assertNotEqual(masked, "cfg-real-session-123")

    def test_execute_commercial_api_request_uses_injected_opener_and_parses_envelope(self) -> None:
        captured = {}

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"success": True, "data": {"ok": True}}, ensure_ascii=False).encode("utf-8")

        def fake_opener(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["body"] = req.data.decode("utf-8")
            captured["timeout"] = timeout
            return FakeResponse()

        request = build_api_key_owner_verify_request(
            self.contract,
            api_key="sk-secret",
            target_buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
        )

        data, summary = execute_commercial_api_request(request, fake_opener, timeout=7)

        self.assertEqual(data, {"ok": True})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["timeout"], 7)
        self.assertIn('"api_key": "sk-secret"', captured["body"])
        self.assertIn('"target_buyer_user_id": "buyer-1"', captured["body"])
        self.assertIn("api-keys/verify-owner", captured["url"])
        self.assertNotIn("sk-secret", summary)

    def test_parse_api_envelope_requires_success_and_data(self) -> None:
        data = parse_api_envelope({"success": True, "data": {"ok": True}})

        self.assertEqual(data, {"ok": True})
        with self.assertRaises(ValueError):
            parse_api_envelope({"success": False, "message": "no"})
        with self.assertRaises(ValueError):
            parse_api_envelope({"success": True, "data": []})

    def test_failed_api_envelope_masks_sensitive_server_message(self) -> None:
        raw_message = (
            "代理 agent@example.com 绑定失败，手机号 13800138000，"
            "token secret-token，api_key sk-live-secret，order_id ord-real-123，"
            "invite_code INVITE-SECRET，config_session_id cfg-real-123。"
        )

        with self.assertRaises(ValueError) as caught:
            parse_api_envelope({"success": False, "message": raw_message})

        message = str(caught.exception)
        self.assertNotIn("agent@example.com", message)
        self.assertNotIn("13800138000", message)
        self.assertNotIn("secret-token", message)
        self.assertNotIn("sk-live-secret", message)
        self.assertNotIn("ord-real-123", message)
        self.assertNotIn("INVITE-SECRET", message)
        self.assertNotIn("cfg-real-123", message)
        self.assertIn("***", message)

    def test_commercial_text_sanitizer_masks_common_sensitive_values(self) -> None:
        message = sanitize_commercial_text(
            "email a@b.com phone 13900001111 Bearer token-abc api_key=sk-live order_id=ord-1"
        )

        self.assertNotIn("a@b.com", message)
        self.assertNotIn("13900001111", message)
        self.assertNotIn("token-abc", message)
        self.assertNotIn("sk-live", message)
        self.assertNotIn("ord-1", message)

    def test_parse_config_session_reserve_data_requires_real_session_id(self) -> None:
        self.assertEqual(
            parse_config_session_reserve_data({"config_session_id": "cfg-real"})["config_session_id"],
            "cfg-real",
        )
        with self.assertRaises(ValueError):
            parse_config_session_reserve_data({})

    def test_parse_payment_status_does_not_unlock_without_server_entitlement(self) -> None:
        waiting = parse_payment_status_data({"order_id": "ord-real", "payment_status": "pending"})
        paid_without_entitlement = parse_payment_status_data({"order_id": "ord-real", "payment_status": "paid"})
        ready = parse_payment_status_data(
            {
                "order_id": "ord-real",
                "payment_status": "paid",
                "entitlement_id": "ent-real",
                "entitlement_status": "active",
            }
        )

        self.assertFalse(waiting["ready_for_delivery"])
        self.assertFalse(waiting["requires_manual_review"])
        self.assertFalse(paid_without_entitlement["ready_for_delivery"])
        self.assertTrue(paid_without_entitlement["requires_manual_review"])
        self.assertTrue(ready["ready_for_delivery"])
        self.assertFalse(ready["requires_manual_review"])
        self.assertEqual(ready["entitlement_id"], "ent-real")

    def test_parse_payment_status_accepts_success_aliases_only_with_active_entitlement(self) -> None:
        completed = parse_payment_status_data(
            {
                "order_id": "ord-real",
                "status": "completed",
                "entitlement_id": "ent-real",
                "entitlement_status": "active",
            }
        )
        success_without_entitlement = parse_payment_status_data({"order_id": "ord-real", "status": "success"})

        self.assertTrue(completed["ready_for_delivery"])
        self.assertFalse(completed["requires_manual_review"])
        self.assertFalse(success_without_entitlement["ready_for_delivery"])
        self.assertTrue(success_without_entitlement["requires_manual_review"])

    def test_parse_payment_status_normalizes_status_case_without_unlocking_inactive_entitlement(self) -> None:
        paid_active = parse_payment_status_data(
            {
                "order_id": "ord-real",
                "payment_status": "PAID",
                "entitlement_id": "ent-real",
                "entitlement_status": "ACTIVE",
            }
        )
        paid_inactive = parse_payment_status_data(
            {
                "order_id": "ord-real",
                "payment_status": "Paid",
                "entitlement_id": "ent-real",
                "entitlement_status": "Inactive",
            }
        )

        self.assertTrue(paid_active["ready_for_delivery"])
        self.assertFalse(paid_active["requires_manual_review"])
        self.assertFalse(paid_inactive["ready_for_delivery"])
        self.assertTrue(paid_inactive["requires_manual_review"])

    def test_parse_payment_status_requires_order_and_status(self) -> None:
        with self.assertRaises(ValueError):
            parse_payment_status_data({"payment_status": "paid"})
        with self.assertRaises(ValueError):
            parse_payment_status_data({"order_id": "ord-real"})


if __name__ == "__main__":
    unittest.main()

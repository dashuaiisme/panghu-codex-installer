import sys
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from commercial_api import (  # noqa: E402
    CommercialApiContract,
    build_admin_agent_application_review_request,
    build_admin_agent_ledger_action_request,
    build_admin_agent_marketing_content_update_request,
    build_admin_agent_policy_update_request,
    build_admin_agent_product_update_request,
    build_admin_agent_settlement_action_request,
    build_admin_mobile_control_channel_policy_update_request,
    build_admin_mobile_control_order_action_request,
    build_admin_mobile_control_product_update_request,
    build_admin_mobile_control_session_action_request,
    build_admin_mobile_control_sessions_request,
    build_agent_apply_request,
    build_agent_center_request,
    build_agent_commissions_request,
    build_agent_downstreams_request,
    build_agent_public_offering_request,
    build_agent_settlement_request,
    build_api_key_owner_verify_request,
    build_config_session_complete_request,
    build_config_session_fail_request,
    build_config_session_reserve_request,
    build_entitlement_query_request,
    build_mobile_control_callback_request,
    build_mobile_control_offering_request,
    build_mobile_control_order_create_request,
    build_mobile_control_order_get_request,
    build_mobile_control_session_acceptance_request,
    build_mobile_control_session_create_request,
    build_mobile_control_session_disable_request,
    build_mobile_control_session_get_request,
    build_mobile_control_session_test_request,
    build_order_create_request,
    build_payment_poll_request,
    build_referral_bind_request,
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
    stable_mobile_control_idempotency_key,
)


class CommercialApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = CommercialApiContract(base_url="https://aitokenapi.cc")

    def test_contract_endpoints_are_public_customer_domain_only(self) -> None:
        self.assertEqual(self.contract.entitlements_url, "https://aitokenapi.cc/api/deployer/entitlements")
        self.assertEqual(self.contract.api_key_owner_verify_url, "https://aitokenapi.cc/api/deployer/api-keys/verify-owner")
        self.assertNotIn("api.aitokenapi.cc", self.contract.entitlements_url)
        self.assertNotIn("api.aitokenapi.cc", self.contract.api_key_owner_verify_url)

    def test_agent_business_endpoints_are_service_side_contracts(self) -> None:
        self.assertEqual(self.contract.agent_public_offering_url, "https://aitokenapi.cc/api/agent/public/offering")
        self.assertEqual(self.contract.agent_apply_url, "https://aitokenapi.cc/api/agent/apply")
        self.assertEqual(self.contract.agent_center_url, "https://aitokenapi.cc/api/agent/center")
        self.assertEqual(self.contract.agent_downstreams_url, "https://aitokenapi.cc/api/agent/downstreams")
        self.assertEqual(self.contract.agent_commissions_url, "https://aitokenapi.cc/api/agent/commissions")
        self.assertEqual(self.contract.agent_settlements_url, "https://aitokenapi.cc/api/agent/settlements")
        self.assertEqual(self.contract.referral_bind_url, "https://aitokenapi.cc/api/referrals/bind")
        self.assertEqual(self.contract.admin_agent_products_url, "https://aitokenapi.cc/api/admin/agent/products")
        self.assertEqual(self.contract.admin_agent_policies_url, "https://aitokenapi.cc/api/admin/agent/policies")
        self.assertEqual(
            self.contract.admin_agent_marketing_content_url,
            "https://aitokenapi.cc/api/admin/agent/marketing-content",
        )
        self.assertEqual(self.contract.admin_agent_applications_url, "https://aitokenapi.cc/api/admin/agent/applications")
        self.assertEqual(self.contract.admin_agent_settlements_url, "https://aitokenapi.cc/api/admin/agent/settlements")
        self.assertEqual(
            self.contract.admin_agent_ledger_action_url("ledger-1", "freeze"),
            "https://aitokenapi.cc/api/admin/agent/ledger/ledger-1/freeze",
        )

    def test_mobile_control_endpoints_are_independent_service_contracts(self) -> None:
        self.assertEqual(self.contract.mobile_control_offering_url, "https://aitokenapi.cc/api/mobile-control/offering")
        self.assertEqual(self.contract.mobile_control_orders_url, "https://aitokenapi.cc/api/mobile-control/orders")
        self.assertEqual(self.contract.mobile_control_order_url("svc-ord-1"), "https://aitokenapi.cc/api/mobile-control/orders/svc-ord-1")
        self.assertEqual(self.contract.mobile_control_sessions_url, "https://aitokenapi.cc/api/mobile-control/sessions")
        self.assertEqual(self.contract.mobile_control_session_url("mca-1"), "https://aitokenapi.cc/api/mobile-control/sessions/mca-1")
        self.assertEqual(self.contract.mobile_control_session_test_url("mca-1"), "https://aitokenapi.cc/api/mobile-control/sessions/mca-1/test")
        self.assertEqual(
            self.contract.mobile_control_session_acceptance_url("mca-1"),
            "https://aitokenapi.cc/api/mobile-control/sessions/mca-1/acceptance",
        )
        self.assertEqual(
            self.contract.mobile_control_session_disable_url("mca-1"),
            "https://aitokenapi.cc/api/mobile-control/sessions/mca-1/disable",
        )
        self.assertEqual(self.contract.mobile_control_callback_url("qq_bot"), "https://aitokenapi.cc/api/mobile-control/callbacks/qq-bot")
        self.assertEqual(self.contract.mobile_control_callback_url("feishu"), "https://aitokenapi.cc/api/mobile-control/callbacks/feishu")
        self.assertEqual(self.contract.admin_mobile_control_products_url, "https://aitokenapi.cc/api/admin/mobile-control/products")
        self.assertEqual(
            self.contract.admin_mobile_control_channel_policies_url,
            "https://aitokenapi.cc/api/admin/mobile-control/channel-policies",
        )
        self.assertEqual(self.contract.admin_mobile_control_sessions_url, "https://aitokenapi.cc/api/admin/mobile-control/sessions")
        self.assertEqual(
            self.contract.admin_mobile_control_session_action_url("mca-1", "freeze"),
            "https://aitokenapi.cc/api/admin/mobile-control/sessions/mca-1/freeze",
        )
        self.assertEqual(
            self.contract.admin_mobile_control_order_action_url("svc-ord-1", "manual-review"),
            "https://aitokenapi.cc/api/admin/mobile-control/orders/svc-ord-1/manual-review",
        )

    def test_agent_business_requests_carry_idempotency_and_mask_sensitive_invites(self) -> None:
        offering = build_agent_public_offering_request(self.contract)
        apply = build_agent_apply_request(
            self.contract,
            product_id="agent-l1-free",
            idempotency_key="agent-apply-1",
        )
        center = build_agent_center_request(self.contract)
        bind = build_referral_bind_request(
            self.contract,
            invite_code="INVITE-SECRET",
            idempotency_key="bind-1",
        )
        downstreams = build_agent_downstreams_request(self.contract, cursor="page-1")
        commissions = build_agent_commissions_request(self.contract, status="available", event_type="token_usage_settled")
        settlement = build_agent_settlement_request(
            self.contract,
            requested_cents=1000,
            idempotency_key="settlement-1",
        )
        admin_product = build_admin_agent_product_update_request(
            self.contract,
            product={
                "id": "agent-l1-free",
                "level": "L1",
                "price_cents": 0,
                "status": "listed",
            },
        )
        admin_policy = build_admin_agent_policy_update_request(
            self.contract,
            policy={"event_type": "token_usage_settled", "receiver_level": "L1", "depth": 1, "rate_bps": 1000},
        )
        admin_marketing = build_admin_agent_marketing_content_update_request(
            self.contract,
            content={"page_title": "胖虎AI代理招募", "faq": []},
        )
        admin_review = build_admin_agent_application_review_request(
            self.contract,
            application_id="app-1",
            decision="approve",
            reason="资料通过",
        )
        admin_settlement = build_admin_agent_settlement_action_request(
            self.contract,
            settlement_id="stl-1",
            action="pay",
            reason="T+7 结算",
        )
        ledger_action = build_admin_agent_ledger_action_request(
            self.contract,
            ledger_id="ledger-1",
            action="reverse",
            reason="客户退款",
        )

        self.assertEqual(offering.method, "GET")
        self.assertEqual(apply.method, "POST")
        self.assertEqual(apply.headers["Idempotency-Key"], "agent-apply-1")
        self.assertEqual(apply.body["product_id"], "agent-l1-free")
        self.assertEqual(center.method, "GET")
        self.assertEqual(bind.url, self.contract.referral_bind_url)
        self.assertEqual(bind.headers["Idempotency-Key"], "bind-1")
        self.assertNotIn("INVITE-SECRET", str(sanitize_commercial_api_payload(bind.body)))
        self.assertEqual(downstreams.query["cursor"], "page-1")
        self.assertEqual(commissions.query["event_type"], "token_usage_settled")
        self.assertEqual(settlement.url, self.contract.agent_settlements_url)
        self.assertEqual(settlement.headers["Idempotency-Key"], "settlement-1")
        self.assertEqual(settlement.body["requested_cents"], 1000)
        self.assertEqual(admin_product.method, "PUT")
        self.assertEqual(admin_policy.url, self.contract.admin_agent_policies_url)
        self.assertEqual(admin_policy.body["policy"]["rate_bps"], 1000)
        self.assertEqual(admin_marketing.body["content"]["page_title"], "胖虎AI代理招募")
        self.assertEqual(admin_review.url, self.contract.admin_agent_applications_url)
        self.assertEqual(admin_review.body["decision"], "approve")
        self.assertEqual(admin_settlement.url, self.contract.admin_agent_settlements_url)
        self.assertEqual(admin_settlement.body["action"], "pay")
        self.assertEqual(ledger_action.url, "https://aitokenapi.cc/api/admin/agent/ledger/ledger-1/reverse")
        self.assertEqual(ledger_action.body["reason"], "客户退款")

    def test_mobile_control_requests_carry_independent_order_session_acceptance_contract(self) -> None:
        offering = build_mobile_control_offering_request(self.contract)
        order = build_mobile_control_order_create_request(
            self.contract,
            service_product_id="svc-mobile-control",
            buyer_user_id="buyer-1",
            agent_id="hermes",
            channel="feishu",
            agent_source="existing_local_agent",
            idempotency_key="mca-order-1",
        )
        order_get = build_mobile_control_order_get_request(self.contract, "svc-ord-1")
        session = build_mobile_control_session_create_request(
            self.contract,
            order_id="svc-ord-1",
            agent_id="hermes",
            channel="feishu",
            platform_account_id="bot-account-1",
            platform_chat_id="chat-1",
            gateway_mode="official_bot",
            agent_source="existing_local_agent",
            idempotency_key="mca-session-1",
        )
        session_get = build_mobile_control_session_get_request(self.contract, "mca-1")
        test = build_mobile_control_session_test_request(
            self.contract,
            session_id="mca-1",
            test_prompt="请回复手机控制Agent验收成功",
            idempotency_key="mca-test-1",
        )
        acceptance = build_mobile_control_session_acceptance_request(
            self.contract,
            session_id="mca-1",
            source_event_id="mca-delivered-1",
            inbound_platform_message_id="in-msg-1",
            outbound_platform_message_id="out-msg-1",
            test_prompt="请回复手机控制Agent验收成功",
            agent_response_digest="sha256:reply",
            evidence_url="https://aitokenapi.cc/evidence/mca-delivered-1",
            idempotency_key="mca-accept-1",
        )
        disable = build_mobile_control_session_disable_request(
            self.contract,
            session_id="mca-1",
            reason="客户主动停用",
            idempotency_key="mca-disable-1",
        )

        self.assertEqual(offering.method, "GET")
        self.assertEqual(order.url, self.contract.mobile_control_orders_url)
        self.assertEqual(order.headers["Idempotency-Key"], "mca-order-1")
        self.assertEqual(order.body["service_product_id"], "svc-mobile-control")
        self.assertEqual(order.body["target_buyer_user_id"], "buyer-1")
        self.assertEqual(order.body["agent_source"], "existing_local_agent")
        self.assertTrue(order_get.url.endswith("/api/mobile-control/orders/svc-ord-1"))
        self.assertEqual(session.url, self.contract.mobile_control_sessions_url)
        self.assertEqual(session.body["order_id"], "svc-ord-1")
        self.assertEqual(session.body["platform_chat_id"], "chat-1")
        self.assertTrue(session_get.url.endswith("/api/mobile-control/sessions/mca-1"))
        self.assertTrue(test.url.endswith("/api/mobile-control/sessions/mca-1/test"))
        self.assertEqual(test.body["test_prompt"], "请回复手机控制Agent验收成功")
        self.assertTrue(acceptance.url.endswith("/api/mobile-control/sessions/mca-1/acceptance"))
        self.assertEqual(acceptance.body["source_event_id"], "mca-delivered-1")
        self.assertEqual(acceptance.body["inbound_platform_message_id"], "in-msg-1")
        self.assertTrue(disable.url.endswith("/api/mobile-control/sessions/mca-1/disable"))
        safe_acceptance = sanitize_commercial_api_payload(acceptance.body)
        self.assertNotIn("mca-delivered-1", str(safe_acceptance))
        self.assertNotIn("in-msg-1", str(safe_acceptance))

    def test_mobile_control_callback_and_admin_requests_are_separate_from_basic_agent_delivery(self) -> None:
        callback = build_mobile_control_callback_request(
            self.contract,
            channel="qq_bot",
            platform_message_id="msg-1",
            platform_chat_id="group-1",
            sender_id="user-1",
            text="@机器人 帮我检查项目",
            mentioned_bot=True,
        )
        admin_product = build_admin_mobile_control_product_update_request(
            self.contract,
            product={"id": "svc-mobile-control", "service_type": "mobile_control_agent", "status": "listed"},
        )
        admin_policy = build_admin_mobile_control_channel_policy_update_request(
            self.contract,
            policy={"channel": "qq_bot", "requires_mention": True},
        )
        admin_sessions = build_admin_mobile_control_sessions_request(self.contract, status="manual_review", cursor="page-1")
        admin_session_action = build_admin_mobile_control_session_action_request(
            self.contract,
            session_id="mca-1",
            action="freeze",
            reason="平台回调异常",
        )
        admin_order_action = build_admin_mobile_control_order_action_request(
            self.contract,
            order_id="svc-ord-1",
            action="refund",
            reason="客户未完成验收",
        )

        self.assertEqual(callback.url, "https://aitokenapi.cc/api/mobile-control/callbacks/qq-bot")
        self.assertTrue(callback.body["mentioned_bot"])
        self.assertEqual(admin_product.method, "PUT")
        self.assertEqual(admin_product.url, self.contract.admin_mobile_control_products_url)
        self.assertEqual(admin_policy.url, self.contract.admin_mobile_control_channel_policies_url)
        self.assertEqual(admin_sessions.query["status"], "manual_review")
        self.assertEqual(admin_sessions.query["cursor"], "page-1")
        self.assertTrue(admin_session_action.url.endswith("/api/admin/mobile-control/sessions/mca-1/freeze"))
        self.assertTrue(admin_order_action.url.endswith("/api/admin/mobile-control/orders/svc-ord-1/refund"))

    def test_mobile_control_idempotency_key_is_stable_and_does_not_expose_raw_ids(self) -> None:
        first = stable_mobile_control_idempotency_key("acceptance", "mca-1", "svc-ord-1", "mca-delivered-1")
        retry = stable_mobile_control_idempotency_key("acceptance", "mca-1", "svc-ord-1", "mca-delivered-1")
        other = stable_mobile_control_idempotency_key("test", "mca-1", "svc-ord-1", "mca-delivered-1")

        self.assertEqual(first, retry)
        self.assertNotEqual(first, other)
        self.assertNotIn("mca-1", first)
        self.assertNotIn("svc-ord-1", first)
        self.assertNotIn("mca-delivered-1", first)

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

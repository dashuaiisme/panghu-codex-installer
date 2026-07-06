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
    build_admin_communication_software_link_channel_policy_update_request,
    build_admin_communication_software_link_order_action_request,
    build_admin_communication_software_link_product_update_request,
    build_admin_communication_software_link_session_action_request,
    build_admin_communication_software_link_sessions_request,
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
    build_communication_software_link_callback_request,
    build_communication_software_link_offering_request,
    build_communication_software_link_order_create_request,
    build_communication_software_link_order_get_request,
    build_communication_software_link_session_acceptance_request,
    build_communication_software_link_session_create_request,
    build_communication_software_link_session_disable_request,
    build_communication_software_link_session_get_request,
    build_communication_software_link_platform_auth_create_request,
    build_communication_software_link_platform_auth_get_request,
    build_communication_software_link_session_test_request,
    build_order_create_request,
    build_payment_poll_request,
    build_referral_bind_request,
    build_urllib_request_parts,
    execute_commercial_api_request,
    with_operator_auth,
    mask_business_identifier,
    parse_config_session_reserve_data,
    parse_agent_center_snapshot_data,
    parse_order_entitlement_status_data,
    parse_communication_software_link_order_status_data,
    parse_communication_software_link_state_fields,
    parse_payment_status_data,
    parse_api_envelope,
    sanitize_commercial_text,
    sanitize_commercial_api_payload,
    sanitize_commercial_api_url,
    stable_config_reserve_idempotency_key,
    stable_config_session_idempotency_key,
    stable_agent_business_idempotency_key,
    stable_communication_software_link_idempotency_key,
)
import panghu_ai_client as installer  # noqa: E402


class CommercialApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = CommercialApiContract(base_url="https://aitokenapi.cc")

    def test_contract_endpoints_are_public_customer_domain_only(self) -> None:
        self.assertEqual(self.contract.entitlements_url, "https://aitokenapi.cc/api/deployer/entitlements")
        self.assertEqual(self.contract.api_key_owner_verify_url, "https://aitokenapi.cc/api/deployer/api-keys/verify-owner")
        self.assertNotIn("api.aitokenapi.cc", self.contract.entitlements_url)
        self.assertNotIn("api.aitokenapi.cc", self.contract.api_key_owner_verify_url)

    def test_tool_order_payment_status_endpoint_is_independent_from_deployer_entitlements(self) -> None:
        self.assertEqual(self.contract.payment_status_url, "https://aitokenapi.cc/api/tool-orders/payment-status")
        self.assertNotIn("/api/deployer/orders", self.contract.payment_status_url)

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

    def test_communication_software_link_endpoints_are_independent_service_contracts(self) -> None:
        self.assertEqual(self.contract.communication_software_link_offering_url, "https://aitokenapi.cc/api/communication-software-link/offering")
        self.assertEqual(self.contract.communication_software_link_orders_url, "https://aitokenapi.cc/api/communication-software-link/orders")
        self.assertEqual(self.contract.communication_software_link_order_url("svc-ord-1"), "https://aitokenapi.cc/api/communication-software-link/orders/svc-ord-1")
        self.assertEqual(self.contract.communication_software_link_sessions_url, "https://aitokenapi.cc/api/communication-software-link/sessions")
        self.assertEqual(self.contract.communication_software_link_session_url("csl-1"), "https://aitokenapi.cc/api/communication-software-link/sessions/csl-1")
        self.assertEqual(self.contract.communication_software_link_session_test_url("csl-1"), "https://aitokenapi.cc/api/communication-software-link/sessions/csl-1/test")
        self.assertEqual(
            self.contract.communication_software_link_session_acceptance_url("csl-1"),
            "https://aitokenapi.cc/api/communication-software-link/sessions/csl-1/acceptance",
        )
        self.assertEqual(
            self.contract.communication_software_link_session_disable_url("csl-1"),
            "https://aitokenapi.cc/api/communication-software-link/sessions/csl-1/disable",
        )
        self.assertEqual(self.contract.communication_software_link_platform_auth_url, "https://aitokenapi.cc/api/communication-software-link/platform-auth")
        self.assertEqual(
            self.contract.communication_software_link_platform_auth_session_url("pauth-1"),
            "https://aitokenapi.cc/api/communication-software-link/platform-auth/pauth-1",
        )
        self.assertEqual(self.contract.communication_software_link_callback_url("qq_bot"), "https://aitokenapi.cc/api/communication-software-link/callbacks/qq-bot")
        self.assertEqual(self.contract.communication_software_link_callback_url("feishu"), "https://aitokenapi.cc/api/communication-software-link/callbacks/feishu")
        self.assertEqual(self.contract.admin_communication_software_link_products_url, "https://aitokenapi.cc/api/admin/communication-software-link/products")
        self.assertEqual(
            self.contract.admin_communication_software_link_channel_policies_url,
            "https://aitokenapi.cc/api/admin/communication-software-link/channel-policies",
        )
        self.assertEqual(self.contract.admin_communication_software_link_sessions_url, "https://aitokenapi.cc/api/admin/communication-software-link/sessions")
        self.assertEqual(
            self.contract.admin_communication_software_link_session_action_url("csl-1", "freeze"),
            "https://aitokenapi.cc/api/admin/communication-software-link/sessions/csl-1/freeze",
        )
        self.assertEqual(
            self.contract.admin_communication_software_link_order_action_url("svc-ord-1", "manual-review"),
            "https://aitokenapi.cc/api/admin/communication-software-link/orders/svc-ord-1/manual-review",
        )

    def test_communication_software_link_client_options_exclude_gemini_agy_until_full_delivery_chain_exists(self) -> None:
        self.assertNotIn("gemini_agy", installer.COMMUNICATION_SOFTWARE_LINK_AGENT_OPTIONS)
        self.assertEqual(
            installer.COMMUNICATION_SOFTWARE_LINK_AGENT_OPTIONS,
            ("codex", "claude_code", "openclaw", "hermes"),
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

    def test_communication_software_link_requests_carry_independent_order_session_acceptance_contract(self) -> None:
        offering = build_communication_software_link_offering_request(self.contract)
        order = build_communication_software_link_order_create_request(
            self.contract,
            service_product_id="svc-communication-software-link",
            buyer_user_id="buyer-1",
            agent_id="hermes",
            channel="feishu",
            agent_source="existing_local_agent",
            idempotency_key="csl-order-1",
        )
        order_get = build_communication_software_link_order_get_request(self.contract, "svc-ord-1")
        session = build_communication_software_link_session_create_request(
            self.contract,
            order_id="svc-ord-1",
            agent_id="hermes",
            channel="feishu",
            platform_account_id="bot-account-1",
            platform_chat_id="chat-1",
            gateway_mode="official_bot",
            agent_source="existing_local_agent",
            idempotency_key="csl-session-1",
        )
        session_get = build_communication_software_link_session_get_request(self.contract, "csl-1")
        platform_auth = build_communication_software_link_platform_auth_create_request(
            self.contract,
            order_id="svc-ord-1",
            agent_id="hermes",
            channel="feishu",
            gateway_mode="official_bot",
            platform_chat_hint="chat-hint",
            idempotency_key="csl-platform-auth-1",
        )
        platform_auth_get = build_communication_software_link_platform_auth_get_request(self.contract, "pauth-1")
        test = build_communication_software_link_session_test_request(
            self.contract,
            session_id="csl-1",
            test_prompt="请回复连接通讯软件验收成功",
            idempotency_key="csl-test-1",
        )
        acceptance = build_communication_software_link_session_acceptance_request(
            self.contract,
            session_id="csl-1",
            source_event_id="csl-delivered-1",
            inbound_platform_message_id="in-msg-1",
            outbound_platform_message_id="out-msg-1",
            test_prompt="请回复连接通讯软件验收成功",
            agent_response_digest="sha256:reply",
            evidence_url="https://aitokenapi.cc/evidence/csl-delivered-1",
            idempotency_key="csl-accept-1",
        )
        disable = build_communication_software_link_session_disable_request(
            self.contract,
            session_id="csl-1",
            reason="客户主动停用",
            idempotency_key="csl-disable-1",
        )

        self.assertEqual(offering.method, "GET")
        self.assertEqual(order.url, self.contract.communication_software_link_orders_url)
        self.assertEqual(order.headers["Idempotency-Key"], "csl-order-1")
        self.assertEqual(order.body["service_product_id"], "svc-communication-software-link")
        self.assertEqual(order.body["target_buyer_user_id"], "buyer-1")
        self.assertEqual(order.body["agent_source"], "existing_local_agent")
        self.assertTrue(order_get.url.endswith("/api/communication-software-link/orders/svc-ord-1"))
        self.assertEqual(session.url, self.contract.communication_software_link_sessions_url)
        self.assertEqual(session.body["order_id"], "svc-ord-1")
        self.assertEqual(session.body["platform_chat_id"], "chat-1")
        self.assertTrue(session_get.url.endswith("/api/communication-software-link/sessions/csl-1"))
        self.assertEqual(platform_auth.url, self.contract.communication_software_link_platform_auth_url)
        self.assertEqual(platform_auth.headers["Idempotency-Key"], "csl-platform-auth-1")
        self.assertEqual(platform_auth.body["order_id"], "svc-ord-1")
        self.assertEqual(platform_auth.body["channel"], "feishu")
        self.assertEqual(platform_auth.body["platform_chat_hint"], "chat-hint")
        self.assertEqual(platform_auth_get.method, "GET")
        self.assertTrue(platform_auth_get.url.endswith("/api/communication-software-link/platform-auth/pauth-1"))
        self.assertTrue(test.url.endswith("/api/communication-software-link/sessions/csl-1/test"))
        self.assertEqual(test.body["test_prompt"], "请回复连接通讯软件验收成功")
        self.assertTrue(acceptance.url.endswith("/api/communication-software-link/sessions/csl-1/acceptance"))
        self.assertEqual(acceptance.body["source_event_id"], "csl-delivered-1")
        self.assertEqual(acceptance.body["inbound_platform_message_id"], "in-msg-1")
        self.assertTrue(disable.url.endswith("/api/communication-software-link/sessions/csl-1/disable"))
        safe_acceptance = sanitize_commercial_api_payload(acceptance.body)
        self.assertNotIn("csl-delivered-1", str(safe_acceptance))
        self.assertNotIn("in-msg-1", str(safe_acceptance))

    def test_communication_software_link_callback_and_admin_requests_are_separate_from_basic_agent_delivery(self) -> None:
        callback = build_communication_software_link_callback_request(
            self.contract,
            channel="qq_bot",
            platform_message_id="msg-1",
            platform_chat_id="group-1",
            sender_id="user-1",
            text="@机器人 帮我检查项目",
            mentioned_bot=True,
            source_event_id="evt-msg-1",
        )
        admin_product = build_admin_communication_software_link_product_update_request(
            self.contract,
            product={"id": "svc-communication-software-link", "service_type": "communication_software_link", "status": "listed"},
        )
        admin_policy = build_admin_communication_software_link_channel_policy_update_request(
            self.contract,
            policy={"channel": "qq_bot", "requires_mention": True},
        )
        admin_sessions = build_admin_communication_software_link_sessions_request(self.contract, status="manual_review", cursor="page-1")
        admin_session_action = build_admin_communication_software_link_session_action_request(
            self.contract,
            session_id="csl-1",
            action="freeze",
            reason="平台回调异常",
        )
        admin_order_action = build_admin_communication_software_link_order_action_request(
            self.contract,
            order_id="svc-ord-1",
            action="refund",
            reason="客户未完成验收",
        )

        self.assertEqual(callback.url, "https://aitokenapi.cc/api/communication-software-link/callbacks/qq-bot")
        self.assertTrue(callback.headers["Idempotency-Key"].startswith("csl-callback-"))
        self.assertNotIn("evt-msg-1", callback.headers["Idempotency-Key"])
        self.assertTrue(callback.body["mentioned_bot"])
        self.assertEqual(callback.body["source_event_id"], "evt-msg-1")
        self.assertEqual(admin_product.method, "PUT")
        self.assertEqual(admin_product.url, self.contract.admin_communication_software_link_products_url)
        self.assertEqual(admin_policy.url, self.contract.admin_communication_software_link_channel_policies_url)
        self.assertEqual(admin_sessions.query["status"], "manual_review")
        self.assertEqual(admin_sessions.query["cursor"], "page-1")
        self.assertTrue(admin_session_action.url.endswith("/api/admin/communication-software-link/sessions/csl-1/freeze"))
        self.assertTrue(admin_order_action.url.endswith("/api/admin/communication-software-link/orders/svc-ord-1/refund"))

    def test_communication_software_link_idempotency_key_is_stable_and_does_not_expose_raw_ids(self) -> None:
        first = stable_communication_software_link_idempotency_key("acceptance", "csl-1", "svc-ord-1", "csl-delivered-1")
        retry = stable_communication_software_link_idempotency_key("acceptance", "csl-1", "svc-ord-1", "csl-delivered-1")
        other = stable_communication_software_link_idempotency_key("test", "csl-1", "svc-ord-1", "csl-delivered-1")

        self.assertEqual(first, retry)
        self.assertNotEqual(first, other)
        self.assertNotIn("csl-1", first)
        self.assertNotIn("svc-ord-1", first)
        self.assertNotIn("csl-delivered-1", first)

    def test_agent_business_idempotency_key_is_stable_and_separate_from_service_link_keys(self) -> None:
        first = stable_agent_business_idempotency_key("referral_bind", "buyer-1", "INVITE-SECRET")
        retry = stable_agent_business_idempotency_key("referral_bind", "buyer-1", "INVITE-SECRET")
        other = stable_agent_business_idempotency_key("agent_apply", "buyer-1", "agent-l1-free")

        self.assertEqual(first, retry)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("agent-referral_bind-"))
        self.assertNotIn("buyer-1", first)
        self.assertNotIn("INVITE-SECRET", first)
        with self.assertRaisesRegex(ValueError, "代理业务"):
            stable_agent_business_idempotency_key("order", "buyer-1")

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

    def test_api_url_summary_masks_business_ids_in_path_and_query(self) -> None:
        safe_url = sanitize_commercial_api_url(
            "https://aitokenapi.cc/api/communication-software-link/sessions/csl-1/test?order_id=svc-ord-1"
        )

        self.assertEqual(
            safe_url,
            "https://aitokenapi.cc/api/communication-software-link/sessions/[redacted]/test?[redacted-query]",
        )
        self.assertNotIn("csl-1", safe_url)
        self.assertNotIn("svc-ord-1", safe_url)

    def test_entitlement_order_payment_and_config_session_requests_carry_required_context(self) -> None:
        entitlement = build_entitlement_query_request(self.contract, buyer_user_id="buyer-1", operator_user_id="buyer-1")
        order = build_order_create_request(
            self.contract,
            product_id="prod-1",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            idempotency_key="idem-1",
        )
        payment = build_payment_poll_request(
            self.contract, order_id="order-1", buyer_user_id="buyer-1", operator_user_id="buyer-1"
        )
        config = build_config_session_reserve_request(
            self.contract,
            entitlement_id="ent-1",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-1",
            diagnostic_code="PH-CFG-1",
            idempotency_key="idem-2",
        )

        self.assertEqual(entitlement.query["buyer_user_id"], "buyer-1")
        self.assertEqual(order.body["target_buyer_user_id"], "buyer-1")
        self.assertEqual(order.body["delivery_scope"], "codex_agent_config")
        self.assertEqual(order.headers["Idempotency-Key"], "idem-1")
        self.assertEqual(payment.query["order_id"], "order-1")
        self.assertEqual(payment.query["operator_user_id"], "buyer-1")
        with self.assertRaises(ValueError):
            build_payment_poll_request(
                self.contract, order_id="order-1", buyer_user_id="buyer-1", operator_user_id="other-user"
            )
        self.assertEqual(config.body["diagnostic_code"], "PH-CFG-1")
        self.assertEqual(config.body["delivery_scope"], "codex_agent_config")
        self.assertEqual(config.headers["Idempotency-Key"], "idem-2")

    def test_api_key_owner_verify_request_targets_buyer_without_logging_raw_key(self) -> None:
        request = build_api_key_owner_verify_request(
            self.contract,
            api_key="sk-live-secret-token",
            target_buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
        )

        self.assertTrue(request.url.endswith("/api/deployer/api-keys/verify-owner"))
        self.assertEqual(request.body["api_key"], "sk-live-secret-token")
        self.assertEqual(request.body["target_buyer_user_id"], "buyer-1")
        self.assertEqual(request.body["operator_user_id"], "buyer-1")
        safe_payload = sanitize_commercial_api_payload(request.body)
        self.assertNotIn("sk-live-secret-token", str(safe_payload))
        self.assertNotIn("buyer-1", str(safe_payload))

    def test_current_buyer_operations_reject_non_buyer_operator_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "当前买家本人"):
            build_entitlement_query_request(self.contract, buyer_user_id="buyer-1", operator_user_id="agent-1")
        with self.assertRaisesRegex(ValueError, "当前买家本人"):
            build_order_create_request(
                self.contract,
                product_id="prod-1",
                buyer_user_id="buyer-1",
                operator_user_id="agent-1",
                idempotency_key="idem-1",
            )
        with self.assertRaisesRegex(ValueError, "当前买家本人"):
            build_api_key_owner_verify_request(
                self.contract,
                api_key="sk-live-secret-token",
                target_buyer_user_id="buyer-1",
                operator_user_id="agent-1",
            )
        with self.assertRaisesRegex(ValueError, "当前买家本人"):
            build_config_session_reserve_request(
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
        with self.assertRaisesRegex(ValueError, "当前买家本人"):
            stable_config_reserve_idempotency_key(
                "ent-1",
                "buyer-1",
                "agent-1",
                "codex",
                "direct_api",
                "device-1",
                "PH-CFG-1",
            )

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

    def test_commercial_api_payload_masks_sensitive_nested_list_items(self) -> None:
        safe_payload = sanitize_commercial_api_payload(
            {
                "items": [
                    {
                        "session_id": "csl-real-session",
                        "source_event_id": "evt-real-delivery",
                        "platform_chat_id": "chat-secret",
                        "name": "连接通讯软件",
                    }
                ],
                "summary": {"sender_id": "sender-secret", "status": "manual_review"},
            }
        )

        self.assertNotIn("csl-real-session", str(safe_payload))
        self.assertNotIn("evt-real-delivery", str(safe_payload))
        self.assertNotIn("chat-secret", str(safe_payload))
        self.assertNotIn("sender-secret", str(safe_payload))
        self.assertIn("连接通讯软件", str(safe_payload))

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

    def test_failed_api_envelope_masks_communication_software_link_sensitive_server_message(self) -> None:
        raw_message = (
            "连接通讯软件失败：session_id csl-real-1 source_event_id evt-real-1 "
            "platform_chat_id group-secret inbound_platform_message_id in-msg-secret "
            "outbound_platform_message_id out-msg-secret sender_id user-secret"
        )

        with self.assertRaises(ValueError) as caught:
            parse_api_envelope({"success": False, "message": raw_message})

        message = str(caught.exception)
        self.assertNotIn("csl-real-1", message)
        self.assertNotIn("evt-real-1", message)
        self.assertNotIn("group-secret", message)
        self.assertNotIn("in-msg-secret", message)
        self.assertNotIn("out-msg-secret", message)
        self.assertNotIn("user-secret", message)
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

    def test_parse_order_entitlement_status_data_reports_delivery_guards(self) -> None:
        pending = parse_order_entitlement_status_data({"order_id": "ord-1", "payment_status": "pending"})
        paid_without_entitlement = parse_order_entitlement_status_data({"order_id": "ord-2", "payment_status": "paid"})
        ready = parse_order_entitlement_status_data(
            {
                "order_id": "ord-3",
                "payment_status": "paid",
                "entitlement_id": "ent-3",
                "entitlement_status": "active",
                "config_session_status": "completed",
            }
        )
        reversed_status = parse_order_entitlement_status_data(
            {"order_id": "ord-4", "order_status": "reversed", "entitlement_status": "revoked"}
        )

        self.assertEqual(pending["order_status_report"], "payment_pending")
        self.assertEqual(pending["entitlement_status_report"], "unpaid")
        self.assertEqual(paid_without_entitlement["order_status_report"], "entitlement_pending")
        self.assertEqual(paid_without_entitlement["entitlement_status_report"], "paid_unconfirmed")
        self.assertEqual(ready["order_status_report"], "local_session_completed_pending_real_delivery")
        self.assertEqual(ready["entitlement_status_report"], "authorized")
        self.assertIn("本地配置会话完成不代表客户真实交付完成", "\n".join(ready["blocking_gaps"]))
        self.assertEqual(reversed_status["order_status_report"], "local_reversed")
        self.assertEqual(reversed_status["entitlement_status_report"], "revoked")

    def test_parse_communication_software_link_order_status_allows_paid_or_manual_review_only(self) -> None:
        paid = parse_communication_software_link_order_status_data(
            {"service_order_id": "svc-ord-1", "status": "paid", "charge_status": "paid", "payment_id": "pay-1"}
        )
        manual = parse_communication_software_link_order_status_data(
            {"order_id": "svc-ord-2", "status": "created", "charge_status": "manual_review"}
        )
        unpaid = parse_communication_software_link_order_status_data(
            {"order_id": "svc-ord-3", "status": "created", "charge_status": "unpaid"}
        )
        cancelled_paid = parse_communication_software_link_order_status_data(
            {"order_id": "svc-ord-4", "status": "cancelled", "charge_status": "paid"}
        )

        self.assertTrue(paid["session_allowed"])
        self.assertEqual(paid["payment_id"], "pay-1")
        self.assertFalse(paid["terminal_order"])
        self.assertTrue(manual["session_allowed"])
        self.assertTrue(manual["requires_manual_review"])
        self.assertFalse(unpaid["session_allowed"])
        self.assertTrue(unpaid["requires_payment"])
        self.assertFalse(cancelled_paid["session_allowed"])
        self.assertTrue(cancelled_paid["terminal_order"])

    def test_parse_communication_software_link_state_fields_extracts_server_return_aliases(self) -> None:
        parsed = parse_communication_software_link_state_fields(
            {
                "service_order_id": " svc-ord-1 ",
                "communication_software_link_session_id": " csl-1 ",
                "session_status": " READY ",
                "source_event_id": "evt-1",
                "inbound_platform_message_id": "in-msg-1",
                "outbound_platform_message_id": "out-msg-1",
                "agent_response_digest": "sha256:reply",
                "evidence_url": "https://aitokenapi.cc/evidence/evt-1",
            }
        )

        self.assertEqual(parsed["order_id"], "svc-ord-1")
        self.assertEqual(parsed["session_id"], "csl-1")
        self.assertEqual(parsed["status"], "ready")
        self.assertEqual(parsed["source_event_id"], "evt-1")
        self.assertEqual(parsed["inbound_platform_message_id"], "in-msg-1")
        self.assertEqual(parsed["outbound_platform_message_id"], "out-msg-1")
        self.assertEqual(parsed["agent_response_digest"], "sha256:reply")
        self.assertEqual(parsed["evidence_url"], "https://aitokenapi.cc/evidence/evt-1")

    def test_parse_communication_software_link_state_fields_extracts_auto_acceptance_charged(self) -> None:
        # 服务端自动验收：GET session 返回 acceptance_status=accepted + charged=true。
        accepted = parse_communication_software_link_state_fields(
            {"session_id": "csl_x", "acceptance_status": "accepted", "charged": True}
        )
        self.assertEqual(accepted["acceptance_status"], "accepted")
        self.assertIs(accepted["charged"], True)
        # 未返回 charged 时默认 False，且不因缺省而误判已扣费。
        pending = parse_communication_software_link_state_fields({"session_id": "csl_x"})
        self.assertIs(pending["charged"], False)

    def test_parse_communication_software_link_state_fields_keeps_real_acceptance_separate_from_local_precheck(self) -> None:
        parsed = parse_communication_software_link_state_fields(
            {
                "order_id": "svc-ord-1",
                "session_id": "csl-1",
                "real_service_state": "delivered",
                "platform_callback_state": "accepted",
                "adapter_status": "local_precheck_passed",
                "real_acceptance_status": "verified",
                "client_may_claim_delivery_complete": "true",
            }
        )
        defaulted = parse_communication_software_link_state_fields(
            {
                "order_id": "svc-ord-2",
                "session_id": "csl-2",
                "real_service_status": "delivered",
                "platform_callback_status": "accepted",
                "runtime_adapter_status": "local_precheck_passed",
                "acceptance_status": "verified",
            }
        )

        self.assertEqual(parsed["real_service_status"], "delivered")
        self.assertEqual(parsed["platform_callback_status"], "accepted")
        self.assertEqual(parsed["runtime_adapter_status"], "local_precheck_passed")
        self.assertEqual(parsed["acceptance_status"], "verified")
        self.assertTrue(parsed["client_may_claim_delivery_complete"])
        self.assertFalse(defaulted["client_may_claim_delivery_complete"])

    def test_parse_communication_software_link_state_fields_does_not_reuse_generic_id_for_order_and_session(self) -> None:
        parsed = parse_communication_software_link_state_fields({"id": "generic-id-1", "status": "ready"})

        self.assertEqual(parsed["order_id"], "")
        self.assertEqual(parsed["session_id"], "")
        self.assertEqual(parsed["status"], "ready")

    def test_parse_agent_center_snapshot_data_guards_admin_fields(self) -> None:
        missing = parse_agent_center_snapshot_data({})
        not_agent = parse_agent_center_snapshot_data({"status": "not_agent"})
        active = parse_agent_center_snapshot_data(
            {
                "status": "active",
                "current_level": "L2",
                "upgrade_label": "申请升级",
                "invite_url": "https://aitokenapi.cc/invite/abc",
                "join_page_url": "https://aitokenapi.cc/agent/join",
                "backend_url": "https://aitokenapi.cc/agent/center",
                "rules_url": "https://aitokenapi.cc/agent/rules",
                "settlement_status": "available",
                "last_synced_at": "2026-06-27T10:00:00+08:00",
                "summary": {
                    "downstream_count": 2,
                    "token_commission_cents": 100,
                    "activation_commission_cents": 200,
                    "agent_install_commission_cents": 300,
                    "available_settlement_cents": 400,
                    "pending_settlement_cents": 500,
                    "frozen_cents": 0,
                    "commission_ratio": "50%",
                    "rate_bps": 5000,
                    "admin_note": "internal",
                },
                "benefits": ["可绑定买家"],
                "boundaries": ["收益以后台结算为准"],
            }
        )
        guarded = parse_agent_center_snapshot_data(
            {"status": "active", "current_level": "L1", "summary": {"downstream_count": 1}}
        )

        self.assertEqual(missing["snapshot_status"], "snapshot_missing")
        self.assertIn("服务端快照未返回", "\n".join(missing["blocking_gaps"]))
        self.assertEqual(not_agent["snapshot_status"], "not_agent")
        self.assertEqual(not_agent["blocking_gaps"], [])
        self.assertEqual(active["snapshot_status"], "active")
        self.assertEqual(active["upgrade_label"], "申请升级")
        self.assertEqual(active["invite_url"], "https://aitokenapi.cc/invite/abc")
        self.assertEqual(active["join_page_url"], "https://aitokenapi.cc/agent/join")
        self.assertEqual(active["backend_url"], "https://aitokenapi.cc/agent/center")
        self.assertEqual(active["rules_url"], "https://aitokenapi.cc/agent/rules")
        self.assertEqual(active["benefits"], ["可绑定买家"])
        self.assertEqual(active["boundaries"], ["收益以后台结算为准"])
        self.assertEqual(active["summary"]["downstream_count"], 2)
        self.assertNotIn("commission_ratio", active["summary"])
        self.assertNotIn("rate_bps", active["summary"])
        self.assertNotIn("admin_note", active["summary"])
        self.assertEqual(active["missing_fields"], [])
        self.assertEqual(guarded["snapshot_status"], "guarded")
        self.assertIn("summary.token_commission_cents", guarded["missing_fields"])
        self.assertIn("last_synced_at", guarded["missing_fields"])


if __name__ == "__main__":
    unittest.main()

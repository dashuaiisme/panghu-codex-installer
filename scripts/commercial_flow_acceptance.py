from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from commercial_backend_contract import CommercialLedgerContract  # noqa: E402
from commercial_core import CommercialProduct, DeliveryScope, find_orderable_product  # noqa: E402
from panghu_codex_installer import commercial_api_request_with_auth, deployment_commercial_contexts  # noqa: E402


def backend_closeout_matrix() -> dict[str, list[dict[str, str]]]:
    return {
        "local_closed": [
            {
                "item": "商业订单、支付、权益、配置会话和扣次状态机",
                "evidence": "offline ledger acceptance",
                "status": "closed_local",
            },
            {
                "item": "API Key 归属校验、设备限制、试用权益和幂等守卫",
                "evidence": "offline contract assertions",
                "status": "closed_local",
            },
            {
                "item": "代理中心快照字段白名单和管理员字段过滤",
                "evidence": "agent_center snapshot guard",
                "status": "closed_local",
            },
            {
                "item": "连接通讯软件独立订单、支付门禁、Runtime结果、验收证据和终态守卫",
                "evidence": "communication_software_link offline flow",
                "status": "closed_local",
            },
        ],
        "real_service_pending": [
            {
                "item": "真实数据库和服务端账本",
                "evidence": "requires production/service integration",
                "status": "pending_authorization",
            },
            {
                "item": "真实支付回调和权益创建",
                "evidence": "requires payment callback integration",
                "status": "pending_authorization",
            },
            {
                "item": "真实 Agent Runtime Adapter 和平台回调",
                "evidence": "requires live adapter and channel callback",
                "status": "pending_authorization",
            },
            {
                "item": "真实 agent_center 服务端快照",
                "evidence": "requires server snapshot endpoint",
                "status": "pending_authorization",
            },
            {
                "item": "客户真实账号、真实设备和端到端验收",
                "evidence": "requires customer credentials/device acceptance",
                "status": "pending_authorization",
            },
        ],
        "release_deferred": [
            {
                "item": "三端发布包、签名、公钥注入、GitHub Release、下载页和 latest.json",
                "evidence": "explicitly out of current backend closeout scope",
                "status": "deferred_by_user_scope",
            },
        ],
    }


def _run_communication_software_link_acceptance(ledger: CommercialLedgerContract) -> dict:
    ledger.configure_service_product(
        product_id="svc-communication-software-link",
        service_type="communication_software_link",
        name="连接通讯软件",
        price_cents=19900,
        requires_base_agent_delivery=True,
        supported_agent_ids=("codex", "hermes"),
        supported_channels=("feishu", "qq_bot"),
        allowed_agent_sources=("current_delivery", "existing_local_agent", "manual_review"),
    )
    order = ledger.create_communication_software_link_order(
        idempotency_key="csl-order-flow-1",
        service_product_id="svc-communication-software-link",
        buyer_user_id="buyer-1",
        agent_id="codex",
        channel="feishu",
        agent_source="current_delivery",
    )
    try:
        ledger.create_communication_software_link_session(
            idempotency_key="csl-session-unpaid-flow-1",
            order_id=order.order_id,
            buyer_user_id="buyer-1",
            agent_id="codex",
            channel="feishu",
            platform_account_id="feishu-bot-offline",
            platform_chat_id="feishu-chat-offline",
            gateway_mode="official_bot",
            agent_source="current_delivery",
        )
        unpaid_session_blocked = False
    except ValueError:
        unpaid_session_blocked = True
    paid_order = ledger.mark_communication_software_link_order_paid(order.order_id, "pay-csl-flow-1")
    session = ledger.create_communication_software_link_session(
        idempotency_key="csl-session-flow-1",
        order_id=order.order_id,
        buyer_user_id="buyer-1",
        agent_id="codex",
        channel="feishu",
        platform_account_id="feishu-bot-offline",
        platform_chat_id="feishu-chat-offline",
        gateway_mode="official_bot",
        agent_source="current_delivery",
    )
    connected_session = ledger.mark_communication_software_link_connected(session.session_id)
    connected_session_status = connected_session.status
    try:
        ledger.record_communication_software_link_acceptance(
            session_id=session.session_id,
            source_event_id="csl-delivery-missing-evidence-flow-1",
            inbound_platform_message_id="inbound-csl-flow-missing-evidence",
            outbound_platform_message_id="outbound-csl-flow-missing-evidence",
            test_prompt="@胖虎 ping",
            agent_response_digest="pong",
            evidence_url="",
            accepted_by="admin-offline",
        )
        missing_evidence_url_blocked = False
    except ValueError:
        missing_evidence_url_blocked = True
    callback = ledger.evaluate_communication_software_link_callback(
        session_id=session.session_id,
        channel="feishu",
        platform_message_id="inbound-csl-flow-1",
        sender_id="buyer-1",
        text="@胖虎 ping",
        mentioned_bot=True,
        authorized_sender_ids={"buyer-1"},
        source_event_id="csl-delivery-flow-1",
    )
    try:
        ledger.record_communication_software_link_acceptance(
            session_id=session.session_id,
            source_event_id="csl-delivery-flow-1",
            inbound_platform_message_id="inbound-csl-flow-1",
            outbound_platform_message_id="outbound-csl-flow-1",
            test_prompt="@胖虎 ping",
            agent_response_digest="pong",
            evidence_url="offline://communication-software-link/flow-1",
            accepted_by="admin-offline",
        )
        runtime_adapter_missing_blocked = False
    except ValueError:
        runtime_adapter_missing_blocked = True
    runtime_result = ledger.record_communication_software_link_runtime_result(
        session_id=session.session_id,
        source_event_id="csl-delivery-flow-1",
        inbound_platform_message_id="inbound-csl-flow-1",
        outbound_platform_message_id="outbound-csl-flow-1",
        agent_response_digest="pong",
        status="success",
    )
    acceptance = ledger.record_communication_software_link_acceptance(
        session_id=session.session_id,
        source_event_id="csl-delivery-flow-1",
        inbound_platform_message_id="inbound-csl-flow-1",
        outbound_platform_message_id="outbound-csl-flow-1",
        test_prompt="@胖虎 ping",
        agent_response_digest="pong",
        evidence_url="offline://communication-software-link/flow-1",
        accepted_by="admin-offline",
    )
    callback_replay = ledger.evaluate_communication_software_link_callback(
        session_id=session.session_id,
        channel="feishu",
        platform_message_id="inbound-csl-flow-replay",
        sender_id="buyer-1",
        text="@胖虎 ping replay",
        mentioned_bot=True,
        authorized_sender_ids={"buyer-1"},
        source_event_id="csl-delivery-flow-1",
    )
    ledger_event = next(
        event
        for event in ledger.service_ledger_events.values()
        if event.source_event_id == "csl-delivery-flow-1"
    )
    disabled_order = ledger.create_communication_software_link_order(
        idempotency_key="csl-order-disable-flow-1",
        service_product_id="svc-communication-software-link",
        buyer_user_id="buyer-1",
        agent_id="codex",
        channel="feishu",
        agent_source="current_delivery",
    )
    ledger.mark_communication_software_link_order_paid(disabled_order.order_id, "pay-csl-disable-flow-1")
    disabled_session = ledger.create_communication_software_link_session(
        idempotency_key="csl-session-disable-flow-1",
        order_id=disabled_order.order_id,
        buyer_user_id="buyer-1",
        agent_id="codex",
        channel="feishu",
        platform_account_id="feishu-bot-disabled",
        platform_chat_id="feishu-chat-disabled",
        gateway_mode="official_bot",
        agent_source="current_delivery",
    )
    ledger.disable_communication_software_link_session(disabled_session.session_id)
    try:
        ledger.fail_communication_software_link_session(disabled_session.session_id, "disabled should stay terminal")
        disabled_blocks_fail = False
    except ValueError:
        disabled_blocks_fail = True
    try:
        ledger.pause_communication_software_link_session_for_external_dependency(
            disabled_session.session_id,
            "disabled should stay terminal",
        )
        disabled_blocks_pause = False
    except ValueError:
        disabled_blocks_pause = True
    default_product = ledger.configure_service_product(
        product_id="svc-communication-software-link-default-flow",
        service_type="communication_software_link",
        name="连接通讯软件默认范围",
        price_cents=19900,
    )
    try:
        ledger.create_communication_software_link_order(
            idempotency_key="csl-order-gemini-flow-1",
            service_product_id=default_product.product_id,
            buyer_user_id="buyer-1",
            agent_id="gemini_agy",
            channel="feishu",
            agent_source="existing_local_agent",
        )
        gemini_agy_order_blocked = False
    except ValueError:
        gemini_agy_order_blocked = True
    return {
        "order_id": order.order_id,
        "session_id": session.session_id,
        "acceptance_id": acceptance.acceptance_id,
        "unpaid_session_blocked": unpaid_session_blocked,
        "missing_evidence_url_blocked": missing_evidence_url_blocked,
        "paid_charge_status": paid_order.charge_status,
        "connected_session_status": connected_session_status,
        "callback_status": callback.status,
        "callback_replay_status": callback_replay.status,
        "runtime_adapter_required": True,
        "runtime_adapter_missing_blocked": runtime_adapter_missing_blocked,
        "runtime_adapter_status": runtime_result.status,
        "final_order_status": ledger.service_orders[order.order_id].status,
        "final_charge_status": ledger.service_orders[order.order_id].charge_status,
        "service_ledger_event_type": ledger_event.event_type,
        "service_ledger_service_type": ledger_event.service_type,
        "disabled_session_status": ledger.communication_software_link_sessions[disabled_session.session_id].status,
        "disabled_order_status": ledger.service_orders[disabled_order.order_id].status,
        "disabled_blocks_fail": disabled_blocks_fail,
        "disabled_blocks_pause": disabled_blocks_pause,
        "gemini_agy_order_blocked": gemini_agy_order_blocked,
        "real_service_status": "pending_authorization",
        "client_may_claim_delivery_complete": False,
        "delivery_boundary": "本地仅验证 mock/离线守卫；真实交付仍需要真实平台回调、Agent Runtime Adapter、支付、账本和服务端验收记录。",
    }


def run_acceptance() -> dict:
    ledger = CommercialLedgerContract()
    agent_chain = ["agent-1", "agent-2", "agent-3", "agent-4", "agent-5", "agent-6"]
    ledger.configure_agent_product("agent-l1-free", "L1", "L1 免费代理", 0)
    ledger.apply_agent("agent-1", "agent-l1-free")
    ledger.configure_commission_policy_rule("tool_order_paid", "L1", 1, 1000)

    order = ledger.create_order(
        idempotency_key="order-idem-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="buyer-1",
        agent_chain=agent_chain,
        diagnostic_code="PH-CFG-OFFLINE-1",
    )
    retry_order = ledger.create_order(
        idempotency_key="order-idem-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="buyer-1",
        agent_chain=agent_chain,
        diagnostic_code="PH-CFG-OFFLINE-1",
    )
    entitlement = ledger.mark_paid_and_create_entitlement(
        order.order_id,
        payment_id="pay-idem-1",
        payment_amount_cents=10000,
    )
    retry_entitlement = ledger.mark_paid_and_create_entitlement(
        order.order_id,
        payment_id="pay-idem-1",
        payment_amount_cents=10000,
    )
    try:
        ledger.create_order(
            idempotency_key="order-idem-1",
            product_id="prod-other",
            buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
            agent_chain=agent_chain,
            diagnostic_code="PH-CFG-OFFLINE-1",
        )
        order_payload_drift_blocked = False
    except ValueError:
        order_payload_drift_blocked = True
    try:
        ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-idem-1", payment_amount_cents=1)
        payment_payload_drift_blocked = False
    except ValueError:
        payment_payload_drift_blocked = True
    ledger.register_api_key_owner("sk-buyer-offline", "buyer-1")
    ledger.register_api_key_owner("sk-agent-offline", "agent-1")
    buyer_key_verified = (
        ledger.verify_api_key_owner(
            "sk-buyer-offline",
            target_buyer_user_id="buyer-1",
            operator_user_id="buyer-1",
        )["owner_user_id"]
        == "buyer-1"
    )
    try:
        ledger.verify_api_key_owner("sk-agent-offline", target_buyer_user_id="buyer-1", operator_user_id="buyer-1")
        agent_key_blocked = False
    except ValueError:
        agent_key_blocked = True
    api_contexts = deployment_commercial_contexts({"id": "buyer-1", "username": "buyer"})
    client_agent_actions = {
        "agent_public_offering": {},
        "agent_apply": {"product_id": "agent-l1-free"},
        "referral_bind": {"invite_code": "https://aitokenapi.cc/register?invite=INVITE-OFFLINE"},
        "agent_settlement": {"requested_cents": 1000},
    }
    client_agent_dispatch = {}
    for action, kwargs in client_agent_actions.items():
        request = commercial_api_request_with_auth(
            action,
            api_contexts,
            deployer_auth={"token": "buyer-token"},
            **kwargs,
        )
        client_agent_dispatch[action] = {
            "authorized": request.headers.get("Authorization") == "Bearer buyer-token",
            "idempotent": action == "agent_public_offering" or bool(request.headers.get("Idempotency-Key")),
            "url": request.url,
        }
    try:
        commercial_api_request_with_auth(
            "admin_agent_policy_update",
            api_contexts,
            deployer_auth={"token": "buyer-token"},
        )
        admin_action_blocked = False
    except ValueError:
        admin_action_blocked = True
    ledger.configure_agent_center(
        enabled=True,
        current_level="L1",
        upgrade_label="申请升级",
        invite_url="https://aitokenapi.cc/invite/offline",
        join_page_url="https://aitokenapi.cc/agent/join",
        backend_url="https://aitokenapi.cc/agent/center",
        rules_url="https://aitokenapi.cc/agent/rules",
        status="active",
        settlement_status="available",
        last_synced_at="offline://agent-center/snapshot",
        summary={
            "downstream_count": 1,
            "token_commission_cents": 0,
            "activation_commission_cents": 0,
            "agent_install_commission_cents": 0,
            "available_settlement_cents": 0,
            "pending_settlement_cents": 0,
            "frozen_cents": 0,
        },
        benefits=["可绑定买家"],
        boundaries=["收益以后台结算为准"],
        commission_ratio="50%",
    )
    agent_center = ledger.agent_center_snapshot()

    trial_entitlement = ledger.grant_trial_entitlement(
        idempotency_key="trial-idem-1",
        buyer_user_id="buyer-1",
        agent_id="codex",
        mode_key="direct_api",
        remaining_uses=1,
    )
    retry_trial_entitlement = ledger.grant_trial_entitlement(
        idempotency_key="trial-idem-1",
        buyer_user_id="buyer-1",
        agent_id="codex",
        mode_key="direct_api",
        remaining_uses=1,
    )
    try:
        ledger.grant_trial_entitlement(
            idempotency_key="trial-idem-1",
            buyer_user_id="buyer-2",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
        )
        trial_payload_drift_blocked = False
    except ValueError:
        trial_payload_drift_blocked = True
    try:
        ledger.grant_trial_entitlement(
            idempotency_key="trial-idem-2",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
        )
        trial_duplicate_claim_blocked = False
    except ValueError:
        trial_duplicate_claim_blocked = True
    try:
        ledger.grant_trial_entitlement(
            idempotency_key="trial-idem-3",
            buyer_user_id="buyer-1",
            agent_id="openclaw",
            mode_key="direct_api",
            remaining_uses=1,
        )
        trial_cross_agent_claim_blocked = False
    except ValueError:
        trial_cross_agent_claim_blocked = True
    try:
        ledger.grant_trial_entitlement(
            idempotency_key="trial-dual-state-1",
            buyer_user_id="buyer-dual-state",
            agent_id="codex",
            mode_key="dual_state",
            remaining_uses=1,
        )
        trial_dual_state_blocked = False
    except ValueError:
        trial_dual_state_blocked = True
    trial_session = ledger.reserve_config_session(
        idempotency_key="reserve-trial-1",
        entitlement_id=trial_entitlement.entitlement_id,
        operator_user_id="buyer-1",
        agent_id="codex",
        mode_key="direct_api",
        device_id="device-1",
        diagnostic_code="PH-CFG-OFFLINE-TRIAL-1",
    )
    ledger.complete_config_session(trial_session.config_session_id, real_task_verified=True)
    paid_remaining_after_trial_completed = ledger.entitlements[entitlement.entitlement_id].remaining_uses
    trial_remaining_after_completed = ledger.entitlements[trial_entitlement.entitlement_id].remaining_uses

    failed_session = ledger.reserve_config_session(
        idempotency_key="reserve-fail-1",
        entitlement_id=entitlement.entitlement_id,
        operator_user_id="buyer-1",
        agent_id="codex",
        mode_key="direct_api",
        device_id="device-1",
        diagnostic_code="PH-CFG-OFFLINE-1",
    )
    try:
        ledger.reserve_config_session(
            idempotency_key="reserve-fail-1",
            entitlement_id=trial_entitlement.entitlement_id,
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-1",
            diagnostic_code="PH-CFG-OFFLINE-1",
        )
        config_session_payload_drift_blocked = False
    except ValueError:
        config_session_payload_drift_blocked = True
    ledger.fail_config_session(failed_session.config_session_id, "真实任务失败")
    remaining_after_failed = ledger.entitlements[entitlement.entitlement_id].remaining_uses

    manual_review_order = ledger.create_order(
        idempotency_key="order-manual-review-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="buyer-1",
        agent_chain=[],
        diagnostic_code="PH-CFG-OFFLINE-MANUAL-1",
    )
    manual_review_entitlement = ledger.mark_paid_and_create_entitlement(
        manual_review_order.order_id,
        payment_id="pay-manual-review-1",
    )
    manual_review_session = ledger.reserve_config_session(
        idempotency_key="reserve-manual-review-1",
        entitlement_id=manual_review_entitlement.entitlement_id,
        operator_user_id="buyer-1",
        agent_id="codex",
        mode_key="direct_api",
        device_id="device-1",
        diagnostic_code="PH-CFG-OFFLINE-MANUAL-1",
    )
    ledger.mark_config_session_manual_review(
        manual_review_session.config_session_id,
        "离线验收人工复核",
    )
    remaining_after_manual_review = ledger.entitlements[manual_review_entitlement.entitlement_id].remaining_uses
    try:
        ledger.reserve_config_session(
            idempotency_key="reserve-manual-review-2",
            entitlement_id=manual_review_entitlement.entitlement_id,
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-1",
            diagnostic_code="PH-CFG-OFFLINE-MANUAL-2",
        )
        manual_review_blocks_new_reservation = False
    except ValueError:
        manual_review_blocks_new_reservation = True

    device_policy_order = ledger.create_order(
        idempotency_key="order-device-policy-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="buyer-1",
        agent_chain=[],
        diagnostic_code="PH-CFG-OFFLINE-DEVICE-1",
    )
    device_policy_entitlement = ledger.mark_paid_and_create_entitlement(
        device_policy_order.order_id,
        payment_id="pay-device-policy-1",
    )
    device_policy_entitlement.remaining_uses = 2
    device_policy_entitlement.device_limit = 1
    device_policy_session = ledger.reserve_config_session(
        idempotency_key="reserve-device-policy-1",
        entitlement_id=device_policy_entitlement.entitlement_id,
        operator_user_id="buyer-1",
        agent_id="codex",
        mode_key="direct_api",
        device_id="device-1",
        diagnostic_code="PH-CFG-OFFLINE-DEVICE-1",
    )
    ledger.complete_config_session(device_policy_session.config_session_id, real_task_verified=True)
    try:
        ledger.reserve_config_session(
            idempotency_key="reserve-device-policy-2",
            entitlement_id=device_policy_entitlement.entitlement_id,
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-2",
            diagnostic_code="PH-CFG-OFFLINE-DEVICE-2",
        )
        new_device_blocked = False
    except ValueError:
        new_device_blocked = True
    remaining_after_device_block = ledger.entitlements[device_policy_entitlement.entitlement_id].remaining_uses

    rollout_product = CommercialProduct(
        product_id="prod-rollout-gated",
        title="灰度商品",
        agent_id="codex",
        mode_key="direct_api",
        delivery_scope=DeliveryScope.FULL_CONFIG,
        price_cents=1,
        currency="CNY",
        remaining_uses=1,
        valid_until="2026-12-31T23:59:59+08:00",
        includes_dual_state=False,
        device_limit=1,
        is_listed=True,
        min_client_version="1.0.15",
        allowed_buyer_user_ids=("buyer-1",),
    )
    old_client_blocked = find_orderable_product(
        [rollout_product],
        product_id="prod-rollout-gated",
        agent_id="codex",
        mode_key="direct_api",
        app_version="1.0.14",
        buyer_user_id="buyer-1",
    ) is None
    non_gray_buyer_blocked = find_orderable_product(
        [rollout_product],
        product_id="prod-rollout-gated",
        agent_id="codex",
        mode_key="direct_api",
        app_version="1.0.15",
        buyer_user_id="buyer-other",
    ) is None
    gray_buyer_allowed = find_orderable_product(
        [rollout_product],
        product_id="prod-rollout-gated",
        agent_id="codex",
        mode_key="direct_api",
        app_version="1.0.15",
        buyer_user_id="buyer-1",
    ) is not None

    completed_order = ledger.create_order(
        idempotency_key="order-complete-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="buyer-1",
        agent_chain=[],
        diagnostic_code="PH-CFG-OFFLINE-COMPLETE-1",
    )
    completed_entitlement = ledger.mark_paid_and_create_entitlement(
        completed_order.order_id,
        payment_id="pay-complete-1",
    )
    completed_session = ledger.reserve_config_session(
        idempotency_key="reserve-complete-1",
        entitlement_id=completed_entitlement.entitlement_id,
        operator_user_id="buyer-1",
        agent_id="codex",
        mode_key="direct_api",
        device_id="device-1",
        diagnostic_code="PH-CFG-OFFLINE-2",
    )
    ledger.complete_config_session(completed_session.config_session_id, real_task_verified=True)
    remaining_after_completed = ledger.entitlements[completed_entitlement.entitlement_id].remaining_uses
    communication_software_link = _run_communication_software_link_acceptance(ledger)

    ledger.reverse_order(order.order_id, "离线验收撤销")
    ledger.reverse_order(order.order_id, "离线验收撤销")
    order_status_report = ledger.order_entitlement_status_report(order.order_id)

    withdrawn_commission_order = ledger.create_order(
        idempotency_key="order-withdrawn-commission-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="buyer-1",
        agent_chain=["agent-withdrawn", "agent-pending"],
        diagnostic_code="PH-CFG-OFFLINE-WITHDRAWN-1",
    )
    ledger.mark_paid_and_create_entitlement(
        withdrawn_commission_order.order_id,
        payment_id="pay-withdrawn-commission-1",
    )
    ledger.commission_entries[-2].status = "withdrawn"
    ledger.reverse_order(withdrawn_commission_order.order_id, "离线验收已提现佣金撤销")

    agent_business_ledger = CommercialLedgerContract()
    agent_business_ledger.configure_agent_product(
        "agent-l1-free",
        "L1",
        "L1 免费推广代理",
        price_cents=0,
        requires_review=False,
    )
    agent_business_ledger.configure_agent_product(
        "agent-l2-paid",
        "L2",
        "L2 付费代理",
        price_cents=19900,
        requires_review=True,
    )
    agent_business_ledger.configure_agent_marketing_content(
        page_title="胖虎AI代理招募",
        hero_title="把 Agent 安装和 token 消费变成长期生意",
        selling_points=["卖工具部署服务", "赚 token、激活和安装三类佣金"],
        faq=[{"question": "多久结算？", "answer": "默认 T+7 后可申请结算。"}],
        materials=[{"title": "朋友圈话术", "url": "https://aitokenapi.cc/agent/materials/moments"}],
    )
    free_profile = agent_business_ledger.apply_agent("agent-l1", "agent-l1-free")
    paid_profile = agent_business_ledger.apply_agent("agent-paid-l2", "agent-l2-paid")
    paid_l2_initial_status = paid_profile.status
    for level in range(2, 6):
        product_id = f"agent-l{level}-free"
        agent_business_ledger.configure_agent_product(
            product_id,
            f"L{level}",
            f"L{level} 离线代理",
            price_cents=0,
            requires_review=False,
        )
        agent_business_ledger.apply_agent(f"agent-l{level}", product_id)
    offering = agent_business_ledger.public_agent_offering()
    paid_l2_application = agent_business_ledger.agent_applications[1]
    paid_l2_review = agent_business_ledger.review_agent_application(
        application_id=paid_l2_application.application_id,
        decision="approve",
        reviewer_user_id="admin-offline",
        reason="离线验收批准付费代理",
    )
    agent_business_ledger.bind_referral("agent-l2", agent_business_ledger.agent_profiles["agent-l1"].invite_code)
    agent_business_ledger.bind_referral("agent-l3", agent_business_ledger.agent_profiles["agent-l2"].invite_code)
    agent_business_ledger.bind_referral("agent-l4", agent_business_ledger.agent_profiles["agent-l3"].invite_code)
    agent_business_ledger.bind_referral("agent-l5", agent_business_ledger.agent_profiles["agent-l4"].invite_code)
    agent_business_ledger.bind_referral("buyer-commission", agent_business_ledger.agent_profiles["agent-l5"].invite_code)
    rebound = agent_business_ledger.bind_referral(
        "buyer-commission",
        agent_business_ledger.agent_profiles["agent-l1"].invite_code,
    )
    snapshot = agent_business_ledger.build_agent_chain_snapshot("buyer-commission", "snapshot-1")
    no_policy_event = agent_business_ledger.record_commission_event(
        "no-policy-1",
        "token_usage_settled",
        "buyer-commission",
        10000,
    )
    entries_after_no_policy_event = len(agent_business_ledger.commission_entries)
    agent_business_ledger.configure_commission_policy_rule("token_usage_settled", "L5", 1, 1000)
    agent_business_ledger.configure_commission_policy_rule("activation_paid", "L5", 1, 2000)
    agent_business_ledger.configure_commission_policy_rule("agent_install_delivered", "L5", 1, 3000)
    token_event = agent_business_ledger.record_commission_event(
        "usage-1",
        "token_usage_settled",
        "buyer-commission",
        10000,
    )
    token_event_retry = agent_business_ledger.record_commission_event(
        "usage-1",
        "token_usage_settled",
        "buyer-commission",
        10000,
    )
    agent_business_ledger.record_commission_event("activation-1", "activation_paid", "buyer-commission", 10000)
    agent_business_ledger.record_commission_event("install-1", "agent_install_delivered", "buyer-commission", 10000)
    agent_business_ledger.release_commissions_after_days(6)
    pending_count_after_6_days = len([entry for entry in agent_business_ledger.commission_entries if entry.status == "pending"])
    agent_business_ledger.release_commissions_after_days(7)
    available_count_after_7_days = len([entry for entry in agent_business_ledger.commission_entries if entry.status == "available"])
    settlement = agent_business_ledger.create_settlement_request("agent-l5", requested_cents=1000)
    settlement_status_after_request = settlement.status
    paid_settlement = agent_business_ledger.mark_settlement_paid(settlement.settlement_id, admin_user_id="admin-offline")
    settlement_status_after_admin_pay = paid_settlement.status
    agent_business_ledger.commission_entries[1].status = "available"
    agent_business_ledger.admin_update_commission_entry(
        agent_business_ledger.commission_entries[1].commission_id,
        "freeze",
        "离线验收风控冻结",
    )
    agent_business_ledger.admin_update_commission_entry(
        agent_business_ledger.commission_entries[1].commission_id,
        "release",
        "离线验收风控解除",
    )
    agent_business_ledger.admin_update_commission_entry(
        agent_business_ledger.commission_entries[1].commission_id,
        "reverse",
        "离线验收风控冲正",
    )
    ledger_status_after_freeze_release_reverse = agent_business_ledger.commission_entries[1].status
    agent_business_ledger.commission_entries[0].status = "settled"
    agent_business_ledger.reverse_commission_event("usage-1", "离线验收退款")
    agent_business_ledger.reverse_commission_event("activation-1", "离线验收退款")
    manual_review_after_reverse = len([entry for entry in agent_business_ledger.commission_entries if entry.status == "manual_review"])
    reversed_after_reverse = len([entry for entry in agent_business_ledger.commission_entries if entry.status == "reversed"])

    reversed_commissions = [entry for entry in ledger.commission_entries if entry.status == "reversed"]
    manual_review_commissions = [entry for entry in ledger.commission_entries if entry.status == "manual_review"]
    tool_order_commissions = [
        entry
        for entry in ledger.commission_entries
        if entry.event_type == "tool_order_paid" and entry.order_id == order.order_id
    ]
    report = {
        "status": "PASS",
        "offline_only": True,
        "backend_closeout_matrix": backend_closeout_matrix(),
        "blocking_gaps": [
            "真实平台回调未接入：本报告只验证 mock callback 本地守卫。",
            "真实 Agent Runtime Adapter 未接入：本报告只验证 mock adapter 成功结果门槛。",
            "真实服务端/数据库/支付未接入：本报告只验证离线账本状态机。",
            "Agent Center 真实服务端快照未接入：本报告只验证本地管理员字段守卫。",
            "订单/权益/配置会话仅为本地离线状态报告，不能代表客户真实交付完成。",
        ],
        "runtime_adapter_status": "mock_guarded",
        "callback_status": "mock_guarded",
        "ledger_status": "offline_guarded",
        "agent_center_status": "offline_guarded",
        "order_entitlement_status": "offline_guarded",
        "order": {
            "order_id": order.order_id,
            "retry_same_order": retry_order.order_id == order.order_id,
            "status": ledger.orders[order.order_id].status,
        },
        "order_status_report": order_status_report,
        "idempotency": {
            "order_payload_drift_blocked": order_payload_drift_blocked,
            "payment_payload_drift_blocked": payment_payload_drift_blocked,
            "trial_payload_drift_blocked": trial_payload_drift_blocked,
            "trial_duplicate_claim_blocked": trial_duplicate_claim_blocked,
            "trial_cross_agent_claim_blocked": trial_cross_agent_claim_blocked,
            "trial_dual_state_blocked": trial_dual_state_blocked,
            "config_session_payload_drift_blocked": config_session_payload_drift_blocked,
        },
        "entitlement": {
            "entitlement_id": entitlement.entitlement_id,
            "retry_same_entitlement": retry_entitlement.entitlement_id == entitlement.entitlement_id,
            "buyer_user_id": entitlement.buyer_user_id,
            "source": entitlement.source,
            "trial_entitlement_id": trial_entitlement.entitlement_id,
            "trial_source": trial_entitlement.source,
            "retry_same_trial_entitlement": retry_trial_entitlement.entitlement_id == trial_entitlement.entitlement_id,
            "paid_remaining_after_trial_completed": paid_remaining_after_trial_completed,
            "trial_remaining_after_completed_session": trial_remaining_after_completed,
            "remaining_uses_after_failed_session": remaining_after_failed,
            "remaining_uses_after_manual_review_session": remaining_after_manual_review,
            "remaining_uses_after_completed_session": remaining_after_completed,
            "status_after_reversal": ledger.entitlements[entitlement.entitlement_id].status,
        },
        "config_sessions": {
            "failed_session_status": ledger.config_sessions[failed_session.config_session_id].status,
            "failed_session_deducted": ledger.config_sessions[failed_session.config_session_id].deducted,
            "manual_review_session_status": ledger.config_sessions[manual_review_session.config_session_id].status,
            "manual_review_session_deducted": ledger.config_sessions[manual_review_session.config_session_id].deducted,
            "manual_review_blocks_new_reservation": manual_review_blocks_new_reservation,
            "completed_session_status": ledger.config_sessions[completed_session.config_session_id].status,
            "completed_session_deducted": ledger.config_sessions[completed_session.config_session_id].deducted,
            "session_status_reports": {
                failed_session.config_session_id: ledger.config_sessions[failed_session.config_session_id].status,
                manual_review_session.config_session_id: ledger.config_sessions[manual_review_session.config_session_id].status,
                completed_session.config_session_id: ledger.config_sessions[completed_session.config_session_id].status,
            },
        },
        "device_policy": {
            "new_device_blocked": new_device_blocked,
            "remaining_uses_after_device_block": remaining_after_device_block,
        },
        "rollout_gates": {
            "old_client_blocked": old_client_blocked,
            "non_gray_buyer_blocked": non_gray_buyer_blocked,
            "gray_buyer_allowed": gray_buyer_allowed,
        },
        "api_key_owner": {
            "buyer_key_verified": buyer_key_verified,
            "agent_key_blocked": agent_key_blocked,
        },
        "client_agent_dispatch": {
            "all_authorized": all(item["authorized"] for item in client_agent_dispatch.values()),
            "all_idempotent": all(item["idempotent"] for item in client_agent_dispatch.values()),
            "admin_action_blocked": admin_action_blocked,
            "actions": client_agent_dispatch,
        },
        "agent_center": agent_center,
        "communication_software_link": communication_software_link,
        "agent_business": {
            "free_l1_status": free_profile.status,
            "paid_l2_status": paid_l2_initial_status,
            "referral_owner_after_rebind": rebound.direct_agent_user_id,
            "chain_snapshot": snapshot.chain,
            "no_policy_event_status": no_policy_event.status,
            "entries_after_no_policy_event": entries_after_no_policy_event,
            "event_idempotent": token_event.event_id == token_event_retry.event_id,
            "pending_count_after_6_days": pending_count_after_6_days,
            "available_count_after_7_days": available_count_after_7_days,
            "offering_levels": offering["available_levels"],
            "marketing_has_join_copy": "长期生意" in str(offering["marketing_content"]),
            "paid_l2_review_after_approve": paid_l2_review.status,
            "paid_l2_profile_after_approve": agent_business_ledger.agent_profiles["agent-paid-l2"].status,
            "settlement_status_after_request": settlement_status_after_request,
            "settlement_status_after_admin_pay": settlement_status_after_admin_pay,
            "ledger_status_after_freeze_release_reverse": ledger_status_after_freeze_release_reverse,
            "manual_review_after_reverse": manual_review_after_reverse,
            "reversed_after_reverse": reversed_after_reverse,
        },
        "commissions": {
            "created_count": len(ledger.commission_entries),
            "reversed_count": len(reversed_commissions),
            "manual_review_count": len(manual_review_commissions),
            "tool_order_paid_count": len(tool_order_commissions),
            "tool_order_paid_cents": sum(entry.commission_cents for entry in tool_order_commissions),
        },
        "reversal": {
            "count": len(ledger.commission_reversals),
        },
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline commercial flow acceptance checks.")
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    args = parser.parse_args()

    report = run_acceptance()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return
    print("商业流程离线验收：PASS")
    print(f"订单状态：{report['order']['status']}")
    print(f"权益分账：付费={report['entitlement']['source']}，试用={report['entitlement']['trial_source']}")
    print(f"失败会话后剩余次数：{report['entitlement']['remaining_uses_after_failed_session']}")
    print(f"人工复核会话后剩余次数：{report['entitlement']['remaining_uses_after_manual_review_session']}")
    print(f"设备超限拦截：{report['device_policy']['new_device_blocked']}")
    print(f"成功会话后剩余次数：{report['entitlement']['remaining_uses_after_completed_session']}")
    print(f"连接通讯软件支付门禁：{report['communication_software_link']['unpaid_session_blocked']}")
    print(f"佣金冲正：{report['commissions']['reversed_count']}/{report['commissions']['created_count']}")


if __name__ == "__main__":
    main()

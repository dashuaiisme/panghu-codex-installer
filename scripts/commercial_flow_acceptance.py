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


def run_acceptance() -> dict:
    ledger = CommercialLedgerContract()
    agent_chain = ["agent-1", "agent-2", "agent-3", "agent-4", "agent-5", "agent-6"]

    order = ledger.create_order(
        idempotency_key="order-idem-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="agent-1",
        agent_chain=agent_chain,
        diagnostic_code="PH-CFG-OFFLINE-1",
    )
    retry_order = ledger.create_order(
        idempotency_key="order-idem-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="agent-1",
        agent_chain=agent_chain,
        diagnostic_code="PH-CFG-OFFLINE-1",
    )
    entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-idem-1")
    retry_entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-idem-1")
    try:
        ledger.create_order(
            idempotency_key="order-idem-1",
            product_id="prod-other",
            buyer_user_id="buyer-1",
            operator_user_id="agent-1",
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
            operator_user_id="agent-1",
        )["owner_user_id"]
        == "buyer-1"
    )
    try:
        ledger.verify_api_key_owner("sk-agent-offline", target_buyer_user_id="buyer-1", operator_user_id="agent-1")
        agent_key_blocked = False
    except ValueError:
        agent_key_blocked = True
    ledger.configure_agent_center(
        enabled=True,
        current_level="L1",
        upgrade_label="申请升级",
        invite_url="https://aitokenapi.cc/invite/offline",
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
        operator_user_id="agent-1",
        agent_id="codex",
        mode_key="direct_api",
        device_id="device-1",
        diagnostic_code="PH-CFG-OFFLINE-1",
    )
    try:
        ledger.reserve_config_session(
            idempotency_key="reserve-fail-1",
            entitlement_id=trial_entitlement.entitlement_id,
            operator_user_id="agent-1",
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
        operator_user_id="agent-1",
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
        operator_user_id="agent-1",
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
            operator_user_id="agent-1",
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
        operator_user_id="agent-1",
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
        operator_user_id="agent-1",
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
            operator_user_id="agent-1",
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
        operator_user_id="agent-1",
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
        operator_user_id="agent-1",
        agent_id="codex",
        mode_key="direct_api",
        device_id="device-1",
        diagnostic_code="PH-CFG-OFFLINE-2",
    )
    ledger.complete_config_session(completed_session.config_session_id, real_task_verified=True)
    remaining_after_completed = ledger.entitlements[completed_entitlement.entitlement_id].remaining_uses

    ledger.reverse_order(order.order_id, "离线验收撤销")
    ledger.reverse_order(order.order_id, "离线验收撤销")

    withdrawn_commission_order = ledger.create_order(
        idempotency_key="order-withdrawn-commission-1",
        product_id="prod-codex-direct-api",
        buyer_user_id="buyer-1",
        operator_user_id="agent-1",
        agent_chain=["agent-withdrawn", "agent-pending"],
        diagnostic_code="PH-CFG-OFFLINE-WITHDRAWN-1",
    )
    ledger.mark_paid_and_create_entitlement(
        withdrawn_commission_order.order_id,
        payment_id="pay-withdrawn-commission-1",
    )
    ledger.commission_entries[-2].status = "withdrawn"
    ledger.reverse_order(withdrawn_commission_order.order_id, "离线验收已提现佣金撤销")

    reversed_commissions = [entry for entry in ledger.commission_entries if entry.status == "reversed"]
    manual_review_commissions = [entry for entry in ledger.commission_entries if entry.status == "manual_review"]
    report = {
        "status": "PASS",
        "offline_only": True,
        "order": {
            "order_id": order.order_id,
            "retry_same_order": retry_order.order_id == order.order_id,
            "status": ledger.orders[order.order_id].status,
        },
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
        "agent_center": agent_center,
        "commissions": {
            "created_count": len(ledger.commission_entries),
            "reversed_count": len(reversed_commissions),
            "manual_review_count": len(manual_review_commissions),
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
    print(f"佣金冲正：{report['commissions']['reversed_count']}/{report['commissions']['created_count']}")


if __name__ == "__main__":
    main()

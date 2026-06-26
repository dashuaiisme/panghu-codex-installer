import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from commercial_backend_contract import CommercialLedgerContract  # noqa: E402


class CommercialBackendContractTests(unittest.TestCase):
    def test_paid_order_creates_buyer_entitlement_and_commission_once(self) -> None:
        ledger = CommercialLedgerContract()

        order = ledger.create_order(
            idempotency_key="order-1",
            product_id="prod-codex",
            buyer_user_id="buyer-1",
            operator_user_id="agent-1",
            agent_chain=["agent-1", "agent-parent"],
            diagnostic_code="PH-CFG-1",
        )
        retry = ledger.create_order(
            idempotency_key="order-1",
            product_id="prod-codex",
            buyer_user_id="buyer-1",
            operator_user_id="agent-1",
            agent_chain=["agent-1", "agent-parent"],
            diagnostic_code="PH-CFG-1",
        )

        self.assertEqual(order.order_id, retry.order_id)

        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-1")
        retry_entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-1")

        self.assertEqual(entitlement.entitlement_id, retry_entitlement.entitlement_id)
        self.assertEqual(entitlement.buyer_user_id, "buyer-1")
        self.assertEqual(len(ledger.commission_entries), 2)

    def test_idempotency_keys_reject_payload_drift_in_commercial_ledger(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order(
            idempotency_key="order-1",
            product_id="prod-codex",
            buyer_user_id="buyer-1",
            operator_user_id="agent-1",
            agent_chain=["agent-1"],
            diagnostic_code="PH-CFG-1",
        )
        paid = ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-1")
        trial = ledger.grant_trial_entitlement(
            idempotency_key="trial-1",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
        )
        session = ledger.reserve_config_session(
            idempotency_key="reserve-1",
            entitlement_id=paid.entitlement_id,
            operator_user_id="agent-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-1",
            diagnostic_code="PH-CFG-1",
        )

        with self.assertRaisesRegex(ValueError, "幂等"):
            ledger.create_order("order-1", "prod-other", "buyer-1", "agent-1", ["agent-1"], "PH-CFG-1")
        with self.assertRaisesRegex(ValueError, "幂等"):
            ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-1", payment_amount_cents=999)
        with self.assertRaisesRegex(ValueError, "幂等"):
            ledger.grant_trial_entitlement("trial-1", "buyer-2", "codex", "direct_api", 1)
        with self.assertRaisesRegex(ValueError, "幂等"):
            ledger.reserve_config_session(
                "reserve-1",
                trial.entitlement_id,
                "agent-1",
                "codex",
                "direct_api",
                "device-1",
                "PH-CFG-1",
            )
        self.assertEqual(session.entitlement_id, paid.entitlement_id)

    def test_trial_and_paid_entitlements_use_separate_ledgers(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "agent-1", ["agent-1"], "PH-CFG-1")
        paid = ledger.mark_paid_and_create_entitlement(order.order_id, payment_id="pay-1")
        trial = ledger.grant_trial_entitlement(
            idempotency_key="trial-1",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
        )
        retry_trial = ledger.grant_trial_entitlement(
            idempotency_key="trial-1",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
        )

        self.assertEqual(paid.source, "paid")
        self.assertEqual(trial.source, "trial")
        self.assertEqual(trial.order_id, "")
        self.assertEqual(trial.entitlement_id, retry_trial.entitlement_id)
        self.assertEqual(len(ledger.commission_entries), 1)

        trial_session = ledger.reserve_config_session(
            "reserve-trial-1",
            trial.entitlement_id,
            "buyer-1",
            "codex",
            "direct_api",
            "device-1",
            "PH-CFG-TRIAL-1",
        )
        ledger.complete_config_session(trial_session.config_session_id, real_task_verified=True)

        self.assertEqual(ledger.entitlements[trial.entitlement_id].remaining_uses, 0)
        self.assertEqual(ledger.entitlements[paid.entitlement_id].remaining_uses, 1)

    def test_trial_entitlement_cannot_be_claimed_twice_by_same_buyer_even_with_new_idempotency_key(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.grant_trial_entitlement(
            idempotency_key="trial-1",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
        )

        with self.assertRaisesRegex(ValueError, "试用权益"):
            ledger.grant_trial_entitlement(
                idempotency_key="trial-2",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=1,
            )

    def test_trial_entitlement_cannot_be_claimed_for_another_agent_by_same_buyer(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.grant_trial_entitlement(
            idempotency_key="trial-1",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
        )

        with self.assertRaisesRegex(ValueError, "试用权益"):
            ledger.grant_trial_entitlement(
                idempotency_key="trial-2",
                buyer_user_id="buyer-1",
                agent_id="openclaw",
                mode_key="direct_api",
                remaining_uses=1,
            )

    def test_trial_entitlement_rejects_dual_state_mode(self) -> None:
        ledger = CommercialLedgerContract()

        with self.assertRaisesRegex(ValueError, "双态"):
            ledger.grant_trial_entitlement(
                idempotency_key="trial-1",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="dual_state",
                remaining_uses=1,
            )

    def test_config_session_reserve_complete_and_fail_are_idempotent(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "buyer-1", [], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")

        session = ledger.reserve_config_session(
            idempotency_key="reserve-1",
            entitlement_id=entitlement.entitlement_id,
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-1",
            diagnostic_code="PH-CFG-1",
        )
        retry = ledger.reserve_config_session(
            idempotency_key="reserve-1",
            entitlement_id=entitlement.entitlement_id,
            operator_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            device_id="device-1",
            diagnostic_code="PH-CFG-1",
        )

        self.assertEqual(session.config_session_id, retry.config_session_id)

        completed = ledger.complete_config_session(session.config_session_id, real_task_verified=True)
        retry_completed = ledger.complete_config_session(session.config_session_id, real_task_verified=True)

        self.assertTrue(completed)
        self.assertTrue(retry_completed)
        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 0)

    def test_unlimited_entitlement_can_complete_multiple_sessions_without_decrementing(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "buyer-1", [], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1", is_unlimited=True)

        first = ledger.reserve_config_session("reserve-1", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-1")
        ledger.complete_config_session(first.config_session_id, real_task_verified=True)
        second = ledger.reserve_config_session("reserve-2", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-2")
        ledger.complete_config_session(second.config_session_id, real_task_verified=True)

        self.assertTrue(ledger.entitlements[entitlement.entitlement_id].is_unlimited)
        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 0)

    def test_failed_config_session_releases_reservation_without_deducting(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "buyer-1", [], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")
        session = ledger.reserve_config_session("reserve-1", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-1")

        ledger.fail_config_session(session.config_session_id, "真实任务失败")

        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 1)
        self.assertEqual(ledger.config_sessions[session.config_session_id].status, "failed")
        with self.assertRaisesRegex(ValueError, "已失败"):
            ledger.complete_config_session(session.config_session_id, real_task_verified=True)
        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 1)

    def test_manual_review_session_freezes_without_deducting_or_auto_reclosing(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "buyer-1", [], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")
        session = ledger.reserve_config_session("reserve-1", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-1")

        ledger.mark_config_session_manual_review(session.config_session_id, "等待客服确认真实任务")
        ledger.mark_config_session_manual_review(session.config_session_id, "重复提交")

        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 1)
        self.assertEqual(ledger.config_sessions[session.config_session_id].status, "manual_review")
        self.assertFalse(ledger.config_sessions[session.config_session_id].deducted)
        with self.assertRaisesRegex(ValueError, "人工复核"):
            ledger.complete_config_session(session.config_session_id, real_task_verified=True)
        with self.assertRaisesRegex(ValueError, "人工复核"):
            ledger.fail_config_session(session.config_session_id, "自动失败重试")

    def test_manual_review_session_blocks_new_reservation_until_staff_resolves_it(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "buyer-1", [], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")
        entitlement.remaining_uses = 2
        session = ledger.reserve_config_session("reserve-1", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-1")
        ledger.mark_config_session_manual_review(session.config_session_id, "等待客服确认真实任务")

        with self.assertRaisesRegex(ValueError, "人工复核"):
            ledger.reserve_config_session("reserve-2", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-2")

        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 2)

    def test_device_limit_blocks_new_device_without_deducting_entitlement(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "buyer-1", [], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")
        entitlement.remaining_uses = 2
        entitlement.device_limit = 1
        first = ledger.reserve_config_session("reserve-1", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-1")
        ledger.complete_config_session(first.config_session_id, real_task_verified=True)

        with self.assertRaisesRegex(ValueError, "设备"):
            ledger.reserve_config_session("reserve-2", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-2", "PH-CFG-2")

        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 1)

    def test_config_session_allows_retry_after_failure_but_blocks_parallel_and_completed_retry(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "buyer-1", [], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")
        first = ledger.reserve_config_session("reserve-1", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-1")

        with self.assertRaisesRegex(ValueError, "活跃配置会话"):
            ledger.reserve_config_session("reserve-2", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-2")

        ledger.fail_config_session(first.config_session_id, "真实任务失败")
        retry = ledger.reserve_config_session("reserve-2", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-2")
        ledger.complete_config_session(retry.config_session_id, real_task_verified=True)

        self.assertNotEqual(first.config_session_id, retry.config_session_id)
        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].remaining_uses, 0)
        with self.assertRaisesRegex(ValueError, "权益不可用"):
            ledger.reserve_config_session("reserve-3", entitlement.entitlement_id, "buyer-1", "codex", "direct_api", "device-1", "PH-CFG-3")

    def test_order_reversal_recovers_entitlement_and_reverses_commissions_once(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "agent-1", ["agent-1"], "PH-CFG-1")
        entitlement = ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")
        ledger.reserve_config_session("reserve-1", entitlement.entitlement_id, "agent-1", "codex", "direct_api", "device-1", "PH-CFG-1")

        ledger.reverse_order(order.order_id, "客服按订单撤销")
        ledger.reverse_order(order.order_id, "客服按订单撤销")

        self.assertEqual(ledger.orders[order.order_id].status, "reversed")
        self.assertEqual(ledger.entitlements[entitlement.entitlement_id].status, "revoked")
        self.assertEqual(ledger.config_sessions["cfg-1"].status, "cancelled")
        self.assertEqual(len(ledger.commission_reversals), 1)
        with self.assertRaisesRegex(ValueError, "已取消"):
            ledger.complete_config_session("cfg-1", real_task_verified=True)

    def test_order_reversal_sends_withdrawn_commission_to_manual_review(self) -> None:
        ledger = CommercialLedgerContract()
        order = ledger.create_order("order-1", "prod-codex", "buyer-1", "agent-1", ["agent-1", "agent-2"], "PH-CFG-1")
        ledger.mark_paid_and_create_entitlement(order.order_id, "pay-1")
        ledger.commission_entries[0].status = "withdrawn"

        ledger.reverse_order(order.order_id, "客服按订单撤销")
        ledger.reverse_order(order.order_id, "客服按订单撤销")

        self.assertEqual(ledger.commission_entries[0].status, "manual_review")
        self.assertEqual(ledger.commission_entries[1].status, "reversed")
        self.assertEqual(len(ledger.commission_reversals), 1)

    def test_free_l1_agent_product_can_activate_directly_and_paid_levels_are_backend_configured(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product(
            product_id="agent-l1-free",
            level="L1",
            name="L1 免费推广代理",
            price_cents=0,
            currency="CNY",
            validity_days=365,
            requires_review=False,
            status="listed",
            intro_page_enabled=True,
        )
        ledger.configure_agent_product(
            product_id="agent-l2-paid",
            level="L2",
            name="L2 付费代理",
            price_cents=19900,
            currency="CNY",
            validity_days=365,
            requires_review=True,
            status="listed",
            intro_page_enabled=True,
        )

        free_profile = ledger.apply_agent("agent-free", "agent-l1-free")
        paid_profile = ledger.apply_agent("agent-paid", "agent-l2-paid")

        self.assertEqual(free_profile.level, "L1")
        self.assertEqual(free_profile.status, "active")
        self.assertTrue(free_profile.invite_code)
        self.assertEqual(paid_profile.level, "L2")
        self.assertEqual(paid_profile.status, "pending_review")

    def test_referral_binding_is_not_overwritten_by_new_invite_code(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product("agent-l1-free", "L1", "L1 免费代理", 0)
        first_agent = ledger.apply_agent("agent-first", "agent-l1-free")
        second_agent = ledger.apply_agent("agent-second", "agent-l1-free")

        first_binding = ledger.bind_referral("buyer-1", first_agent.invite_code)
        retry_binding = ledger.bind_referral("buyer-1", second_agent.invite_code)

        self.assertEqual(first_binding.direct_agent_user_id, "agent-first")
        self.assertEqual(retry_binding.direct_agent_user_id, "agent-first")
        self.assertEqual(len(ledger.referral_bindings), 1)

    def test_agent_chain_snapshot_uses_pure_five_level_relation(self) -> None:
        ledger = CommercialLedgerContract()
        for level in range(1, 6):
            product_id = f"agent-l{level}-free"
            ledger.configure_agent_product(product_id, f"L{level}", f"L{level} 免费代理", 0)
            ledger.apply_agent(f"agent-l{level}", product_id)

        ledger.bind_referral("agent-l2", ledger.agent_profiles["agent-l1"].invite_code)
        ledger.bind_referral("agent-l3", ledger.agent_profiles["agent-l2"].invite_code)
        ledger.bind_referral("agent-l4", ledger.agent_profiles["agent-l3"].invite_code)
        ledger.bind_referral("agent-l5", ledger.agent_profiles["agent-l4"].invite_code)
        ledger.bind_referral("buyer-1", ledger.agent_profiles["agent-l5"].invite_code)

        snapshot = ledger.build_agent_chain_snapshot("buyer-1", "usage-1")

        self.assertEqual(
            snapshot.chain,
            ["agent-l5", "agent-l4", "agent-l3", "agent-l2", "agent-l1"],
        )

    def test_commission_event_uses_level_depth_rules_and_source_idempotency(self) -> None:
        ledger = CommercialLedgerContract()
        for level in range(1, 6):
            product_id = f"agent-l{level}-free"
            ledger.configure_agent_product(product_id, f"L{level}", f"L{level} 免费代理", 0)
            ledger.apply_agent(f"agent-l{level}", product_id)
        ledger.bind_referral("agent-l2", ledger.agent_profiles["agent-l1"].invite_code)
        ledger.bind_referral("agent-l3", ledger.agent_profiles["agent-l2"].invite_code)
        ledger.bind_referral("agent-l4", ledger.agent_profiles["agent-l3"].invite_code)
        ledger.bind_referral("agent-l5", ledger.agent_profiles["agent-l4"].invite_code)
        ledger.bind_referral("buyer-1", ledger.agent_profiles["agent-l5"].invite_code)
        ledger.configure_commission_policy_rule("token_usage_settled", "L5", depth=1, rate_bps=1000)
        ledger.configure_commission_policy_rule("token_usage_settled", "L4", depth=2, rate_bps=800)
        ledger.configure_commission_policy_rule("token_usage_settled", "L1", depth=5, rate_bps=5000)

        event = ledger.record_commission_event(
            source_event_id="usage-1",
            event_type="token_usage_settled",
            buyer_user_id="buyer-1",
            amount_cents=10000,
        )
        retry = ledger.record_commission_event(
            source_event_id="usage-1",
            event_type="token_usage_settled",
            buyer_user_id="buyer-1",
            amount_cents=10000,
        )

        self.assertEqual(event.event_id, retry.event_id)
        self.assertEqual(len(ledger.commission_entries), 2)
        self.assertEqual(
            [(entry.agent_user_id, entry.depth, entry.commission_cents) for entry in ledger.commission_entries],
            [("agent-l5", 1, 1000), ("agent-l4", 2, 800)],
        )
        with self.assertRaisesRegex(ValueError, "事件幂等"):
            ledger.record_commission_event("usage-1", "token_usage_settled", "buyer-1", 20000)

    def test_commission_event_without_active_policy_records_event_without_ledger_entries(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product("agent-l1-free", "L1", "L1 免费代理", 0)
        profile = ledger.apply_agent("agent-1", "agent-l1-free")
        ledger.bind_referral("buyer-1", profile.invite_code)

        event = ledger.record_commission_event(
            source_event_id="usage-no-policy-1",
            event_type="token_usage_settled",
            buyer_user_id="buyer-1",
            amount_cents=5000,
        )

        self.assertEqual(event.status, "recorded")
        self.assertEqual(len(ledger.commission_events), 1)
        self.assertEqual(len(ledger.commission_entries), 0)

    def test_three_commission_event_types_release_after_t7_and_reverse_with_manual_review(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product("agent-l1-free", "L1", "L1 免费代理", 0)
        profile = ledger.apply_agent("agent-1", "agent-l1-free")
        ledger.bind_referral("buyer-1", profile.invite_code)
        ledger.configure_commission_policy_rule("token_usage_settled", "L1", depth=1, rate_bps=1000)
        ledger.configure_commission_policy_rule("activation_paid", "L1", depth=1, rate_bps=2000)
        ledger.configure_commission_policy_rule("agent_install_delivered", "L1", depth=1, rate_bps=3000)

        ledger.record_commission_event("usage-1", "token_usage_settled", "buyer-1", 10000)
        ledger.record_commission_event("activation-1", "activation_paid", "buyer-1", 10000)
        ledger.record_commission_event("install-1", "agent_install_delivered", "buyer-1", 10000)
        ledger.release_commissions_after_days(6)

        self.assertEqual([entry.status for entry in ledger.commission_entries], ["pending", "pending", "pending"])

        ledger.release_commissions_after_days(7)
        self.assertEqual([entry.status for entry in ledger.commission_entries], ["available", "available", "available"])
        self.assertEqual(sum(entry.commission_cents for entry in ledger.commission_entries), 6000)

        ledger.commission_entries[0].status = "settled"
        ledger.reverse_commission_event("usage-1", "客户退款")
        ledger.reverse_commission_event("activation-1", "客户退款")

        self.assertEqual(ledger.commission_entries[0].status, "manual_review")
        self.assertEqual(ledger.commission_entries[1].status, "reversed")
        self.assertEqual(ledger.commission_entries[2].status, "available")

    def test_api_key_owner_verification_blocks_agent_owned_key_for_buyer_delivery(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.register_api_key_owner("sk-buyer", "buyer-1")
        ledger.register_api_key_owner("sk-agent", "agent-1")

        buyer_result = ledger.verify_api_key_owner("sk-buyer", target_buyer_user_id="buyer-1", operator_user_id="agent-1")

        self.assertEqual(buyer_result["owner_user_id"], "buyer-1")
        with self.assertRaisesRegex(ValueError, "目标买家"):
            ledger.verify_api_key_owner("sk-agent", target_buyer_user_id="buyer-1", operator_user_id="agent-1")
        with self.assertRaisesRegex(ValueError, "归属"):
            ledger.verify_api_key_owner("sk-unknown", target_buyer_user_id="buyer-1", operator_user_id="agent-1")

    def test_agent_center_snapshot_is_backend_controlled(self) -> None:
        ledger = CommercialLedgerContract()

        closed = ledger.agent_center_snapshot()
        ledger.configure_agent_center(
            enabled=True,
            current_level="L2",
            upgrade_label="申请升级 L3",
            invite_url="https://aitokenapi.cc/invite/abc",
            join_page_url="https://aitokenapi.cc/agent/join",
            backend_url="https://aitokenapi.cc/agent/center",
            rules_url="https://aitokenapi.cc/agent/rules",
            summary={
                "downstream_count": 12,
                "token_commission_cents": 1234,
                "activation_commission_cents": 2000,
                "agent_install_commission_cents": 3000,
                "available_settlement_cents": 4000,
                "pending_settlement_cents": 5000,
                "frozen_cents": 600,
            },
            benefits=["可绑定买家"],
            boundaries=["收益以后台结算为准"],
            commission_ratio="50%",
        )
        opened = ledger.agent_center_snapshot()

        self.assertFalse(closed["enabled"])
        self.assertTrue(opened["enabled"])
        self.assertEqual(opened["current_level"], "L2")
        self.assertEqual(opened["join_page_url"], "https://aitokenapi.cc/agent/join")
        self.assertEqual(opened["backend_url"], "https://aitokenapi.cc/agent/center")
        self.assertEqual(opened["rules_url"], "https://aitokenapi.cc/agent/rules")
        self.assertEqual(opened["summary"]["downstream_count"], 12)
        self.assertNotIn("commission_ratio", opened)

    def test_public_agent_offering_uses_marketing_content_and_only_exposes_open_products(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product("agent-l1-free", "L1", "L1 免费推广代理", 0)
        ledger.configure_agent_product("agent-l2-hidden", "L2", "L2 内测代理", 19900, status="hidden")
        ledger.configure_agent_product(
            "agent-l3-no-intro",
            "L3",
            "L3 暂不招商",
            39900,
            intro_page_enabled=False,
        )
        ledger.configure_agent_marketing_content(
            page_title="胖虎AI代理招募",
            hero_title="把 Agent 安装和 token 消费变成长期生意",
            selling_points=["卖工具部署服务", "赚 token、激活和安装三类佣金"],
            faq=[{"question": "多久结算？", "answer": "默认 T+7 后可申请结算。"}],
            materials=[{"title": "朋友圈话术", "url": "https://aitokenapi.cc/agent/materials/moments"}],
        )

        offering = ledger.public_agent_offering()

        self.assertEqual(offering["marketing_content"]["page_title"], "胖虎AI代理招募")
        self.assertEqual([product["id"] for product in offering["products"]], ["agent-l1-free"])
        self.assertEqual(offering["products"][0]["price_cents"], 0)
        self.assertEqual(offering["available_levels"], ["L1"])
        self.assertIn("T+7", offering["marketing_content"]["faq"][0]["answer"])

    def test_agent_application_review_activates_paid_or_review_required_profile(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product(
            product_id="agent-l2-review",
            level="L2",
            name="L2 审核代理",
            price_cents=19900,
            requires_review=True,
        )

        profile = ledger.apply_agent("agent-review", "agent-l2-review")
        application = ledger.agent_applications[-1]

        self.assertEqual(profile.status, "pending_review")
        self.assertEqual(application.status, "pending_review")

        approved = ledger.review_agent_application(
            application_id=application.application_id,
            decision="approve",
            reviewer_user_id="admin-1",
            reason="已确认代理费用和资料",
        )

        self.assertEqual(approved.status, "approved")
        self.assertEqual(ledger.agent_profiles["agent-review"].status, "active")
        self.assertTrue(ledger.agent_profiles["agent-review"].activated_at)

    def test_settlement_request_only_uses_t7_available_commissions_and_admin_marks_settled(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product("agent-l1-free", "L1", "L1 免费代理", 0)
        profile = ledger.apply_agent("agent-1", "agent-l1-free")
        ledger.bind_referral("buyer-1", profile.invite_code)
        ledger.configure_commission_policy_rule("token_usage_settled", "L1", depth=1, rate_bps=1000)
        ledger.record_commission_event("usage-1", "token_usage_settled", "buyer-1", 10000)

        with self.assertRaisesRegex(ValueError, "可结算"):
            ledger.create_settlement_request("agent-1", requested_cents=1000)

        ledger.release_commissions_after_days(7)
        request = ledger.create_settlement_request("agent-1", requested_cents=1000)

        self.assertEqual(request.status, "pending")
        self.assertEqual(request.requested_cents, 1000)
        self.assertEqual([entry.status for entry in ledger.commission_entries], ["settlement_requested"])

        settled = ledger.mark_settlement_paid(request.settlement_id, admin_user_id="admin-1")

        self.assertEqual(settled.status, "settled")
        self.assertEqual([entry.status for entry in ledger.commission_entries], ["settled"])

    def test_admin_ledger_freeze_release_and_reverse_are_state_safe(self) -> None:
        ledger = CommercialLedgerContract()
        ledger.configure_agent_product("agent-l1-free", "L1", "L1 免费代理", 0)
        profile = ledger.apply_agent("agent-1", "agent-l1-free")
        ledger.bind_referral("buyer-1", profile.invite_code)
        ledger.configure_commission_policy_rule("agent_install_delivered", "L1", depth=1, rate_bps=3000)
        ledger.record_commission_event("install-1", "agent_install_delivered", "buyer-1", 10000)
        ledger.release_commissions_after_days(7)

        commission_id = ledger.commission_entries[0].commission_id
        ledger.admin_update_commission_entry(commission_id, "freeze", "疑似重复回调")
        self.assertEqual(ledger.commission_entries[0].status, "frozen")
        ledger.admin_update_commission_entry(commission_id, "release", "风控解除")
        self.assertEqual(ledger.commission_entries[0].status, "available")
        ledger.admin_update_commission_entry(commission_id, "reverse", "安装失败冲正")

        self.assertEqual(ledger.commission_entries[0].status, "reversed")

        ledger.commission_entries[0].status = "settled"
        ledger.admin_update_commission_entry(commission_id, "reverse", "已结算后退款")

        self.assertEqual(ledger.commission_entries[0].status, "manual_review")


if __name__ == "__main__":
    unittest.main()

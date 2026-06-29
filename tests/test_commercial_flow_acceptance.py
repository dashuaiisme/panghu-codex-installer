import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CommercialFlowAcceptanceTests(unittest.TestCase):
    def test_offline_acceptance_script_covers_order_payment_entitlement_sessions_and_reversal(self) -> None:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "commercial_flow_acceptance.py"),
                "--json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["offline_only"])
        matrix = report["backend_closeout_matrix"]
        self.assertEqual(
            [item["status"] for item in matrix["local_closed"]],
            ["closed_local", "closed_local", "closed_local", "closed_local"],
        )
        self.assertIn("真实数据库和服务端账本", [item["item"] for item in matrix["real_service_pending"]])
        self.assertIn("真实支付回调和权益创建", [item["item"] for item in matrix["real_service_pending"]])
        self.assertIn("真实 Agent Runtime Adapter 和平台回调", [item["item"] for item in matrix["real_service_pending"]])
        self.assertIn("真实 agent_center 服务端快照", [item["item"] for item in matrix["real_service_pending"]])
        self.assertIn("客户真实账号、真实设备和端到端验收", [item["item"] for item in matrix["real_service_pending"]])
        self.assertEqual(matrix["release_deferred"][0]["status"], "deferred_by_user_scope")
        self.assertIn("真实平台回调未接入", "\n".join(report["blocking_gaps"]))
        self.assertEqual(report["runtime_adapter_status"], "mock_guarded")
        self.assertEqual(report["callback_status"], "mock_guarded")
        self.assertEqual(report["ledger_status"], "offline_guarded")
        self.assertEqual(report["agent_center_status"], "offline_guarded")
        self.assertIn("Agent Center 真实服务端快照未接入", "\n".join(report["blocking_gaps"]))
        self.assertEqual(report["order_entitlement_status"], "offline_guarded")
        self.assertIn("订单/权益/配置会话仅为本地离线状态报告", "\n".join(report["blocking_gaps"]))
        self.assertEqual(report["order"]["status"], "reversed")
        self.assertEqual(report["order_status_report"]["order_status_report"], "local_reversed")
        self.assertEqual(report["order_status_report"]["entitlement_status_report"], "revoked")
        self.assertIn("订单已撤销", "\n".join(report["order_status_report"]["blocking_gaps"]))
        self.assertTrue(report["idempotency"]["order_payload_drift_blocked"])
        self.assertTrue(report["idempotency"]["payment_payload_drift_blocked"])
        self.assertTrue(report["idempotency"]["trial_payload_drift_blocked"])
        self.assertTrue(report["idempotency"]["trial_duplicate_claim_blocked"])
        self.assertTrue(report["idempotency"]["trial_cross_agent_claim_blocked"])
        self.assertTrue(report["idempotency"]["trial_dual_state_blocked"])
        self.assertTrue(report["idempotency"]["config_session_payload_drift_blocked"])
        self.assertEqual(report["entitlement"]["source"], "paid")
        self.assertEqual(report["entitlement"]["trial_source"], "trial")
        self.assertEqual(report["entitlement"]["paid_remaining_after_trial_completed"], 1)
        self.assertEqual(report["entitlement"]["trial_remaining_after_completed_session"], 0)
        self.assertEqual(report["entitlement"]["remaining_uses_after_failed_session"], 1)
        self.assertEqual(report["entitlement"]["remaining_uses_after_completed_session"], 0)
        self.assertEqual(report["entitlement"]["status_after_reversal"], "revoked")
        self.assertEqual(report["config_sessions"]["failed_session_status"], "failed")
        self.assertIn("failed", report["config_sessions"]["session_status_reports"].values())
        self.assertIn("manual_review", report["config_sessions"]["session_status_reports"].values())
        self.assertIn("completed", report["config_sessions"]["session_status_reports"].values())
        self.assertEqual(report["config_sessions"]["completed_session_status"], "completed")
        self.assertEqual(report["config_sessions"]["manual_review_session_status"], "manual_review")
        self.assertFalse(report["config_sessions"]["manual_review_session_deducted"])
        self.assertTrue(report["config_sessions"]["manual_review_blocks_new_reservation"])
        self.assertEqual(report["entitlement"]["remaining_uses_after_manual_review_session"], 1)
        self.assertTrue(report["device_policy"]["new_device_blocked"])
        self.assertEqual(report["device_policy"]["remaining_uses_after_device_block"], 1)
        self.assertTrue(report["rollout_gates"]["old_client_blocked"])
        self.assertTrue(report["rollout_gates"]["non_gray_buyer_blocked"])
        self.assertTrue(report["rollout_gates"]["gray_buyer_allowed"])
        self.assertEqual(report["commissions"]["created_count"], 7)
        self.assertEqual(report["commissions"]["reversed_count"], 6)
        self.assertEqual(report["commissions"]["manual_review_count"], 1)
        self.assertEqual(report["commissions"]["tool_order_paid_count"], 1)
        self.assertEqual(report["commissions"]["tool_order_paid_cents"], 1000)
        self.assertEqual(report["reversal"]["count"], 2)
        self.assertTrue(report["api_key_owner"]["buyer_key_verified"])
        self.assertTrue(report["api_key_owner"]["agent_key_blocked"])
        self.assertTrue(report["client_agent_dispatch"]["all_authorized"])
        self.assertTrue(report["client_agent_dispatch"]["all_idempotent"])
        self.assertTrue(report["client_agent_dispatch"]["admin_action_blocked"])
        self.assertEqual(
            set(report["client_agent_dispatch"]["actions"]),
            {"agent_public_offering", "agent_apply", "referral_bind", "agent_settlement"},
        )
        self.assertTrue(report["agent_center"]["enabled"])
        self.assertEqual(report["agent_center"]["snapshot_status"], "active")
        self.assertEqual(report["agent_center"]["settlement_status"], "available")
        self.assertEqual(report["agent_center"]["last_synced_at"], "offline://agent-center/snapshot")
        self.assertEqual(report["agent_center"]["missing_fields"], [])
        self.assertEqual(report["agent_center"]["blocking_gaps"], [])
        self.assertNotIn("commission_ratio", report["agent_center"])
        self.assertTrue(report["communication_software_link"]["unpaid_session_blocked"])
        self.assertTrue(report["communication_software_link"]["missing_evidence_url_blocked"])
        self.assertTrue(report["communication_software_link"]["gemini_agy_order_blocked"])
        self.assertTrue(report["communication_software_link"]["runtime_adapter_required"])
        self.assertTrue(report["communication_software_link"]["runtime_adapter_missing_blocked"])
        self.assertEqual(report["communication_software_link"]["runtime_adapter_status"], "success")
        self.assertEqual(report["communication_software_link"]["callback_replay_status"], "replayed")
        self.assertEqual(report["communication_software_link"]["paid_charge_status"], "paid")
        self.assertEqual(report["communication_software_link"]["connected_session_status"], "connected")
        self.assertEqual(report["communication_software_link"]["callback_status"], "accepted")
        self.assertEqual(report["communication_software_link"]["final_order_status"], "delivered")
        self.assertEqual(report["communication_software_link"]["final_charge_status"], "paid")
        self.assertEqual(report["communication_software_link"]["service_ledger_service_type"], "communication_software_link")
        self.assertEqual(report["communication_software_link"]["service_ledger_event_type"], "communication_software_link_delivered")
        self.assertEqual(report["communication_software_link"]["disabled_session_status"], "disabled")
        self.assertEqual(report["communication_software_link"]["disabled_order_status"], "cancelled")
        self.assertTrue(report["communication_software_link"]["disabled_blocks_fail"])
        self.assertTrue(report["communication_software_link"]["disabled_blocks_pause"])
        self.assertEqual(report["communication_software_link"]["real_service_status"], "pending_authorization")
        self.assertFalse(report["communication_software_link"]["client_may_claim_delivery_complete"])
        self.assertIn("真实平台回调", report["communication_software_link"]["delivery_boundary"])
        self.assertEqual(report["agent_business"]["free_l1_status"], "active")
        self.assertEqual(report["agent_business"]["paid_l2_status"], "pending_review")
        self.assertEqual(report["agent_business"]["referral_owner_after_rebind"], "agent-l5")
        self.assertEqual(
            report["agent_business"]["chain_snapshot"],
            ["agent-l5", "agent-l4", "agent-l3", "agent-l2", "agent-l1"],
        )
        self.assertEqual(report["agent_business"]["event_idempotent"], True)
        self.assertEqual(report["agent_business"]["entries_after_no_policy_event"], 0)
        self.assertEqual(report["agent_business"]["pending_count_after_6_days"], 3)
        self.assertEqual(report["agent_business"]["available_count_after_7_days"], 3)
        self.assertEqual(report["agent_business"]["manual_review_after_reverse"], 1)
        self.assertEqual(report["agent_business"]["reversed_after_reverse"], 1)
        self.assertEqual(report["agent_business"]["offering_levels"], ["L1", "L2", "L3", "L4", "L5"])
        self.assertTrue(report["agent_business"]["marketing_has_join_copy"])
        self.assertEqual(report["agent_business"]["paid_l2_review_after_approve"], "approved")
        self.assertEqual(report["agent_business"]["paid_l2_profile_after_approve"], "active")
        self.assertEqual(report["agent_business"]["settlement_status_after_request"], "pending")
        self.assertEqual(report["agent_business"]["settlement_status_after_admin_pay"], "settled")
        self.assertEqual(report["agent_business"]["ledger_status_after_freeze_release_reverse"], "reversed")


if __name__ == "__main__":
    unittest.main()

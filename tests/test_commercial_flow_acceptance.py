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
        self.assertEqual(report["order"]["status"], "reversed")
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
        self.assertEqual(report["reversal"]["count"], 2)
        self.assertTrue(report["api_key_owner"]["buyer_key_verified"])
        self.assertTrue(report["api_key_owner"]["agent_key_blocked"])
        self.assertTrue(report["agent_center"]["enabled"])
        self.assertNotIn("commission_ratio", report["agent_center"])
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

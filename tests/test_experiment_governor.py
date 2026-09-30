"""Tier-1 tests: experiment governor (read-only guard + A/B/C/D typing)."""
import unittest
from datetime import datetime, timezone

import experiment_governor as gov


OPEN = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
CLOSED = datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc)


class TestGovernor(unittest.TestCase):
    def test_window_open_before_close(self):
        st = gov.protected_window_status(now=OPEN)
        self.assertEqual(st["EXP-SUB-001"]["state"], "PROTECTED")

    def test_window_closed_after_close(self):
        st = gov.protected_window_status(now=CLOSED)
        self.assertEqual(st["EXP-SUB-001"]["state"], "CLOSED")

    def test_mutation_blocked_inside_window(self):
        with self.assertRaises(gov.ExperimentProtectedError):
            gov.assert_safe_to_mutate("EXP-SUB-001", "re-poll", now=OPEN)

    def test_mutation_allowed_after_close(self):
        self.assertTrue(
            gov.assert_safe_to_mutate("EXP-SUB-001", "reconcile", now=CLOSED)["ok"])

    def test_unrelated_target_passes(self):
        self.assertTrue(
            gov.assert_safe_to_mutate("server.js", "read", now=OPEN)["ok"])

    def test_live_source_is_file_not_constant(self):
        # The registry must prefer the live observation file when readable.
        rec = gov.protected_experiments()["EXP-SUB-001"]
        self.assertIn("nostr_sub_observation", rec["source"])

    def test_action_typing(self):
        self.assertEqual(gov.classify_action("health_check"), "B_AUTOMATABLE")
        self.assertEqual(gov.classify_action("publish"), "A_FOUNDER_GATE")
        self.assertEqual(gov.classify_action("paddle_onboarding"), "C_EXTERNAL_APPROVAL")
        self.assertEqual(gov.classify_action("evidence_rewrite"), "D_FORBIDDEN")
        self.assertEqual(gov.classify_action("something_new"), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

"""Tier-1 tests: resource governor SKIP/PROCEED rules."""
import unittest

import resource_governor as rg


class TestGovernor(unittest.TestCase):
    def test_low_value_skips(self):
        self.assertEqual(rg.govern("low")["decision"], "SKIP")

    def test_repeat_skips(self):
        self.assertEqual(
            rg.govern("high", repeated_without_change=True)["decision"], "SKIP")

    def test_unchanged_skips(self):
        self.assertEqual(
            rg.govern("high", state_changed=False)["decision"], "SKIP")

    def test_early_recheck_skips(self):
        self.assertEqual(
            rg.govern("high", blocker_recheck_due=False)["decision"], "SKIP")

    def test_good_run_proceeds(self):
        r = rg.govern("high")
        self.assertEqual(r["decision"], "PROCEED")


if __name__ == "__main__":
    unittest.main()

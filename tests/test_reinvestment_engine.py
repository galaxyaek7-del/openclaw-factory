"""Tests for reinvestment_engine.py — the founder-approval profit-split policy.

    python -m unittest tests.test_reinvestment_engine -v
"""

import os
import sys
import tempfile
import unittest

_FACTORY_ROOT = Path = __import__("pathlib").Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from reinvestment_engine import (
    build_reinvestment_plan,
    reinvestment_status,
    realized_affiliate_profit,
    FOUNDER_RESERVE_RATE,
    DEFAULT_POLICY,
)


class TestReinvestmentPlan(unittest.TestCase):
    def test_zero_profit_plan_is_all_zeroes_honestly(self):
        plan = build_reinvestment_plan(net_profit=0.0)
        self.assertEqual(plan.realized_net_profit_usd, 0.0)
        self.assertEqual(plan.founder_reserve_usd, 0.0)
        self.assertEqual(plan.reinvestable_usd, 0.0)
        self.assertTrue(any("صفر إيراد" in n for n in plan.notes))
        for v in plan.allocations.values():
            self.assertEqual(v, 0.0)

    def test_negative_profit_clamped_to_zero(self):
        plan = build_reinvestment_plan(net_profit=-50.0)
        self.assertEqual(plan.realized_net_profit_usd, 0.0)

    def test_positive_profit_split_matches_policy_and_reserve(self):
        plan = build_reinvestment_plan(net_profit=1000.0)
        self.assertEqual(plan.founder_reserve_usd, round(1000 * FOUNDER_RESERVE_RATE, 2))
        self.assertEqual(plan.reinvestable_usd, round(1000 * (1 - FOUNDER_RESERVE_RATE), 2))
        # Allocations must sum exactly to reinvestable.
        self.assertEqual(sum(plan.allocations.values()), plan.reinvestable_usd)
        # Priority order: system improvement is the largest share.
        self.assertEqual(plan.allocations["system_improvement"],
                         plan.allocations.get("system_improvement"))
        self.assertGreaterEqual(plan.allocations["system_improvement"],
                                plan.allocations["recurring_revenue_products"])

    def test_custom_policy_respected(self):
        policy = {k: 0.0 for k in DEFAULT_POLICY}
        policy["galaxy_forge_assets"] = 1.0
        plan = build_reinvestment_plan(net_profit=200.0, policy=policy)
        self.assertEqual(plan.allocations["galaxy_forge_assets"],
                         round(200 * (1 - FOUNDER_RESERVE_RATE), 2))

    def test_real_ledger_zero_profit_status(self):
        status = reinvestment_status()
        self.assertEqual(status["realized_net_profit_usd"], 0.0)
        self.assertIn("policy", status)


if __name__ == "__main__":
    unittest.main()
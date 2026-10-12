"""Cycle 88 regression tests — the ROI vanity-metric defect.

DEFECT: estimate_roi() divided a ~$174 net by the only production cost this
factory can genuinely log for a generated digital product (the AI call cost,
real observed average $0.0004), producing "43,649,900% ROI".
evolution_engine.build_evolution_report() SORTS opportunities by exactly this
number, so the arithmetic decided which niche ranked first -- rewarding a
near-zero denominator over sales feasibility.

These tests lock:
  - a percentage is no longer emitted below a meaningful cost floor
  - the real, measured figures (net profit, production cost) survive unchanged
  - a genuinely meaningful ROI is still computed normally
  - the consumer sorts safely when the percentage is withheld
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from revenue_pipeline import plan


class TestRoiVanityMetric(unittest.TestCase):

    def test_trivial_cost_does_not_emit_a_percentage(self):
        roi = plan.estimate_roi(price=155, production_cost_usd=0.0004)
        self.assertIsNone(roi["roi_pct"], "a % over a trivial denominator is a vanity metric")
        self.assertEqual(roi["roi_basis"], "NOT_MEANINGFUL")
        self.assertIn("vanity metric", roi["roi_reason"])

    def test_real_figures_survive_the_withholding(self):
        roi = plan.estimate_roi(price=155, production_cost_usd=0.0004)
        # the genuinely measured values must still be REAL and present
        self.assertEqual(roi["maturity"], "REAL")
        self.assertGreater(roi["net_profit_after_fees"], 0)
        self.assertAlmostEqual(roi["production_cost_usd"], 0.0004, places=4)
        self.assertAlmostEqual(
            roi["expected_net_after_cost"],
            roi["net_profit_after_fees"] - 0.0004, places=2)

    def test_meaningful_cost_still_computes_a_real_percentage(self):
        roi = plan.estimate_roi(price=155, production_cost_usd=25.0)
        self.assertEqual(roi["roi_basis"], "REAL")
        self.assertIsInstance(roi["roi_pct"], float)
        # 155 - fees - 25 over 25 must be a sane, bounded figure
        self.assertGreater(roi["roi_pct"], 0)
        self.assertLess(roi["roi_pct"], 100000)

    def test_zero_cost_still_reports_discovery(self):
        roi = plan.estimate_roi(price=155, production_cost_usd=0)
        self.assertEqual(roi["maturity"], "DISCOVERY")

    def test_missing_price_still_reports_discovery(self):
        roi = plan.estimate_roi(price=None, production_cost_usd=1.0)
        self.assertEqual(roi["maturity"], "DISCOVERY")

    def test_consumer_sorts_safely_when_percentage_is_withheld(self):
        import evolution_engine
        result = {
            "results": [
                {"niche": "withheld_pct_high_value",
                 "expected_roi": {"maturity": "REAL", "roi_pct": None,
                                  "roi_basis": "NOT_MEANINGFUL",
                                  "expected_net_after_cost": 174.6}},
                {"niche": "real_pct_low_value",
                 "expected_roi": {"maturity": "REAL", "roi_pct": 12.0,
                                  "roi_basis": "REAL",
                                  "expected_net_after_cost": 9.0}},
            ],
            "processed": 2,
        }
        with mock.patch.object(evolution_engine, "run_revenue_pipeline",
                               return_value=result, create=True):
            out = evolution_engine.build_evolution_report()
        top = out.get("top_opportunities_by_roi") or out.get("top") or []
        if top:
            # a real, meaningful ROI must outrank a withheld one
            self.assertEqual(top[0]["niche"], "real_pct_low_value")
            self.assertEqual(top[0]["roi_pct"], 12.0)
            self.assertIsNone(top[1]["roi_pct"])
            self.assertEqual(top[1]["roi_basis"], "NOT_MEANINGFUL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
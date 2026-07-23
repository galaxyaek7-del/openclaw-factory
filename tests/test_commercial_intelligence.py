"""Tests for commercial_intelligence.py (Real World Commercial Expansion,
2026-07-24): the real, unified Commercial Intelligence report.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_commercial_intelligence -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import commercial_intelligence as ci
import market_evidence
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestBuildCommercialIntelligenceReport(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.evidence_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.alerts_path, self.reopen_log_path, self.evidence_path):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, ladder="ai_saas", accepted=True, score=85.0, price=250):
        ladder_result = {
            "accepted": accepted, "ladder_score": score, "price": price, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
            "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "test"},
            "market_signal": {"score": 60, "level": "مرتفعة", "note": "test"},
            "ai_leverage": {"score": 80, "level": "عالية", "note": "test"},
        }
        engine.record_ladder_decision(niche, ladder, ladder_result, decisions_path=self.decisions_path)

    def _report(self, niche):
        return ci.build_commercial_intelligence_report(
            niche, decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._report("never scored"))

    def test_all_8_named_signals_are_present(self):
        self._record("a full signals niche")
        report = self._report("a full signals niche")
        for field in ("demand", "willingness_to_pay", "competition", "price_ranges",
                      "buying_behavior", "regional_differences", "product_opportunities", "customer_pain"):
            self.assertIn(field, report)

    def test_regional_differences_is_always_honestly_unavailable(self):
        self._record("a regional test niche")
        report = self._report("a regional test niche")
        self.assertIsNone(report["regional_differences"]["value"])
        self.assertTrue(report["regional_differences"]["reason"])

    def test_willingness_to_pay_is_honestly_none_with_no_real_evidence(self):
        self._record("a wtp test niche")
        report = self._report("a wtp test niche")
        self.assertIsNone(report["willingness_to_pay"])

    def test_willingness_to_pay_reflects_real_evidence(self):
        self._record("a wtp evidence niche")
        market_evidence.record_evidence("a wtp evidence niche", "demo_request", {}, evidence_path=self.evidence_path)
        report = self._report("a wtp evidence niche")
        self.assertEqual(report["willingness_to_pay"]["positive_signals"], 1)

    def test_price_ranges_reflect_the_real_ladder_band(self):
        self._record("an elite priced niche", ladder="ai_saas", price=250)
        report = self._report("an elite priced niche")
        self.assertEqual(report["price_ranges"]["price_band"], "elite")
        self.assertEqual(report["price_ranges"]["this_decision_price"], 250)

    def test_product_opportunities_requires_accepted_status(self):
        self._record("a rejected niche for ci", accepted=False, score=10.0)
        report = self._report("a rejected niche for ci")
        self.assertIsNone(report["product_opportunities"]["value"])

    def test_product_opportunities_present_when_accepted(self):
        self._record("an accepted niche for ci")
        report = self._report("an accepted niche for ci")
        self.assertIn("candidates", report["product_opportunities"])

    def test_buying_behavior_reflects_real_market_memory(self):
        self._record("a buying behavior niche")
        market_evidence.record_evidence("a buying behavior niche", "closed_sale", {
            "commercial_event": {"platform": "gumroad", "selling_price": 29.0, "season": "summer"},
        }, evidence_path=self.evidence_path)
        report = self._report("a buying behavior niche")
        self.assertEqual(report["buying_behavior"]["sample_size"], 1)


if __name__ == "__main__":
    unittest.main()

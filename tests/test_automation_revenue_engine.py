"""Tests for the AI Automation Revenue Engine (ADR-164, 2026-07-31):
automation_catalog.py / automation_intelligence.py / automation_
opportunity_scanner.py / automation_scoring.py / automation_dashboard.py.
Real scoring is a pure relabeling of profit_oracle.py::
ladder_opportunity_score() -- never a second scoring algorithm.

    python -m unittest tests.test_automation_revenue_engine -v
"""

import sys
import unittest
from unittest import mock
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import automation_catalog
import automation_intelligence
import automation_opportunity_scanner as scanner
import automation_scoring
import automation_dashboard


class TestAutomationCatalog(unittest.TestCase):
    def test_covers_all_15_named_categories(self):
        expected = {
            "AI workflow systems", "n8n templates", "Business process automation", "CRM automation",
            "Email automation", "Lead qualification", "Customer support assistants", "Internal AI copilots",
            "Reporting automation", "Knowledge assistants", "Document processing", "Invoice automation",
            "HR automation", "Sales automation", "Operations automation",
        }
        self.assertEqual(set(automation_catalog.AUTOMATION_CATEGORIES.keys()), expected)

    def test_every_category_maps_to_a_real_ladder(self):
        import profit_oracle
        for category, ladder in automation_catalog.AUTOMATION_CATEGORIES.items():
            self.assertIn(ladder, profit_oracle.RECURRING_REVENUE_BY_LADDER, category)

    def test_category_catalog_cites_real_constants(self):
        result = automation_catalog.category_catalog()
        self.assertEqual(len(result["categories"]), 15)
        for cat in result["categories"].values():
            self.assertIsNotNone(cat["real_recurring_revenue_potential"])


class TestIsB2B(unittest.TestCase):
    def test_b2b_ladder_is_true(self):
        is_b2b, reason = automation_intelligence.is_b2b("some niche", ladder="b2b_systems")
        self.assertTrue(is_b2b)

    def test_b2b_phrase_is_true(self):
        is_b2b, reason = automation_intelligence.is_b2b("automation tool for accounting firms", ladder="automation_tools")
        self.assertTrue(is_b2b)

    def test_no_b2b_signal_is_honestly_false(self):
        is_b2b, reason = automation_intelligence.is_b2b("printable monthly planner", ladder="kdp_books")
        self.assertFalse(is_b2b)


class TestAutomationPercentage(unittest.TestCase):
    def test_known_ladder_cites_real_constant(self):
        result = automation_intelligence.automation_percentage("automation_tools")
        self.assertEqual(result["value"], 90)

    def test_unknown_ladder_is_honestly_unknown(self):
        result = automation_intelligence.automation_percentage("not_a_real_ladder")
        self.assertEqual(result["value"], "UNKNOWN")


class TestScanCandidates(unittest.TestCase):
    def test_finds_real_seed_candidates(self):
        result = scanner.scan_candidates()
        self.assertIn("candidates", result)
        self.assertGreater(result["count"], 0)

    def test_honestly_returns_no_verified_opportunity_when_none_match(self):
        with mock.patch("market_hunter.SEED_CATEGORIES", [{"niche": "x", "ladder": "kdp_books"}]), \
             mock.patch("decision_engine.ranking.rank_all", return_value=[]):
            result = scanner.scan_candidates()
        self.assertEqual(result["answer"], scanner.NO_VERIFIED_OPPORTUNITY)

    def test_never_calls_run_hunt(self):
        # Regression test for the real, proactively-avoided bug class
        # ADR-162's addendum discovered the hard way: run_hunt() genuinely
        # writes real new decisions even with execute_production=False.
        # A passive scanner must never trigger it.
        with mock.patch("golden_hunter.hunt.run_hunt") as run_hunt:
            scanner.scan_candidates()
            run_hunt.assert_not_called()


class TestScoreOpportunity(unittest.TestCase):
    def test_relabels_real_ladder_score_fields(self):
        fake_result = {
            "niche": "n", "ladder": "automation_tools", "ladder_score": 80.0, "price": 197,
            "accepted": True, "reason": "accepted: all gates satisfied", "payment_evidence": [],
            "components": {"recurring_revenue_potential": 55, "automation_potential": 90},
            "risk": {"level": "low"}, "confidence": {"score": 70, "level": "medium"}, "defensibility": {},
        }
        with mock.patch("profit_oracle.ladder_opportunity_score", return_value=fake_result):
            result = automation_scoring.score_opportunity("n", "automation_tools")
        self.assertEqual(result["estimated_selling_price"]["answer"], 197)
        self.assertEqual(result["confidence_score"]["answer"]["score"], 70)
        self.assertTrue(result["accepted"])

    def test_never_fabricates_build_time(self):
        fake_result = {
            "niche": "n", "ladder": "automation_tools", "ladder_score": 80.0, "price": 197,
            "accepted": True, "reason": "x", "payment_evidence": [],
            "components": {"recurring_revenue_potential": 55, "automation_potential": 90},
            "risk": {}, "confidence": {}, "defensibility": {},
        }
        with mock.patch("profit_oracle.ladder_opportunity_score", return_value=fake_result):
            result = automation_scoring.score_opportunity("n", "automation_tools")
        self.assertEqual(result["estimated_build_time"]["value"], "UNKNOWN")

    def test_never_fabricates_monthly_revenue_dollar_amount(self):
        fake_result = {
            "niche": "n", "ladder": "automation_tools", "ladder_score": 80.0, "price": 197,
            "accepted": True, "reason": "x", "payment_evidence": [],
            "components": {"recurring_revenue_potential": 55, "automation_potential": 90},
            "risk": {}, "confidence": {}, "defensibility": {},
        }
        with mock.patch("profit_oracle.ladder_opportunity_score", return_value=fake_result):
            result = automation_scoring.score_opportunity("n", "automation_tools")
        self.assertEqual(result["potential_monthly_revenue_range"]["value"], "UNKNOWN")
        self.assertEqual(result["potential_monthly_revenue_range"]["real_recurring_revenue_potential_score"], 55)


class TestBuildAutomationDashboard(unittest.TestCase):
    def test_never_calls_run_hunt_or_distribute(self):
        with mock.patch("golden_hunter.hunt.run_hunt") as run_hunt, \
             mock.patch("distributor.distribute") as distribute:
            automation_dashboard.build_automation_dashboard()
            run_hunt.assert_not_called()
            distribute.assert_not_called()

    def test_honest_no_verified_opportunity_when_all_rejected(self):
        result = automation_dashboard.build_automation_dashboard()
        # Real current state: zero real payment evidence exists for any
        # seed candidate today -- honestly NO VERIFIED OPPORTUNITY FOUND.
        if "ranked_opportunities" not in result:
            self.assertEqual(result["answer"], scanner.NO_VERIFIED_OPPORTUNITY)

    def test_b2b_ranked_before_non_b2b_when_opportunities_exist(self):
        fake_scan = {"candidates": [
            {"niche": "n1", "ladder": "kdp_books", "source": "x"},
            {"niche": "n2", "ladder": "b2b_systems", "source": "x"},
        ], "count": 2}
        fake_score_b2c = {"niche": "n1", "accepted": True, "is_b2b": {"answer": False}, "ladder_score": 90}
        fake_score_b2b = {"niche": "n2", "accepted": True, "is_b2b": {"answer": True}, "ladder_score": 60}
        with mock.patch("automation_opportunity_scanner.scan_candidates", return_value=fake_scan), \
             mock.patch("automation_scoring.score_opportunity", side_effect=[fake_score_b2c, fake_score_b2b]):
            result = automation_dashboard.build_automation_dashboard()
        self.assertEqual(result["ranked_opportunities"][0]["niche"], "n2")


if __name__ == "__main__":
    unittest.main()

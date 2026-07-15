"""Tests for market_intelligence_engine.py (ADR-043).

Runs with stdlib unittest. All network-calling functions
(_query_github_issues, _query_hn_discussions, and competitor_discovery's
_query_hn/_query_github) are mocked throughout — this suite never depends
on live API availability.

    python -m unittest tests.test_market_intelligence_engine -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_intelligence_engine as mie


class TestCustomerPainIntelligence(unittest.TestCase):
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_no_real_results_gives_no_score_not_a_guess(self, mock_issues, mock_hn):
        mock_issues.return_value = ([], 0)
        mock_hn.return_value = ([], 0)
        result = mie.analyze_customer_pain("a totally obscure niche")
        self.assertIsNone(result["pain_score"])
        self.assertEqual(result["confidence"], "low")

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_real_pain_language_increases_score(self, mock_issues, mock_hn):
        mock_hn.return_value = ([], 0)
        mock_issues.return_value = (
            [{"title": "This is so frustrating, wish there was a tool", "body": "", "reactions": {"total_count": 10}, "comments": 5}],
            50,
        )
        result = mie.analyze_customer_pain("niche")
        self.assertGreater(result["real_evidence"]["pain_language_hits"], 0)
        self.assertIsNotNone(result["pain_score"])

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_willingness_to_pay_language_is_detected(self, mock_issues, mock_hn):
        mock_hn.return_value = ([], 0)
        mock_issues.return_value = (
            [{"title": "shut up and take my money for this", "body": "", "reactions": {"total_count": 1}, "comments": 1}],
            10,
        )
        result = mie.analyze_customer_pain("niche")
        self.assertGreater(result["real_evidence"]["willingness_to_pay_hits"], 0)

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_reddit_and_product_hunt_always_explicitly_unknown(self, mock_issues, mock_hn):
        mock_issues.return_value = ([], 0)
        mock_hn.return_value = ([], 0)
        result = mie.analyze_customer_pain("niche")
        self.assertIn("reddit", result["unknown_sources"])
        self.assertIn("product_hunt", result["unknown_sources"])

    @patch("market_intelligence_engine._http_get_json")
    def test_query_github_issues_never_raises_on_network_failure(self, mock_get):
        mock_get.side_effect = Exception("network down")
        items, total = mie._query_github_issues("x")
        self.assertEqual(items, [])
        self.assertEqual(total, 0)

    @patch("market_intelligence_engine._http_get_json")
    def test_query_hn_discussions_never_raises_on_network_failure(self, mock_get):
        mock_get.side_effect = Exception("network down")
        items, total = mie._query_hn_discussions("x")
        self.assertEqual(items, [])
        self.assertEqual(total, 0)


class TestDemandPatternClassification(unittest.TestCase):
    def test_seasonal_keyword_match_is_real_not_guessed(self):
        from datetime import datetime
        result = mie.classify_demand_pattern("back to school planner", now=datetime(2026, 8, 1))
        self.assertEqual(result["pattern"], "Seasonal")
        self.assertEqual(result["confidence"], "high")

    def test_no_seasonal_match_is_evergreen_with_honest_unknown_for_trend_direction(self):
        result = mie.classify_demand_pattern("a totally generic niche")
        self.assertIn("Evergreen", result["pattern"])
        self.assertIn("Unknown", result["pattern"])
        self.assertIn("Exploding/Declining", result["reason"])


class TestAiCeoDecision(unittest.TestCase):
    def _base(self, **overrides):
        base = {
            "risk": {"level": "low", "notes": []},
            "scores": {"competition": 70},
            "customer_pain": {"pain_score": 40, "confidence": "low"},
            "opportunity_gap": 50,
            "confidence": {"score": 60},
        }
        base.update(overrides)
        return base

    def test_high_risk_always_rejects_regardless_of_everything_else(self):
        analysis = self._base(risk={"level": "blocked", "notes": ["safety_filter flagged it"]}, opportunity_gap=95)
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn("safety_filter", result["evidence"][0])

    def test_low_overall_confidence_waits_instead_of_guessing(self):
        analysis = self._base(confidence={"score": 10}, customer_pain={"pain_score": 90, "confidence": "low"})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "WAIT")

    def test_pain_confidence_uses_the_same_numeric_scale_as_profit_oracle_confidence(self):
        """Regression test for a self-audit finding (2026-07-15): pain's
        'medium' confidence was previously mapped to 100 (the theoretical
        ceiling), which could single-handedly drag a genuinely low overall
        confidence above the WAIT gate. 'medium' must map to a moderate
        value (55, matching profit_oracle._score_confidence()'s own scale),
        not the maximum."""
        # confidence.score=10 (very low) + pain 'medium' must NOT be enough
        # to escape the < 40 WAIT gate on its own.
        analysis = self._base(confidence={"score": 10}, customer_pain={"pain_score": 50, "confidence": "medium"}, opportunity_gap=80)
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "WAIT", f"avg confidence should stay below 40, got: {result}")
        self.assertLess(result["confidence_gate"], 40)

    def test_high_opportunity_gap_and_real_pain_builds(self):
        analysis = self._base(opportunity_gap=80, customer_pain={"pain_score": 70, "confidence": "medium"}, confidence={"score": 70})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "BUILD")

    def test_very_high_competition_pivots(self):
        analysis = self._base(scores={"competition": 15}, confidence={"score": 70})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "PIVOT")

    def test_moderate_gap_improves(self):
        analysis = self._base(opportunity_gap=50, confidence={"score": 70})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "IMPROVE")

    def test_every_decision_cites_real_evidence_not_just_a_number(self):
        for analysis in [
            self._base(risk={"level": "blocked", "notes": ["x"]}),
            self._base(confidence={"score": 5}),
            self._base(opportunity_gap=80, customer_pain={"pain_score": 70, "confidence": "medium"}, confidence={"score": 70}),
        ]:
            result = mie.ai_ceo_decision(analysis)
            self.assertTrue(len(result["evidence"]) > 0)
            self.assertTrue(all(isinstance(e, str) and len(e) > 10 for e in result["evidence"]))

    def test_decision_is_always_one_of_the_five_valid_values(self):
        analysis = self._base()
        result = mie.ai_ceo_decision(analysis)
        self.assertIn(result["decision"], mie.DECISIONS)


class TestAnalyzeOpportunityOrchestration(unittest.TestCase):
    """The one integrated entry point — every network-calling function
    across both modules is mocked, so this never makes a real call.
    analysis_db_file is always redirected to a temp path — this must never
    write into the real data/market_intelligence_analyses.jsonl."""

    def setUp(self):
        import tempfile
        fd, self.db_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_empty_niche_degrades_honestly_never_crashes(self):
        """Regression test for a self-audit finding (2026-07-15):
        analyze_opportunity('') used to raise an uncaught ValueError from
        profit_oracle — every other function here degrades (None/Unknown)
        instead of crashing; this one must too."""
        for bad_niche in ('', '   ', None):
            result = mie.analyze_opportunity(bad_niche, analysis_db_file=self.db_path)
            self.assertIn("error", result)
            self.assertEqual(result["ai_ceo"]["decision"], "WAIT")

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_full_analysis_combines_every_real_engine(self, mock_issues, mock_hn_disc, mock_cd_hn, mock_cd_gh):
        mock_issues.return_value = ([], 0)
        mock_hn_disc.return_value = ([], 0)
        mock_cd_hn.return_value = []
        mock_cd_gh.return_value = []

        result = mie.analyze_opportunity("a test niche xyz", max_results=3, analysis_db_file=self.db_path)
        self.assertIn("scores", result)
        self.assertIn("risk", result)
        self.assertIn("confidence", result)
        self.assertIn("customer_pain", result)
        self.assertIn("demand_pattern", result)
        self.assertIn("competitors", result)
        self.assertIn("opportunity_gap", result)
        self.assertIn("pricing", result)
        self.assertIn("ai_ceo", result)
        self.assertIn(result["ai_ceo"]["decision"], mie.DECISIONS)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_pricing_never_invents_a_competitor_price(self, mock_issues, mock_hn_disc, mock_cd_hn, mock_cd_gh):
        mock_issues.return_value = ([], 0)
        mock_hn_disc.return_value = ([], 0)
        mock_cd_hn.return_value = []
        mock_cd_gh.return_value = []
        result = mie.analyze_opportunity("a test niche xyz", max_results=3, analysis_db_file=self.db_path)
        self.assertIn("Unknown", result["pricing"]["note"])


if __name__ == "__main__":
    unittest.main()

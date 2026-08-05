"""Tests for goos.py (Galaxy Opportunity Operating System, ADR-171,
2026-08-05): a consolidation/citation layer over already-real
evaluation systems, never a second, parallel decision engine, and
never a replacement for the real 65/100 weighted production floor.

    python -m unittest tests.test_goos -v
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import goos


_FAKE_SNAPSHOT = {
    "status": "REJECTED",
    "decided_at": "2026-08-01T00:00:00Z",
    "reasoning": ["low opportunity score"],
    "evaluation_snapshot": {
        "scores": {
            "market_demand": 54, "competition_favorability": 85,
            "profit_potential": 52, "automation_potential": 100,
            "long_term_value": 25,
        },
        "risk": {"level": "high"},
        "defensibility": {"score": 75, "level": "high"},
        "ai_leverage": {"score": 70, "level": "high"},
    },
}

_FAKE_ACCEPTED_SNAPSHOT = {**_FAKE_SNAPSHOT, "status": "ACCEPTED"}


class TestDimensionSources(unittest.TestCase):
    def test_all_20_named_dimensions_present(self):
        expected = {
            "real_customer_pain", "market_size_tam_sam_som", "willingness_to_pay",
            "competition_level", "difficulty_of_copying", "scalability",
            "recurring_revenue_potential", "automation_potential", "global_demand",
            "ai_leverage", "development_complexity", "time_to_mvp", "strategic_fit",
            "brand_fit", "long_term_asset_value", "profitability",
            "customer_lifetime_value", "risk_level", "legal_risk",
            "operational_complexity",
        }
        self.assertEqual(set(goos.DIMENSION_SOURCES.keys()), expected)

    def test_tam_sam_som_is_honestly_not_measurable(self):
        self.assertIn("no free real market-sizing data source", goos.DIMENSION_SOURCES["market_size_tam_sam_som"])


class TestEvaluateDimensions(unittest.TestCase):
    def test_never_evaluated_niche_is_honest(self):
        result = goos.evaluate_dimensions("a niche that has never been evaluated", snapshot=None)
        self.assertEqual(result["status"], "NOT_YET_EVALUATED")

    def test_real_snapshot_maps_correctly(self):
        result = goos.evaluate_dimensions("fake niche", snapshot=_FAKE_SNAPSHOT)
        self.assertEqual(result["status"], "EVALUATED")
        self.assertEqual(result["dimensions"]["real_customer_pain"]["value"], 54)
        self.assertEqual(result["dimensions"]["market_size_tam_sam_som"]["value"], goos.NOT_MEASURABLE)
        self.assertEqual(result["dimensions"]["risk_level"]["value"], "high")

    def test_missing_field_is_honestly_none_not_zero(self):
        result = goos.evaluate_dimensions("fake niche", snapshot=_FAKE_SNAPSHOT)
        self.assertIsNone(result["dimensions"]["development_complexity"]["value"])


class TestGoosScore(unittest.TestCase):
    def test_advisory_score_never_replaces_real_gate(self):
        result = goos.goos_score("fake niche", snapshot=_FAKE_SNAPSHOT)
        self.assertIn("never gates anything", result["real_production_gate"])

    def test_score_only_averages_real_numeric_dimensions(self):
        result = goos.goos_score("fake niche", snapshot=_FAKE_SNAPSHOT)
        self.assertEqual(result["dimensions_scored"], 5)  # market_demand, competition, automation, long_term_value, profit_potential
        self.assertIsInstance(result["score"], float)

    def test_meets_85_threshold_is_a_real_boolean_never_fabricated_true(self):
        result = goos.goos_score("fake niche", snapshot=_FAKE_SNAPSHOT)
        self.assertFalse(result["meets_advisory_85_threshold"])

    def test_never_evaluated_has_no_score(self):
        result = goos.goos_score("never evaluated niche xyz", snapshot=None)
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "NOT_YET_EVALUATED")


class TestBuildOpportunityIntelligenceReport(unittest.TestCase):
    def test_never_evaluated_niche_returns_honest_status(self):
        with mock.patch("goos._latest_snapshot", return_value=None):
            report = goos.build_opportunity_intelligence_report("nonexistent niche")
        self.assertEqual(report["status"], "NOT_YET_EVALUATED")

    def test_rejected_niche_has_no_post_acceptance_sections(self):
        with mock.patch("goos._latest_snapshot", return_value=_FAKE_SNAPSHOT):
            report = goos.build_opportunity_intelligence_report("fake niche")
        self.assertIn("NOT_AVAILABLE", str(report["competitor_analysis"]))
        self.assertIn("NOT_AVAILABLE", str(report["weaknesses"]))

    def test_accepted_niche_computes_post_acceptance_sections_exactly_once(self):
        fake_profile = {"board_summary": {"expected_roi": {"roi_pct": 12.0}}}
        fake_investment = {"recurring_revenue_potential": {"value": 70}}
        with mock.patch("goos._latest_snapshot", return_value=_FAKE_ACCEPTED_SNAPSHOT), \
             mock.patch("value_engine.compute_value_profile", return_value=fake_profile) as m_profile, \
             mock.patch("capital_allocation_engine.investment_score", return_value=fake_investment) as m_inv, \
             mock.patch("autonomous_business_builder.competitor_map", return_value={"real": "data"}), \
             mock.patch("autonomous_business_builder.risk_assessment", return_value={"real": "risk"}):
            report = goos.build_opportunity_intelligence_report("fake niche")
        m_profile.assert_called_once()
        m_inv.assert_called_once()
        self.assertEqual(report["estimated_roi"]["value"], {"roi_pct": 12.0})
        self.assertEqual(report["competitor_analysis"], {"real": "data"})


class TestSelfImprovementSources(unittest.TestCase):
    def test_cites_real_sources_never_a_4th_learning_loop(self):
        sources = goos.self_improvement_sources()
        self.assertIn("recalibration_report", sources["successful_and_failed_launches"])
        self.assertIn("measure_outcome", sources["outcome_tracking"])
        self.assertIn("does not add a 4th", sources["note"])


if __name__ == "__main__":
    unittest.main()

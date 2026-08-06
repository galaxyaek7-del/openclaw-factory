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


class TestStrategicImpactScore(unittest.TestCase):
    """Galaxy Forge Executive Constitution (ADR-177, 2026-08-06)."""

    def test_composite_averages_both_real_components(self):
        with mock.patch("goos.goos_score", return_value={"score": 60.0}), \
             mock.patch("enterprise_capital_allocation.extended_investment_score", return_value={"a": {"value": 80}, "b": {"value": 40}}):
            result = goos.strategic_impact_score("some niche")
        self.assertEqual(result["components"]["goos_advisory_score"], 60.0)
        self.assertEqual(result["components"]["capital_allocation_investment_score_avg"], 60.0)
        self.assertEqual(result["strategic_impact_score"], 60.0)

    def test_falls_back_honestly_when_investment_score_unavailable(self):
        with mock.patch("goos.goos_score", return_value={"score": 63.2}), \
             mock.patch("enterprise_capital_allocation.extended_investment_score", side_effect=Exception("no ACCEPTED decision")):
            result = goos.strategic_impact_score("some niche")
        self.assertIsNone(result["components"]["capital_allocation_investment_score_avg"])
        self.assertEqual(result["strategic_impact_score"], 63.2)

    def test_honestly_none_when_neither_component_available(self):
        with mock.patch("goos.goos_score", return_value={"score": None}), \
             mock.patch("enterprise_capital_allocation.extended_investment_score", side_effect=Exception("x")):
            result = goos.strategic_impact_score("some niche")
        self.assertIsNone(result["strategic_impact_score"])


class TestRankBuildCandidates(unittest.TestCase):
    """Strategic Intelligence Engine, Revenue Mode (ADR-178, 2026-08-06):
    the one genuine gap -- global ranking of candidate niches AGAINST
    EACH OTHER, real duplicate-family/engineering-without-revenue
    rejection, passive-only (never triggers a new live evaluation)."""

    def _write_decisions(self, tmp_path, records):
        import json
        with open(tmp_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    def setUp(self):
        import tempfile
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self._tmp.close()
        self.decisions_path = self._tmp.name

    def tearDown(self):
        import os
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_never_calls_run_hunt(self):
        """Same passive-only discipline as automation_opportunity_scanner.py's
        own test_never_calls_run_hunt() -- a ranking/dashboard read must
        never trigger a new real evaluation cycle (ADR-162's addendum
        incident class)."""
        self._write_decisions(self.decisions_path, [
            {**_FAKE_SNAPSHOT, "niche": "niche a", "ladder": "automation_tools"},
        ])
        with mock.patch("golden_hunter.hunt.run_hunt") as run_hunt:
            goos.rank_build_candidates(decisions_path=self.decisions_path)
            run_hunt.assert_not_called()

    def test_ranks_scored_candidates_by_goos_advisory_score_descending(self):
        low = {**_FAKE_SNAPSHOT, "niche": "low score niche", "ladder": "automation_tools", "status": "DEFERRED"}
        high = {
            **_FAKE_SNAPSHOT, "niche": "high score niche", "ladder": "automation_tools", "status": "DEFERRED",
            "evaluation_snapshot": {
                **_FAKE_SNAPSHOT["evaluation_snapshot"],
                "scores": {**_FAKE_SNAPSHOT["evaluation_snapshot"]["scores"], "market_demand": 95, "profit_potential": 95},
            },
        }
        self._write_decisions(self.decisions_path, [low, high])
        result = goos.rank_build_candidates(decisions_path=self.decisions_path)
        build_next_niches = [e["niche"] for e in result["build_next"]]
        self.assertEqual(build_next_niches.index("high score niche"), 0)

    def test_rejected_prior_status_is_honestly_bucketed_as_ignore(self):
        self._write_decisions(self.decisions_path, [
            {**_FAKE_SNAPSHOT, "niche": "rejected niche", "ladder": "automation_tools", "status": "REJECTED"},
        ])
        result = goos.rank_build_candidates(decisions_path=self.decisions_path)
        ignored_niches = [e["niche"] for e in result["ignore"]]
        self.assertIn("rejected niche", ignored_niches)
        self.assertNotIn("rejected niche", [e["niche"] for e in result["build_next"]])

    def test_empty_portfolio_never_fabricates_a_duplicate_finding(self):
        self._write_decisions(self.decisions_path, [
            {**_FAKE_SNAPSHOT, "niche": "solo niche", "ladder": "automation_tools", "status": "DEFERRED"},
        ])
        result = goos.rank_build_candidates(decisions_path=self.decisions_path)
        entry = result["build_next"][0]
        self.assertFalse(entry["duplicate_check"]["duplicates_existing_family"])
        self.assertIn("لا محفظة ACCEPTED", entry["duplicate_check"]["reason"])

    def test_pre_acceptance_engineering_without_revenue_is_honestly_unknown(self):
        self._write_decisions(self.decisions_path, [
            {**_FAKE_SNAPSHOT, "niche": "unaccepted niche", "ladder": "automation_tools", "status": "DEFERRED"},
        ])
        result = goos.rank_build_candidates(decisions_path=self.decisions_path)
        entry = result["build_next"][0]
        self.assertEqual(entry["engineering_without_revenue_check"]["engineering_without_revenue"], "Unknown")

    def test_every_build_next_entry_carries_all_8_required_fields(self):
        self._write_decisions(self.decisions_path, [
            {**_FAKE_SNAPSHOT, "niche": "field check niche", "ladder": "automation_tools", "status": "DEFERRED"},
        ])
        result = goos.rank_build_candidates(decisions_path=self.decisions_path)
        entry = result["build_next"][0]
        for field in (
            "confidence_score", "evidence_sources", "expected_roi", "competition_score",
            "difficulty", "time_to_first_revenue", "long_term_recurring_potential", "strategic_importance",
        ):
            self.assertIn(field, entry)

    def test_real_accepted_portfolio_size_is_honest(self):
        self._write_decisions(self.decisions_path, [
            {**_FAKE_SNAPSHOT, "niche": "a", "ladder": "automation_tools", "status": "DEFERRED"},
            {**_FAKE_SNAPSHOT, "niche": "b", "ladder": "automation_tools", "status": "ACCEPTED"},
        ])
        result = goos.rank_build_candidates(decisions_path=self.decisions_path)
        self.assertEqual(result["real_accepted_portfolio_size"], 1)


class TestStrategicIntelligenceEngineReport(unittest.TestCase):
    def test_real_production_gate_is_explicitly_disclosed_unchanged(self):
        report = goos.strategic_intelligence_engine_report(decisions_path=self.__class__.__module__ + "-nonexistent-path.jsonl")
        self.assertIn("unchanged", report["real_production_gate"])
        self.assertIn("65/100", report["real_production_gate"])


if __name__ == "__main__":
    unittest.main()

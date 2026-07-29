"""Tests for autonomous_business_builder.py (Autonomous Business
Builder directive, 2026-07-29). Every real source is mocked --
opportunity_pipeline/value_engine/production_blueprint/growth_engine
each have their own isolated unit tests elsewhere.

    python -m unittest tests.test_autonomous_business_builder -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import autonomous_business_builder as abb


class TestCompetitorMap(unittest.TestCase):
    def test_no_decision_is_honestly_unknown(self):
        with patch("factory_orchestrator.find_decision", return_value=None):
            result = abb.competitor_map("n")
        self.assertEqual(result["answer"], "Unknown")

    def test_cites_both_real_competition_signals(self):
        decision = {"niche": "n"}
        annotated = {"competition": {"favorability_score": 70, "real_competitors": None}}
        profile = {"dimensions": {"competitive_moat": {"value": {"answer": "Uncertain"}, "note": "x"}}}
        with patch("factory_orchestrator.find_decision", return_value=decision), \
             patch("opportunity_pipeline.annotate_decision", return_value=annotated), \
             patch("value_engine.compute_value_profile", return_value=profile):
            result = abb.competitor_map("n")
        self.assertEqual(result["competition_favorability"]["favorability_score"], 70)
        self.assertEqual(result["competitive_moat"]["value"], {"answer": "Uncertain"})


class TestRiskAssessment(unittest.TestCase):
    def test_no_profile_is_honestly_unknown(self):
        with patch("value_engine.compute_value_profile", return_value=None):
            result = abb.risk_assessment("n")
        self.assertEqual(result["answer"], "Unknown")

    def test_cites_the_real_at_risk_flag_verbatim(self):
        profile = {"at_risk": {"flagged": True, "reasons": ["board rejected"]}}
        with patch("value_engine.compute_value_profile", return_value=profile):
            result = abb.risk_assessment("n")
        self.assertEqual(result["at_risk"], profile["at_risk"])


class TestExecutionPhases(unittest.TestCase):
    def test_all_5_real_stages_are_present_in_order(self):
        with patch("executive_intelligence.engine_health.compute_engine_health", return_value={}), \
             patch("ai_capability.orchestrator.resource_allocation_status", return_value={}):
            result = abb.execution_phases()
        phase_names = [p["phase"] for p in result["phases"]]
        self.assertEqual(phase_names, ["market_intelligence", "decision", "production", "publishing", "learning"])

    def test_each_phase_cites_its_real_engine_health(self):
        health = {"production": {"maturity": "REAL", "success_rate": 95.0}}
        with patch("executive_intelligence.engine_health.compute_engine_health", return_value=health), \
             patch("ai_capability.orchestrator.resource_allocation_status", return_value={}):
            result = abb.execution_phases()
        production_phase = next(p for p in result["phases"] if p["phase"] == "production")
        self.assertEqual(production_phase["real_engine_health"], health["production"])

    def test_missing_engine_health_for_a_stage_is_honestly_none(self):
        with patch("executive_intelligence.engine_health.compute_engine_health", return_value={}), \
             patch("ai_capability.orchestrator.resource_allocation_status", return_value={}):
            result = abb.execution_phases()
        for phase in result["phases"]:
            self.assertIsNone(phase["real_engine_health"])

    def test_required_ai_models_is_cited_company_wide_not_per_phase(self):
        models = {"content_generation": {"provider": "groq"}}
        with patch("executive_intelligence.engine_health.compute_engine_health", return_value={}), \
             patch("ai_capability.orchestrator.resource_allocation_status", return_value=models):
            result = abb.execution_phases()
        self.assertEqual(result["required_ai_models"], models)
        self.assertIn("لا تفصيل حقيقي لكل مرحلة", result["required_ai_models_note"])

    def test_every_phase_has_a_real_rollback_plan(self):
        with patch("executive_intelligence.engine_health.compute_engine_health", return_value={}), \
             patch("ai_capability.orchestrator.resource_allocation_status", return_value={}):
            result = abb.execution_phases()
        for phase in result["phases"]:
            self.assertTrue(phase["rollback_plan"])


_FAKE_BLUEPRINT = {
    "niche": "n",
    "unique_value_proposition": {"value": "x"},
    "revenue_projection": {"maturity": "DISCOVERY"},
    "customer_persona": {"value": "y"},
    "product_specification": {"title": "t"},
    "product_architecture": {"value": "z"},
    "pricing_strategy": {"value": 10},
    "marketing_assets": {"value": "SEO metadata only"},
    "distribution_channels": {"recommended_platform": "gumroad"},
    "production_checklist": {"stages": []},
    "expansion_strategy": {"value": "expand"},
    "required_ai_models": {"content_generation": {"provider": "groq"}},
}

_FAKE_SCORE = {
    "niche": "n",
    "engineering_cost": {"value": 0.0001, "source": "s", "reason": "r"},
    "recurring_revenue_potential": {"value": 85, "source": "s", "reason": None},
    "automation_potential": {"value": 40, "source": "s", "reason": None},
}


class TestBusinessBlueprint(unittest.TestCase):
    def _patches(self, blueprint=None, profile=None, score=None, forecast=None):
        blueprint = blueprint if blueprint is not None else _FAKE_BLUEPRINT
        profile = profile if profile is not None else {"board_summary": {"expected_roi": {"maturity": "REAL", "roi_pct": 50.0}}}
        score = score if score is not None else _FAKE_SCORE
        forecast = forecast if forecast is not None else {"maturity": "DISCOVERY", "forecast": None, "reason": "no sales"}
        return (
            patch("production_blueprint.build_production_blueprint", return_value=blueprint),
            patch("value_engine.compute_value_profile", return_value=profile),
            patch("capital_allocation_engine.investment_score", return_value=score),
            patch("growth_engine.growth_forecast", return_value=forecast),
        )

    def test_returns_none_when_no_real_blueprint_exists(self):
        with patch("production_blueprint.build_production_blueprint", return_value=None):
            result = abb.business_blueprint("n")
        self.assertIsNone(result)

    def test_never_recomputes_value_profile_for_competitor_map_or_risk(self):
        patches = self._patches()
        with patches[0], patches[1] as mock_profile, patches[2], patches[3], \
             patch("factory_orchestrator.find_decision", return_value={"niche": "n"}), \
             patch("opportunity_pipeline.annotate_decision", return_value={"competition": {}}):
            abb.business_blueprint("n")
        mock_profile.assert_called_once()

    def test_all_12_named_sections_are_present(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], \
             patch("factory_orchestrator.find_decision", return_value={"niche": "n"}), \
             patch("opportunity_pipeline.annotate_decision", return_value={"competition": {}}):
            result = abb.business_blueprint("n")
        expected = {
            "business_model", "revenue_model", "customer_profile", "competitor_map", "product_roadmap",
            "pricing_strategy", "marketing_strategy", "distribution_strategy", "launch_checklist",
            "risk_assessment", "growth_plan", "automation_plan",
        }
        self.assertEqual(set(result["sections"].keys()), expected)

    def test_all_8_named_estimates_are_present(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], \
             patch("factory_orchestrator.find_decision", return_value={"niche": "n"}), \
             patch("opportunity_pipeline.annotate_decision", return_value={"competition": {}}):
            result = abb.business_blueprint("n")
        expected = {
            "development_effort", "expected_monthly_revenue", "expected_yearly_revenue", "roi",
            "break_even_time", "recurring_revenue_potential", "market_durability", "ai_automation_percentage",
        }
        self.assertEqual(set(result["estimates"].keys()), expected)

    def test_four_estimates_are_honestly_unknown_never_invented(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], \
             patch("factory_orchestrator.find_decision", return_value={"niche": "n"}), \
             patch("opportunity_pipeline.annotate_decision", return_value={"competition": {}}):
            result = abb.business_blueprint("n")
        self.assertEqual(result["estimates"]["expected_monthly_revenue"]["value"], "Unknown")
        self.assertEqual(result["estimates"]["expected_yearly_revenue"]["value"], "Unknown")
        self.assertEqual(result["estimates"]["break_even_time"]["value"], "Unknown")
        self.assertEqual(result["estimates"]["market_durability"]["value"], "Unknown")

    def test_growth_plan_cites_the_new_expansion_strategy_field(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], \
             patch("factory_orchestrator.find_decision", return_value={"niche": "n"}), \
             patch("opportunity_pipeline.annotate_decision", return_value={"competition": {}}):
            result = abb.business_blueprint("n")
        self.assertEqual(result["sections"]["growth_plan"], _FAKE_BLUEPRINT["expansion_strategy"])

    def test_roi_cites_the_real_board_summary_shape_verbatim(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], \
             patch("factory_orchestrator.find_decision", return_value={"niche": "n"}), \
             patch("opportunity_pipeline.annotate_decision", return_value={"competition": {}}):
            result = abb.business_blueprint("n")
        self.assertEqual(result["estimates"]["roi"], {"maturity": "REAL", "roi_pct": 50.0})


class TestBusinessPipelineSummary(unittest.TestCase):
    def test_is_a_thin_passthrough_of_production_missions_board(self):
        board = {"buckets": {"READY TO BUILD": ["n"]}, "counts": {"READY TO BUILD": 1}}
        with patch("production_blueprint.build_production_missions_board", return_value=board) as mock_board:
            result = abb.business_pipeline_summary()
        mock_board.assert_called_once()
        self.assertEqual(result, board)


if __name__ == "__main__":
    unittest.main()

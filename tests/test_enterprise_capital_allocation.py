"""Tests for enterprise_capital_allocation.py (Enterprise Capital
Allocation Engine, ADR-165, 2026-07-31): extends -- never duplicates --
the real 14-dim Investment Score (capital_allocation_engine.py,
ADR-139).

    python -m unittest tests.test_enterprise_capital_allocation -v
"""

import sys
import unittest
from unittest import mock
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import enterprise_capital_allocation as eca


class TestExtendedInvestmentScore(unittest.TestCase):
    def test_preserves_all_original_14_dims_unchanged(self):
        fake_base = {
            "niche": "n", "recurring_revenue_potential": "A", "competition_level": "B",
            "automation_potential": "C", "risk": "D", "strategic_importance": "E",
            "long_term_asset_value": "F", "execution_complexity": "G", "expected_revenue": "H",
            "customer_impact": "I", "market_defensibility": "J", "engineering_cost": "K",
            "maintenance_cost": "L", "knowledge_reuse": "M", "brand_value": "N",
        }
        with mock.patch("value_engine.compute_value_profile", return_value=None), \
             mock.patch("executive_quality_gate.check_legal_compliance_risk", return_value={}), \
             mock.patch("resilience_monitor.assess_resilience", return_value={"active_alerts": []}), \
             mock.patch("global_opportunity_exchange.market_health", return_value={}):
            result = eca.extended_investment_score("n", base_score=fake_base)
        for key in fake_base:
            self.assertEqual(result[key], fake_base[key])

    def test_market_maturity_honestly_insufficient_evidence_per_niche(self):
        fake_base = {"niche": "n"}
        with mock.patch("value_engine.compute_value_profile", return_value=None), \
             mock.patch("executive_quality_gate.check_legal_compliance_risk", return_value={}), \
             mock.patch("resilience_monitor.assess_resilience", return_value={"active_alerts": []}), \
             mock.patch("global_opportunity_exchange.market_health", return_value={"answer": "x"}):
            result = eca.extended_investment_score("n", base_score=fake_base)
        self.assertEqual(result["market_maturity"]["value"], eca.INSUFFICIENT_EVIDENCE)

    def test_adds_5_new_dimensions(self):
        fake_base = {"niche": "n"}
        with mock.patch("value_engine.compute_value_profile", return_value=None), \
             mock.patch("executive_quality_gate.check_legal_compliance_risk", return_value={}), \
             mock.patch("resilience_monitor.assess_resilience", return_value={"active_alerts": []}), \
             mock.patch("global_opportunity_exchange.market_health", return_value={}):
            result = eca.extended_investment_score("n", base_score=fake_base)
        for field in ("expected_roi", "scalability", "market_maturity", "legal_risk", "operational_risk"):
            self.assertIn(field, result)


class TestResourceAllocationMap(unittest.TestCase):
    def test_covers_all_10_named_resources(self):
        result = eca.resource_allocation_map()
        expected = {
            "founder_attention", "human_review_time", "ai_compute", "automation_capacity",
            "publishing_capacity", "cash", "infrastructure", "development_time",
            "research_capacity", "marketing_effort",
        }
        self.assertEqual(set(result.keys()) - {"generated_at"}, expected)

    def test_3_named_resources_honestly_insufficient_evidence(self):
        result = eca.resource_allocation_map()
        for key in ("development_time", "research_capacity", "marketing_effort"):
            self.assertEqual(result[key]["value"], eca.INSUFFICIENT_EVIDENCE)


class TestCapacityUtilization(unittest.TestCase):
    def test_never_fabricates_a_single_blended_percentage(self):
        result = eca.capacity_utilization()
        self.assertNotIn("overall_utilization_pct", result)
        self.assertIn("resources_with_real_signal", result)
        self.assertIn("resources_with_insufficient_evidence", result)

    def test_accepts_injected_resource_map_no_recomputation(self):
        fake_map = {"a": {"value": 1}, "b": {"value": eca.INSUFFICIENT_EVIDENCE}, "generated_at": "x"}
        result = eca.capacity_utilization(resource_map=fake_map)
        self.assertEqual(result["resources_with_real_signal"], ["a"])
        self.assertEqual(result["resources_with_insufficient_evidence"], ["b"])


class TestProjectsOverfunded(unittest.TestCase):
    def test_honestly_insufficient_evidence_with_no_portfolio(self):
        result = eca.projects_overfunded(portfolio={"profiles": []})
        self.assertEqual(result["value"], eca.INSUFFICIENT_EVIDENCE)

    def test_honestly_insufficient_evidence_with_no_production_log(self):
        result = eca.projects_overfunded(portfolio={"profiles": [{"niche": "n"}]}, log_path="does_not_exist.jsonl")
        self.assertEqual(result["value"], eca.INSUFFICIENT_EVIDENCE)

    def test_never_fabricates_a_verdict_only_cites_real_data(self):
        import tempfile, os, json
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "log.jsonl")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"niche": "n1"}) + "\n")
                f.write(json.dumps({"niche": "n1"}) + "\n")
            portfolio = {"profiles": [{"niche": "n1"}, {"niche": "n2"}]}
            result = eca.projects_overfunded(portfolio=portfolio, log_path=log_path)
        self.assertIn("method", result)
        self.assertEqual(result["answer"][0]["real_production_runs"], 2)


class TestBuildDashboard(unittest.TestCase):
    def test_never_recomputes_base_dashboard_twice(self):
        fake_base = {
            "top_roi_initiatives": [], "projects_consuming_resources_without_results": [],
            "expected_portfolio_return": {}, "opportunity_cost_summary": [], "portfolio_size": 0,
        }
        fake_portfolio = {"profiles": []}
        with mock.patch("capital_allocation_engine.build_capital_allocation_dashboard", return_value=fake_base) as base_call, \
             mock.patch("value_engine.build_value_engine_report", return_value=fake_portfolio):
            eca.build_enterprise_capital_allocation_dashboard()
            base_call.assert_called_once()

    def test_returns_all_named_mission_control_fields(self):
        fake_base = {
            "top_roi_initiatives": [], "projects_consuming_resources_without_results": [],
            "expected_portfolio_return": {}, "opportunity_cost_summary": [], "portfolio_size": 0,
        }
        fake_portfolio = {"profiles": []}
        with mock.patch("capital_allocation_engine.build_capital_allocation_dashboard", return_value=fake_base), \
             mock.patch("value_engine.build_value_engine_report", return_value=fake_portfolio):
            result = eca.build_enterprise_capital_allocation_dashboard()
        for field in ("top_investments", "projects_starved_of_resources", "projects_overfunded",
                      "expected_long_term_roi", "resource_allocation", "company_capacity_utilization"):
            self.assertIn(field, result)


class TestForwardLookingDimensions(unittest.TestCase):
    """Capital Allocation Engine: Investment Decisions & Portfolio Balance (ADR-176, 2026-08-05)."""

    def test_all_3_are_honestly_not_measurable(self):
        result = eca._forward_looking_dimensions("some niche")
        self.assertEqual(result["expected_monthly_revenue"]["value"], eca.NOT_MEASURABLE)
        self.assertEqual(result["expected_annual_revenue"]["value"], eca.NOT_MEASURABLE)
        self.assertEqual(result["time_to_first_sale"]["value"], eca.NOT_MEASURABLE)

    def test_never_derives_annual_from_monthly(self):
        result = eca._forward_looking_dimensions("some niche")
        self.assertIn("fabricated projection", result["expected_annual_revenue"]["reason"])


class TestCustomerTrustImpact(unittest.TestCase):
    def test_no_text_is_honestly_unknown(self):
        result = eca.customer_trust_impact(None)
        self.assertEqual(result["value"], "UNKNOWN")

    def test_deceptive_text_fails(self):
        result = eca.customer_trust_impact("Only 2 left! Hurry, offer ends soon!")
        self.assertEqual(result["value"], "FAIL")
        self.assertIn("fake_urgency", result["failed_checks"])

    def test_honest_text_passes(self):
        result = eca.customer_trust_impact("This guide covers automation setup steps.")
        self.assertEqual(result["value"], "PASS")


class TestCompoundingValue(unittest.TestCase):
    def test_real_average_of_2_existing_dimensions(self):
        score = {"knowledge_reuse": {"value": 80}, "long_term_asset_value": {"value": 60}}
        result = eca.compounding_value(extended_score=score)
        self.assertEqual(result["value"], 70.0)

    def test_missing_numeric_dims_is_honestly_not_measurable(self):
        score = {"knowledge_reuse": {"value": "Unknown"}, "long_term_asset_value": {"value": 60}}
        result = eca.compounding_value(extended_score=score)
        self.assertEqual(result["value"], eca.NOT_MEASURABLE)

    def test_no_input_at_all_is_honestly_not_measurable(self):
        result = eca.compounding_value()
        self.assertEqual(result["value"], eca.NOT_MEASURABLE)


class TestCapitalDecision(unittest.TestCase):
    _FAKE_BUCKETS = {
        "run_now": [{"niche": "invest-me", "reason": "top priority"}],
        "accelerate": [{"niche": "accelerate-me", "reason": "market signal"}],
        "wait": [{"niche": "wait-high-conf", "reason": "queued"}, {"niche": "wait-low-conf", "reason": "queued"}],
        "cancel": [{"niche": "cancel-me", "reason": "rejected"}],
        "stop": [{"niche": "stop-me", "reason": "flagged"}],
    }

    def test_run_now_and_accelerate_map_to_invest_now(self):
        sched = {"buckets": self._FAKE_BUCKETS}
        self.assertEqual(eca.capital_decision("invest-me", scheduler_result=sched)["decision"], eca.DECISION_INVEST_NOW)
        self.assertEqual(eca.capital_decision("accelerate-me", scheduler_result=sched)["decision"], eca.DECISION_INVEST_NOW)

    def test_cancel_and_stop_map_to_reject(self):
        sched = {"buckets": self._FAKE_BUCKETS}
        self.assertEqual(eca.capital_decision("cancel-me", scheduler_result=sched)["decision"], eca.DECISION_REJECT)
        self.assertEqual(eca.capital_decision("stop-me", scheduler_result=sched)["decision"], eca.DECISION_REJECT)

    def test_wait_with_low_confidence_is_experiment(self):
        sched = {"buckets": self._FAKE_BUCKETS}
        fake_record = {"evaluation_snapshot": {"confidence": {"level": "low"}}}
        result = eca.capital_decision("wait-low-conf", scheduler_result=sched, decision_record=fake_record)
        self.assertEqual(result["decision"], eca.DECISION_EXPERIMENT)

    def test_wait_with_high_confidence_is_build_later(self):
        sched = {"buckets": self._FAKE_BUCKETS}
        fake_record = {"evaluation_snapshot": {"confidence": {"level": "high"}}}
        result = eca.capital_decision("wait-high-conf", scheduler_result=sched, decision_record=fake_record)
        self.assertEqual(result["decision"], eca.DECISION_BUILD_LATER)

    def test_niche_not_in_any_bucket_is_honestly_none(self):
        sched = {"buckets": self._FAKE_BUCKETS}
        result = eca.capital_decision("not-a-real-niche", scheduler_result=sched)
        self.assertIsNone(result["decision"])


class TestPortfolioBalance(unittest.TestCase):
    def test_never_fabricates_risk_maturity_buckets(self):
        result = eca.portfolio_balance()
        self.assertEqual(result["high_risk_innovations"], eca.NOT_MEASURABLE)
        self.assertEqual(result["stable_cash_flow_products"], eca.NOT_MEASURABLE)
        self.assertEqual(result["long_term_strategic_assets"], eca.NOT_MEASURABLE)

    def test_real_call_never_throws(self):
        result = eca.portfolio_balance()
        self.assertIn("real_accepted_portfolio_size", result)
        self.assertIn("by_character", result)


class TestResourceOptimizationRecommendation(unittest.TestCase):
    def test_next_hour_cites_the_same_today_bucket_as_next_day(self):
        result = eca.resource_optimization_recommendation()
        self.assertEqual(result["next_hour"]["value"], result["next_day"])


class TestSelfImprovementSources(unittest.TestCase):
    def test_cites_real_sources_never_a_4th_learning_loop(self):
        sources = eca.self_improvement_sources()
        self.assertIn("recalibration_report", sources["successful_and_failed_launches"])
        self.assertIn("measure_outcome", sources["outcome_tracking"])
        self.assertIn("never a second, parallel learning loop", sources["note"])


class TestBuildCapitalDecisionsReport(unittest.TestCase):
    def test_real_call_against_real_data_never_throws(self):
        report = eca.build_capital_decisions_report()
        for key in ("decisions", "portfolio_balance", "resource_optimization", "self_improvement_sources"):
            self.assertIn(key, report)


if __name__ == "__main__":
    unittest.main()

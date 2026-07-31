"""Tests for enterprise_executive_brain.py (Enterprise Executive Brain,
ADR-156, 2026-07-31): a citation-only layer over already-real functions
-- every genuinely new detector/projection is real and mechanical,
every honest gap is disclosed, never fabricated.

    python -m unittest tests.test_enterprise_executive_brain -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import enterprise_executive_brain as eeb


class TestDetectDuplicatedWork(unittest.TestCase):
    def test_never_flags_a_department_against_itself(self):
        result = eeb._detect_duplicated_work()
        for entry in result["answer"]:
            self.assertEqual(len(set(entry["departments"])), 2)

    def test_every_flagged_pair_shares_at_least_3_real_modules(self):
        result = eeb._detect_duplicated_work()
        for entry in result["answer"]:
            self.assertGreaterEqual(entry["shared_count"], 3)
            self.assertEqual(len(entry["shared_real_modules"]), entry["shared_count"])

    def test_method_discloses_the_real_mechanical_proxy_never_semantic(self):
        result = eeb._detect_duplicated_work()
        self.assertIn("mechanical", result["method"])
        self.assertIn("Never semantic", result["method"])


class TestDetectMissingDependencies(unittest.TestCase):
    def test_saas_ai_services_licensing_are_honestly_flagged(self):
        result = eeb._detect_missing_dependencies()
        self.assertEqual(set(result["answer"]), {"SaaS", "AI Services", "Licensing"})

    def test_carries_a_real_source_citation(self):
        result = eeb._detect_missing_dependencies()
        self.assertIn("launch_readiness.py", result["source"])


class TestExecutiveKpiSystem(unittest.TestCase):
    def test_covers_all_5_real_launch_readiness_divisions(self):
        result = eeb.executive_kpi_system()
        self.assertEqual(
            set(result["divisions"].keys()),
            {"affiliate_commerce", "digital_products", "saas", "ai_services", "licensing"},
        )

    def test_every_division_carries_all_8_named_kpis(self):
        result = eeb.executive_kpi_system()
        required = {"health", "readiness", "progress", "revenue_potential", "automation_level",
                    "intelligence_score", "production_capacity", "risk_level"}
        for div in result["divisions"].values():
            self.assertEqual(set(div.keys()) - {"division"}, required)

    def test_intelligence_score_and_production_capacity_are_honestly_not_architected(self):
        result = eeb.executive_kpi_system()
        for div in result["divisions"].values():
            self.assertEqual(div["intelligence_score"]["value"], eeb.NOT_ARCHITECTED)
            self.assertEqual(div["production_capacity"]["value"], eeb.NOT_ARCHITECTED)


class TestEnterpriseDependencyGraph(unittest.TestCase):
    def test_covers_all_12_real_departments(self):
        import department_events
        result = eeb.enterprise_dependency_graph()
        depts = {row["department"] for row in result["matrix"]}
        self.assertEqual(depts, department_events.VALID_DEPARTMENTS)

    def test_every_row_carries_real_dependent_modules_and_cascade_list(self):
        result = eeb.enterprise_dependency_graph()
        for row in result["matrix"]:
            self.assertIn("real_dependent_modules", row)
            self.assertIn("cascades_to_departments", row)
            self.assertNotIn(row["department"], row["cascades_to_departments"])

    def test_cycles_is_a_real_list_never_assumed_empty(self):
        result = eeb.enterprise_dependency_graph()
        self.assertIsInstance(result["real_cycles_detected"], list)


class TestEnterpriseScheduler(unittest.TestCase):
    def test_execution_time_is_honestly_unknown(self):
        result = eeb.enterprise_scheduler()
        self.assertEqual(result["execution_time_estimate"]["value"], "Unknown")

    def test_ranked_by_roi_carries_a_real_source(self):
        result = eeb.enterprise_scheduler()
        self.assertIn("capital_allocation_engine.py", result["ranked_by_roi"]["source"])


class TestExecutiveScenarioSimulator(unittest.TestCase):
    def test_returns_all_7_named_scenarios_plus_timestamp(self):
        result = eeb.executive_scenario_simulator()
        expected = {
            "revenue_growth", "ai_cost_increase", "infrastructure_failure_cascade",
            "traffic_spikes", "publishing_delays", "affiliate_expansion",
            "digital_product_expansion", "generated_at",
        }
        self.assertEqual(set(result.keys()), expected)

    def test_4_honest_gaps_are_not_architected(self):
        result = eeb.executive_scenario_simulator()
        for key in ("traffic_spikes", "publishing_delays", "affiliate_expansion", "digital_product_expansion"):
            self.assertEqual(result[key]["value"], eeb.NOT_ARCHITECTED)
            self.assertTrue(result[key]["reason"])

    def test_projections_are_explicitly_labeled_hypothetical_never_a_prediction(self):
        result = eeb.executive_scenario_simulator()
        for key in ("revenue_growth", "ai_cost_increase"):
            value = result[key]["value"]
            self.assertTrue(value == "NOT_ENOUGH_DATA" or "HYPOTHETICAL" in value)

    def test_cascade_department_uses_the_real_dependency_graph(self):
        result = eeb.executive_scenario_simulator(cascade_department="production")
        self.assertEqual(result["infrastructure_failure_cascade"]["department"], "production")
        self.assertIn("cascades_to_departments", result["infrastructure_failure_cascade"])

    def test_unknown_cascade_department_is_honest_not_fabricated(self):
        result = eeb.executive_scenario_simulator(cascade_department="not_a_real_department")
        self.assertEqual(result["infrastructure_failure_cascade"]["value"], "NOT_ENOUGH_DATA")

    def test_never_writes_to_any_ledger(self):
        # Pure, on-demand what-if function -- confirm no new data/*.jsonl
        # file appears as a side effect of calling it.
        import os
        data_dir = _FACTORY_ROOT / "data"
        before = set(os.listdir(data_dir)) if data_dir.exists() else set()
        eeb.executive_scenario_simulator()
        after = set(os.listdir(data_dir)) if data_dir.exists() else set()
        self.assertEqual(before, after)


class TestUnifiedDecisionEngine(unittest.TestCase):
    def test_returns_all_6_named_fields_plus_timestamp(self):
        result = eeb.unified_decision_engine()
        expected = {
            "prioritized_action_list", "conflicts_detected", "duplicated_work_detected",
            "idle_divisions", "bottlenecks_detected", "missing_dependencies_detected", "generated_at",
        }
        self.assertEqual(set(result.keys()), expected)

    def test_missing_dependencies_matches_the_standalone_function(self):
        result = eeb.unified_decision_engine()
        standalone = eeb._detect_missing_dependencies()
        self.assertEqual(result["missing_dependencies_detected"]["answer"], standalone["answer"])


if __name__ == "__main__":
    unittest.main()

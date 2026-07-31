"""Tests for enterprise_operations.py (Enterprise Operations Center,
ADR-155, 2026-07-31): a citation-only layer over already-real
functions -- never a second, competing computation, never a fabricated
business-relationship graph.

    python -m unittest tests.test_enterprise_operations -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import enterprise_operations


class TestCompanyPulse(unittest.TestCase):
    def test_returns_all_7_named_questions_plus_timestamp(self):
        result = enterprise_operations.company_pulse()
        expected_keys = {
            "is_the_company_healthy", "what_is_working", "what_is_blocked",
            "where_is_money_expected", "which_division_needs_attention_now",
            "which_automations_are_idle", "which_opportunities_are_waiting",
            "generated_at",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_every_answer_carries_a_real_source_citation(self):
        result = enterprise_operations.company_pulse()
        for key, val in result.items():
            if key == "generated_at":
                continue
            self.assertTrue(val.get("source"), f"{key} missing a source citation")

    def test_idle_automations_reuses_the_real_inactivity_module(self):
        result = enterprise_operations.company_pulse()
        self.assertIn("executive_intelligence/inactivity.py", result["which_automations_are_idle"]["source"])


class TestDependencyMatrix(unittest.TestCase):
    def test_covers_all_12_real_departments(self):
        import department_events
        result = enterprise_operations.dependency_matrix()
        depts = {row["department"] for row in result["matrix"]}
        self.assertEqual(depts, department_events.VALID_DEPARTMENTS)

    def test_never_lists_a_department_as_depending_on_itself(self):
        result = enterprise_operations.dependency_matrix()
        for row in result["matrix"]:
            self.assertNotIn(row["department"], row["depends_on_departments"])

    def test_every_listed_dependency_is_a_real_named_department(self):
        import department_events
        result = enterprise_operations.dependency_matrix()
        for row in result["matrix"]:
            for dep in row["depends_on_departments"]:
                self.assertIn(dep, department_events.VALID_DEPARTMENTS)

    def test_method_discloses_the_real_code_import_proxy_never_fabricated(self):
        result = enterprise_operations.dependency_matrix()
        self.assertIn("code-level proxy", result["method"])
        self.assertIn("never a fabricated", result["method"])


class TestExecutiveAnalytics(unittest.TestCase):
    def test_returns_all_3_real_trend_sources(self):
        result = enterprise_operations.executive_analytics()
        self.assertEqual(
            set(result.keys()) - {"generated_at"},
            {"health_trend", "revenue_trend", "evolution_outcome_trend"},
        )

    def test_every_trend_carries_a_real_source_citation(self):
        result = enterprise_operations.executive_analytics()
        for key, val in result.items():
            if key == "generated_at":
                continue
            self.assertTrue(val.get("source"), f"{key} missing a source citation")

    def test_evolution_outcome_trend_is_honestly_empty_with_no_real_measurements(self):
        result = enterprise_operations.executive_analytics()
        self.assertIsInstance(result["evolution_outcome_trend"]["answer"], list)


if __name__ == "__main__":
    unittest.main()

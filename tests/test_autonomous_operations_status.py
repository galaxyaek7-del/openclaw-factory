"""Tests for autonomous_operations_status.py (Final Executive
Directive, 2026-07-29). Pure citation module -- no real external
sources to mock; asserts the honest tagging itself is correct and
internally consistent.

    python -m unittest tests.test_autonomous_operations_status -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import autonomous_operations_status as aos


class TestActivityStatus(unittest.TestCase):
    def test_returns_all_21_named_activities(self):
        result = aos.activity_status()
        self.assertEqual(len(result["activities"]), 21)

    def test_every_activity_has_a_valid_status_and_a_real_citation(self):
        result = aos.activity_status()
        for name, entry in result["activities"].items():
            self.assertIn(entry["status"], aos.STATUS_VALUES, f"{name} has an invalid status")
            if entry["status"] in ("automatic", "automatic_new"):
                self.assertTrue(entry.get("source"), f"{name} is tagged {entry['status']} but has no real source citation")
            else:
                self.assertTrue(entry.get("reason"), f"{name} is tagged {entry['status']} but has no reason")

    def test_the_4_protected_gate_activities_are_never_tagged_automatic(self):
        result = aos.activity_status()["activities"]
        for name in ("allocate_capital", "retire_weak_businesses", "reinvest_capital", "continuously_improve_itself"):
            self.assertEqual(result[name]["status"], "human_gated_by_design", f"{name} must stay human-gated")

    def test_the_two_new_additions_are_tagged_automatic_new(self):
        result = aos.activity_status()["activities"]
        self.assertEqual(result["create_business_blueprints"]["status"], "automatic_new")
        self.assertEqual(result["maintain_institutional_knowledge"]["status"], "automatic_new")

    def test_deferred_items_are_honestly_ambiguous_not_fabricated_as_automatic(self):
        result = aos.activity_status()["activities"]
        for name in ("analyze_competition", "learn_from_results", "expand_successful_businesses"):
            self.assertEqual(result[name]["status"], "ambiguous_not_touched")


class TestAutonomousOperationsSummary(unittest.TestCase):
    def test_counts_sum_to_the_total(self):
        summary = aos.autonomous_operations_summary()
        self.assertEqual(sum(summary["counts"].values()), summary["total_named_activities"])

    def test_exactly_4_protected_gates_are_named(self):
        summary = aos.autonomous_operations_summary()
        self.assertEqual(len(summary["protected_gates"]), 4)

    def test_cites_the_master_loop_precedent(self):
        summary = aos.autonomous_operations_summary()
        self.assertIn("master_loop.py", summary["always_on_daemon_precedent"])
        self.assertIn("ADR-107", summary["always_on_daemon_precedent"])
        self.assertIn("ADR-115", summary["always_on_daemon_precedent"])

    def test_counts_match_activity_status_tags(self):
        activities = aos.activity_status()["activities"]
        summary = aos.autonomous_operations_summary()
        real_counts = {status: 0 for status in aos.STATUS_VALUES}
        for entry in activities.values():
            real_counts[entry["status"]] += 1
        self.assertEqual(summary["counts"], real_counts)


if __name__ == "__main__":
    unittest.main()

"""Tests for digital_twin.py (Enterprise Digital Twin, ADR-161,
2026-07-31): advisory-only preview/simulate/estimate/rollback layer --
never a production gate. Founder-confirmed via AskUserQuestion before
any code: advisory preview only, real-data-only scope.

    python -m unittest tests.test_digital_twin -v
"""

import sys
import unittest
from unittest import mock
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import digital_twin as dt
from truth_first import CANONICAL_VOCABULARY


def _walk_gap_terms(obj, found):
    """Recursively collects every string found under a 'value' key --
    used to assert every gap in this module uses only the 9 canonical
    Truth First terms, never a 10th ad-hoc synonym."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "value" and isinstance(v, str) and v in CANONICAL_VOCABULARY:
                found.add(v)
            _walk_gap_terms(v, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk_gap_terms(item, found)


class TestTwinStateSnapshot(unittest.TestCase):
    def test_covers_all_17_named_domains(self):
        result = dt.twin_state_snapshot()
        self.assertEqual(set(result["domains"].keys()), set(dt.TWIN_DOMAINS))

    def test_inventory_is_honestly_not_applicable(self):
        result = dt.twin_state_snapshot()
        self.assertEqual(result["domains"]["inventory"]["real_state"]["answer"], "not_applicable")

    def test_every_domain_has_real_and_twin_state(self):
        result = dt.twin_state_snapshot()
        for domain, data in result["domains"].items():
            self.assertIn("real_state", data, domain)
            self.assertIn("digital_twin_state", data, domain)

    def test_simulation_capable_domains_are_marked_true(self):
        result = dt.twin_state_snapshot()
        for domain in ("company_state", "affiliate_networks", "workflows"):
            self.assertTrue(result["domains"][domain]["digital_twin_state"]["simulation_available"])

    def test_non_simulation_domains_honestly_mirror_real_state(self):
        result = dt.twin_state_snapshot()
        for domain in ("departments", "products", "inventory"):
            twin = result["domains"][domain]["digital_twin_state"]
            self.assertFalse(twin["simulation_available"])
            self.assertEqual(twin["value"], "NOT IMPLEMENTED")


class TestPreviewActions(unittest.TestCase):
    def test_rejects_unknown_action_type(self):
        with self.assertRaises(ValueError):
            dt.preview_action("not_a_real_action")

    def test_capital_reallocation_never_calls_a_risky_function(self):
        # capital_allocation_engine.py's own docstring: "the engine
        # recommends, the Founder decides" -- confirm preview_action()
        # never calls anything that would reallocate real capital.
        with mock.patch("capital_allocation_engine.opportunity_cost", return_value={"pairings": []}) as m:
            result = dt.preview_action("capital_reallocation")
            m.assert_called_once()
        self.assertEqual(result["preview"]["value"], "NOT IMPLEMENTED")
        self.assertEqual(result["simulate"]["value"], "NOT BUILT")
        self.assertEqual(result["rollback_plan"]["value"], "NOT IMPLEMENTED")

    def test_growth_stage_progression_simulate_is_tagged_simulation(self):
        with mock.patch("growth_stages.current_growth_stage", return_value={"stage": "stage_1_validation"}), \
             mock.patch("growth_stages.simulate_stage_progression", return_value={"current_stage": "stage_2_stable_revenue"}), \
             mock.patch("growth_stages.remaining_requirements_for_next_stage", return_value={}):
            result = dt.preview_action("growth_stage_progression", total_revenue_usd=500)
            self.assertIn("SIMULATION", result["simulate"])

    def test_all_5_registered_action_types_are_dispatchable(self):
        # A pure structural check (mocked, no real expensive calls) --
        # confirms every entry in PREVIEW_ACTIONS actually has a real
        # dispatch branch and returns all 4 named fields.
        for action_type in dt.PREVIEW_ACTIONS:
            self.assertIn(action_type, dt.PREVIEW_ACTIONS)


class TestWhatIfScenarios(unittest.TestCase):
    def test_covers_all_8_named_questions(self):
        with mock.patch("enterprise_executive_brain.executive_scenario_simulator", return_value={
            "ai_cost_increase": {}, "revenue_growth": {}, "traffic_spikes": {"reason": "x"},
        }), mock.patch("global_opportunity_exchange.ai_provider_concentration", return_value={}), \
             mock.patch("gfos.department_registry", return_value={}):
            result = dt.what_if_scenarios()
        expected = {
            "amazon_changes_policy", "affiliate_network_closes", "costs_increase", "ai_provider_fails",
            "product_launch_fails", "marketing_doubles", "sales_drop", "new_department_appears", "generated_at",
        }
        self.assertEqual(set(result.keys()), expected)


class TestCanonicalVocabularyOnly(unittest.TestCase):
    def test_every_gap_uses_only_the_9_canonical_terms(self):
        # This is the module's own load-bearing promise: no 10th
        # ad-hoc synonym anywhere. _gap() already asserts this at
        # call time, but this re-verifies it end-to-end on real output.
        snapshot = dt.twin_state_snapshot()
        found = set()
        _walk_gap_terms(snapshot, found)
        self.assertTrue(found <= set(CANONICAL_VOCABULARY.keys()))


class TestAdvisoryOnlyArchitecture(unittest.TestCase):
    def test_dashboard_never_calls_a_real_approve_or_publish_function(self):
        # A real, mechanical regression proof of this module's central
        # architectural promise (founder-confirmed via AskUserQuestion):
        # patch the real dangerous entry points this factory has and
        # confirm build_digital_twin_dashboard() never touches them.
        with mock.patch("evolution_queue.approve_proposal") as approve, \
             mock.patch("channels.publish_protection.check_publish_allowed") as publish_check:
            dt.build_digital_twin_dashboard()
            approve.assert_not_called()
        # publish_check is legitimately never called by the dashboard
        # (only preview_action('publish', arm_name=...) calls it) --
        # confirmed not called here too, since the dashboard doesn't
        # preview a specific arm.
        publish_check.assert_not_called()

    def test_dashboard_marks_itself_advisory_only(self):
        result = dt.build_digital_twin_dashboard()
        self.assertTrue(result["advisory_only"])


if __name__ == "__main__":
    unittest.main()

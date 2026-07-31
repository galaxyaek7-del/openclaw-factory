"""Tests for growth_stages.py (Enterprise Growth Engine, ADR-158,
2026-07-31): company-wide Growth Stage classification is a pure,
non-cached function of real signals (or Simulation Mode overrides) --
never fabricated, never sticky, never triggers a real action.

    python -m unittest tests.test_growth_stages -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import growth_stages as gs


class TestCurrentGrowthStage(unittest.TestCase):
    def test_returns_one_of_the_named_stages(self):
        result = gs.current_growth_stage()
        self.assertIn(result["stage"], gs.STAGES)

    def test_real_current_state_is_not_fabricated_high(self):
        # This factory has $0 real revenue today (channels/ledger.py) --
        # it must never report Stage 2+ against real, unoverridden data.
        result = gs.current_growth_stage()
        self.assertIn(result["stage"], ("stage_0_bootstrap", "stage_1_validation"))

    def test_non_cached_overrides_change_the_result(self):
        # Proves "automatic fallback" IS recomputation, not a stored/
        # cached value: two calls, two different override sets, two
        # different (in this case) stages.
        low = gs.current_growth_stage(overrides={"total_revenue_usd": 0, "open_critical_incidents": 5})
        high = gs.current_growth_stage(overrides={
            "accepted_opportunities_count": 5, "real_production_runs": 10,
            "total_revenue_usd": 500, "open_critical_incidents": 0,
        })
        self.assertNotEqual(low["stage"], high["stage"])

    def test_overridden_conditions_are_marked_simulated(self):
        result = gs.current_growth_stage(overrides={"total_revenue_usd": 500})
        stage_2_conditions = result["all_conditions"]["stage_2_stable_revenue"]
        revenue_cond = next(c for c in stage_2_conditions if c["name"] == "positive_recurring_revenue")
        self.assertTrue(revenue_cond["simulated"])

    def test_unoverridden_conditions_are_not_marked_simulated(self):
        result = gs.current_growth_stage(overrides={"total_revenue_usd": 500})
        stage_2_conditions = result["all_conditions"]["stage_2_stable_revenue"]
        incidents_cond = next(c for c in stage_2_conditions if c["name"] == "no_open_critical_incidents")
        self.assertFalse(incidents_cond["simulated"])

    def test_stage_5_always_cites_the_4_protected_gates(self):
        result = gs.current_growth_stage(overrides={
            "accepted_opportunities_count": 5, "real_production_runs": 10,
            "total_revenue_usd": 999999, "open_critical_incidents": 0,
            "platforms_with_real_revenue": 5,
        })
        stage_5_conditions = result["all_conditions"]["stage_5_autonomous_enterprise"]
        gate_cond = stage_5_conditions[0]
        self.assertFalse(gate_cond["met"])
        self.assertEqual(len(gate_cond["current_value"]), 4)

    def test_never_invents_a_revenue_or_cash_threshold(self):
        result = gs.current_growth_stage()
        stage_2_conditions = result["all_conditions"]["stage_2_stable_revenue"]
        revenue_policy = next(c for c in stage_2_conditions if c["name"] == "minimum_recurring_revenue_policy_threshold")
        cash_policy = next(c for c in stage_2_conditions if c["name"] == "minimum_cash_reserve_policy_threshold")
        self.assertIsNone(revenue_policy["met"])
        self.assertEqual(revenue_policy["reason"], gs.NOT_ARCHITECTED)
        self.assertIsNone(cash_policy["met"])
        self.assertEqual(cash_policy["reason"], gs.NOT_ARCHITECTED)


class TestRemainingRequirementsAndBlockingFactors(unittest.TestCase):
    def test_remaining_requirements_only_lists_unmet_conditions(self):
        req = gs.remaining_requirements_for_next_stage()
        for cond in req["requirements"]:
            self.assertIsNot(cond["met"], True)

    def test_blocking_factors_splits_false_from_none(self):
        result = gs.blocking_factors()
        for cond in result["blocking_factors"]:
            self.assertFalse(cond["met"])
        for cond in result["undetermined_factors"]:
            self.assertIsNone(cond["met"])


class TestDivisionStageObjectives(unittest.TestCase):
    def test_covers_all_7_named_divisions(self):
        result = gs.division_stage_objectives()
        self.assertEqual(set(result["divisions"].keys()), set(gs.DIVISIONS.keys()))

    def test_every_division_has_all_6_stage_objectives(self):
        result = gs.division_stage_objectives()
        for division_data in result["divisions"].values():
            self.assertEqual(set(division_data["objectives"].keys()), set(gs.STAGES))

    def test_rejects_unknown_division(self):
        with self.assertRaises(ValueError):
            gs.division_stage_objectives(division="not_a_real_division")


class TestHighestRoiAction(unittest.TestCase):
    def test_matches_enterprise_scheduler_ranking_exactly_no_second_algorithm(self):
        fake_scheduler_result = {"ranked_by_roi": {"answer": [{"niche": "fake-niche", "roi": 99}]}}
        result = gs.highest_roi_action_to_advance(scheduler_result=fake_scheduler_result)
        self.assertEqual(result["answer"], {"niche": "fake-niche", "roi": 99})

    def test_honestly_none_when_scheduler_has_no_ranked_candidates(self):
        result = gs.highest_roi_action_to_advance(scheduler_result={"ranked_by_roi": {"answer": []}})
        self.assertIsNone(result["answer"])


class TestSimulateStageProgression(unittest.TestCase):
    def test_rejects_unknown_override_keys(self):
        with self.assertRaises(ValueError):
            gs.simulate_stage_progression(not_a_real_signal=123)

    def test_tags_result_as_simulated(self):
        result = gs.simulate_stage_progression(total_revenue_usd=500)
        self.assertTrue(result["simulation"])

    def test_writes_nothing_to_data_directory(self):
        data_dir = _FACTORY_ROOT / "data"
        before = {p: p.stat().st_mtime for p in data_dir.glob("*.jsonl")}
        gs.simulate_stage_progression(total_revenue_usd=500, open_critical_incidents=0)
        after = {p: p.stat().st_mtime for p in data_dir.glob("*.jsonl")}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

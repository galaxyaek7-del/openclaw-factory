"""Tests for strategic_planning.py (Enterprise Strategic Planning System,
ADR-159, 2026-07-31): rolling roadmap, per-division status board,
Enterprise Priority Matrix, planning Q&A, and extended Executive
Timeline are all citation/relabeling layers over already-real
functions -- never a second planner or a second ranking algorithm.

    python -m unittest tests.test_strategic_planning -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import strategic_planning as sp
import growth_stages


class TestRollingRoadmap(unittest.TestCase):
    def test_covers_all_5_named_horizons(self):
        result = sp.rolling_roadmap()
        expected = {"today", "this_week", "this_month", "this_quarter", "this_year"}
        self.assertEqual(set(result.keys()) - {"generated_at"}, expected)

    def test_every_horizon_discloses_not_a_committed_date(self):
        result = sp.rolling_roadmap()
        for key in ("today", "this_week", "this_month", "this_quarter", "this_year"):
            self.assertEqual(result[key]["note"], sp.NOT_A_COMMITTED_DATE)

    def test_every_horizon_carries_a_real_source_citation(self):
        result = sp.rolling_roadmap()
        for key in ("today", "this_week", "this_month", "this_quarter", "this_year"):
            self.assertTrue(result[key]["source"])

    def test_accepts_injected_lifecycle_and_growth_no_recomputation(self):
        fake_lifecycle = {"real_buckets": {"run_now": [], "wait": [], "accelerate": [], "stop": [], "cancel": []}}
        fake_growth = {"remaining_requirements": {"requirements": []}}
        result = sp.rolling_roadmap(lifecycle=fake_lifecycle, growth=fake_growth)
        self.assertEqual(result["this_week"]["items"], [])
        self.assertEqual(result["this_month"]["items"], [])


class TestDivisionStatusBoard(unittest.TestCase):
    def test_covers_all_7_named_divisions(self):
        result = sp.division_status_board()
        self.assertEqual(set(result["divisions"].keys()), set(growth_stages.DIVISIONS.keys()))

    def test_estimated_completion_is_honestly_unknown(self):
        result = sp.division_status_board()
        for div in result["divisions"].values():
            self.assertIsNone(div["estimated_completion"]["value"])
            self.assertTrue(div["estimated_completion"]["reason"])

    def test_dependencies_honestly_none_where_no_taxonomy_match(self):
        result = sp.division_status_board()
        # affiliate_commerce and operations have no 1:1 match in gfos.py's
        # 12-department roster -- must never be force-mapped.
        self.assertIsNone(result["divisions"]["affiliate_commerce"]["dependencies"]["answer"])
        self.assertIsNone(result["divisions"]["operations"]["dependencies"]["answer"])

    def test_current_objectives_cite_growth_stages_module(self):
        result = sp.division_status_board()
        for div in result["divisions"].values():
            self.assertIn("growth_stages.py", div["current_objectives"]["source"])


class TestEnterprisePriorityMatrix(unittest.TestCase):
    def test_preserves_execution_status_report_order_exactly(self):
        fake_report = {
            "opportunities": [
                {"niche": "a", "priority": 90, "next_action": {"bucket": "run_now"}},
                {"niche": "b", "priority": 50, "next_action": {"bucket": "wait"}},
            ]
        }
        result = sp.enterprise_priority_matrix(report=fake_report)
        self.assertEqual([row["niche"] for row in result["matrix"]], ["a", "b"])

    def test_urgency_derived_from_scheduler_bucket(self):
        fake_report = {"opportunities": [
            {"niche": "a", "next_action": {"bucket": "run_now"}},
            {"niche": "b", "next_action": {"bucket": "accelerate"}},
            {"niche": "c", "next_action": {"bucket": "wait"}},
        ]}
        result = sp.enterprise_priority_matrix(report=fake_report)
        urgencies = {row["niche"]: row["urgency"]["answer"] for row in result["matrix"]}
        self.assertEqual(urgencies, {"a": "high", "b": "medium", "c": "low"})

    def test_technical_impact_honestly_none_no_expensive_per_niche_call(self):
        fake_report = {"opportunities": [{"niche": "a", "next_action": {"bucket": "wait"}}]}
        result = sp.enterprise_priority_matrix(report=fake_report)
        self.assertIsNone(result["matrix"][0]["technical_impact"]["value"])

    def test_never_a_second_ranking_algorithm(self):
        fake_report = {"opportunities": [{"niche": "a", "priority": 42, "next_action": {"bucket": "wait"}}]}
        result = sp.enterprise_priority_matrix(report=fake_report)
        self.assertEqual(result["matrix"][0]["priority_score"]["answer"], 42)


class TestAnswerPlanningQuestions(unittest.TestCase):
    def test_covers_all_4_named_questions(self):
        fake_strategic = {
            "what_should_be_built_next": {"answer": "X"}, "what_should_be_paused": {"answer": "Y"},
            "what_creates_the_highest_roi": {"answer": "Z"}, "which_bottleneck_blocks_future_scaling": {"answer": "W"},
        }
        fake_growth = {"what_blocks_the_next_stage": {"answer": "V"}}
        result = sp.answer_planning_questions(strategic_answers=fake_strategic, growth_answers=fake_growth)
        expected = {"what_should_the_company_build_next", "what_should_be_delayed",
                    "what_creates_the_highest_roi", "what_blocks_company_growth", "generated_at"}
        self.assertEqual(set(result.keys()), expected)

    def test_no_new_computation_pure_relabeling(self):
        fake_strategic = {
            "what_should_be_built_next": {"answer": "REAL_X"}, "what_should_be_paused": {"answer": "REAL_Y"},
            "what_creates_the_highest_roi": {"answer": "REAL_Z"}, "which_bottleneck_blocks_future_scaling": {"answer": "REAL_W"},
        }
        fake_growth = {"what_blocks_the_next_stage": {"answer": "REAL_V"}}
        result = sp.answer_planning_questions(strategic_answers=fake_strategic, growth_answers=fake_growth)
        self.assertEqual(result["what_should_the_company_build_next"]["answer"], "REAL_X")
        self.assertEqual(result["what_creates_the_highest_roi"]["answer"], "REAL_Z")
        self.assertEqual(result["what_blocks_company_growth"]["growth_stage_answer"]["answer"], "REAL_V")


class TestExecutiveTimelineExtended(unittest.TestCase):
    def test_growth_stage_history_reads_the_real_recorder(self):
        result = sp.executive_timeline_extended()
        self.assertIn("entries", result["growth_stage_history"])

    def test_major_architectural_decisions_filters_adr_events_only(self):
        fake_timeline = {"entries": [{"type": "adr", "summary": "x"}, {"type": "decision", "summary": "y"}]}
        fake_growth = {
            "current_stage": "stage_1_validation",
            "reason": {"conditions_met_for_current_stage": []},
            "remaining_requirements": {"next_stage": "stage_2_stable_revenue", "requirements": []},
        }
        result = sp.executive_timeline_extended(timeline=fake_timeline, growth_dashboard=fake_growth)
        self.assertEqual(len(result["major_architectural_decisions"]["answer"]), 1)
        self.assertEqual(result["major_architectural_decisions"]["answer"][0]["type"], "adr")


class TestGrowthStageSnapshotRecorder(unittest.TestCase):
    def test_recorder_is_additive_only(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "growth_stage_snapshots.jsonl")
            fake_stage_result = {"stage": "stage_1_validation", "stage_name": "Stage 1 — Validation"}
            growth_stages.record_growth_stage_snapshot(stage_result=fake_stage_result, snapshots_path=snap_path)
            history_1 = growth_stages.growth_stage_history(snapshots_path=snap_path)
            self.assertEqual(len(history_1["entries"]), 1)

            growth_stages.record_growth_stage_snapshot(stage_result=fake_stage_result, snapshots_path=snap_path)
            history_2 = growth_stages.growth_stage_history(snapshots_path=snap_path)
            self.assertEqual(len(history_2["entries"]), 2)
            # first entry untouched
            self.assertEqual(history_2["entries"][0], history_1["entries"][0])

    def test_history_honestly_empty_before_any_snapshot(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "does_not_exist.jsonl")
            result = growth_stages.growth_stage_history(snapshots_path=snap_path)
            self.assertEqual(result["entries"], [])
            self.assertTrue(result["reason"])


class TestSimulateRoadmapExecution(unittest.TestCase):
    def test_tags_result_as_simulated(self):
        result = sp.simulate_roadmap_execution(total_revenue_usd=500)
        self.assertTrue(result["simulation"])

    def test_rejects_unknown_override_keys(self):
        with self.assertRaises(ValueError):
            sp.simulate_roadmap_execution(not_a_real_signal=1)

    def test_writes_nothing_to_data_directory(self):
        data_dir = _FACTORY_ROOT / "data"
        before = {p: p.stat().st_mtime for p in data_dir.glob("*.jsonl")}
        sp.simulate_roadmap_execution(total_revenue_usd=500)
        after = {p: p.stat().st_mtime for p in data_dir.glob("*.jsonl")}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

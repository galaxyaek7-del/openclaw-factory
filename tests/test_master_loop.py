"""Tests for master_loop.py (Complete Autonomous Company Master Loop,
2026-07-24): pure orchestration/tracing over already-real modules --
zero new business logic, per the directive's own explicit rule.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files (except
mission_control_heartbeat()'s current_revenue field, which is
deliberately always real, matching mission_control_api._revenue()'s
own existing convention).

    python -m unittest tests.test_master_loop -v
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import master_loop as ml
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestTraceLifecycle(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.evidence_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.alerts_path, self.reopen_log_path,
                  self.evidence_path, self.timeline_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, ladder="ai_saas", score=85.0, price=250):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": price, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
            "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "test"},
            "market_signal": {"score": 60, "level": "مرتفعة", "note": "test"},
            "ai_leverage": {"score": 80, "level": "عالية", "note": "test"},
        }
        engine.record_ladder_decision(niche, ladder, ladder_result, decisions_path=self.decisions_path)

    def _trace(self, niche):
        return ml.trace_lifecycle(
            niche, decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._trace("never scored"))

    def test_all_20_named_stages_are_present_in_order(self):
        self._record("a full trace niche")
        trace = self._trace("a full trace niche")
        self.assertEqual(len(trace["stages"]), 20)
        names = [s["stage"] for s in trace["stages"]]
        self.assertEqual(names[0], "1_global_opportunity_discovery")
        self.assertEqual(names[-1], "20_next_opportunity_discovery")

    def test_every_stage_names_a_real_owning_module(self):
        self._record("an owner trace niche")
        trace = self._trace("an owner trace niche")
        for stage in trace["stages"]:
            self.assertTrue(stage["owner"])

    def test_fresh_decision_has_reached_early_stages_not_late_ones(self):
        self._record("a fresh trace niche")
        trace = self._trace("a fresh trace niche")
        by_name = {s["stage"]: s for s in trace["stages"]}
        self.assertTrue(by_name["3_executive_decision"]["reached"])
        self.assertFalse(by_name["12_automatic_publishing"]["reached"])
        self.assertFalse(by_name["14_sales_monitoring"]["reached"])

    def test_executive_learning_and_next_opportunity_are_honestly_factory_wide(self):
        """Stages 19-20 are real but not niche-specific -- reported as
        such (reached: None), never forced into a fabricated per-niche
        boolean."""
        self._record("a factory wide niche")
        trace = self._trace("a factory wide niche")
        by_name = {s["stage"]: s for s in trace["stages"]}
        self.assertIsNone(by_name["19_executive_learning"]["reached"])
        self.assertIsNone(by_name["20_next_opportunity_discovery"]["reached"])


class TestMissionControlHeartbeat(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.evidence_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.db_file = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.alerts_path, self.reopen_log_path,
                  self.evidence_path, self.timeline_path, self.outcomes_path, self.db_file):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, score):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": 200, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        engine.record_ladder_decision(niche, "ai_saas", ladder_result, decisions_path=self.decisions_path)

    def _heartbeat(self):
        with patch("mission_control_api._revenue", return_value={"real": "revenue"}):
            return ml.mission_control_heartbeat(
                decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
                reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
                timeline_path=self.timeline_path, outcomes_path=self.outcomes_path, db_file=self.db_file,
            )

    def test_all_6_named_fields_present(self):
        self._record("a heartbeat niche", 85.0)
        result = self._heartbeat()
        for field in ("current_opportunity", "current_product", "current_stage",
                      "current_revenue", "current_learning", "current_next_action", "company_reality_score"):
            self.assertIn(field, result)

    def test_empty_factory_has_honestly_no_current_opportunity(self):
        result = self._heartbeat()
        self.assertIsNone(result["current_opportunity"])
        self.assertTrue(result["current_opportunity_reason"])

    def test_current_opportunity_matches_schedulers_real_run_now_pick(self):
        self._record("low priority heartbeat", 40.0)
        self._record("high priority heartbeat", 95.0)
        result = self._heartbeat()
        self.assertEqual(result["current_opportunity"], "high priority heartbeat")
        self.assertIsNotNone(result["current_product"])
        self.assertIsNotNone(result["current_stage"])

    def test_current_revenue_reuses_real_mission_control_action(self):
        result = self._heartbeat()
        self.assertEqual(result["current_revenue"], {"real": "revenue"})


if __name__ == "__main__":
    unittest.main()

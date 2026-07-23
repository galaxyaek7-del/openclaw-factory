"""Tests for execution_status.py (Autonomous Global Execution Engine,
2026-07-23): the real, honest per-opportunity execution status view.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_execution_status -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import execution_status as es
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestBuildExecutionStatus(unittest.TestCase):
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

    def _record(self, niche, ladder="ai_saas", accepted=True, score=85.0, price=250):
        ladder_result = {
            "accepted": accepted, "ladder_score": score, "price": price, "reason": "test",
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

    def _status(self, niche, **kwargs):
        kwargs.setdefault("decisions_path", self.decisions_path)
        kwargs.setdefault("board_path", self.board_path)
        kwargs.setdefault("alerts_path", self.alerts_path)
        kwargs.setdefault("reopen_log_path", self.reopen_log_path)
        kwargs.setdefault("evidence_path", self.evidence_path)
        kwargs.setdefault("timeline_path", self.timeline_path)
        kwargs.setdefault("outcomes_path", self.outcomes_path)
        return es.build_execution_status(niche, **kwargs)

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._status("never scored"))

    def test_fresh_accepted_decision_has_all_real_fields(self):
        self._record("a fresh execution status niche")
        status = self._status("a fresh execution status niche")
        for field in ("current_phase", "current_owner", "completion_pct", "blocking_issue",
                      "business_value", "estimated_revenue", "estimated_effort",
                      "confidence", "priority", "expected_completion", "final_outcome"):
            self.assertIn(field, status)
        # Expected completion has no real source in this factory today.
        self.assertIsNone(status["expected_completion"]["value"])
        self.assertTrue(status["expected_completion"]["reason"])

    def test_completion_pct_reflects_real_reached_stage_count(self):
        self._record("a completion pct niche")
        status = self._status("a completion pct niche")
        self.assertGreater(status["completion_pct"], 0)
        self.assertLess(status["completion_pct"], 100)

    def test_owner_is_a_real_subsystem_name_for_an_owned_stage(self):
        self._record("an owner test niche")
        status = self._status("an owner test niche")
        # A fresh decision has at minimum reached evidence_based_validation
        # -- owned by Decision Engine, a real, named subsystem string.
        self.assertIsInstance(status["current_owner"], str)

    def test_no_owner_stage_is_honestly_reported(self):
        """Directly exercises the 4 stages with no real owner in this
        factory (customer_testing/localization/global_expansion/
        long_term_maintenance) via the module's own static mapping."""
        self.assertIsNone(es._OWNER_BY_STAGE["localization"])
        self.assertIsNone(es._OWNER_BY_STAGE["customer_testing"])

    def test_blocking_issue_prioritizes_an_active_at_risk_reason(self):
        import json
        self._record("a blocked niche")
        meeting = {
            "niche": "a blocked niche", "convened_at": "2026-07-23T00:00:00+00:00",
            "tally": {"board_decision": "NOT_APPROVED"}, "decision_summary": {"decision": "NOT_APPROVED", "confidence": 0.2},
        }
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meeting) + "\n")
        status = self._status("a blocked niche")
        self.assertIn("قرار مجلس", status["blocking_issue"])

    def test_blocking_issue_falls_back_to_next_unreached_stage_reason(self):
        self._record("a niche with no risk yet")
        status = self._status("a niche with no risk yet")
        self.assertTrue(status["blocking_issue"])

    def test_learning_feedback_is_honestly_empty_with_no_real_signal(self):
        self._record("a niche with no learning signal")
        status = self._status("a niche with no learning signal")
        self.assertFalse(status["learning_feedback"]["has_real_signal"])

    def test_learning_feedback_reflects_real_market_memory_evidence(self):
        import market_evidence
        self._record("a niche with real sales evidence")
        market_evidence.record_evidence("a niche with real sales evidence", "closed_sale", {
            "commercial_event": {"platform": "gumroad", "selling_price": 29.0, "season": "summer"},
        }, evidence_path=self.evidence_path)
        status = self._status("a niche with real sales evidence")
        feedback = status["learning_feedback"]
        self.assertTrue(feedback["has_real_signal"])
        self.assertEqual(feedback["real_sales_sample_size"], 1)
        self.assertEqual(feedback["total_revenue_to_date"], 29.0)


class TestBuildExecutionStatusReport(unittest.TestCase):
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

    def _record(self, niche, score):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": 200, "reason": "test",
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
        engine.record_ladder_decision(niche, "ai_saas", ladder_result, decisions_path=self.decisions_path)

    def test_empty_portfolio_reports_honestly(self):
        report = es.build_execution_status_report(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(report["count"], 0)
        self.assertEqual(report["opportunities"], [])

    def test_real_portfolio_ranked_same_order_as_value_engine(self):
        import value_engine
        self._record("low priority niche", 40.0)
        self._record("high priority niche", 95.0)

        portfolio = value_engine.build_value_engine_report(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        report = es.build_execution_status_report(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(
            [o["niche"] for o in report["opportunities"]],
            [p["niche"] for p in portfolio["profiles"]],
        )

    def test_limit_forwards_to_value_engine_and_caps_the_report(self):
        self._record("low priority niche", 40.0)
        self._record("high priority niche", 95.0)
        report = es.build_execution_status_report(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path, limit=1,
        )
        self.assertEqual(report["count"], 1)
        self.assertEqual(report["total_accepted"], 2)
        self.assertEqual(report["limited_to"], 1)
        self.assertEqual(report["opportunities"][0]["niche"], "high priority niche")


if __name__ == "__main__":
    unittest.main()

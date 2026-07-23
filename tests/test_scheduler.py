"""Tests for scheduler.py (Autonomous Global Execution Engine, 2026-07-23):
real, evidence-based 5-bucket classification (run_now / wait / accelerate
/ stop / cancel), on-demand only -- no live process, confirmed via
AskUserQuestion before this was built.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_scheduler -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import scheduler
import market_evidence
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestDecideNextActions(unittest.TestCase):
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

    def _record(self, niche, status="ACCEPTED", score=85.0):
        ladder_result = {
            "accepted": status == "ACCEPTED", "ladder_score": score, "price": 200, "reason": "test",
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

    def _decide(self):
        return scheduler.decide_next_actions(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )

    def test_empty_factory_reports_honestly(self):
        result = self._decide()
        self.assertEqual(result["counts"], {"run_now": 0, "wait": 0, "accelerate": 0, "stop": 0, "cancel": 0})

    def test_rejected_decision_is_cancelled(self):
        self._record("a rejected niche", status="REJECTED", score=10.0)
        result = self._decide()
        self.assertIn("a rejected niche", [c["niche"] for c in result["buckets"]["cancel"]])

    def test_board_rejection_is_cancelled_not_stopped(self):
        self._record("a board rejected niche")
        meeting = {
            "niche": "a board rejected niche", "convened_at": "2026-07-23T00:00:00+00:00",
            "tally": {"board_decision": "NOT_APPROVED"}, "decision_summary": {"decision": "NOT_APPROVED", "confidence": 0.2},
        }
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meeting) + "\n")
        result = self._decide()
        cancelled = [c["niche"] for c in result["buckets"]["cancel"]]
        stopped = [c["niche"] for c in result["buckets"]["stop"]]
        self.assertIn("a board rejected niche", cancelled)
        self.assertNotIn("a board rejected niche", stopped)

    def test_critical_alert_is_stopped_not_cancelled(self):
        import market_alerts
        self._record("a niche with a critical alert")
        alert = {
            "niche": "a niche with a critical alert", "event_type": "new_competitor_detected",
            "source": "manual", "evidence": {"competitor": "x"}, "severity": "Critical",
            "confidence": "high", "occurred_at": "2026-07-23T00:00:00+00:00", "dedupe_key": "k1",
        }
        market_alerts._append_alert(alert, alerts_path=self.alerts_path)
        result = self._decide()
        stopped = [c["niche"] for c in result["buckets"]["stop"]]
        cancelled = [c["niche"] for c in result["buckets"]["cancel"]]
        self.assertIn("a niche with a critical alert", stopped)
        self.assertNotIn("a niche with a critical alert", cancelled)

    def test_real_increase_investment_evidence_is_accelerated(self):
        for i in range(3):
            market_evidence.record_evidence("a proven niche", "closed_sale", {
                "commercial_event": {"platform": "gumroad", "selling_price": 20.0, "profit": 10.0, "season": "summer"},
            }, evidence_path=self.evidence_path)
        self._record("a proven niche")
        result = self._decide()
        self.assertIn("a proven niche", [c["niche"] for c in result["buckets"]["accelerate"]])

    def test_highest_priority_clean_opportunity_is_run_now_others_wait(self):
        self._record("low priority", score=40.0)
        self._record("high priority", score=95.0)
        result = self._decide()
        run_now = [c["niche"] for c in result["buckets"]["run_now"]]
        waiting = [c["niche"] for c in result["buckets"]["wait"]]
        self.assertEqual(run_now, ["high priority"])
        self.assertEqual(waiting, ["low priority"])

    def test_only_one_run_now_ever(self):
        self._record("a", score=95.0)
        self._record("b", score=94.0)
        self._record("c", score=93.0)
        result = self._decide()
        self.assertEqual(len(result["buckets"]["run_now"]), 1)


if __name__ == "__main__":
    unittest.main()

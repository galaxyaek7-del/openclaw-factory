"""Tests for factory_orchestrator.py (Galaxy Forge Architecture Review,
2026-07-22): the single real control point composing Executive Quality
Gate + AI Executive Board + Revenue Pipeline production.

Never writes to a real default data path -- every real-write call
(board_meetings) is redirected to a temp path and cleaned up.

    python -m unittest tests.test_factory_orchestrator -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from decision_engine import store
from decision_engine.types import Decision, make_decision_id

import factory_orchestrator as orch


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _accepted_decision(niche="a factory orchestrator test niche"):
    decided_at = "2026-07-16T10:00:00+00:00"
    return Decision(
        decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
        decided_at=decided_at, status="ACCEPTED", ai_ceo_decision="BUILD",
        opportunity_score=80.0, opportunity_score_accepted=True,
        reasoning=["real evidence"],
        evaluation_snapshot={"pricing": {"recommended_price": "$19", "note": "x"}},
    )


class TestFindDecision(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_no_decision_returns_none_honestly(self):
        self.assertIsNone(orch.find_decision("a niche nobody accepted", decisions_path=self.decisions_path))

    def test_real_decision_is_found(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        found = orch.find_decision(d.niche, decisions_path=self.decisions_path)
        self.assertIsNotNone(found)
        self.assertEqual(found["niche"], d.niche)


class TestRunMasterCycle(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.timeline_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_missing_decision_reports_honestly_not_an_exception(self):
        result = orch.run_master_cycle("nonexistent niche", decisions_path=self.decisions_path,
                                        board_path=self.board_path)
        self.assertFalse(result["success"])
        self.assertIn("reason", result)

    def test_real_decision_produces_quality_gate_and_board_meeting(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        result = orch.run_master_cycle(d.niche, decisions_path=self.decisions_path, board_path=self.board_path)
        self.assertTrue(result["success"])
        self.assertIn("criteria", result["quality_gate"])
        self.assertIn("tally", result["board_meeting"])
        self.assertIsNone(result["production_result"])  # execute=False by default

    def test_advisory_only_default_never_blocks_execute(self):
        """The explicit 2026-07-22 architecture decision: advisory_only=True
        is the default, so a real board rejection never silently freezes
        production -- production only depends on execute=True itself."""
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        with patch("revenue_pipeline.pipeline.process_opportunity") as mock_process:
            mock_process.return_value = {"executed": True, "niche": d.niche}
            result = orch.run_master_cycle(
                d.niche, execute=True, decisions_path=self.decisions_path, board_path=self.board_path,
                timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
            )
        self.assertFalse(result["board_blocks_production"])
        self.assertTrue(mock_process.called)
        self.assertIsNotNone(result["production_result"])

    def test_enforced_board_blocks_execute_on_a_real_rejection(self):
        """advisory_only=False: a real NOT_APPROVED board tally must
        actually prevent revenue_pipeline.process_opportunity() from
        being called at all."""
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        with patch("executive_board.convene_board") as mock_convene, \
             patch("revenue_pipeline.pipeline.process_opportunity") as mock_process:
            mock_convene.return_value = {
                "niche": d.niche, "tally": {"board_decision": "NOT_APPROVED", "approve_count": 2,
                                            "reject_count": 4, "defer_count": 4, "total": 10},
                "executives": [],
            }
            result = orch.run_master_cycle(
                d.niche, execute=True, advisory_only=False, decisions_path=self.decisions_path,
                board_path=self.board_path,
            )
        self.assertTrue(result["board_blocks_production"])
        self.assertFalse(mock_process.called)
        self.assertFalse(result["production_result"]["executed"])

    def test_never_writes_a_permanent_board_meeting_when_given_a_temp_path(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        orch.run_master_cycle(d.niche, decisions_path=self.decisions_path, board_path=self.board_path)
        self.assertTrue(os.path.exists(self.board_path))
        with open(self.board_path, encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()

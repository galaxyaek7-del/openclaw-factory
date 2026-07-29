"""Tests for founder_console.py (EOS Phase 1, 2026-07-19): the
Python-side half of the Founder Console (blocked channels + DEFERRED
decisions).

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/decisions.jsonl.

    python -m unittest tests.test_founder_console -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from decision_engine import store
from decision_engine.types import Decision, make_decision_id

import founder_console


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


def _decision(niche, status):
    decided_at = datetime.now(timezone.utc).isoformat()
    return Decision(
        decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
        decided_at=decided_at, status=status, ai_ceo_decision="WAIT",
        opportunity_score=70, opportunity_score_accepted=(status == "ACCEPTED"),
        reasoning=["real reason"], evaluation_snapshot={},
    )


class TestBuildFounderQueuePartial(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    @patch("commercial_execution.approval_gates.check_approval_gates")
    def test_merges_gated_channels_and_deferred_decisions(self, mock_gates):
        mock_gates.return_value = {
            "gated": [{"marketplace": "gumroad", "status": "unavailable", "reason": "no API key"}],
            "autonomous": [{"marketplace": "paddle", "status": "ready"}],
        }
        store.append_decision(_decision("deferred niche", "DEFERRED"), path=self.decisions_path)
        store.append_decision(_decision("accepted niche", "ACCEPTED"), path=self.decisions_path)

        result = founder_console.build_founder_queue_partial(
            decisions_path=self.decisions_path,
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
            publish_protection_state_path="C:/definitely/not/a/real/publish_protection_state.json",
        )
        self.assertEqual(len(result["blocked_channels"]), 1)
        self.assertEqual(result["blocked_channels"][0]["marketplace"], "gumroad")
        self.assertEqual(len(result["autonomous_channels"]), 1)
        self.assertEqual(len(result["pending_decisions"]), 1)
        self.assertEqual(result["pending_decisions"][0]["niche"], "deferred niche")

    @patch("commercial_execution.approval_gates.check_approval_gates")
    def test_no_deferred_decisions_is_honestly_empty(self, mock_gates):
        mock_gates.return_value = {"gated": [], "autonomous": []}
        store.append_decision(_decision("accepted niche", "ACCEPTED"), path=self.decisions_path)
        result = founder_console.build_founder_queue_partial(
            decisions_path=self.decisions_path,
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
            publish_protection_state_path="C:/definitely/not/a/real/publish_protection_state.json",
        )
        self.assertEqual(result["pending_decisions"], [])

    @patch("commercial_execution.approval_gates.check_approval_gates")
    def test_pending_evolution_proposals_reflects_real_queue_state(self, mock_gates):
        """Autonomous Company Evolution Engine, Round 6 (2026-07-29)."""
        mock_gates.return_value = {"gated": [], "autonomous": []}
        import evolution_queue
        queue_path = _temp_path().replace(".jsonl", ".json")
        try:
            evolution_queue.run_daily_cycle(
                proposals=[{
                    "id": "p1", "tool": "Test tool", "status": "مقترَح، لا تنفيذ",
                    "why_needed": "a real reason", "expected_business_value": "a real value",
                    "implementation_effort": "low", "estimated_roi": "unmeasured",
                    "dependencies": ["a real dependency"], "risks": ["a real risk"],
                    "evidence": "some_module.py's some_function()",
                }],
                state_path=queue_path,
            )
            result = founder_console.build_founder_queue_partial(
                decisions_path=self.decisions_path, evolution_queue_state_path=queue_path,
                publish_protection_state_path="C:/definitely/not/a/real/publish_protection_state.json",
            )
            self.assertEqual(len(result["pending_evolution_proposals"]), 1)
            self.assertEqual(result["pending_evolution_proposals"][0]["proposal_id"], "p1")
        finally:
            if os.path.exists(queue_path):
                os.remove(queue_path)

    @patch("commercial_execution.approval_gates.check_approval_gates")
    def test_publish_emergency_stop_reflects_real_protection_state(self, mock_gates):
        """Global Commercial Hardening, Phase 1 (2026-07-29)."""
        mock_gates.return_value = {"gated": [], "autonomous": []}
        from channels import publish_protection
        protection_path = _temp_path().replace(".jsonl", ".json")
        try:
            publish_protection.trigger_emergency_stop("suspicious pattern", triggered_by="founder", state_path=protection_path)
            result = founder_console.build_founder_queue_partial(
                decisions_path=self.decisions_path,
                evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
                publish_protection_state_path=protection_path,
            )
            self.assertIsNotNone(result["publish_emergency_stop"])
            self.assertEqual(result["publish_emergency_stop"]["emergency_reason"], "suspicious pattern")
        finally:
            if os.path.exists(protection_path):
                os.remove(protection_path)

    @patch("commercial_execution.approval_gates.check_approval_gates")
    def test_no_emergency_stop_is_honestly_none(self, mock_gates):
        mock_gates.return_value = {"gated": [], "autonomous": []}
        result = founder_console.build_founder_queue_partial(
            decisions_path=self.decisions_path,
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
            publish_protection_state_path="C:/definitely/not/a/real/publish_protection_state.json",
        )
        self.assertIsNone(result["publish_emergency_stop"])

    def test_real_call_against_real_data_never_throws(self):
        result = founder_console.build_founder_queue_partial()
        self.assertIn("blocked_channels", result)
        self.assertIn("pending_decisions", result)
        self.assertIn("pending_evolution_proposals", result)
        self.assertIn("publish_emergency_stop", result)


if __name__ == "__main__":
    unittest.main()

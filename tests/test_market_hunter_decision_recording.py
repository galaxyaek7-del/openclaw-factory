"""Tests for market_hunter.py's write side of the single source of truth
(ADR-076, Decision Surface Reconciliation). Every real candidate
hunt_market() scans must be recorded into decision_engine's own store —
the same file mission_control_api.py/decision_engine.ranking read.

    python -m unittest tests.test_market_hunter_decision_recording -v
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

import market_hunter as mh
from decision_engine import store


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestHuntMarketRecordsToSharedDecisionStore(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_every_actually_scored_candidate_is_recorded_regardless_of_accept_reject(self):
        from decision_engine.engine import record_ladder_decision

        def _record_to_temp_path(niche, ladder, scored):
            return record_ladder_decision(niche, ladder, scored, decisions_path=self.decisions_path)

        with patch.object(mh, "RECORD_LADDER_DECISION", _record_to_temp_path):
            result = mh.hunt_market(limit=3, write_opportunities=False)

        # A candidate blocked by the Knowledge Brain (REJECTED_NICHES.md/
        # QUARANTINE.md) or a scoring error never reaches profit_oracle at
        # all, so it correctly has no ladder_score and is correctly never
        # recorded — count against entries that were ACTUALLY scored, not
        # every scanned entry (some of which were never real candidates
        # for decision_engine to record in the first place).
        actually_scored = [e for e in result["scanned"] if "ladder_score" in e]
        recorded = list(store.read_decisions(path=self.decisions_path))
        self.assertGreater(len(actually_scored), 0, "test setup should produce at least one real scoreable candidate")
        self.assertEqual(len(recorded), len(actually_scored), "every actually-scored candidate must be recorded, accepted or not")

    def test_a_recording_failure_never_blocks_the_real_hunt(self):
        with patch.object(mh, "RECORD_LADDER_DECISION", side_effect=RuntimeError("store unavailable")):
            result = mh.hunt_market(limit=1, write_opportunities=False)
        self.assertIn("scanned_count", result)
        self.assertGreater(result["scanned_count"], 0)

    def test_recording_disabled_entirely_never_crashes(self):
        with patch.object(mh, "RECORD_LADDER_DECISION", None):
            result = mh.hunt_market(limit=1, write_opportunities=False)
        self.assertIn("scanned_count", result)


if __name__ == "__main__":
    unittest.main()

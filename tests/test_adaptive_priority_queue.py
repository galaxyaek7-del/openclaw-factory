"""Tests for adaptive_priority_queue.py (ADR-206, Phase 16, 2026-08-08).
No live executive_brain call is made -- eos_decision_feed.build_eos_
decision_feed is patched with a fake, fast, real-shaped card set.

    python -m unittest tests.test_adaptive_priority_queue -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import adaptive_priority_queue as apq
import eos_decision_feed


_FAKE_FEED = {
    "recommendations": [
        {
            "problem": "Real candidate opportunity not yet built: test niche",
            "evidence": ["source_a", "source_b"],
            "business_impact": "high",
            "financial_impact": {"value": 100},
            "confidence": "medium",
            "recommended_action": "build it",
            "estimated_roi": {"value": 50},
            "time_to_execute": "2 weeks",
            "priority": "Tier 2",
            "source": "goos.rank_build_candidates()",
            "consequence_of_inaction": "state continues",
        },
    ],
    "total": 1,
    "note": "test",
}


class TestBuildAdaptivePriorityQueue(unittest.TestCase):
    def test_all_12_named_fields_present(self):
        with patch.object(eos_decision_feed, "build_eos_decision_feed", return_value=_FAKE_FEED):
            r = apq.build_adaptive_priority_queue()
        expected = {
            "priority", "type", "evidence", "expected_value", "actual_value", "risk",
            "confidence", "required_resources", "recommended_action", "owner", "status", "last_evaluation",
        }
        self.assertTrue(expected.issubset(r["queue"][0].keys()))

    def test_actual_value_never_backfilled_from_expected_value(self):
        with patch.object(eos_decision_feed, "build_eos_decision_feed", return_value=_FAKE_FEED):
            r = apq.build_adaptive_priority_queue()
        item = r["queue"][0]
        self.assertEqual(item["actual_value"]["status"], "NOT_YET_MEASURED")
        self.assertNotEqual(item["actual_value"], item["expected_value"])

    def test_type_inferred_from_source(self):
        with patch.object(eos_decision_feed, "build_eos_decision_feed", return_value=_FAKE_FEED):
            r = apq.build_adaptive_priority_queue()
        self.assertEqual(r["queue"][0]["type"], "opportunity")

    def test_weak_evidence_flagged_for_thin_evidence(self):
        thin_feed = {"recommendations": [dict(_FAKE_FEED["recommendations"][0], evidence=[])], "total": 1, "note": "t"}
        with patch.object(eos_decision_feed, "build_eos_decision_feed", return_value=thin_feed):
            r = apq.build_adaptive_priority_queue()
        self.assertTrue(r["queue"][0]["weak_evidence"])

    def test_owner_is_the_real_documented_single_operator(self):
        with patch.object(eos_decision_feed, "build_eos_decision_feed", return_value=_FAKE_FEED):
            r = apq.build_adaptive_priority_queue()
        self.assertIn("Founder", r["queue"][0]["owner"])

    def test_reuses_eos_decision_feed_never_recomputes(self):
        with patch.object(eos_decision_feed, "build_eos_decision_feed", return_value=_FAKE_FEED) as mock_feed:
            apq.build_adaptive_priority_queue()
        mock_feed.assert_called_once()


if __name__ == "__main__":
    unittest.main()

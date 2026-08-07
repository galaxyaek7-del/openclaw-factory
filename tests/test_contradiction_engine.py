"""Tests for contradiction_engine.py (ADR-208, Phase 18, 2026-08-08).
No live Paddle API call is made in these tests -- detect_price_
contradiction() is tested with live_check=False or a mocked network call.

    python -m unittest tests.test_contradiction_engine -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import contradiction_engine as ce


def _write_decisions(tmp, records):
    path = os.path.join(tmp, "decisions.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


class TestDetectDecisionVolatility(unittest.TestCase):
    def test_no_contradiction_below_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_decisions(tmp, [
                {"niche": "n1", "opportunity_score": 50, "status": "DEFERRED", "decision_id": "d1"},
                {"niche": "n1", "opportunity_score": 55, "status": "DEFERRED", "decision_id": "d2"},
            ])
            result = ce.detect_decision_volatility(decisions_path=path)
            self.assertEqual(result, [])

    def test_contradiction_above_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_decisions(tmp, [
                {"niche": "n1", "opportunity_score": 20, "status": "DEFERRED", "decision_id": "d1", "decided_at": "t1"},
                {"niche": "n1", "opportunity_score": 80, "status": "DEFERRED", "decision_id": "d2", "decided_at": "t2"},
            ])
            result = ce.detect_decision_volatility(decisions_path=path)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["category"], "conflicting_market_estimate")
            self.assertEqual(result[0]["spread"], 60.0)

    def test_never_picks_a_winner_both_sources_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_decisions(tmp, [
                {"niche": "n1", "opportunity_score": 20, "status": "DEFERRED", "decision_id": "d1", "decided_at": "t1"},
                {"niche": "n1", "opportunity_score": 80, "status": "DEFERRED", "decision_id": "d2", "decided_at": "t2"},
            ])
            result = ce.detect_decision_volatility(decisions_path=path)
            self.assertEqual(len(result[0]["sources"]), 2)
            self.assertTrue(result[0]["requires_verification"])

    def test_status_flip_flop_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_decisions(tmp, [
                {"niche": "n1", "status": "ACCEPTED", "decision_id": "d1"},
                {"niche": "n1", "status": "REJECTED", "decision_id": "d2"},
            ])
            result = ce.detect_decision_volatility(decisions_path=path)
            categories = {c["category"] for c in result}
            self.assertIn("contradictory_strategic_conclusion", categories)

    def test_single_evaluation_never_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_decisions(tmp, [{"niche": "n1", "opportunity_score": 90, "status": "ACCEPTED", "decision_id": "d1"}])
            result = ce.detect_decision_volatility(decisions_path=path)
            self.assertEqual(result, [])

    def test_missing_file_is_honestly_empty(self):
        result = ce.detect_decision_volatility(decisions_path="C:/definitely/not/real.jsonl")
        self.assertEqual(result, [])


class TestDetectPriceContradiction(unittest.TestCase):
    def test_not_found_when_product_missing(self):
        with patch.object(ce, "_PADDLE_PRODUCTS_PATH", Path("C:/definitely/not/real.json")):
            result = ce.detect_price_contradiction("Some Product")
            self.assertEqual(result["status"], "NOT_FOUND")

    def test_live_check_false_skips_network_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "paddle_products.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump([{"title": "X", "price": 100, "price_id": "pri_1"}], f)
            with patch.object(ce, "_PADDLE_PRODUCTS_PATH", Path(path)):
                result = ce.detect_price_contradiction("X", live_check=False)
            self.assertEqual(result["status"], "SKIPPED")


class TestDetectAllContradictions(unittest.TestCase):
    def test_aggregates_without_price_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_decisions(tmp, [
                {"niche": "n1", "opportunity_score": 20, "status": "DEFERRED", "decision_id": "d1"},
                {"niche": "n1", "opportunity_score": 80, "status": "DEFERRED", "decision_id": "d2"},
            ])
            result = ce.detect_all_contradictions(decisions_path=path, check_prices=False)
            self.assertEqual(result["total_contradictions"], 1)
            self.assertEqual(result["price_checks_performed"], 0)


if __name__ == "__main__":
    unittest.main()

"""Tests for market_intelligence_core/market_review.py (EOS Phase 1,
2026-07-19): the weekly Market Review, the last genuinely-missing
Continuous Improvement Engine review type.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_market_review -v
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from market_intelligence_core import market_review


def _write_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


class TestScanSummary(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            if os.path.exists(p):
                os.remove(p)

    def test_counts_distinct_niches_within_the_window_only(self):
        now = datetime(2026, 7, 20, tzinfo=timezone.utc)
        events = [
            {"action": "attempted", "niche": "a", "timestamp": (now - timedelta(days=1)).isoformat()},
            {"action": "skipped", "niche": "b", "timestamp": (now - timedelta(days=2)).isoformat()},
            {"action": "attempted", "niche": "a", "timestamp": (now - timedelta(days=3)).isoformat()},  # same niche again
            {"action": "attempted", "niche": "c", "timestamp": (now - timedelta(days=20)).isoformat()},  # too old
            {"action": "n8n_notify", "niche": "d", "timestamp": (now - timedelta(days=1)).isoformat()},  # not a scan action
        ]
        path = _write_jsonl(events)
        self._paths = [path]
        result = market_review._scan_summary(7, now, path)
        self.assertEqual(result["niches_scanned"], 2)  # a, b only

    def test_missing_file_returns_honest_zero(self):
        result = market_review._scan_summary(7, datetime.now(timezone.utc), "/no/such/file.jsonl")
        self.assertEqual(result["niches_scanned"], 0)


class TestOpportunityTrend(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            if os.path.exists(p):
                os.remove(p)

    def test_no_real_data_returns_unknown_honestly(self):
        result = market_review._opportunity_trend(7, datetime.now(timezone.utc), "/no/such/file.jsonl")
        self.assertEqual(result["answer"], "Unknown")

    def test_period_vs_all_time_averages_computed_correctly(self):
        now = datetime(2026, 7, 20, tzinfo=timezone.utc)
        analyses = [
            {"opportunity_gap": 80, "customer_pain": {"pain_score": 40}, "analyzed_at": (now - timedelta(days=1)).isoformat()},
            {"opportunity_gap": 60, "customer_pain": {"pain_score": 20}, "analyzed_at": (now - timedelta(days=20)).isoformat()},
        ]
        path = _write_jsonl(analyses)
        self._paths = [path]
        result = market_review._opportunity_trend(7, now, path)
        self.assertEqual(result["period_avg_opportunity_gap"], 80)
        self.assertEqual(result["all_time_avg_opportunity_gap"], 70.0)
        self.assertEqual(result["period_sample_size"], 1)
        self.assertEqual(result["all_time_sample_size"], 2)


class TestGenerateMarketReview(unittest.TestCase):
    def test_real_call_against_real_data_never_throws(self):
        report = market_review.generate_market_review()
        self.assertIn("scan_summary", report)
        self.assertIn("opportunity_trend", report)
        self.assertIn("top_rejection_reasons", report)

    def test_render_markdown_handles_unknown_trend_honestly(self):
        report = {
            "period_days": 7,
            "scan_summary": {"niches_scanned": 0, "source": "x"},
            "opportunity_trend": {"answer": "Unknown", "reason": "no data"},
            "top_rejection_reasons": {"answer": "Unknown", "reason": "no data"},
        }
        md = market_review.render_markdown(report)
        self.assertIn("غير متاح", md)

    def test_render_markdown_real_shape(self):
        report = {
            "period_days": 7,
            "scan_summary": {"niches_scanned": 5, "source": "x"},
            "opportunity_trend": {
                "period_avg_opportunity_gap": 70, "all_time_avg_opportunity_gap": 65,
                "period_avg_pain_score": 30, "all_time_avg_pain_score": 25,
                "period_sample_size": 5, "all_time_sample_size": 50,
            },
            "top_rejection_reasons": {"answer": "REJECT", "counts": {"REJECT": 3}, "total_rejected": 3},
        }
        md = market_review.render_markdown(report)
        self.assertIn("70", md)
        self.assertIn("REJECT", md)


if __name__ == "__main__":
    unittest.main()

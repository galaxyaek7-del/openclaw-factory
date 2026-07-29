"""Tests for department_health.py (EOS Phase 2, 2026-07-19): pure
assembly of already-computed real health signals per named department.

Runs with stdlib unittest.

    python -m unittest tests.test_department_health -v
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

import department_health as dh


def _write_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


class TestRecentActivityCount(unittest.TestCase):
    def test_counts_only_within_the_window(self):
        now = datetime(2026, 7, 20, tzinfo=timezone.utc)
        events = [
            {"timestamp": (now - timedelta(days=1)).isoformat()},
            {"timestamp": (now - timedelta(days=20)).isoformat()},
        ]
        count = dh.recent_activity_count(events, days=7, now=now)
        self.assertEqual(count, 1)

    def test_missing_timestamp_never_throws(self):
        count = dh.recent_activity_count([{"no_timestamp": True}])
        self.assertEqual(count, 0)


class TestEngineDepartment(unittest.TestCase):
    def test_discovery_maturity_reports_none_honestly(self):
        health = {"production": {"maturity": "DISCOVERY", "reason": "no data"}}
        result = dh._engine_department(health, "production")
        self.assertEqual(result["data_source"], "none")

    def test_real_maturity_reports_real_fields(self):
        health = {"production": {"maturity": "REAL", "success_rate": 90.0, "total_executions": 10, "last_status": "SUCCESS", "last_run_at": "t"}}
        result = dh._engine_department(health, "production")
        self.assertEqual(result["data_source"], "real")
        self.assertEqual(result["success_rate"], 90.0)


class TestBuildDepartmentHealth(unittest.TestCase):
    def test_real_call_never_throws_and_covers_every_department(self):
        report = dh.build_department_health()
        for dept in ("executive", "market_intelligence", "golden_hunter", "pioneer", "researchers",
                     "production", "publishing", "finance", "customer_intelligence",
                     "infrastructure", "recovery", "ai_capability_manager"):
            self.assertIn(dept, report)

    def test_researchers_and_customer_intelligence_are_honestly_none(self):
        report = dh.build_department_health()
        self.assertEqual(report["researchers"]["data_source"], "none")
        self.assertEqual(report["customer_intelligence"]["data_source"], "none")

    def test_render_markdown_never_throws(self):
        report = dh.build_department_health()
        md = dh.render_markdown(report)
        self.assertIsInstance(md, str)
        self.assertIn("صحة الأقسام", md)


class TestRankDepartmentWeakness(unittest.TestCase):
    """Executive Intelligence Core, Round 4 (2026-07-29)."""

    def test_no_data_departments_are_bucketed_with_their_real_reason(self):
        report = {
            "researchers": {"data_source": "none", "reason": "غير مؤتمَت بعد"},
            "production": {"data_source": "real", "success_rate": 95.0},
        }
        result = dh.rank_department_weakness(report=report)
        self.assertEqual(result["no_data"], [{"department": "researchers", "reason": "غير مؤتمَت بعد"}])
        self.assertEqual(result["healthy"], ["production"])
        self.assertEqual(result["below_threshold"], [])

    def test_low_success_rate_is_flagged_below_threshold_not_healthy(self):
        report = {
            "production": {"data_source": "real", "success_rate": 50.0},
            "finance": {"data_source": "real", "recorded_sales": 3},  # no success_rate field at all
        }
        result = dh.rank_department_weakness(report=report)
        self.assertEqual(result["below_threshold"], [{"department": "production", "success_rate": 50.0}])
        self.assertEqual(result["healthy"], ["finance"])

    def test_weakest_combines_no_data_and_below_threshold_only(self):
        report = {
            "a": {"data_source": "none", "reason": "r"},
            "b": {"data_source": "real", "success_rate": 10.0},
            "c": {"data_source": "real", "success_rate": 99.0},
        }
        result = dh.rank_department_weakness(report=report)
        weakest_names = {w.get("department") for w in result["weakest"]}
        self.assertEqual(weakest_names, {"a", "b"})

    def test_never_computes_a_single_blended_score(self):
        # The real, standing rule this module documents -- no key named
        # anything like "score"/"rank"/"index" should ever appear.
        report = dh.build_department_health()
        result = dh.rank_department_weakness(report=report)
        for forbidden in ("score", "rank", "index"):
            self.assertNotIn(forbidden, result)

    def test_real_call_never_throws(self):
        result = dh.rank_department_weakness()
        for key in ("no_data", "below_threshold", "healthy", "weakest"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

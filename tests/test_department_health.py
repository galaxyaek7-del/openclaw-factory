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


if __name__ == "__main__":
    unittest.main()

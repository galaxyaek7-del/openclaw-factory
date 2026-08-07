"""Tests for knowledge_decay.py (ADR-208, Phase 18, 2026-08-08).

    python -m unittest tests.test_knowledge_decay -v
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import knowledge_decay as kd


class TestCheckStaleness(unittest.TestCase):
    def test_fresh_within_threshold(self):
        now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        result = kd.check_staleness("2026-08-01", "pricing", now=now)
        self.assertEqual(result["status"], "FRESH")
        self.assertEqual(result["age_days"], 7)

    def test_stale_beyond_threshold(self):
        now = datetime(2026, 12, 1, tzinfo=timezone.utc)
        result = kd.check_staleness("2026-08-01", "pricing", now=now)
        self.assertEqual(result["status"], "STALE")

    def test_unknown_category_honestly_unknown(self):
        result = kd.check_staleness("2026-08-01", "not_a_real_category")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_unparseable_date_honestly_unknown(self):
        result = kd.check_staleness("not-a-date", "pricing")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_exactly_at_threshold_is_not_yet_stale(self):
        now = datetime(2026, 8, 31, tzinfo=timezone.utc)  # 30 days after 2026-08-01
        result = kd.check_staleness("2026-08-01", "pricing", now=now)
        self.assertEqual(result["status"], "FRESH")


class TestAssessAllKnownKnowledge(unittest.TestCase):
    def test_all_known_checks_run(self):
        r = kd.assess_all_known_knowledge()
        self.assertEqual(r["total_checked"], len(kd.KNOWN_STALENESS_CHECKS))

    def test_far_future_now_flags_everything_stale(self):
        far_future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        r = kd.assess_all_known_knowledge(now=far_future)
        self.assertEqual(r["stale_count"], len(kd.KNOWN_STALENESS_CHECKS))

    def test_every_check_cites_a_real_source(self):
        r = kd.assess_all_known_knowledge()
        for check in r["checks"]:
            self.assertIn("source", check)
            self.assertGreater(len(check["source"]), 10)


if __name__ == "__main__":
    unittest.main()

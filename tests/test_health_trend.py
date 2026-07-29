"""Tests for health_trend.py (Global Trust & Resilience Layer, Round 1,
2026-07-29): the Python-side mirror of lib/health_trend.js's real
detection logic.

Runs with stdlib unittest. Never touches the real
data/health_snapshots.jsonl -- every test passes an explicit temp path.

    python -m unittest tests.test_health_trend -v
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

import health_trend as ht


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


def _write_snapshots(path, statuses):
    with open(path, 'w', encoding='utf-8') as f:
        for s in statuses:
            f.write(json.dumps({"at": "2026-07-29T00:00:00Z", "status": s}) + "\n")


class BaseHealthTrendTest(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class TestReadHealthSnapshots(BaseHealthTrendTest):
    def test_missing_file_is_honestly_empty(self):
        # _temp_path() in setUp already ensures the file does not exist.
        self.assertEqual(ht.read_health_snapshots(self.path), [])

    def test_corrupt_line_is_skipped_never_crashes(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write('{"at":"x","status":"healthy"}\n')
            f.write('not valid json\n')
            f.write('{"at":"y","status":"degraded"}\n')
        entries = ht.read_health_snapshots(self.path)
        self.assertEqual(len(entries), 2)


class TestDetectHealthDegradation(BaseHealthTrendTest):
    def test_fewer_than_window_size_is_honestly_not_degrading(self):
        _write_snapshots(self.path, ["critical"])
        result = ht.detect_health_degradation(self.path, window_size=3)
        self.assertFalse(result["degrading"])
        self.assertIn("أقل من", result["reason"])

    def test_strictly_worsening_trend_is_flagged(self):
        _write_snapshots(self.path, ["healthy", "degraded", "critical"])
        result = ht.detect_health_degradation(self.path, window_size=3)
        self.assertTrue(result["degrading"])
        self.assertIn("تزداد سوءاً", result["reason"])

    def test_sustained_unhealthy_is_flagged_even_without_worsening(self):
        _write_snapshots(self.path, ["degraded", "critical", "degraded"])
        result = ht.detect_health_degradation(self.path, window_size=3)
        self.assertTrue(result["degrading"])
        self.assertIn("غير سليمة", result["reason"])

    def test_stable_healthy_history_is_honestly_not_degrading(self):
        _write_snapshots(self.path, ["healthy", "healthy", "healthy"])
        result = ht.detect_health_degradation(self.path, window_size=3)
        self.assertFalse(result["degrading"])

    def test_invalid_status_in_window_is_honestly_not_degrading(self):
        _write_snapshots(self.path, ["healthy", "not_a_real_status", "critical"])
        result = ht.detect_health_degradation(self.path, window_size=3)
        self.assertFalse(result["degrading"])


if __name__ == "__main__":
    unittest.main()

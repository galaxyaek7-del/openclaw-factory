"""Tests for learning_log.py (Cycle 82, item 5 -- weekly learning loop).

    python -m unittest tests.test_learning_log -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import learning_log


class _TempFileMixin:
    def setUp(self):
        self._tmp_paths = []

    def tearDown(self):
        for p in self._tmp_paths:
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass

    def _tmp(self, suffix):
        path = Path(tempfile.mktemp(suffix=suffix))
        self._tmp_paths.append(path)
        return path


class TestRecordWeeklyLearningEntry(_TempFileMixin, unittest.TestCase):
    def test_rejects_a_variable_not_in_the_named_three(self):
        with self.assertRaises(ValueError):
            learning_log.record_weekly_learning_entry(
                week_label="2026-W43",
                hypothesis="a real hypothesis",
                variable_changed="platform",  # not one of headline/price/post_type
                change_description="switched from Facebook to TikTok",
                funnel_snapshot={},
                log_path=self._tmp(".jsonl"),
            )

    def test_rejects_empty_hypothesis(self):
        with self.assertRaises(ValueError):
            learning_log.record_weekly_learning_entry(
                week_label="2026-W43",
                hypothesis="   ",
                variable_changed="headline",
                change_description="x",
                funnel_snapshot={},
                log_path=self._tmp(".jsonl"),
            )

    def test_accepts_each_of_the_three_named_variables(self):
        path = self._tmp(".jsonl")
        for var in ("headline", "price", "post_type"):
            entry = learning_log.record_weekly_learning_entry(
                week_label="2026-W43",
                hypothesis=f"changing {var} will improve clicks",
                variable_changed=var,
                change_description="real description",
                funnel_snapshot={"clicks": 0},
                log_path=path,
            )
            self.assertEqual(entry["variable_changed"], var)

    def test_real_entry_round_trips_through_list_learning_entries(self):
        path = self._tmp(".jsonl")
        learning_log.record_weekly_learning_entry(
            week_label="2026-W43",
            hypothesis="a shorter headline raises clicks",
            variable_changed="headline",
            change_description="shortened post #1's headline",
            funnel_snapshot={"clicks": 12},
            result=None,
            log_path=path,
        )
        entries = learning_log.list_learning_entries(log_path=path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["week_label"], "2026-W43")
        self.assertEqual(entries[0]["funnel_snapshot"], {"clicks": 12})

    def test_missing_log_file_reads_empty_not_fabricated(self):
        entries = learning_log.list_learning_entries(log_path=self._tmp(".jsonl"))
        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()

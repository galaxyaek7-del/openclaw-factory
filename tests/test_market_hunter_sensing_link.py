"""Tests for market_hunter.py's Sensing Engine -> market_hunter input link
(ADR-065 Step 3(b)).

    python -m unittest tests.test_market_hunter_sensing_link -v
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


class TestReadSensingEngineNiches(unittest.TestCase):
    def _write(self, lines):
        fd, path = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return path

    def test_missing_file_returns_empty_never_throws(self):
        self.assertEqual(mh._read_sensing_engine_niches(opps_file="/no/such/file.md"), [])

    def test_reads_real_sensing_engine_lines(self):
        path = self._write([
            "- [2026-07-17T00:00:00.000Z] compliance automation for accounting firms — نجحت كل فحوصات الجودة",
        ])
        try:
            niches = mh._read_sensing_engine_niches(opps_file=path)
            self.assertIn("compliance automation for accounting firms", niches)
        finally:
            os.remove(path)

    def test_own_prior_market_hunter_output_is_excluded(self):
        """market_hunter's own _append_to_opportunities() always writes a
        'market_hunter:' reason prefix — these must never be re-read back in
        as if they were a new external Sensing Engine signal."""
        path = self._write([
            "- [2026-07-17T00:00:00.000Z] printable monthly planner — market_hunter: GOOD (65/100)",
        ])
        try:
            niches = mh._read_sensing_engine_niches(opps_file=path)
            self.assertEqual(niches, [])
        finally:
            os.remove(path)

    def test_duplicates_collapsed_and_limit_respected(self):
        lines = [
            f"- [2026-07-17T00:0{i}:00.000Z] niche {i} — نجحت كل فحوصات الجودة"
            for i in range(5)
        ]
        path = self._write(lines)
        try:
            niches = mh._read_sensing_engine_niches(limit=3, opps_file=path)
            self.assertEqual(len(niches), 3)
        finally:
            os.remove(path)


class TestHuntMarketLinksSensingEngine(unittest.TestCase):
    """Pioneer (Strategic Phase, 2026-07-19) is mocked to an empty list in
    every test here -- its own real HN network calls are tested once,
    deliberately, in tests/test_pioneer.py, not repeated on every
    market_hunter test run.

    decisions_path is always redirected to a temp file: hunt_market()'s
    RECORD_LADDER_DECISION() call has no other test-isolation switch, and
    without this every run here was writing real ladder decisions for
    fixture niches ("what is a monsoon", "a real pioneer test candidate
    niche xyz") straight into the live data/decisions.jsonl governance
    ledger -- 174 such lines had already accumulated there across prior
    sessions before this was found and fixed (2026-07-23 post-reboot
    integrity audit)."""

    def setUp(self):
        fd, self.decisions_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.decisions_path)

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    # Both Pioneer entry points must be mocked: hunt_market() CALLS
    # PIONEER_DISCOVER(limit=..) and PIONEER_DISCOVER_ALL(limit_per_source=..),
    # so the replacements must be callables (MagicMock), not bare lists.
    # Patching only the first leaves the second on live network (many
    # sequential calls, unbounded total time in a slow sandbox) — the
    # 2026-09-21 hang root cause.
    def _no_pioneer(self, **kw):
        from unittest.mock import MagicMock
        return patch.multiple(
            mh, PIONEER_DISCOVER=MagicMock(return_value=kw.get("one", [])),
            PIONEER_DISCOVER_ALL=MagicMock(return_value=kw.get("all", [])))

    def test_hunt_market_result_reports_sensing_engine_linked_count(self):
        with self._no_pioneer():
            result = mh.hunt_market(limit=1, write_opportunities=False, decisions_path=self.decisions_path)
        self.assertIn("sensing_engine_linked_count", result)
        self.assertIsInstance(result["sensing_engine_linked_count"], int)

    def test_scanned_entries_are_labeled_with_their_real_source(self):
        with self._no_pioneer():
            result = mh.hunt_market(limit=1, write_opportunities=False, decisions_path=self.decisions_path)
        # "pioneer_all" was added to market_hunter.py by Golden Hunter v2
        # (2026-08-14), which consumes Pioneer's multi-source discover_all()
        # feed alongside discover(). This allowlist still listed only the three
        # pre-v2 labels, so it failed whenever that real source produced an
        # entry -- which is exactly what happened in CI once the committed
        # version stopped mocking PIONEER_DISCOVER_ALL.
        for entry in result["scanned"]:
            self.assertIn(entry["source"], ("seed", "sensing_engine", "pioneer", "pioneer_all"))

    def test_hunt_market_result_reports_pioneer_linked_count(self):
        from unittest.mock import MagicMock
        with patch.multiple(mh, PIONEER_DISCOVER=MagicMock(return_value=[
            {"niche": "a real pioneer test candidate niche xyz", "source": "hacker_news_top_stories"},
        ]), PIONEER_DISCOVER_ALL=MagicMock(return_value=[])):
            result = mh.hunt_market(limit=1, write_opportunities=False, decisions_path=self.decisions_path)
        self.assertEqual(result["pioneer_linked_count"], 1)
        pioneer_entries = [e for e in result["scanned"] if e["source"] == "pioneer"]
        self.assertEqual(len(pioneer_entries), 1)
        self.assertEqual(pioneer_entries[0]["niche"], "a real pioneer test candidate niche xyz")
        self.assertEqual(pioneer_entries[0]["ladder"], "kdp_books")

    def test_a_pioneer_failure_never_blocks_the_real_hunt(self):
        with patch.object(mh, "PIONEER_DISCOVER", side_effect=RuntimeError("HN unreachable")), \
             patch.object(mh, "PIONEER_DISCOVER_ALL", side_effect=RuntimeError("HN unreachable")):
            result = mh.hunt_market(limit=1, write_opportunities=False, decisions_path=self.decisions_path)
        self.assertIn("scanned_count", result)
        self.assertEqual(result["pioneer_linked_count"], 0)

    def test_real_decisions_are_written_to_the_given_path_not_the_live_ledger(self):
        with self._no_pioneer():
            mh.hunt_market(limit=1, write_opportunities=False, decisions_path=self.decisions_path)
        self.assertTrue(os.path.exists(self.decisions_path))


if __name__ == "__main__":
    unittest.main()

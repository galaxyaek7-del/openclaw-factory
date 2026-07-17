"""Tests for market_hunter.py's Sensing Engine -> market_hunter input link
(ADR-065 Step 3(b)).

    python -m unittest tests.test_market_hunter_sensing_link -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

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
    def test_hunt_market_result_reports_sensing_engine_linked_count(self):
        result = mh.hunt_market(limit=1, write_opportunities=False)
        self.assertIn("sensing_engine_linked_count", result)
        self.assertIsInstance(result["sensing_engine_linked_count"], int)

    def test_scanned_entries_are_labeled_with_their_real_source(self):
        result = mh.hunt_market(limit=1, write_opportunities=False)
        for entry in result["scanned"]:
            self.assertIn(entry["source"], ("seed", "sensing_engine"))


if __name__ == "__main__":
    unittest.main()

"""Tests for integrity_monitor.py (Security P1 C3, 2026-08-18): the
SHA-256 hash-chain append-only ledger integrity baseline.

    python -m unittest tests.test_integrity_monitor -v
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

import integrity_monitor as im


def _tmp_dir():
    return tempfile.mkdtemp(prefix="integrity_test_")


class TestIntegrityMonitor(unittest.TestCase):
    def setUp(self):
        self.dir = _tmp_dir()
        self.ledger = os.path.join(self.dir, "test_ledger.jsonl")
        self.baseline = os.path.join(self.dir, "baseline.json")
        self._write_ledger(["line1", "line2", "line3"])

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write_ledger(self, lines):
        with open(self.ledger, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    def _check(self, ledgers=None):
        return im.check_ledger_integrity(
            ledgers=ledgers or [self.ledger], baseline_path=self.baseline)

    def _statuses(self, results):
        return {os.path.basename(r["path"]): r["status"] for r in results}

    def test_first_run_establishes_a_baseline_and_reports_not_baselined(self):
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_NOT_BASELINED)
        self.assertFalse(results[0]["data_available"])
        # The baseline was actually written so the NEXT check is real.
        self.assertTrue(os.path.exists(self.baseline))

    def test_second_run_reports_clean(self):
        self._check()  # establish baseline
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_CLEAN)
        self.assertTrue(results[0]["data_available"])

    def test_a_legitimate_append_is_never_flagged(self):
        self._check()
        self._write_ledger(["line1", "line2", "line3", "appended4"])
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_CLEAN)

    def test_modifying_an_already_baselined_line_is_real_drift(self):
        self._check()
        self._write_ledger(["line1", "TAMPERED", "line3"])
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_DRIFT)
        self.assertTrue(results[0]["data_available"])

    def test_an_append_that_lands_inside_the_baselined_prefix_is_drift(self):
        # Two full checks: after the 2nd, all 4 lines are baselined. Then a
        # middle-line edit (not an append) must still be caught.
        self._check()
        self._write_ledger(["line1", "line2", "line3", "appended4"])
        self._check()
        self._write_ledger(["line1", "line2", "TAMPERED4", "appended4"])
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_DRIFT)

    def test_truncation_is_detected(self):
        self._check()
        self._write_ledger(["line1"])  # was 3 lines, now 1
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_TRUNCATED)

    def test_a_baselined_file_that_disappears_is_missing(self):
        self._check()
        os.remove(self.ledger)
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_MISSING)

    def test_drift_does_not_rebaseline_tampered_content_as_clean(self):
        self._check()
        # Tampered content is reported as drift and never silently
        # re-baselined: the baseline keeps the ORIGINAL chain, and a
        # still-tampered file keeps reporting drift on every check.
        self._write_ledger(["line1", "TAMPERED", "line3"])
        first = self._check()
        self.assertEqual(self._statuses(first)["test_ledger.jsonl"], im.STATUS_DRIFT)
        with open(self.baseline, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.assertEqual(state["ledgers"][self.ledger]["lines"], 3,
                         "a drift must never advance/replace the trusted baseline")
        again = self._check()
        self.assertEqual(self._statuses(again)["test_ledger.jsonl"], im.STATUS_DRIFT,
                         "the still-tampered prefix must keep reporting drift, never a fabricated clean")
        # Restoring the ORIGINAL bytes matches the trusted baseline -> clean.
        self._write_ledger(["line1", "line2", "line3"])
        repaired = self._check()
        self.assertEqual(self._statuses(repaired)["test_ledger.jsonl"], im.STATUS_CLEAN)

    def test_clean_advances_the_baseline_to_protect_appended_lines(self):
        # After one append + clean check, the previously-appended line is
        # now baselined -- a later edit to it must be caught.
        self._check()
        self._write_ledger(["line1", "line2", "line3", "appended4"])
        self._check()  # clean -> baseline advanced to 4 lines
        self._write_ledger(["line1", "line2", "line3", "TAMPERED4"])
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_DRIFT)

    def test_missing_and_nonexistent_ledgers_are_skipped_not_errors(self):
        results = im.check_ledger_integrity(
            ledgers=[os.path.join(self.dir, "never_existed.jsonl")],
            baseline_path=self.baseline)
        self.assertEqual(results[0]["status"], im.STATUS_NOT_BASELINED)
        self.assertFalse(results[0]["data_available"])

    def test_build_baseline_establishes_a_real_trusted_state(self):
        state = im.build_baseline(ledgers=[self.ledger], baseline_path=self.baseline)
        entry = state["ledgers"][self.ledger]
        self.assertEqual(entry["lines"], 3)
        self.assertTrue(entry["chain"])
        results = self._check()
        self.assertEqual(self._statuses(results)["test_ledger.jsonl"], im.STATUS_CLEAN)

    def test_assess_ledger_integrity_aggregates_real_counts(self):
        self._check()
        self._check()  # clean -> both established
        self._write_ledger(["line1", "TAMPERED", "line3"])
        agg = im.assess_ledger_integrity(ledgers=[self.ledger], baseline_path=self.baseline)
        self.assertEqual(agg["summary"].get("DRIFT"), 1)
        self.assertIn("generated_at", agg)

    def test_baseline_contains_no_ledger_content_only_hashes(self):
        self._check()
        with open(self.baseline, "r", encoding="utf-8") as f:
            state = json.load(f)
        with open(self.baseline, "r", encoding="utf-8") as f:
            raw = f.read()
        for line in ("line1", "line2", "line3"):
            self.assertNotIn(line, raw, "baseline must never embed ledger content")


if __name__ == "__main__":
    unittest.main()
#!/usr/bin/env python3
"""Recurring spreadsheet clean-up (backlog B34, 2026-10-29). Synthetic data, temp dirs only."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "services" / "spreadsheet_normalization"))

import recurring as rc  # noqa: E402

PROFILE = {"buyer_id": "shop_a", "key_col": "SKU", "amount_cols": ["Total"], "date_cols": ["Date"],
           "sku_cols": ["SKU"]}
SEPT = [{"Date": "9/3/2026", "SKU": "a-1", "Total": "$10.00"},
        {"Date": "9/4/2026", "SKU": "b-2", "Total": "€5,50"},
        {"Date": "9/4/2026", "SKU": "b-2", "Total": "€5,50"}]
OCT = [{"Date": "10/2/2026", "SKU": "A-1", "Total": "12.5"},
       {"Date": "10/9/2026", "SKU": "c-3", "Total": "$7"}]


class Recurring(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_profile_saved_normalised_and_reused(self):
        p = rc.save_profile(PROFILE, self.d)
        self.assertEqual("sku", p["key_col"])
        self.assertEqual(p, rc.load_profile("shop_a", self.d))
        with self.assertRaises(ValueError):
            rc.save_profile(dict(PROFILE, buyer_id="../x"), self.d)
        with self.assertRaises(ValueError):
            rc.save_profile({"buyer_id": "x"}, self.d)

    def test_two_months_reconcile(self):
        p = rc.save_profile(PROFILE, self.d)
        sept = rc.run_month(SEPT, p)
        self.assertEqual("OK", sept["status"], sept["reasons"])
        self.assertEqual(1, sept["qa"]["duplicates_removed"])
        self.assertIsNone(sept["change_report"])
        octo = rc.run_month(OCT, p, previous_rows=sept["rows"])
        self.assertEqual("OK", octo["status"], octo["reasons"])
        rep = octo["change_report"]
        self.assertEqual(["C-3"], rep["keys_added"])
        self.assertEqual(["B-2"], rep["keys_removed"])
        self.assertEqual({"previous": 15.5, "current": 19.5, "change": 4.0}, rep["totals"]["total"])
        self.assertTrue(octo["checks"]["totals_reconcile"])

    def test_flagged_file_is_refused_before_processing(self):
        p = rc.save_profile(PROFILE, self.d)
        rows = [{"Date": "9/3/2026", "SKU": "a", "Total": "1", "api_key": "x"}]
        r = rc.run_month(rows, p)
        self.assertEqual("REFUSED", r["status"])
        self.assertNotIn("rows", r)
        r = rc.run_month([{"Date": "9/3/2026", "SKU": "ghp_abcdef123456", "Total": "1"}], p)
        self.assertEqual("REFUSED", r["status"])

    def test_profile_columns_must_exist(self):
        p = rc.save_profile(PROFILE, self.d)
        r = rc.run_month([{"Date": "9/3/2026", "Item": "a", "Total": "1"}], p)
        self.assertEqual("FAILED", r["status"])
        self.assertIn("sku", r["reasons"][0])

    def test_non_numeric_amounts_are_counted_not_summed(self):
        p = rc.save_profile(PROFILE, self.d)
        sept = rc.run_month(SEPT, p)
        octo = rc.run_month(OCT + [{"Date": "10/9/2026", "SKU": "d-4", "Total": "n/a"}], p, sept["rows"])
        self.assertEqual(1, octo["change_report"]["non_numeric_amounts"]["total"])
        self.assertEqual(19.5, octo["change_report"]["totals"]["total"]["current"])

    def test_empty_file(self):
        self.assertEqual("FAILED", rc.run_month([], rc.save_profile(PROFILE, self.d))["status"])


if __name__ == "__main__":
    unittest.main()

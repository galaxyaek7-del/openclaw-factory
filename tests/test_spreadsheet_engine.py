#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spreadsheet engine tests (offline; synthetic data only)."""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))
sys.path.insert(0, str(_FACTORY_ROOT / "services" / "spreadsheet_normalization"))

from engine import normalize, norm_currency, norm_date


class TestEngine(unittest.TestCase):
    def test_duplicate_caught(self):
        rows = [{"sku": "a-1", "price": "5"}, {"sku": "A-1 ", "price": "5.00"}]
        r = normalize(rows, currency_cols=("price",))
        self.assertEqual(r["qa"]["output_rows"], 1)
        self.assertEqual(r["qa"]["duplicates_removed"], 1)

    def test_currency_locales(self):
        self.assertEqual(norm_currency("€99,99"), 99.99)
        self.assertEqual(norm_currency("1,234.56"), 1234.56)
        self.assertEqual(norm_currency("1.234,56"), 1234.56)

    def test_dates_iso(self):
        self.assertEqual(norm_date("03/15/2026"), "2026-03-15")
        self.assertEqual(norm_date("15-03-2026"), "2026-03-15")

    def test_impossible_dates_are_never_written_as_iso(self):
        # Before 2026-10-29: "13/04/2026" -> "2026-13-04", "2026.02.30" -> "2026-02-30".
        for v in ("13/13/2026", "2026.02.30", "2026-13-01", "31-04-2026"):
            self.assertEqual(norm_date(v), v, v)
        from engine import parse_date
        self.assertEqual(parse_date("2026.02.30")[1], "invalid")
        self.assertEqual(parse_date("13/04/2026"), ("2026-04-13", "converted"))

    def test_ambiguous_dates_are_kept_and_flagged_unless_the_column_settles_them(self):
        rows = [{"date": "03/04/2026"}, {"date": "05/06/2026"}]
        r = normalize(rows, currency_cols=(), date_cols=("date",))
        self.assertEqual([x["date"] for x in r["rows"]], ["03/04/2026", "05/06/2026"])
        self.assertEqual(r["qa"]["dates_ambiguous_kept"], 2)
        dmy = [{"date": "03/04/2026"}, {"date": "25/12/2026"}]
        r = normalize(dmy, currency_cols=(), date_cols=("date",))
        self.assertEqual(r["qa"]["date_order_inferred"], {"date": "DMY"})
        self.assertEqual([x["date"] for x in r["rows"]], ["2026-04-03", "2026-12-25"])
        mdy = [{"date": "03/04/2026"}, {"date": "12/25/2026"}]
        r = normalize(mdy, currency_cols=(), date_cols=("date",))
        self.assertEqual([x["date"] for x in r["rows"]], ["2026-03-04", "2026-12-25"])

    def test_repeated_skus_are_reported_not_merged(self):
        rows = [{"sku": "ab-1", "price": "$8.50", "src": "a"}, {"sku": "AB-1", "price": "€8,50", "src": "b"},
                {"sku": "AB-2", "price": "9", "src": "a"}, {"sku": "AB-2", "price": "9.5", "src": "b"}]
        r = normalize(rows, currency_cols=("price",), date_cols=())
        self.assertEqual(r["qa"]["output_rows"], 4)
        self.assertEqual(r["qa"]["sku_repeats"]["AB-1"], {"rows": 2, "prices": ["8.5"], "price_conflict": False})
        self.assertTrue(r["qa"]["sku_repeats"]["AB-2"]["price_conflict"])
        self.assertEqual(r["qa"]["sku_price_conflicts"], 1)
        # "$8.50" and "€8,50" become the same number: the column must be flagged.
        self.assertEqual(r["qa"]["mixed_currency_columns"], ["price"])
        self.assertEqual(r["qa"]["currency_symbols_by_column"]["price"], ["$", "€"])

    def test_conflicting_evidence_infers_nothing(self):
        rows = [{"date": "25/12/2026"}, {"date": "12/26/2026"}, {"date": "03/04/2026"}]
        r = normalize(rows, currency_cols=(), date_cols=("date",))
        self.assertIsNone(r["qa"]["date_order_inferred"]["date"])
        self.assertEqual(r["rows"][2]["date"], "03/04/2026")
        self.assertEqual(r["qa"]["dates_ambiguous_kept"], 1)

    def test_empty_input(self):
        r = normalize([])
        self.assertEqual(r["qa"]["output_rows"], 0)

    def test_no_silent_loss(self):
        rows = [{"sku": "a", "price": "1"}, {"sku": "b", "price": "bad!!"}]
        r = normalize(rows, currency_cols=("price",))
        qa = r["qa"]
        self.assertEqual(qa["input_rows"], qa["output_rows"] + qa["duplicates_removed"])

    def test_stress_scale(self):
        import random
        random.seed(7)
        rows = [{"sku": "X-%03d" % (i % 200), "price": "$%d.99" % (i % 50),
                 "date": "2026-03-%02d" % ((i % 28) + 1)} for i in range(500)]
        r = normalize(rows, currency_cols=("price",), date_cols=("date",))
        self.assertEqual(r["qa"]["input_rows"], 500)
        self.assertEqual(r["qa"]["output_rows"] + r["qa"]["duplicates_removed"], 500)

    def test_secrets_rejected(self):
        from engine import scan_secrets
        bad = [{"password": "x", "sku": "a"}, {"sku": "b"}]
        r = scan_secrets(bad)
        self.assertFalse(r["clean"])
        good = [{"sku": "a", "price": "5"}]
        self.assertTrue(scan_secrets(good)["clean"])

    def test_package_files(self):
        base = _FACTORY_ROOT / "services" / "spreadsheet_normalization"
        for f in ("engine.py", "README.md", "offer.md", "runbook.md",
                  "sample_before.csv", "sample_after.csv"):
            self.assertTrue((base / f).exists(), f)


if __name__ == "__main__":
    unittest.main(verbosity=2)

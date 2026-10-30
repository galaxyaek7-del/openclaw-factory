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


class TestReadTable(unittest.TestCase):
    """read_table(): the offer promises CSV and XLSX; both must actually read."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.TemporaryDirectory()
        self.d = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_xlsx_first_sheet_typed_values_and_notes(self):
        import datetime
        import openpyxl
        import engine
        p = self.d / "cat.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Products"
        ws.append(["SKU", "Price", "Date", None])
        ws.append([" ab-1 ", 8.5, datetime.datetime(2026, 3, 15), 3.0])
        ws.append([None, None, None, None])
        ws.append(["ab-2", "€8,50", "03-04-2026", None])
        wb.create_sheet("Notes")
        wb.save(p)
        rows, notes = engine.read_table(p)
        self.assertEqual(len(rows), 2)                                  # the empty row is skipped
        self.assertEqual(rows[0]["Date"], "2026-03-15")                 # a real Excel date becomes ISO
        self.assertEqual(rows[0]["column_4"], 3)                        # unnamed header gets a name
        self.assertIn("other sheets: Notes", notes[0])
        out = normalize(rows, sku_cols=("sku",), currency_cols=("price",), date_cols=("date",))
        self.assertEqual([r["price"] for r in out["rows"]], [8.5, 8.5])
        self.assertEqual(out["qa"]["dates_ambiguous_kept"], 1)

    def test_csv_with_semicolons_and_bad_files(self):
        import engine
        p = self.d / "eu.csv"
        p.write_text("sku;price\nAB-1;8,50\n", encoding="utf-8")
        rows, _ = engine.read_table(p)
        self.assertEqual(rows, [{"sku": "AB-1", "price": "8,50"}])
        bad = self.d / "fake.xlsx"
        bad.write_bytes(b"not a zip")
        with self.assertRaises(engine.UnreadableTable):
            engine.read_table(bad)
        orig = engine.MAX_UPLOAD_BYTES
        engine.MAX_UPLOAD_BYTES = 5
        try:
            with self.assertRaises(engine.UnreadableTable):
                engine.read_table(p)
        finally:
            engine.MAX_UPLOAD_BYTES = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)

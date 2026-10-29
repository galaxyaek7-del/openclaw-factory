"""The sample data product release validates against its own data card (file
hash, row count, columns, licence, no personal data) and carries both filing
methods with a source and date on every row."""
import csv
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data_products import datacard  # noqa: E402

RELEASE = ROOT / "data_products" / "releases" / "uspto-trademark-fees" / "2026-10-29"


class UsptoFeeRelease(unittest.TestCase):
    def test_card_passes_against_the_files_on_disk(self):
        card = json.loads((RELEASE / "datacard.json").read_text(encoding="utf-8"))
        result = datacard.validate_card(card, ROOT, today=date(2026, 10, 29))
        self.assertEqual(result["status"], "PASS", result)

    def test_every_row_has_both_filing_methods_and_a_source(self):
        rows = list(csv.DictReader(open(RELEASE / "uspto_trademark_fees.csv", encoding="utf-8")))
        self.assertEqual(len(rows), 8)
        for r in rows:
            self.assertTrue(float(r["efile_fee_usd"]) > 0 and float(r["paper_fee_usd"]) > 0, r)
            self.assertTrue(r["source_url"].startswith("https://www.uspto.gov/"), r)
            self.assertEqual(r["retrieved_on"], "2026-10-29")
        sou = next(r for r in rows if r["efile_fee_code"] == "7003")
        self.assertEqual((sou["efile_fee_usd"], sou["paper_fee_usd"]), ("150.00", "250.00"))

    def test_release_goes_stale_after_its_refresh_interval(self):
        card = json.loads((RELEASE / "datacard.json").read_text(encoding="utf-8"))
        self.assertNotEqual(datacard.validate_card(card, ROOT, today=date(2026, 12, 15))["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

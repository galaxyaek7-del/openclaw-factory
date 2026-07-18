"""Tests for channels/ledger.py's finance reconciliation (ADR-077, Product
Generation Pipeline — Finance Ledger stage).

Runs with stdlib unittest. Never touches the real data/sales_ledger.jsonl
or finance_data.json — every test passes explicit temp paths.

    python -m unittest tests.test_ledger -v
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

from channels import ledger


def _temp_path(suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestReconcileLedgerToFinance(unittest.TestCase):
    def setUp(self):
        self.ledger_path = _temp_path(".jsonl")
        self.finance_path = _temp_path(".json")

    def tearDown(self):
        for p in (self.ledger_path, self.finance_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_ledger_file_reconciles_to_the_honest_default_shape(self):
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)
        self.assertEqual(result, {"reconciled": 0, "skipped_unrecognized": 0, "total_sales": 0})
        self.assertFalse(Path(self.finance_path).exists())  # nothing to write, file untouched

    def test_gumroad_sale_reconciles_with_real_amount(self):
        ledger.record_sale("gumroad", {"id": "sale_1", "price": "19.99", "product_name": "Real Book"}, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["reconciled"], 1)
        self.assertEqual(result["skipped_unrecognized"], 0)
        self.assertEqual(result["total_sales"], 19.99)

        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["totalGumroad"], 19.99)
        self.assertEqual(data["totalSales"], 19.99)
        self.assertEqual(data["sales"][0]["platform"], "Gumroad")
        self.assertEqual(data["sales"][0]["source_ledger_key"], "gumroad:sale_1")
        self.assertEqual(data["byLadder"]["kdp_books"], 19.99)  # honest default rank

    def test_paddle_sale_amount_extracted_from_grand_total_cents(self):
        raw = {"id": "txn_1", "details": {"totals": {"grand_total": "38800"}}}
        ledger.record_sale("paddle", raw, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["reconciled"], 1)
        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["totalPaddle"], 388.0)

    def test_unrecognized_platform_is_skipped_never_counted_as_zero(self):
        ledger.record_sale("mystery_platform", {"id": "x"}, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["reconciled"], 0)
        self.assertEqual(result["skipped_unrecognized"], 1)
        self.assertFalse(Path(self.finance_path).exists())

    def test_rerunning_reconciliation_never_double_counts(self):
        ledger.record_sale("gumroad", {"id": "sale_1", "price": "19.99"}, ledger_path=self.ledger_path)
        ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)
        second = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(second["reconciled"], 0)
        self.assertEqual(second["total_sales"], 19.99)
        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["sales"]), 1)

    def test_reconciliation_is_additive_to_existing_finance_data(self):
        existing = {
            "sales": [{"id": 1, "platform": "KDP", "amount": 5.0, "product": "old", "date": "2026-01-01"}],
            "totalKDP": 5.0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 0, "totalSales": 5.0,
            "byLadder": {"kdp_books": 5.0}, "lastUpdated": "2026-01-01T00:00:00+00:00",
        }
        with open(self.finance_path, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        ledger.record_sale("gumroad", {"id": "sale_1", "price": "19.99"}, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["total_sales"], 24.99)
        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["sales"]), 2)
        self.assertEqual(data["sales"][0]["platform"], "KDP")  # pre-existing sale preserved verbatim
        self.assertEqual(data["sales"][1]["id"], 2)  # new sale's id continues the sequence


if __name__ == "__main__":
    unittest.main()

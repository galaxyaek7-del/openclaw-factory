"""Real market evidence is not a Galaxy Forge sale.

Regression coverage for the stale 2-record decision-snapshot assumption:
the source of truth is data/market_evidence.jsonl, and none of its records
is a closed sale or revenue event. Read-only; no network.
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FACTORY = Path(__file__).resolve().parent.parent
NICHE = "Legal Case Research Automation System for Solo Attorneys"


class TestMarketEvidenceIsNotSale(unittest.TestCase):
    def test_legal_niche_has_real_market_evidence_only(self):
        rows = [json.loads(line) for line in
                (FACTORY / "data" / "market_evidence.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]
        records = [r for r in rows if r.get("niche") == NICHE]
        self.assertGreaterEqual(len(records), 2)
        for r in records:
            self.assertNotIn(r.get("event_type"), {"sale", "closed_sale", "revenue"})
            self.assertTrue(r.get("payload", {}).get("source_url"))
            self.assertTrue(r.get("payload", {}).get("quote"))

    def test_no_sale_events_or_revenue_exist(self):
        sales = [json.loads(line) for line in
                 (FACTORY / "data" / "sales_ledger.jsonl").read_text(encoding="utf-8").splitlines()
                 if line.strip()]
        self.assertEqual([e for e in sales if e.get("event_type") == "sale"], [])
        finance = json.loads((FACTORY / "finance_data.json").read_text(encoding="utf-8"))
        self.assertEqual(finance.get("sales"), [])
        self.assertEqual(finance.get("totalSales", 0), 0)


if __name__ == "__main__":
    unittest.main()

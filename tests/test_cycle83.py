"""Cycle 83 — regression tests for revenue evidence integrity.

Every test here exists because a real defect was confirmed by reading the code,
not by imagining one. Three of them are the direct inverses of a bug that was
live in this repository.

THE THREE THAT MATTER MOST

1. affiliate/reconcile.py summed a top-level `amount_usd_cents` key that
   channels/ledger.py::record_sale() has NEVER written -- it writes
   {"event_type","platform","raw",...} with the amount inside `raw`. So
   gumroad_revenue_usd was structurally $0.00 no matter how many real sales
   existed. It also divided by 100 while the canonical extractor returns whole
   DOLLARS.

2. affiliate/reality.py carried the literal string "$0 VERIFIED" as the REVENUE
   row, written to data/reality_audit_live.json on every run regardless of what
   the API returned -- and discarded its own `recon` argument on the next line.

3. The same file reported FINANCIAL_RECONCILIATION = "CONSISTENT" when the
   platform source was UNREADABLE: None was filtered out of the comparison,
   the two remaining zeros agreed, and a failed source became a passing
   verdict.

Run:  python -m unittest discover -s tests -p "test_cycle83.py" -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import reality as affiliate_reality
from affiliate import reconcile as affiliate_reconcile


def _sale(platform, raw, **extra):
    """A row shaped exactly like channels/ledger.py::record_sale() writes."""
    return {"event_type": "sale", "platform": platform, "raw": raw, **extra}


class TestSaleAmountExtraction(unittest.TestCase):
    """Defect 1: the wrong key made real revenue read as $0."""

    def _reconcile_with(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                          encoding="utf-8")
        for r in rows:
            tmp.write(json.dumps(r) + "\n")
        tmp.close()
        original = affiliate_reconcile._read_jsonl

        def fake(path):
            if path.endswith("sales_ledger.jsonl"):
                return list(rows)
            return original(path)

        affiliate_reconcile._read_jsonl = fake
        try:
            return affiliate_reconcile.reconcile()
        finally:
            affiliate_reconcile._read_jsonl = original
            os.unlink(tmp.name)

    def test_a_real_gumroad_sale_is_no_longer_reported_as_zero(self):
        """Gumroad's real sale shape is {"price": "29.00"} in whole dollars,
        per channels/ledger.py::_extract_sale_amount and the v2 Sales docs."""
        r = self._reconcile_with([_sale("gumroad", {"price": "29.00"})])
        self.assertEqual(r["gumroad_sales_events"], 1)
        self.assertEqual(r["gumroad_revenue_usd"], 29.0,
                         "a real $29 sale must not reconcile to $0.00")
        self.assertEqual(r["sale_amount_status"], "PASS")

    def test_no_cent_double_division(self):
        """$155 must be 155.00, not 1.55. The old code divided by 100 again."""
        r = self._reconcile_with([_sale("gumroad", {"price": 155})])
        self.assertEqual(r["gumroad_revenue_usd"], 155.0)

    def test_multiple_sales_sum(self):
        r = self._reconcile_with([
            _sale("gumroad", {"price": "29.00"}),
            _sale("gumroad", {"price": "69.00"}),
            _sale("paddle", {"details": {"totals": {"grand_total": 19700}}}),
        ])
        self.assertEqual(r["gumroad_revenue_usd"], 98.0)
        self.assertEqual(r["paddle_revenue_usd"], 197.0)

    def test_unrecognized_amount_is_unknown_never_zero(self):
        """A real sale we cannot price must not become a silent $0 sale."""
        r = self._reconcile_with([_sale("gumroad", {"unexpected": "shape"})])
        self.assertEqual(r["gumroad_sales_events"], 1)
        self.assertEqual(r["gumroad_revenue_usd"], 0.0)
        self.assertEqual(r["gumroad_sales_with_unrecognized_amount"], 1)
        self.assertEqual(r["sale_amount_status"], "PARTIAL_AMOUNT_UNRECOGNIZED")
        self.assertNotEqual(r["sale_amount_evidence"], "OBSERVED")

    def test_genuine_zero_stays_zero(self):
        """An empty ledger with a clean read is a REAL zero and stays one."""
        r = self._reconcile_with([])
        self.assertEqual(r["gumroad_sales_events"], 0)
        self.assertEqual(r["gumroad_revenue_usd"], 0.0)
        self.assertEqual(r["sale_amount_status"], "PASS")
        self.assertEqual(r["sale_amount_evidence"], "OBSERVED")

    def test_duplicate_transactions_are_not_double_counted_here(self):
        """Dedup is poll_sales.py's job; this asserts reconcile reports the
        row count it actually saw rather than inventing a distinct count."""
        rows = [_sale("gumroad", {"price": "10.00"})] * 2
        r = self._reconcile_with(rows)
        self.assertEqual(r["gumroad_sales_events"], 2)
        self.assertEqual(r["gumroad_revenue_usd"], 20.0)


class TestPayoutsAreUnknownNotZero(unittest.TestCase):
    """affiliate_payouts_verified_usd used to be the literal 0, which reads as
    'we checked and there were none'. No payout feed exists here at all."""

    def test_payouts_are_unknown(self):
        r = affiliate_reconcile.reconcile()
        self.assertIsNone(r["affiliate_payouts_verified_usd"])
        self.assertEqual(r["affiliate_payouts_status"], "UNKNOWN")


class TestReconcileVerdictHonesty(unittest.TestCase):
    """Defect 3: an unreadable platform used to reconcile as CONSISTENT."""

    def test_readable_zero_is_consistent(self):
        rc = affiliate_reality.reconcile(0)
        self.assertEqual(rc["FINANCIAL_RECONCILIATION"], "CONSISTENT")
        self.assertTrue(rc["platform_source_readable"])

    def test_unreadable_platform_is_not_reconcilable(self):
        rc = affiliate_reality.reconcile(None)
        self.assertEqual(rc["FINANCIAL_RECONCILIATION"], "NOT_RECONCILABLE")
        self.assertFalse(rc["platform_source_readable"],
                         "an unreadable source must be flagged, not passed")

    def test_disagreement_is_failed(self):
        rc = affiliate_reality.reconcile(5)
        self.assertEqual(rc["FINANCIAL_RECONCILIATION"], "FAILED")


class TestRevenueRowIsDerivedNotHardcoded(unittest.TestCase):
    """Defect 2: the literal string "$0 VERIFIED"."""

    def _revenue_row(self, platform_count):
        rc = affiliate_reality.reconcile(platform_count)
        rows = affiliate_reality.evidence_matrix({}, rc)
        return next(r for r in rows if r["DOMAIN"] == "REVENUE")

    def test_verified_is_never_asserted_without_a_retrieved_transaction(self):
        for pc in (0, None, 5):
            status = self._revenue_row(pc)["STATUS"]
            self.assertNotEqual(
                status, "$0 VERIFIED",
                "no transaction has ever been retrieved, so 'VERIFIED' is "
                "an unearned claim regardless of the other sources")

    def test_unreadable_source_yields_unknown(self):
        row = self._revenue_row(None)
        self.assertEqual(row["STATUS"], "UNKNOWN")

    def test_real_zero_is_labelled_as_a_successful_query(self):
        row = self._revenue_row(0)
        self.assertIn("QUERY SUCCEEDED", row["STATUS"])
        self.assertIn("observed", row["EVIDENCE"])

    def test_contradiction_is_surfaced_not_smoothed(self):
        row = self._revenue_row(5)
        self.assertEqual(row["STATUS"], "CONTRADICTED")


class TestEvidenceMatrixStillCoversItsDomains(unittest.TestCase):
    """The REVENUE row is now derived. Guard that deriving it did not drop a
    domain or break the 4-field contract the renderer depends on."""

    def test_every_row_has_four_fields(self):
        rc = affiliate_reality.reconcile(0)
        for row in affiliate_reality.evidence_matrix({}, rc):
            self.assertEqual(set(row),
                             {"DOMAIN", "STATUS", "EVIDENCE", "UNKNOWN",
                              "CONTRADICTION"})

    def test_domains_are_not_lost(self):
        rc = affiliate_reality.reconcile(0)
        domains = {r["DOMAIN"] for r in affiliate_reality.evidence_matrix({}, rc)}
        for expected in ("PRODUCT", "BUYER", "TRAFFIC", "CHECKOUT", "PURCHASE",
                         "REVENUE", "ATTRIBUTION"):
            self.assertIn(expected, domains)


class TestNoFabricationInTheFix(unittest.TestCase):
    def test_reconcile_output_carries_no_hardcoded_verified_revenue(self):
        blob = json.dumps(affiliate_reconcile.reconcile())
        self.assertNotIn("VERIFIED_REVENUE", blob)
        self.assertNotIn("$0 VERIFIED", blob)

    def test_simulated_commissions_are_still_segregated(self):
        r = affiliate_reconcile.reconcile()
        self.assertIn("not revenue", r["simulation_note"])
        self.assertNotIn("simulation", r["affiliate_revenue_verified_usd"].__str__())


if __name__ == "__main__":
    unittest.main(verbosity=2)
"""Affiliate arm revenue attribution (backlog B22, 2026-10-29).

Only a REAL commission with status PAID in commission_ledger is revenue for the
Affiliate Intelligence arm. TEST rows never count; CONFIRMED is reported but does
not promote the arm. Every ledger here is a temp file.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import business_arms as ba  # noqa: E402
import commission_ledger as cl  # noqa: E402

NO_REVENUE = {"status": "PASS", "gross_usd": 0}


class AffiliateArmRevenue(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.ledger = os.path.join(self.d, "commission_ledger.jsonl")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def status(self, commissions):
        cfg = ba._affiliate_cfg(ba.ARMS["affiliate_intelligence"], {}, commissions)
        return ba.evaluate_arm("affiliate_intelligence", cfg, NO_REVENUE), cfg

    def test_test_rows_never_count(self):
        cl.record_commission("p", "o", "PAID", 500.0, "TEST", external_transaction_id="t1",
                             ledger_path=self.ledger)
        ev = ba._commission_evidence(self.ledger)
        self.assertEqual(0, ev["real_records"])
        self.assertEqual(1, ev["test_records"])
        arm, cfg = self.status(ev)
        self.assertNotEqual("REVENUE_VERIFIED", arm["status"])
        self.assertIn("TEST rows excluded: 1", cfg["gap"])

    def test_real_confirmed_is_reported_but_does_not_promote(self):
        cl.record_commission("amazon", "CO-amazon-affiliate", "CONFIRMED", 4.2, "REAL",
                             external_transaction_id="amz-1", evidence="network report row 17",
                             ledger_path=self.ledger)
        arm, cfg = self.status(ba._commission_evidence(self.ledger))
        self.assertNotEqual("REVENUE_VERIFIED", arm["status"])
        self.assertIn("$0.00 paid, $4.20 confirmed or paid", cfg["gap"])

    def test_real_paid_promotes_the_affiliate_arm(self):
        cl.record_commission("amazon", "CO-amazon-affiliate", "PAID", 4.2, "REAL",
                             external_transaction_id="amz-2", evidence="payout statement 2026-11",
                             ledger_path=self.ledger)
        arm, cfg = self.status(ba._commission_evidence(self.ledger))
        self.assertEqual("REVENUE_VERIFIED", arm["status"])
        self.assertTrue(arm["arm_revenue_attributable"])
        self.assertEqual("commission_ledger (REAL, PAID)", cfg["arm_revenue_evidence"]["source"])

    def test_reversed_commission_no_longer_counts(self):
        cl.record_commission("amazon", "CO-amazon-affiliate", "PAID", 4.2, "REAL",
                             external_transaction_id="amz-3", evidence="payout", ledger_path=self.ledger)
        cl.record_status_change("amz-3", "REVERSED", "REAL", evidence="network reversal notice",
                                ledger_path=self.ledger)
        arm, _ = self.status(ba._commission_evidence(self.ledger))
        self.assertNotEqual("REVENUE_VERIFIED", arm["status"])

    def test_company_revenue_does_not_promote_the_affiliate_arm(self):
        # A Gumroad sale is Digital Products revenue, not affiliate revenue.
        cfg = ba._affiliate_cfg(ba.ARMS["affiliate_intelligence"], {}, ba._commission_evidence(self.ledger))
        arm = ba.evaluate_arm("affiliate_intelligence", cfg, {"status": "PASS", "gross_usd": 99})
        self.assertNotEqual("REVENUE_VERIFIED", arm["status"])

    def test_other_arms_keep_the_company_rule(self):
        cfg = dict(ba.ARMS["digital_products"], arm_revenue_attributable=True)
        cfg.pop("external_dependency", None)
        self.assertEqual("REVENUE_VERIFIED",
                         ba.evaluate_arm("digital_products", cfg, {"status": "PASS", "gross_usd": 15})["status"])
        self.assertNotEqual("REVENUE_VERIFIED",
                            ba.evaluate_arm("digital_products", cfg, {"status": "STALE", "gross_usd": 15})["status"])


if __name__ == "__main__":
    unittest.main()

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import record_real_commission as rrc  # noqa: E402
import commission_ledger as cl  # noqa: E402


class RecordRealCommissionTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ledger = os.path.join(self.dir, "ledger.jsonl")

    def go(self, *extra):
        args = rrc.build_args(["--ledger", self.ledger] + list(extra))
        return rrc.run(args)

    def test_dry_run_writes_nothing(self):
        self.assertEqual(0, self.go("--amount", "10", "--status", "PENDING", "--evidence", "dashboard 2026-11-20 referral 1"))
        self.assertFalse(os.path.exists(self.ledger))

    def test_pending_real_with_evidence_is_recorded_but_not_paid(self):
        self.assertEqual(0, self.go("--amount", "10", "--status", "PENDING", "--evidence",
                                    "systeme.io dashboard 2026-11-20 referral 1", "--apply"))
        s = cl.real_commission_summary(self.ledger)
        self.assertEqual(1, s["real_commission_records"])
        self.assertEqual(0, s["real_paid_commission_usd"])

    def test_paid_without_txid_is_refused(self):
        self.assertEqual(2, self.go("--amount", "30", "--status", "PAID", "--evidence",
                                    "payout email 2026-12-01 from partner", "--apply"))
        self.assertFalse(os.path.exists(self.ledger))

    def test_paid_with_txid_counts_and_a_repeat_is_refused(self):
        a = ["--amount", "30", "--status", "PAID", "--evidence", "payout email 2026-12-01 from partner",
             "--txid", "SYS-PAYOUT-0001", "--apply"]
        self.assertEqual(0, self.go(*a))
        self.assertEqual(30, cl.real_commission_summary(self.ledger)["real_paid_commission_usd"])
        self.assertEqual(2, self.go(*a))
        self.assertEqual(30, cl.real_commission_summary(self.ledger)["real_paid_commission_usd"])

    def test_trivial_evidence_is_refused(self):
        self.assertEqual(2, self.go("--amount", "10", "--status", "PENDING", "--evidence", "ok", "--apply"))

    def test_test_environment_never_counts_as_real(self):
        self.assertEqual(0, self.go("--amount", "10", "--status", "PAID", "--environment", "TEST",
                                    "--evidence", "rehearsal", "--apply"))
        self.assertEqual(0, cl.real_commission_summary(self.ledger)["real_commission_records"])


if __name__ == "__main__":
    unittest.main()

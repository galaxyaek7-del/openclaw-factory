import json
import os
import tempfile
import unittest

import commission_ledger as cl


class TestAntiFabricationGuard(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "ledger.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_real_without_evidence_raises(self):
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_commission("p", "o", "EXPECTED", 10.0, "REAL", ledger_path=self.path)

    def test_whitespace_only_evidence_rejected(self):
        # Phase 35 (ADR-228) regression: a real, found firewall gap --
        # "   " is truthy in Python and previously bypassed the bare
        # `not evidence` check.
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_commission("p", "o", "PAID", 999.0, "REAL", evidence="   ",
                                  external_transaction_id="fake_txn", ledger_path=self.path)

    def test_trivially_short_transaction_id_rejected(self):
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_commission("p", "o", "PAID", 999.0, "REAL", evidence="real evidence here",
                                  external_transaction_id="ab", ledger_path=self.path)

    def test_whitespace_transaction_id_rejected(self):
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_commission("p", "o", "CONFIRMED", 999.0, "REAL", evidence="real evidence here",
                                  external_transaction_id="   ", ledger_path=self.path)

    def test_real_without_evidence_never_writes_to_disk(self):
        try:
            cl.record_commission("p", "o", "EXPECTED", 10.0, "REAL", ledger_path=self.path)
        except cl.AntiFabricationError:
            pass
        self.assertFalse(os.path.exists(self.path))

    def test_real_confirmed_without_transaction_id_raises(self):
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_commission("p", "o", "CONFIRMED", 10.0, "REAL", evidence="real evidence", ledger_path=self.path)

    def test_real_paid_without_transaction_id_raises(self):
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_commission("p", "o", "PAID", 10.0, "REAL", evidence="real evidence", ledger_path=self.path)

    def test_real_with_evidence_and_transaction_id_succeeds(self):
        record = cl.record_commission("p", "o", "CONFIRMED", 10.0, "REAL", evidence="real evidence",
                                       external_transaction_id="txn_real_1", ledger_path=self.path)
        self.assertEqual(record["environment"], "REAL")

    def test_test_environment_never_requires_evidence(self):
        record = cl.record_commission("p", "o", "EXPECTED", 10.0, "TEST", ledger_path=self.path)
        self.assertEqual(record["environment"], "TEST")

    def test_simulation_environment_never_requires_evidence(self):
        record = cl.record_commission("p", "o", "EXPECTED", 10.0, "SIMULATION", ledger_path=self.path)
        self.assertEqual(record["environment"], "SIMULATION")

    def test_invalid_environment_rejected(self):
        with self.assertRaises(ValueError):
            cl.record_commission("p", "o", "EXPECTED", 10.0, "FAKE_ENV", ledger_path=self.path)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            cl.record_commission("p", "o", "NOT_A_REAL_STATUS", 10.0, "TEST", ledger_path=self.path)


class TestLedgerArithmetic(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "ledger.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_net_commission_subtracts_fees(self):
        record = cl.record_commission("p", "o", "EXPECTED", 100.0, "TEST", fees=15.0, ledger_path=self.path)
        self.assertEqual(record["net_commission"], 85.0)


class TestRealCommissionSummary(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "ledger.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_empty_ledger_is_zero(self):
        summary = cl.real_commission_summary(ledger_path=self.path)
        self.assertEqual(summary["real_confirmed_or_paid_commission_usd"], 0)

    def test_simulation_never_counted_in_real_totals(self):
        cl.record_commission("p", "o", "PAID", 500.0, "SIMULATION", ledger_path=self.path)
        summary = cl.real_commission_summary(ledger_path=self.path)
        self.assertEqual(summary["real_confirmed_or_paid_commission_usd"], 0)
        self.assertEqual(summary["simulation_records"], 1)

    def test_test_never_counted_in_real_totals(self):
        cl.record_commission("p", "o", "PAID", 500.0, "TEST", ledger_path=self.path)
        summary = cl.real_commission_summary(ledger_path=self.path)
        self.assertEqual(summary["real_confirmed_or_paid_commission_usd"], 0)

    def test_real_expected_not_counted_only_confirmed_or_paid(self):
        cl.record_commission("p", "o", "EXPECTED", 500.0, "REAL", evidence="real", ledger_path=self.path)
        summary = cl.real_commission_summary(ledger_path=self.path)
        self.assertEqual(summary["real_confirmed_or_paid_commission_usd"], 0)
        self.assertEqual(summary["real_commission_records"], 1)

    def test_real_confirmed_is_counted(self):
        cl.record_commission("p", "o", "CONFIRMED", 500.0, "REAL", evidence="real",
                              external_transaction_id="txn_1", ledger_path=self.path)
        summary = cl.real_commission_summary(ledger_path=self.path)
        self.assertEqual(summary["real_confirmed_or_paid_commission_usd"], 500.0)

    def test_duplicate_environments_all_tracked_separately(self):
        cl.record_commission("p", "o", "PAID", 100.0, "REAL", evidence="real evidence", external_transaction_id="txn_1", ledger_path=self.path)
        cl.record_commission("p", "o", "PAID", 200.0, "TEST", ledger_path=self.path)
        cl.record_commission("p", "o", "PAID", 300.0, "SIMULATION", ledger_path=self.path)
        summary = cl.real_commission_summary(ledger_path=self.path)
        self.assertEqual(summary["real_paid_commission_usd"], 100.0)
        self.assertEqual(summary["test_records"], 1)
        self.assertEqual(summary["simulation_records"], 1)


if __name__ == "__main__":
    unittest.main()

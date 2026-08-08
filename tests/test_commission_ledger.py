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


class TestFirstRealDollarStatus(unittest.TestCase):
    """Phase 38b ('Chief Commercial Engineer' directive, ADR-234), Section 11."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "ledger.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_false_on_empty_ledger(self):
        result = cl.first_real_dollar_status(ledger_path=self.path)
        self.assertFalse(result["FIRST_REAL_DOLLAR"])
        self.assertEqual(result["REAL_REVENUE"], 0)
        self.assertEqual(result["REAL_COMMISSION_REVENUE"], 0)
        self.assertEqual(result["REAL_CUSTOMERS"], 0)
        self.assertEqual(result["REAL_DEALS"], 0)
        self.assertEqual(result["REAL_PAYOUTS"], 0)

    def test_false_when_only_test_or_simulation_records_exist(self):
        cl.record_commission("p", "o", "PAID", 500.0, "TEST", ledger_path=self.path)
        cl.record_commission("p", "o", "PAID", 500.0, "SIMULATION", ledger_path=self.path)
        result = cl.first_real_dollar_status(ledger_path=self.path)
        self.assertFalse(result["FIRST_REAL_DOLLAR"])

    def test_false_when_real_but_only_expected_or_pending(self):
        cl.record_commission("p", "o", "EXPECTED", 500.0, "REAL", evidence="real evidence", ledger_path=self.path)
        result = cl.first_real_dollar_status(ledger_path=self.path)
        self.assertFalse(result["FIRST_REAL_DOLLAR"])
        self.assertEqual(result["REAL_REVENUE"], 0)

    def test_true_only_after_real_confirmed_with_evidence(self):
        cl.record_commission("p", "o", "CONFIRMED", 500.0, "REAL", evidence="real webhook event",
                              external_transaction_id="txn_real_1", customer_id="cust_1", deal_id="deal_1", ledger_path=self.path)
        result = cl.first_real_dollar_status(ledger_path=self.path)
        self.assertTrue(result["FIRST_REAL_DOLLAR"])
        self.assertEqual(result["REAL_REVENUE"], 500.0)
        self.assertEqual(result["REAL_CUSTOMERS"], 1)
        self.assertEqual(result["REAL_DEALS"], 1)
        self.assertEqual(len(result["evidence"]), 1)

    def test_real_payouts_only_counts_paid_not_confirmed(self):
        cl.record_commission("p", "o", "CONFIRMED", 500.0, "REAL", evidence="real evidence", external_transaction_id="txn_1", ledger_path=self.path)
        result = cl.first_real_dollar_status(ledger_path=self.path)
        self.assertTrue(result["FIRST_REAL_DOLLAR"])
        self.assertEqual(result["REAL_PAYOUTS"], 0)


class TestDuplicateCommissionGuard(unittest.TestCase):
    """Phase 38b ('Chief Commercial Engineer' directive, ADR-234), Section 13."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "ledger.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_same_real_transaction_id_recorded_twice_raises(self):
        cl.record_commission("p", "o", "CONFIRMED", 100.0, "REAL", evidence="real evidence 1",
                              external_transaction_id="txn_1", ledger_path=self.path)
        with self.assertRaises(cl.DuplicateCommissionError):
            cl.record_commission("p", "o", "CONFIRMED", 100.0, "REAL", evidence="real evidence 2",
                                  external_transaction_id="txn_1", ledger_path=self.path)

    def test_duplicate_check_never_writes_the_second_record(self):
        cl.record_commission("p", "o", "CONFIRMED", 100.0, "REAL", evidence="real evidence 1",
                              external_transaction_id="txn_1", ledger_path=self.path)
        try:
            cl.record_commission("p", "o", "CONFIRMED", 999.0, "REAL", evidence="real evidence 2",
                                  external_transaction_id="txn_1", ledger_path=self.path)
        except cl.DuplicateCommissionError:
            pass
        records = cl.load_ledger(self.path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["gross_commission"], 100.0)

    def test_same_transaction_id_in_test_environment_never_blocked(self):
        """TEST/SIMULATION records carry no real financial claim -- a
        repeated test transaction_id is harmless."""
        cl.record_commission("p", "o", "PAID", 100.0, "TEST", external_transaction_id="txn_test", ledger_path=self.path)
        cl.record_commission("p", "o", "PAID", 100.0, "TEST", external_transaction_id="txn_test", ledger_path=self.path)
        records = cl.load_ledger(self.path)
        self.assertEqual(len(records), 2)

    def test_different_real_transaction_ids_both_succeed(self):
        cl.record_commission("p", "o", "CONFIRMED", 100.0, "REAL", evidence="real evidence 1",
                              external_transaction_id="txn_a", ledger_path=self.path)
        cl.record_commission("p", "o", "CONFIRMED", 200.0, "REAL", evidence="real evidence 2",
                              external_transaction_id="txn_b", ledger_path=self.path)
        records = cl.load_ledger(self.path)
        self.assertEqual(len(records), 2)

    def test_duplicate_check_does_not_apply_across_different_ledgers(self):
        other_path = os.path.join(self._tmpdir.name, "other_ledger.jsonl")
        cl.record_commission("p", "o", "CONFIRMED", 100.0, "REAL", evidence="real evidence",
                              external_transaction_id="txn_shared", ledger_path=self.path)
        # A different real ledger file is a genuinely separate real store -- no cross-file dedup claimed.
        record = cl.record_commission("p", "o", "CONFIRMED", 100.0, "REAL", evidence="real evidence",
                                       external_transaction_id="txn_shared", ledger_path=other_path)
        self.assertIsNotNone(record)


if __name__ == "__main__":
    unittest.main()

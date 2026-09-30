"""Tier-1 tests: outcome classification + idempotency gate (no blind retry)."""
import unittest

import execution_outcome as eo


class TestClassify(unittest.TestCase):
    def test_never_started(self):
        self.assertEqual(eo.classify_outcome({"started": False}), "NOT_STARTED")
        self.assertEqual(eo.classify_outcome({}), "NOT_STARTED")
        self.assertEqual(eo.classify_outcome(None), "NOT_STARTED")

    def test_clean_completion(self):
        self.assertEqual(eo.classify_outcome(
            {"started": True, "completed_clean": True}), "COMPLETED")

    def test_partial_bytes(self):
        self.assertEqual(eo.classify_outcome(
            {"started": True, "response_bytes": 512}), "PARTIAL")

    def test_error_after_start(self):
        self.assertEqual(eo.classify_outcome(
            {"started": True, "error": "socket closed"}), "STARTED_NOT_COMPLETED")

    def test_ambiguous_is_unknown(self):
        self.assertEqual(eo.classify_outcome({"started": True}), "UNKNOWN")
        self.assertEqual(eo.classify_outcome(
            {"started": True, "completed_clean": True, "incomplete": True}), "UNKNOWN")


class TestGate(unittest.TestCase):
    def test_retry_only_when_idempotent_and_known(self):
        self.assertTrue(eo.idempotency_check(True, True)["retry_allowed"])
        self.assertFalse(eo.idempotency_check(True, False)["retry_allowed"])
        self.assertFalse(eo.idempotency_check(False, True)["retry_allowed"])
        self.assertFalse(eo.idempotency_check()["retry_allowed"])

    def test_policy_matrix(self):
        self.assertEqual(eo.retry_policy("NOT_STARTED")["decision"], "ALLOW")
        self.assertEqual(eo.retry_policy("COMPLETED")["decision"], "HOLD")
        self.assertEqual(
            eo.retry_policy("UNKNOWN", True, True)["decision"], "ALLOW")
        self.assertEqual(
            eo.retry_policy("UNKNOWN", True, False)["decision"], "HOLD")
        self.assertEqual(
            eo.retry_policy("PARTIAL", False, True)["decision"], "HOLD")


class TestBudgetAndCircuit(unittest.TestCase):
    def test_budget(self):
        self.assertFalse(eo.retry_budget_exceeded(0))
        self.assertFalse(eo.retry_budget_exceeded(2))
        self.assertTrue(eo.retry_budget_exceeded(3))
        self.assertTrue(eo.retry_budget_exceeded(99))

    def test_circuit(self):
        self.assertEqual(eo.circuit_check(0)["circuit"], "CLOSED")
        self.assertEqual(eo.circuit_check(4)["circuit"], "CLOSED")
        opened = eo.circuit_check(5)
        self.assertEqual(opened["circuit"], "OPEN")
        self.assertEqual(opened["action"], "HOLD")


if __name__ == "__main__":
    unittest.main()

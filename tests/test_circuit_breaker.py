"""Tests for circuit_breaker.py (Founder Directive, Phase A, 2026-08-20):
the authoritative CircuitBreakerState execution-isolation state machine.

Runs with stdlib unittest. Never touches the real
data/circuit_breaker_state.json -- every test passes an explicit temp state
path.

    python -m unittest tests.test_circuit_breaker -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from circuit_breaker import (
    CircuitBreakerState, CLOSED, ISOLATED, HALF_OPEN, FAILURE_THRESHOLD,
    current_state, allow_execution, is_isolated, reset, record_failure,
    record_success, enter_half_open, record_recovery_success,
    record_recovery_failure, list_circuit_breaker_status,
)


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


class BaseCircuitBreakerTest(unittest.TestCase):
    def setUp(self):
        self.state_path = _temp_path()
        self.cb = CircuitBreakerState(state_path=self.state_path)

    def tearDown(self):
        if os.path.exists(self.state_path):
            os.remove(self.state_path)


class TestTransitions(BaseCircuitBreakerTest):
    def test_normal_starts_closed(self):
        rec = self.cb.current("some_path")
        self.assertEqual(rec["state"], CLOSED)
        self.assertEqual(rec["consecutive_failures"], 0)

    def test_three_verified_failures_isolate(self):
        self.cb.record_failure("pipeline_a", "failure 1")
        self.cb.record_failure("pipeline_a", "failure 2")
        self.cb.record_failure("pipeline_a", "failure 3")
        rec = self.cb.current("pipeline_a")
        self.assertEqual(rec["state"], ISOLATED)
        self.assertEqual(rec["consecutive_failures"], FAILURE_THRESHOLD)
        self.assertFalse(self.cb.allow_execution("pipeline_a"))
        self.assertTrue(self.cb.is_isolated("pipeline_a"))

    def test_two_failures_keep_closed_and_allow_execution(self):
        self.cb.record_failure("pipeline_a", "failure 1")
        self.cb.record_failure("pipeline_a", "failure 2")
        rec = self.cb.current("pipeline_a")
        self.assertEqual(rec["state"], CLOSED)
        self.assertTrue(self.cb.allow_execution("pipeline_a"))
        self.assertFalse(self.cb.is_isolated("pipeline_a"))

    def test_success_before_threshold_resets_failures(self):
        self.cb.record_failure("pipeline_a", "failure 1")
        self.cb.record_failure("pipeline_a", "failure 2")
        self.cb.record_success("pipeline_a")
        rec = self.cb.current("pipeline_a")
        self.assertEqual(rec["state"], CLOSED)
        self.assertEqual(rec["consecutive_failures"], 0)

    def test_half_open_is_controlled_retry_from_isolated(self):
        self.cb.record_failure("pipeline_a", "f1")
        self.cb.record_failure("pipeline_a", "f2")
        self.cb.record_failure("pipeline_a", "f3")
        rec = self.cb.enter_half_open("pipeline_a")
        self.assertEqual(rec["state"], HALF_OPEN)
        self.assertEqual(rec["recovery_attempts"], 1)
        self.assertTrue(self.cb.allow_execution("pipeline_a"))

    def test_successful_recovery_returns_closed(self):
        self.cb.record_failure("pipeline_a", "f1")
        self.cb.record_failure("pipeline_a", "f2")
        self.cb.record_failure("pipeline_a", "f3")
        self.cb.enter_half_open("pipeline_a")
        rec = self.cb.record_recovery_success("pipeline_a")
        self.assertEqual(rec["state"], CLOSED)
        self.assertEqual(rec["consecutive_failures"], 0)
        self.assertTrue(self.cb.allow_execution("pipeline_a"))

    def test_failed_recovery_returns_isolated(self):
        self.cb.record_failure("pipeline_a", "f1")
        self.cb.record_failure("pipeline_a", "f2")
        self.cb.record_failure("pipeline_a", "f3")
        self.cb.enter_half_open("pipeline_a")
        rec = self.cb.record_recovery_failure("pipeline_a", "probe failed")
        self.assertEqual(rec["state"], ISOLATED)
        self.assertFalse(self.cb.allow_execution("pipeline_a"))
        self.assertTrue(self.cb.is_isolated("pipeline_a"))

    def test_enter_half_open_requires_isolated(self):
        with self.assertRaises(ValueError):
            self.cb.enter_half_open("pipeline_a")  # still CLOSED

    def test_recovery_success_requires_half_open(self):
        with self.assertRaises(ValueError):
            self.cb.record_recovery_success("pipeline_a")

    def test_reset_returns_normal_closed(self):
        self.cb.record_failure("pipeline_a", "f1")
        self.cb.record_failure("pipeline_a", "f2")
        self.cb.record_failure("pipeline_a", "f3")
        rec = self.cb.reset("pipeline_a", triggered_by="founder")
        self.assertEqual(rec["state"], CLOSED)
        self.assertEqual(rec["consecutive_failures"], 0)
        self.assertEqual(rec["triggered_by"], "founder")
        self.assertTrue(self.cb.allow_execution("pipeline_a"))

    def test_breakers_are_independent(self):
        self.cb.record_failure("pipeline_a", "f1")
        self.cb.record_failure("pipeline_a", "f2")
        self.cb.record_failure("pipeline_a", "f3")
        self.assertTrue(self.cb.is_isolated("pipeline_a"))
        self.assertFalse(self.cb.is_isolated("pipeline_b"))


class TestPersistence(BaseCircuitBreakerTest):
    def test_state_survives_new_instance(self):
        self.cb.record_failure("pipeline_a", "f1")
        self.cb.record_failure("pipeline_a", "f2")
        self.cb.record_failure("pipeline_a", "f3")
        fresh = CircuitBreakerState(state_path=self.state_path)
        self.assertTrue(fresh.is_isolated("pipeline_a"))
        rec = fresh.current("pipeline_a")
        self.assertEqual(rec["state"], ISOLATED)

    def test_missing_file_is_safe_default(self):
        rec = self.cb.current("nobody_home")
        self.assertEqual(rec["state"], CLOSED)
        self.assertTrue(self.cb.allow_execution("nobody_home"))

    def test_corrupt_file_falls_back_to_default_never_raises(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        rec = self.cb.current("pipeline_a")
        self.assertEqual(rec["state"], CLOSED)


class TestModuleLevelWrappers(BaseCircuitBreakerTest):
    def test_wrappers_delegate_to_authoritative_class(self):
        record_failure("pipeline_a", "f1", state_path=self.state_path)
        record_failure("pipeline_a", "f2", state_path=self.state_path)
        record_failure("pipeline_a", "f3", state_path=self.state_path)
        self.assertTrue(is_isolated("pipeline_a", state_path=self.state_path))
        self.assertFalse(allow_execution("pipeline_a", state_path=self.state_path))
        enter_half_open("pipeline_a", state_path=self.state_path)
        self.assertEqual(current_state("pipeline_a", state_path=self.state_path)["state"], HALF_OPEN)
        record_recovery_success("pipeline_a", state_path=self.state_path)
        self.assertEqual(current_state("pipeline_a", state_path=self.state_path)["state"], CLOSED)
        reset("pipeline_a", state_path=self.state_path)
        self.assertTrue(allow_execution("pipeline_a", state_path=self.state_path))

    def test_list_status_is_read_only_view(self):
        self.cb.record_failure("pipeline_a", "f1")
        status = list_circuit_breaker_status(state_path=self.state_path)
        self.assertEqual(status["threshold"], FAILURE_THRESHOLD)
        self.assertIn("pipeline_a", status["breakers"])
        self.assertEqual(status["breakers"]["pipeline_a"]["state"], CLOSED)


class TestNoAutomaticRetirementOrSideEffects(BaseCircuitBreakerTest):
    def test_isolating_never_retires_an_agent(self):
        # Isolating execution must not touch any agent/retirement state.
        self.cb.record_failure("pipeline_a", "f1")
        self.cb.record_failure("pipeline_a", "f2")
        self.cb.record_failure("pipeline_a", "f3")
        self.assertTrue(self.cb.is_isolated("pipeline_a"))
        # The breaker's own state holds nothing resembling a retirement record.
        rec = self.cb.current("pipeline_a")
        self.assertNotIn("retired", rec)
        self.assertNotIn("agent_retired", rec)

    def test_breaker_never_touches_financial_truth(self):
        import circuit_breaker as cb_mod
        source = Path(cb_mod.__file__).read_text(encoding="utf-8")
        for banned in ("finance_data.json", "sales_ledger", "spend(", "transfer(", "publish("):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
"""Tests for reality_audit.py (Enterprise Truth Audit, ADR-162,
2026-07-31): the classification engine itself -- fast, mocked, never
re-running the real 147-endpoint live audit (that's a ~11-minute,
real-network-touching operation, run manually / via the ADR's own
one-off script, not part of the regular test suite).

    python -m unittest tests.test_reality_audit -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import reality_audit as ra


class TestWriteEndpointSafetyGate(unittest.TestCase):
    def test_flags_a_real_write_pattern(self):
        def fake_resolve_recovery():
            from recovery.startup_check import resolve_recovery
            return resolve_recovery()
        unsafe, pattern = ra._is_write_endpoint(fake_resolve_recovery)
        self.assertTrue(unsafe)

    def test_does_not_flag_a_pure_read(self):
        def fake_read_only():
            from decision_engine import ranking
            return ranking.rank_all()
        unsafe, pattern = ra._is_write_endpoint(fake_read_only)
        self.assertFalse(unsafe)


class TestClassifyFromResult(unittest.TestCase):
    def test_real_simulation_tag_is_classified_simulation(self):
        result = {"simulation": True, "current_stage": "stage_2"}
        classification, evidence = ra._classify_from_result(result, 1.0)
        self.assertEqual(classification, "SIMULATION")

    def test_mentioning_the_word_simulation_in_prose_is_not_flagged(self):
        # Regression test for the real false-positive this ADR's own
        # research caught: truth_first.CANONICAL_VOCABULARY's own
        # definition text for the term "SIMULATION" must never trip
        # the classifier on a bare substring match.
        result = {"canonical_vocabulary": {"SIMULATION": "This output is a real, disclosed hypothetical."}}
        classification, evidence = ra._classify_from_result(result, 1.0)
        self.assertEqual(classification, "REAL")

    def test_honestly_empty_real_result_is_real_not_architecture_only(self):
        # Regression test for the real bug this ADR's own audit run
        # caught and fixed: a real, honestly-empty result ({"entries": []})
        # is proof of real working code, never a sign of a stub.
        result = {"entries": []}
        classification, evidence = ra._classify_from_result(result, 0.5)
        self.assertEqual(classification, "REAL")

    def test_dominated_by_honest_gap_markers_is_architecture_only(self):
        result = {"a": "NOT_ARCHITECTED", "b": "NOT_ARCHITECTED", "c": "NOT_ARCHITECTED", "d": "NOT_ARCHITECTED", "e": "NOT_ARCHITECTED"}
        classification, evidence = ra._classify_from_result(result, 0.5)
        self.assertEqual(classification, "ARCHITECTURE_ONLY")


class TestCallWithTimeout(unittest.TestCase):
    def test_fast_function_returns_normally(self):
        outcome = ra._call_with_timeout(lambda: 42, 5)
        self.assertFalse(outcome["timed_out"])
        self.assertEqual(outcome["result"], 42)

    def test_slow_function_times_out(self):
        import time
        outcome = ra._call_with_timeout(lambda: time.sleep(5), 0.2)
        self.assertTrue(outcome["timed_out"])

    def test_raising_function_captures_the_error(self):
        def raiser():
            raise ValueError("real error")
        outcome = ra._call_with_timeout(raiser, 5)
        self.assertFalse(outcome["timed_out"])
        self.assertIsInstance(outcome["error"], ValueError)


class TestClassifyEndpoint(unittest.TestCase):
    def test_write_flagged_endpoint_is_not_live_invoked(self):
        called = {"n": 0}

        def fake_approve():
            called["n"] += 1
            return {"approved": True}
        fake_approve.__doc__ = None
        # Force the source scan to see a write pattern regardless of
        # this test's own thin wrapper source.
        import inspect
        original_getsource = inspect.getsource
        try:
            inspect.getsource = lambda f: "def _x():\n    approve_proposal()\n"
            result = ra.classify_endpoint("fake_approve", fake_approve)
        finally:
            inspect.getsource = original_getsource
        self.assertFalse(result["live_invoked"])
        self.assertEqual(called["n"], 0)

    def test_parameter_required_error_classified_real(self):
        def needs_niche():
            raise ValueError("{ niche } is required")
        result = ra.classify_endpoint("needs_niche", needs_niche)
        self.assertEqual(result["classification"], "REAL")
        self.assertTrue(result["live_invoked"])

    def test_unexpected_error_classified_not_implemented(self):
        def broken():
            raise AttributeError("module has no attribute 'x'")
        result = ra.classify_endpoint("broken", broken)
        self.assertEqual(result["classification"], "NOT_IMPLEMENTED")


class TestRealityScore(unittest.TestCase):
    def test_computed_directly_no_estimates(self):
        results = [
            {"classification": "REAL"}, {"classification": "REAL"},
            {"classification": "SIMULATION"}, {"classification": "ARCHITECTURE_ONLY"},
        ]
        score = ra.reality_score(results)
        self.assertEqual(score["total"], 4)
        self.assertEqual(score["counts"]["REAL"], 2)
        self.assertEqual(score["percentages"]["REAL"], 50.0)

    def test_empty_input_honestly_reports_zero(self):
        score = ra.reality_score([])
        self.assertEqual(score["total"], 0)


class TestTechnicalDebtRegister(unittest.TestCase):
    def test_only_includes_architecture_only_and_not_implemented(self):
        ledger = [
            {"name": "a", "classification": "REAL", "dependencies": []},
            {"name": "b", "classification": "ARCHITECTURE_ONLY", "dependencies": []},
            {"name": "c", "classification": "NOT_IMPLEMENTED", "dependencies": []},
            {"name": "d", "classification": "SIMULATION", "dependencies": []},
        ]
        debt = ra.technical_debt_register(ledger)
        self.assertEqual({e["name"] for e in debt}, {"b", "c"})

    def test_honestly_empty_when_no_debt_exists(self):
        ledger = [{"name": "a", "classification": "REAL", "dependencies": []}]
        debt = ra.technical_debt_register(ledger)
        self.assertEqual(debt, [])

    def test_never_a_fabricated_priority_no_missing_dimensions(self):
        ledger = [{"name": "a", "classification": "ARCHITECTURE_ONLY", "dependencies": ["customer_pipeline"]}]
        debt = ra.technical_debt_register(ledger)
        scoring = debt[0]["debt_scoring"]
        for dim in ("business_impact", "architectural_importance", "legal_risk", "customer_trust_risk", "implementation_effort_proxy", "composite_score"):
            self.assertIn(dim, scoring)


if __name__ == "__main__":
    unittest.main()

"""Tests for truth_registry.py (Enterprise Truth Registry, ADR-168,
2026-07-31): every per-component field must trace to a real, injectable
signal -- these tests use small, controlled fixtures rather than the
full 246-module/152-endpoint live scan (covered separately by manual
live verification, documented in the ADR).

    python -m unittest tests.test_truth_registry -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import truth_registry as tr


class TestStatusFor(unittest.TestCase):
    def test_no_endpoint_hits_is_honestly_unknown(self):
        status, reason = tr._status_for("nonexistent_module", {})
        self.assertEqual(status, "UNKNOWN")
        self.assertIn("No reality_audit.py-classified", reason)

    def test_real_live_invoked_hit_is_ready(self):
        hits = {"foo": [{"name": "e1", "classification": "REAL", "live_invoked": True}]}
        status, reason = tr._status_for("foo", hits)
        self.assertEqual(status, "READY")

    def test_real_not_live_invoked_is_not_ready(self):
        hits = {"foo": [{"name": "e1", "classification": "REAL", "live_invoked": False}]}
        status, reason = tr._status_for("foo", hits)
        self.assertNotEqual(status, "READY")

    def test_simulation_hit_is_partial(self):
        hits = {"foo": [{"name": "e1", "classification": "SIMULATION", "live_invoked": True}]}
        status, reason = tr._status_for("foo", hits)
        self.assertEqual(status, "PARTIAL")

    def test_deprecated_hit_wins_over_real(self):
        hits = {"foo": [
            {"name": "e1", "classification": "DEPRECATED", "live_invoked": True},
            {"name": "e2", "classification": "REAL", "live_invoked": True},
        ]}
        status, reason = tr._status_for("foo", hits)
        self.assertEqual(status, "DEPRECATED")


class TestBusinessCriticality(unittest.TestCase):
    def test_finance_keyword_is_critical(self):
        crit, note = tr._business_criticality_for("channels.ledger", "channels/ledger.py")
        self.assertEqual(crit, "CRITICAL")

    def test_decision_engine_keyword_is_high(self):
        crit, note = tr._business_criticality_for("decision_engine.engine", "decision_engine/engine.py")
        self.assertEqual(crit, "HIGH")

    def test_no_keyword_match_is_honestly_unknown(self):
        crit, note = tr._business_criticality_for("some_random_util", "some_random_util.py")
        self.assertEqual(crit, "UNKNOWN")


class TestTestCoverageFor(unittest.TestCase):
    def test_real_test_file_is_partial(self):
        cov, note = tr._test_coverage_for("truth_registry")
        self.assertEqual(cov, "PARTIAL")

    def test_no_test_file_is_none(self):
        cov, note = tr._test_coverage_for("a_module_with_definitely_no_test_file_xyz")
        self.assertEqual(cov, "NONE")

    def test_full_is_never_assigned(self):
        # No coverage.py line-coverage tool is wired into this factory --
        # FULL must never appear regardless of input.
        for name in ("truth_registry", "server", "book_generator", "anything_xyz"):
            cov, _ = tr._test_coverage_for(name)
            self.assertIn(cov, ("PARTIAL", "NONE"))


class TestConfidenceScore(unittest.TestCase):
    def test_every_factor_present_reaches_100(self):
        entry = {
            "purpose": "Real docstring.",
            "test_coverage": "PARTIAL",
            "production_usage": "YES",
            "live_verified": "YES",
            "last_commit": {"date": "2026-07-31T00:00:00Z"},
        }
        score, factors = tr._confidence_score(entry)
        self.assertEqual(score, 100)
        self.assertEqual(len(factors), 5)

    def test_no_factors_is_zero_never_fabricated(self):
        entry = {
            "purpose": "UNKNOWN -- no real module docstring present",
            "test_coverage": "NONE",
            "production_usage": "UNKNOWN",
            "live_verified": "NO",
            "last_commit": {"date": None},
        }
        score, factors = tr._confidence_score(entry)
        self.assertEqual(score, 0)
        self.assertEqual(factors, [])


class TestDuplicateBasenames(unittest.TestCase):
    def test_init_py_excluded_as_structural_not_duplication(self):
        registry = [
            {"location": "a/__init__.py"},
            {"location": "b/__init__.py"},
            {"location": "c/registry.py"},
            {"location": "d/registry.py"},
        ]
        dups = tr._duplicate_basenames(registry)
        self.assertNotIn("__init__.py", dups)
        self.assertIn("registry.py", dups)

    def test_unique_basenames_not_flagged(self):
        registry = [{"location": "a/foo.py"}, {"location": "b/bar.py"}]
        self.assertEqual(tr._duplicate_basenames(registry), {})


class TestReachableFromProduction(unittest.TestCase):
    def test_transitive_closure_real_bfs(self):
        graph = {"a": ["b"], "b": ["c"], "c": []}
        reachable = tr._reachable_from_production({"a"}, graph)
        self.assertEqual(reachable, {"a", "b", "c"})

    def test_unreachable_module_excluded(self):
        graph = {"a": ["b"], "b": [], "unreachable_module": []}
        reachable = tr._reachable_from_production({"a"}, graph)
        self.assertNotIn("unreachable_module", reachable)


class TestBuildTruthRegistryReport(unittest.TestCase):
    def test_never_asserts_reconstructable_yes(self):
        fake_registry = [{
            "name": "x", "category": "root", "purpose": "p", "location": "x.py",
            "owner": "Unassigned", "dependencies": [], "dependents": [],
            "status": "READY", "status_reason": "r", "production_usage": "YES",
            "production_usage_note": "n", "live_verified": "YES",
            "live_verified_evidence": "e", "test_coverage": "PARTIAL",
            "test_coverage_note": "n", "last_verification": "2026-07-31",
            "last_commit": {"date": "2026-07-31", "commit": "abc"},
            "business_criticality": "LOW", "business_criticality_note": "n",
            "confidence_score": 100, "confidence_factors": [],
        }]
        report = tr.build_truth_registry_report(registry=fake_registry)
        self.assertEqual(report["reconstructable_from_registry_alone"]["answer"], "NO")
        self.assertGreater(len(report["reconstructable_from_registry_alone"]["missing"]), 0)

    def test_truth_score_bounded_0_to_100(self):
        fake_registry = [{
            "name": "x", "category": "root", "purpose": "UNKNOWN -- no real module docstring present",
            "location": "x.py", "owner": "Unassigned", "dependencies": [], "dependents": [],
            "status": "UNKNOWN", "status_reason": "r", "production_usage": "UNKNOWN",
            "production_usage_note": "n", "live_verified": "NO", "live_verified_evidence": None,
            "test_coverage": "NONE", "test_coverage_note": "n",
            "last_verification": "NEVER -- no real live-verification event exists for this module in this scan",
            "last_commit": {"date": None, "commit": None}, "business_criticality": "UNKNOWN",
            "business_criticality_note": "n", "confidence_score": 0, "confidence_factors": [],
        }]
        report = tr.build_truth_registry_report(registry=fake_registry)
        self.assertGreaterEqual(report["10_enterprise_truth_score"]["score_0_to_100"], 0)
        self.assertLessEqual(report["10_enterprise_truth_score"]["score_0_to_100"], 100)


if __name__ == "__main__":
    unittest.main()

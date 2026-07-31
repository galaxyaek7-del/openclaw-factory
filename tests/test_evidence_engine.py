"""Tests for evidence_engine.py (Enterprise Evidence Engine, ADR-163,
2026-07-31): a real, immutable, append-only evidence framework -- never
a fabricated compliance/coverage claim.

    python -m unittest tests.test_evidence_engine -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import evidence_engine as ee


class TestRecordAndReadEvidence(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "evidence.jsonl")
            ee.record_evidence("TEST", "test_module", "in", "out", 5.0, True, ledger_path=path)
            entries = ee.read_evidence(ledger_path=path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["evidence_type"], "TEST")
            self.assertTrue(entries[0]["evidence_id"])

    def test_rejects_unknown_evidence_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "evidence.jsonl")
            with self.assertRaises(ValueError):
                ee.record_evidence("NOT_A_REAL_TYPE", "m", "i", "o", 1.0, True, ledger_path=path)

    def test_append_only_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "evidence.jsonl")
            ee.record_evidence("TEST", "m", "i1", "o1", 1.0, True, ledger_path=path)
            ee.record_evidence("TEST", "m", "i2", "o2", 1.0, True, ledger_path=path)
            entries = ee.read_evidence(ledger_path=path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["input"], "i1")
            self.assertEqual(entries[1]["input"], "i2")

    def test_filters_by_type_and_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "evidence.jsonl")
            ee.record_evidence("TEST", "mod_a", "i", "o", 1.0, True, ledger_path=path)
            ee.record_evidence("SYSTEM", "mod_b", "i", "o", 1.0, True, ledger_path=path)
            self.assertEqual(len(ee.read_evidence(evidence_type="TEST", ledger_path=path)), 1)
            self.assertEqual(len(ee.read_evidence(module="mod_b", ledger_path=path)), 1)


class TestMakeEvidenceId(unittest.TestCase):
    def test_deterministic(self):
        id1 = ee.make_evidence_id("TEST", "m", "2026-01-01T00:00:00Z", "input")
        id2 = ee.make_evidence_id("TEST", "m", "2026-01-01T00:00:00Z", "input")
        self.assertEqual(id1, id2)

    def test_different_inputs_different_ids(self):
        id1 = ee.make_evidence_id("TEST", "m", "t", "input1")
        id2 = ee.make_evidence_id("TEST", "m", "t", "input2")
        self.assertNotEqual(id1, id2)


class TestVerify(unittest.TestCase):
    def test_honestly_not_verified_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "does_not_exist.jsonl")
            result = ee.verify(ledger_path=path)
            self.assertEqual(result["verification_status"], ee.NOT_VERIFIED)
            self.assertEqual(result["evidence_count"], 0)
            self.assertIsNone(result["last_verified"])

    def test_verified_when_evidence_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "evidence.jsonl")
            ee.record_evidence("TEST", "m", "i", "o", 1.0, True, ledger_path=path)
            result = ee.verify(ledger_path=path)
            self.assertEqual(result["verification_status"], "VERIFIED")
            self.assertEqual(result["evidence_count"], 1)
            self.assertIsNotNone(result["last_verified"])


class TestEvidenceCoverageReport(unittest.TestCase):
    def test_covers_all_10_named_types(self):
        report = ee.evidence_coverage_report()
        self.assertEqual(set(report["coverage"].keys()), set(ee.EVIDENCE_TYPES))

    def test_never_fabricates_a_source_for_a_type_with_none(self):
        report = ee.evidence_coverage_report()
        for etype, c in report["coverage"].items():
            if not c["has_existing_evidence"]:
                self.assertEqual(c["existing_real_sources"], [])


class TestCheckUnsupportedCompletionClaims(unittest.TestCase):
    def test_no_text_is_honestly_unknown(self):
        result = ee.check_unsupported_completion_claims(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_clean_text_passes(self):
        result = ee.check_unsupported_completion_claims("A helpful guide to morning routines.")
        self.assertEqual(result["status"], "PASS")

    def test_unsupported_completion_claim_fails(self):
        result = ee.check_unsupported_completion_claims("The system is fully Operational and Production Ready.")
        self.assertEqual(result["status"], "FAIL")

    def test_claim_with_evidence_citation_passes(self):
        result = ee.check_unsupported_completion_claims("The system is Operational. evidence_id: abc123")
        self.assertEqual(result["status"], "PASS")


class TestDecisionTransparency(unittest.TestCase):
    def test_returns_all_5_named_fields(self):
        fake_explanation = {
            "found": True, "evidence_used": {"a": "NOT_ARCHITECTED"}, "confidence": "high",
            "conflict_check": {"conflict": False}, "tier": 1,
        }
        result = ee.decision_transparency("fake_id", explanation=fake_explanation)
        for field in ("evidence_used", "confidence", "missing_evidence", "risk_level", "unknown_assumptions"):
            self.assertIn(field, result)

    def test_missing_evidence_detects_real_gap_terms(self):
        # Only the 9 canonical Truth First terms (ADR-160) are matched --
        # grandfathered pre-ADR-160 variants like "NOT_ARCHITECTED" are
        # deliberately NOT retrofitted/matched here, same discipline.
        fake_explanation = {
            "found": True, "evidence_used": {"a": "NOT BUILT", "b": "UNKNOWN"}, "confidence": "low",
        }
        result = ee.decision_transparency("fake_id", explanation=fake_explanation)
        self.assertIn("NOT BUILT", result["missing_evidence"]["answer"])
        self.assertIn("UNKNOWN", result["missing_evidence"]["answer"])

    def test_not_found_passes_through_honestly(self):
        fake_explanation = {"found": False, "reason": "no such decision"}
        result = ee.decision_transparency("fake_id", explanation=fake_explanation)
        self.assertFalse(result["found"])


if __name__ == "__main__":
    unittest.main()

"""Tests for truth_first.py (Truth First Constitution, ADR-160,
2026-07-31): a real, mechanical vocabulary census + compliance report
citing already-real controls -- never a fabricated compliance score.

    python -m unittest tests.test_truth_first -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import truth_first
import executive_quality_gate as eqg


class TestCanonicalVocabulary(unittest.TestCase):
    def test_has_all_9_named_terms(self):
        expected = {
            "NOT BUILT", "NOT IMPLEMENTED", "NOT CONNECTED", "NOT MEASURED", "UNKNOWN",
            "WAITING FOR REAL DATA", "SIMULATION", "REFERENCE IMPLEMENTATION", "PLANNED",
        }
        self.assertEqual(set(truth_first.CANONICAL_VOCABULARY.keys()), expected)

    def test_every_term_has_a_real_definition(self):
        for term, definition in truth_first.CANONICAL_VOCABULARY.items():
            self.assertTrue(definition and len(definition) > 10, term)


class TestVocabularyCensus(unittest.TestCase):
    def test_finds_a_real_nonzero_count_for_known_common_variants(self):
        result = truth_first.vocabulary_census()
        # Regression-proofs this ADR's own research finding -- these
        # variants are known to be real and heavily used as of ADR-160.
        self.assertGreater(result["counts"]["DISCOVERY"], 0)
        self.assertGreater(result["counts"]["NOT ENOUGH EVIDENCE"], 0)
        self.assertGreater(result["counts"]["NOT_ARCHITECTED"], 0)

    def test_total_instances_is_sum_of_counts(self):
        result = truth_first.vocabulary_census()
        self.assertEqual(result["total_instances"], sum(result["counts"].values()))

    def test_scoped_to_a_temp_dir_finds_zero(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "empty.py"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")
            result = truth_first.vocabulary_census(root_dir=tmp)
            self.assertEqual(result["total_instances"], 0)
            self.assertEqual(result["files_scanned"], 1)

    def test_counts_a_real_known_variant_in_an_isolated_fixture(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "fixture.py"), "w", encoding="utf-8") as f:
                f.write('x = "NOT_ARCHITECTED"\ny = "NOT_ARCHITECTED"\n')
            result = truth_first.vocabulary_census(root_dir=tmp)
            self.assertEqual(result["counts"]["NOT_ARCHITECTED"], 2)
            self.assertEqual(result["total_instances"], 2)


class TestComplianceReport(unittest.TestCase):
    def test_every_field_carries_a_real_source(self):
        fake_census = {"counts": {}, "total_instances": 0, "files_scanned": 0, "generated_at": "x"}
        report = truth_first.truth_first_compliance_report(census=fake_census)
        self.assertTrue(report["simulation_production_separation"]["source"])
        self.assertTrue(report["legal_safety_review_coverage"]["source"])
        self.assertTrue(report["self_audit_subsystems"]["source"])

    def test_legal_safety_review_cites_real_reject_if_fail_tuple(self):
        report = truth_first.truth_first_compliance_report(census={"counts": {}, "total_instances": 0, "files_scanned": 0, "generated_at": "x"})
        self.assertEqual(report["legal_safety_review_coverage"]["hard_reject_pipeline"], eqg.REJECT_IF_FAIL)

    def test_never_fabricates_a_numeric_compliance_score(self):
        report = truth_first.truth_first_compliance_report(census={"counts": {}, "total_instances": 0, "files_scanned": 0, "generated_at": "x"})
        self.assertNotIn("compliance_score", report)
        self.assertNotIn("compliance_pct", report)


class TestCheckCopyrightTrademarkRisk(unittest.TestCase):
    def test_no_content_is_honestly_unknown(self):
        result = eqg.check_copyright_trademark_risk(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_clean_content_passes(self):
        result = eqg.check_copyright_trademark_risk([{"content": "A helpful guide to morning routines."}])
        self.assertEqual(result["status"], "PASS")

    def test_flags_claimed_amazon_partnership(self):
        result = eqg.check_copyright_trademark_risk([{"content": "This product is in partnership with Amazon."}])
        self.assertEqual(result["status"], "FAIL")

    def test_registered_in_reject_if_fail(self):
        self.assertIn("copyright_trademark_risk", eqg.REJECT_IF_FAIL)


if __name__ == "__main__":
    unittest.main()

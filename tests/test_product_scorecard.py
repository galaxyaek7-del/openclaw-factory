"""Tests for product_scorecard -- the measurable gate (directive D).

The most important property to pin is that a HIGH SCORE NEVER CANCELS A
CRITICAL DEFECT, and that UNKNOWN is never treated as PASS. Both are things a
future edit could quietly break, and both are the founder's explicit rule.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import product_scorecard as ps


class _FakeFileResult:
    def __init__(self, status, path="x"):
        self.status = status
        self.path = path
        self.problems = ["synthetic"] if status != "PASS" else []


class _FakeContent:
    def __init__(self, findings):
        self.findings = findings


class _FakeFinding:
    def __init__(self, rule="FABRICATED_CITATION", severity="CRITICAL"):
        self.rule = rule
        self.severity = severity


class _FakeGrounding:
    def __init__(self, violations=None):
        self.violations = violations or []


class TestDefectOverridesScore(unittest.TestCase):
    """The founder's rule: a high score never cancels a critical defect."""

    def _perfect_inputs(self):
        return dict(
            file_results=[_FakeFileResult("PASS")],
            content_result=_FakeContent([]),
            grounding_result=_FakeGrounding(),
            word_stats={"median_chapter_words": 400,
                       "workbooks_tested": 2, "workbooks_without_formulas": 0},
            test_summary={"files_independently_tested": 1, "files_required": 1,
                          "human_specialist_review": True},
            page_result={"unmatched_claims": []},
        )

    def test_perfect_product_passes(self):
        sc = ps.build_scorecard("p", **self._perfect_inputs())
        self.assertGreaterEqual(sc.total, ps.THRESHOLD)
        self.assertEqual(sc.decide(), ps.PASS)

    def test_critical_defect_forces_hold_despite_max_score(self):
        kw = self._perfect_inputs()
        sc = ps.build_scorecard("p", **kw)
        self.assertEqual(sc.decide(), ps.PASS)
        sc.critical_defects.append("fabricated Annex III citation")
        self.assertEqual(sc.decide(), ps.HOLD,
                         "a maxed score must NOT rescue an open defect")

    def test_defect_is_checked_before_score(self):
        kw = self._perfect_inputs()
        sc = ps.build_scorecard("p", **kw)
        sc.critical_defects.append("defect")
        # even if someone manually inflates the total
        for d in sc.dimensions:
            d.earned = d.max_points
        self.assertEqual(sc.decide(), ps.HOLD)


class TestUnknownIsNotPass(unittest.TestCase):
    def test_unknown_file_blocks_verdict(self):
        sc = ps.build_scorecard(
            "p",
            file_results=[_FakeFileResult("UNKNOWN", "missing.xlsx")],
            content_result=_FakeContent([]),
            grounding_result=_FakeGrounding(),
            word_stats={"median_chapter_words": 400},
            test_summary={"files_independently_tested": 1, "files_required": 1,
                          "human_specialist_review": True},
            page_result={"unmatched_claims": []})
        self.assertNotEqual(sc.decide(), ps.PASS)
        self.assertEqual(sc.decide(), ps.HOLD)

    def test_no_files_tested_is_unknown_dimension(self):
        d = ps.dim_files([])
        self.assertEqual(d.status, ps.UNKNOWN)
        self.assertEqual(d.earned, 0)
        # UNKNOWN must carry a reason, so a reviewer can see why it is unknown
        self.assertTrue(d.has_evidence,
                        "an UNKNOWN dimension must explain itself")
        self.assertIn("no files", d.evidence[0])

    def test_unchecked_content_is_unknown_not_pass(self):
        d = ps.dim_accuracy(None, None)
        self.assertEqual(d.status, ps.UNKNOWN)
        self.assertEqual(d.earned, 0)

    def test_missing_human_review_cannot_reach_pass(self):
        sc = ps.build_scorecard(
            "p",
            file_results=[_FakeFileResult("PASS")],
            content_result=_FakeContent([]),
            grounding_result=_FakeGrounding(),
            word_stats={"median_chapter_words": 400},
            test_summary={"files_independently_tested": 1, "files_required": 1,
                          "human_specialist_review": False},
            page_result={"unmatched_claims": []})
        self.assertNotEqual(sc.decide(), ps.PASS)


class TestDimensionScoring(unittest.TestCase):
    def test_all_files_pass_earns_full(self):
        d = ps.dim_files([_FakeFileResult("PASS"), _FakeFileResult("PASS")])
        self.assertEqual(d.earned, 25)
        self.assertEqual(d.status, ps.PASS)

    def test_one_of_two_fails_scores_partial(self):
        d = ps.dim_files([_FakeFileResult("PASS"), _FakeFileResult("FAIL")])
        self.assertLess(d.earned, 25)
        self.assertEqual(d.status, ps.FAIL)

    def test_fabricated_citation_fails_accuracy_outright(self):
        d = ps.dim_accuracy(_FakeContent([_FakeFinding()]), _FakeGrounding())
        self.assertEqual(d.status, ps.FAIL)
        self.assertLessEqual(d.earned, 2)

    def test_grounding_violation_also_fails_accuracy(self):
        d = ps.dim_accuracy(_FakeContent([]),
                            _FakeGrounding(["fabricated legal framing 'Annex III Part A'"]))
        self.assertEqual(d.status, ps.FAIL)

    def test_zero_formula_workbooks_reduce_value(self):
        good = ps.dim_practical_value({"median_chapter_words": 400,
                                       "workbooks_tested": 2,
                                       "workbooks_without_formulas": 0})
        bad = ps.dim_practical_value({"median_chapter_words": 400,
                                      "workbooks_tested": 2,
                                      "workbooks_without_formulas": 2})
        self.assertGreater(good.earned, bad.earned)

    def test_unmatched_sales_claim_fails_presentation(self):
        d = ps.dim_presentation({"unmatched_claims": ["31 pages"]})
        self.assertEqual(d.status, ps.FAIL)
        self.assertLess(d.earned, 15)

    def test_no_value_signal_is_unknown(self):
        d = ps.dim_practical_value({})
        self.assertEqual(d.status, ps.UNKNOWN)


class TestVerdictVocabulary(unittest.TestCase):
    def test_blocked_when_a_dimension_is_blocked(self):
        sc = ps.build_scorecard(
            "p",
            file_results=[_FakeFileResult("PASS")],
            content_result=_FakeContent([]),
            grounding_result=_FakeGrounding(),
            word_stats={"median_chapter_words": 400},
            test_summary={"files_independently_tested": 1, "files_required": 1,
                          "human_specialist_review": True},
            page_result={"unmatched_claims": []})
        sc.dimensions[0].status = ps.BLOCKED
        self.assertEqual(sc.decide(), ps.BLOCKED)

    def test_verdict_is_one_of_the_five_words(self):
        sc = ps.build_scorecard("p", file_results=[], content_result=None,
                                grounding_result=None, word_stats={},
                                test_summary={}, page_result=None)
        self.assertIn(sc.decide(),
                      {ps.PASS, ps.HOLD, ps.BLOCKED, ps.FAIL, ps.UNKNOWN})

    def test_as_dict_is_serialisable(self):
        import json
        sc = ps.build_scorecard("p", file_results=[], content_result=None,
                                grounding_result=None, word_stats={},
                                test_summary={}, page_result=None)
        json.dumps(sc.as_dict())   # must not raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
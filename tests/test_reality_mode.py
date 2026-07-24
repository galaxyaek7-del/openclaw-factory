"""Tests for reality_mode.py (Reality Mode, 2026-07-24): the real
4-level evidence taxonomy (VERIFIED_REALITY/ESTIMATED/SIMULATED/UNKNOWN),
the generic reality_audit() retrofit over any existing report, and the
real, transparent Company Reality Score.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_reality_mode -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import reality_mode as rm
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestConstructors(unittest.TestCase):
    def test_verified_shape(self):
        result = rm.verified(42, "real Paddle transaction")
        self.assertEqual(result["evidence_level"], rm.VERIFIED_REALITY)
        self.assertEqual(result["value"], 42)

    def test_estimated_shape(self):
        result = rm.estimated(42, "ladder-based proxy")
        self.assertEqual(result["evidence_level"], rm.ESTIMATED)

    def test_simulated_shape(self):
        result = rm.simulated(42, "dry run")
        self.assertEqual(result["evidence_level"], rm.SIMULATED)

    def test_unknown_shape_always_has_a_reason(self):
        result = rm.unknown("لا دليل بعد")
        self.assertEqual(result["evidence_level"], rm.UNKNOWN)
        self.assertIsNone(result["value"])
        self.assertTrue(result["reason"])


class TestClassifyExistingField(unittest.TestCase):
    def test_already_tagged_field_is_trusted_verbatim(self):
        self.assertEqual(rm.classify_existing_field({"evidence_level": rm.SIMULATED, "value": 1}), rm.SIMULATED)

    def test_dry_run_marker_is_simulated(self):
        self.assertEqual(rm.classify_existing_field({"dry_run": True, "ok": False}), rm.SIMULATED)

    def test_unknown_answer_shape_is_unknown(self):
        self.assertEqual(rm.classify_existing_field({"answer": "Unknown", "reason": "x"}), rm.UNKNOWN)

    def test_value_none_reason_shape_is_unknown(self):
        self.assertEqual(rm.classify_existing_field({"value": None, "reason": "x"}), rm.UNKNOWN)

    def test_maturity_discovery_is_unknown(self):
        self.assertEqual(rm.classify_existing_field({"maturity": "DISCOVERY"}), rm.UNKNOWN)

    def test_maturity_real_is_verified(self):
        self.assertEqual(rm.classify_existing_field({"maturity": "REAL", "estimated_cost_usd": 0.01}), rm.VERIFIED_REALITY)

    def test_proxy_language_is_estimated(self):
        self.assertEqual(rm.classify_existing_field({"value": "ai_saas", "note": "proxy من مسار الإنتاج"}), rm.ESTIMATED)

    def test_unwrapped_none_is_unknown(self):
        self.assertEqual(rm.classify_existing_field(None), rm.UNKNOWN)

    def test_unwrapped_raw_value_defaults_to_estimated_never_verified(self):
        """Conservative by design -- never claim false certainty for a
        field this classifier cannot actually confirm is a direct
        observation."""
        self.assertEqual(rm.classify_existing_field(85.5), rm.ESTIMATED)


class TestRealityAudit(unittest.TestCase):
    def test_counts_and_paths_are_consistent(self):
        report = {
            "a": rm.verified(1, "x"),
            "b": rm.unknown("y"),
            "nested": {"c": rm.estimated(2, "z")},
        }
        audit = rm.reality_audit(report)
        self.assertEqual(audit["counts"][rm.VERIFIED_REALITY], 1)
        self.assertEqual(audit["counts"][rm.UNKNOWN], 1)
        self.assertEqual(audit["counts"][rm.ESTIMATED], 1)
        self.assertEqual(audit["total_fields"], 3)
        self.assertEqual(audit["paths"][rm.VERIFIED_REALITY], ["a"])

    def test_verified_reality_pct_is_computed_honestly(self):
        report = {"a": rm.verified(1, "x"), "b": rm.unknown("y")}
        audit = rm.reality_audit(report)
        self.assertEqual(audit["verified_reality_pct"], 50.0)

    def test_empty_report_never_divides_by_zero(self):
        audit = rm.reality_audit({})
        self.assertIsNone(audit["verified_reality_pct"])
        self.assertEqual(audit["total_fields"], 0)


class TestComputeCompanyRealityScore(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.evidence_path = _temp_path()
        self.board_path = _temp_path()
        self.db_file = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.evidence_path, self.board_path, self.db_file):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, score=85.0):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": 200, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        engine.record_ladder_decision(niche, "ai_saas", ladder_result, decisions_path=self.decisions_path)

    def test_zero_accepted_reports_honestly(self):
        score = rm.compute_company_reality_score(
            decisions_path=self.decisions_path, evidence_path=self.evidence_path,
            board_path=self.board_path, db_file=self.db_file,
        )
        self.assertIsNone(score["score_pct"])
        self.assertEqual(score["real_accepted_opportunities"], 0)

    def test_no_real_evidence_yet_is_zero_percent(self):
        self._record("a bare niche")
        score = rm.compute_company_reality_score(
            decisions_path=self.decisions_path, evidence_path=self.evidence_path,
            board_path=self.board_path, db_file=self.db_file,
        )
        self.assertEqual(score["score_pct"], 0.0)
        self.assertEqual(score["opportunities_with_real_external_evidence"], 0)

    def test_real_closed_sale_evidence_increases_the_score(self):
        import market_evidence
        self._record("a niche with real evidence")
        market_evidence.record_evidence("a niche with real evidence", "closed_sale", {
            "commercial_event": {"platform": "gumroad", "selling_price": 29.0, "season": "summer"},
        }, evidence_path=self.evidence_path)
        score = rm.compute_company_reality_score(
            decisions_path=self.decisions_path, evidence_path=self.evidence_path,
            board_path=self.board_path, db_file=self.db_file,
        )
        self.assertEqual(score["score_pct"], 100.0)
        self.assertEqual(score["opportunities_with_real_external_evidence"], 1)
        detail = score["detail"][0]
        self.assertTrue(detail["has_market_evidence_events"])


if __name__ == "__main__":
    unittest.main()

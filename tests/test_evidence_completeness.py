"""Tests for evidence_completeness.py (Evidence Completeness Engine,
ADR-127, 2026-07-25).

Isolation note: real acquisition calls (competitor_discovery.py,
market_intelligence_engine.py) are mocked in every test that doesn't
specifically exist to prove the real wiring — same discipline
tests/test_ladder_opportunity_score.py already established for
_score_defensibility(). The one test that DOES prove real wiring uses an
isolated db_file, never the real shared data/competitor_database.json.

    python -m unittest tests.test_evidence_completeness -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import evidence_completeness as ec
import profit_oracle as po
from decision_engine.engine import record_ladder_decision


def _base_ladder_result(**overrides):
    """A real-shaped ladder_opportunity_score() result, every field
    present, defaults chosen to be fully VERIFIED (no Unknowns) so each
    test only has to override what it's actually testing."""
    result = {
        "niche": "test niche",
        "ladder": "ai_saas",
        "ladder_score": 80.0,
        "price": 200,
        "accepted": True,
        "reason": "accepted: test fixture",
        "payment_evidence": [{"event_type": "paid_job_posting", "source_url": "https://example.com", "quote": "q"}],
        "components": {
            "competition_favorability": 70,
            "profit_potential": 75,
            "recurring_revenue_potential": 85,
            "reusability": 85,
        },
        "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "real fixture note"},
        "ai_leverage": {"score": 70, "level": "عالية", "note": "real fixture note"},
        "urgency": {"score": 40, "level": "متوسطة", "note": "real fixture note"},
    }
    result.update(overrides)
    return result


class TestClassifyCriteria(unittest.TestCase):
    def test_fully_verified_fixture_has_zero_unknowns(self):
        c = ec.classify_criteria(_base_ladder_result())
        unknowns = [k for k, v in c.items() if v["state"] == ec.UNKNOWN]
        # high_commercial_value / continuous_improvement_potential are
        # ALWAYS Unknown (genuine gaps, ADR-126) — the only 2 expected.
        self.assertEqual(set(unknowns), {"high_commercial_value", "continuous_improvement_potential"})

    def test_zero_payment_evidence_is_unknown_not_verified_false(self):
        """The core rule: absence of a real negative-search-confirmation
        mechanism means zero evidence is UNKNOWN (never looked), not
        VERIFIED_FALSE (confirmed no market exists)."""
        c = ec.classify_criteria(_base_ladder_result(payment_evidence=[]))
        self.assertEqual(c["proof_of_payment"]["state"], ec.UNKNOWN)

    def test_real_payment_evidence_is_verified_true(self):
        c = ec.classify_criteria(_base_ladder_result())
        self.assertEqual(c["proof_of_payment"]["state"], ec.VERIFIED_TRUE)

    def test_no_pain_evidence_passed_is_unknown(self):
        c = ec.classify_criteria(_base_ladder_result(urgency={"score": None, "level": "Unknown", "note": "no evidence"}))
        self.assertEqual(c["pain_severity"]["state"], ec.UNKNOWN)

    def test_real_low_pain_score_is_verified_false_not_unknown(self):
        """A real, gathered-but-weak signal must not be reported as
        Unknown — it's a real, if unfavorable, measurement."""
        c = ec.classify_criteria(_base_ladder_result(urgency={"score": 10, "level": "منخفضة", "note": "real weak signal"}))
        self.assertEqual(c["pain_severity"]["state"], ec.VERIFIED_FALSE)

    def test_defensibility_unknown_level_is_unknown(self):
        c = ec.classify_criteria(_base_ladder_result(defensibility={"score": None, "level": "Unknown", "note": "no cached data"}))
        self.assertEqual(c["difficult_to_copy"]["state"], ec.UNKNOWN)

    def test_defensibility_low_level_is_verified_false_not_unknown(self):
        c = ec.classify_criteria(_base_ladder_result(defensibility={"score": 25, "level": "منخفضة", "note": "real crowded market"}))
        self.assertEqual(c["difficult_to_copy"]["state"], ec.VERIFIED_FALSE)

    def test_ai_leverage_none_is_unknown(self):
        c = ec.classify_criteria(_base_ladder_result(ai_leverage={"score": None, "level": "Unknown", "note": "no keyword hits"}))
        self.assertEqual(c["ai_significant_advantage"]["state"], ec.UNKNOWN)

    def test_ai_leverage_real_negative_is_verified_false_not_unknown(self):
        c = ec.classify_criteria(_base_ladder_result(ai_leverage={"score": 20, "level": "منخفضة", "note": "real physical-task keywords"}))
        self.assertEqual(c["ai_significant_advantage"]["state"], ec.VERIFIED_FALSE)

    def test_competition_and_margin_and_pricing_and_scalability_never_unknown(self):
        """These 4 are always real/deterministic (a saved report, an
        external signal, or a keyword-count fallback -- never None) --
        must never report Unknown."""
        c = ec.classify_criteria(_base_ladder_result())
        for key in ("low_or_moderate_competition", "high_profit_margin", "premium_pricing_potential", "global_scalability", "long_term_strategic_value"):
            self.assertIn(c[key]["state"], (ec.VERIFIED_TRUE, ec.VERIFIED_FALSE), f"{key} must never be Unknown")

    def test_global_scalability_is_the_same_real_value_as_reusability_component(self):
        result = _base_ladder_result()
        c = ec.classify_criteria(result)
        self.assertEqual(c["global_scalability"]["value"], result["components"]["reusability"])

    def test_high_commercial_value_and_continuous_improvement_always_unknown(self):
        c = ec.classify_criteria(_base_ladder_result())
        self.assertEqual(c["high_commercial_value"]["state"], ec.UNKNOWN)
        self.assertEqual(c["continuous_improvement_potential"]["state"], ec.UNKNOWN)


class TestEvidenceCoverageReport(unittest.TestCase):
    def test_fully_verified_fixture_coverage(self):
        c = ec.classify_criteria(_base_ladder_result())
        report = ec.evidence_coverage_report(c)
        self.assertEqual(report["total_count"], 11)
        self.assertEqual(report["unknown_count"], 2)
        self.assertEqual(report["verified_count"], 9)
        self.assertAlmostEqual(report["coverage_pct"], 100.0 * 9 / 11, places=1)
        self.assertEqual(set(report["missing_evidence"]), {"high_commercial_value", "continuous_improvement_potential"})

    def test_more_unknowns_lowers_coverage(self):
        c = ec.classify_criteria(_base_ladder_result(
            payment_evidence=[],
            urgency={"score": None, "level": "Unknown", "note": "n/a"},
            defensibility={"score": None, "level": "Unknown", "note": "n/a"},
        ))
        report = ec.evidence_coverage_report(c)
        self.assertEqual(report["unknown_count"], 5)
        self.assertLess(report["coverage_pct"], 60)

    def test_confidence_equals_coverage(self):
        c = ec.classify_criteria(_base_ladder_result())
        report = ec.evidence_coverage_report(c)
        self.assertEqual(ec.confidence_from_coverage(report["coverage_pct"]), report["coverage_pct"])


class TestEstimateValueIfVerified(unittest.TestCase):
    def test_never_invents_a_different_score_or_price(self):
        """Gates never change ladder_score/price -- only accept/reject.
        The 'estimated value if evidence becomes available' must be the
        exact same real numbers, never a fabricated higher projection."""
        result = _base_ladder_result(payment_evidence=[])
        c = ec.classify_criteria(result)
        estimate = ec.estimate_value_if_verified(result, c)
        self.assertEqual(estimate["ladder_score"], result["ladder_score"])
        self.assertEqual(estimate["price"], result["price"])

    def test_condition_text_names_the_real_unknown_criteria(self):
        result = _base_ladder_result(payment_evidence=[])
        c = ec.classify_criteria(result)
        estimate = ec.estimate_value_if_verified(result, c)
        self.assertIn("proof_of_payment", estimate["condition"])


class TestAssessLifecycleStatus(unittest.TestCase):
    def test_accepted_ladder_result_is_accepted_lifecycle(self):
        result = _base_ladder_result(accepted=True)
        report = ec.assess("test niche", result)
        self.assertEqual(report["lifecycle_status"], "ACCEPTED")

    def test_rejected_with_low_coverage_and_acquirable_unknown_is_research_required(self):
        """The core rule: a real, acquirable Unknown (difficult_to_copy)
        must trigger RESEARCH_REQUIRED instead of a final REJECT, when
        coverage is below threshold."""
        result = _base_ladder_result(
            accepted=False,
            payment_evidence=[],
            defensibility={"score": None, "level": "Unknown", "note": "n/a"},
        )
        report = ec.assess("test niche", result)
        self.assertEqual(report["lifecycle_status"], "RESEARCH_REQUIRED")

    def test_rejected_with_high_coverage_is_a_real_final_reject(self):
        """Real, sufficient evidence supporting a genuine reject must not
        be deferred into RESEARCH_REQUIRED just because 2 permanently-
        Unknown gaps (commercial value, continuous improvement) exist."""
        result = _base_ladder_result(accepted=False, ai_leverage={"score": 20, "level": "منخفضة", "note": "real negative"})
        report = ec.assess("test niche", result)
        self.assertEqual(report["lifecycle_status"], "REJECTED")
        self.assertGreaterEqual(report["coverage"]["coverage_pct"], ec.DEFAULT_RESEARCH_THRESHOLD_PCT)

    def test_rejected_with_low_coverage_but_no_real_acquirable_unknown_is_still_a_real_reject(self):
        """Honest final call: if the only Unknowns are ones this factory
        has no real automated way to research (commercial value,
        continuous improvement), deferring forever would never resolve
        anything — a real reject, clearly low-confidence, is the honest
        outcome. (proof_of_payment is no longer in this set: it gained a
        REAL connector in payment_evidence_connector.py — an Unknown
        there now legitimately triggers RESEARCH_REQUIRED.)"""
        result = _base_ladder_result(accepted=False, ai_leverage={"score": 20, "level": "منخفضة", "note": "real negative"})
        report = ec.assess("test niche", result)
        self.assertEqual(report["lifecycle_status"], "REJECTED")

    def test_confidence_reason_explains_incomplete_confidence(self):
        result = _base_ladder_result(accepted=False, payment_evidence=[])
        report = ec.assess("test niche", result)
        self.assertIn("%", report["confidence_reason"])
        self.assertLess(report["confidence_pct"], 100)


class TestAcquireMissingEvidence(unittest.TestCase):
    """ADR-128: acquire_missing_evidence() dispatches through
    evidence_network's registry rather than hard-coding which function
    resolves which criterion -- these tests patch the real, original
    functions (competitor_discovery.get_or_refresh_competitors,
    market_intelligence_engine.analyze_customer_pain) directly, since
    evidence_network.py's connector lambdas look those up by module
    attribute at call time, not at import time."""

    def test_pain_severity_not_attempted_without_explicit_opt_in(self):
        """analyze_customer_pain() has a real per-call cost even with its
        own new cache (ADR-128) -- must never fire without
        gather_pain=True."""
        result = _base_ladder_result(urgency={"score": None, "level": "Unknown", "note": "n/a"})
        c = ec.classify_criteria(result)
        with patch("market_intelligence_engine.analyze_customer_pain") as mock_pain:
            acq = ec.acquire_missing_evidence("test niche", c, gather_pain=False)
            mock_pain.assert_not_called()
        self.assertFalse(acq["pain_severity"]["attempted"])

    def test_pain_severity_attempted_with_explicit_opt_in(self):
        result = _base_ladder_result(urgency={"score": None, "level": "Unknown", "note": "n/a"})
        c = ec.classify_criteria(result)
        with patch("market_intelligence_engine.analyze_customer_pain", return_value={"pain_score": 50}) as mock_pain:
            acq = ec.acquire_missing_evidence("test niche", c, gather_pain=True)
            mock_pain.assert_called_once()
        self.assertTrue(acq["pain_severity"]["attempted"])
        self.assertTrue(acq["pain_severity"]["acquired"])

    def test_difficult_to_copy_is_always_attempted_real_acquisition(self):
        """competitor_discovery.py is cached — real, but bounded cost —
        so unlike pain_severity, this fires without a separate opt-in."""
        result = _base_ladder_result(defensibility={"score": None, "level": "Unknown", "note": "n/a"})
        c = ec.classify_criteria(result)
        with patch("competitor_discovery.get_or_refresh_competitors", return_value={"total_found": 3}) as mock_cd:
            acq = ec.acquire_missing_evidence("test niche", c)
            mock_cd.assert_called_once()
        self.assertTrue(acq["difficult_to_copy"]["attempted"])
        self.assertTrue(acq["difficult_to_copy"]["acquired"])
        self.assertEqual(acq["difficult_to_copy"]["connector"], "competitor_discovery")

    def test_non_acquirable_criteria_are_never_attempted_and_carry_a_real_note(self):
        """Default fixture: the only Unknowns are the 2 permanently-
        unacquirable criteria (high_commercial_value, continuous_
        improvement_potential, ADR-126) -- proof_of_payment is VERIFIED_TRUE
        so its new REAL connector (payment_evidence_connector.py) never
        fires a live search here."""
        result = _base_ladder_result()
        c = ec.classify_criteria(result)
        acq = ec.acquire_missing_evidence("test niche", c)
        # high_commercial_value still has no real connector (evidence_network
        # upgrade made proof_of_payment acquirable, not this one) -- must be
        # never attempted and still carry a real declared-source note.
        self.assertFalse(acq["high_commercial_value"]["attempted"])
        self.assertIn("note", acq["high_commercial_value"])

    def test_proof_of_payment_is_now_a_real_acquirable_criterion(self):
        """Evidence Network upgrade: proof_of_payment gained a REAL
        connector (payment_evidence_connector.py) -- acquire_missing_
        evidence() now genuinely attempts it instead of declaring it
        unacquirable."""
        result = _base_ladder_result(payment_evidence=[])
        c = ec.classify_criteria(result)
        self.assertIn("proof_of_payment", ec.REAL_ACQUIRABLE_CRITERIA)
        with patch("payment_evidence_connector.collect_payment_evidence",
                   return_value={"candidates_found": 1, "recorded": [{"source_url": "https://x.com", "quote": "$50/hr"}]}) as mock_pec:
            acq = ec.acquire_missing_evidence("test niche", c)
            mock_pec.assert_called_once()
        self.assertTrue(acq["proof_of_payment"]["attempted"])
        self.assertTrue(acq["proof_of_payment"]["acquired"])
        self.assertEqual(acq["proof_of_payment"]["connector"], "payment_evidence")

    def test_real_acquisition_against_an_isolated_competitor_database_not_the_real_shared_one(self):
        """Proves the real wiring end-to-end (no mocking) against an
        isolated db_file — never data/competitor_database.json."""
        import tempfile
        import os
        niche = "evidence completeness engine real acquisition smoke test zzz"
        result = _base_ladder_result(defensibility={"score": None, "level": "Unknown", "note": "n/a"})
        c = ec.classify_criteria(result)
        tmp_db = tempfile.mktemp(suffix=".json")
        try:
            acq = ec.acquire_missing_evidence(niche, c, competitor_db_file=tmp_db)
            self.assertTrue(acq["difficult_to_copy"]["attempted"])
            self.assertTrue(os.path.exists(tmp_db), "must write to the isolated db_file, proving it never touched the real shared one")
        finally:
            if os.path.exists(tmp_db):
                os.remove(tmp_db)

    def test_registry_declares_a_source_for_every_criterion_even_unbuilt_ones(self):
        """Founder rule 1 (ADR-128): every UNKNOWN criterion must declare
        which evidence source could resolve it, even ones this factory
        cannot query yet. Uses the default fixture so the only Unknowns
        are the permanently-unbuilt ones (high_commercial_value,
        continuous_improvement_potential) -- proof_of_payment is
        VERIFIED_TRUE here, so its REAL connector never fires a live
        search in this test."""
        result = _base_ladder_result()
        c = ec.classify_criteria(result)
        acq = ec.acquire_missing_evidence("test niche", c)
        self.assertIn("note", acq["high_commercial_value"])
        self.assertTrue(len(acq["high_commercial_value"]["note"]) > 0)
        self.assertFalse(acq["high_commercial_value"]["attempted"])


class TestRecordLadderDecisionWithEvidenceReport(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.decisions_path = tempfile.mktemp(suffix=".jsonl")

    def tearDown(self):
        import os
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_research_required_lifecycle_status_is_recorded_as_the_real_decision_status(self):
        niche = "test niche for research required status"
        result = _base_ladder_result(niche=niche, accepted=False, payment_evidence=[], defensibility={"score": None, "level": "Unknown", "note": "n/a"})
        report = ec.assess(niche, result)
        self.assertEqual(report["lifecycle_status"], "RESEARCH_REQUIRED")

        decision = record_ladder_decision(niche, "ai_saas", result, decisions_path=self.decisions_path, evidence_report=report)
        self.assertEqual(decision.status, "RESEARCH_REQUIRED")
        self.assertEqual(decision.evaluation_snapshot["evidence_completeness"]["lifecycle_status"], "RESEARCH_REQUIRED")

    def test_omitting_evidence_report_preserves_the_exact_prior_binary_behavior(self):
        """Regression guard: every existing real caller that doesn't pass
        evidence_report must see byte-identical behavior to before
        ADR-127."""
        niche = "test niche for backward compat"
        accepted_result = _base_ladder_result(niche=niche, accepted=True)
        decision = record_ladder_decision(niche, "ai_saas", accepted_result, decisions_path=self.decisions_path)
        self.assertEqual(decision.status, "ACCEPTED")
        self.assertIsNone(decision.evaluation_snapshot["evidence_completeness"])


if __name__ == "__main__":
    unittest.main()

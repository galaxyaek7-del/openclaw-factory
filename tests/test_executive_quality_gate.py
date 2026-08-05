"""Tests for executive_quality_gate.py (Executive Directive, 2026-07-22).

Runs with stdlib unittest. No live network calls -- every real function
this gate wraps (competitor_discovery, safety_filter, inspectors,
product_families, revenue_pipeline.plan) is either called against
already-cached/deterministic data or patched.

    python -m unittest tests.test_executive_quality_gate -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import executive_quality_gate as eqg


class TestCustomerPainEvidence(unittest.TestCase):
    def test_no_customer_pain_dict_is_unknown(self):
        result = eqg.check_customer_pain_evidence(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_zero_real_evidence_fails(self):
        result = eqg.check_customer_pain_evidence({
            "pain_score": 20, "real_evidence": {"github_issues_found": 0, "hn_discussions_found": 0, "stack_overflow_found": 0},
        })
        self.assertEqual(result["status"], "FAIL")

    def test_real_evidence_passes(self):
        result = eqg.check_customer_pain_evidence({
            "pain_score": 70, "real_evidence": {"github_issues_found": 3, "hn_discussions_found": 2, "stack_overflow_found": 0},
        })
        self.assertEqual(result["status"], "PASS")


class TestWillingnessToPay(unittest.TestCase):
    def test_no_source_and_no_niche_is_always_unknown(self):
        """This factory has zero real per-opportunity WTP data -- must
        never silently pass."""
        result = eqg.check_willingness_to_pay()
        self.assertEqual(result["status"], "UNKNOWN")

    def test_explicit_real_evidence_is_accepted(self):
        result = eqg.check_willingness_to_pay({"source": "real discovery sprint replies", "count": 5})
        self.assertEqual(result["status"], "PASS")

    def test_niche_with_no_market_evidence_logged_is_still_unknown(self):
        result = eqg.check_willingness_to_pay(niche="a niche with zero logged evidence")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_market_learning_loop_real_positive_signal_passes(self):
        """The whole point of ADR-088: UNKNOWN disappears only because
        real evidence arrived, never assumed."""
        path = _temp_evidence_path()
        try:
            import market_evidence as me
            me.record_evidence("n", "demo_request", {}, evidence_path=path)
            with patch.object(me, "DEFAULT_EVIDENCE_PATH", Path(path)):
                result = eqg.check_willingness_to_pay(niche="n")
            self.assertEqual(result["status"], "PASS")
        finally:
            import os
            if os.path.exists(path):
                os.remove(path)

    def test_market_learning_loop_real_pricing_objection_fails(self):
        path = _temp_evidence_path()
        try:
            import market_evidence as me
            me.record_evidence("n", "pricing_objection", {}, evidence_path=path)
            with patch.object(me, "DEFAULT_EVIDENCE_PATH", Path(path)):
                result = eqg.check_willingness_to_pay(niche="n")
            self.assertEqual(result["status"], "FAIL")
        finally:
            import os
            if os.path.exists(path):
                os.remove(path)


def _temp_evidence_path():
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestCustomerRetentionPotential(unittest.TestCase):
    def test_always_unknown_with_no_niche_zero_real_sales_exist(self):
        result = eqg.check_customer_retention_potential()
        self.assertEqual(result["status"], "UNKNOWN")

    def test_niche_with_no_retention_evidence_is_still_unknown(self):
        result = eqg.check_customer_retention_potential(niche="untouched niche")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_real_churn_signal_fails(self):
        path = _temp_evidence_path()
        try:
            import market_evidence as me
            me.record_evidence("n", "retention_signal", {"outcome": "churned"}, evidence_path=path)
            with patch.object(me, "DEFAULT_EVIDENCE_PATH", Path(path)):
                result = eqg.check_customer_retention_potential(niche="n")
            self.assertEqual(result["status"], "FAIL")
        finally:
            import os
            if os.path.exists(path):
                os.remove(path)


class TestMarketSaturation(unittest.TestCase):
    def test_no_cached_data_is_unknown(self):
        result = eqg.check_market_saturation("a totally novel niche xyz", competitor_db={})
        self.assertEqual(result["status"], "UNKNOWN")

    def test_two_enterprise_leaders_fails(self):
        db = {"crowded niche": {"competitors": [
            {"classification": "Enterprise Leader"}, {"classification": "Enterprise Leader"},
        ]}}
        result = eqg.check_market_saturation("crowded niche", competitor_db=db)
        self.assertEqual(result["status"], "FAIL")

    def test_no_enterprise_leaders_passes(self):
        db = {"open niche": {"competitors": [{"classification": "Emerging Startup"}]}}
        result = eqg.check_market_saturation("open niche", competitor_db=db)
        self.assertEqual(result["status"], "PASS")


class TestTechnicalFeasibility(unittest.TestCase):
    def test_unknown_ladder_is_unknown(self):
        result = eqg.check_technical_feasibility("not_a_real_ladder")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_no_registered_adapter_fails(self):
        with patch("product_families.mapping.resolve_product_family", return_value="nonexistent_family"):
            with patch("product_families.registry.get", return_value=None):
                result = eqg.check_technical_feasibility("ai_saas")
        self.assertEqual(result["status"], "FAIL")

    def test_registered_adapter_passes(self):
        with patch("product_families.mapping.resolve_product_family", return_value="digital_toolkits"):
            with patch("product_families.registry.get", return_value=object()):
                result = eqg.check_technical_feasibility("automation_tools")
        self.assertEqual(result["status"], "PASS")


class TestLegalComplianceRisk(unittest.TestCase):
    def test_quarantined_niche_fails(self):
        with patch("inspectors._read_quarantined_niches", return_value={"bad niche"}):
            result = eqg.check_legal_compliance_risk("Bad Niche")
        self.assertEqual(result["status"], "FAIL")

    def test_safety_filter_blocked_fails(self):
        with patch("inspectors._read_quarantined_niches", return_value=set()), \
             patch("safety_filter.evaluate", return_value={"allowed": False, "risk_level": "blocked", "reasons": ["x:y"], "score": 0}):
            result = eqg.check_legal_compliance_risk("risky niche")
        self.assertEqual(result["status"], "FAIL")

    def test_clean_niche_passes_as_partial_check(self):
        with patch("inspectors._read_quarantined_niches", return_value=set()), \
             patch("safety_filter.evaluate", return_value={"allowed": True, "risk_level": "low", "reasons": [], "score": 100}):
            result = eqg.check_legal_compliance_risk("clean niche")
        self.assertEqual(result["status"], "PASS")
        self.assertIn("جزئي", result["reason"])  # never presented as full legal clearance


class TestScalabilityAndRevenue(unittest.TestCase):
    def test_missing_components_is_unknown(self):
        self.assertEqual(eqg.check_scalability(None)["status"], "UNKNOWN")
        self.assertEqual(eqg.check_revenue_model_sustainability(None)["status"], "UNKNOWN")

    def test_low_reusability_fails(self):
        result = eqg.check_scalability({"reusability": 30})
        self.assertEqual(result["status"], "FAIL")

    def test_high_reusability_passes(self):
        result = eqg.check_scalability({"reusability": 90})
        self.assertEqual(result["status"], "PASS")

    def test_low_recurring_revenue_fails(self):
        result = eqg.check_revenue_model_sustainability({"recurring_revenue_potential": 10})
        self.assertEqual(result["status"], "FAIL")


class TestBrandReputationRisk(unittest.TestCase):
    def test_no_content_is_unknown(self):
        result = eqg.check_brand_reputation_risk(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_real_bug_pattern_fails(self):
        """The exact real bug found live 2026-07-22: AI content claiming a
        hosted platform, sales team, and 24/7 support that don't exist."""
        chapters = [{"title": "Support", "content": "Our dedicated support team is available 24/7 support for your account."}]
        result = eqg.check_brand_reputation_risk(chapters)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("24/7" in h for h in result["evidence"]))

    def test_honest_blueprint_content_passes(self):
        chapters = [{"title": "Overview", "content": "This is a real implementation blueprint, not installed software."}]
        result = eqg.check_brand_reputation_risk(chapters)
        self.assertEqual(result["status"], "PASS")


class TestContentNeutralityRisk(unittest.TestCase):
    """Executive Safety Principles (Global Commercial Hardening, Phase 1,
    2026-07-29)."""

    def test_no_content_is_unknown(self):
        result = eqg.check_content_neutrality_risk(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_political_content_fails(self):
        chapters = [{"title": "Chapter 1", "content": "Please vote for our preferred candidate this November."}]
        result = eqg.check_content_neutrality_risk(chapters)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("vote for" in h for h in result["evidence"]))

    def test_hate_content_fails(self):
        chapters = [{"title": "Chapter 1", "content": "This section contains real hate speech examples."}]
        result = eqg.check_content_neutrality_risk(chapters)
        self.assertEqual(result["status"], "FAIL")

    def test_neutral_business_content_passes(self):
        chapters = [{"title": "Overview", "content": "A practical guide to budgeting for freelancers."}]
        result = eqg.check_content_neutrality_risk(chapters)
        self.assertEqual(result["status"], "PASS")

    def test_is_a_real_hard_reject_criterion(self):
        self.assertIn("content_neutrality_risk", eqg.REJECT_IF_FAIL)


class TestFakeUrgencyRisk(unittest.TestCase):
    """Customer Experience & Brand DNA (ADR-170, 2026-08-05)."""

    def test_no_content_is_unknown(self):
        result = eqg.check_fake_urgency_risk(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_deceptive_scarcity_fails(self):
        chapters = [{"title": "Pricing", "content": "Only 2 left in stock, almost sold out!"}]
        result = eqg.check_fake_urgency_risk(chapters)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("only 2 left" in h for h in result["evidence"]))

    def test_deceptive_time_pressure_fails(self):
        chapters = [{"title": "Offer", "content": "Hurry, offer ends in 10 minutes -- act now before it's gone."}]
        result = eqg.check_fake_urgency_risk(chapters)
        self.assertEqual(result["status"], "FAIL")

    def test_honest_content_passes(self):
        chapters = [{"title": "Overview", "content": "This guide covers automation setup for support teams."}]
        result = eqg.check_fake_urgency_risk(chapters)
        self.assertEqual(result["status"], "PASS")

    def test_is_a_real_hard_reject_criterion(self):
        self.assertIn("fake_urgency_risk", eqg.REJECT_IF_FAIL)


class TestConstitutionAlignment(unittest.TestCase):
    """Global Policy Engine (Global Trust & Resilience Layer, Round 3,
    2026-07-29)."""

    def test_no_spec_is_unknown(self):
        result = eqg.check_constitution_alignment(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_spec_with_neither_field_cites_nothing_but_never_fails(self):
        result = eqg.check_constitution_alignment({"niche": "test niche"})
        self.assertEqual(result["status"], "INFO")
        self.assertEqual(result["evidence"]["cited"], {})
        self.assertIn("16_butter_principle", result["evidence"]["missing"])

    def test_real_evaluation_snapshot_cites_butter_principle(self):
        result = eqg.check_constitution_alignment({"evaluation_snapshot": {"components": {}}})
        self.assertIn("16_butter_principle", result["evidence"]["cited"])

    def test_real_product_chapters_cites_dual_inspection(self):
        result = eqg.check_constitution_alignment({"product_chapters": [{"content": "x"}]})
        self.assertIn("17_dual_inspection", result["evidence"]["cited"])

    def test_never_added_to_hard_reject_criteria(self):
        self.assertNotIn("constitution_alignment", eqg.REJECT_IF_FAIL)


class TestPlatformTosAwareness(unittest.TestCase):
    """Global Policy Engine (Global Trust & Resilience Layer, Round 3,
    2026-07-29): honestly UNKNOWN always -- no platform ToS is parsed
    anywhere in this factory."""

    def test_no_platform_is_unknown(self):
        result = eqg.check_platform_tos_awareness(None)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_named_platform_is_still_honestly_unknown_never_a_fabricated_pass(self):
        result = eqg.check_platform_tos_awareness(["kdp", "shopify"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("kdp", result["reason"])
        self.assertIn("shopify", result["reason"])

    def test_never_added_to_hard_reject_criteria(self):
        self.assertNotIn("platform_tos_awareness", eqg.REJECT_IF_FAIL)


class TestEvidenceFreshness(unittest.TestCase):
    def test_no_timestamps_is_unknown(self):
        result = eqg.check_evidence_freshness()
        self.assertEqual(result["status"], "UNKNOWN")

    def test_stale_evidence_fails(self):
        result = eqg.check_evidence_freshness(competitor_cache_age_days=200)
        self.assertEqual(result["status"], "FAIL")

    def test_fresh_evidence_passes(self):
        result = eqg.check_evidence_freshness(competitor_cache_age_days=5)
        self.assertEqual(result["status"], "PASS")


class TestHumanReviewAndFinalDecision(unittest.TestCase):
    def test_unknown_wtp_forces_human_review_not_silent_pass(self):
        spec = {"niche": "test niche", "ladder": "ai_saas"}
        with patch("competitor_discovery.load_database", return_value={}), \
             patch("inspectors._read_quarantined_niches", return_value=set()), \
             patch("safety_filter.evaluate", return_value={"allowed": True, "risk_level": "low", "reasons": [], "score": 100}), \
             patch("product_families.mapping.resolve_product_family", return_value="digital_toolkits"), \
             patch("product_families.registry.get", return_value=object()), \
             patch("revenue_pipeline.plan.estimate_production_cost", return_value={"maturity": "DISCOVERY"}):
            result = eqg.run_executive_quality_gate(spec)
        self.assertTrue(result["human_review_required"])
        self.assertEqual(result["final_decision"], "NEEDS_HUMAN_REVIEW")
        self.assertNotEqual(result["final_decision"], "APPROVED")

    def test_hard_failure_rejects_regardless_of_other_passes(self):
        spec = {
            "niche": "quarantined niche", "ladder": "ai_saas",
            "explicit_wtp_evidence": {"real": True}, "explicit_cac_evidence": {"real": True},
        }
        with patch("competitor_discovery.load_database", return_value={}), \
             patch("inspectors._read_quarantined_niches", return_value={"quarantined niche"}), \
             patch("product_families.mapping.resolve_product_family", return_value="digital_toolkits"), \
             patch("product_families.registry.get", return_value=object()), \
             patch("revenue_pipeline.plan.estimate_production_cost", return_value={"maturity": "DISCOVERY"}):
            result = eqg.run_executive_quality_gate(spec)
        self.assertEqual(result["final_decision"], "REJECTED")
        self.assertTrue(any("QUARANTINE" in r for r in result["decision_reasons"]))

    def test_written_explanation_lists_every_criterion(self):
        spec = {"niche": "x", "ladder": "ai_saas"}
        with patch("competitor_discovery.load_database", return_value={}), \
             patch("inspectors._read_quarantined_niches", return_value=set()), \
             patch("safety_filter.evaluate", return_value={"allowed": True, "risk_level": "low", "reasons": [], "score": 100}), \
             patch("product_families.mapping.resolve_product_family", return_value=None), \
             patch("revenue_pipeline.plan.estimate_production_cost", return_value={"maturity": "DISCOVERY"}):
            result = eqg.run_executive_quality_gate(spec)
        for name in result["criteria"]:
            self.assertIn(name, result["written_explanation"])

    def test_never_raises_on_a_completely_empty_spec(self):
        with patch("competitor_discovery.load_database", return_value={}), \
             patch("inspectors._read_quarantined_niches", return_value=set()), \
             patch("safety_filter.evaluate", return_value={"allowed": True, "risk_level": "low", "reasons": [], "score": 100}), \
             patch("revenue_pipeline.plan.estimate_production_cost", return_value={"maturity": "DISCOVERY"}):
            result = eqg.run_executive_quality_gate({})
        self.assertIn(result["final_decision"], ("REJECTED", "NEEDS_HUMAN_REVIEW", "APPROVED"))


if __name__ == "__main__":
    unittest.main()

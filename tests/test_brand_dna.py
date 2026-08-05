"""Tests for brand_dna.py (Customer Experience & Brand DNA, ADR-170,
2026-08-05): the real, callable Brand Consistency Engine + the honest
Customer Journey / Trust Framework status citations.

    python -m unittest tests.test_brand_dna -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import brand_dna


class TestCompanyPersonality(unittest.TestCase):
    def test_all_9_named_traits_present(self):
        expected = {
            "professional", "honest", "respectful", "calm", "helpful",
            "transparent", "intelligent", "premium",
            "human_like_without_pretending_to_be_human",
        }
        self.assertEqual(set(brand_dna.COMPANY_PERSONALITY.keys()), expected)

    def test_every_trait_has_a_real_rule_and_evidence(self):
        for name, trait in brand_dna.COMPANY_PERSONALITY.items():
            self.assertTrue(trait.get("rule"), f"{name} missing a real rule")
            self.assertTrue(trait.get("evidence"), f"{name} missing real evidence")


class TestCommunicationStandards(unittest.TestCase):
    def test_all_8_named_standards_present(self):
        expected = {
            "be_truthful", "never_exaggerate", "never_manipulate", "explain_clearly",
            "respect_customer_time", "avoid_robotic_language", "avoid_unnecessary_text",
            "solve_problems_first",
        }
        self.assertEqual(set(brand_dna.COMMUNICATION_STANDARDS.keys()), expected)


class TestCustomerJourneyStandards(unittest.TestCase):
    def test_all_10_named_stages_present(self):
        expected = {
            "first_contact", "product_discovery", "recommendation", "purchase",
            "delivery", "after_sales_support", "complaint_handling",
            "refund_requests", "follow_up", "long_term_relationship",
        }
        self.assertEqual(set(brand_dna.CUSTOMER_JOURNEY_STANDARDS.keys()), expected)

    def test_complaint_handling_and_refunds_honestly_future_instrumentation(self):
        # Real, confirmed gap -- must never be silently marked REAL.
        self.assertEqual(brand_dna.CUSTOMER_JOURNEY_STANDARDS["complaint_handling"]["status"], brand_dna.FUTURE_INSTRUMENTATION)
        self.assertEqual(brand_dna.CUSTOMER_JOURNEY_STANDARDS["refund_requests"]["status"], brand_dna.FUTURE_INSTRUMENTATION)

    def test_every_stage_has_a_real_citation(self):
        for name, stage in brand_dna.CUSTOMER_JOURNEY_STANDARDS.items():
            self.assertIn(stage["status"], (brand_dna.REAL, brand_dna.FUTURE_INSTRUMENTATION))
            self.assertTrue(stage.get("citation"), f"{name} missing a real citation")


class TestTrustPrinciples(unittest.TestCase):
    def test_all_5_named_principles_present(self):
        expected = {
            "promises_match_reality", "no_fake_reviews", "no_fake_urgency",
            "no_misleading_pricing", "no_deceptive_wording",
        }
        self.assertEqual(set(brand_dna.TRUST_PRINCIPLES.keys()), expected)

    def test_no_fake_urgency_cites_the_new_check(self):
        citation = brand_dna.TRUST_PRINCIPLES["no_fake_urgency"]["citation"]
        self.assertIn("check_fake_urgency_risk", citation)


class TestValidateCustomerFacingText(unittest.TestCase):
    def test_deceptive_urgency_fails(self):
        result = brand_dna.validate_customer_facing_text("Only 2 left! Offer ends in 10 minutes, act now!")
        self.assertFalse(result["passed"])
        self.assertIn("fake_urgency", result["failed_checks"])

    def test_honest_text_passes(self):
        result = brand_dna.validate_customer_facing_text("This guide covers automation setup steps for support teams.")
        self.assertTrue(result["passed"])
        self.assertEqual(result["failed_checks"], [])

    def test_fabricated_infrastructure_claim_fails(self):
        result = brand_dna.validate_customer_facing_text("Our dedicated support team is available 24/7 support for your account.")
        self.assertFalse(result["passed"])
        self.assertIn("brand_reputation", result["failed_checks"])


class TestCustomerMemoryArchitecture(unittest.TestCase):
    def test_honestly_not_implemented(self):
        self.assertEqual(brand_dna.CUSTOMER_MEMORY_ARCHITECTURE["status"], brand_dna.FUTURE_INSTRUMENTATION)

    def test_has_real_design_principles_not_fabricated_metrics(self):
        principles = brand_dna.CUSTOMER_MEMORY_ARCHITECTURE["design_principles"]
        self.assertGreater(len(principles), 0)
        self.assertNotIn("current_active_users", brand_dna.CUSTOMER_MEMORY_ARCHITECTURE)


class TestBrandDnaReport(unittest.TestCase):
    def test_aggregates_without_fabricating(self):
        report = brand_dna.brand_dna_report()
        self.assertIn("8/10", report["customer_journey_coverage"])
        self.assertIn("5/5", report["trust_coverage"])
        self.assertIn("generated_at", report)


if __name__ == "__main__":
    unittest.main()

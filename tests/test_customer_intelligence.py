import unittest
from unittest.mock import patch

import customer_intelligence as ci


class TestCustomerIdentity(unittest.TestCase):
    def test_no_identifier_is_unknown_never_guessed(self):
        result = ci.customer_identity_view()
        self.assertEqual(result["identity_status"], "UNKNOWN")

    def test_no_match_is_honest_not_fabricated(self):
        result = ci.customer_identity_view(email="definitely-not-a-real-customer@example.com")
        self.assertEqual(result["identity_status"], "NO_MATCH")

    def test_never_merges_on_weak_evidence(self):
        result = ci.customer_identity_view(email="x@example.com")
        self.assertIn("never fuzzy", result["resolution_method"])


class TestCustomerJourney(unittest.TestCase):
    def test_unknown_stage_never_inferred(self):
        result = ci.customer_journey_view("nonexistent_request_id")
        self.assertEqual(result["journey_stage"], "UNKNOWN")

    def test_stage_map_never_produces_an_unnamed_stage(self):
        for real_stage, journey_stage in ci._STAGE_ORDER_TO_JOURNEY.items():
            self.assertIn(journey_stage, ci.CUSTOMER_JOURNEY_STAGES)


class TestPurchaseReasons(unittest.TestCase):
    def test_zero_purchases_never_fabricates_a_reason(self):
        result = ci.purchase_reason_report()
        self.assertEqual(result["total_real_purchases"], 0)
        self.assertTrue(all(v == 0 for v in result["by_reason"].values()))

    def test_non_purchase_never_treats_silence_as_rejection(self):
        result = ci.non_purchase_reason_report()
        self.assertTrue(all(v == "NO_REAL_SIGNAL" for v in result["by_reason"].values()))


class TestSentimentSafety(unittest.TestCase):
    def test_honestly_not_built(self):
        result = ci.sentiment_safety_status()
        self.assertEqual(result["status"], "NOT_BUILT")


class TestCustomerTrust(unittest.TestCase):
    def test_never_produces_a_single_fabricated_composite_score(self):
        result = ci.customer_trust_score()
        self.assertNotIn("overall_score", result)
        self.assertNotIn("composite_score", result)
        self.assertIn("components", result)


class TestRefundIntelligence(unittest.TestCase):
    def test_zero_refunds_never_classifies_abuse(self):
        result = ci.refund_intelligence_report()
        self.assertEqual(result["total_real_refunds_usd"], 0)
        self.assertEqual(result["refund_events"], [])


class TestChurnIntelligence(unittest.TestCase):
    def test_honestly_not_applicable_with_zero_subscriptions(self):
        result = ci.churn_intelligence_report()
        self.assertEqual(result["status"], "NOT_APPLICABLE")


class TestRetentionEngine(unittest.TestCase):
    def test_no_dark_patterns_in_action_taxonomy(self):
        forbidden = ["HIDE_CANCELLATION", "OBSTRUCT_REFUND", "FAKE_URGENCY", "FAKE_SCARCITY"]
        for f in forbidden:
            self.assertNotIn(f, ci.RETENTION_ACTIONS)

    def test_do_nothing_is_a_valid_action(self):
        self.assertIn("DO_NOTHING", ci.RETENTION_ACTIONS)


class TestUpsellRecommendation(unittest.TestCase):
    def test_missing_evidence_never_recommends(self):
        result = ci.upsell_recommendation()
        self.assertEqual(result["decision"], "DO_NOT_RECOMMEND")

    def test_missing_relevance_evidence_never_recommends(self):
        result = ci.upsell_recommendation(customer_need="faster reports", product_relevance_evidence=None)
        self.assertEqual(result["decision"], "DO_NOT_RECOMMEND")

    def test_both_present_recommends(self):
        result = ci.upsell_recommendation(customer_need="faster reports", product_relevance_evidence="real evidence")
        self.assertEqual(result["decision"], "RECOMMEND")


class TestFeedbackToRoadmap(unittest.TestCase):
    def test_zero_customers_affected_is_insufficient_evidence(self):
        result = ci.classify_feedback_for_roadmap(customers_affected=0)
        self.assertEqual(result["classification"], "INSUFFICIENT_EVIDENCE")

    def test_high_customers_and_revenue_is_high_value(self):
        result = ci.classify_feedback_for_roadmap(customers_affected=15, revenue_impact=1000)
        self.assertEqual(result["classification"], "HIGH_VALUE")

    def test_classification_always_in_named_set(self):
        for count in (0, 1, 5, 20):
            result = ci.classify_feedback_for_roadmap(customers_affected=count)
            self.assertIn(result["classification"], ci.ROADMAP_CLASSIFICATIONS)


class TestSupportAutomation(unittest.TestCase):
    def test_honestly_not_built(self):
        result = ci.support_automation_status()
        self.assertEqual(result["status"], "NOT_BUILT")

    def test_six_escalation_categories_present(self):
        result = ci.support_automation_status()
        self.assertEqual(len(result["escalation_categories"]), 6)


class TestCustomerSegmentation(unittest.TestCase):
    def test_zero_customers_all_segments_empty(self):
        result = ci.customer_segmentation_report()
        for seg in ci.CUSTOMER_SEGMENTS:
            self.assertEqual(result["segments"][seg]["count"], 0)


class TestCustomerCohorts(unittest.TestCase):
    def test_zero_customers_empty_cohorts(self):
        result = ci.customer_cohort_report()
        self.assertEqual(result["cohorts"], [])


class TestExecutiveCustomerQuestions(unittest.TestCase):
    def test_ten_questions_answered(self):
        result = ci.executive_customer_questions()
        self.assertEqual(len(result["answers"]), 10)

    def test_every_answer_tagged_fact_inference_estimate_or_unknown(self):
        result = ci.executive_customer_questions()
        for a in result["answers"]:
            self.assertIn(a["tag"], ("FACT", "INFERENCE", "ESTIMATE", "UNKNOWN"))


class TestGoldenHunterIntegration(unittest.TestCase):
    def test_reuses_market_evidence_never_a_second_engine(self):
        result = ci.golden_hunter_customer_signal("a niche with no real evidence")
        self.assertIn("willingness_to_pay", result)
        self.assertEqual(result["source"], "market_evidence.py (already real, already feeds profit_oracle.py's ladder_opportunity_score())")


class TestRevenueIntegration(unittest.TestCase):
    def test_never_computes_a_second_competing_financial_figure(self):
        result = ci.customer_intelligence_to_revenue()
        self.assertIn("commissions", result)
        self.assertIn("b2b_revenue", result)


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = ci.build_customer_intelligence_dashboard()
        for key in ("data_minimization", "purchase_reasons", "non_purchase_reasons", "problem_mining",
                    "feedback", "sentiment_safety", "trust_score", "refunds", "churn", "retention",
                    "customer_value", "segmentation", "support", "support_automation", "cohorts",
                    "privacy", "incident_protection", "revenue_link", "executive_questions"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

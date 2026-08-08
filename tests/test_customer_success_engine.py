import unittest
from unittest.mock import patch

import customer_success_engine as cse

_TEST_NICHE = "AI-Powered Compliance Automation System for Accounting Firms"


class TestCustomerHealthScore(unittest.TestCase):
    def test_state_always_named(self):
        result = cse.customer_health_score("nonexistent_request")
        self.assertIn(result["state"], cse.CUSTOMER_HEALTH_STATES)

    def test_never_hides_uncertainty_as_healthy(self):
        result = cse.customer_health_score("nonexistent_request")
        self.assertNotEqual(result["state"], "HEALTHY")


class TestFeatureRequestDecision(unittest.TestCase):
    def test_decision_always_named(self):
        result = cse.feature_request_decision(customers_affected=5)
        self.assertIn(result["decision"], cse.FEATURE_REQUEST_DECISIONS)

    def test_zero_customers_affected_is_reject(self):
        result = cse.feature_request_decision(customers_affected=0)
        self.assertEqual(result["decision"], "REJECT")

    def test_high_affected_and_revenue_is_build(self):
        result = cse.feature_request_decision(customers_affected=15, revenue_impact=1000)
        self.assertEqual(result["decision"], "BUILD")


class TestRecurringValueTest(unittest.TestCase):
    def test_all_false_refuses_by_default(self):
        result = cse.recurring_value_test()
        self.assertEqual(result["decision"], "DO_NOT_CREATE_A_SUBSCRIPTION")

    def test_one_true_answer_justifies_subscription(self):
        result = cse.recurring_value_test(continuing_value=True)
        self.assertEqual(result["decision"], "SUBSCRIPTION_JUSTIFIED")


class TestCustomerProfitability(unittest.TestCase):
    def test_high_revenue_not_automatically_high_profit(self):
        result = cse.customer_profitability(revenue=1000, fees=200, commission=200, refunds=300, support_cost=200)
        self.assertEqual(result["customer_contribution"], 100)

    def test_negative_contribution_possible(self):
        result = cse.customer_profitability(revenue=100, fees=50, commission=50, refunds=50)
        self.assertLess(result["customer_contribution"], 0)

    def test_acquisition_cost_reduces_contribution_when_known(self):
        result = cse.customer_profitability(revenue=1000, acquisition_cost=200)
        self.assertEqual(result["customer_contribution"], 800)


class TestCustomerROI(unittest.TestCase):
    def test_missing_inputs_are_unknown_never_zero(self):
        result = cse.customer_roi()
        self.assertEqual(result["customer_roi"], "UNKNOWN -- requires real investment + real savings, neither exists yet for any real customer")
        self.assertEqual(result["customer_investment"]["tier"], "UNKNOWN")


class TestRootCauseAnalysis(unittest.TestCase):
    def test_reuses_real_customer_pipeline_signal(self):
        result = cse.root_cause_analysis()
        self.assertIn("real_problem_trend", result)


class TestCustomerSuccessAutonomy(unittest.TestCase):
    def test_reuses_phase19_levels_verbatim(self):
        result = cse.customer_success_autonomy()
        self.assertIn("autonomous_operations.py", result["source"])

    def test_action_category_check_refuses_without_approval(self):
        result = cse.customer_success_autonomy(action_category="enterprise_contract_commitment")
        self.assertEqual(result["authorization_check"]["decision"], "REFUSE")

    def test_six_named_levels(self):
        self.assertEqual(len(cse.CS_AUTONOMY_LEVELS), 6)


class TestCSAutomationBoundaries(unittest.TestCase):
    def test_seven_requires_human_categories(self):
        result = cse.cs_automation_boundaries()
        self.assertEqual(len(result["requires_human"]), 7)

    def test_nine_safe_to_automate_categories(self):
        result = cse.cs_automation_boundaries()
        self.assertEqual(len(result["safe_to_automate"]), 9)


class TestChurnPrediction(unittest.TestCase):
    def test_never_claims_certainty(self):
        result = cse.churn_prediction()
        self.assertEqual(result["real_status"]["real_status"]["status"], "NOT_APPLICABLE")


class TestSimulations(unittest.TestCase):
    def test_simulation_2_flags_at_risk_on_steep_decline(self):
        result = cse.simulation_2_high_value_declining_usage(usage_trend_pct=-50)
        self.assertEqual(result["churn_risk"], "AT_RISK")

    def test_simulation_3_detects_real_spike(self):
        result = cse.simulation_3_refund_spike_after_version(refunds_before=2, refunds_after=20)
        self.assertTrue(result["spike_detected"])

    def test_simulation_3_no_spike_when_proportional(self):
        result = cse.simulation_3_refund_spike_after_version(refunds_before=10, refunds_after=15)
        self.assertFalse(result["spike_detected"])

    def test_simulation_4_requires_both_real_signals(self):
        result = cse.simulation_4_strong_expansion_candidate(outcome_achieved=True, usage_high=False)
        self.assertFalse(result["expansion_recommended"])

    def test_simulation_7_always_escalates_to_human(self):
        result = cse.simulation_7_enterprise_service_failure()
        self.assertEqual(result["escalation"], "HUMAN_REQUIRED")

    def test_run_all_returns_ten_simulations(self):
        result = cse.run_all_phase29_simulations()
        for i in range(1, 11):
            self.assertIn(f"simulation_{i}", result)

    def test_none_of_the_simulations_write_to_a_ledger(self):
        from channels import ledger as sales_ledger
        with patch.object(sales_ledger, "append_event") as mock_append:
            cse.run_all_phase29_simulations()
            mock_append.assert_not_called()


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = cse.build_customer_success_dashboard()
        for key in ("customer_outcome", "onboarding", "churn", "retention", "support", "root_cause",
                    "refunds", "feedback", "recurring_revenue", "renewal", "expansion", "ltv",
                    "segment_profitability", "queue", "automation_boundaries", "community",
                    "enterprise_success", "forecast", "experiments", "trust", "autonomy"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

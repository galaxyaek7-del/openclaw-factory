import unittest
from unittest.mock import patch

import commercial_autonomy_engine as cae

_TEST_NICHE = "AI-Powered Compliance Automation System for Accounting Firms"
_TEST_PLATFORM = "amazon"


class TestCommercialOpportunityScore(unittest.TestCase):
    def test_never_a_single_unexplained_score(self):
        result = cae.commercial_opportunity_score(_TEST_NICHE)
        self.assertNotIn("score", result)
        self.assertIn("components", result)
        self.assertGreaterEqual(len(result["components"]), 8)


class TestProductAllocation(unittest.TestCase):
    def test_status_always_named(self):
        result = cae.product_allocation(_TEST_NICHE)
        self.assertIn(result["status"], cae.ALLOCATION_STATUSES + ["UNKNOWN"])

    def test_unrecognized_product_is_unknown(self):
        result = cae.product_allocation("a product that has never existed")
        self.assertEqual(result["status"], "UNKNOWN")


class TestPlatformAllocation(unittest.TestCase):
    def test_tier_always_named(self):
        result = cae.platform_allocation(_TEST_PLATFORM)
        self.assertIn(result["tier"], cae.PLATFORM_ALLOCATION_TIERS)


class TestPartnerAllocation(unittest.TestCase):
    def test_action_always_named(self):
        result = cae.partner_allocation(_TEST_PLATFORM)
        self.assertIn(result["action"], cae.PARTNER_ALLOCATION_ACTIONS)


class TestGoldenHunterROI(unittest.TestCase):
    def test_status_always_named(self):
        result = cae.golden_hunter_roi_preacceptance(_TEST_NICHE)
        self.assertIn(result["roi_status"], cae.ROI_STATUSES)

    def test_zero_gates_passed_never_accepts(self):
        with patch("product_innovation_engine.validation_gate_status") as mock_gates:
            mock_gates.return_value = {"gates": {g: {"passed": False} for g in range(6)}, "overall_accepted": False}
            result = cae.golden_hunter_roi_preacceptance(_TEST_NICHE)
            self.assertNotEqual(result["roi_status"], "ACCEPT")


class TestScenarioEngine(unittest.TestCase):
    def test_all_four_cases_present(self):
        result = cae.scenario_engine()
        for key in ("base_case_30d_net_usd", "upside_case_30d_net_usd",
                    "downside_case_30d_net_usd", "stress_case_30d_net_usd"):
            self.assertIn(key, result)

    def test_labeled_hypothetical_never_a_prediction(self):
        result = cae.scenario_engine()
        self.assertIn("HYPOTHETICAL", result["label"])

    def test_stress_case_never_better_than_base_case_given_worse_assumptions(self):
        result = cae.scenario_engine()
        self.assertLessEqual(result["stress_case_30d_net_usd"], result["base_case_30d_net_usd"] + 0.01)


class TestSafeAutonomyLevels(unittest.TestCase):
    def test_six_named_levels(self):
        self.assertEqual(len(cae.SAFE_AUTONOMY_LEVELS), 6)

    def test_level_5_is_human_approval(self):
        self.assertEqual(cae.SAFE_AUTONOMY_LEVELS[5], "HUMAN_APPROVAL_REQUIRED")


class TestCommercialQueue(unittest.TestCase):
    def test_every_item_has_a_named_queue_state(self):
        result = cae.commercial_queue()
        for item in result["queue"]:
            self.assertIn(item["queue_state"], cae.QUEUE_STATES)

    def test_level_6_items_are_blocked(self):
        result = cae.commercial_queue()
        for item in result["queue"]:
            if item.get("authorization", {}).get("required_level", 0) >= 6:
                self.assertEqual(item["queue_state"], "BLOCKED")


class TestCommercialHealthScore(unittest.TestCase):
    def test_never_a_single_fabricated_composite(self):
        result = cae.commercial_health_score()
        self.assertNotIn("global_commercial_health_score", result)
        self.assertNotIn("overall_score", result)
        self.assertEqual(len(result["components"]), 11)


class TestCommercialExecutionAndRollback(unittest.TestCase):
    def test_zero_real_automated_executions(self):
        result = cae.commercial_execution_status()
        self.assertIn("0 fully automated", result["note"])

    def test_zero_real_rollbacks(self):
        result = cae.commercial_rollback_status()
        self.assertEqual(result["real_rollbacks_performed"], 0)


class TestSimulations(unittest.TestCase):
    def test_simulation_1_recommends_reduce_for_low_margin(self):
        result = cae.simulation_1_high_revenue_low_contribution(gross=5000, net_margin_pct=0.03)
        self.assertEqual(result["recommendation"], "REDUCE")

    def test_simulation_2_prefers_recurring_product(self):
        result = cae.simulation_2_recurring_vs_onetime(product_a_gross=10000, product_a_margin=0.05,
                                                         product_b_gross=1000, product_b_margin=0.10, product_b_recurring=True)
        self.assertEqual(result["recommendation"], "Product B")

    def test_simulation_3_fee_increase_reduces_net(self):
        result = cae.simulation_3_platform_fee_increase()
        self.assertLess(result["new_net"], result["old_net"])

    def test_simulation_4_refund_doubling_reduces_net(self):
        result = cae.simulation_4_refund_rate_doubles()
        self.assertLess(result["new_net"], result["old_net"])

    def test_simulation_5_triggers_at_65_percent(self):
        result = cae.simulation_5_concentration_65_percent()
        self.assertTrue(result["triggered"])

    def test_run_all_returns_ten_simulations(self):
        result = cae.run_all_phase27_simulations()
        for i in range(1, 11):
            self.assertIn(f"simulation_{i}", result)

    def test_none_of_the_simulations_write_to_a_ledger(self):
        from channels import ledger as sales_ledger
        with patch.object(sales_ledger, "append_event") as mock_append:
            cae.run_all_phase27_simulations()
            mock_append.assert_not_called()


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = cae.build_commercial_autonomy_dashboard()
        for key in ("commercial_forecast", "scenario_engine", "risk_engine", "revenue_leakage_tasks",
                    "margin_protection", "anomaly_response", "autonomous_recommendations",
                    "resource_allocation", "commercial_queue", "prediction_vs_reality",
                    "experiment_learning", "execution_status", "rollback_status", "health_score"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

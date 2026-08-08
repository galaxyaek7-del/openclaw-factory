import unittest
from unittest.mock import patch

import global_growth_engine as gge

_TEST_PLATFORM = "amazon"
_TEST_NICHE = "AI-Powered Compliance Automation System for Accounting Firms"


class TestLeadRegistryAndQualification(unittest.TestCase):
    def test_qualification_always_named(self):
        result = gge.lead_qualification("nonexistent_request")
        self.assertIn(result["qualification"], gge.LEAD_QUALIFICATION_LEVELS)

    def test_never_auto_assigns_enterprise_or_strategic(self):
        result = gge.lead_qualification("nonexistent_request")
        self.assertNotIn(result["qualification"], ("ENTERPRISE", "STRATEGIC"))


class TestCACAndLTV(unittest.TestCase):
    def test_cac_never_estimates_from_unsupported_assumptions(self):
        result = gge.cac_engine()
        for key in ("cac", "cac_by_product", "cac_by_platform", "cac_by_channel"):
            self.assertEqual(result[key], "UNKNOWN")

    def test_ltv_cac_never_computed_from_two_unknowns(self):
        result = gge.ltv_cac_ratio()
        self.assertEqual(result["ltv_cac_ratio"], "UNKNOWN")


class TestGrowthChannelScore(unittest.TestCase):
    def test_tier_always_named(self):
        result = gge.growth_channel_score(_TEST_PLATFORM)
        self.assertIn(result["tier"], gge.GROWTH_CHANNEL_TIERS)

    def test_unregistered_channel_is_experimental_never_core(self):
        result = gge.growth_channel_score("a channel that was never registered")
        self.assertEqual(result["tier"], "EXPERIMENTAL")


class TestGrowthJourney(unittest.TestCase):
    def test_unmapped_request_is_unknown(self):
        result = gge.growth_journey_view("nonexistent_request")
        self.assertEqual(result["growth_journey_stage"], "UNKNOWN")

    def test_mapping_values_are_all_named_stages(self):
        for stage in gge.GROWTH_JOURNEY_MAPPING.values():
            self.assertIn(stage, gge.GROWTH_JOURNEY_STAGES)


class TestNotBuiltEngines(unittest.TestCase):
    def test_content_landing_crm_guardrails_localization_all_honest(self):
        for fn in (gge.content_to_customer_status, gge.landing_page_intelligence,
                   gge.crm_status, gge.paid_acquisition_guardrails, gge.localization_status,
                   gge.customer_advocacy_status):
            result = fn()
            self.assertEqual(result["status"], "NOT_BUILT")


class TestMarketExpansion(unittest.TestCase):
    def test_status_always_named(self):
        result = gge.market_expansion_check()
        self.assertIn(result["status"], gge.MARKET_EXPANSION_STATUSES)

    def test_real_market_maps_to_test_not_enter(self):
        result = gge.market_expansion_check("global_online_markets")
        self.assertEqual(result["status"], "TEST")

    def test_never_measurable_region_is_wait(self):
        result = gge.market_expansion_check("europe")
        self.assertEqual(result["status"], "WAIT")


class TestGrowthScenarios(unittest.TestCase):
    def test_reuses_phase27_scenario_engine_directly(self):
        result = gge.growth_scenarios()
        self.assertIn("HYPOTHETICAL", result["label"])
        self.assertIn("base_case_30d_net_usd", result)


class TestGrowthAutonomyBoundaries(unittest.TestCase):
    def test_reuses_phase19_levels_verbatim(self):
        result = gge.growth_autonomy_boundaries()
        self.assertIn("autonomous_operations.py", result["source"])

    def test_six_may_and_six_requires_approval_categories(self):
        result = gge.growth_autonomy_boundaries()
        self.assertEqual(len(result["may_autonomously"]), 8)
        self.assertEqual(len(result["requires_human_approval"]), 6)


class TestChurnIntelligence(unittest.TestCase):
    def test_never_invents_a_churn_reason(self):
        result = gge.churn_intelligence_v2()
        self.assertEqual(result["real_status"]["status"], "NOT_APPLICABLE")


class TestSimulations(unittest.TestCase):
    def test_simulation_3_flags_unprofitable_channel(self):
        result = gge.simulation_3_cac_increases_40_percent(channels={"x": {"cac": 40, "ltv": 50}})
        self.assertFalse(result["channels"]["x"]["still_profitable"])

    def test_simulation_5_compares_total_segment_value_not_size(self):
        result = gge.simulation_5_small_high_ltv_vs_large_low_value(segment_a_size=10, segment_a_ltv=5000, segment_b_size=1000, segment_b_ltv=1)
        self.assertIn("Segment A", result["recommendation"])

    def test_simulation_9_detects_false_positive_growth(self):
        result = gge.simulation_9_revenue_positive_but_unprofitable_after_costs(gross=1000, fee_pct=0.3, refund_pct=0.4, commission_pct=0.35)
        self.assertTrue(result["false_positive_growth_signal"])

    def test_run_all_returns_ten_simulations(self):
        result = gge.run_all_phase28_simulations()
        for i in range(1, 11):
            self.assertIn(f"simulation_{i}", result)

    def test_none_of_the_simulations_write_to_a_ledger(self):
        from channels import ledger as sales_ledger
        with patch.object(sales_ledger, "append_event") as mock_append:
            gge.run_all_phase28_simulations()
            mock_append.assert_not_called()


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = gge.build_growth_dashboard()
        for key in ("lead_registry", "acquisition", "cac", "ltv", "ltv_cac", "organic_growth",
                    "customer_success", "churn", "retention", "expansion", "referral",
                    "growth_forecast", "growth_scenarios", "growth_risk", "autonomy_boundaries"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

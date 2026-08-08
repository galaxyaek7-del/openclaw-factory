import unittest
from unittest.mock import patch

import enterprise_sales_engine as ese

_TEST_NICHE = "AI-Powered Compliance Automation System for Accounting Firms"


class TestHighValueProblemScore(unittest.TestCase):
    def test_classification_always_named(self):
        result = ese.high_value_problem_score(_TEST_NICHE)
        self.assertIn(result["classification"], ese.HIGH_VALUE_PROBLEM_CLASSIFICATIONS)

    def test_never_fabricates_premium_without_all_gates(self):
        result = ese.high_value_problem_score(_TEST_NICHE)
        if result["classification"] == "PREMIUM_OPPORTUNITY":
            self.assertEqual(result["passed_gates"], 6)

    def test_components_are_decomposable_not_a_single_number(self):
        result = ese.high_value_problem_score(_TEST_NICHE)
        self.assertIsInstance(result["components"], dict)
        self.assertGreater(len(result["components"]), 1)


class TestEnterpriseSalesPipeline(unittest.TestCase):
    def test_stages_match_named_13(self):
        self.assertEqual(len(ese.ENTERPRISE_PIPELINE_STAGES), 13)

    def test_pipeline_view_maps_real_accounts(self):
        result = ese.enterprise_sales_pipeline_view()
        for account in result["accounts"]:
            self.assertIn(account["sales_stage"], ese.ENTERPRISE_PIPELINE_STAGES + ["REJECTED"])

    def test_pipeline_priority_states_named(self):
        result = ese.enterprise_pipeline_priority()
        for account in result["accounts"]:
            self.assertIn(account["priority"], ese.PIPELINE_PRIORITY_STATES)


class TestAccountRegistryAndStakeholders(unittest.TestCase):
    def test_zero_real_accounts_honestly_disclosed(self):
        result = ese.account_registry()
        self.assertEqual(result["real_accounts"], [])

    def test_stakeholder_map_never_fabricates_identity(self):
        result = ese.stakeholder_map()
        for role, value in result["roles"].items():
            self.assertIn("UNKNOWN", value)


class TestEnterpriseQualification(unittest.TestCase):
    def test_qualification_always_named(self):
        result = ese.enterprise_qualification(_TEST_NICHE)
        self.assertIn(result["qualification"], ese.ENTERPRISE_QUALIFICATION_LEVELS)


class TestPilotToContractConversion(unittest.TestCase):
    def test_decision_always_named(self):
        result = ese.pilot_to_contract_conversion()
        self.assertIn(result["decision"], ese.PILOT_CONVERSION_DECISIONS)

    def test_no_success_is_stop(self):
        result = ese.pilot_to_contract_conversion(pilot_success=False)
        self.assertEqual(result["decision"], "STOP")

    def test_full_success_is_expand(self):
        result = ese.pilot_to_contract_conversion(pilot_success=True, customer_roi_positive=True, user_adoption_high=True)
        self.assertEqual(result["decision"], "EXPAND")

    def test_success_alone_is_revise(self):
        result = ese.pilot_to_contract_conversion(pilot_success=True)
        self.assertEqual(result["decision"], "REVISE")


class TestDealProfitabilityDecision(unittest.TestCase):
    def test_decision_always_named(self):
        result = ese.deal_profitability_decision(expected_revenue=100000, expected_cost=50000, risk_level="LOW")
        self.assertIn(result["decision"], ese.DEAL_PROFITABILITY_DECISIONS)

    def test_negative_margin_is_reject(self):
        result = ese.deal_profitability_decision(expected_revenue=50000, expected_cost=90000, risk_level="LOW")
        self.assertEqual(result["decision"], "REJECT")

    def test_thin_margin_is_renegotiate(self):
        result = ese.deal_profitability_decision(expected_revenue=100000, expected_cost=90000, risk_level="LOW")
        self.assertEqual(result["decision"], "RENEGOTIATE")

    def test_missing_data_is_review_not_accept(self):
        result = ese.deal_profitability_decision()
        self.assertEqual(result["decision"], "REVIEW")

    def test_high_risk_never_auto_accepts(self):
        result = ese.deal_profitability_decision(expected_revenue=100000, expected_cost=50000, risk_level="HIGH")
        self.assertEqual(result["decision"], "REVIEW")


class TestDeliveryProfitability(unittest.TestCase):
    def test_large_contract_can_be_unprofitable(self):
        result = ese.delivery_profitability(contract_revenue=100000, implementation_hours_cost=120000)
        self.assertLess(result["contribution"], 0)

    def test_zero_revenue_is_unknown_margin(self):
        result = ese.delivery_profitability()
        self.assertEqual(result["margin_pct"], "UNKNOWN")


class TestContractRiskCheck(unittest.TestCase):
    def test_eleven_named_categories(self):
        result = ese.contract_risk_check()
        self.assertEqual(len(result["checklist"]), 11)

    def test_never_auto_clears_without_a_real_contract(self):
        result = ese.contract_risk_check()
        for status in result["checklist"].values():
            self.assertIn("NOT_CHECKED", status)


class TestValueBasedRoi(unittest.TestCase):
    def test_never_fabricates_roi_without_real_inputs(self):
        result = ese.value_based_roi()
        self.assertEqual(result["estimated_roi"], "UNKNOWN -- requires real cost + real savings, neither exists for any real deal yet")


class TestSectionSchemas(unittest.TestCase):
    def test_ideal_customer_profile_is_schema_not_example(self):
        result = ese.ideal_enterprise_customer_profile()
        self.assertGreaterEqual(len(result["required_fields"]), 10)

    def test_discovery_record_template_is_schema(self):
        result = ese.discovery_record_template()
        self.assertGreaterEqual(len(result["required_fields"]), 10)

    def test_contract_value_tracker_honestly_empty(self):
        result = ese.contract_value_tracker()
        self.assertEqual(result["real_contracts"], [])

    def test_objection_template_never_pressures(self):
        result = ese.objection_response_template()
        for response in result["objections"].values():
            self.assertNotIn("act now", response.lower())
            self.assertNotIn("limited time", response.lower())


class TestReusedFunctionsReturnDicts(unittest.TestCase):
    def test_opportunity_registry(self):
        self.assertIsInstance(ese.enterprise_opportunity_registry(), dict)

    def test_security_trust_package(self):
        self.assertIsInstance(ese.security_trust_package(), dict)

    def test_ai_governance_disclosure(self):
        self.assertIsInstance(ese.ai_governance_disclosure(), dict)

    def test_enterprise_forecast(self):
        self.assertIsInstance(ese.enterprise_forecast(), dict)

    def test_enterprise_sales_autonomy_boundaries(self):
        self.assertIsInstance(ese.enterprise_sales_autonomy_boundaries(), dict)

    def test_enterprise_red_team(self):
        self.assertIsInstance(ese.enterprise_red_team(_TEST_NICHE), dict)

    def test_enterprise_partnership_signal(self):
        self.assertIsInstance(ese.enterprise_partnership_signal(), dict)

    def test_recurring_enterprise_revenue(self):
        self.assertIsInstance(ese.recurring_enterprise_revenue(), dict)


class TestSimulations(unittest.TestCase):
    def test_run_all_returns_ten_simulations(self):
        result = ese.run_all_phase30_simulations()
        for i in range(1, 11):
            self.assertIn(f"simulation_{i}", result)

    def test_simulation_2_rejects_severe_underfunding(self):
        result = ese.simulation_2_insufficient_budget(requested_scope_cost=50000, offered_budget=1000)
        self.assertEqual(result["decision"], "REJECT")

    def test_simulation_3_pilot_success_expands(self):
        result = ese.simulation_3_pilot_roi_expansion()
        self.assertEqual(result["decision"], "EXPAND")

    def test_simulation_5_flags_unlimited_support_for_human_review(self):
        result = ese.simulation_5_unlimited_support_request()
        self.assertEqual(result["recommendation"], "FLAG_FOR_HUMAN_LEGAL_REVIEW")

    def test_simulation_6_never_fabricates_competitor_value(self):
        result = ese.simulation_6_cheaper_competitor()
        self.assertIn("UNKNOWN", result["competitor_value_per_dollar"])

    def test_none_of_the_simulations_write_to_a_ledger(self):
        from channels import ledger as sales_ledger
        with patch.object(sales_ledger, "append_event") as mock_append:
            ese.run_all_phase30_simulations()
            mock_append.assert_not_called()


class TestDashboard(unittest.TestCase):
    def test_dashboard_computes_every_subreport_once(self):
        result = ese.build_enterprise_sales_dashboard()
        expected_keys = {
            "opportunity_registry", "sales_pipeline", "pipeline_priority", "account_registry",
            "stakeholder_map", "contract_value", "recurring_revenue", "expansion", "partnership",
            "objections", "security_trust", "ai_governance", "delivery_handoff", "contract_risk",
            "forecast", "autonomy_boundaries",
        }
        self.assertTrue(expected_keys.issubset(result.keys()))


if __name__ == "__main__":
    unittest.main()

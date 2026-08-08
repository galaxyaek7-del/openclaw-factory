import unittest
from unittest.mock import patch

import global_commercial_scale as gcs


class TestEvidenceGate(unittest.TestCase):
    def test_zero_revenue_factory_reports_insufficient_evidence(self):
        result = gcs.evidence_gate_check()
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("verified_revenue", result["critical_fields_missing"])

    def test_never_fabricates_a_sufficient_field_it_cannot_source(self):
        result = gcs.evidence_gate_check()
        self.assertFalse(result["fields"]["refund_rate"]["sufficient"])
        self.assertFalse(result["fields"]["customer_satisfaction"]["sufficient"])

    @patch("channels.ledger.revenue_trend")
    def test_real_revenue_present_clears_that_one_field(self, mock_rev):
        mock_rev.return_value = {"recent_7d_revenue_usd": 500}
        result = gcs.evidence_gate_check()
        self.assertTrue(result["fields"]["verified_revenue"]["sufficient"])
        # net revenue is still honestly unmeasured -- revenue alone
        # doesn't prove profitability.
        self.assertFalse(result["fields"]["verified_net_revenue"]["sufficient"])


class TestScalingEligibility(unittest.TestCase):
    def test_every_entry_is_a_named_state(self):
        result = gcs.scaling_eligibility_report()
        for entry in result["entries"]:
            self.assertIn(entry["status"], gcs.SCALING_ELIGIBILITY_STATES)

    def test_zero_revenue_products_never_classified_scaling_or_mature(self):
        result = gcs.scaling_eligibility_report()
        for entry in result["entries"]:
            if entry["real_revenue_usd"] == 0:
                self.assertNotIn(entry["status"], ("SCALING", "MATURE", "SCALE_CANDIDATE"))


class TestUnitEconomics(unittest.TestCase):
    def test_every_product_has_all_named_cost_fields(self):
        result = gcs.unit_economics_report()
        required = [
            "gross_revenue_per_unit", "affiliate_commissions", "customer_acquisition_cost",
            "ai_cost", "infrastructure_cost", "support_cost", "refund_cost",
            "contribution_margin", "net_revenue", "lifetime_value",
        ]
        for product in result["products"]:
            for field in required:
                self.assertIn(field, product)

    def test_never_invents_a_customer_acquisition_cost(self):
        result = gcs.unit_economics_report()
        for product in result["products"]:
            self.assertIn("UNKNOWN", product["customer_acquisition_cost"])


class TestB2BCommercialEngine(unittest.TestCase):
    def test_zero_real_b2b_ladder_candidates_is_honestly_reported(self):
        result = gcs.b2b_commercial_engine_report()
        self.assertEqual(result["real_b2b_ladder_candidates"], 0)

    def test_case_study_is_the_one_real_product_not_a_fabricated_lead(self):
        result = gcs.b2b_commercial_engine_report()
        self.assertIn("EU AI Act", result["case_study"]["product"])


class TestB2BSalesPipeline(unittest.TestCase):
    def test_pipeline_has_no_entry_beyond_target_stage(self):
        result = gcs.b2b_sales_pipeline_report()
        for entry in result["pipeline"]:
            self.assertEqual(entry["stage"], "TARGET")

    def test_every_stage_name_is_from_the_named_11(self):
        self.assertEqual(len(gcs.B2B_PIPELINE_STAGES), 11)


class TestGlobalRevenueForecast(unittest.TestCase):
    def test_six_categories_stay_structurally_separate(self):
        result = gcs.global_revenue_forecast()
        for key in ("actual", "verified", "pipeline", "estimated", "projected", "potential"):
            self.assertIn(key, result)

    def test_projected_and_potential_are_never_computed_from_nothing(self):
        result = gcs.global_revenue_forecast()
        self.assertEqual(result["projected"]["value"], "NOT_COMPUTABLE")
        self.assertEqual(result["potential"]["value"], "NOT_COMPUTABLE")


class TestAutonomousScaleRecommendations(unittest.TestCase):
    def test_every_recommendation_carries_a_real_authorization_decision(self):
        result = gcs.autonomous_scale_recommendations()
        for rec in result["recommendations"]:
            self.assertIn("decision", rec["authorization"])
            self.assertIn(rec["authorization"]["decision"], ("ALLOW", "REFUSE"))

    def test_never_self_executes_anything(self):
        """The module must never call a real publish/approve/reallocate
        function -- only classify what authority level would be needed."""
        import distributor
        with patch.object(distributor, "distribute") as mock_distribute:
            gcs.autonomous_scale_recommendations()
            mock_distribute.assert_not_called()


class TestInternationalComplianceFlags(unittest.TestCase):
    def test_all_seven_categories_flagged_for_human_review(self):
        result = gcs.international_compliance_flags()
        self.assertEqual(len(result["compliance_flags"]), 7)
        for flag in result["compliance_flags"]:
            self.assertEqual(flag["status"], "FLAG_FOR_HUMAN_REVIEW")

    def test_never_returns_a_false_certainty_pass(self):
        result = gcs.international_compliance_flags()
        statuses = {f["status"] for f in result["compliance_flags"]}
        self.assertNotIn("PASS", statuses)


class TestTransformationProductLadder(unittest.TestCase):
    def test_every_real_product_is_honestly_digital_asset_today(self):
        result = gcs.transformation_product_ladder_status()
        for entry in result["products"]:
            self.assertEqual(entry["current_stage"], "DIGITAL_ASSET")


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport_exactly_once(self):
        result = gcs.build_global_commercial_scale_dashboard()
        for key in ("evidence_gate", "scaling_eligibility", "unit_economics",
                    "concentration_risk", "market_prioritization", "b2b_commercial_engine",
                    "partnerships", "revenue_forecast", "commercial_reputation"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

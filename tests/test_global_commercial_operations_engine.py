import unittest
from unittest.mock import patch

import global_commercial_operations_engine as gcoe

_TEST_PRODUCT = "AI-Powered Compliance Automation System for Accounting Firms"
_TEST_PLATFORM = "amazon"


class TestCommercialTruthTag(unittest.TestCase):
    def test_valid_status_accepted(self):
        result = gcoe.commercial_truth_tag(100, "VERIFIED")
        self.assertEqual(result["status"], "VERIFIED")

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            gcoe.commercial_truth_tag(100, "TOTALLY_MADE_UP")


class TestPlatformRegistry(unittest.TestCase):
    def test_reuses_real_registry(self):
        result = gcoe.platform_registry()
        self.assertGreater(result["total_real_platforms"], 0)


class TestPlatformFit(unittest.TestCase):
    def test_verdict_always_named(self):
        result = gcoe.platform_fit(_TEST_PRODUCT, _TEST_PLATFORM)
        self.assertIn(result["verdict"], gcoe.PLATFORM_FIT_VERDICTS)

    def test_unrecognized_platform_is_unknown(self):
        result = gcoe.platform_fit(_TEST_PRODUCT, "not_a_real_platform")
        self.assertEqual(result["verdict"], "UNKNOWN")

    def test_unrecognized_product_is_unknown(self):
        result = gcoe.platform_fit("a product that does not exist", _TEST_PLATFORM)
        self.assertEqual(result["verdict"], "UNKNOWN")


class TestProductPlatformMatrix(unittest.TestCase):
    def test_matrix_has_real_entries(self):
        result = gcoe.product_platform_matrix()
        self.assertGreater(result["total_real_entries"], 0)


class TestOrderNormalization(unittest.TestCase):
    def test_every_order_has_a_classified_revenue_type(self):
        result = gcoe.order_normalization_view()
        for order in result["orders"]:
            self.assertIn("revenue_type", order)


class TestPlatformExpansionExit(unittest.TestCase):
    def test_never_auto_activates_unknown_platform(self):
        result = gcoe.platform_expansion_check("a completely unregistered platform")
        self.assertEqual(result["recommendation"], "UNKNOWN")

    def test_exit_never_recommended_purely_from_historical_revenue(self):
        result = gcoe.platform_exit_check(_TEST_PLATFORM)
        self.assertIn("recommend_exit", result)


class TestCommercialGovernance(unittest.TestCase):
    def test_five_named_levels(self):
        self.assertEqual(len(gcoe.COMMERCIAL_GOVERNANCE_LEVELS), 5)

    def test_reuses_autonomous_operations_verbatim(self):
        result = gcoe.commercial_governance_view()
        self.assertIn("autonomous_operations.py", result["source"])


class TestAnomalyDetection(unittest.TestCase):
    def test_never_auto_classifies_as_fraud(self):
        result = gcoe.commercial_anomaly_detection()
        self.assertIn("anomaly_detected", result)
        self.assertNotIn("fraud", str(result.get("anomaly_detected")).lower())


class TestSimulations(unittest.TestCase):
    def test_simulation_a_labels_hypothetical(self):
        result = gcoe.simulation_a_multi_platform_net_contribution()
        self.assertIn("HYPOTHETICAL", result["label"])

    def test_simulation_b_computes_real_arithmetic(self):
        result = gcoe.simulation_b_partner_profitability_with_refunds(gross_revenue=1000, commission_rate=0.2, refund_rate=0.3)
        self.assertEqual(result["net_contribution"], 500.0)
        self.assertTrue(result["remains_profitable"])

    def test_simulation_b_detects_unprofitable_partner(self):
        result = gcoe.simulation_b_partner_profitability_with_refunds(gross_revenue=1000, commission_rate=0.4, refund_rate=0.7)
        self.assertFalse(result["remains_profitable"])

    def test_simulation_c_low_margin_flags_review(self):
        result = gcoe.simulation_c_high_revenue_poor_margin(gross_revenue=10000, margin_pct=0.02)
        self.assertEqual(result["recommendation"], "REVIEW_OR_EXIT")

    def test_simulation_d_computes_real_discrepancy(self):
        result = gcoe.simulation_d_payout_discrepancy(expected_payout=500, actual_payout=430)
        self.assertEqual(result["discrepancy"], 70)

    def test_simulation_g_is_real_not_hypothetical(self):
        result = gcoe.simulation_g_concentration_warning()
        self.assertIn("REAL", result["label"])

    def test_run_all_returns_eight_simulations(self):
        result = gcoe.run_all_commercial_simulations()
        for key in ("simulation_a", "simulation_b", "simulation_c", "simulation_d",
                    "simulation_e", "simulation_f", "simulation_g", "simulation_h"):
            self.assertIn(key, result)

    def test_none_of_the_hypothetical_simulations_write_to_a_ledger(self):
        """A real regression guard: simulations must never call a real
        ledger-writing function."""
        from channels import ledger as sales_ledger
        with patch.object(sales_ledger, "append_event") as mock_append:
            gcoe.run_all_commercial_simulations()
            mock_append.assert_not_called()


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = gcoe.build_commercial_operations_dashboard()
        for key in ("platform_registry", "product_platform_matrix", "multi_currency",
                    "commission_engine", "order_normalization", "refund_normalization",
                    "payout_reconciliation", "platform_account_health", "payment_infrastructure",
                    "commercial_task_queue", "commercial_alerts", "anomaly_detection",
                    "fraud_protection", "channel_profitability", "concentration_risk", "governance"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

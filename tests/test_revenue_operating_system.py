import json
import os
import tempfile
import unittest
from unittest.mock import patch

import revenue_operating_system as ros


def _temp_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


class TestRevenueClassification(unittest.TestCase):
    def test_non_sale_events_are_other(self):
        self.assertEqual(ros.classify_revenue_event({"event_type": "publish_attempt"}), "OTHER")

    def test_plain_paddle_sale_is_sale(self):
        event = {"event_type": "sale", "platform": "paddle", "raw": {"id": "txn_1"}}
        self.assertEqual(ros.classify_revenue_event(event), "SALE")

    def test_partner_tagged_sale_is_partnership(self):
        event = {"event_type": "sale", "platform": "paddle", "partner": "acme", "raw": {}}
        self.assertEqual(ros.classify_revenue_event(event), "PARTNERSHIP")

    def test_unrecognized_platform_is_unknown_never_guessed(self):
        event = {"event_type": "sale", "platform": "totally_new_platform", "raw": {}}
        self.assertEqual(ros.classify_revenue_event(event), "UNKNOWN")

    def test_report_never_drops_an_event(self):
        path = _temp_jsonl([
            {"event_type": "sale", "platform": "paddle", "raw": {"id": "1"}},
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "2"}},
        ])
        report = ros.revenue_classification_report(ledger_path=path)
        self.assertEqual(report["total_events"], 2)
        self.assertEqual(sum(report["by_type"].values()), 2)
        os.remove(path)


class TestGrossVsNet(unittest.TestCase):
    def test_zero_gross_never_reports_a_fabricated_net(self):
        report = ros.gross_vs_net_report(ledger_path=_temp_jsonl([]))
        self.assertEqual(report["gross_revenue_usd"], 0)
        self.assertEqual(report["net_revenue_usd"], 0)

    def test_never_calls_gross_revenue_profit(self):
        report = ros.gross_vs_net_report(ledger_path=_temp_jsonl([]))
        self.assertNotIn("profit", str(report.get("gross_revenue_usd", "")).lower())


class TestCurrencyStatus(unittest.TestCase):
    def test_honestly_not_built(self):
        result = ros.currency_status()
        self.assertEqual(result["status"], "NOT_BUILT")
        self.assertEqual(result["supported_currencies"], ["USD"])


class TestIdempotency(unittest.TestCase):
    def test_distinguishes_finance_layer_from_ledger_append_layer(self):
        result = ros.idempotency_status(ledger_path=_temp_jsonl([]))
        self.assertIn("IDEMPOTENT", result["finance_reconciliation_layer"])
        self.assertIn("NOT_IDEMPOTENT", result["raw_ledger_append_layer"])

    def test_detects_real_raw_duplicates(self):
        path = _temp_jsonl([
            {"event_type": "sale", "platform": "paddle", "raw": {"id": "dup_1"}},
            {"event_type": "sale", "platform": "paddle", "raw": {"id": "dup_1"}},
        ])
        result = ros.idempotency_status(ledger_path=path)
        self.assertEqual(result["real_raw_ledger_duplicates_found"], 1)
        os.remove(path)


class TestReconciliationStateView(unittest.TestCase):
    @patch("commercial_reconciliation.reconcile_all")
    def test_reconciled_maps_to_matched(self, mock_reconcile):
        mock_reconcile.return_value = {"platforms": {"paddle": {"platform": "paddle", "status": "RECONCILED", "discrepancies": []}}}
        result = ros.reconciliation_state_view()
        self.assertEqual(result["platforms"][0]["named_state"], "MATCHED")

    @patch("commercial_reconciliation.reconcile_all")
    def test_discrepancy_maps_to_mismatch(self, mock_reconcile):
        mock_reconcile.return_value = {"platforms": {"paddle": {"platform": "paddle", "status": "DISCREPANCY_FOUND", "discrepancies": [{"difference_usd": 50}]}}}
        result = ros.reconciliation_state_view()
        self.assertEqual(result["platforms"][0]["named_state"], "MISMATCH")

    @patch("commercial_reconciliation.reconcile_all")
    def test_not_reconcilable_maps_to_unknown_never_matched(self, mock_reconcile):
        mock_reconcile.return_value = {"platforms": {"gumroad": {"platform": "gumroad", "status": "NOT_RECONCILABLE", "discrepancies": []}}}
        result = ros.reconciliation_state_view()
        self.assertEqual(result["platforms"][0]["named_state"], "UNKNOWN")
        self.assertNotEqual(result["platforms"][0]["named_state"], "MATCHED")


class TestGovernanceHonesty(unittest.TestCase):
    def test_receivables_never_fabricates_an_outstanding_amount(self):
        result = ros.receivables_report()
        self.assertEqual(result["total_outstanding_usd"], 0)
        self.assertEqual(result["receivables"], [])

    def test_subscription_metrics_never_computed_from_zero_subscriptions(self):
        result = ros.subscription_engine_status()
        for metric in ("mrr", "arr", "churn_rate", "retention", "customer_lifetime_value"):
            self.assertTrue(result[metric].startswith("NOT_COMPUTABLE"))

    def test_payment_vs_revenue_never_assumes_checkout_equals_cash(self):
        result = ros.payment_vs_revenue_status()
        self.assertTrue(result["recognition_rule_status"].startswith("FLAG_FOR_HUMAN_ACCOUNTING_REVIEW"))

    def test_commission_never_reports_expected_as_actual(self):
        result = ros.commission_engine_report()
        self.assertEqual(result["confirmed_commission_usd"], 0)
        self.assertEqual(result["paid_commission_usd"], 0)


class TestRevenueLeakageReport(unittest.TestCase):
    def test_never_crashes_when_a_subcheck_fails(self):
        with patch("product_master_catalog.build_product_master_catalog", side_effect=RuntimeError("boom")):
            result = ros.revenue_leakage_report(ledger_path=_temp_jsonl([]))
            statuses = [f.get("status") for f in result["findings"]]
            self.assertIn("CHECK_FAILED", statuses)

    def test_discloses_not_architected_categories_rather_than_claiming_clean(self):
        result = ros.revenue_leakage_report(ledger_path=_temp_jsonl([]))
        self.assertGreater(len(result["not_architected_checks"]), 0)


class TestDataQualityReport(unittest.TestCase):
    def test_empty_ledger_is_honest_zero_issues(self):
        result = ros.data_quality_report(ledger_path=_temp_jsonl([]))
        self.assertEqual(result["total_real_events_checked"], 0)

    def test_missing_platform_detected(self):
        path = _temp_jsonl([{"event_type": "sale", "raw": {"id": "1"}, "timestamp": "2026-01-01"}])
        result = ros.data_quality_report(ledger_path=path)
        self.assertEqual(result["issues"]["missing_platform"], 1)
        os.remove(path)


class TestRevenueHealthScore(unittest.TestCase):
    def test_never_produces_a_single_fabricated_composite_number(self):
        result = ros.revenue_health_score()
        self.assertNotIn("overall_score", result)
        self.assertNotIn("composite_score", result)
        self.assertIn("components", result)

    def test_ten_named_components_present(self):
        result = ros.revenue_health_score()
        self.assertEqual(len(result["components"]), 10)


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = ros.build_revenue_operating_system_dashboard()
        for key in ("source_of_truth", "revenue_classification", "gross_vs_net", "currency",
                    "ledger_conformance", "idempotency", "reconciliation", "payment_vs_revenue",
                    "subscriptions", "commissions", "b2b_revenue", "receivables", "payouts",
                    "leakage", "data_quality", "revenue_health"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

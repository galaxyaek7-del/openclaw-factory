import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import commercial_activation as ca


class TestCommercialLifecycleState(unittest.TestCase):
    def test_unknown_entry_is_unknown(self):
        result = ca.evaluate_commercial_lifecycle_state({})
        self.assertEqual(result["state"], "UNKNOWN")

    def test_never_advances_past_checkout_available_without_real_payment_evidence(self):
        entry = {"product_id": "pro_x", "price_id": "pri_x"}
        result = ca.evaluate_commercial_lifecycle_state(entry, checkout_ready=True)
        self.assertEqual(result["state"], "CHECKOUT_AVAILABLE")
        self.assertNotIn(result["state"], ("PAYMENT_CONFIRMED", "ORDER_CONFIRMED", "REVENUE_RECORDED"))

    def test_checkout_ready_false_is_honestly_blocked(self):
        entry = {"product_id": "pro_x", "price_id": "pri_x"}
        result = ca.evaluate_commercial_lifecycle_state(entry, checkout_ready=False)
        self.assertTrue(result["blocked"])

    def test_unsupplied_checkout_status_is_not_assumed_true(self):
        entry = {"product_id": "pro_x", "price_id": "pri_x"}
        result = ca.evaluate_commercial_lifecycle_state(entry, checkout_ready=None)
        self.assertIsNone(result["blocked"])
        self.assertNotEqual(result["state"], "CHECKOUT_AVAILABLE")


class TestPlatformActivationReadiness(unittest.TestCase):
    def test_returns_all_eight_named_dimensions(self):
        result = ca.platform_activation_readiness("paddle")
        for key in ("TECHNICAL_READY", "COMMERCIAL_READY", "CHECKOUT_READY", "PAYMENT_READY",
                    "DELIVERY_READY", "FINANCE_READY", "WEBHOOK_READY", "PAYOUT_READY"):
            self.assertIn(key, result)

    def test_never_collapses_into_one_score(self):
        result = ca.platform_activation_readiness("paddle")
        self.assertNotIn("overall_score", result)
        self.assertNotIn("score", result)

    def test_uncredentialed_platform_reports_false_commercial_ready(self):
        result = ca.platform_activation_readiness("gumroad")
        self.assertFalse(result["credential_valid"])
        self.assertFalse(result["COMMERCIAL_READY"])

    def test_payout_ready_is_honestly_not_available_not_zero(self):
        result = ca.platform_activation_readiness("paddle")
        self.assertIn("NOT_AVAILABLE", result["PAYOUT_READY"])


class TestFounderActionCenter(unittest.TestCase):
    def test_every_action_has_required_fields(self):
        result = ca.founder_action_center()
        for action in result["actions"]:
            for field in ("why_required", "what_to_do", "unlocks", "current_status"):
                self.assertIn(field, action)

    def test_never_lists_an_engineering_task(self):
        result = ca.founder_action_center()
        for action in result["actions"]:
            self.assertNotIn("write code", action["what_to_do"].lower())
            self.assertNotIn("implement", action["what_to_do"].lower())


class TestGoldenHunterFreshness(unittest.TestCase):
    def test_missing_file_is_reported_missing(self):
        result = ca.golden_hunter_freshness_status(golden_json_path="/nonexistent/path.json")
        self.assertEqual(result["status"], "MISSING")

    def test_fresh_file_is_reported_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "golden.json")
            now = datetime.now(timezone.utc)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"generated_at": now.isoformat(), "count": 5}, f)
            result = ca.golden_hunter_freshness_status(golden_json_path=path, now=now)
            self.assertEqual(result["status"], "FRESH")

    def test_stale_file_is_reported_stale_not_silently_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "golden.json")
            old = datetime.now(timezone.utc) - timedelta(hours=100)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"generated_at": old.isoformat(), "count": 5}, f)
            result = ca.golden_hunter_freshness_status(golden_json_path=path)
            self.assertEqual(result["status"], "STALE")

    def test_never_fabricates_freshness_from_missing_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "golden.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"count": 5}, f)
            result = ca.golden_hunter_freshness_status(golden_json_path=path)
            self.assertEqual(result["status"], "MISSING_TIMESTAMP")


class TestRefundDisputeChargeback(unittest.TestCase):
    def test_covers_all_four_platforms(self):
        result = ca.refund_dispute_chargeback_status()
        for platform in ("gumroad", "paddle", "etsy", "payhip"):
            self.assertIn(platform, result["platforms"])

    def test_not_available_is_never_confused_with_zero(self):
        result = ca.refund_dispute_chargeback_status()
        for platform_data in result["platforms"].values():
            self.assertNotEqual(platform_data["refunds"], 0)
            self.assertNotEqual(platform_data["disputes"], 0)


class TestAggregator(unittest.TestCase):
    def test_returns_all_required_sections(self):
        result = ca.build_commercial_activation_status()
        for key in ("readiness", "founder_action_center", "golden_hunter_freshness", "refunds_disputes_chargebacks"):
            self.assertIn(key, result)

    def test_never_writes_any_file(self):
        before = set(os.listdir("data"))
        ca.build_commercial_activation_status()
        after = set(os.listdir("data"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

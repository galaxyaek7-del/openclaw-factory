"""Tests for commercial_alerts.py (ADR-202, 2026-08-07).

    python -m unittest tests.test_commercial_alerts -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import commercial_alerts as ca


class TestAssessCommercialAlerts(unittest.TestCase):
    def test_real_call_never_raises(self):
        result = ca.assess_commercial_alerts()
        self.assertIn("findings", result)
        self.assertIn("active_alerts", result)

    def test_every_finding_has_the_shared_shape(self):
        result = ca.assess_commercial_alerts()
        for f in result["findings"]:
            self.assertIn("area", f)
            self.assertIn("severity", f)
            self.assertIn("detail", f)
            self.assertIn("evidence", f)
            self.assertIn("data_available", f)

    def test_not_architected_triggers_each_have_a_specific_reason(self):
        result = ca.assess_commercial_alerts()
        self.assertEqual(len(result["not_architected_triggers"]), 5)
        for trigger, reason in result["not_architected_triggers"].items():
            self.assertGreater(len(reason), 20, trigger)

    def test_active_alerts_only_includes_warning_or_above(self):
        result = ca.assess_commercial_alerts()
        for alert in result["active_alerts"]:
            self.assertIn(alert["severity"], ("warning", "critical", "emergency"))


class TestRevenueDropCheck(unittest.TestCase):
    def test_critical_when_recent_daily_average_less_than_half_trailing(self):
        with patch("channels.ledger.revenue_trend", return_value={
            "trailing_daily_avg_usd": 100.0, "recent_7d_revenue_usd": 100.0, "total_sales_count": 10,
        }):
            result = ca._check_revenue_drop()
        self.assertEqual(result["severity"], "critical")

    def test_informational_when_no_real_sales_exist(self):
        with patch("channels.ledger.revenue_trend", return_value={
            "trailing_daily_avg_usd": None, "recent_7d_revenue_usd": 0, "total_sales_count": 0,
        }):
            result = ca._check_revenue_drop()
        self.assertEqual(result["severity"], "informational")
        self.assertFalse(result["data_available"])


class TestCheckoutUnavailableCheck(unittest.TestCase):
    def test_critical_on_real_checkout_failure_event(self):
        fake_events = [
            {"event_type": "publish_attempt", "platform": "paddle", "ok": False, "error": "transaction_checkout_not_enabled"},
        ]
        with patch("channels.ledger.read_events", return_value=fake_events):
            result = ca._check_checkout_unavailable()
        self.assertEqual(result["severity"], "critical")

    def test_informational_when_no_checkout_failures(self):
        with patch("channels.ledger.read_events", return_value=[]):
            result = ca._check_checkout_unavailable()
        self.assertEqual(result["severity"], "informational")


if __name__ == "__main__":
    unittest.main()

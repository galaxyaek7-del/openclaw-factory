"""Tests for commercial_acquisition.py (ADR-202, 2026-08-07).

    python -m unittest tests.test_commercial_acquisition -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import commercial_acquisition as caq


class TestCustomerAcquisitionReport(unittest.TestCase):
    def test_all_9_named_channels_present(self):
        r = caq.customer_acquisition_report(ledger_events=[])
        self.assertEqual(set(r["channels"].keys()), set(caq.ACQUISITION_CHANNELS))

    def test_channel_with_no_real_data_honestly_insufficient(self):
        r = caq.customer_acquisition_report(ledger_events=[])
        for channel, report in r["channels"].items():
            self.assertEqual(report["status"], "INSUFFICIENT_DATA")

    def test_channel_with_real_attributed_sales_computes_revenue(self):
        events = [
            {"channel": "affiliate", "raw": {}, "amount": 50},
            {"channel": "affiliate", "raw": {}, "amount": 30},
        ]
        r = caq.customer_acquisition_report(ledger_events=events)
        self.assertEqual(r["channels"]["affiliate"]["revenue_usd"], 80)
        self.assertEqual(r["channels"]["affiliate"]["sale_count"], 2)
        self.assertIn("affiliate", r["channels_with_real_data"])

    def test_cac_ltv_roi_still_insufficient_even_with_revenue_data(self):
        """A real revenue figure existing doesn't fabricate a CAC/LTV/ROI
        that requires separate real signals this factory doesn't have."""
        events = [{"channel": "direct", "raw": {}, "amount": 100}]
        r = caq.customer_acquisition_report(ledger_events=events)
        direct = r["channels"]["direct"]
        self.assertEqual(direct["cac"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(direct["ltv"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(direct["roi"]["status"], "INSUFFICIENT_DATA")


class TestCommercialFunnel(unittest.TestCase):
    def test_all_11_named_stages_present(self):
        r = caq.commercial_funnel(conversion_summary={"answer": "Unknown", "reason": "no data"})
        self.assertEqual(set(r["stages"].keys()), set(caq.FUNNEL_STAGES))

    def test_top_funnel_stages_honestly_no_real_source(self):
        r = caq.commercial_funnel(conversion_summary={"answer": "Unknown"})
        for stage in ("market", "visitor", "lead", "qualified_lead", "trial_interest"):
            self.assertEqual(r["stages"][stage]["status"], "NO_REAL_SOURCE")

    def test_customer_stage_uses_real_conversion_summary_when_available(self):
        fake_summary = {"stage_reach_counts": {"PAID": 3, "NEW": 10}}
        r = caq.commercial_funnel(conversion_summary=fake_summary)
        self.assertEqual(r["stages"]["customer"]["real_count"], 3)
        self.assertEqual(r["stages"]["customer"]["status"], "OK")

    def test_partner_stage_cites_business_development_pipeline(self):
        r = caq.commercial_funnel(conversion_summary={"answer": "Unknown"})
        self.assertEqual(r["stages"]["partner"]["status"], "OK")
        self.assertIn("business_development.py", r["stages"]["partner"]["source"])


if __name__ == "__main__":
    unittest.main()

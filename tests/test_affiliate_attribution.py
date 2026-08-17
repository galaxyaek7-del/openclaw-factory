"""Tests for the directive-section-7/8 extensions:
attributed click tracking (UTM/channel) and the full Revenue Intelligence
dashboard.

    python -m unittest tests.test_affiliate_attribution -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate_commerce import click_tracking
from revenue_intelligence import revenue_intelligence_dashboard


def _temp_ledger():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestUtmCapture(unittest.TestCase):
    """Evidence Chain + Attribution phase (2026-08-17): privacy-minimal
    UTM capture. parse_utm_query must extract ONLY the real UTM fields
    that exist in a query dict -- never a guessed placeholder, never an
    empty field for something absent."""

    def test_extracts_only_present_utm_fields(self):
        query = {
            "utm_source": "x", "utm_medium": "social",
            "utm_campaign": "standing-desk-launch", "utm_content": "top-link",
            "page_id": "solutions", "foo": "bar",
        }
        out = click_tracking.parse_utm_query(query)
        self.assertEqual(out, {
            "utm_source": "x", "utm_medium": "social",
            "utm_campaign": "standing-desk-launch", "utm_content": "top-link",
        })

    def test_partial_utm_returns_only_what_exists(self):
        out = click_tracking.parse_utm_query({"utm_source": "linkedin"})
        self.assertEqual(out, {"utm_source": "linkedin"})

    def test_missing_or_empty_utm_returns_empty(self):
        self.assertEqual(click_tracking.parse_utm_query({}), {})
        self.assertEqual(click_tracking.parse_utm_query({"utm_source": "  "}), {})
        self.assertEqual(click_tracking.parse_utm_query(None), {})

    def test_non_string_utm_ignored(self):
        self.assertEqual(click_tracking.parse_utm_query({"utm_source": 42}), {})


class TestSourcePropagation(unittest.TestCase):
    """Evidence Chain + Attribution phase (2026-08-17): a real recorded
    click/page-view carries its real source into the read-model
    (clicks_by_source/page_views_by_source). A record with NO attribution
    is honestly grouped as UNSET -- never invented."""

    def test_attributed_click_groups_under_real_source(self):
        path = _temp_ledger()
        try:
            click_tracking.record_attributed_click(
                "CO-zapier-affiliate", channel="linkedin", campaign="saas-automation",
                content="post-01", utm_medium="social", utm_source="linkedin",
                ledger_path=path)
            summary = click_tracking.clicks_by_source(ledger_path=path)
            self.assertEqual(summary["clicks_by_source"], {"linkedin": 1})
            self.assertEqual(summary["total_real_clicks"], 1)
        finally:
            os.remove(path)

    def test_explicit_source_field_used_when_no_utm(self):
        path = _temp_ledger()
        try:
            click_tracking.record_attributed_click(
                "CO-zapier-affiliate", source="manual-outreach",
                ledger_path=path)
            summary = click_tracking.clicks_by_source(ledger_path=path)
            self.assertEqual(summary["clicks_by_source"], {"manual-outreach": 1})
        finally:
            os.remove(path)

    def test_attributed_page_view_groups_under_real_source(self):
        path = _temp_ledger()
        try:
            click_tracking.record_attributed_page_view(
                "solutions", referrer="https://x.com/some/status", utm_source="x",
                utm_medium="social", utm_campaign="solutions-launch",
                ledger_path=path)
            summary = click_tracking.page_views_by_source(ledger_path=path)
            self.assertEqual(summary["page_views_by_source"], {"x": 1})
            self.assertEqual(summary["total_real_page_views"], 1)
        finally:
            os.remove(path)

    def test_missing_source_is_honest_unset(self):
        path = _temp_ledger()
        try:
            click_tracking.record_attributed_click(
                "CO-zapier-affiliate", ledger_path=path)
            summary = click_tracking.clicks_by_source(ledger_path=path)
            self.assertEqual(summary["clicks_by_source"], {"UNSET": 1})
        finally:
            os.remove(path)

    def test_source_grouping_never_touches_real_ledger(self):
        real_count = click_tracking.clicks_by_source()["total_real_clicks"]
        path = _temp_ledger()
        try:
            click_tracking.record_attributed_click(
                "CO-zapier-affiliate", utm_source="x", ledger_path=path)
        finally:
            os.remove(path)
        after_count = click_tracking.clicks_by_source()["total_real_clicks"]
        self.assertEqual(real_count, after_count)


class TestAttributedClickTracking(unittest.TestCase):
    def test_attributed_click_records_full_context(self):
        path = _temp_ledger()
        try:
            rec = click_tracking.record_attributed_click(
                "CO-zapier-affiliate",
                channel="linkedin", campaign="saas-automation", content="post-01",
                utm_medium="social", utm_source="linkedin",
                ledger_path=path,
            )
            self.assertEqual(rec["channel"], "linkedin")
            self.assertEqual(rec["campaign"], "saas-automation")
            self.assertEqual(rec["content"], "post-01")
            self.assertEqual(rec["utm_medium"], "social")
            loaded = click_tracking.read_clicks(path)
            self.assertEqual(len(loaded), 1)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_attributed_summary_groups_by_real_fields(self):
        path = _temp_ledger()
        try:
            click_tracking.record_attributed_click("CO-a", channel="x", campaign="c1", ledger_path=path)
            click_tracking.record_attributed_click("CO-a", channel="x", campaign="c1", ledger_path=path)
            click_tracking.record_attributed_click("CO-b", channel="linkedin", campaign="c2", ledger_path=path)
            s = click_tracking.attributed_click_summary(path)
            self.assertEqual(s["total_real_clicks"], 3)
            self.assertEqual(s["clicks_by_channel"]["x"], 2)
            self.assertEqual(s["clicks_by_channel"]["linkedin"], 1)
            self.assertEqual(s["clicks_by_campaign"]["c1"], 2)
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestRevenueDashboard(unittest.TestCase):
    def test_dashboard_honest_with_zero_data(self):
        click_path = _temp_ledger()
        view_path = _temp_ledger()
        comm_path = _temp_ledger()
        try:
            d = revenue_intelligence_dashboard(view_path, click_path, comm_path)
            self.assertEqual(d["CLICKS"], 0)
            self.assertEqual(d["PAGE_VIEWS"], 0)
            self.assertEqual(d["REVENUE_COMMISSION_USD"], 0.0)
            # Zero denominators -> N/A, never a fabricated rate.
            self.assertIn("N/A", str(d["CTR"]))
            self.assertIn("N/A", str(d["EPC_USD"]))
        finally:
            for p in (click_path, view_path, comm_path):
                if os.path.exists(p):
                    os.remove(p)

    def test_dashboard_aggregates_real_rows_only(self):
        click_path = _temp_ledger()
        view_path = _temp_ledger()
        comm_path = _temp_ledger()
        try:
            with open(view_path, "w", encoding="utf-8") as f:
                f.write('{"page_id": "p1", "timestamp": "2026-08-10T00:00:00+00:00"}\n')
            click_tracking.record_click("CO-zapier-affiliate", ledger_path=click_path)
            click_tracking.record_click("CO-n8n-affiliate", ledger_path=click_path)
            with open(comm_path, "w", encoding="utf-8") as f:
                # TEST row must NOT count; REAL CONFIRMED row counts.
                f.write('{"opportunity_id": "CO-zapier-affiliate", "environment": "TEST", "commission_status": "PAID", "gross_commission": 999.0}\n')
                f.write('{"opportunity_id": "CO-n8n-affiliate", "environment": "REAL", "commission_status": "CONFIRMED", "gross_commission": 30.0}\n')
            d = revenue_intelligence_dashboard(view_path, click_path, comm_path)
            self.assertEqual(d["PAGE_VIEWS"], 1)
            self.assertEqual(d["CLICKS"], 2)
            self.assertEqual(d["CONVERSIONS"], 1)
            self.assertEqual(d["REVENUE_COMMISSION_USD"], 30.0)
            self.assertEqual(d["RECURRING_COMMISSION_USD"], 0.0)  # n8n not in recurring filter here
            self.assertEqual(d["REVENUE_PER_1000_VIEWS"], 30000.0)
            self.assertIn(("CO-n8n-affiliate", 30.0), d["TOP_PRODUCTS_BY_COMMISSION"])
        finally:
            for p in (click_path, view_path, comm_path):
                if os.path.exists(p):
                    os.remove(p)


if __name__ == "__main__":
    unittest.main()
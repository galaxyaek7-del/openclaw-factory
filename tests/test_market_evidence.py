"""Tests for market_evidence.py (Market Learning Loop, Executive Directive,
2026-07-22).

Runs with stdlib unittest. No live network calls, no live Gmail/CRM
integration to mock -- this module only reads/writes a real, isolated
JSONL file per test.

    python -m unittest tests.test_market_evidence -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_evidence as me


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestRecordAndReadEvidence(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_records_a_real_event_and_reads_it_back(self):
        me.record_evidence("test niche", "demo_request", {"who": "real prospect"}, evidence_path=self.path)
        events = me.read_evidence("test niche", evidence_path=self.path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "demo_request")
        self.assertEqual(events[0]["payload"]["who"], "real prospect")
        self.assertIsNone(events[0]["note"])

    def test_unrecognized_event_type_is_recorded_not_dropped_but_flagged(self):
        event = me.record_evidence("test niche", "totally_made_up_type", {}, evidence_path=self.path)
        self.assertIsNotNone(event["note"])
        events = me.read_evidence("test niche", evidence_path=self.path)
        self.assertEqual(len(events), 1)

    def test_missing_file_reads_as_empty_not_an_error(self):
        events = me.read_evidence("anything", evidence_path=self.path)
        self.assertEqual(events, [])

    def test_filters_by_niche_and_event_type_independently(self):
        me.record_evidence("niche A", "demo_request", {}, evidence_path=self.path)
        me.record_evidence("niche A", "pricing_objection", {}, evidence_path=self.path)
        me.record_evidence("niche B", "demo_request", {}, evidence_path=self.path)
        self.assertEqual(len(me.read_evidence("niche A", evidence_path=self.path)), 2)
        self.assertEqual(len(me.read_evidence(event_type="demo_request", evidence_path=self.path)), 2)
        self.assertEqual(len(me.read_evidence("niche A", "demo_request", evidence_path=self.path)), 1)

    def test_corrupt_line_is_skipped_not_fatal(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("not valid json\n")
            f.write(json.dumps({"niche": "n", "event_type": "demo_request", "payload": {}}) + "\n")
        events = me.read_evidence("n", evidence_path=self.path)
        self.assertEqual(len(events), 1)


class TestWillingnessToPaySignal(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_no_evidence_is_none_not_a_fabricated_zero(self):
        self.assertIsNone(me.get_willingness_to_pay_signal("untouched niche", evidence_path=self.path))

    def test_real_positive_signals_counted(self):
        me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        me.record_evidence("n", "closed_sale", {}, evidence_path=self.path)
        signal = me.get_willingness_to_pay_signal("n", evidence_path=self.path)
        self.assertEqual(signal["positive_signals"], 2)
        self.assertEqual(signal["pricing_objections"], 0)

    def test_real_pricing_objections_counted(self):
        me.record_evidence("n", "pricing_objection", {"detail": "too expensive"}, evidence_path=self.path)
        signal = me.get_willingness_to_pay_signal("n", evidence_path=self.path)
        self.assertEqual(signal["pricing_objections"], 1)
        self.assertEqual(signal["positive_signals"], 0)


class TestCustomerAcquisitionSignal(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_no_evidence_is_none(self):
        self.assertIsNone(me.get_customer_acquisition_signal("untouched", evidence_path=self.path))

    def test_real_reply_rate_computed_from_logged_sent_count(self):
        me.record_evidence("n", "cold_outreach_result", {"sent": 20}, evidence_path=self.path)
        me.record_evidence("n", "email_reply", {}, evidence_path=self.path)
        me.record_evidence("n", "email_reply", {}, evidence_path=self.path)
        signal = me.get_customer_acquisition_signal("n", evidence_path=self.path)
        self.assertEqual(signal["sent"], 20)
        self.assertEqual(signal["replied"], 2)
        self.assertEqual(signal["reply_rate_pct"], 10.0)


class TestRetentionSignal(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_no_evidence_is_none_zero_real_sales_means_zero_real_retention_data(self):
        self.assertIsNone(me.get_retention_signal("untouched", evidence_path=self.path))

    def test_real_renewal_and_churn_counted(self):
        me.record_evidence("n", "retention_signal", {"outcome": "renewed"}, evidence_path=self.path)
        me.record_evidence("n", "retention_signal", {"outcome": "churned"}, evidence_path=self.path)
        me.record_evidence("n", "retention_signal", {"outcome": "churned"}, evidence_path=self.path)
        signal = me.get_retention_signal("n", evidence_path=self.path)
        self.assertEqual(signal["renewed"], 1)
        self.assertEqual(signal["churned"], 2)


class TestCompetitorEvidence(unittest.TestCase):
    """Market Evidence & Alerting layer (2026-07-23): the 9 competitor-
    landscape event types are the one real exception to this module's
    "never reject" convention -- a claim about a THIRD PARTY's business
    requires a real, checkable citation."""

    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_competitor_event_without_competitor_or_source_url_is_rejected(self):
        with self.assertRaises(ValueError):
            me.record_evidence("n", "competitor_funding_round", {}, evidence_path=self.path)

    def test_competitor_event_missing_only_source_url_is_rejected(self):
        with self.assertRaises(ValueError):
            me.record_evidence("n", "competitor_funding_round", {"competitor": "Acme"}, evidence_path=self.path)

    def test_competitor_event_missing_only_competitor_name_is_rejected(self):
        with self.assertRaises(ValueError):
            me.record_evidence("n", "competitor_funding_round", {"source_url": "https://example.com/news"}, evidence_path=self.path)

    def test_fully_cited_competitor_event_is_recorded(self):
        event = me.record_evidence(
            "n", "competitor_funding_round",
            {"competitor": "Acme", "source_url": "https://example.com/news", "amount": "$5M Series A"},
            evidence_path=self.path,
        )
        self.assertIsNone(event["note"])
        events = me.read_evidence("n", "competitor_funding_round", evidence_path=self.path)
        self.assertEqual(len(events), 1)

    def test_pre_existing_15_event_types_are_completely_unaffected(self):
        """Backward compatibility: the stricter gate is scoped ONLY to
        COMPETITOR_EVENT_TYPES -- every pre-existing category still
        records with zero payload, exactly as before."""
        event = me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        self.assertIsNone(event["note"])

    def test_get_competitor_events_filters_to_only_the_9_competitor_types(self):
        me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        me.record_evidence(
            "n", "competitor_pricing_change",
            {"competitor": "Acme", "source_url": "https://example.com/pricing"}, evidence_path=self.path,
        )
        events = me.get_competitor_events("n", evidence_path=self.path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "competitor_pricing_change")

    def test_summarize_niche_surfaces_competitor_landscape_events_additively(self):
        me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        me.record_evidence(
            "n", "competitor_acquisition",
            {"competitor": "Acme", "source_url": "https://example.com/m-and-a"}, evidence_path=self.path,
        )
        summary = me.summarize_niche("n", evidence_path=self.path)
        # every pre-existing key must still be present, unchanged in shape
        for key in ("willingness_to_pay", "customer_acquisition", "retention",
                    "customer_objections", "pricing_objections", "feature_requests", "lost_opportunities"):
            self.assertIn(key, summary)
        self.assertIn("competitor_landscape_events", summary)
        self.assertEqual(len(summary["competitor_landscape_events"]["competitor_acquisition"]), 1)

    def test_all_9_competitor_types_are_in_event_types(self):
        for event_type in me.COMPETITOR_EVENT_TYPES:
            self.assertIn(event_type, me.EVENT_TYPES)
        self.assertEqual(len(me.COMPETITOR_EVENT_TYPES), 9)


class TestPaymentEvidence(unittest.TestCase):
    """Proof of Payment doctrine (ADR-121, 2026-07-24): the 4 payment-
    evidence event types are the second real exception to this module's
    "never reject" convention -- same reasoning as TestCompetitorEvidence
    above (a claim this factory cannot independently verify requires a
    real, checkable citation), except source_url + quote (not competitor
    name) are what's required."""

    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_payment_evidence_without_source_url_or_quote_is_rejected(self):
        with self.assertRaises(ValueError):
            me.record_evidence("n", "complaining_review", {}, evidence_path=self.path)

    def test_payment_evidence_missing_only_quote_is_rejected(self):
        with self.assertRaises(ValueError):
            me.record_evidence("n", "paid_job_posting", {"source_url": "https://example.com"}, evidence_path=self.path)

    def test_payment_evidence_missing_only_source_url_is_rejected(self):
        with self.assertRaises(ValueError):
            me.record_evidence("n", "freelancer_agency_pricing", {"quote": "$50/hr"}, evidence_path=self.path)

    def test_fully_cited_payment_evidence_is_recorded(self):
        event = me.record_evidence(
            "n", "subscription_escape",
            {"source_url": "https://example.com/complaint", "quote": "cancelling because it's too expensive"},
            evidence_path=self.path,
        )
        self.assertIsNone(event["note"])
        events = me.read_evidence("n", "subscription_escape", evidence_path=self.path)
        self.assertEqual(len(events), 1)

    def test_pre_existing_event_types_are_completely_unaffected(self):
        event = me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        self.assertIsNone(event["note"])

    def test_get_payment_evidence_filters_to_only_the_4_payment_types(self):
        me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        me.record_evidence(
            "n", "complaining_review",
            {"source_url": "https://g2.com/review/123", "quote": "hate paying for this every month"},
            evidence_path=self.path,
        )
        events = me.get_payment_evidence("n", evidence_path=self.path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "complaining_review")

    def test_summarize_niche_surfaces_payment_evidence_additively(self):
        me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        me.record_evidence(
            "n", "paid_job_posting",
            {"source_url": "https://example.com/job/456", "quote": "hiring for manual invoice entry, $20/hr"},
            evidence_path=self.path,
        )
        summary = me.summarize_niche("n", evidence_path=self.path)
        for key in ("willingness_to_pay", "customer_acquisition", "retention",
                    "customer_objections", "pricing_objections", "feature_requests",
                    "lost_opportunities", "competitor_landscape_events"):
            self.assertIn(key, summary)
        self.assertIn("payment_evidence", summary)
        self.assertEqual(len(summary["payment_evidence"]), 1)
        self.assertEqual(summary["payment_evidence"][0]["event_type"], "paid_job_posting")

    def test_all_4_payment_types_are_in_event_types(self):
        for event_type in me.PAYMENT_EVIDENCE_EVENT_TYPES:
            self.assertIn(event_type, me.EVENT_TYPES)
        self.assertEqual(len(me.PAYMENT_EVIDENCE_EVENT_TYPES), 4)


class TestSummarizeNiche(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_empty_niche_is_honestly_empty(self):
        summary = me.summarize_niche("nothing recorded", evidence_path=self.path)
        self.assertEqual(summary["total_events"], 0)
        self.assertIsNone(summary["willingness_to_pay"])
        self.assertIsNone(summary["customer_acquisition"])
        self.assertIsNone(summary["retention"])

    def test_full_real_summary_across_categories(self):
        me.record_evidence("n", "demo_request", {}, evidence_path=self.path)
        me.record_evidence("n", "customer_objection", {"detail": "too complex"}, evidence_path=self.path)
        me.record_evidence("n", "feature_request", {"detail": "wants mobile app"}, evidence_path=self.path)
        summary = me.summarize_niche("n", evidence_path=self.path)
        self.assertEqual(summary["total_events"], 3)
        self.assertEqual(summary["by_type_counts"]["demo_request"], 1)
        self.assertEqual(len(summary["customer_objections"]), 1)
        self.assertEqual(len(summary["feature_requests"]), 1)


if __name__ == "__main__":
    unittest.main()

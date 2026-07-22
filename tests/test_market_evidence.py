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

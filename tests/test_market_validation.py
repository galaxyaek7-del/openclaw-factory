#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for market_validation.py — the Internal Market Validation System
(Founder Directive, 2026-08-14). Pure stdlib unittest, same isolation
discipline as tests/test_market_evidence.py (temp JSONL path, never
touches the real data/ ledger).

    python -m unittest tests.test_market_validation -v
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import market_validation  # noqa: E402


def _valid_payload(**overrides):
    payload = {
        "q1_frequency": "weekly",
        "q2_intent": "maybe",
        "q3_pain": "I waste hours checking whether citations are still good law.",
        "source": "linkedin",
        "professional_role": "Solo attorney",
        "practice_area": "Family law",
        "contact": "lawyer@example.com",
        "session_id": "sess-test-1",
    }
    payload.update(overrides)
    return payload


class ValidationStorageTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(prefix="val_resp_", suffix=".jsonl", delete=False)
        self._tmp.close()
        self._path = self._tmp.name
        self._old_env = os.environ.get("VALIDATION_RESPONSES_PATH")
        os.environ["VALIDATION_RESPONSES_PATH"] = self._path

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("VALIDATION_RESPONSES_PATH", None)
        else:
            os.environ["VALIDATION_RESPONSES_PATH"] = self._old_env
        if os.path.exists(self._path):
            os.remove(self._path)

    def test_record_appends_one_jsonl_row_and_returns_timestamp(self):
        row = market_validation.record_response(_valid_payload())
        self.assertIn("timestamp", row)
        with open(self._path, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 1)
        stored = json.loads(lines[0])
        self.assertEqual(stored["q1_frequency"], "weekly")
        self.assertEqual(stored["source"], "linkedin")

    def test_validate_rejects_bad_q1(self):
        with self.assertRaises(ValueError) as ctx:
            market_validation.record_response(_valid_payload(q1_frequency="always"))
        self.assertIn("q1_frequency", str(ctx.exception))

    def test_validate_rejects_bad_q2(self):
        with self.assertRaises(ValueError) as ctx:
            market_validation.record_response(_valid_payload(q2_intent="definitely"))
        self.assertIn("q2_intent", str(ctx.exception))

    def test_validate_rejects_empty_q3(self):
        with self.assertRaises(ValueError) as ctx:
            market_validation.record_response(_valid_payload(q3_pain="  "))
        self.assertIn("q3_pain", str(ctx.exception))

    def test_validate_rejects_non_dict_payload(self):
        with self.assertRaises(ValueError):
            market_validation.record_response("not an object")

    def test_unknown_source_normalized_to_other(self):
        row = market_validation.record_response(_valid_payload(source="telegram"))
        self.assertEqual(row["source"], "other")

    def test_duplicate_is_rejected_not_doubled(self):
        market_validation.record_response(_valid_payload())
        with self.assertRaises(ValueError) as ctx:
            market_validation.record_response(_valid_payload())
        self.assertIn("duplicate", str(ctx.exception))
        with open(self._path, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 1)

    def test_optional_fields_default_to_empty(self):
        row = market_validation.record_response(_valid_payload(professional_role=None, practice_area="", contact=None, session_id=""))
        self.assertEqual(row["professional_role"], "")
        self.assertEqual(row["practice_area"], "")
        self.assertEqual(row["contact"], "")
        self.assertEqual(row["session_id"], "")

    def test_sample_request_and_waitlist_stored(self):
        row = market_validation.record_response(_valid_payload(sample_request="yes", waitlist="yes"))
        self.assertEqual(row["sample_request"], "yes")
        self.assertEqual(row["waitlist"], "yes")

    def test_rejects_invalid_sample_request(self):
        with self.assertRaises(ValueError) as ctx:
            market_validation.record_response(_valid_payload(sample_request="maybe"))
        self.assertIn("sample_request", str(ctx.exception))

    def test_rejects_invalid_waitlist(self):
        with self.assertRaises(ValueError) as ctx:
            market_validation.record_response(_valid_payload(waitlist="certainly"))
        self.assertIn("waitlist", str(ctx.exception))


class ValidationAggregationTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(prefix="val_resp_", suffix=".jsonl", delete=False)
        self._tmp.close()
        self._path = self._tmp.name
        self._old_env = os.environ.get("VALIDATION_RESPONSES_PATH")
        os.environ["VALIDATION_RESPONSES_PATH"] = self._path
        market_validation.record_response(_valid_payload(
            session_id="a", q1_frequency="several_times_per_week", q2_intent="yes", source="linkedin",
            sample_request="yes", waitlist="yes"))
        market_validation.record_response(_valid_payload(
            session_id="b", q1_frequency="weekly", q2_intent="maybe", source="facebook",
            waitlist="yes"))
        market_validation.record_response(_valid_payload(
            session_id="c", q1_frequency="rarely", q2_intent="no", source="direct",
            professional_role="", practice_area=""))

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("VALIDATION_RESPONSES_PATH", None)
        else:
            os.environ["VALIDATION_RESPONSES_PATH"] = self._old_env
        if os.path.exists(self._path):
            os.remove(self._path)

    def test_aggregate_counts_total_and_qualified(self):
        s = market_validation.aggregate()
        self.assertEqual(s["total_responses"], 3)
        self.assertEqual(s["qualified_responses"], 2)
        self.assertEqual(s["pain_signals"], 3)
        self.assertEqual(s["weekly_or_more_pain"], 2)

    def test_aggregate_intent_counts(self):
        s = market_validation.aggregate()
        self.assertEqual(s["q2_yes"], 1)
        self.assertEqual(s["q2_maybe"], 1)
        self.assertEqual(s["q2_no"], 1)

    def test_aggregate_conversion_rate_is_qualified_yes(self):
        s = market_validation.aggregate()
        self.assertEqual(s["qualified_conversion_rate_pct"], 50.0)

    def test_aggregate_source_breakdown(self):
        s = market_validation.aggregate()
        self.assertEqual(s["source_breakdown"], {"linkedin": 1, "facebook": 1, "direct": 1})

    def test_aggregate_sample_requests_and_waitlist(self):
        s = market_validation.aggregate()
        self.assertEqual(s["sample_requests"], 1)
        self.assertEqual(s["waitlist_signups"], 2)

    def test_aggregate_visits_counts_validation_page_only(self):
        self._views_tmp = tempfile.NamedTemporaryFile(prefix="val_views_", suffix=".jsonl", delete=False)
        self._views_tmp.close()
        self._views_path = self._views_tmp.name
        market_validation.record_visit("linkedin", page_views_path=self._views_path)
        market_validation.record_visit("facebook", page_views_path=self._views_path)
        s = market_validation.aggregate(page_views_path=self._views_path)
        self.assertEqual(s["visits"], 2)
        views = market_validation.read_visits(self._views_path)
        self.assertEqual(len(views), 2)
        self.assertTrue(all(v["page_id"] == market_validation.VALIDATION_PAGE_ID for v in views))
        if os.path.exists(self._views_path):
            os.remove(self._views_path)

    def test_aggregate_never_exposes_pii_or_raw_text(self):
        s = market_validation.aggregate()
        dumped = json.dumps(s)
        self.assertNotIn("lawyer@example.com", dumped)
        self.assertNotIn("I waste hours", dumped)
        self.assertNotIn("contact", dumped)

    def test_aggregate_returns_top_themes_from_real_text(self):
        s = market_validation.aggregate()
        self.assertTrue(any(t["theme"] == "citations" for t in s["top_pain_themes"]))
        self.assertLessEqual(len(s["top_pain_themes"]), 10)

    def test_aggregate_empty_ledger_is_safe(self):
        os.remove(self._path)
        s = market_validation.aggregate()
        self.assertEqual(s["total_responses"], 0)
        self.assertIsNone(s["qualified_conversion_rate_pct"])
        self.assertEqual(s["source_breakdown"], {})
        self.assertEqual(s["top_pain_themes"], [])

    def test_corrupt_line_does_not_break_aggregate(self):
        with open(self._path, "a", encoding="utf-8") as f:
            f.write("{ this is not json\n")
        s = market_validation.aggregate()
        self.assertEqual(s["total_responses"], 3)


if __name__ == "__main__":
    unittest.main()
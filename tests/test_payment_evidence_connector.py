#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the Proof-of-Payment Evidence Connector (ADR-121 extension).

Honesty contract under test: the connector only records REAL, verbatim,
URL-cited currency-marked evidence through market_evidence.record_
evidence()'s own source_url + quote validation — a result with no money
marker, or no real https URL, is SKIPPED, never recorded. All source
queries are patched to fake REAL-shaped API responses; nothing here
touches the real ledger or real cache."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import payment_evidence_connector as PEC


def _gh(text, url="https://github.com/org/repo/issues/1", title=None):
    return {"title": title or f"Issue on {url.split('/')[-1]}", "body": text, "html_url": url}


def _hn(text, url="https://news.ycombinator.com/item?id=1", oid="1"):
    return {"title": text, "story_text": text, "url": url, "objectID": oid}


def _so(text, link="https://stackoverflow.com/questions/1/x"):
    return {"title": text, "link": link}


def _run(niche, gh, hn, so, evidence_path, cache_file):
    with patch("market_intelligence_engine.reformulate_pain_query",
               return_value=("the real problem query", "test_semantic", None)), \
         patch("market_intelligence_engine._query_github_issues", return_value=(gh, len(gh))), \
         patch("market_intelligence_engine._query_hn_discussions", return_value=(hn, len(hn))), \
         patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=(so, len(so))):
        return PEC.collect_payment_evidence(niche, evidence_path=evidence_path, cache_file=cache_file)


class TestRealCurrencyExtraction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.evidence_path = os.path.join(self.tmp, "market_evidence.jsonl")
        self.cache_file = os.path.join(self.tmp, "payment_evidence_cache.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_real_money_quotes_are_extracted_and_recorded_with_source_url_and_quote(self):
        gh = [_gh("Users complain we have to pay $50/hr for manual review") ]
        hn = [_hn("Freelancer priced the cleanup at $200 per month") ]
        so = [_so("Does anyone else find the subscription too expensive at $30/mo?")]
        r = _run("some niche", gh, hn, so, self.evidence_path, self.cache_file)
        self.assertEqual(r["candidates_found"], 3)
        self.assertEqual(len(r["recorded"]), 3)
        for c in r["recorded"]:
            self.assertTrue(c["source_url"].startswith("https://"))
            self.assertTrue(PEC._has_currency_marker(c["quote"]))
        recorded = PEC.ME.get_payment_evidence("some niche", evidence_path=self.evidence_path)
        self.assertEqual(len(recorded), 3)
        for e in recorded:
            self.assertIn("source_url", e["payload"])
            self.assertIn("quote", e["payload"])

    def test_no_currency_marker_means_never_recorded(self):
        gh = [_gh("Users complain about the process being manual")]
        r = _run("some niche", gh, [], [], self.evidence_path, self.cache_file)
        self.assertEqual(r["candidates_found"], 0)
        self.assertEqual(r["recorded"], [])
        self.assertEqual(PEC.ME.get_payment_evidence("some niche", evidence_path=self.evidence_path), [])

    def test_non_https_sources_are_never_recorded(self):
        gh = [_gh("We pay $50/hr for manual review", url="http://github.com/plain-http")]
        r = _run("some niche", gh, [], [], self.evidence_path, self.cache_file)
        self.assertEqual(r["candidates_found"], 0)
        self.assertEqual(r["recorded"], [])

    def test_event_type_classification_is_keyword_gated(self):
        gh = [_gh("We are hiring a contractor at $60/hr to do the cleanup")]
        hn = [_hn("I cancelled the subscription after it hit $80/month")]
        so = [_so("This tool is overpriced at $200/year — total rip-off")]
        r = _run("some niche", gh, hn, so, self.evidence_path, self.cache_file)
        types = {c["event_type"] for c in r["recorded"]}
        self.assertIn("paid_job_posting", types)
        self.assertIn("subscription_escape", types)
        self.assertIn("complaining_review", types)

    def test_plain_money_quote_falls_back_honestly_to_freelancer_agency_pricing(self):
        gh = [_gh("The manual work here costs $75 per project")]
        r = _run("some niche", gh, [], [], self.evidence_path, self.cache_file)
        self.assertEqual(len(r["recorded"]), 1)
        self.assertEqual(r["recorded"][0]["event_type"], "freelancer_agency_pricing")


class TestDedupAndCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.evidence_path = os.path.join(self.tmp, "market_evidence.jsonl")
        self.cache_file = os.path.join(self.tmp, "payment_evidence_cache.json")
        PEC.ME.record_evidence(
            "some niche", "paid_job_posting",
            {"source_url": "https://github.com/org/repo/issues/1", "quote": "already recorded $50/hr"},
            source="test-seed", evidence_path=self.evidence_path,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dedup_skips_source_urls_already_in_the_real_ledger(self):
        gh = [_gh("We pay $50/hr for manual review", url="https://github.com/org/repo/issues/1"),
              _gh("Another team pays $40/hr", url="https://github.com/org/repo/issues/2")]
        r = _run("some niche", gh, [], [], self.evidence_path, self.cache_file)
        urls = [c["source_url"] for c in r["recorded"]]
        self.assertEqual(urls, ["https://github.com/org/repo/issues/2"])
        self.assertNotIn("https://github.com/org/repo/issues/1", urls)

    def test_second_call_is_a_real_cache_hit_with_no_live_search(self):
        gh = [_gh("We pay $50/hr for manual review")]
        r1 = _run("some niche", gh, [], [], self.evidence_path, self.cache_file)
        self.assertFalse(r1["_cache"]["hit"])
        with patch("market_intelligence_engine.reformulate_pain_query") as mock_rq, \
             patch("market_intelligence_engine._query_github_issues") as mock_gh, \
             patch("market_intelligence_engine._query_hn_discussions") as mock_hn, \
             patch("market_intelligence_engine._query_stack_overflow_for_pain") as mock_so:
            r2 = PEC.collect_payment_evidence("some niche", evidence_path=self.evidence_path, cache_file=self.cache_file)
            mock_rq.assert_not_called()
            mock_gh.assert_not_called()
            mock_hn.assert_not_called()
            mock_so.assert_not_called()
        self.assertTrue(r2["_cache"]["hit"])
        self.assertEqual(r2["candidates_found"], r1["candidates_found"])

    def test_force_true_bypasses_cache_and_restores_live_queries(self):
        gh = [_gh("We pay $50/hr for manual review", url="https://github.com/org/repo/issues/10")]
        _run("some niche", gh, [], [], self.evidence_path, self.cache_file)
        gh2 = [_gh("Now it costs $90/hr", url="https://github.com/org/repo/issues/20")]
        with patch("market_intelligence_engine.reformulate_pain_query",
                   return_value=("the real problem query", "test_semantic", None)), \
             patch("market_intelligence_engine._query_github_issues", return_value=(gh2, 1)), \
             patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0)), \
             patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0)):
            r = PEC.collect_payment_evidence("some niche", force=True,
                                             evidence_path=self.evidence_path, cache_file=self.cache_file)
        self.assertFalse(r["_cache"]["hit"])
        self.assertIn("$90/hr", r["recorded"][0]["quote"])

    def test_cache_persists_to_a_real_file_for_future_opportunities(self):
        gh = [_gh("We pay $50/hr for manual review", url="https://github.com/org/repo/issues/30")]
        _run("some niche", gh, [], [], self.evidence_path, self.cache_file)
        self.assertTrue(os.path.exists(self.cache_file))
        with open(self.cache_file, encoding="utf-8") as f:
            db = json.load(f)
        key = PEC.MIE.COMPETITOR_DISCOVERY._normalize_key("some niche")
        self.assertIn(key, db)
        self.assertEqual(db[key]["candidates_found"], 1)


class TestHonestyContract(unittest.TestCase):
    def test_record_false_returns_candidates_without_touching_the_ledger(self):
        tmp = tempfile.mkdtemp()
        try:
            evidence_path = os.path.join(tmp, "market_evidence.jsonl")
            cache_file = os.path.join(tmp, "payment_evidence_cache.json")
            gh = [_gh("We pay $50/hr for manual review")]
            with patch("market_intelligence_engine.reformulate_pain_query",
                       return_value=("q", "test", None)), \
                 patch("market_intelligence_engine._query_github_issues", return_value=(gh, 1)), \
                 patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0)), \
                 patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0)):
                r = PEC.collect_payment_evidence("some niche", record=False,
                                                 evidence_path=evidence_path, cache_file=cache_file)
            self.assertEqual(r["candidates_found"], 1)
            self.assertEqual(r["recorded"], [])
            self.assertFalse(os.path.exists(evidence_path))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
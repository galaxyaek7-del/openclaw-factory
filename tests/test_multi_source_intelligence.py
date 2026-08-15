"""Tests for multi_source_intelligence/ (ADR-059).

Runs with stdlib unittest. Real-network-calling connectors
(hacker_news, github, stack_overflow) are mocked at their underlying
functions throughout — this suite never depends on live API
availability, matching this project's established convention.

    python -m unittest tests.test_multi_source_intelligence -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from multi_source_intelligence import aggregator, coverage, manual_verification, registry
from multi_source_intelligence.types import EVIDENCE_SOURCE_PRIORITY, SOURCES, blocked_result, not_architected_result, unavailable_result


class TestRegistryAutoDiscovery(unittest.TestCase):
    def test_all_fourteen_sources_are_registered(self):
        import multi_source_intelligence.connectors  # noqa: F401
        connectors_map = registry.get_connectors()
        self.assertEqual(len(SOURCES), 14)
        for source in SOURCES:
            self.assertIn(source, connectors_map)

    def test_evidence_source_priority_covers_every_registered_source(self):
        self.assertEqual(set(EVIDENCE_SOURCE_PRIORITY), set(SOURCES))


class TestRealConnectorsWork(unittest.TestCase):
    @patch("competitor_discovery._query_hn", return_value=[{"title": "Show HN: X", "points": 50, "num_comments": 5}])
    def test_hacker_news_connector_reports_real_verified_data(self, mock_hn):
        from multi_source_intelligence.connectors import hacker_news
        result = hacker_news.check("a real hn connector test niche")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(len(result.parsed_data), 1)

    @patch("competitor_discovery._query_hn", side_effect=Exception("network down"))
    def test_hacker_news_connector_degrades_honestly_on_failure(self, mock_hn):
        from multi_source_intelligence.connectors import hacker_news
        result = hacker_news.check("a failure test niche")
        self.assertEqual(result.availability, "unavailable")
        self.assertEqual(result.verification_status, "UNKNOWN")

    @patch("competitor_discovery._query_github", return_value=[{"full_name": "x/y", "stargazers_count": 500, "created_at": "2026-01-01T00:00:00Z"}])
    def test_github_connector_reports_real_verified_data(self, mock_gh):
        from multi_source_intelligence.connectors import github
        result = github.check("a real github connector test niche")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.parsed_data[0]["stars"], 500)

    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[{"title": "a real SO question", "view_count": 100, "answer_count": 2, "score": 5}])
    def test_stack_overflow_connector_reports_real_verified_data(self, mock_so):
        from multi_source_intelligence.connectors import stack_overflow
        result = stack_overflow.check("a real stack overflow connector test niche")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(result.parsed_data[0]["view_count"], 100)

    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", side_effect=Exception("network down"))
    def test_stack_overflow_connector_degrades_honestly_on_failure(self, mock_so):
        from multi_source_intelligence.connectors import stack_overflow
        result = stack_overflow.check("a failure test niche")
        self.assertEqual(result.availability, "unavailable")

    @patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[{"title": "A Real Paper", "summary": "abstract text", "published": "2026-01-01T00:00:00Z", "url": "https://arxiv.org/abs/0000.00000"}])
    def test_arxiv_connector_reports_real_verified_data(self, mock_arxiv):
        from multi_source_intelligence.connectors import arxiv
        result = arxiv.check("a real arxiv connector test niche")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(result.parsed_data[0]["title"], "A Real Paper")

    @patch("multi_source_intelligence.connectors.arxiv._query_arxiv", side_effect=Exception("network down"))
    def test_arxiv_connector_degrades_honestly_on_failure(self, mock_arxiv):
        from multi_source_intelligence.connectors import arxiv
        result = arxiv.check("a failure test niche")
        self.assertEqual(result.availability, "unavailable")
        self.assertEqual(result.verification_status, "UNKNOWN")

    def test_arxiv_connector_parses_real_atom_xml_shape(self):
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <published>2026-01-01T00:00:00Z</published>
    <title>  A Sample Paper Title  </title>
    <summary>  A sample abstract.  </summary>
  </entry>
</feed>"""
        with patch("market_intelligence_core.http_client.http_get_text", return_value=sample_xml):
            from multi_source_intelligence.connectors.arxiv import _query_arxiv
            entries = _query_arxiv("sample niche")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "A Sample Paper Title")
        self.assertEqual(entries[0]["summary"], "A sample abstract.")
        self.assertEqual(entries[0]["url"], "http://arxiv.org/abs/1234.5678v1")


class TestHonestlyUnavailableConnectors(unittest.TestCase):
    def test_product_hunt_is_always_unavailable_with_a_specific_reason(self):
        from multi_source_intelligence.connectors import product_hunt
        result = product_hunt.check("x")
        self.assertEqual(result.availability, "unavailable")
        self.assertEqual(result.confidence, 0)
        self.assertIsNotNone(result.reason)
        self.assertGreater(len(result.reason), 10)

    def test_reddit_is_always_unavailable_with_a_specific_reason(self):
        from multi_source_intelligence.connectors import reddit
        result = reddit.check("x")
        self.assertEqual(result.availability, "unavailable")
        self.assertIsNotNone(result.reason)

    def test_google_trends_is_always_unavailable_with_a_specific_reason(self):
        from multi_source_intelligence.connectors import google_trends
        result = google_trends.check("x")
        self.assertEqual(result.availability, "unavailable")
        self.assertIn("n8n", result.reason)

    def test_public_search_is_always_unavailable_with_a_specific_reason(self):
        from multi_source_intelligence.connectors import public_search
        result = public_search.check("x")
        self.assertEqual(result.availability, "unavailable")

    def test_amazon_connector_reuses_real_market_evidence_and_is_unavailable_without_a_saved_report(self):
        with patch("profit_oracle._find_niche_report", return_value=None):
            from multi_source_intelligence.connectors import amazon
            result = amazon.check("a niche with no saved amazon report")
        self.assertEqual(result.availability, "unavailable")

    def test_amazon_connector_reports_available_with_a_real_saved_report(self):
        fixture = {
            "status": "success", "analyzed_at": "2026-07-01T00:00:00",
            "metrics": {"total_results": 5000, "books_analyzed": 10, "price": {"min": 5, "avg": 9, "max": 15}, "reviews": {"avg": 50, "max": 200}},
        }
        with patch("profit_oracle._find_niche_report", return_value=fixture):
            from multi_source_intelligence.connectors import amazon
            result = amazon.check("a niche with a real saved report")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.verification_status, "VERIFIED")

    def test_gumroad_connector_checks_the_real_arm_status(self):
        from multi_source_intelligence.connectors import gumroad
        result = gumroad.check("x")
        # Real state (updated 2026-08-15): GUMROAD_ACCESS_TOKEN IS set in .env,
        # so the real arm reports available. The connector must mirror the
        # REAL arm status (channel_registry), not a hardcoded belief.
        expected = "available" if gumroad._arm_available() else "unavailable"
        self.assertEqual(result.availability, expected)
        self.assertIn("Gumroad", result.reason)


class TestEvidenceCoverageScore(unittest.TestCase):
    @patch("competitor_discovery._query_hn", return_value=[])
    @patch("competitor_discovery._query_github", return_value=[])
    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[])
    @patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[])
    def test_coverage_score_reports_all_fourteen_sources_checked(self, mock_arxiv, mock_so, mock_gh, mock_hn):
        result = coverage.evidence_coverage_score("a coverage test niche", max_results=3)
        self.assertEqual(len(result["checked"]), 14)
        self.assertEqual(set(result["checked"]), set(SOURCES))

    @patch("competitor_discovery._query_hn", return_value=[{"title": "x", "points": 10, "num_comments": 1}])
    @patch("competitor_discovery._query_github", return_value=[{"full_name": "a/b", "stargazers_count": 10, "created_at": "2026-01-01T00:00:00Z"}])
    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[{"title": "x", "view_count": 1, "answer_count": 1, "score": 1}])
    @patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[{"title": "x", "summary": "y", "published": "2026-01-01T00:00:00Z", "url": "https://arxiv.org/abs/x"}])
    def test_coverage_score_correctly_tallies_succeeded_vs_unknown(self, mock_arxiv, mock_so, mock_gh, mock_hn):
        result = coverage.evidence_coverage_score("a tally test niche", max_results=3)
        self.assertEqual(set(result["succeeded"]), {"hacker_news", "github", "stack_overflow", "arxiv"})
        self.assertEqual(len(result["unknown"]), 10)
        self.assertAlmostEqual(result["coverage_pct"], 28.6, places=1)

    @patch("competitor_discovery._query_github", return_value=[])
    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[])
    @patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[])
    def test_a_connector_raising_an_uncaught_exception_is_tallied_as_failed_not_crashing_the_score(self, mock_arxiv, mock_so, mock_gh):
        with patch.dict(registry._CONNECTORS, {"hacker_news": lambda niche, max_results: (_ for _ in ()).throw(Exception("boom"))}):
            result = coverage.evidence_coverage_score("a raising connector test niche", max_results=3)
        self.assertIn("hacker_news", result["failed"])
        # every other source is still checked -- one source's crash never stops the rest
        self.assertEqual(len(result["checked"]), 14)


class TestBlockedAndNotArchitectedResults(unittest.TestCase):
    """Real Evidence Provider abstraction (ADR-179, 2026-08-06)."""

    def test_blocked_result_shape(self):
        r = blocked_result("stack_overflow", "HTTP 403 rejected the request", status_code=403)
        self.assertEqual(r.verification_status, "BLOCKED")
        self.assertEqual(r.availability, "unavailable")
        self.assertEqual(r.confidence, 0)
        self.assertEqual(r.status_code, 403)

    def test_not_architected_result_shape(self):
        r = not_architected_result("rss_feeds", "no real connector built")
        self.assertEqual(r.verification_status, "NOT_ARCHITECTED")
        self.assertEqual(r.availability, "unavailable")
        self.assertIsNone(r.status_code)

    def test_blocked_is_distinguishable_from_unavailable(self):
        blocked = blocked_result("x", "blocked")
        unavailable = unavailable_result("x", "no credentials")
        self.assertNotEqual(blocked.verification_status, unavailable.verification_status)


class TestHttpClientBlockedDetection(unittest.TestCase):
    def test_403_raises_evidence_source_blocked(self):
        import urllib.error
        from market_intelligence_core import http_client

        def raise_403(*a, **kw):
            raise urllib.error.HTTPError("http://x", 403, "Forbidden", {}, None)

        with patch("urllib.request.urlopen", side_effect=raise_403):
            with self.assertRaises(http_client.EvidenceSourceBlocked) as ctx:
                http_client.http_get_json("http://x")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_404_is_not_treated_as_blocked(self):
        import urllib.error
        from market_intelligence_core import http_client

        def raise_404(*a, **kw):
            raise urllib.error.HTTPError("http://x", 404, "Not Found", {}, None)

        with patch("urllib.request.urlopen", side_effect=raise_404):
            with self.assertRaises(urllib.error.HTTPError):
                http_client.http_get_json("http://x")

    def test_evidence_source_blocked_is_still_a_plain_exception(self):
        """Every pre-existing `except Exception` call site in this
        factory's connectors must keep catching this — zero behavior
        change for any caller that predates ADR-179."""
        from market_intelligence_core import http_client
        self.assertTrue(issubclass(http_client.EvidenceSourceBlocked, Exception))


class TestStackOverflowAndArxivBlockedDetection(unittest.TestCase):
    def test_stack_overflow_reports_blocked_not_generic_unavailable(self):
        from market_intelligence_core import http_client
        from multi_source_intelligence.connectors import stack_overflow
        with patch(
            "multi_source_intelligence.connectors.stack_overflow._query_stack_overflow",
            side_effect=http_client.EvidenceSourceBlocked(403, "http://x"),
        ):
            result = stack_overflow.check("a blocked test niche")
        self.assertEqual(result.verification_status, "BLOCKED")
        self.assertEqual(result.status_code, 403)

    def test_arxiv_reports_blocked_not_generic_unavailable(self):
        from market_intelligence_core import http_client
        from multi_source_intelligence.connectors import arxiv
        with patch(
            "multi_source_intelligence.connectors.arxiv._query_arxiv",
            side_effect=http_client.EvidenceSourceBlocked(429, "http://x"),
        ):
            result = arxiv.check("a blocked test niche")
        self.assertEqual(result.verification_status, "BLOCKED")
        self.assertEqual(result.status_code, 429)


class TestManualVerificationLedger(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self._tmp.close()
        self.ledger_path = self._tmp.name

    def tearDown(self):
        import os
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

    def test_record_and_read_round_trip(self):
        manual_verification.record_verification(
            "a niche", "https://example.com/real-page", "BLOCKED",
            reason="HTTP 403", status_code=403, ledger_path=self.ledger_path,
        )
        attempts = manual_verification.get_verification_attempts("a niche", ledger_path=self.ledger_path)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["status"], "BLOCKED")
        self.assertEqual(attempts[0]["status_code"], 403)

    def test_rejects_a_fabricated_status(self):
        with self.assertRaises(ValueError):
            manual_verification.record_verification("a niche", "https://example.com", "PROBABLY_FINE", ledger_path=self.ledger_path)

    def test_rejects_missing_source_url(self):
        with self.assertRaises(ValueError):
            manual_verification.record_verification("a niche", "", "VERIFIED", ledger_path=self.ledger_path)

    def test_a_different_niche_never_sees_another_niches_attempts(self):
        manual_verification.record_verification("niche a", "https://example.com/a", "BLOCKED", status_code=403, ledger_path=self.ledger_path)
        attempts = manual_verification.get_verification_attempts("niche b", ledger_path=self.ledger_path)
        self.assertEqual(attempts, [])

    def test_no_recorded_attempts_is_honestly_empty(self):
        attempts = manual_verification.get_verification_attempts("a never-checked niche", ledger_path=self.ledger_path)
        self.assertEqual(attempts, [])


class TestWebPagesConnector(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self._tmp.close()
        self.ledger_path = self._tmp.name

    def tearDown(self):
        import os
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

    def test_no_attempt_is_honestly_not_architected(self):
        from multi_source_intelligence.connectors import web_pages
        with patch("multi_source_intelligence.manual_verification.DEFAULT_LEDGER_PATH", self.ledger_path):
            result = web_pages.check("a never-checked web_pages niche")
        self.assertEqual(result.verification_status, "NOT_ARCHITECTED")

    def test_a_real_blocked_attempt_is_reported_as_blocked_never_halts(self):
        from multi_source_intelligence.connectors import web_pages
        manual_verification.record_verification("a blocked web_pages niche", "https://example.com/x", "BLOCKED", status_code=403, ledger_path=self.ledger_path)
        with patch("multi_source_intelligence.manual_verification.DEFAULT_LEDGER_PATH", self.ledger_path):
            result = web_pages.check("a blocked web_pages niche")
        self.assertEqual(result.verification_status, "BLOCKED")
        self.assertEqual(result.status_code, 403)

    def test_a_real_verified_attempt_is_reported_as_verified(self):
        from multi_source_intelligence.connectors import web_pages
        manual_verification.record_verification("a verified web_pages niche", "https://example.com/x", "VERIFIED", quote="real quoted text", ledger_path=self.ledger_path)
        with patch("multi_source_intelligence.manual_verification.DEFAULT_LEDGER_PATH", self.ledger_path):
            result = web_pages.check("a verified web_pages niche")
        self.assertEqual(result.verification_status, "VERIFIED")


class TestPrioritizedEvidenceSummary(unittest.TestCase):
    """Real Evidence Provider abstraction (ADR-179, 2026-08-06) --
    the exact 4-field-per-opportunity shape the founder's directive
    asked for, and the "never terminate evaluation" guarantee."""

    @patch("competitor_discovery._query_hn", return_value=[])
    @patch("competitor_discovery._query_github", return_value=[])
    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[])
    @patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[])
    def test_returns_exactly_the_4_required_fields(self, mock_arxiv, mock_so, mock_gh, mock_hn):
        result = coverage.prioritized_evidence_summary("a 4-field test niche")
        for field in ("confidence", "evidence_count", "verification_status", "missing_evidence"):
            self.assertIn(field, result)

    def test_a_connector_raising_a_brand_new_unforeseen_exception_never_halts_the_others(self):
        with patch.dict(registry._CONNECTORS, {"github": lambda niche, max_results: (_ for _ in ()).throw(RuntimeError("totally unexpected"))}):
            result = coverage.prioritized_evidence_summary("a resilience test niche")
        # every other source was still evaluated -- one unforeseen crash never stops the priority walk
        self.assertEqual(len(result["sources"]), len(EVIDENCE_SOURCE_PRIORITY))
        self.assertIn("github", [m["source"] for m in result["missing_evidence"]])

    @patch("competitor_discovery._query_hn", return_value=[{"title": "x", "points": 10, "num_comments": 1}])
    @patch("competitor_discovery._query_github", return_value=[])
    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[])
    @patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[])
    def test_a_verified_source_raises_confidence_and_evidence_count(self, mock_arxiv, mock_so, mock_gh, mock_hn):
        result = coverage.prioritized_evidence_summary("a verified test niche")
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertGreater(result["confidence"], 0)
        self.assertGreaterEqual(result["evidence_count"], 1)

    def test_a_blocked_source_never_raises_confidence_only_the_status_reflects_it(self):
        # Every source in the registry is deterministically stubbed --
        # exactly one BLOCKED, the rest honestly unavailable -- so this
        # test isolates the one real claim under test (a blocked source
        # alone can never raise confidence) from every other real
        # connector's own live/unmocked behavior.
        blocked = blocked_result("hacker_news", "HTTP 429", status_code=429)
        stub_connectors = {
            source: (lambda niche, max_results, source=source: blocked if source == "hacker_news" else unavailable_result(source, "stub"))
            for source in EVIDENCE_SOURCE_PRIORITY
        }
        with patch.dict(registry._CONNECTORS, stub_connectors, clear=True):
            result = coverage.prioritized_evidence_summary("a blocked-only test niche")
        self.assertEqual(result["confidence"], 0, "a blocked source must never raise confidence")
        self.assertEqual(result["verification_status"], "BLOCKED")
        self.assertIn("hacker_news", result["blocked_sources"])

    def test_missing_evidence_never_includes_a_verified_source(self):
        with patch("competitor_discovery._query_hn", return_value=[{"title": "x", "points": 1, "num_comments": 0}]), \
             patch("competitor_discovery._query_github", return_value=[]), \
             patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[]), \
             patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[]):
            result = coverage.prioritized_evidence_summary("a missing-evidence test niche")
        missing_sources = {m["source"] for m in result["missing_evidence"]}
        self.assertNotIn("hacker_news", missing_sources)


class TestAggregatorIsStandaloneNotWiredIntoScoring(unittest.TestCase):
    def test_accumulate_evidence_returns_coverage_and_per_source_evidence(self):
        with patch("competitor_discovery._query_hn", return_value=[]), \
             patch("competitor_discovery._query_github", return_value=[]), \
             patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[]), \
             patch("multi_source_intelligence.connectors.arxiv._query_arxiv", return_value=[]):
            result = aggregator.accumulate_evidence("a standalone aggregator test niche", max_results=3)
        self.assertIn("coverage", result)
        self.assertIn("evidence_by_source", result)

    def test_module_never_imports_orchestrator_or_decision_engine_scoring(self):
        """Structural guarantee (requirement 7: 'no production logic may
        change'): this package must never import orchestrator.orchestrator
        or profit_oracle's scoring internals — it only produces evidence,
        never consumes it into a decision."""
        import multi_source_intelligence.aggregator as agg_mod
        import multi_source_intelligence.coverage as cov_mod
        for mod in (agg_mod, cov_mod):
            with open(mod.__file__, encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("import orchestrator.orchestrator", content)
            self.assertNotIn("decision_engine.engine", content)


if __name__ == "__main__":
    unittest.main()

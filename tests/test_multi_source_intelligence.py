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

from multi_source_intelligence import aggregator, coverage, registry
from multi_source_intelligence.types import SOURCES, unavailable_result


class TestRegistryAutoDiscovery(unittest.TestCase):
    def test_all_ten_sources_are_registered(self):
        import multi_source_intelligence.connectors  # noqa: F401
        connectors_map = registry.get_connectors()
        for source in SOURCES:
            self.assertIn(source, connectors_map)


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
        # Confirmed real state today: no live GUMROAD_ACCESS_TOKEN in .env
        self.assertEqual(result.availability, "unavailable")
        self.assertIn("Gumroad", result.reason)


class TestEvidenceCoverageScore(unittest.TestCase):
    @patch("competitor_discovery._query_hn", return_value=[])
    @patch("competitor_discovery._query_github", return_value=[])
    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[])
    def test_coverage_score_reports_all_ten_sources_checked(self, mock_so, mock_gh, mock_hn):
        result = coverage.evidence_coverage_score("a coverage test niche", max_results=3)
        self.assertEqual(len(result["checked"]), 10)
        self.assertEqual(set(result["checked"]), set(SOURCES))

    @patch("competitor_discovery._query_hn", return_value=[{"title": "x", "points": 10, "num_comments": 1}])
    @patch("competitor_discovery._query_github", return_value=[{"full_name": "a/b", "stargazers_count": 10, "created_at": "2026-01-01T00:00:00Z"}])
    @patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[{"title": "x", "view_count": 1, "answer_count": 1, "score": 1}])
    def test_coverage_score_correctly_tallies_succeeded_vs_unknown(self, mock_so, mock_gh, mock_hn):
        result = coverage.evidence_coverage_score("a tally test niche", max_results=3)
        self.assertEqual(set(result["succeeded"]), {"hacker_news", "github", "stack_overflow"})
        self.assertEqual(len(result["unknown"]), 7)
        self.assertEqual(result["coverage_pct"], 30.0)

    def test_a_connector_raising_an_uncaught_exception_is_tallied_as_failed_not_crashing_the_score(self):
        with patch.dict(registry._CONNECTORS, {"hacker_news": lambda niche, max_results: (_ for _ in ()).throw(Exception("boom"))}):
            result = coverage.evidence_coverage_score("a raising connector test niche", max_results=3)
        self.assertIn("hacker_news", result["failed"])
        # every other source is still checked -- one source's crash never stops the rest
        self.assertEqual(len(result["checked"]), 10)


class TestAggregatorIsStandaloneNotWiredIntoScoring(unittest.TestCase):
    def test_accumulate_evidence_returns_coverage_and_per_source_evidence(self):
        with patch("competitor_discovery._query_hn", return_value=[]), \
             patch("competitor_discovery._query_github", return_value=[]), \
             patch("multi_source_intelligence.connectors.stack_overflow._query_stack_overflow", return_value=[]):
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

"""Tests for competitor_discovery.py (ADR-042).

Runs with stdlib unittest (see tests/test_base_arm.py). Every test uses
fixture data or temp files — _query_hn()/_query_github() (the only
functions that make real network calls) are mocked throughout, so this
suite never depends on live API availability, matching this project's
general convention of not depending on live network in the automated
suite (see test_gumroad_publisher.py's mocking of HTTP calls).

    python -m unittest tests.test_competitor_discovery -v
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import competitor_discovery as cd


def _iso_days_ago(days, now=None):
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=days)).isoformat()


class TestClassifyCompetitor(unittest.TestCase):
    def test_github_org_with_many_stars_is_enterprise_leader(self):
        hit = {"stargazers_count": 5000, "owner": {"type": "Organization"}, "created_at": _iso_days_ago(1000)}
        category, reason = cd.classify_competitor(hit, "github")
        self.assertEqual(category, "Enterprise Leader")
        self.assertIn("5000", reason)

    def test_github_new_repo_modest_stars_is_emerging_startup(self):
        hit = {"stargazers_count": 50, "owner": {"type": "User"}, "created_at": _iso_days_ago(30)}
        category, reason = cd.classify_competitor(hit, "github")
        self.assertEqual(category, "Emerging Startup")

    def test_github_established_repo_is_direct_competitor(self):
        hit = {"stargazers_count": 800, "owner": {"type": "User"}, "created_at": _iso_days_ago(900)}
        category, reason = cd.classify_competitor(hit, "github")
        self.assertEqual(category, "Direct Competitor")

    def test_github_weak_signal_is_unclassified_not_a_guess(self):
        hit = {"stargazers_count": 3, "owner": {"type": "User"}, "created_at": _iso_days_ago(900)}
        category, reason = cd.classify_competitor(hit, "github")
        self.assertEqual(category, "Unclassified")
        self.assertIn("لا ثقة كافية", reason)

    def test_hn_high_points_is_direct_competitor(self):
        hit = {"points": 150, "num_comments": 40}
        category, reason = cd.classify_competitor(hit, "hacker_news")
        self.assertEqual(category, "Direct Competitor")

    def test_hn_moderate_points_is_alternative_solution(self):
        hit = {"points": 30, "num_comments": 5}
        category, reason = cd.classify_competitor(hit, "hacker_news")
        self.assertEqual(category, "Alternative Solution")

    def test_hn_low_points_is_unclassified_not_a_guess(self):
        hit = {"points": 2, "num_comments": 0}
        category, reason = cd.classify_competitor(hit, "hacker_news")
        self.assertEqual(category, "Unclassified")

    def test_unknown_source_is_unclassified_never_raises(self):
        category, reason = cd.classify_competitor({}, "carrier_pigeon")
        self.assertEqual(category, "Unclassified")


class TestGatherRealMetrics(unittest.TestCase):
    def test_github_metrics_include_only_real_fields_plus_explicit_unknowns(self):
        hit = {
            "stargazers_count": 100, "forks_count": 10, "open_issues_count": 2,
            "updated_at": "2026-07-01T00:00:00Z", "pushed_at": _iso_days_ago(5),
            "created_at": _iso_days_ago(400),
        }
        metrics = cd.gather_real_metrics(hit, "github")
        self.assertEqual(metrics["github_stars"], 100)
        self.assertEqual(metrics["github_forks"], 10)
        self.assertIn("نشط مؤخراً", metrics["development_velocity"])
        # fields with no real GitHub source must say so explicitly, not be silently absent as if computed
        self.assertIn("website_visits", metrics)
        self.assertIn("لا أداة", metrics["website_visits"])
        # fields not applicable to a GitHub-sourced hit are dropped, not marked Unknown-for-it
        self.assertNotIn("reddit_mentions", metrics)
        self.assertNotIn("google_trends", metrics)

    def test_hn_metrics_include_only_real_fields(self):
        hit = {"points": 50, "num_comments": 10, "created_at": "2026-01-01T00:00:00Z"}
        metrics = cd.gather_real_metrics(hit, "hacker_news")
        self.assertEqual(metrics["hacker_news_points"], 50)
        self.assertEqual(metrics["hacker_news_comments"], 10)
        self.assertIn("company_size", metrics)  # still genuinely unknown for HN too

    def test_stale_github_repo_flagged_as_stagnant(self):
        hit = {"created_at": _iso_days_ago(900), "pushed_at": _iso_days_ago(400)}
        metrics = cd.gather_real_metrics(hit, "github")
        self.assertIn("راكد", metrics["development_velocity"])


class TestNetworkFailureHandling(unittest.TestCase):
    """Coverage gap found in self-audit (2026-07-15): _query_hn/_query_github's
    graceful-degradation behavior was only exercised indirectly through
    higher-level tests, unlike market_intelligence_engine.py's equivalent
    fetchers which have direct failure-mode tests. Added for consistency."""

    @patch("competitor_discovery._http_get_json")
    def test_query_hn_never_raises_on_network_failure(self, mock_get):
        mock_get.side_effect = Exception("network down")
        self.assertEqual(cd._query_hn("x"), [])

    @patch("competitor_discovery._http_get_json")
    def test_query_github_never_raises_on_network_failure(self, mock_get):
        mock_get.side_effect = Exception("network down")
        self.assertEqual(cd._query_github("x"), [])


class TestOpportunityGap(unittest.TestCase):
    def test_high_demand_low_competition_is_high_gap(self):
        gap = cd.compute_opportunity_gap(demand_score=90, competition_score=10)
        self.assertGreater(gap, 70)

    def test_low_demand_high_competition_is_low_gap(self):
        gap = cd.compute_opportunity_gap(demand_score=10, competition_score=90)
        self.assertLess(gap, 30)

    def test_never_exceeds_0_100_bounds(self):
        self.assertLessEqual(cd.compute_opportunity_gap(100, 0), 100)
        self.assertGreaterEqual(cd.compute_opportunity_gap(0, 100), 0)


class TestDiscoverCompetitors(unittest.TestCase):
    """discover_competitors() orchestrates _query_hn/_query_github — both
    mocked here so this never makes a real network call."""

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_combines_both_sources_honestly(self, mock_hn, mock_gh):
        mock_hn.return_value = [{"title": "Show HN: X", "points": 200, "num_comments": 50, "url": "https://x.com"}]
        mock_gh.return_value = [{"full_name": "org/y", "stargazers_count": 3000, "owner": {"type": "Organization"}, "created_at": _iso_days_ago(1000)}]
        result = cd.discover_competitors("test niche")
        self.assertEqual(result["total_found"], 2)
        self.assertIn("Direct Competitor", result["by_category"])
        self.assertIn("Enterprise Leader", result["by_category"])

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_both_sources_down_returns_empty_not_an_error(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        result = cd.discover_competitors("test niche")
        self.assertEqual(result["total_found"], 0)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_market_saturation_and_barrier_are_explicit_unknown(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        result = cd.discover_competitors("test niche")
        self.assertIn("Unknown", result["market_saturation"])
        self.assertIn("Unknown", result["barrier_to_entry"])
        self.assertIn("Unknown", result["pricing_power"])

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_is_open_source_is_a_real_fact_from_the_api_source_not_a_guess(self, mock_hn, mock_gh):
        """Live Competitive Intelligence Layer (2026-07-23): GitHub-sourced
        hits are real, 100%-verifiable open-source substitutes; HN-sourced
        hits are not tagged as open source just because they got upvoted."""
        mock_hn.return_value = [{"title": "Show HN: X", "points": 200, "num_comments": 50, "url": "https://x.com"}]
        mock_gh.return_value = [{"full_name": "org/y", "stargazers_count": 3000, "owner": {"type": "Organization"}, "created_at": _iso_days_ago(1000)}]
        result = cd.discover_competitors("test niche")
        by_source = {c["source"]: c["is_open_source"] for c in result["competitors"]}
        self.assertTrue(by_source["github"])
        self.assertFalse(by_source["hacker_news"])


class TestCompetitorDatabase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.db_path)
        fd, self.history_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.history_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.history_path):
            os.remove(self.history_path)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_first_call_performs_a_real_search_and_stores_it(self, mock_hn, mock_gh):
        mock_hn.return_value = [{"title": "a", "points": 5, "num_comments": 0}]
        mock_gh.return_value = []
        result = cd.get_or_refresh_competitors("niche a", db_file=self.db_path)
        self.assertFalse(result["_cache"]["hit"])
        self.assertTrue(os.path.exists(self.db_path))
        self.assertEqual(mock_hn.call_count, 1)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_second_call_within_freshness_window_hits_cache_no_new_search(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path)
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path)
        self.assertEqual(mock_hn.call_count, 1, "second call must not re-query — this is the whole point of the cache")

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_stale_entry_triggers_a_real_refresh(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        db = {cd._normalize_key("niche a"): {"discovered_at": _iso_days_ago(30), "competitors": []}}
        cd.save_database(db, db_file=self.db_path)
        result = cd.get_or_refresh_competitors("niche a", max_age_days=7, db_file=self.db_path, history_file=self.history_path)
        self.assertFalse(result["_cache"]["hit"])
        self.assertEqual(mock_hn.call_count, 1)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_force_always_refreshes_even_if_fresh(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path, force=True)
        self.assertEqual(mock_hn.call_count, 2)

    def test_load_database_missing_file_returns_empty_dict_never_throws(self):
        self.assertEqual(cd.load_database(db_file="/no/such/file.json"), {})

    def test_load_database_malformed_json_returns_empty_dict_never_throws(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        self.assertEqual(cd.load_database(db_file=self.db_path), {})

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_first_ever_discovery_has_no_history_to_diff_against(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        result = cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        self.assertFalse(result["changes"]["has_history"])
        self.assertFalse(os.path.exists(self.history_path), "nothing existed yet to preserve — no history write should happen")

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_a_real_refresh_preserves_the_outgoing_snapshot_in_history(self, mock_hn, mock_gh):
        mock_hn.return_value = [{"title": "a", "points": 5, "num_comments": 0}]
        mock_gh.return_value = []
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path, force=True)
        self.assertTrue(os.path.exists(self.history_path))
        with open(self.history_path, encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 1, "exactly one prior snapshot should have been preserved")

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_a_real_new_competitor_is_detected_on_the_second_refresh(self, mock_hn, mock_gh):
        mock_gh.return_value = []
        mock_hn.return_value = [{"title": "first competitor", "points": 5, "num_comments": 0}]
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        mock_hn.return_value = [
            {"title": "first competitor", "points": 5, "num_comments": 0},
            {"title": "a brand new competitor", "points": 8, "num_comments": 1},
        ]
        result = cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path, force=True)
        self.assertTrue(result["changes"]["has_history"])
        new_names = [c["name"] for c in result["changes"]["new_competitors"]]
        self.assertEqual(new_names, ["a brand new competitor"])

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_a_failed_history_write_never_blocks_the_real_refresh(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        # An impossible path (a file where a directory is expected) makes
        # the append fail — the real refresh itself must still succeed.
        bad_history_path = os.path.join(self.db_path, "impossible", "history.jsonl")
        result = cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=bad_history_path, force=True)
        self.assertFalse(result["_cache"]["hit"])


class TestDiffCompetitorSnapshots(unittest.TestCase):
    """Pure function, no I/O — real comparison logic between two
    real, previously-computed snapshots."""

    def test_no_prior_snapshot_is_honestly_reported_not_a_fabricated_trend(self):
        result = cd.diff_competitor_snapshots(None, {"competitors": []})
        self.assertFalse(result["has_history"])
        self.assertEqual(result["new_competitors"], [])

    def test_a_real_new_competitor_is_detected(self):
        old = {"competitors": [{"name": "a", "metrics": {}}]}
        new = {"competitors": [{"name": "a", "metrics": {}}, {"name": "b", "metrics": {}}]}
        result = cd.diff_competitor_snapshots(old, new)
        self.assertEqual([c["name"] for c in result["new_competitors"]], ["b"])
        self.assertEqual(result["disappeared_competitors"], [])

    def test_a_real_disappeared_competitor_is_detected(self):
        old = {"competitors": [{"name": "a", "metrics": {}}, {"name": "b", "metrics": {}}]}
        new = {"competitors": [{"name": "a", "metrics": {}}]}
        result = cd.diff_competitor_snapshots(old, new)
        self.assertEqual(result["new_competitors"], [])
        self.assertEqual([c["name"] for c in result["disappeared_competitors"]], ["b"])

    def test_real_growth_in_stars_is_detected(self):
        old = {"competitors": [{"name": "a", "metrics": {"github_stars": 100}}]}
        new = {"competitors": [{"name": "a", "metrics": {"github_stars": 250}}]}
        result = cd.diff_competitor_snapshots(old, new)
        self.assertEqual(len(result["growth_signals"]), 1)
        self.assertEqual(result["growth_signals"][0]["from"], 100)
        self.assertEqual(result["growth_signals"][0]["to"], 250)

    def test_a_decline_in_stars_is_never_reported_as_growth(self):
        old = {"competitors": [{"name": "a", "metrics": {"github_stars": 250}}]}
        new = {"competitors": [{"name": "a", "metrics": {"github_stars": 100}}]}
        result = cd.diff_competitor_snapshots(old, new)
        self.assertEqual(result["growth_signals"], [])

    def test_unknown_metrics_never_fabricate_a_growth_signal(self):
        old = {"competitors": [{"name": "a", "metrics": {"github_stars": None}}]}
        new = {"competitors": [{"name": "a", "metrics": {"github_stars": None}}]}
        result = cd.diff_competitor_snapshots(old, new)
        self.assertEqual(result["growth_signals"], [])


if __name__ == "__main__":
    unittest.main()

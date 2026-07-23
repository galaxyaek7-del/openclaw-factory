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


class TestThreatAssessment(unittest.TestCase):
    """Threat Engine (Live Competitive Intelligence Layer, 2026-07-23):
    pure functions over already-computed real snapshot data — no I/O, no
    network. 3 dimensions are real; the other 5 requested dimensions must
    always come back as an explicit, reasoned Unknown, never a number."""

    def test_all_8_dimensions_present_and_5_are_explicit_unknown(self):
        result = cd.compute_threat_assessment({"total_found": 0, "competitors": []})
        expected_unknown = {
            "funding_pressure", "pricing_pressure", "technology_disruption",
            "regulatory_threat", "talent_competition",
        }
        for dim in expected_unknown:
            self.assertEqual(result[dim]["level"], "Unknown")
            self.assertIsNone(result[dim]["score"])
            self.assertTrue(result[dim]["basis"], f"{dim} must state a real reason, not just say Unknown")
        for dim in ("competitor_saturation", "market_concentration", "new_entrant_trajectory"):
            self.assertIn(dim, result)
        # this empty fixture has no competitors/history, so saturation is the
        # only one of the 3 real dimensions with a non-Unknown answer here —
        # concentration/trajectory correctly stay Unknown too, just for a
        # different, real reason (no popularity metric / no history yet)
        self.assertNotEqual(result["competitor_saturation"]["level"], "Unknown")

    def test_saturation_scales_with_real_competitor_count(self):
        self.assertEqual(cd._score_competitor_saturation({"total_found": 0})["level"], "لا تشبع ملحوظ")
        self.assertEqual(cd._score_competitor_saturation({"total_found": 1})["score"], 25)
        self.assertEqual(cd._score_competitor_saturation({"total_found": 4})["score"], 50)
        self.assertEqual(cd._score_competitor_saturation({"total_found": 8})["score"], 75)
        self.assertEqual(cd._score_competitor_saturation({"total_found": 12})["score"], 100)

    def test_concentration_is_unknown_with_no_real_popularity_metric(self):
        snapshot = {"competitors": [{"name": "a", "metrics": {}}, {"name": "b", "metrics": {}}]}
        result = cd._score_market_concentration(snapshot)
        self.assertEqual(result["level"], "Unknown")
        self.assertIsNone(result["score"])

    def test_concentration_is_low_when_evenly_distributed(self):
        snapshot = {"competitors": [
            {"name": f"c{i}", "metrics": {"github_stars": 100}} for i in range(10)
        ]}
        result = cd._score_market_concentration(snapshot)
        self.assertIn("غير مركّز", result["level"])

    def test_concentration_is_high_when_one_competitor_dominates(self):
        snapshot = {"competitors": [
            {"name": "a", "metrics": {"github_stars": 9900}},
            {"name": "b", "metrics": {"github_stars": 50}},
            {"name": "c", "metrics": {"github_stars": 50}},
        ]}
        result = cd._score_market_concentration(snapshot)
        self.assertIn("تركّز عالٍ", result["level"])

    def test_new_entrant_trajectory_unknown_without_real_history(self):
        result = cd._score_new_entrant_trajectory({"total_found": 3})
        self.assertEqual(result["level"], "Unknown")
        self.assertIsNone(result["score"])

    def test_new_entrant_trajectory_unknown_on_first_ever_discovery(self):
        snapshot = {"changes": {"has_history": False}}
        result = cd._score_new_entrant_trajectory(snapshot)
        self.assertEqual(result["level"], "Unknown")

    def test_new_entrant_trajectory_rising_when_more_new_than_gone(self):
        snapshot = {"changes": {
            "has_history": True, "new_competitors": [{"name": "x"}, {"name": "y"}],
            "disappeared_competitors": [], "growth_signals": [], "previous_discovered_at": "2026-07-01",
        }}
        result = cd._score_new_entrant_trajectory(snapshot)
        self.assertIn("تصاعدي", result["level"])
        self.assertEqual(result["score"], 2)

    def test_new_entrant_trajectory_declining_when_more_gone_than_new(self):
        snapshot = {"changes": {
            "has_history": True, "new_competitors": [], "disappeared_competitors": [{"name": "x"}, {"name": "y"}],
            "growth_signals": [], "previous_discovered_at": "2026-07-01",
        }}
        result = cd._score_new_entrant_trajectory(snapshot)
        self.assertIn("تراجعي", result["level"])
        self.assertEqual(result["score"], -2)

    def test_new_entrant_trajectory_stable_when_net_zero(self):
        snapshot = {"changes": {
            "has_history": True, "new_competitors": [{"name": "x"}], "disappeared_competitors": [{"name": "y"}],
            "growth_signals": [], "previous_discovered_at": "2026-07-01",
        }}
        result = cd._score_new_entrant_trajectory(snapshot)
        self.assertEqual(result["level"], "مستقر")
        self.assertEqual(result["score"], 0)


class TestGetOrRefreshCompetitorsAttachesThreatAssessment(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.db_path)
        fd, self.history_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.history_path)

    def tearDown(self):
        for p in (self.db_path, self.history_path):
            if os.path.exists(p):
                os.remove(p)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_fresh_refresh_carries_a_real_threat_assessment(self, mock_hn, mock_gh):
        mock_hn.return_value = [{"title": "a", "points": 5, "num_comments": 0}]
        mock_gh.return_value = []
        result = cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        self.assertIn("threat_assessment", result)
        self.assertIn("competitor_saturation", result["threat_assessment"])

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    def test_cache_hit_also_carries_a_real_threat_assessment(self, mock_hn, mock_gh):
        mock_hn.return_value = []
        mock_gh.return_value = []
        cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        result = cd.get_or_refresh_competitors("niche a", db_file=self.db_path, history_file=self.history_path)
        self.assertTrue(result["_cache"]["hit"])
        self.assertIn("threat_assessment", result)


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

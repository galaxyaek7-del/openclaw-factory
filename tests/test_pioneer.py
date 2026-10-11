"""Tests for golden_hunter/pioneer.py (Strategic Phase, 2026-07-19): real
discovery upstream of Golden Hunter's existing scoring.

Every network call is mocked except TestRealHackerNewsIntegration,
which deliberately makes the one real, free, keyless HN Firebase call
this factory's own established convention allows for a genuine
connectivity proof (same discipline as
tests/test_product_package.py::TestCliDispatchAutoFillsSectionsForTechdoc).

    python -m unittest tests.test_pioneer -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from golden_hunter import pioneer


class TestDiscoverCandidates(unittest.TestCase):
    def test_real_titles_become_candidates_ranked_by_signal_then_points(self):
        with patch.object(pioneer, "_fetch_story_ids_with_status", return_value=([1, 2, 3], "OK")), \
             patch.object(pioneer, "_fetch_item", side_effect=[
                 {"title": "Some AI news article", "score": 900, "url": "http://a"},
                 {"title": "Show HN: I built a real tool", "score": 50, "url": "http://b"},
                 {"title": "Another news story", "score": 100, "url": "http://c"},
             ]):
            candidates = pioneer.discover_candidates(limit=10, scan_pool=3)

        # Signal-matched candidate ranked first despite lower points.
        self.assertEqual(candidates[0]["niche"], "Show HN: I built a real tool")
        self.assertTrue(candidates[0]["signal_matched"])
        self.assertEqual(candidates[0]["source"], "hacker_news_top_stories")

    def test_limit_is_respected(self):
        with patch.object(pioneer, "_fetch_story_ids_with_status", return_value=([1, 2, 3, 4, 5], "OK")), \
             patch.object(pioneer, "_fetch_item", side_effect=[
                 {"title": f"story {i}", "score": i, "url": f"http://{i}"} for i in range(5)
             ]):
            candidates = pioneer.discover_candidates(limit=2, scan_pool=5)
        self.assertEqual(len(candidates), 2)

    def test_items_with_no_title_are_skipped_never_fabricated(self):
        with patch.object(pioneer, "_fetch_story_ids_with_status", return_value=([1, 2], "OK")), \
             patch.object(pioneer, "_fetch_item", side_effect=[
                 {"score": 10},  # no title -- e.g. a real HN poll/job item shape
                 {"title": "a real story", "score": 5},
             ]):
            candidates = pioneer.discover_candidates(limit=10, scan_pool=2)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["niche"], "a real story")

    def test_a_missing_item_never_crashes(self):
        with patch.object(pioneer, "_fetch_story_ids_with_status", return_value=([1, 2], "OK")), \
             patch.object(pioneer, "_fetch_item", side_effect=[None, {"title": "ok", "score": 1}]):
            candidates = pioneer.discover_candidates(limit=10, scan_pool=2)
        self.assertEqual(len(candidates), 1)

    def test_network_failure_returns_honestly_empty_never_fabricates(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", side_effect=RuntimeError("down")):
            candidates = pioneer.discover_candidates(limit=10)
        self.assertEqual(candidates, [])

    def test_network_failure_is_tagged_unknown_not_a_guessed_empty(self):
        """Cycle 76 section 1: a genuine fetch failure must be
        distinguishable from a real, honest zero-result day -- never
        silently collapsed into the same bare empty list with no signal."""
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", side_effect=RuntimeError("down")):
            candidates, status = pioneer.discover_candidates_with_status(limit=10)
        self.assertEqual(candidates, [])
        self.assertTrue(status.startswith("UNKNOWN"))


class TestFetchHelpers(unittest.TestCase):
    def test_fetch_top_story_ids_network_failure_returns_empty(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", side_effect=RuntimeError("down")):
            self.assertEqual(pioneer._fetch_top_story_ids(10), [])

    def test_fetch_top_story_ids_non_list_response_returns_empty(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", return_value={"unexpected": "shape"}):
            self.assertEqual(pioneer._fetch_top_story_ids(10), [])

    def test_fetch_item_network_failure_returns_none(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", side_effect=RuntimeError("down")):
            self.assertIsNone(pioneer._fetch_item(123))


class TestDiscoverHnFeed(unittest.TestCase):
    """The shared HN feed builder (used for Ask HN / Show HN) follows the
    same honesty discipline as discover_candidates: real titles only,
    signal matches ranked first, empty on failure — never fabricated."""

    def test_ask_hn_feed_ranks_signal_matches_first(self):
        with patch.object(pioneer, "_fetch_story_ids_with_status", return_value=([1, 2], "OK")), \
             patch.object(pioneer, "_fetch_item", side_effect=[
                 {"title": "Ask HN: How do you handle contract renewal tracking?", "score": 40, "url": "http://a"},
                 {"title": "Some general tech discussion", "score": 900, "url": "http://b"},
             ]):
            candidates = pioneer._discover_hn_feed(
                pioneer.HN_ASK_STORIES_URL, "hacker_news_ask_hn", limit=10, scan_pool=2)
        self.assertEqual(candidates[0]["niche"], "Ask HN: How do you handle contract renewal tracking?")
        self.assertEqual(candidates[0]["source"], "hacker_news_ask_hn")
        self.assertTrue(candidates[0]["signal_matched"])

    def test_ask_hn_network_failure_returns_empty(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", side_effect=RuntimeError("down")):
            candidates = pioneer._discover_hn_feed(
                pioneer.HN_ASK_STORIES_URL, "hacker_news_ask_hn", limit=10, scan_pool=2)
        self.assertEqual(candidates, [])

    def test_ask_hn_network_failure_is_tagged_unknown(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", side_effect=RuntimeError("down")):
            candidates, status = pioneer._discover_hn_feed_with_status(
                pioneer.HN_ASK_STORIES_URL, "hacker_news_ask_hn", limit=10, scan_pool=2)
        self.assertEqual(candidates, [])
        self.assertTrue(status.startswith("UNKNOWN"))


class TestDiscoverGithubRecentRepos(unittest.TestCase):
    def test_real_github_shape_becomes_candidates(self):
        fake = {"items": [
            {"full_name": "acme/agent-toolkit", "description": "open source agent toolkit for startups",
             "html_url": "http://gh/acme/agent-toolkit", "stargazers_count": 1200,
             "language": "Python", "created_at": "2026-08-01T00:00:00Z"},
            {"full_name": "nobody/blog", "description": "my personal blog",
             "html_url": "http://gh/nobody/blog", "stargazers_count": 2,
             "language": "HTML", "created_at": "2026-08-02T00:00:00Z"},
        ]}
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", return_value=fake):
            candidates = pioneer.discover_github_recent_repos(limit=5, days=30)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["source"], "github_recent_repos")
        self.assertTrue(candidates[0]["signal_matched"])  # "agent" keyword hit
        self.assertEqual(candidates[0]["stars"], 1200)
        self.assertIn("stars", candidates[0])
        self.assertIn("language", candidates[0])

    def test_github_network_failure_returns_empty(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", side_effect=RuntimeError("rate limited")):
            self.assertEqual(pioneer.discover_github_recent_repos(limit=5), [])

    def test_github_non_dict_response_returns_empty(self):
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", return_value=["not", "a", "dict"]):
            self.assertEqual(pioneer.discover_github_recent_repos(limit=5), [])

    def test_github_items_without_names_are_skipped(self):
        fake = {"items": [{"stargazers_count": 5}, {"full_name": "ok/repo", "stargazers_count": 3}]}
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", return_value=fake):
            candidates = pioneer.discover_github_recent_repos(limit=5)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["niche"], "ok/repo")


class TestDiscoverAll(unittest.TestCase):
    def test_discover_all_merges_sources_and_dedupes(self):
        with patch.object(pioneer, "_discover_hn_feed", side_effect=[
                [{"niche": "Ask HN: real pain question", "source": "hacker_news_ask_hn",
                  "points": 10, "signal_matched": True}],
                [{"niche": "Show HN: I built a tool", "source": "hacker_news_show_hn",
                  "points": 5, "signal_matched": True}],
            ]), \
             patch.object(pioneer, "discover_github_recent_repos", return_value=[
                 {"niche": "gh/agent-toolkit: build agents", "source": "github_recent_repos",
                  "points": 1200, "signal_matched": True},
             ]), \
             patch.object(pioneer, "discover_candidates", return_value=[
                 {"niche": "Ask HN: real pain question", "source": "hacker_news_top_stories",
                  "points": 99, "signal_matched": True},
                 {"niche": "a top story", "source": "hacker_news_top_stories",
                  "points": 50, "signal_matched": False},
             ]):
            merged = pioneer.discover_all(limit_per_source=10, scan_pool=5)

        niches = [c["niche"] for c in merged]
        # The dedupe keeps the HIGHEST-point occurrence of the duplicate.
        self.assertEqual(niches.count("Ask HN: real pain question"), 1)
        dup = [c for c in merged if c["niche"] == "Ask HN: real pain question"][0]
        self.assertEqual(dup["points"], 99)
        self.assertIn("Show HN: I built a tool", niches)
        self.assertIn("gh/agent-toolkit: build agents", niches)
        self.assertIn("a top story", niches)

    def test_discover_all_each_source_failure_never_blocks_others(self):
        with patch.object(pioneer, "_discover_hn_feed", return_value=[]), \
             patch.object(pioneer, "discover_github_recent_repos", return_value=[]), \
             patch.object(pioneer, "discover_candidates", return_value=[]):
            merged = pioneer.discover_all()
        self.assertEqual(merged, [])


class TestRealHackerNewsIntegration(unittest.TestCase):
    """Deliberately real: one live, free, keyless call to HN's Firebase
    API, proving Pioneer is genuinely connected to a real, current data
    source — not just a mocked shape. Read-only, zero cost, zero side
    effects on anything this factory owns.

    Cycle 77 section 2: the test suite blocks real network access by
    default (tests/network_guard.py) -- this is the one documented
    exception, opted into explicitly at the call site via
    allow_network(), not via a global flag."""

    def test_a_real_call_returns_real_current_candidates(self):
        from network_guard import allow_network
        with allow_network():
            candidates = pioneer.discover_candidates(limit=3, scan_pool=10)
        self.assertGreater(len(candidates), 0, "HN's real API should return at least one real current story")
        for c in candidates:
            self.assertTrue(c["niche"])
            self.assertEqual(c["source"], "hacker_news_top_stories")
            self.assertIn("signal_matched", c)


class TestEveryCandidateCarriesSourceUrlAndFetchedAt(unittest.TestCase):
    """Cycle 76 section 1, hard requirement: 'كل مرشح يحمل: source_url
    وfetched_at والبيانات الخام' -- every real candidate from every real
    source must fail this test if either field is missing or empty."""

    def _assert_candidate_shape(self, candidates):
        self.assertTrue(candidates, "fixture produced no candidates to check")
        for c in candidates:
            self.assertIn("source_url", c)
            self.assertTrue(c["source_url"], "source_url must not be empty")
            self.assertIn("fetched_at", c)
            self.assertTrue(c["fetched_at"], "fetched_at must not be empty")
            self.assertIn("raw", c, "raw fetched data must be preserved for audit")

    def test_discover_candidates_shape(self):
        with patch.object(pioneer, "_fetch_story_ids_with_status", return_value=([1], "OK")), \
             patch.object(pioneer, "_fetch_item", return_value={"title": "t", "score": 1, "url": "http://x"}):
            self._assert_candidate_shape(pioneer.discover_candidates(limit=1, scan_pool=1))

    def test_discover_hn_feed_shape(self):
        with patch.object(pioneer, "_fetch_story_ids_with_status", return_value=([1], "OK")), \
             patch.object(pioneer, "_fetch_item", return_value={"title": "t", "score": 1, "url": "http://x"}):
            self._assert_candidate_shape(pioneer._discover_hn_feed(
                pioneer.HN_ASK_STORIES_URL, "hacker_news_ask_hn", limit=1, scan_pool=1))

    def test_discover_github_recent_repos_shape(self):
        fake = {"items": [{"full_name": "a/b", "html_url": "http://gh/a/b", "stargazers_count": 1}]}
        with patch.object(pioneer.MIC_HTTP_CLIENT, "http_get_json", return_value=fake):
            self._assert_candidate_shape(pioneer.discover_github_recent_repos(limit=1))

    def test_a_candidate_missing_source_url_fails_this_check(self):
        """Proves the check itself is real -- a candidate stripped of
        source_url must fail, not silently pass."""
        with self.assertRaises(AssertionError):
            self._assert_candidate_shape([{"niche": "x", "fetched_at": "2026-01-01", "raw": {}}])

    def test_a_candidate_missing_fetched_at_fails_this_check(self):
        with self.assertRaises(AssertionError):
            self._assert_candidate_shape([{"niche": "x", "source_url": "http://x", "raw": {}}])


if __name__ == "__main__":
    unittest.main()

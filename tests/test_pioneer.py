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
        with patch.object(pioneer, "_fetch_top_story_ids", return_value=[1, 2, 3]), \
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
        with patch.object(pioneer, "_fetch_top_story_ids", return_value=[1, 2, 3, 4, 5]), \
             patch.object(pioneer, "_fetch_item", side_effect=[
                 {"title": f"story {i}", "score": i, "url": f"http://{i}"} for i in range(5)
             ]):
            candidates = pioneer.discover_candidates(limit=2, scan_pool=5)
        self.assertEqual(len(candidates), 2)

    def test_items_with_no_title_are_skipped_never_fabricated(self):
        with patch.object(pioneer, "_fetch_top_story_ids", return_value=[1, 2]), \
             patch.object(pioneer, "_fetch_item", side_effect=[
                 {"score": 10},  # no title -- e.g. a real HN poll/job item shape
                 {"title": "a real story", "score": 5},
             ]):
            candidates = pioneer.discover_candidates(limit=10, scan_pool=2)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["niche"], "a real story")

    def test_a_missing_item_never_crashes(self):
        with patch.object(pioneer, "_fetch_top_story_ids", return_value=[1, 2]), \
             patch.object(pioneer, "_fetch_item", side_effect=[None, {"title": "ok", "score": 1}]):
            candidates = pioneer.discover_candidates(limit=10, scan_pool=2)
        self.assertEqual(len(candidates), 1)

    def test_network_failure_returns_honestly_empty_never_fabricates(self):
        with patch.object(pioneer, "_fetch_top_story_ids", return_value=[]):
            candidates = pioneer.discover_candidates(limit=10)
        self.assertEqual(candidates, [])


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


class TestRealHackerNewsIntegration(unittest.TestCase):
    """Deliberately real: one live, free, keyless call to HN's Firebase
    API, proving Pioneer is genuinely connected to a real, current data
    source — not just a mocked shape. Read-only, zero cost, zero side
    effects on anything this factory owns."""

    def test_a_real_call_returns_real_current_candidates(self):
        candidates = pioneer.discover_candidates(limit=3, scan_pool=10)
        self.assertGreater(len(candidates), 0, "HN's real API should return at least one real current story")
        for c in candidates:
            self.assertTrue(c["niche"])
            self.assertEqual(c["source"], "hacker_news_top_stories")
            self.assertIn("signal_matched", c)


if __name__ == "__main__":
    unittest.main()

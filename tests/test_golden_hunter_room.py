import unittest
from unittest.mock import patch

import golden_hunter_room as ghr

_FAKE_RANKING = {
    "build_next": [
        {
            "niche": "high roi candidate", "prior_status": "DEFERRED",
            "confidence_score": "high", "evidence_sources": ["a", "b"],
            "expected_roi": {"value": 90}, "competition_score": {"value": 30},
            "difficulty": {"value": 20}, "reject_recommended": False,
        },
        {
            "niche": "reject candidate", "prior_status": "REJECTED",
            "confidence_score": "low", "evidence_sources": [],
            "expected_roi": {"value": 10}, "competition_score": {"value": 90},
            "difficulty": {"value": None}, "reject_recommended": True,
        },
        {
            "niche": "accepted candidate", "prior_status": "ACCEPTED",
            "confidence_score": "high", "evidence_sources": ["c"],
            "expected_roi": {"value": 60}, "competition_score": {"value": 40},
            "difficulty": {"value": 50}, "reject_recommended": False,
        },
    ]
}


class TestGoldenHunterRoom(unittest.TestCase):
    def test_room_entry_never_fabricates_dollar_revenue(self):
        with patch("goos.rank_build_candidates", return_value=_FAKE_RANKING):
            room = ghr.build_golden_hunter_room()
            for entry in room["top_opportunities"]:
                self.assertIn("NOT_MEASURABLE", entry["expected_revenue"])
                self.assertIn("NOT_MEASURABLE", entry["market_size"])

    def test_reject_recommended_maps_to_reject_priority(self):
        with patch("goos.rank_build_candidates", return_value=_FAKE_RANKING):
            room = ghr.build_golden_hunter_room()
            rejected = [e for e in room["top_opportunities"] if e["opportunity"] == "reject candidate"]
            self.assertEqual(rejected[0]["priority"], "reject")

    def test_next_action_for_accepted_is_proceed_to_production(self):
        entry = ghr._recommended_next_action({"prior_status": "ACCEPTED", "reject_recommended": False})
        self.assertIn("Proceed to production", entry)

    def test_next_action_for_deferred_asks_for_new_evidence(self):
        entry = ghr._recommended_next_action({"prior_status": "DEFERRED", "reject_recommended": False})
        self.assertIn("new evidence", entry)

    def test_next_action_reject_recommended_overrides_status(self):
        entry = ghr._recommended_next_action({"prior_status": "ACCEPTED", "reject_recommended": True})
        self.assertIn("Do not pursue", entry)

    def test_ceo_view_best_and_second_exclude_reject_candidates(self):
        with patch("goos.rank_build_candidates", return_value=_FAKE_RANKING):
            view = ghr.ceo_view()
            self.assertNotEqual(view["best_opportunity_today"]["opportunity"], "reject candidate")
            self.assertNotEqual(view["second_best_opportunity"]["opportunity"], "reject candidate")

    def test_ceo_view_should_be_ignored_contains_reject_only(self):
        with patch("goos.rank_build_candidates", return_value=_FAKE_RANKING):
            view = ghr.ceo_view()
            self.assertEqual(len(view["should_be_ignored"]), 1)
            self.assertEqual(view["should_be_ignored"][0]["opportunity"], "reject candidate")

    def test_ceo_view_highest_long_term_potential_never_a_dollar_figure(self):
        with patch("goos.rank_build_candidates", return_value=_FAKE_RANKING):
            view = ghr.ceo_view()
            self.assertIn("never a literal dollar projection", view["highest_long_term_potential"]["note"])

    def test_ceo_view_computes_ranking_exactly_once(self):
        with patch("goos.rank_build_candidates", return_value=_FAKE_RANKING) as mock_rank:
            ghr.ceo_view()
            self.assertEqual(mock_rank.call_count, 1)

    def test_real_call_never_throws(self):
        result = ghr.build_golden_hunter_room(top_n=3)
        self.assertIn("top_opportunities", result)


if __name__ == "__main__":
    unittest.main()

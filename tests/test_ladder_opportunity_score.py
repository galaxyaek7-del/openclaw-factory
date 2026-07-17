"""Tests for profit_oracle.ladder_opportunity_score() (ADR-065,
MASTER_CHARTER.md §2 — Strategic Production Priority Ladder).

Purely additive gate: never touches opportunity_score()/score_opportunity(),
so tests/test_opportunity_score.py's full suite is the regression guard for
that side; these tests cover only the new function.

    python -m unittest tests.test_ladder_opportunity_score -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import profit_oracle as po


class TestLadderFallback(unittest.TestCase):
    def test_unknown_ladder_falls_back_to_kdp_books(self):
        result = po.ladder_opportunity_score("some niche", ladder="not-a-real-ladder")
        self.assertEqual(result["ladder"], "kdp_books")


class TestLadderWeighting(unittest.TestCase):
    def test_ai_saas_scores_higher_than_kdp_books_for_identical_niche(self):
        """The whole point of the ladder: identical underlying demand/
        competition/margin signals, higher score for a higher-ranked track,
        because recurring revenue + reusability are weighted highest."""
        niche = "subscription workflow automation system for accounting firms"
        saas_score = po.ladder_opportunity_score(niche, ladder="ai_saas")["ladder_score"]
        kdp_score = po.ladder_opportunity_score(niche, ladder="kdp_books")["ladder_score"]
        self.assertGreater(saas_score, kdp_score)

    def test_score_never_exceeds_100(self):
        result = po.ladder_opportunity_score("premium subscription enterprise workflow system", ladder="ai_saas")
        self.assertLessEqual(result["ladder_score"], 100)

    def test_components_reused_unchanged_from_score_opportunity(self):
        niche = "evergreen daily journal habit"
        raw = po.score_opportunity(niche)
        result = po.ladder_opportunity_score(niche, ladder="b2b_systems")
        self.assertEqual(result["components"]["market_demand"], raw["scores"]["demand"])
        self.assertEqual(result["components"]["profit_potential"], raw["scores"]["margin"])


class TestRealCandidatesDifferentiate(unittest.TestCase):
    """Real, unmocked niches — the exact case this ADR was written to fix
    (0/1,344 real opportunities ever accepted): at least one professional-
    business-problem niche in a high-ladder-rank category must clear both
    gates, while a plain KDP niche must not."""

    def test_ai_saas_candidate_is_accepted(self):
        result = po.ladder_opportunity_score(
            "AI-powered compliance automation subscription system for accounting firms",
            ladder="ai_saas",
        )
        self.assertTrue(result["accepted"], result)
        self.assertGreaterEqual(result["price"], po.MIN_LADDER_PROFIT_FLOOR)

    def test_plain_kdp_printable_is_rejected(self):
        result = po.ladder_opportunity_score("printable monthly planner", ladder="kdp_books")
        self.assertFalse(result["accepted"])


class TestProfitFloorIndependentOfScore(unittest.TestCase):
    """Mission requirement: reject anything below the $97 profit floor
    regardless of how well it otherwise scores — a separate gate, not
    folded into the weighted formula."""

    @patch("profit_oracle.butter_price", return_value=50)
    def test_high_scoring_niche_still_rejected_below_price_floor(self, mock_price):
        result = po.ladder_opportunity_score(
            "premium subscription enterprise automation system", ladder="ai_saas",
        )
        self.assertGreaterEqual(result["ladder_score"], po.LADDER_MIN_SCORE)
        self.assertFalse(result["accepted"])
        self.assertIn("profit floor", result["reason"])

    @patch("profit_oracle.butter_price", return_value=200)
    def test_price_above_floor_does_not_by_itself_force_acceptance(self, mock_price):
        """A high price alone must not override a weak ladder_score."""
        result = po.ladder_opportunity_score("x", ladder="kdp_books")
        self.assertLess(result["ladder_score"], po.LADDER_MIN_SCORE)
        self.assertFalse(result["accepted"])


if __name__ == "__main__":
    unittest.main()

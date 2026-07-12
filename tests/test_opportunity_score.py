"""Tests for profit_oracle.opportunity_score() (ADR-026,
ELITE_ASSET_DOCTRINE.md §4).

Runs with stdlib unittest (see tests/test_base_arm.py).

    python -m unittest tests.test_opportunity_score -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import profit_oracle as po


class TestOpportunityScoreComponents(unittest.TestCase):
    def test_competition_is_not_inverted(self):
        """score_opportunity()'s competition_score is already oriented
        high=favorable (see profit_oracle.py's _score_competition()) — the
        composite must use it directly, never as (100 - competition)."""
        raw = po.score_opportunity("a very specific narrow test niche")
        result = po.opportunity_score("a very specific narrow test niche", tier="tier4")
        self.assertEqual(
            result["components"]["competition_favorability"],
            raw["scores"]["competition"],
        )

    def test_demand_and_margin_reused_unchanged_from_score_opportunity(self):
        raw = po.score_opportunity("evergreen daily journal habit")
        result = po.opportunity_score("evergreen daily journal habit", tier="tier2")
        self.assertEqual(result["components"]["market_demand"], raw["scores"]["demand"])
        self.assertEqual(result["components"]["profit_potential"], raw["scores"]["margin"])

    def test_unknown_tier_falls_back_to_tier4(self):
        result = po.opportunity_score("some niche", tier="not-a-real-tier")
        self.assertEqual(result["tier"], "tier4")
        self.assertEqual(result["tier_weight"], po.TIER_WEIGHTS["tier4"])


class TestOpportunityScoreTierWeighting(unittest.TestCase):
    def test_same_niche_scores_higher_at_higher_tier(self):
        """The whole point of tier_weight: identical underlying signals,
        higher score for a higher tier (ELITE_ASSET_DOCTRINE.md §3)."""
        niche = "premium subscription budget planner for professionals"
        t1 = po.opportunity_score(niche, tier="tier1")["opportunity_score"]
        t2 = po.opportunity_score(niche, tier="tier2")["opportunity_score"]
        t3 = po.opportunity_score(niche, tier="tier3")["opportunity_score"]
        t4 = po.opportunity_score(niche, tier="tier4")["opportunity_score"]
        self.assertGreater(t1, t2)
        self.assertGreater(t2, t3)
        self.assertGreater(t3, t4)

    def test_score_never_exceeds_100(self):
        result = po.opportunity_score("premium subscription enterprise workflow system", tier="tier1")
        self.assertLessEqual(result["opportunity_score"], 100)


class TestOpportunityScoreThreshold(unittest.TestCase):
    def test_accepted_matches_min_opportunity_score_floor(self):
        result = po.opportunity_score("a random weak generic niche", tier="tier4")
        self.assertEqual(result["accepted"], result["opportunity_score"] >= po.MIN_OPPORTUNITY_SCORE)

    def test_weak_generic_niche_rejected_at_tier4(self):
        result = po.opportunity_score("كتاب", tier="tier4")
        self.assertFalse(result["accepted"])

    def test_min_opportunity_score_stricter_than_book_profit_floor(self):
        """ADR-026: 'fewer, better assets' means a higher bar than
        inspectors.py's existing MIN_PROFIT_SCORE=60, not the same one."""
        self.assertGreater(po.MIN_OPPORTUNITY_SCORE, 60)


if __name__ == "__main__":
    unittest.main()

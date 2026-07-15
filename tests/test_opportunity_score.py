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


class TestTierInvariantAcceptanceFloor(unittest.TestCase):
    """ADR-035: before this fix, tier1's fixed automation_potential/
    long_term_value bonuses (combined with its 1.3 tier_weight) made
    virtually anything clear 65 at tier1 — even a single-character niche.
    Acceptance must now require the same underlying raw quality bar tier4
    already used in production, applied to every tier equally."""

    def test_trivial_single_char_niche_rejected_even_at_tier1(self):
        result = po.opportunity_score("x", tier="tier1")
        self.assertFalse(result["accepted"], result)

    def test_generic_two_word_niche_rejected_at_tier1(self):
        result = po.opportunity_score("AI agent", tier="tier1")
        self.assertFalse(result["accepted"], result)

    def test_fix_is_a_no_op_for_tier4(self):
        """Provable algebraically: raw_floor is MIN_OPPORTUNITY_SCORE /
        TIER_WEIGHTS['tier4'], so for tier4 itself `raw >= raw_floor` is
        exactly `weighted >= MIN_OPPORTUNITY_SCORE` — the only live caller
        (factory_loop.js's Golden Hunter Bridge) always passes tier4, so
        this fix must change nothing about today's production behavior."""
        for niche in ["x", "AI agent", "كتاب", "premium subscription enterprise workflow system"]:
            result = po.opportunity_score(niche, tier="tier4")
            self.assertEqual(result["accepted"], result["opportunity_score"] >= po.MIN_OPPORTUNITY_SCORE, niche)

    def test_a_maximally_optimized_string_can_still_pass_tier1(self):
        """The new floor must be strict, not impossible — confirms tier1
        acceptance is still reachable in principle, not a permanent zero."""
        result = po.score_opportunity("premium subscription")
        raw_ceiling = (
            0.25 * 100 + 0.20 * 100 + 0.20 * 100
            + 0.15 * po.AUTOMATION_POTENTIAL_BY_TIER["tier1"]
            + 0.20 * po.LONG_TERM_VALUE_BY_TIER["tier1"]
        )
        raw_floor = po.MIN_OPPORTUNITY_SCORE / po.TIER_WEIGHTS["tier4"]
        self.assertGreaterEqual(raw_ceiling, raw_floor)


class TestExternalSignal(unittest.TestCase):
    """ADR-038: real HN/GitHub engagement evidence, gathered during the
    Tier-1 research batches (ADR-035/036), can now feed the demand
    component directly instead of the word-count guess."""

    def test_omitting_external_signal_reproduces_exact_prior_behavior(self):
        """The single most important property: every current live caller
        (factory_loop.js) never passes external_signal, so this must be a
        pure no-op for them."""
        niche = "a very specific narrow test niche"
        with_none = po.score_opportunity(niche, external_signal=None)
        without_arg = po.score_opportunity(niche)
        self.assertEqual(with_none["scores"], without_arg["scores"])
        self.assertEqual(with_none["profit_score"], without_arg["profit_score"])

    def test_real_signal_changes_demand_component(self):
        niche = "some niche with no keyword hits at all"
        baseline = po.score_opportunity(niche)["scores"]["demand"]
        with_signal = po.score_opportunity(niche, external_signal={"source": "hacker_news", "points": 200})["scores"]["demand"]
        self.assertNotEqual(baseline, with_signal)

    def test_stronger_real_signal_scores_higher_demand_than_weaker(self):
        weak = po.score_opportunity("x", external_signal={"source": "hacker_news", "points": 1})["scores"]["demand"]
        strong = po.score_opportunity("x", external_signal={"source": "hacker_news", "points": 200})["scores"]["demand"]
        self.assertGreater(strong, weak)

    def test_github_stars_also_recognized(self):
        weak = po.score_opportunity("x", external_signal={"source": "github", "stars": 50})["scores"]["demand"]
        strong = po.score_opportunity("x", external_signal={"source": "github", "stars": 10000})["scores"]["demand"]
        self.assertGreater(strong, weak)

    def test_unknown_source_degrades_to_neutral_never_throws(self):
        result = po.score_opportunity("x", external_signal={"source": "carrier_pigeon", "count": 5})
        self.assertIsInstance(result["scores"]["demand"], int)

    def test_missing_created_at_degrades_to_neutral_momentum_never_throws(self):
        result = po.score_opportunity("x", external_signal={"source": "hacker_news", "points": 50})
        self.assertIsInstance(result["scores"]["demand"], int)

    def test_recent_post_scores_higher_momentum_than_old_one(self):
        from datetime import datetime, timedelta
        now = datetime(2026, 7, 15)
        recent = po.score_opportunity("x", now=now, external_signal={"source": "hacker_news", "points": 50, "created_at": (now - timedelta(days=5)).isoformat()})["scores"]["demand"]
        old = po.score_opportunity("x", now=now, external_signal={"source": "hacker_news", "points": 50, "created_at": (now - timedelta(days=400)).isoformat()})["scores"]["demand"]
        self.assertGreater(recent, old)

    def test_opportunity_score_passes_external_signal_through(self):
        niche = "x"
        r = po.opportunity_score(niche, tier="tier1", external_signal={"source": "github", "stars": 13000})
        without = po.opportunity_score(niche, tier="tier1")
        self.assertNotEqual(r["opportunity_score"], without["opportunity_score"])

    def test_real_batch_candidates_now_differentiate_instead_of_clustering(self):
        """The exact regression this fixes (ADR-036): 8 real, wildly
        different candidates used to all land on the identical 81.6/100.
        With real signal, they must no longer be identical."""
        weak = po.opportunity_score("niche a", tier="tier1", external_signal={"source": "hacker_news", "points": 2})
        strong = po.opportunity_score("niche b", tier="tier1", external_signal={"source": "github", "stars": 13443})
        self.assertNotEqual(weak["opportunity_score"], strong["opportunity_score"])
        self.assertGreater(strong["opportunity_score"], weak["opportunity_score"])


if __name__ == "__main__":
    unittest.main()

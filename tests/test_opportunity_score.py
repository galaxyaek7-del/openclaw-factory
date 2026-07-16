"""Tests for profit_oracle.opportunity_score() (ADR-026,
ELITE_ASSET_DOCTRINE.md §4).

Runs with stdlib unittest (see tests/test_base_arm.py).

    python -m unittest tests.test_opportunity_score -v
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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


class TestRiskAndConfidence(unittest.TestCase):
    """ADR-039: only the two dimensions with a real, already-existing data
    source (safety_filter.py's blocklist, REJECTED_NICHES.md's circuit
    breaker) were added as new scores — never folded into profit_score, so
    no existing accept/reject decision can change because of them."""

    def test_risk_and_confidence_never_change_profit_score_or_verdict(self):
        niche = "premium subscription budget planner for professionals"
        result = po.score_opportunity(niche)
        self.assertIn("risk", result)
        self.assertIn("confidence", result)
        # same profit_score/verdict this niche always produced
        self.assertEqual(result["profit_score"], po.score_opportunity(niche)["profit_score"])

    def test_clean_niche_with_no_rejection_history_scores_low_risk(self):
        result = po.score_opportunity("a totally unremarkable niche xyz123")
        self.assertEqual(result["risk"]["level"], "low")
        self.assertGreaterEqual(result["risk"]["score"], 80)

    def test_is_in_rejected_niches_true_for_real_matching_content(self):
        import tempfile, os as _os
        fd, path = tempfile.mkstemp(suffix=".md")
        _os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write("## 🚫 2026-07-15\n**النيتش:** some rejected niche\n**السبب:** test\n")
        try:
            self.assertTrue(po._is_in_rejected_niches("some rejected niche", rejected_file=path))
            self.assertFalse(po._is_in_rejected_niches("a totally different niche", rejected_file=path))
        finally:
            _os.remove(path)

    def test_is_in_rejected_niches_missing_file_is_false_never_throws(self):
        self.assertFalse(po._is_in_rejected_niches("anything", rejected_file="/no/such/file.md"))

    def test_confidence_low_with_no_real_signal_at_all(self):
        result = po.score_opportunity("some totally generic niche with nothing special")
        self.assertEqual(result["confidence"]["level"], "منخفضة")

    def test_confidence_higher_with_real_external_signal(self):
        without = po.score_opportunity("xyz", external_signal=None)
        withsig = po.score_opportunity("xyz", external_signal={"source": "hacker_news", "points": 50})
        self.assertGreater(withsig["confidence"]["score"], without["confidence"]["score"])


class TestRealCompetitionAndMargin(unittest.TestCase):
    """ADR-041: real competitor-count feeds competition; real platform fees
    (economics.py) + real logged AI cost (book_generator.py's cost log)
    feed margin — same 'reuse before creating' pattern as ADR-038/039."""

    def test_competition_unaffected_when_no_real_signal_present(self):
        niche = "a niche with no saved report and no external signal"
        without = po.score_opportunity(niche)
        with_none = po.score_opportunity(niche, external_signal=None)
        self.assertEqual(without["scores"]["competition"], with_none["scores"]["competition"])

    def test_real_related_results_count_changes_competition_score(self):
        niche = "some niche xyz"
        baseline = po.score_opportunity(niche)["scores"]["competition"]
        crowded = po.score_opportunity(niche, external_signal={"competition": {"related_results_count": 500}})["scores"]["competition"]
        self.assertNotEqual(baseline, crowded)

    def test_more_real_competitors_scores_lower_than_fewer(self):
        few = po.score_opportunity("x", external_signal={"competition": {"related_results_count": 1}})["scores"]["competition"]
        many = po.score_opportunity("x", external_signal={"competition": {"related_results_count": 1000}})["scores"]["competition"]
        self.assertGreater(few, many)

    def test_saved_amazon_report_still_takes_priority_over_external_signal(self):
        """The original real-data path (niche_validator_v2 saved reports)
        must still win over the newer external_signal path when both exist
        — it's the more specific, platform-real signal."""
        niche = "a niche with no saved report at all zzz"
        result = po.score_opportunity(niche, external_signal={"competition": {"related_results_count": 5}})
        # no saved report for this fake niche, so the external_signal path is used
        self.assertIn("بحث حي", result["reasoning"])

    def test_margin_uses_real_economics_fees_not_flat_100(self):
        result = po.score_opportunity("premium subscription budget planner")
        self.assertIn("هامش صافٍ حقيقي", result["reasoning"])
        self.assertIn("economics.json", result["reasoning"])

    def test_margin_never_raises_if_economics_unavailable(self):
        original = po.ECONOMICS
        try:
            po.ECONOMICS = None
            result = po.score_opportunity("premium subscription budget planner")
            self.assertIsInstance(result["scores"]["margin"], int)
        finally:
            po.ECONOMICS = original

    def test_real_average_ai_cost_missing_log_returns_none_not_zero(self):
        avg, count = po._real_average_ai_cost_per_call(log_file="/no/such/ai_cost_log.jsonl")
        self.assertIsNone(avg)
        self.assertEqual(count, 0)

    def test_real_average_ai_cost_computed_from_real_logged_entries(self):
        import tempfile, os as _os
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        _os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_usd": 0.01}) + "\n")
                f.write(json.dumps({"cost_usd": 0.03}) + "\n")
            avg, count = po._real_average_ai_cost_per_call(log_file=path)
            self.assertEqual(count, 2)
            self.assertAlmostEqual(avg, 0.02, places=6)
        finally:
            _os.remove(path)


class TestRealMarginPricing(unittest.TestCase):
    """Revenue Activation phase (2026-07-16): _score_margin() now checks
    _find_niche_report() for a real saved competitor price first — the
    same real-data-priority pattern _score_competition() already used
    since ADR-041/042 — falling back to the keyword-tier estimate only
    when no real report exists."""

    _REAL_REPORT = {
        "status": "success",
        "metrics": {"price": {"min": 6.99, "avg": 24.99, "max": 39.99}},
    }

    @patch("profit_oracle._find_niche_report", return_value=_REAL_REPORT)
    def test_real_saved_price_is_used_when_available(self, mock_find):
        margin_score, notes, price = po._score_margin("a niche with a real saved report")
        self.assertEqual(price, 24.99)
        self.assertTrue(any("بيانات حقيقية" in n and "24.99" in n for n in notes))

    @patch("profit_oracle._find_niche_report", return_value=_REAL_REPORT)
    def test_real_price_score_is_normalized_against_max_butter_price(self, mock_find):
        _, notes, price = po._score_margin("a niche with a real saved report")
        expected_score = max(0, min(100, round(price / po.MAX_BUTTER_PRICE * 100)))
        self.assertTrue(any(f"{expected_score}/100" in n for n in notes))

    @patch("profit_oracle._find_niche_report", return_value=None)
    def test_keyword_estimation_used_as_fallback_when_no_report(self, mock_find):
        _, notes, price = po._score_margin("template bundle system")  # PREMIUM_KEYWORDS tier
        self.assertEqual(price, 39)  # unchanged from before this fix
        self.assertTrue(any("تقدير حسب فئة الكلمات المفتاحية" in n for n in notes))

    @patch("profit_oracle._find_niche_report", return_value={"status": "error"})
    def test_error_status_report_also_falls_back_to_keyword_estimate(self, mock_find):
        _, notes, price = po._score_margin("template bundle system")
        self.assertEqual(price, 39)

    @patch("profit_oracle._find_niche_report", return_value={"status": "success", "metrics": {}})
    def test_report_missing_price_field_falls_back_to_keyword_estimate(self, mock_find):
        _, notes, price = po._score_margin("template bundle system")
        self.assertEqual(price, 39)

    def test_existing_behavior_unchanged_when_no_report_exists_on_real_disk(self):
        """The exact regression proof requested: with the real,
        untouched niche_reports/ directory (empty, per this session's own
        confirmation), score_opportunity()'s margin score and reasoning
        for an existing, already-tested niche must be byte-for-byte
        identical to before this fix."""
        result = po.score_opportunity("premium subscription budget planner")
        self.assertIn("هامش صافٍ حقيقي", result["reasoning"])
        self.assertIn("economics.json", result["reasoning"])
        self.assertIn("$19", result["recommended_price"])


if __name__ == "__main__":
    unittest.main()

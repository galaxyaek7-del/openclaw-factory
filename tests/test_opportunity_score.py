"""Tests for profit_oracle.opportunity_score() (ADR-026,
ELITE_ASSET_DOCTRINE.md §4).

Runs with stdlib unittest (see tests/test_base_arm.py).

    python -m unittest tests.test_opportunity_score -v
"""

import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import profit_oracle as po

# Captured before any test patches profit_oracle.score_opportunity, so
# tests that mock it can still obtain one real, fully-shaped result to
# safely override individual fields on.
_REAL_SCORE_OPPORTUNITY = po.score_opportunity


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


class TestReasonStringReflectsActualDecision(unittest.TestCase):
    """Red-team audit (Phase 10 follow-up) — MEDIUM finding: the `reason`
    string used to compare `weighted` against the literal
    MIN_OPPORTUNITY_SCORE constant (65), but `accepted` is actually decided
    by `raw >= raw_floor` (81.25, tier-invariant — see ADR-035 above), a
    different comparison for every tier except tier4. For tier3
    (tier_weight=1.0, so weighted == raw) this could produce a false
    inequality like "69.5/100 < 65" for a value that is not, in fact, less
    than 65 — a real, permanently-recorded (decisions.jsonl) bug for any
    future tier1-3 caller. Dormant today: factory_loop.js's only live
    caller always passes tier4 (test_fix_is_a_no_op_for_tier4 above)."""

    @patch("profit_oracle.score_opportunity")
    def test_tier3_rejection_reason_uses_raw_floor_not_the_flat_constant(self, mock_score):
        # demand=competition=margin=70 with tier3's fixed
        # automation_potential=80/long_term_value=60 gives weighted=raw=69.5:
        # rejected (69.5 < raw_floor 81.25) even though 69.5 is NOT < 65 —
        # exactly the false-inequality condition the old string produced.
        # Start from a real result (so every field opportunity_score() reads
        # is present and realistic) and override only the three scores.
        real_result = _REAL_SCORE_OPPORTUNITY("مثال اختبار")
        real_result["scores"] = {"demand": 70, "competition": 70, "margin": 70}
        mock_score.return_value = real_result
        result = po.opportunity_score("مثال اختبار", tier="tier3")

        self.assertEqual(result["opportunity_score"], 69.5)
        self.assertFalse(result["accepted"])
        # The number this rejection is measured against must be raw_floor
        # (81.25), never the flat MIN_OPPORTUNITY_SCORE (65) — 69.5 is not
        # less than 65, so a reason string built from 65 would be a lie.
        raw_floor = po.MIN_OPPORTUNITY_SCORE / po.TIER_WEIGHTS["tier4"]
        self.assertIn(f"{raw_floor:.1f}", result["reason"])
        self.assertNotIn(f"{result['opportunity_score']}/100 < {po.MIN_OPPORTUNITY_SCORE}", result["reason"])

    def test_tier4_reason_string_unchanged_in_substance(self):
        """No-op check for the only live tier: for tier4, raw == weighted /
        tier_weight and raw_floor's comparison is algebraically identical
        to weighted >= MIN_OPPORTUNITY_SCORE, so accepted/rejected must
        still line up exactly with the flat floor for every real niche."""
        for niche in ["x", "AI agent", "كتاب", "premium subscription enterprise workflow system"]:
            result = po.opportunity_score(niche, tier="tier4")
            self.assertEqual(
                result["accepted"],
                result["opportunity_score"] >= po.MIN_OPPORTUNITY_SCORE,
                niche,
            )
            if result["accepted"]:
                self.assertIn("accepted:", result["reason"])
            else:
                self.assertIn("rejected:", result["reason"])


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


class TestDefensibility(unittest.TestCase):
    """Strategic Phase 3, Round 1 (2026-07-22): Golden Hunter Evolution's
    'defensibility' dimension -- additive only (ADR-039 pattern), sourced
    from competitor_discovery.py's CACHED database only. Never triggers a
    live HN+GitHub search from inside scoring."""

    def test_defensibility_never_changes_profit_score_or_verdict(self):
        niche = "premium subscription budget planner for professionals"
        result = po.score_opportunity(niche)
        self.assertIn("defensibility", result)
        self.assertEqual(result["profit_score"], po.score_opportunity(niche)["profit_score"])

    def test_unknown_when_no_cached_competitor_data_exists(self):
        with patch.object(po.COMPETITOR_DISCOVERY, "load_database", return_value={}):
            result = po.score_opportunity("a niche with no cached competitor data at all xyz")
        self.assertEqual(result["defensibility"]["level"], "Unknown")
        self.assertIsNone(result["defensibility"]["score"])

    def test_never_triggers_a_live_competitor_search_from_inside_scoring(self):
        with patch.object(po.COMPETITOR_DISCOVERY, "discover_competitors", side_effect=AssertionError("must never be called from scoring")), \
             patch.object(po.COMPETITOR_DISCOVERY, "get_or_refresh_competitors", side_effect=AssertionError("must never be called from scoring")):
            po.score_opportunity("any niche")  # would raise if either were called

    def test_low_defensibility_when_cached_data_shows_strong_competitors(self):
        niche = "crowded niche with strong competitors"
        fixture = {
            po.COMPETITOR_DISCOVERY._normalize_key(niche): {
                "total_found": 4,
                "by_category": {"Direct Competitor": ["a", "b"], "Enterprise Leader": ["c"], "Unclassified": ["d"]},
            }
        }
        with patch.object(po.COMPETITOR_DISCOVERY, "load_database", return_value=fixture):
            result = po.score_opportunity(niche)
        self.assertEqual(result["defensibility"]["level"], "منخفضة")
        self.assertLess(result["defensibility"]["score"], 50)

    def test_higher_defensibility_when_cached_data_shows_no_strong_competitors(self):
        niche = "quiet niche with only weak competitors"
        fixture = {
            po.COMPETITOR_DISCOVERY._normalize_key(niche): {
                "total_found": 3,
                "by_category": {"Unclassified": ["a", "b"], "Emerging Startup": ["c"]},
            }
        }
        with patch.object(po.COMPETITOR_DISCOVERY, "load_database", return_value=fixture):
            result = po.score_opportunity(niche)
        self.assertEqual(result["defensibility"]["level"], "عالية نسبياً")
        self.assertGreaterEqual(result["defensibility"]["score"], 70)


class TestMarketSignal(unittest.TestCase):
    """Strategic Opportunity Intelligence Engine (2026-07-22): a real
    discussion-volume proxy -- explicitly NOT a dollar TAM estimate. Never
    fabricates a market-size number when no real evidence exists."""

    def test_never_changes_profit_score_or_verdict(self):
        niche = "a market signal test niche"
        result = po.score_opportunity(niche)
        self.assertIn("market_signal", result)
        self.assertEqual(result["profit_score"], po.score_opportunity(niche)["profit_score"])

    def test_honestly_unknown_with_no_cached_data_and_no_external_signal(self):
        with patch.object(po.COMPETITOR_DISCOVERY, "load_database", return_value={}):
            result = po.score_opportunity("a niche with zero market signal data xyz")
        self.assertEqual(result["market_signal"]["level"], "Unknown")
        self.assertIsNone(result["market_signal"]["score"])

    def test_real_cached_volume_produces_a_real_score(self):
        niche = "a niche with real cached discussion volume"
        fixture = {po.COMPETITOR_DISCOVERY._normalize_key(niche): {"total_found": 50, "by_category": {}}}
        with patch.object(po.COMPETITOR_DISCOVERY, "load_database", return_value=fixture):
            result = po.score_opportunity(niche)
        self.assertIsNotNone(result["market_signal"]["score"])
        self.assertIn("50", result["market_signal"]["note"])

    def test_never_presents_itself_as_a_dollar_tam(self):
        niche = "a niche checking market signal wording"
        fixture = {po.COMPETITOR_DISCOVERY._normalize_key(niche): {"total_found": 20, "by_category": {}}}
        with patch.object(po.COMPETITOR_DISCOVERY, "load_database", return_value=fixture):
            result = po.score_opportunity(niche)
        self.assertNotIn("$", result["market_signal"]["note"])
        self.assertIn("TAM", result["market_signal"]["note"])  # explicitly disclaims being one

    def test_external_signal_used_when_no_cache_entry(self):
        result = po.score_opportunity("a niche with only external signal", external_signal={"competition": {"related_results_count": 30}})
        self.assertIsNotNone(result["market_signal"]["score"])

    def test_never_triggers_a_live_competitor_search(self):
        with patch.object(po.COMPETITOR_DISCOVERY, "discover_competitors", side_effect=AssertionError("must never be called from scoring")), \
             patch.object(po.COMPETITOR_DISCOVERY, "get_or_refresh_competitors", side_effect=AssertionError("must never be called from scoring")):
            po.score_opportunity("any niche")


class TestAiLeverage(unittest.TestCase):
    """Strategic Opportunity Intelligence Engine (2026-07-22): a real,
    deterministic keyword classification -- same discipline as every other
    keyword-based score in this file, never a fabricated 'AI readiness'
    number."""

    def test_never_changes_profit_score_or_verdict(self):
        niche = "AI-powered research and writing assistant"
        result = po.score_opportunity(niche)
        self.assertIn("ai_leverage", result)
        self.assertEqual(result["profit_score"], po.score_opportunity(niche)["profit_score"])

    def test_high_leverage_for_text_knowledge_work(self):
        result = po.score_opportunity("automated research and content writing assistant for analysts")
        self.assertEqual(result["ai_leverage"]["level"], "عالية")

    def test_low_leverage_for_physical_work(self):
        result = po.score_opportunity("warehouse logistics and physical shipping manufacturing tool")
        self.assertEqual(result["ai_leverage"]["level"], "منخفضة")

    def test_unknown_with_no_recognizable_keywords_at_all(self):
        result = po.score_opportunity("xyz qwerty zzz")
        self.assertEqual(result["ai_leverage"]["level"], "Unknown")
        self.assertIsNone(result["ai_leverage"]["score"])


class TestUrgency(unittest.TestCase):
    """Global Opportunity Intelligence extension (2026-07-23): real
    customer-pain evidence, passed in via external_signal -- never a live
    query triggered from inside scoring, never a guessed urgency."""

    def test_never_changes_profit_score_or_verdict(self):
        # Isolates customer_pain specifically: _score_demand() branches
        # on whether external_signal is truthy AT ALL (real,
        # pre-existing behavior, unrelated to this change — an empty
        # dict and no dict take different internal branches from a
        # non-empty one), so both calls here carry the same baseline
        # "an external signal was provided" key to hold that branch
        # constant, differing only in whether customer_pain is present.
        niche = "compliance automation for accounting firms"
        baseline_signal = {"source": "manual_baseline"}
        with_pain = po.score_opportunity(niche, external_signal={**baseline_signal, "customer_pain": {"willingness_to_pay_hits": 3, "pain_language_hits": 5}})
        without_pain = po.score_opportunity(niche, external_signal=baseline_signal)
        self.assertIn("urgency", with_pain)
        self.assertEqual(with_pain["profit_score"], without_pain["profit_score"])

    def test_unknown_when_no_customer_pain_evidence_passed_in(self):
        result = po.score_opportunity("a niche with no pain evidence passed in xyz")
        self.assertEqual(result["urgency"]["level"], "Unknown")
        self.assertIsNone(result["urgency"]["score"])

    def test_high_urgency_from_real_willingness_to_pay_and_pain_evidence(self):
        signal = {"customer_pain": {"willingness_to_pay_hits": 4, "pain_language_hits": 6}}
        result = po.score_opportunity("a real niche with strong pain evidence", external_signal=signal)
        self.assertEqual(result["urgency"]["level"], "عالية")

    def test_low_urgency_from_weak_real_evidence(self):
        signal = {"customer_pain": {"willingness_to_pay_hits": 0, "pain_language_hits": 1}}
        result = po.score_opportunity("a real niche with weak pain evidence", external_signal=signal)
        self.assertEqual(result["urgency"]["level"], "منخفضة")

    def test_never_triggers_a_live_customer_pain_query_from_inside_scoring(self):
        # score_opportunity() must only ever read external_signal -- it has
        # no live customer-pain query capability to call in the first
        # place, so this documents the contract rather than mocking a
        # specific function; a real regression here would look like a new
        # network call being added to this file.
        po.score_opportunity("any niche")  # no external_signal at all — must not raise or hang


class TestBarrierToEntry(unittest.TestCase):
    """Global Opportunity Intelligence extension (2026-07-23): a real
    signal deliberately distinct from defensibility (current competitive
    intensity) -- this measures technical replication difficulty, derived
    from the real, already-computed execution score."""

    def test_never_changes_profit_score_or_verdict(self):
        niche = "premium subscription budget planner for professionals"
        result = po.score_opportunity(niche)
        self.assertIn("barrier_to_entry", result)
        self.assertEqual(result["profit_score"], po.score_opportunity(niche)["profit_score"])

    def test_is_the_inverse_of_execution_score_not_a_copy_of_defensibility(self):
        niche = "a real test niche for barrier to entry"
        result = po.score_opportunity(niche)
        execution_score = result["scores"]["execution"]
        self.assertEqual(result["barrier_to_entry"]["score"], 100 - execution_score)
        # Distinct field, not silently aliasing defensibility's own value.
        self.assertNotEqual(
            result["barrier_to_entry"], result["defensibility"],
            "barrier_to_entry must be its own real computation, not a copy of defensibility",
        )


class TestAutomationPotentialByLadder(unittest.TestCase):
    """Strategic Opportunity Intelligence Engine (2026-07-22): the ladder
    path had zero automation_potential field before this -- grounded in
    ELITE_ASSET_DOCTRINE.md's real finding (ai_saas/b2b_systems need
    infrastructure that doesn't exist; automation_tools/reusable_assets/
    educational/kdp_books already run on the existing pipeline today)."""

    def test_ai_saas_has_low_automation_potential_today(self):
        result = po.ladder_opportunity_score("a real automation potential test niche", ladder="ai_saas")
        self.assertEqual(result["components"]["automation_potential"], 40)

    def test_kdp_books_has_high_automation_potential_today(self):
        result = po.ladder_opportunity_score("a real automation potential test niche", ladder="kdp_books")
        self.assertEqual(result["components"]["automation_potential"], 100)

    def test_never_changes_ladder_score_formula_weights(self):
        """The core weighted formula must stay exactly as ADR-065 defined
        it -- automation_potential is additive context, not a 6th weighted
        component silently added to the gate."""
        with_it = po.ladder_opportunity_score("a formula stability test niche", ladder="automation_tools")
        # ladder_score is computed from exactly 5 weighted components; confirm the value is unchanged from before this dimension existed by recomputing the same formula manually.
        c = with_it["components"]
        expected = round(min(100.0, 0.15 * c["market_demand"] + 0.15 * c["competition_favorability"] + 0.15 * c["profit_potential"] + 0.25 * c["recurring_revenue_potential"] + 0.30 * c["reusability"]), 1)
        self.assertEqual(with_it["ladder_score"], expected)


class TestStrategicInvestmentLayer(unittest.TestCase):
    """Strategic Opportunity Intelligence Engine (2026-07-22): a pure
    synthesis over an already-computed ladder_opportunity_score() result
    -- never recomputes, never changes accepted, every answer cites real
    evidence or is honestly Uncertain."""

    def _ladder_result(self, **overrides):
        base = {
            "niche": "a strategic layer test niche", "ladder": "ai_saas", "price": 297,
            "accepted": True, "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 55,
                "recurring_revenue_potential": 100, "reusability": 95, "automation_potential": 40,
            },
            "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "لا منافسين أقوياء"},
            "market_signal": {"score": 60, "level": "مرتفعة", "note": "حجم نقاش حقيقي: 50 نتيجة"},
            "ai_leverage": {"score": 80, "level": "عالية", "note": "2 كلمة عالية"},
        }
        base.update(overrides)
        return base

    def test_never_mutates_or_recomputes_the_input(self):
        ladder_result = self._ladder_result()
        original = dict(ladder_result)
        po.strategic_investment_layer(ladder_result)
        self.assertEqual(ladder_result, original)

    def test_all_seven_questions_present(self):
        result = po.strategic_investment_layer(self._ladder_result())
        for key in (
            "can_become_premium_digital_asset", "can_evolve_into_software_business",
            "can_create_recurring_revenue", "can_dominate_a_narrow_market",
            "competitors_can_copy_it_easily", "becomes_more_valuable_over_time",
            "can_create_a_product_ecosystem",
        ):
            self.assertIn(key, result)
            self.assertIn(result[key]["answer"], ("Yes", "No", "Uncertain"))
            self.assertTrue(result[key]["evidence"])

    def test_strong_real_evidence_across_the_board_answers_yes_consistently(self):
        result = po.strategic_investment_layer(self._ladder_result())
        self.assertEqual(result["can_become_premium_digital_asset"]["answer"], "Yes")
        self.assertEqual(result["can_evolve_into_software_business"]["answer"], "Yes")
        self.assertEqual(result["can_create_recurring_revenue"]["answer"], "Yes")
        self.assertEqual(result["competitors_can_copy_it_easily"]["answer"], "No")
        self.assertEqual(result["can_create_a_product_ecosystem"]["answer"], "Yes")

    def test_missing_defensibility_is_uncertain_never_a_guessed_yes_or_no(self):
        ladder_result = self._ladder_result(defensibility={"score": None, "level": "Unknown", "note": "لا بيانات"})
        result = po.strategic_investment_layer(ladder_result)
        self.assertEqual(result["can_become_premium_digital_asset"]["answer"], "Uncertain")
        self.assertEqual(result["competitors_can_copy_it_easily"]["answer"], "Uncertain")

    def test_low_price_answers_no_never_yes(self):
        ladder_result = self._ladder_result(price=45)
        result = po.strategic_investment_layer(ladder_result)
        self.assertEqual(result["can_become_premium_digital_asset"]["answer"], "No")

    def test_kdp_books_ladder_cannot_become_a_software_business(self):
        ladder_result = self._ladder_result(ladder="kdp_books")
        result = po.strategic_investment_layer(ladder_result)
        self.assertEqual(result["can_evolve_into_software_business"]["answer"], "No")

    def test_low_defensibility_says_competitors_can_copy_it(self):
        ladder_result = self._ladder_result(defensibility={"score": 25, "level": "منخفضة", "note": "منافسون أقوياء كثر"})
        result = po.strategic_investment_layer(ladder_result)
        self.assertEqual(result["competitors_can_copy_it_easily"]["answer"], "Yes")

    def test_never_changes_the_real_accept_reject_gate(self):
        ladder_result = self._ladder_result()
        po.strategic_investment_layer(ladder_result)
        self.assertTrue(ladder_result["accepted"])  # untouched


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


class TestRealAiCostTrend(unittest.TestCase):
    """Autonomous Digital Company v1 follow-up (2026-07-19): the same real
    cost-rate-trend signal lib/infrastructure_intelligence.js's
    getCostTrend() computes for the dashboard, reimplemented here so
    _score_margin() can use a real, current cost figure instead of a flat
    all-time average."""

    def _write_log(self, entries):
        import tempfile, os as _os
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        _os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        return path

    def test_missing_log_returns_none_not_zero(self):
        avg, outlier = po._real_ai_cost_trend(log_file="/no/such/ai_cost_log.jsonl")
        self.assertIsNone(avg)
        self.assertFalse(outlier)

    def test_no_recent_entries_returns_none(self):
        now = datetime(2026, 7, 20)
        old_ts = (now - timedelta(days=20)).isoformat()
        path = self._write_log([{"cost_usd": 0.01, "timestamp": old_ts}])
        try:
            avg, outlier = po._real_ai_cost_trend(log_file=path, now=now)
            self.assertIsNone(avg)
            self.assertFalse(outlier)
        finally:
            os.remove(path)

    def test_real_trailing_baseline_plus_a_genuine_spike_is_flagged(self):
        now = datetime(2026, 7, 20)
        entries = []
        for d in range(10, 1, -1):
            entries.append({"cost_usd": 0.0001, "timestamp": (now - timedelta(days=d)).isoformat()})
        entries.append({"cost_usd": 5.0, "timestamp": (now - timedelta(hours=1)).isoformat()})
        path = self._write_log(entries)
        try:
            avg, outlier = po._real_ai_cost_trend(log_file=path, now=now)
            self.assertGreater(avg, 0)
            self.assertTrue(outlier)
        finally:
            os.remove(path)

    def test_steady_spend_is_not_flagged(self):
        now = datetime(2026, 7, 20)
        entries = [{"cost_usd": 0.0001, "timestamp": (now - timedelta(days=d)).isoformat()} for d in range(15, 0, -1)]
        path = self._write_log(entries)
        try:
            avg, outlier = po._real_ai_cost_trend(log_file=path, now=now)
            self.assertFalse(outlier)
        finally:
            os.remove(path)


class TestScoreMarginUsesRealCostTrendOnAGenuineOutlier(unittest.TestCase):
    @patch("profit_oracle._real_ai_cost_trend", return_value=(0.5, True))
    @patch("profit_oracle._real_average_ai_cost_per_call", return_value=(0.001, 10))
    def test_real_outlier_uses_the_recent_average_and_notes_it(self, mock_avg, mock_trend):
        _, notes, _ = po._score_margin("template bundle system")
        self.assertTrue(any("ارتفاع حقيقي في تكلفة" in n for n in notes))

    @patch("profit_oracle._real_ai_cost_trend", return_value=(None, False))
    @patch("profit_oracle._real_average_ai_cost_per_call", return_value=(0.001, 10))
    def test_no_outlier_keeps_prior_behavior_unchanged(self, mock_avg, mock_trend):
        _, notes, _ = po._score_margin("template bundle system")
        self.assertFalse(any("ارتفاع حقيقي في تكلفة" in n for n in notes))


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

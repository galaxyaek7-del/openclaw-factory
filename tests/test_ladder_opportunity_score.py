"""Tests for profit_oracle.ladder_opportunity_score() (ADR-065,
MASTER_CHARTER.md §2 — Strategic Production Priority Ladder; reweighted
under the Proof of Payment doctrine, ADR-121, 2026-07-24).

Purely additive gate: never touches opportunity_score()/score_opportunity(),
so tests/test_opportunity_score.py's full suite is the regression guard for
that side; these tests cover only the new function.

Isolation note: every test here passes its own temp evidence_path (never
the real data/market_evidence.jsonl) — same test-isolation convention as
every other stateful path this factory's tests already use. Tests whose
own purpose is something OTHER than the payment-evidence gate itself
(price floor, score floor, ladder weighting) record one real-shaped
evidence event first, in the isolated ledger, so that gate is cleanly
satisfied and doesn't mask what the test actually means to exercise.

    python -m unittest tests.test_ladder_opportunity_score -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_evidence as me
import profit_oracle as po


def _temp_evidence_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


def _seed_payment_evidence(niche, evidence_path, n=1, event_type="complaining_review"):
    """Records n real-shaped (test-fixture) payment evidence events for
    niche in the isolated ledger at evidence_path -- exercises the exact
    same record_evidence() validation real evidence goes through."""
    for i in range(n):
        me.record_evidence(
            niche, event_type,
            payload={"source_url": f"https://example.com/evidence-{i}", "quote": f"real quoted complaint #{i}"},
            evidence_path=evidence_path,
        )


def _patch_defensibility_pass(testcase):
    """GALAXY FORGE PRODUCT STRATEGY (ADR-126): defensibility is now a hard
    gate ("difficult to copy"), fed by _score_defensibility()'s real read
    of the SHARED data/competitor_database.json -- unlike payment evidence,
    it has no evidence_path-style override, since competitor data is
    genuinely global-per-niche, not something a caller records per call.
    Tests that aren't specifically exercising this gate mock the function
    directly (unittest.mock.patch, the same isolation technique this file
    already uses for butter_price()) rather than writing into the real
    shared competitor database, which would pollute it for every other
    real caller."""
    patcher = patch("profit_oracle._score_defensibility", return_value=(75, "عالية نسبياً", "test-seeded: real cached fixture, isolated via mock"))
    patcher.start()
    testcase.addCleanup(patcher.stop)


def _pain_evidence_signal(pain_hits=1, wtp_hits=1):
    """Strategic Doctrine v2 (ADR-122): the exact external_signal shape
    _score_urgency() expects -- a caller's own real, already-computed
    market_intelligence_engine.analyze_customer_pain() result (real_evidence
    sub-dict), never gathered by ladder_opportunity_score() itself."""
    return {"customer_pain": {"pain_language_hits": pain_hits, "willingness_to_pay_hits": wtp_hits}}


class TestLadderFallback(unittest.TestCase):
    def setUp(self):
        self.evidence_path = _temp_evidence_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_unknown_ladder_falls_back_to_kdp_books(self):
        result = po.ladder_opportunity_score("some niche", ladder="not-a-real-ladder", evidence_path=self.evidence_path)
        self.assertEqual(result["ladder"], "kdp_books")


class TestLadderWeighting(unittest.TestCase):
    def setUp(self):
        self.evidence_path = _temp_evidence_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_ai_saas_scores_higher_than_kdp_books_for_identical_niche(self):
        """The whole point of the ladder: identical underlying demand/
        competition/margin signals AND identical payment evidence, higher
        score for a higher-ranked track, because recurring revenue +
        reusability are weighted highest among the ladder-derived factors."""
        niche = "subscription workflow automation system for accounting firms"
        _seed_payment_evidence(niche, self.evidence_path, n=3)
        saas_score = po.ladder_opportunity_score(niche, ladder="ai_saas", evidence_path=self.evidence_path)["ladder_score"]
        kdp_score = po.ladder_opportunity_score(niche, ladder="kdp_books", evidence_path=self.evidence_path)["ladder_score"]
        self.assertGreater(saas_score, kdp_score)

    def test_score_never_exceeds_100(self):
        niche = "premium subscription enterprise workflow system"
        _seed_payment_evidence(niche, self.evidence_path, n=3)
        result = po.ladder_opportunity_score(niche, ladder="ai_saas", evidence_path=self.evidence_path)
        self.assertLessEqual(result["ladder_score"], 100)

    def test_components_reused_unchanged_from_score_opportunity(self):
        niche = "evergreen daily journal habit"
        raw = po.score_opportunity(niche)
        result = po.ladder_opportunity_score(niche, ladder="b2b_systems", evidence_path=self.evidence_path)
        self.assertEqual(result["components"]["market_demand"], raw["scores"]["demand"])
        self.assertEqual(result["components"]["profit_potential"], raw["scores"]["margin"])


class TestProofOfPaymentDoctrine(unittest.TestCase):
    """ADR-121 (2026-07-24): real payment evidence is the highest-weighted
    factor and a hard gate — an opportunity with zero real, cited evidence
    is UNPROVEN and rejected regardless of every other score."""

    def setUp(self):
        self.evidence_path = _temp_evidence_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_zero_evidence_is_rejected_as_unproven_even_with_a_high_score(self):
        # A niche whose keyword/ladder signals alone would clear both the
        # score and price floors under the old doctrine -- proves the new
        # gate is independent of, and fires before, the old ones.
        result = po.ladder_opportunity_score(
            "AI-powered compliance automation subscription system for accounting firms",
            ladder="ai_saas", evidence_path=self.evidence_path,
        )
        self.assertFalse(result["accepted"])
        self.assertIn("UNPROVEN", result["reason"])
        self.assertEqual(result["payment_evidence"], [])
        self.assertEqual(result["components"]["payment_evidence_score"], 0.0)

    def test_real_cited_evidence_clears_the_gate(self):
        _patch_defensibility_pass(self)
        niche = "AI-powered compliance automation subscription system for accounting firms"
        _seed_payment_evidence(niche, self.evidence_path, n=1, event_type="paid_job_posting")
        result = po.ladder_opportunity_score(
            niche, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertTrue(result["accepted"], result)
        self.assertEqual(len(result["payment_evidence"]), 1)
        self.assertEqual(result["payment_evidence"][0]["event_type"], "paid_job_posting")
        self.assertTrue(result["payment_evidence"][0]["source_url"].startswith("https://"))
        self.assertIn("real quoted complaint", result["payment_evidence"][0]["quote"])

    def test_payment_evidence_field_carries_the_actual_source_and_quote(self):
        niche = "test niche for citation passthrough"
        me.record_evidence(
            niche, "freelancer_agency_pricing",
            payload={"source_url": "https://upwork.com/real-gig-123", "quote": "$45/hr for manual invoice entry"},
            evidence_path=self.evidence_path,
        )
        result = po.ladder_opportunity_score(niche, ladder="automation_tools", evidence_path=self.evidence_path)
        self.assertEqual(result["payment_evidence"][0]["source_url"], "https://upwork.com/real-gig-123")
        self.assertEqual(result["payment_evidence"][0]["quote"], "$45/hr for manual invoice entry")

    def test_more_independent_evidence_scores_higher_but_never_bypasses_other_floors(self):
        one_evidence = "niche with one real evidence record"
        three_evidence = "niche with three real evidence records"
        _seed_payment_evidence(one_evidence, self.evidence_path, n=1)
        _seed_payment_evidence(three_evidence, self.evidence_path, n=3)
        r1 = po.ladder_opportunity_score(one_evidence, ladder="automation_tools", evidence_path=self.evidence_path)
        r3 = po.ladder_opportunity_score(three_evidence, ladder="automation_tools", evidence_path=self.evidence_path)
        self.assertEqual(r1["components"]["payment_evidence_score"], 40.0)
        self.assertEqual(r3["components"]["payment_evidence_score"], 100.0)

    def test_payment_evidence_is_the_single_highest_weighted_component(self):
        """Founder directive: weight evidence of EXISTING SPEND above
        inferred demand -- 0.35, higher than every other single factor."""
        niche = "weighting sanity check niche"
        _seed_payment_evidence(niche, self.evidence_path, n=3)
        result = po.ladder_opportunity_score(niche, ladder="ai_saas", evidence_path=self.evidence_path)
        components = result["components"]
        # payment_evidence_score is 100 here (3 real records) and is the
        # only component that can reach 100 purely from real evidence
        # regardless of the niche's keyword-inferred demand/competition —
        # a real, direct proof the 0.35 weight is applied, not just present.
        self.assertEqual(components["payment_evidence_score"], 100.0)

    def test_real_evidence_citation_still_requires_source_url_and_quote_to_record(self):
        """The gate is only as honest as what it's allowed to accept —
        record_evidence() itself refuses an uncited payment-evidence
        event, same discipline as COMPETITOR_EVENT_TYPES."""
        with self.assertRaises(ValueError):
            me.record_evidence(
                "some niche", "complaining_review", payload={"source_url": "https://example.com"},
                evidence_path=self.evidence_path,
            )  # missing "quote"


class TestStrategicDoctrineV2(unittest.TestCase):
    """ADR-122 (2026-07-24): the 4-condition decision hierarchy — Proof of
    Payment -> Pain Severity -> Competitive Advantage -> Long-Term
    Strategic Asset. Each of the 3 new gates is independently provable:
    a niche/ladder combination engineered to pass every OTHER gate still
    gets rejected on exactly the one gate under test."""

    NICHE = "AI-powered compliance automation subscription system for accounting firms"  # real ai_leverage hit ("compliance"), ai_saas-eligible

    def setUp(self):
        self.evidence_path = _temp_evidence_path()
        _seed_payment_evidence(self.NICHE, self.evidence_path, n=1)
        _patch_defensibility_pass(self)

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_all_4_conditions_satisfied_is_accepted(self):
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["strategic_doctrine_v2"], {
            "proof_of_payment": True, "pain_severity": True,
            "competitive_advantage": True, "long_term_strategic_asset": True,
            "all_4_satisfied": True,
        })

    def test_missing_pain_evidence_rejects_even_with_payment_evidence_and_high_score(self):
        result = po.ladder_opportunity_score(self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path)
        self.assertFalse(result["accepted"])
        self.assertIn("PAIN NOT ESTABLISHED", result["reason"])
        self.assertFalse(result["strategic_doctrine_v2"]["pain_severity"])

    def test_pain_evidence_below_the_real_severity_floor_still_rejects(self):
        # _score_urgency: score = wtp*25 + pain*10; 1 pain hit alone = 10,
        # below the 25 floor -- real evidence that doesn't clear urgency's
        # own "منخفضة" (low) band must not pass the gate either.
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(pain_hits=1, wtp_hits=0),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("PAIN NOT ESTABLISHED", result["reason"])

    def test_no_ai_leverage_keywords_rejects_on_competitive_advantage(self):
        # Real niche text with zero AI_LEVERAGE_HIGH/LOW_KEYWORDS matches ->
        # ai_leverage stays genuinely Unknown, same "absence of evidence
        # never defaults to a pass" principle as every other gate here.
        niche = "zzz neutral placeholder niche text"
        _seed_payment_evidence(niche, self.evidence_path, n=1)
        result = po.ladder_opportunity_score(
            niche, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("NO PROVEN COMPETITIVE ADVANTAGE", result["reason"])
        self.assertIsNone(result["ai_leverage"]["score"])

    def test_physical_task_niche_rejects_on_competitive_advantage(self):
        # A real, net-negative ai_leverage niche (physical/logistics
        # keywords outweigh AI-suitable ones) -- proves the gate rejects a
        # genuinely poor AI fit, not just an Unknown one.
        niche = "warehouse physical delivery logistics manual shipping coordination"
        _seed_payment_evidence(niche, self.evidence_path, n=1)
        result = po.ladder_opportunity_score(
            niche, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("NO PROVEN COMPETITIVE ADVANTAGE", result["reason"])
        self.assertLess(result["ai_leverage"]["score"], 50)

    def test_non_durable_ladder_rejects_on_long_term_strategic_asset(self):
        # kdp_books: recurring=10, reusability=20 -- both real, both far
        # below the 55/55 durability floor, regardless of every other gate.
        _seed_payment_evidence(self.NICHE, self.evidence_path, n=1)
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="kdp_books", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("NOT A DURABLE STRATEGIC ASSET", result["reason"])
        self.assertFalse(result["strategic_doctrine_v2"]["long_term_strategic_asset"])

    def test_durable_ladders_clear_the_strategic_asset_gate(self):
        for ladder in ("ai_saas", "b2b_systems", "automation_tools"):
            with self.subTest(ladder=ladder):
                result = po.ladder_opportunity_score(
                    self.NICHE, ladder=ladder, evidence_path=self.evidence_path,
                    external_signal=_pain_evidence_signal(),
                )
                self.assertTrue(result["strategic_doctrine_v2"]["long_term_strategic_asset"], result)

    def test_gates_are_checked_in_the_founders_own_hierarchy_order(self):
        """Proof of Payment -> Pain -> Competitive Advantage -> Strategic
        Asset. Zero payment evidence must report UNPROVEN even when every
        other condition would also independently fail."""
        empty_path = _temp_evidence_path()
        try:
            result = po.ladder_opportunity_score("zzz neutral placeholder niche text", ladder="kdp_books", evidence_path=empty_path)
            self.assertIn("UNPROVEN", result["reason"])
        finally:
            if os.path.exists(empty_path):
                os.remove(empty_path)


class TestGalaxyForgeProductStrategy(unittest.TestCase):
    """ADR-126 (2026-07-25): the founder's 10-condition GALAXY FORGE
    PRODUCT STRATEGY checklist. 3 new hard gates on top of ADR-121/122's
    4 (competition, defensibility/"difficult to copy", margin) -- each
    independently provable, same discipline as TestStrategicDoctrineV2.
    A niche/ladder engineered to pass every other gate still rejects on
    exactly the one condition under test."""

    NICHE = "AI-powered compliance automation subscription system for accounting firms"

    def setUp(self):
        self.evidence_path = _temp_evidence_path()
        _seed_payment_evidence(self.NICHE, self.evidence_path, n=1)
        _patch_defensibility_pass(self)

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    @patch("profit_oracle._score_competition", return_value=(30, ["real test fixture: saturated market"]))
    def test_strong_competition_rejects_on_low_or_moderate_competition(self, mock_competition):
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("COMPETITION TOO STRONG", result["reason"])
        self.assertFalse(result["product_strategy"]["low_or_moderate_competition"])

    def test_low_defensibility_rejects_on_difficult_to_copy(self):
        with patch("profit_oracle._score_defensibility", return_value=(25, "منخفضة", "real test fixture: crowded with strong competitors")):
            result = po.ladder_opportunity_score(
                self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
                external_signal=_pain_evidence_signal(),
            )
        self.assertFalse(result["accepted"])
        self.assertIn("NOT DIFFICULT TO COPY", result["reason"])
        self.assertFalse(result["product_strategy"]["difficult_to_copy"])

    def test_unknown_defensibility_rejects_on_difficult_to_copy_absence_is_never_a_pass(self):
        with patch("profit_oracle._score_defensibility", return_value=(None, "Unknown", "real test fixture: no cached competitor data")):
            result = po.ladder_opportunity_score(
                self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
                external_signal=_pain_evidence_signal(),
            )
        self.assertFalse(result["accepted"])
        self.assertIn("NOT DIFFICULT TO COPY", result["reason"])

    @patch("profit_oracle._score_margin", return_value=(20, ["real test fixture: thin margin"], 150))
    def test_low_margin_rejects_on_high_profit_margin(self, mock_margin):
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("MARGIN TOO LOW", result["reason"])
        self.assertFalse(result["product_strategy"]["high_profit_margin"])

    def test_all_8_gateable_conditions_satisfied_is_accepted(self):
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertTrue(result["accepted"], result)
        ps = result["product_strategy"]
        self.assertTrue(ps["strong_proof_of_payment"])
        self.assertTrue(ps["low_or_moderate_competition"])
        self.assertTrue(ps["difficult_to_copy"])
        self.assertTrue(ps["premium_pricing_potential"])
        self.assertTrue(ps["global_scalability"])
        self.assertTrue(ps["long_term_strategic_value"])
        self.assertTrue(ps["ai_significant_advantage"])
        self.assertTrue(ps["high_profit_margin"])
        self.assertTrue(ps["all_gateable_satisfied"])

    def test_global_scalability_is_the_same_real_signal_as_long_term_strategic_value_not_a_second_computation(self):
        """ADR-126: "Global Scalability" has no independent signal -- it
        reuses the identical reusability-driven durable-asset boolean,
        never a separately-computed duplicate."""
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertEqual(result["product_strategy"]["global_scalability"], result["product_strategy"]["long_term_strategic_value"])

    def test_high_commercial_value_and_continuous_improvement_are_honestly_unknown_never_gated(self):
        """ADR-126's own audit: no real per-opportunity signal exists for
        these 2 of the 10 named conditions anywhere in this factory --
        they must read Unknown, never a fabricated Yes/No, and must never
        block acceptance (an 8-gate pass with these 2 Unknown still
        accepts)."""
        result = po.ladder_opportunity_score(
            self.NICHE, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        ps = result["product_strategy"]
        self.assertEqual(ps["high_commercial_value"]["answer"], "Unknown")
        self.assertEqual(ps["continuous_improvement_potential"]["answer"], "Unknown")
        self.assertTrue(result["accepted"], "2 honestly-Unknown conditions must never block acceptance of an otherwise fully-gated niche")


class TestRealCandidatesDifferentiate(unittest.TestCase):
    """Real, unmocked niches. Under the Proof of Payment doctrine these
    are UNPROVEN with zero recorded evidence — proving that, and proving
    the plain-KDP niche stays rejected even once evidence is supplied, are
    both real, meaningful assertions post-ADR-121."""

    def setUp(self):
        self.evidence_path = _temp_evidence_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_ai_saas_candidate_is_unproven_without_real_evidence(self):
        result = po.ladder_opportunity_score(
            "AI-powered compliance automation subscription system for accounting firms",
            ladder="ai_saas", evidence_path=self.evidence_path,
        )
        self.assertFalse(result["accepted"])
        self.assertIn("UNPROVEN", result["reason"])

    def test_ai_saas_candidate_is_accepted_once_real_evidence_exists(self):
        _patch_defensibility_pass(self)
        niche = "AI-powered compliance automation subscription system for accounting firms"
        _seed_payment_evidence(niche, self.evidence_path, n=1)
        result = po.ladder_opportunity_score(
            niche, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertTrue(result["accepted"], result)
        self.assertGreaterEqual(result["price"], po.MIN_LADDER_PROFIT_FLOOR)

    def test_plain_kdp_printable_is_rejected_even_with_evidence(self):
        niche = "printable monthly planner"
        _seed_payment_evidence(niche, self.evidence_path, n=3)
        result = po.ladder_opportunity_score(niche, ladder="kdp_books", evidence_path=self.evidence_path)
        self.assertFalse(result["accepted"])
        self.assertNotIn("UNPROVEN", result["reason"], "must be rejected on score, not on missing evidence, once evidence is supplied")


class TestProfitFloorIndependentOfScore(unittest.TestCase):
    """Mission requirement: reject anything below the $97 profit floor
    regardless of how well it otherwise scores — a separate gate, not
    folded into the weighted formula. Real evidence is seeded first so
    each test exercises the price/score floor it names, not the (now
    logically prior) payment-evidence gate."""

    def setUp(self):
        self.evidence_path = _temp_evidence_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    @patch("profit_oracle.butter_price", return_value=50)
    def test_high_scoring_niche_still_rejected_below_price_floor(self, mock_price):
        # "reporting" is a real AI_LEVERAGE_HIGH_KEYWORDS hit -- clears the
        # Competitive Advantage gate (ADR-122) so this test isolates the
        # price floor specifically, not an incidental earlier-gate failure.
        _patch_defensibility_pass(self)
        niche = "premium subscription enterprise automation reporting system"
        _seed_payment_evidence(niche, self.evidence_path, n=3)
        result = po.ladder_opportunity_score(
            niche, ladder="ai_saas", evidence_path=self.evidence_path,
            external_signal=_pain_evidence_signal(),
        )
        self.assertGreaterEqual(result["ladder_score"], po.LADDER_MIN_SCORE)
        self.assertFalse(result["accepted"])
        self.assertIn("profit floor", result["reason"])

    @patch("profit_oracle.butter_price", return_value=200)
    def test_price_above_floor_does_not_by_itself_force_acceptance(self, mock_price):
        """A high price alone must not override a weak ladder_score."""
        niche = "x"
        _seed_payment_evidence(niche, self.evidence_path, n=3)
        result = po.ladder_opportunity_score(niche, ladder="kdp_books", evidence_path=self.evidence_path)
        self.assertLess(result["ladder_score"], po.LADDER_MIN_SCORE)
        self.assertFalse(result["accepted"])


class TestTimeToMarket(unittest.TestCase):
    """Global Opportunity Intelligence extension (2026-07-23): a real,
    deterministic check against product_families.registry's real
    registration state -- never a guessed day/week estimate, and never
    factored into ladder_score/accepted. Independent of the payment-
    evidence gate, so no evidence needs to be seeded here."""

    def setUp(self):
        self.evidence_path = _temp_evidence_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_never_changes_ladder_score_or_accepted(self):
        result = po.ladder_opportunity_score("a real test niche", ladder="kdp_books", evidence_path=self.evidence_path)
        self.assertIn("time_to_market", result)
        self.assertEqual(
            result["ladder_score"],
            po.ladder_opportunity_score("a real test niche", ladder="kdp_books", evidence_path=self.evidence_path)["ladder_score"],
        )

    def test_immediate_for_a_ladder_with_a_real_registered_adapter(self):
        # kdp_books has a real, registered product_families adapter
        # (product_families/families/kdp_books.py) -- confirmed live
        # elsewhere this session, not assumed here.
        result = po.ladder_opportunity_score("a real test niche", ladder="kdp_books", evidence_path=self.evidence_path)
        self.assertEqual(result["time_to_market"]["level"], "فوري")
        self.assertEqual(result["time_to_market"]["score"], 100)

    def test_requires_new_engineering_when_no_adapter_is_registered(self):
        with patch.object(po.PRODUCT_FAMILY_REGISTRY, "get", return_value=None):
            result = po.ladder_opportunity_score("a real test niche", ladder="kdp_books", evidence_path=self.evidence_path)
        self.assertEqual(result["time_to_market"]["level"], "يتطلب هندسة جديدة")
        self.assertLess(result["time_to_market"]["score"], 50)

    def test_unknown_when_product_families_is_unavailable(self):
        with patch.object(po, "PRODUCT_FAMILY_REGISTRY", None):
            result = po.ladder_opportunity_score("a real test niche", ladder="kdp_books", evidence_path=self.evidence_path)
        self.assertEqual(result["time_to_market"]["level"], "Unknown")
        self.assertIsNone(result["time_to_market"]["score"])


class TestScoreUrgencyRealShape(unittest.TestCase):
    """Real bug found and fixed (2026-08-06, "EXECUTION MODE" first-revenue
    attempt): market_intelligence_engine.analyze_customer_pain()'s real,
    tested return shape always nests willingness_to_pay_hits/
    pain_language_hits under a "real_evidence" sub-dict -- _score_urgency()
    was reading them at the top level instead, so every real caller that
    ever passed a REAL analyze_customer_pain() result through here
    silently got "Unknown" regardless of real evidence found. No prior
    real caller had ever exercised this path end-to-end (confirmed by
    repo-wide search) before this was caught. Fixed to read the real
    nested shape, falling back to a flat top-level shape for backward
    compatibility with this file's own pre-existing _pain_evidence_signal()
    fixture."""

    def test_real_analyze_customer_pain_shape_is_read_correctly(self):
        real_shaped_pain = {
            "pain_score": 8, "confidence": "medium",
            "real_evidence": {"pain_language_hits": 2, "willingness_to_pay_hits": 1},
        }
        score, level, reason = po._score_urgency("a niche", external_signal={"customer_pain": real_shaped_pain})
        self.assertEqual(score, 45)  # 1*25 + 2*10
        self.assertEqual(level, "متوسطة")

    def test_legacy_flat_shape_still_works(self):
        score, level, reason = po._score_urgency("a niche", external_signal=_pain_evidence_signal(pain_hits=1, wtp_hits=1))
        self.assertEqual(score, 35)  # 1*25 + 1*10
        self.assertEqual(level, "متوسطة")

    def test_real_zero_hits_is_a_real_low_score_not_unknown(self):
        """The exact real scenario this bug hid: analyze_customer_pain()
        genuinely found real GitHub issues but 0 real pain-language/WTP
        keyword matches -- a real, honest low signal, never "Unknown"
        (which would wrongly suggest no evidence was ever gathered)."""
        real_shaped_pain = {"pain_score": 8, "real_evidence": {"pain_language_hits": 0, "willingness_to_pay_hits": 0}}
        score, level, reason = po._score_urgency("a niche", external_signal={"customer_pain": real_shaped_pain})
        self.assertEqual(score, 0)
        self.assertEqual(level, "منخفضة")
        self.assertNotEqual(level, "Unknown")

    def test_no_evidence_at_all_is_honestly_unknown(self):
        score, level, reason = po._score_urgency("a niche", external_signal=None)
        self.assertIsNone(score)
        self.assertEqual(level, "Unknown")


if __name__ == "__main__":
    unittest.main()

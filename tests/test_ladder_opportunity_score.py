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
        niche = "AI-powered compliance automation subscription system for accounting firms"
        _seed_payment_evidence(niche, self.evidence_path, n=1, event_type="paid_job_posting")
        result = po.ladder_opportunity_score(niche, ladder="ai_saas", evidence_path=self.evidence_path)
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
        niche = "AI-powered compliance automation subscription system for accounting firms"
        _seed_payment_evidence(niche, self.evidence_path, n=1)
        result = po.ladder_opportunity_score(niche, ladder="ai_saas", evidence_path=self.evidence_path)
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
        niche = "premium subscription enterprise automation system"
        _seed_payment_evidence(niche, self.evidence_path, n=3)
        result = po.ladder_opportunity_score(niche, ladder="ai_saas", evidence_path=self.evidence_path)
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


if __name__ == "__main__":
    unittest.main()

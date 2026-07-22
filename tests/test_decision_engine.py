"""Tests for decision_engine/ (ADR-050).

Runs with stdlib unittest. Every network-calling function inherited from
market_intelligence_core/competitor_discovery/market_intelligence_engine
is mocked throughout — this suite never depends on live API availability.

    python -m unittest tests.test_decision_engine -v
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

from decision_engine import engine, feedback, learning, ranking, store
from decision_engine.types import Decision, Outcome, make_decision_id


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestMakeDecisionId(unittest.TestCase):
    def test_deterministic_same_inputs_same_id(self):
        self.assertEqual(
            make_decision_id("niche a", "tier4", "2026-07-16T00:00:00"),
            make_decision_id("niche a", "tier4", "2026-07-16T00:00:00"),
        )

    def test_different_inputs_different_id(self):
        self.assertNotEqual(
            make_decision_id("niche a", "tier4", "2026-07-16T00:00:00"),
            make_decision_id("niche b", "tier4", "2026-07-16T00:00:00"),
        )


class TestStoreNeverOverwrites(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def _decision(self, niche, status, decided_at):
        return Decision(
            decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
            decided_at=decided_at, status=status, ai_ceo_decision="WAIT",
            opportunity_score=50.0, opportunity_score_accepted=False,
            reasoning=["test"], evaluation_snapshot={},
        )

    def test_multiple_decisions_for_same_niche_all_preserved(self):
        store.append_decision(self._decision("x", "DEFERRED", "2026-07-01T00:00:00"), path=self.path)
        store.append_decision(self._decision("x", "REJECTED", "2026-07-15T00:00:00"), path=self.path)
        history = store.find_decisions_by_niche("x", path=self.path)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["status"], "DEFERRED")
        self.assertEqual(history[1]["status"], "REJECTED")

    def test_latest_decision_per_niche_picks_the_most_recent(self):
        store.append_decision(self._decision("x", "DEFERRED", "2026-07-01T00:00:00"), path=self.path)
        store.append_decision(self._decision("x", "REJECTED", "2026-07-15T00:00:00"), path=self.path)
        latest = store.latest_decision_per_niche(path=self.path)
        self.assertEqual(latest["x"]["status"], "REJECTED")

    def test_rejected_niche_remains_searchable(self):
        store.append_decision(self._decision("a rejected niche", "REJECTED", "2026-07-01T00:00:00"), path=self.path)
        self.assertEqual(len(store.find_decisions_by_niche("a rejected niche", path=self.path)), 1)

    def test_missing_file_reads_as_empty_never_throws(self):
        self.assertEqual(list(store.read_decisions(path="/no/such/decisions.jsonl")), [])


class TestEvaluateAndDecide(unittest.TestCase):
    """competitor_discovery.COMPETITOR_DB_FILE is redirected (2026-07-16
    fix): get_or_refresh_competitors() writes to it even with the network
    query itself mocked — without this, every run of this class was
    appending a real entry to the live data/competitor_database.json."""

    def setUp(self):
        self.decisions_path = _temp_path()
        self.analysis_db_path = _temp_path()
        self.competitor_db_path = _temp_path(suffix=".json")
        patcher1 = patch("competitor_discovery._query_hn", return_value=[])
        patcher2 = patch("competitor_discovery._query_github", return_value=[])
        patcher3 = patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0))
        patcher4 = patch("market_intelligence_engine._query_github_issues", return_value=([], 0))
        patcher5 = patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path)
        # Opportunity Rejection Investigation (2026-07-22): reformulate_pain_
        # query() now makes a real Groq call and _query_stack_overflow_for_pain()
        # a real network call unless mocked.
        patcher6 = patch("market_intelligence_engine.reformulate_pain_query", return_value=("test", "literal_fallback", None))
        patcher7 = patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0))
        for p in (patcher1, patcher2, patcher3, patcher4, patcher5, patcher6, patcher7):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        for p in (self.decisions_path, self.analysis_db_path, self.competitor_db_path):
            if os.path.exists(p):
                os.remove(p)

    def test_weak_generic_niche_is_rejected_with_explicit_reasoning(self):
        d = engine.evaluate_and_decide("كتاب", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path)
        self.assertIn(d.status, ("REJECTED", "DEFERRED"))
        self.assertGreater(len(d.reasoning), 0)
        self.assertTrue(all(isinstance(r, str) for r in d.reasoning))

    def test_empty_niche_is_rejected_honestly(self):
        d = engine.evaluate_and_decide("", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path)
        self.assertEqual(d.status, "REJECTED")

    def test_decision_is_persisted_and_reproducible_via_evaluation_snapshot(self):
        d = engine.evaluate_and_decide("a reproducibility test niche", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path)
        history = store.find_decisions_by_niche("a reproducibility test niche", path=self.decisions_path)
        self.assertEqual(len(history), 1)
        self.assertIn("dimension_scores", history[0]["evaluation_snapshot"])
        self.assertIn("ai_ceo", history[0]["evaluation_snapshot"])

    # ADR-076 (Decision Surface Reconciliation) — ladder-aware evaluate_and_decide()

    def test_omitting_ladder_reproduces_exact_prior_behavior(self):
        d = engine.evaluate_and_decide("a reproducibility test niche", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path)
        self.assertIsNone(d.ladder)
        self.assertEqual(d.to_dict()["decision_path"], "ai_ceo_full_evaluation")

    def test_ladder_argument_uses_ladder_opportunity_score_not_old_gate(self):
        d = engine.evaluate_and_decide(
            "AI-powered compliance automation subscription system for accounting firms",
            ladder="ai_saas", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path,
        )
        self.assertEqual(d.ladder, "ai_saas")
        self.assertTrue(any("Ladder Opportunity Score (ADR-066)" in r for r in d.reasoning))

    def test_ladder_decision_recorded_with_ladder_field_populated(self):
        engine.evaluate_and_decide(
            "workflow automation system for logistics companies",
            ladder="b2b_systems", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path,
        )
        history = store.find_decisions_by_niche("workflow automation system for logistics companies", path=self.decisions_path)
        self.assertEqual(history[0]["ladder"], "b2b_systems")

    def test_ladder_components_scalability_and_recurring_revenue_are_persisted(self):
        """Opportunity Rejection Investigation (2026-07-22), mission point 7:
        an accepted opportunity must include scalability + long-term
        strategic value. ladder_opportunity_score()'s recurring_revenue_
        potential/reusability were computed but silently discarded before
        this fix -- same pattern as record_ladder_decision()/
        analyze_opportunity(), fixed the same day."""
        d = engine.evaluate_and_decide(
            "workflow automation system for logistics companies",
            ladder="b2b_systems", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path,
        )
        components = d.evaluation_snapshot.get("ladder_components")
        self.assertIsNotNone(components)
        self.assertIn("reusability", components)
        self.assertIn("recurring_revenue_potential", components)

    def test_no_ladder_means_no_ladder_components_key_never_a_fabricated_one(self):
        d = engine.evaluate_and_decide("a reproducibility test niche", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path)
        self.assertNotIn("ladder_components", d.evaluation_snapshot)

    def test_status_derivation_build_and_accepted_is_accepted(self):
        self.assertEqual(engine._derive_status("BUILD", True), "ACCEPTED")

    def test_status_derivation_build_but_not_accepted_is_deferred(self):
        self.assertEqual(engine._derive_status("BUILD", False), "DEFERRED")

    def test_status_derivation_reject_is_rejected(self):
        self.assertEqual(engine._derive_status("REJECT", True), "REJECTED")

    def test_status_derivation_pivot_is_rejected(self):
        self.assertEqual(engine._derive_status("PIVOT", True), "REJECTED")

    def test_status_derivation_wait_is_deferred(self):
        self.assertEqual(engine._derive_status("WAIT", True), "DEFERRED")

    def test_status_derivation_improve_is_deferred(self):
        self.assertEqual(engine._derive_status("IMPROVE", True), "DEFERRED")

    # Packaging Architecture Plan §1 (Phase A, 2026-07-18) — product_family

    def test_omitting_product_family_resolves_from_ladder_default_table(self):
        d = engine.evaluate_and_decide(
            "workflow automation system for logistics companies",
            ladder="b2b_systems", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path,
        )
        self.assertEqual(d.product_family, "automation_systems")

    def test_explicit_product_family_overrides_the_default_table(self):
        d = engine.evaluate_and_decide(
            "AI-powered compliance automation subscription system for accounting firms",
            ladder="ai_saas", product_family="knowledge_bases",
            decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path,
        )
        self.assertEqual(d.product_family, "knowledge_bases")

    def test_no_ladder_no_product_family_reproduces_prior_behavior(self):
        d = engine.evaluate_and_decide("a reproducibility test niche", decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path)
        self.assertIsNone(d.product_family)

    def test_reasoning_reuses_profit_oracles_own_reason_never_rederives_it(self):
        """Zero-assumption audit follow-up (High finding): evaluate_and_decide()
        used to rebuild its own 'opportunity_score >= min_required' string
        from composite['opportunity_score'] (tier-weighted) vs the flat
        MIN_OPPORTUNITY_SCORE constant — a second, independent copy of the
        exact bug already fixed in profit_oracle.opportunity_score()'s own
        `reason` field (which correctly compares raw vs. tier-adjusted
        raw_floor instead). This already produced real, false-inequality
        text in data/decisions.jsonl for real tier1 records (e.g.
        "88.6/100, < 65" for a value that is not, in fact, less than 65).
        Fixed by reusing composite['reason'] directly — this test proves
        that reuse, not just that *a* string exists."""
        # precomputed_analysis bypasses market_intelligence_core.evaluate_opportunity()
        # entirely (that path independently calls profit_oracle for its own
        # scoring, unrelated to this test — patching profit_oracle globally
        # would break that unrelated call too). This isolates exactly the
        # reasoning-construction logic under test.
        fake_analysis = {
            "niche": "مثال اختبار",
            "analyzed_at": "2026-07-17T00:00:00",
            "ai_ceo": {"decision": "BUILD", "evidence": ["real evidence line"]},
        }
        with patch("decision_engine.engine.profit_oracle.opportunity_score") as mock_score:
            mock_score.return_value = {
                "opportunity_score": 69.5,
                "accepted": False,
                "min_required": 65,
                "reason": "rejected: opportunity_score 69.5/100 (raw 69.5 < 81.2 floor, tier=tier3)",
            }
            d = engine.evaluate_and_decide(
                "مثال اختبار", tier="tier3", precomputed_analysis=fake_analysis,
                decisions_path=self.decisions_path, analysis_db_file=self.analysis_db_path,
            )
        joined = " ".join(d.reasoning)
        self.assertIn("raw 69.5 < 81.2 floor", joined, "must reuse profit_oracle's own real comparison, not re-derive one")
        self.assertNotIn("69.5/100, < 65", joined, "must never rebuild the old, potentially-false flat-constant comparison")


class TestRecordLadderDecision(unittest.TestCase):
    """ADR-076 (Decision Surface Reconciliation) — the fast-path recorder
    market_hunter.py calls for every real candidate it scans, writing into
    the exact same single source of truth (data/decisions.jsonl) the full
    AI-CEO evaluate_and_decide() path above writes to."""

    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_accepted_ladder_result_recorded_as_accepted(self):
        ladder_result = {"accepted": True, "ladder_score": 85.3, "price": 388, "reason": "accepted: test", "components": {}}
        d = engine.record_ladder_decision("test niche", "ai_saas", ladder_result, decisions_path=self.decisions_path)
        self.assertEqual(d.status, "ACCEPTED")
        self.assertEqual(d.ladder, "ai_saas")
        self.assertEqual(d.decision_path, "ladder_fast_gate")
        self.assertEqual(d.ai_ceo_decision, "N/A")
        self.assertEqual(d.opportunity_score, 85.3)

    def test_rejected_ladder_result_recorded_as_rejected_never_dropped(self):
        ladder_result = {"accepted": False, "ladder_score": 40.1, "price": 67, "reason": "rejected: test", "components": {}}
        d = engine.record_ladder_decision("test niche 2", "kdp_books", ladder_result, decisions_path=self.decisions_path)
        self.assertEqual(d.status, "REJECTED")
        history = store.find_decisions_by_niche("test niche 2", path=self.decisions_path)
        self.assertEqual(len(history), 1, "a rejected fast-path decision must remain searchable, same guarantee as the AI-CEO path")

    def test_never_recomputes_the_score_reuses_the_caller_supplied_result_verbatim(self):
        """The whole point: this must never silently disagree with the
        score the real caller (market_hunter.py) already acted on."""
        ladder_result = {"accepted": True, "ladder_score": 99.9, "price": 500, "reason": "accepted: verbatim check", "components": {"market_demand": 1}}
        d = engine.record_ladder_decision("verbatim niche", "ai_saas", ladder_result, decisions_path=self.decisions_path)
        self.assertEqual(d.opportunity_score, 99.9)
        self.assertEqual(d.evaluation_snapshot["price"], 500)
        self.assertEqual(d.evaluation_snapshot["components"], {"market_demand": 1})

    # Packaging Architecture Plan §1 (Phase A, 2026-07-18) — product_family

    def test_omitting_product_family_resolves_from_ladder_default_table(self):
        ladder_result = {"accepted": True, "ladder_score": 85.3, "price": 388, "reason": "accepted: test", "components": {}}
        d = engine.record_ladder_decision("test niche", "ai_saas", ladder_result, decisions_path=self.decisions_path)
        self.assertEqual(d.product_family, "ai_saas")

    def test_explicit_product_family_overrides_the_default_table(self):
        ladder_result = {"accepted": True, "ladder_score": 85.3, "price": 388, "reason": "accepted: test", "components": {}}
        d = engine.record_ladder_decision(
            "test niche", "ai_saas", ladder_result, decisions_path=self.decisions_path, product_family="knowledge_bases",
        )
        self.assertEqual(d.product_family, "knowledge_bases")

    def test_risk_confidence_defensibility_are_persisted_not_dropped(self):
        """Opportunity Intelligence Round 2 (2026-07-22): these 3 fields
        were already computed by profit_oracle.ladder_opportunity_score()
        but silently discarded before this fix."""
        ladder_result = {
            "accepted": True, "ladder_score": 85.3, "price": 388, "reason": "accepted: test", "components": {},
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "x"},
            "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "y"},
        }
        d = engine.record_ladder_decision("test niche", "ai_saas", ladder_result, decisions_path=self.decisions_path)
        self.assertEqual(d.evaluation_snapshot["risk"]["score"], 90)
        self.assertEqual(d.evaluation_snapshot["confidence"]["level"], "متوسطة")
        self.assertEqual(d.evaluation_snapshot["defensibility"]["level"], "عالية نسبياً")

    def test_market_signal_and_ai_leverage_are_persisted_proactively(self):
        """Strategic Opportunity Intelligence Engine (2026-07-22): fixed
        proactively this time, before ever shipping the drop."""
        ladder_result = {
            "accepted": True, "ladder_score": 85.3, "price": 388,
            "reason": "accepted: test", "components": {"automation_potential": 40},
            "market_signal": {"score": 60, "level": "مرتفعة", "note": "z"},
            "ai_leverage": {"score": 80, "level": "عالية", "note": "w"},
        }
        d = engine.record_ladder_decision("test niche", "ai_saas", ladder_result, decisions_path=self.decisions_path)
        self.assertEqual(d.evaluation_snapshot["market_signal"]["level"], "مرتفعة")
        self.assertEqual(d.evaluation_snapshot["ai_leverage"]["level"], "عالية")
        self.assertEqual(d.evaluation_snapshot["components"]["automation_potential"], 40)

    def test_missing_risk_confidence_defensibility_degrade_to_none_never_crash(self):
        ladder_result = {"accepted": True, "ladder_score": 85.3, "price": 388, "reason": "accepted: test", "components": {}}
        d = engine.record_ladder_decision("test niche", "ai_saas", ladder_result, decisions_path=self.decisions_path)
        self.assertIsNone(d.evaluation_snapshot["risk"])
        self.assertIsNone(d.evaluation_snapshot["confidence"])
        self.assertIsNone(d.evaluation_snapshot["defensibility"])

    def test_reads_via_the_same_ranking_and_mission_control_path(self):
        """Confirms the actual unification claim: a fast-path decision is
        indistinguishable, to a reader of decision_engine.store/ranking
        (what mission_control_api.py uses), from any other decision."""
        ladder_result = {"accepted": True, "ladder_score": 76.3, "price": 327, "reason": "accepted: b2b test", "components": {}}
        engine.record_ladder_decision("ranking test niche", "b2b_systems", ladder_result, decisions_path=self.decisions_path)
        queue = ranking.rank_queue(decisions_path=self.decisions_path, outcomes_path=_temp_path())
        self.assertTrue(any(d["niche"] == "ranking test niche" for d in queue))


class TestRanking(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def _decision(self, niche, status, score, decided_at="2026-07-16T00:00:00"):
        d = Decision(
            decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
            decided_at=decided_at, status=status, ai_ceo_decision="BUILD",
            opportunity_score=score, opportunity_score_accepted=(status == "ACCEPTED"),
            reasoning=["test"], evaluation_snapshot={"dimension_scores": {}},
        )
        store.append_decision(d, path=self.decisions_path)
        return d

    def test_rank_all_sorts_by_opportunity_score_descending(self):
        self._decision("low", "DEFERRED", 40)
        self._decision("high", "ACCEPTED", 90)
        self._decision("mid", "REJECTED", 60)
        ranked = ranking.rank_all(path=self.decisions_path)
        self.assertEqual([d["niche"] for d in ranked], ["high", "mid", "low"])

    def test_rank_queue_only_includes_accepted_without_a_real_outcome_yet(self):
        d1 = self._decision("accepted no sale", "ACCEPTED", 80)
        d2 = self._decision("accepted with sale", "ACCEPTED", 95)
        self._decision("deferred one", "DEFERRED", 99)

        outcome = Outcome(
            outcome_id="x", decision_id=d2.decision_id, niche=d2.niche,
            recorded_at="2026-07-16T00:00:00", matched=True, match_method="test", raw_sale_event={},
        )
        store.append_outcome(outcome, path=self.outcomes_path)

        queue = ranking.rank_queue(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual([d["niche"] for d in queue], ["accepted no sale"])


class TestFeedbackNeverFabricatesAMatch(unittest.TestCase):
    def setUp(self):
        self.sales_ledger_path = _temp_path()
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.sales_ledger_path, self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_real_sales_reports_honestly(self):
        result = feedback.sync_outcomes(
            sales_ledger_path=self.sales_ledger_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path
        )
        self.assertEqual(result["synced"], 0)
        self.assertIn("لا مبيعات حقيقية", result["reason"])

    def test_real_sale_matched_via_product_id_and_niche_substring(self):
        from channels import ledger as sales_ledger

        d = Decision(
            decision_id=make_decision_id("gratitude journal for teens", "tier4", "2026-07-16T00:00:00"),
            niche="gratitude journal for teens", tier="tier4", decided_at="2026-07-16T00:00:00",
            status="ACCEPTED", ai_ceo_decision="BUILD", opportunity_score=80, opportunity_score_accepted=True,
            reasoning=["test"], evaluation_snapshot={"dimension_scores": {}},
        )
        store.append_decision(d, path=self.decisions_path)

        sales_ledger.append_event({
            "event_type": "publish_attempt", "platform": "gumroad", "ok": True, "dry_run": False,
            "product_id": "prod123", "url": "https://x", "error": None,
            "product_title": "Gratitude Journal For Teens - Deluxe Edition", "product_source_id": "abc",
        }, ledger_path=self.sales_ledger_path)
        sales_ledger.append_event({
            "event_type": "sale", "platform": "gumroad", "raw": {"id": "sale1", "product_id": "prod123", "price": 9.99},
        }, ledger_path=self.sales_ledger_path)

        result = feedback.sync_outcomes(
            sales_ledger_path=self.sales_ledger_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path
        )
        self.assertEqual(result["synced"], 1)
        self.assertEqual(result["matched"], 1)

        outcomes = list(store.read_outcomes(path=self.outcomes_path))
        self.assertEqual(outcomes[0]["decision_id"], d.decision_id)
        self.assertTrue(outcomes[0]["matched"])

    def test_unmatched_sale_still_recorded_honestly_never_dropped(self):
        from channels import ledger as sales_ledger

        sales_ledger.append_event({
            "event_type": "sale", "platform": "gumroad", "raw": {"id": "sale_unknown", "product_id": "unknown_prod"},
        }, ledger_path=self.sales_ledger_path)

        result = feedback.sync_outcomes(
            sales_ledger_path=self.sales_ledger_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path
        )
        self.assertEqual(result["synced"], 1)
        self.assertEqual(result["matched"], 0)
        self.assertEqual(result["unmatched"], 1)

        outcomes = list(store.read_outcomes(path=self.outcomes_path))
        self.assertFalse(outcomes[0]["matched"])
        self.assertIsNone(outcomes[0]["decision_id"])

    def test_resyncing_never_double_records_the_same_real_sale(self):
        from channels import ledger as sales_ledger
        sales_ledger.append_event({
            "event_type": "sale", "platform": "gumroad", "raw": {"id": "sale_dup", "product_id": "x"},
        }, ledger_path=self.sales_ledger_path)

        feedback.sync_outcomes(sales_ledger_path=self.sales_ledger_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        second = feedback.sync_outcomes(sales_ledger_path=self.sales_ledger_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual(second["synced"], 0)
        self.assertEqual(len(list(store.read_outcomes(path=self.outcomes_path))), 1)


class TestLearningNeverFabricatesAccuracy(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_zero_accepted_decisions_reports_insufficient_data(self):
        result = learning.compute_prediction_accuracy(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertIsNone(result["accuracy"])

    def test_accepted_but_zero_matched_outcomes_reports_insufficient_data(self):
        d = Decision(
            decision_id=make_decision_id("x", "tier4", "2026-07-16T00:00:00"), niche="x", tier="tier4",
            decided_at="2026-07-16T00:00:00", status="ACCEPTED", ai_ceo_decision="BUILD",
            opportunity_score=80, opportunity_score_accepted=True, reasoning=["test"], evaluation_snapshot={},
        )
        store.append_decision(d, path=self.decisions_path)
        result = learning.compute_prediction_accuracy(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertIsNone(result["accuracy"])
        self.assertEqual(result["accepted_decisions"], 1)

    def test_recalibration_below_min_samples_reports_not_recalibrated(self):
        result = learning.recalibration_report(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertFalse(result["recalibrated"])

    def test_recalibration_with_enough_real_samples_computes_a_real_difference(self):
        dims_sold = {"demand": {"normalized_score": 90, "confidence": 80, "raw_data": {}, "explanation": ""}}
        dims_not_sold = {"demand": {"normalized_score": 30, "confidence": 80, "raw_data": {}, "explanation": ""}}

        outcome_ids = []
        for i in range(3):
            niche = f"sold niche {i}"
            d = Decision(
                decision_id=make_decision_id(niche, "tier4", "2026-07-16T00:00:00"), niche=niche, tier="tier4",
                decided_at="2026-07-16T00:00:00", status="ACCEPTED", ai_ceo_decision="BUILD",
                opportunity_score=80, opportunity_score_accepted=True, reasoning=["test"],
                evaluation_snapshot={"dimension_scores": dims_sold},
            )
            store.append_decision(d, path=self.decisions_path)
            store.append_outcome(Outcome(
                outcome_id=f"o{i}", decision_id=d.decision_id, niche=niche,
                recorded_at="2026-07-16T00:00:00", matched=True, match_method="test", raw_sale_event={},
            ), path=self.outcomes_path)

        d_not_sold = Decision(
            decision_id=make_decision_id("not sold niche", "tier4", "2026-07-16T00:00:00"), niche="not sold niche", tier="tier4",
            decided_at="2026-07-16T00:00:00", status="ACCEPTED", ai_ceo_decision="BUILD",
            opportunity_score=80, opportunity_score_accepted=True, reasoning=["test"],
            evaluation_snapshot={"dimension_scores": dims_not_sold},
        )
        store.append_decision(d_not_sold, path=self.decisions_path)

        result = learning.recalibration_report(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertTrue(result["recalibrated"])
        self.assertEqual(result["per_dimension"]["demand"]["avg_score_when_sold"], 90.0)
        self.assertEqual(result["per_dimension"]["demand"]["avg_score_when_not_yet_sold"], 30.0)
        self.assertEqual(result["per_dimension"]["demand"]["difference"], 60.0)


if __name__ == "__main__":
    unittest.main()

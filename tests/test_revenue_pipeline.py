"""Tests for revenue_pipeline/ (Phase 6).

Runs with stdlib unittest. No test here ever sets execute=True against
real infrastructure without mocking the underlying subprocess/inspection
calls — nothing here spends real money or touches a real file.

    python -m unittest tests.test_revenue_pipeline -v
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

from decision_engine import store
from decision_engine.types import Decision, make_decision_id

from revenue_pipeline import pipeline, plan


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _accepted_decision(niche="a revenue pipeline test niche", price_str="$19"):
    decided_at = "2026-07-16T10:00:00+00:00"
    return Decision(
        decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
        decided_at=decided_at, status="ACCEPTED", ai_ceo_decision="BUILD",
        opportunity_score=80.0, opportunity_score_accepted=True,
        reasoning=["real evidence"],
        evaluation_snapshot={"pricing": {"recommended_price": price_str, "note": "x"}},
    )


class TestBuildProductionPlan(unittest.TestCase):
    def test_plan_extracts_real_recommended_price(self):
        d = _accepted_decision(price_str="$24.99")
        result = plan.build_production_plan(d.to_dict())
        self.assertEqual(result["recommended_price"], 24.99)

    def test_plan_handles_missing_price_honestly(self):
        d = _accepted_decision()
        d_dict = d.to_dict()
        d_dict["evaluation_snapshot"] = {}
        result = plan.build_production_plan(d_dict)
        self.assertIsNone(result["recommended_price"])

    # ADR-077 (Product Generation Pipeline) — ladder-aware routing

    def test_ladder_tagged_decision_routes_to_paddle_techdoc(self):
        d = _accepted_decision()
        d_dict = d.to_dict()
        d_dict["ladder"] = "ai_saas"
        d_dict["evaluation_snapshot"] = {"price": 388}
        result = plan.build_production_plan(d_dict)
        self.assertEqual(result["recommended_platform"], "paddle")
        self.assertEqual(result["product_type"], "techdoc")
        self.assertEqual(result["recommended_price"], 388)
        # economics/ROI math still uses a real, already-configured band —
        # config/economics.json has no "paddle" entry yet.
        self.assertEqual(result["economics_platform"], "gumroad_elite")

    def test_no_ladder_tag_reproduces_exact_prior_book_gumroad_plan(self):
        d = _accepted_decision(price_str="$19.99")
        result = plan.build_production_plan(d.to_dict())
        self.assertEqual(result["recommended_platform"], "gumroad_digital")
        self.assertEqual(result["product_type"], "book")
        self.assertEqual(result["economics_platform"], "gumroad_digital")


class TestEstimateProductionCost(unittest.TestCase):
    def test_no_logged_cost_is_discovery(self):
        result = plan.estimate_production_cost(log_file="/no/such/ai_cost_log.jsonl")
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_real_logged_cost_is_used(self):
        import json
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_usd": 0.02}) + "\n")
                f.write(json.dumps({"cost_usd": 0.04}) + "\n")
            result = plan.estimate_production_cost(log_file=path)
            self.assertEqual(result["maturity"], "REAL")
            self.assertAlmostEqual(result["estimated_cost_usd"], 0.03, places=6)
            self.assertEqual(result["sample_size"], 2)
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestEstimateRoi(unittest.TestCase):
    def test_missing_price_is_discovery(self):
        result = plan.estimate_roi(None, 0.02)
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_missing_cost_is_discovery(self):
        result = plan.estimate_roi(19.0, None)
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_real_price_and_cost_produce_a_real_roi(self):
        result = plan.estimate_roi(19.0, 0.02)
        self.assertEqual(result["maturity"], "REAL")
        self.assertIn("roi_pct", result)
        self.assertIn("net_profit_after_fees", result)
        # sanity: a $19 digital product's net profit should vastly exceed a $0.02 AI cost
        self.assertGreater(result["roi_pct"], 0)


class TestEstimatePreAcceptanceRoi(unittest.TestCase):
    """EOS Phase 2, Golden Hunter Evolution (2026-07-19): the one real
    ROI signal previously only computed post-acceptance, now usable at
    scoring time via the already-real estimate_production_cost()."""

    def test_no_logged_cost_is_honestly_discovery_not_a_guess(self):
        result = plan.estimate_pre_acceptance_roi(97.0, log_file="/no/such/ai_cost_log.jsonl")
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_real_logged_cost_produces_a_real_roi(self):
        import json
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_usd": 0.02}) + "\n")
            result = plan.estimate_pre_acceptance_roi(97.0, log_file=path)
            self.assertEqual(result["maturity"], "REAL")
            self.assertIn("roi_pct", result)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_never_changes_the_real_accept_reject_gate(self):
        import json
        # This function is purely informational -- confirm it has no
        # side effect on any decision/gate state (it's a pure calculation).
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_usd": 0.02}) + "\n")
            result = plan.estimate_pre_acceptance_roi(97.0, log_file=path)
            self.assertNotIn("accepted", result)
            self.assertNotIn("gate", result)
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestCompareLadderVariants(unittest.TestCase):
    """Strategic Phase 3, Round 1 (2026-07-22): Product Laboratory MVP --
    real per-ladder price/score variants for the SAME niche, compared
    side by side, never auto-selecting a winner."""

    def test_returns_one_variant_per_ladder_rank_by_default(self):
        result = plan.compare_ladder_variants("premium subscription budget planner for professionals")
        self.assertEqual(len(result["variants"]), len(plan.profit_oracle.LADDER_RANKS))
        self.assertEqual({v["ladder"] for v in result["variants"]}, set(plan.profit_oracle.LADDER_RANKS))

    def test_variants_never_auto_select_a_winner(self):
        result = plan.compare_ladder_variants("a niche for winner-selection test")
        self.assertNotIn("winner", result)
        self.assertNotIn("recommended", result)
        self.assertNotIn("selected", result)
        for v in result["variants"]:
            self.assertNotIn("recommended", v)
            self.assertNotIn("selected", v)

    def test_each_variant_carries_a_strategic_investment_layer(self):
        """Strategic Opportunity Intelligence Engine (2026-07-22):
        'evaluate as if acquiring a company' per candidate product line."""
        result = plan.compare_ladder_variants("a niche for strategic layer per variant test", ladders=["ai_saas", "kdp_books"])
        for v in result["variants"]:
            self.assertIn("strategic_investment", v)
            self.assertIn("can_become_premium_digital_asset", v["strategic_investment"])
            self.assertIn("can_evolve_into_software_business", v["strategic_investment"])

    def test_higher_ladder_ranks_get_priced_in_the_elite_band(self):
        result = plan.compare_ladder_variants("a real pricing band comparison niche")
        by_ladder = {v["ladder"]: v for v in result["variants"]}
        self.assertGreater(by_ladder["ai_saas"]["price"], by_ladder["kdp_books"]["price"])

    def test_pre_acceptance_roi_uses_real_logged_cost_when_available(self):
        import json
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_usd": 0.02}) + "\n")
            result = plan.compare_ladder_variants("a real roi comparison niche", log_file=path)
            self.assertTrue(any(v["pre_acceptance_roi"]["maturity"] == "REAL" for v in result["variants"]))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_unknown_ladder_reported_honestly_not_silently_dropped(self):
        result = plan.compare_ladder_variants("a niche", ladders=["ai_saas", "not_a_real_ladder"])
        self.assertEqual(len(result["variants"]), 2)
        bad = next(v for v in result["variants"] if v["ladder"] == "not_a_real_ladder")
        self.assertIn("error", bad)

    def test_sorted_by_ladder_score_descending(self):
        result = plan.compare_ladder_variants("a niche for sort-order test")
        scores = [v["ladder_score"] for v in result["variants"] if "ladder_score" in v]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestRunRevenuePipeline(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.analysis_db_path = _temp_path()
        self.board_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.timeline_path, self.outcomes_path, self.analysis_db_path, self.board_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_accepted_opportunities_reports_honestly(self):
        result = pipeline.run_revenue_pipeline(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual(result["processed"], 0)
        self.assertIn("reason", result)

    def test_default_never_executes_real_production(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        result = pipeline.run_revenue_pipeline(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
            board_path=self.board_path,
        )
        self.assertEqual(result["processed"], 1)
        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["quality_validation"]["maturity"], "DISCOVERY")

    def test_accepted_opportunity_produces_a_full_result_shape(self):
        d = _accepted_decision(price_str="$19")
        store.append_decision(d, path=self.decisions_path)
        result = pipeline.run_revenue_pipeline(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
            board_path=self.board_path,
        )
        r = result["results"][0]
        for key in ("production_plan", "quality_validation", "business_lifecycle",
                    "time_to_market", "production_cost", "expected_roi", "board_brief"):
            self.assertIn(key, r)

    def test_board_brief_is_isolated_and_honest_with_no_real_meeting(self):
        """Executive Board Integration (2026-07-23): informational only
        (founder decision) -- attached but never gates execute=. Reads
        board_path in isolation, never the live default board_meetings.jsonl."""
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        result = pipeline.run_revenue_pipeline(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
            board_path=self.board_path,
        )
        self.assertFalse(result["results"][0]["board_brief"]["has_meeting"])
        self.assertFalse(os.path.exists(self.board_path), "a read-only lookup must never create the board log")

    def test_ceo_report_renders_without_error_for_empty_queue(self):
        result = pipeline.run_revenue_pipeline(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        report = pipeline.render_ceo_revenue_report(result)
        self.assertIn("لا نشاط إيراد اليوم", report)

    def test_ceo_report_renders_without_error_for_a_real_accepted_opportunity(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        result = pipeline.run_revenue_pipeline(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        report = pipeline.render_ceo_revenue_report(result)
        self.assertIn(d.niche, report)

    @patch("orchestrator.orchestrator.run_cycle")
    def test_execute_true_calls_the_real_orchestrator_with_execute_production_true(self, mock_run_cycle):
        mock_run_cycle.return_value = []
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        pipeline.run_revenue_pipeline(
            execute=True, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, analysis_db_file=self.analysis_db_path, board_path=self.board_path,
        )
        self.assertTrue(mock_run_cycle.called)
        self.assertTrue(mock_run_cycle.call_args.kwargs["execute_production"])

    @patch("orchestrator.orchestrator.run_cycle")
    def test_real_bug_2026_07_22_execute_reuses_the_already_recorded_decision(self, mock_run_cycle):
        """Full Factory Integrity Audit (2026-07-22): process_opportunity()
        used to re-run market_intelligence+decision for a niche that
        market_hunter.py had ALREADY accepted for real, via the exact same
        decision-path divergence bug found earlier this session (a stricter
        re-evaluation could DEFER an already-ACCEPTED niche, producing zero
        output and a second, orphaned decision record). orchestrator.py's
        own docstring names existing_decision= as "the real safeguard
        against recording two independent decisions... for the same real
        opportunity" -- process_opportunity() just wasn't passing it."""
        mock_run_cycle.return_value = []
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        pipeline.run_revenue_pipeline(
            execute=True, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, analysis_db_file=self.analysis_db_path, board_path=self.board_path,
        )
        self.assertTrue(mock_run_cycle.called)
        passed_decision = mock_run_cycle.call_args.kwargs.get("existing_decision")
        self.assertIsNotNone(passed_decision)
        self.assertEqual(passed_decision["niche"], d.niche)
        self.assertEqual(passed_decision["decision_id"], d.decision_id)


if __name__ == "__main__":
    unittest.main()

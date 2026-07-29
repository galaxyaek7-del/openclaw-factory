"""Tests for capital_allocation_engine.py (Capital Allocation Engine
directive, 2026-07-29): the 14-dimension Investment Score citation
layer. Every real source is mocked -- strategic_score()'s own logic has
its own isolated unit tests in tests/test_strategic_intelligence_core.py,
value_engine.compute_value_profile()'s in tests/test_value_engine.py.

    python -m unittest tests.test_capital_allocation_engine -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import capital_allocation_engine as cae

_FAKE_STRATEGIC_SCORE = {
    "niche": "n",
    "market": {"value": "strong", "source": "s", "reason": None},
    "competition": {"value": 70, "source": "s", "reason": None},
    "demand": {"value": "Unknown", "source": "s", "reason": "x"},
    "difficulty": {"value": "Unknown", "source": "s", "reason": "x"},
    "automation": {"value": 40, "source": "s", "reason": None},
    "scalability": {"value": 85, "source": "s", "reason": None},
    "recurring_revenue": {"value": 85, "source": "s", "reason": None},
    "strategic_value": {"value": 47.0, "source": "s", "reason": "avg"},
    "risk": {"value": "not_flagged", "source": "s", "reason": "no signals"},
    "trust": {"value": 20, "source": "s", "reason": None},
    "long_term_value": {"value": "Uncertain", "source": "s", "reason": "layer note"},
    "generated_at": "t",
}


class TestKnowledgeReuseCitation(unittest.TestCase):
    def test_unknown_knowledge_accumulation_is_honestly_unknown(self):
        dims = {"knowledge_accumulation": {"answer": "Unknown", "reason": "no data"}}
        result = cae._knowledge_reuse_citation(dims)
        self.assertEqual(result["value"], "Unknown")
        self.assertEqual(result["reason"], "no data")

    def test_folds_real_synergy_and_bundle_into_the_reason(self):
        dims = {
            "knowledge_accumulation": {"score": 2, "level": "مرتفعة", "note": "2/3 مصادر"},
            "synergy_with_existing_products": {"sibling_count": 1, "note": "1 منتج شقيق"},
            "bundle_potential": {"eligible": False, "sibling_count": 1, "note": "يحتاج 2"},
        }
        result = cae._knowledge_reuse_citation(dims)
        self.assertEqual(result["value"], "مرتفعة")
        self.assertIn("تآزر", result["reason"])
        self.assertIn("حزمة", result["reason"])

    def test_unknown_synergy_and_bundle_are_excluded_from_the_reason(self):
        dims = {
            "knowledge_accumulation": {"score": 0, "level": "منخفضة", "note": "0/3 مصادر"},
            "synergy_with_existing_products": {"answer": "Unknown", "reason": "no ladder"},
            "bundle_potential": {"answer": "Unknown", "reason": "no ladder"},
        }
        result = cae._knowledge_reuse_citation(dims)
        self.assertNotIn("تآزر", result["reason"])
        self.assertNotIn("حزمة", result["reason"])


class TestEngineeringCostCitation(unittest.TestCase):
    def test_real_maturity_cites_the_real_cost(self):
        board = {"estimated_build_cost": {"maturity": "REAL", "estimated_cost_usd": 0.0001, "sample_size": 139}}
        result = cae._engineering_cost_citation(board)
        self.assertEqual(result["value"], 0.0001)
        self.assertIn("139", result["reason"])

    def test_discovery_maturity_is_honestly_unknown(self):
        board = {"estimated_build_cost": {"maturity": "DISCOVERY", "reason": "no calls logged"}}
        result = cae._engineering_cost_citation(board)
        self.assertEqual(result["value"], "Unknown")
        self.assertEqual(result["reason"], "no calls logged")


class TestInvestmentScore(unittest.TestCase):
    def test_seven_dimensions_delegate_verbatim_to_strategic_score(self):
        profile = {"dimensions": {}, "board_summary": {}}
        with patch("strategic_intelligence_core.strategic_score", return_value=_FAKE_STRATEGIC_SCORE) as mock_strategic, \
             patch("value_engine.compute_value_profile", return_value=profile):
            result = cae.investment_score("n")
        mock_strategic.assert_called_once_with("n", decisions_path=None)
        self.assertEqual(result["recurring_revenue_potential"], _FAKE_STRATEGIC_SCORE["recurring_revenue"])
        self.assertEqual(result["competition_level"], _FAKE_STRATEGIC_SCORE["competition"])
        self.assertEqual(result["automation_potential"], _FAKE_STRATEGIC_SCORE["automation"])
        self.assertEqual(result["risk"], _FAKE_STRATEGIC_SCORE["risk"])
        self.assertEqual(result["strategic_importance"], _FAKE_STRATEGIC_SCORE["strategic_value"])
        self.assertEqual(result["long_term_asset_value"], _FAKE_STRATEGIC_SCORE["long_term_value"])
        self.assertEqual(result["execution_complexity"], _FAKE_STRATEGIC_SCORE["difficulty"])

    def test_seven_new_dimensions_cite_value_engine_directly(self):
        profile = {
            "dimensions": {
                "expected_customer_value": {"answer": "Unknown", "reason": "no NPS system"},
                "defensibility": {"level": "high", "reason": "real moat"},
                "knowledge_accumulation": {"score": 1, "level": "متوسطة", "note": "1/3"},
                "synergy_with_existing_products": {"answer": "Unknown", "reason": "no ladder"},
                "bundle_potential": {"answer": "Unknown", "reason": "no ladder"},
                "brand_building_impact": {"answer": "Unknown", "reason": "no brand metric"},
            },
            "board_summary": {
                "estimated_lifetime_value": {"value": 500, "basis": "real closed-sale revenue"},
                "estimated_build_cost": {"maturity": "REAL", "estimated_cost_usd": 0.05, "sample_size": 10},
                "estimated_maintenance_cost": {"answer": "Unknown", "reason": "no tracking system"},
            },
        }
        with patch("strategic_intelligence_core.strategic_score", return_value=_FAKE_STRATEGIC_SCORE), \
             patch("value_engine.compute_value_profile", return_value=profile):
            result = cae.investment_score("n")
        self.assertEqual(result["expected_revenue"]["value"], 500)
        self.assertEqual(result["customer_impact"]["value"], "Unknown")
        self.assertEqual(result["market_defensibility"]["value"], "high")
        self.assertEqual(result["engineering_cost"]["value"], 0.05)
        self.assertEqual(result["maintenance_cost"]["value"], "Unknown")
        self.assertEqual(result["knowledge_reuse"]["value"], "متوسطة")
        self.assertEqual(result["brand_value"]["value"], "Unknown")

    def test_no_real_profile_is_honestly_unknown_never_a_crash(self):
        with patch("strategic_intelligence_core.strategic_score", return_value=_FAKE_STRATEGIC_SCORE), \
             patch("value_engine.compute_value_profile", return_value=None):
            result = cae.investment_score("n")
        self.assertEqual(result["expected_revenue"]["value"], "Unknown")
        self.assertEqual(result["engineering_cost"]["value"], "Unknown")
        self.assertEqual(result["knowledge_reuse"]["value"], "Unknown")


class TestOpportunityCost(unittest.TestCase):
    def _portfolio(self, niches):
        return {"profiles": [{"niche": n} for n in niches]}

    def test_never_recomputes_the_portfolio_a_second_time(self):
        portfolio = self._portfolio(["a", "b"])
        buckets = {"run_now": [], "wait": [], "accelerate": [], "stop": [], "cancel": []}
        with patch("value_engine.build_value_engine_report", return_value=portfolio) as mock_build:
            with patch("scheduler.decide_next_actions", return_value={"buckets": buckets}) as mock_decide:
                cae.opportunity_cost()
        mock_build.assert_called_once()
        mock_decide.assert_called_once()
        self.assertIs(mock_decide.call_args.kwargs["portfolio"], portfolio)

    def test_pairs_a_waiting_niche_with_the_real_higher_ranked_niche(self):
        portfolio = self._portfolio(["top", "waiting"])
        buckets = {
            "run_now": [{"niche": "top", "reason": "highest priority"}],
            "wait": [{"niche": "waiting", "reason": "accepted, waiting its turn"}],
            "accelerate": [], "stop": [], "cancel": [],
        }
        with patch("value_engine.build_value_engine_report", return_value=portfolio), \
             patch("scheduler.decide_next_actions", return_value={"buckets": buckets}):
            result = cae.opportunity_cost()
        self.assertEqual(len(result["pairings"]), 1)
        pairing = result["pairings"][0]
        self.assertEqual(pairing["delayed_niche"], "waiting")
        self.assertEqual(pairing["higher_priority_niches"], ["top"])

    def test_rejected_niche_with_no_real_portfolio_rank_is_never_paired(self):
        portfolio = self._portfolio(["top"])
        buckets = {
            "run_now": [{"niche": "top", "reason": "highest priority"}],
            "wait": [], "accelerate": [], "stop": [],
            "cancel": [{"niche": "rejected-elsewhere", "reason": "real rejection"}],
        }
        with patch("value_engine.build_value_engine_report", return_value=portfolio), \
             patch("scheduler.decide_next_actions", return_value={"buckets": buckets}):
            result = cae.opportunity_cost()
        self.assertEqual(result["pairings"], [])

    def test_top_ranked_niche_is_never_paired_against_itself(self):
        portfolio = self._portfolio(["only"])
        buckets = {
            "run_now": [{"niche": "only", "reason": "highest priority"}],
            "wait": [], "accelerate": [], "stop": [], "cancel": [],
        }
        with patch("value_engine.build_value_engine_report", return_value=portfolio), \
             patch("scheduler.decide_next_actions", return_value={"buckets": buckets}):
            result = cae.opportunity_cost()
        self.assertEqual(result["pairings"], [])


class TestStuckWithoutProduction(unittest.TestCase):
    def _lifecycle(self, reached, evidence="no attempt"):
        return {"stages": {"prototype": {"reached": reached, "evidence": evidence}}}

    def test_a_recently_accepted_niche_is_never_flagged_stuck(self):
        from datetime import datetime, timezone
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        decisions = [{"niche": "n", "status": "ACCEPTED", "decided_at": "2026-07-28T00:00:00+00:00"}]
        with patch("decision_engine.ranking.rank_all", return_value=decisions), \
             patch("value_engine.classify_lifecycle_stage", return_value=self._lifecycle(False)):
            result = cae.stuck_without_production(now=now)
        self.assertEqual(result["stuck"], [])

    def test_an_old_accepted_niche_with_no_real_production_is_flagged(self):
        from datetime import datetime, timezone
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        decisions = [{"niche": "n", "status": "ACCEPTED", "decided_at": "2026-07-01T00:00:00+00:00"}]
        with patch("decision_engine.ranking.rank_all", return_value=decisions), \
             patch("value_engine.classify_lifecycle_stage", return_value=self._lifecycle(False, "لا محاولة إنتاج حقيقية بعد")):
            result = cae.stuck_without_production(now=now)
        self.assertEqual(len(result["stuck"]), 1)
        self.assertEqual(result["stuck"][0]["niche"], "n")
        self.assertGreaterEqual(result["stuck"][0]["elapsed_days"], 7)

    def test_a_niche_with_real_production_is_never_flagged_regardless_of_age(self):
        from datetime import datetime, timezone
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        decisions = [{"niche": "n", "status": "ACCEPTED", "decided_at": "2026-01-01T00:00:00+00:00"}]
        with patch("decision_engine.ranking.rank_all", return_value=decisions), \
             patch("value_engine.classify_lifecycle_stage", return_value=self._lifecycle(True, "1 محاولة حقيقية")):
            result = cae.stuck_without_production(now=now)
        self.assertEqual(result["stuck"], [])

    def test_rejected_decisions_are_never_considered(self):
        decisions = [{"niche": "n", "status": "REJECTED", "decided_at": "2026-01-01T00:00:00+00:00"}]
        with patch("decision_engine.ranking.rank_all", return_value=decisions), \
             patch("value_engine.classify_lifecycle_stage") as mock_classify:
            result = cae.stuck_without_production()
        mock_classify.assert_not_called()
        self.assertEqual(result["total_accepted"], 0)


def _profile(niche, priority_score=50.0, roi_pct=100.0, at_risk_flagged=False, reasons=None):
    return {
        "niche": niche,
        "at_risk": {"flagged": at_risk_flagged, "reasons": reasons or []},
        "board_summary": {
            "priority_score": {"score": priority_score, "based_on": ["opportunity_score"]},
            "expected_roi": {"maturity": "REAL", "roi_pct": roi_pct} if roi_pct is not None else {"maturity": "DISCOVERY", "reason": "x"},
            "recommendation": ["x"],
        },
    }


class TestBuildCapitalAllocationDashboard(unittest.TestCase):
    def _patches(self, portfolio=None, scheduling=None, opp_cost=None, stuck=None, snapshot=None):
        portfolio = portfolio if portfolio is not None else {"profiles": [_profile("n")]}
        scheduling = scheduling if scheduling is not None else {
            "buckets": {"run_now": [], "wait": [], "accelerate": [], "stop": [], "cancel": []},
            "counts": {"run_now": 0, "wait": 0, "accelerate": 0, "stop": 0, "cancel": 0},
        }
        opp_cost = opp_cost if opp_cost is not None else {"pairings": [], "portfolio_size": 1}
        stuck = stuck if stuck is not None else {"stuck": [], "total_accepted": 1}
        snapshot = snapshot if snapshot is not None else {"Research": {"count": 0}}
        return (
            patch("value_engine.build_value_engine_report", return_value=portfolio),
            patch("scheduler.decide_next_actions", return_value=scheduling),
            patch("capital_allocation_engine.opportunity_cost", return_value=opp_cost),
            patch("capital_allocation_engine.stuck_without_production", return_value=stuck),
            patch("ceo_decision_center.capital_allocation_snapshot", return_value=snapshot),
        )

    def test_never_recomputes_the_portfolio_for_opportunity_cost(self):
        portfolio = {"profiles": [_profile("n")]}
        scheduling = {"buckets": {"run_now": [], "wait": [], "accelerate": [], "stop": [], "cancel": []}, "counts": {}}
        patches = self._patches(portfolio=portfolio, scheduling=scheduling)
        with patches[0], patches[1], patches[2] as mock_opp_cost, patches[3], patches[4]:
            cae.build_capital_allocation_dashboard()
        self.assertIs(mock_opp_cost.call_args.kwargs["portfolio"], portfolio)
        self.assertIs(mock_opp_cost.call_args.kwargs["scheduling"], scheduling)

    def test_top_roi_initiatives_cites_real_profile_fields(self):
        portfolio = {"profiles": [_profile("n", priority_score=77.0, roi_pct=42.0)]}
        patches = self._patches(portfolio=portfolio)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = cae.build_capital_allocation_dashboard()
        self.assertEqual(result["top_roi_initiatives"][0]["niche"], "n")
        self.assertEqual(result["top_roi_initiatives"][0]["priority_score"], 77.0)
        self.assertEqual(result["top_roi_initiatives"][0]["expected_roi"]["roi_pct"], 42.0)

    def test_projects_losing_value_only_includes_at_risk_flagged(self):
        portfolio = {"profiles": [
            _profile("safe", at_risk_flagged=False),
            _profile("risky", at_risk_flagged=True, reasons=["board rejected"]),
        ]}
        patches = self._patches(portfolio=portfolio)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = cae.build_capital_allocation_dashboard()
        self.assertEqual(len(result["projects_losing_value"]), 1)
        self.assertEqual(result["projects_losing_value"][0]["niche"], "risky")

    def test_expected_portfolio_return_averages_only_real_roi_values(self):
        portfolio = {"profiles": [
            _profile("a", roi_pct=100.0),
            _profile("b", roi_pct=200.0),
            _profile("c", roi_pct=None),
        ]}
        patches = self._patches(portfolio=portfolio)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = cae.build_capital_allocation_dashboard()
        self.assertEqual(result["expected_portfolio_return"]["average_roi_pct"], 150.0)
        self.assertEqual(result["expected_portfolio_return"]["based_on_n_real_opportunities"], 2)

    def test_expected_portfolio_return_is_honestly_unknown_when_no_real_roi_exists(self):
        portfolio = {"profiles": [_profile("a", roi_pct=None)]}
        patches = self._patches(portfolio=portfolio)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = cae.build_capital_allocation_dashboard()
        self.assertEqual(result["expected_portfolio_return"]["answer"], "Unknown")

    def test_resource_distribution_cites_scheduling_counts_and_attention_snapshot(self):
        scheduling = {"buckets": {"run_now": [], "wait": [], "accelerate": [], "stop": [], "cancel": []}, "counts": {"run_now": 2}}
        snapshot = {"Research": {"count": 5}}
        patches = self._patches(scheduling=scheduling, snapshot=snapshot)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = cae.build_capital_allocation_dashboard()
        self.assertEqual(result["resource_distribution"]["scheduling_buckets"], {"run_now": 2})
        self.assertEqual(result["resource_distribution"]["attention_by_department"], snapshot)


if __name__ == "__main__":
    unittest.main()

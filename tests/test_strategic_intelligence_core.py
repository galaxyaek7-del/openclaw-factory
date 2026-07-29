"""Tests for strategic_intelligence_core.py (Strategic Intelligence
Core, 2026-07-29): the real multi-year-horizon evaluator, Strategic
Score citation layer, and Executive Brief aggregator -- every real
source function mocked here; each one's own logic has its own isolated
unit tests elsewhere (test_growth_engine.py, test_ledger.py,
test_value_engine.py, test_opportunity_pipeline.py,
test_executive_score.py, test_resilience_monitor.py,
test_ceo_decision_center.py, test_evolution_engine.py,
test_scheduler.py, test_founder_console.py, test_customer_pipeline.py).

    python -m unittest tests.test_strategic_intelligence_core -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import strategic_intelligence_core as sic


class TestEvaluateStrategicHorizons(unittest.TestCase):

    def test_short_horizons_cite_a_real_forecast_value_when_present(self):
        with patch("growth_engine.growth_forecast", return_value={"maturity": "REAL", "forecast": {"value": 42}}), \
             patch("channels.ledger.revenue_trend", return_value={"by_day": {}}):
            result = sic.evaluate_strategic_horizons()
        self.assertEqual(result["horizons"]["30_days"], {"answer": 42, "source": "growth_engine.growth_forecast()"})
        self.assertEqual(result["horizons"]["90_days"], {"answer": 42, "source": "growth_engine.growth_forecast()"})

    def test_short_horizons_are_honest_not_enough_evidence_when_discovery(self):
        with patch("growth_engine.growth_forecast", return_value={"maturity": "DISCOVERY", "forecast": None, "reason": "0 sales"}), \
             patch("channels.ledger.revenue_trend", return_value={"by_day": {}}):
            result = sic.evaluate_strategic_horizons()
        self.assertEqual(result["horizons"]["30_days"]["answer"], "NOT ENOUGH EVIDENCE")
        self.assertEqual(result["horizons"]["30_days"]["reason"], "0 sales")

    def test_short_horizons_are_honest_not_enough_evidence_when_real_but_value_none(self):
        with patch("growth_engine.growth_forecast", return_value={"maturity": "REAL", "forecast": {"value": None, "reason": "needs 2 windows"}}), \
             patch("channels.ledger.revenue_trend", return_value={"by_day": {}}):
            result = sic.evaluate_strategic_horizons()
        self.assertEqual(result["horizons"]["90_days"]["answer"], "NOT ENOUGH EVIDENCE")
        self.assertEqual(result["horizons"]["90_days"]["reason"], "needs 2 windows")

    def test_long_horizons_report_real_span_when_data_exists_but_insufficient(self):
        by_day = {"2026-07-01": {}, "2026-07-10": {}}
        with patch("growth_engine.growth_forecast", return_value={"maturity": "DISCOVERY", "forecast": None, "reason": "x"}), \
             patch("channels.ledger.revenue_trend", return_value={"by_day": by_day}):
            result = sic.evaluate_strategic_horizons()
        self.assertEqual(result["real_span_days"], 9)
        for name in ("1_year", "3_years", "10_years"):
            self.assertEqual(result["horizons"][name]["answer"], "NOT ENOUGH EVIDENCE")
            self.assertEqual(result["horizons"][name]["real_span_days"], 9)
            self.assertIn("9", result["horizons"][name]["reason"])

    def test_long_horizons_honestly_flag_no_real_algorithm_even_when_span_is_enough(self):
        by_day = {"2020-01-01": {}, "2026-07-29": {}}
        with patch("growth_engine.growth_forecast", return_value={"maturity": "DISCOVERY", "forecast": None, "reason": "x"}), \
             patch("channels.ledger.revenue_trend", return_value={"by_day": by_day}):
            result = sic.evaluate_strategic_horizons()
        self.assertGreaterEqual(result["real_span_days"], sic._LONG_HORIZONS_NEEDED_SPAN_DAYS["1_year"])
        self.assertEqual(result["horizons"]["1_year"]["answer"], "NOT ENOUGH EVIDENCE")
        self.assertIn("لا خوارزمية تنبّؤ حقيقية", result["horizons"]["1_year"]["reason"])
        # 3/10-year horizons still honestly insufficient even with ~6.5 real years of span
        self.assertIn("يحتاج", result["horizons"]["10_years"]["reason"])

    def test_no_real_sales_events_gives_zero_span(self):
        with patch("growth_engine.growth_forecast", return_value={"maturity": "DISCOVERY", "forecast": None, "reason": "x"}), \
             patch("channels.ledger.revenue_trend", return_value={"by_day": {}}):
            result = sic.evaluate_strategic_horizons()
        self.assertEqual(result["real_span_days"], 0)


class TestExtractSignal(unittest.TestCase):

    def test_none_is_honestly_unknown(self):
        result = sic._extract_signal(None, "src")
        self.assertEqual(result, {"value": "Unknown", "source": "src", "reason": "لا بيانات محفوظة لهذا القرار بعد"})

    def test_unknown_answer_shape_passes_through_real_reason(self):
        result = sic._extract_signal({"answer": "Unknown", "reason": "no signal"}, "src")
        self.assertEqual(result, {"value": "Unknown", "source": "src", "reason": "no signal"})

    def test_value_note_shape(self):
        result = sic._extract_signal({"value": 55, "note": "why"}, "src")
        self.assertEqual(result, {"value": 55, "source": "src", "reason": "why"})

    def test_level_shape(self):
        result = sic._extract_signal({"level": "high", "reason": "why"}, "src")
        self.assertEqual(result, {"value": "high", "source": "src", "reason": "why"})

    def test_favorability_score_shape_with_competitors(self):
        result = sic._extract_signal({"favorability_score": 70, "real_competitors": ["a", "b"]}, "src")
        self.assertEqual(result["value"], 70)
        self.assertIn("a", result["reason"])

    def test_favorability_score_shape_without_competitors(self):
        result = sic._extract_signal({"favorability_score": 70, "real_competitors": None}, "src")
        self.assertEqual(result, {"value": 70, "source": "src", "reason": None})

    def test_score_shape(self):
        result = sic._extract_signal({"score": 47.0, "note": "avg"}, "src")
        self.assertEqual(result, {"value": 47.0, "source": "src", "reason": "avg"})

    def test_bare_number_passes_through(self):
        result = sic._extract_signal(85, "src")
        self.assertEqual(result, {"value": 85, "source": "src", "reason": None})

    def test_unrecognized_dict_shape_is_honestly_unknown(self):
        result = sic._extract_signal({"weird_key": 1}, "src")
        self.assertEqual(result["value"], "Unknown")
        self.assertIn("weird_key", result["reason"])


class TestStrategicScore(unittest.TestCase):

    def test_no_accepted_decision_is_honestly_unknown_on_every_dimension(self):
        with patch("factory_orchestrator.find_decision", return_value=None):
            result = sic.strategic_score("nonexistent-niche")
        for key in ("market", "competition", "demand", "difficulty", "automation", "scalability",
                    "recurring_revenue", "strategic_value", "risk", "trust", "long_term_value"):
            self.assertEqual(result[key]["value"], "Unknown")
            self.assertIn("nonexistent-niche", result[key]["reason"])

    def test_real_decision_maps_every_dimension_from_its_real_source(self):
        decision = {"niche": "n", "decision_id": "d1"}
        annotated = {
            "competition": {"favorability_score": 70, "real_competitors": ["Acme"]},
            "pain_level": {"value": 8, "confidence": "high", "reason": "real survey"},
            "technical_complexity": 55,
        }
        profile = {
            "dimensions": {
                "global_demand": {"level": "strong", "reason": "real discussion volume"},
                "automation_potential": 40,
                "scalability": 85,
                "recurring_revenue_potential": 85,
                "long_term_strategic_value": {"value": {"answer": "Uncertain"}, "note": "layer note"},
            },
            "board_summary": {"strategic_value": {"score": 47.0, "note": "avg over 5 dims"}},
            "at_risk": {"flagged": True, "reasons": ["قرار مجلس حقيقي: غير موافَق عليه"]},
        }
        trust = {"value": 20, "source": "enterprise_readiness.compute_trust_score()"}

        with patch("factory_orchestrator.find_decision", return_value=decision), \
             patch("opportunity_pipeline.annotate_decision", return_value=annotated), \
             patch("value_engine.compute_value_profile", return_value=profile), \
             patch("executive_score._trust", return_value=trust):
            result = sic.strategic_score("n")

        self.assertEqual(result["market"]["value"], "strong")
        self.assertEqual(result["competition"]["value"], 70)
        self.assertIn("Acme", result["competition"]["reason"])
        self.assertEqual(result["demand"]["value"], 8)
        self.assertEqual(result["difficulty"]["value"], 55)
        self.assertEqual(result["automation"]["value"], 40)
        self.assertEqual(result["scalability"]["value"], 85)
        self.assertEqual(result["recurring_revenue"]["value"], 85)
        self.assertEqual(result["strategic_value"]["value"], 47.0)
        self.assertEqual(result["strategic_value"]["reason"], "avg over 5 dims")
        self.assertEqual(result["risk"]["value"], "at_risk")
        self.assertIn("قرار مجلس", result["risk"]["reason"])
        self.assertEqual(result["trust"]["value"], 20)
        self.assertEqual(result["long_term_value"]["value"], {"answer": "Uncertain"})

    def test_risk_not_flagged_gives_honest_no_signal_reason(self):
        decision = {"niche": "n"}
        profile = {"dimensions": {}, "board_summary": {}, "at_risk": {"flagged": False, "reasons": []}}
        with patch("factory_orchestrator.find_decision", return_value=decision), \
             patch("opportunity_pipeline.annotate_decision", return_value={}), \
             patch("value_engine.compute_value_profile", return_value=profile), \
             patch("executive_score._trust", return_value={"value": "Unknown", "reason": "no inspections yet"}):
            result = sic.strategic_score("n")
        self.assertEqual(result["risk"]["value"], "not_flagged")
        self.assertEqual(result["risk"]["reason"], "لا إشارات خطر حوكمة حقيقية نشطة حالياً")
        self.assertEqual(result["trust"]["value"], "Unknown")
        self.assertEqual(result["trust"]["reason"], "no inspections yet")

    def test_value_profile_none_still_returns_honest_unknowns_not_a_crash(self):
        decision = {"niche": "n"}
        with patch("factory_orchestrator.find_decision", return_value=decision), \
             patch("opportunity_pipeline.annotate_decision", return_value={}), \
             patch("value_engine.compute_value_profile", return_value=None), \
             patch("executive_score._trust", return_value={"value": "Unknown", "reason": "x"}):
            result = sic.strategic_score("n")
        self.assertEqual(result["market"]["value"], "Unknown")
        self.assertEqual(result["risk"]["value"], "not_flagged")


class TestBuildExecutiveBrief(unittest.TestCase):

    def _patches(self, resilience=None, dashboard=None, evolution_report=None,
                 founder_queue=None, horizons=None, cost_trend=None):
        resilience = resilience if resilience is not None else {
            "findings": [], "active_alerts": [], "resilience_score": "Unknown",
            "resilience_score_note": "n/a", "generated_at": "t",
        }
        dashboard = dashboard if dashboard is not None else {
            "top_risks": {"stop": [], "cancel": []},
            "top_opportunities": [],
            "current_strategic_priority": None,
            "next_executive_decision": None,
            "scheduling_buckets": {"accelerate": [], "stop": [], "cancel": [], "run_now": [], "wait": []},
        }
        evolution_report = evolution_report if evolution_report is not None else {
            "bottlenecks": {"detected": False, "reason": "none"},
            "customer_success_bottleneck": {"detected": False, "reason": "none"},
        }
        founder_queue = founder_queue if founder_queue is not None else {
            "pending_decisions": [], "pending_evolution_proposals": [], "publish_emergency_stop": None,
        }
        horizons = horizons if horizons is not None else {"horizons": {}, "real_span_days": 0}
        cost_trend = cost_trend if cost_trend is not None else {"answer": "NOT ENOUGH EVIDENCE", "reason": "no requests"}
        return (
            patch("resilience_monitor.assess_resilience", return_value=resilience),
            patch("ceo_decision_center.ceo_dashboard", return_value=dashboard),
            patch("evolution_engine.build_evolution_report", return_value=evolution_report),
            patch("founder_console.build_founder_queue_partial", return_value=founder_queue),
            patch("strategic_intelligence_core.evaluate_strategic_horizons", return_value=horizons),
            patch("customer_pipeline.customer_problem_cost_trend", return_value=cost_trend),
        )

    def test_never_recomputes_scheduling_a_second_time(self):
        # Strategic Intelligence Core (2026-07-29): build_executive_brief()
        # must reuse ceo_dashboard()'s own already-computed
        # scheduling_buckets rather than calling scheduler.decide_next_
        # actions() itself a second time -- a real, confirmed timeout bug
        # this test guards against regressing.
        with patch("scheduler.decide_next_actions") as mock_decide:
            patches = self._patches()
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
                sic.build_executive_brief()
        mock_decide.assert_not_called()

    def test_every_field_cites_its_real_source_with_no_gaps(self):
        resilience = {
            "findings": [], "active_alerts": [{"area": "x", "severity": "warning"}],
            "resilience_score": 80, "resilience_score_note": "note", "generated_at": "t",
        }
        dashboard = {
            "top_risks": {"stop": [{"niche": "n1"}], "cancel": []},
            "top_opportunities": [{"niche": "n2"}],
            "current_strategic_priority": {"niche": "n2"},
            "next_executive_decision": {"niche": "n3"},
            "scheduling_buckets": {"accelerate": [{"niche": "n4"}], "stop": [{"niche": "n1"}], "cancel": [], "run_now": [], "wait": []},
        }
        patches = self._patches(resilience=resilience, dashboard=dashboard)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            brief = sic.build_executive_brief()

        self.assertEqual(brief["company_health"]["resilience_score"], 80)
        self.assertEqual(brief["company_health"]["active_alerts_count"], 1)
        self.assertEqual(brief["top_risks"]["stop"], [{"niche": "n1"}])
        self.assertEqual(brief["top_risks"]["resilience_active_alerts"], resilience["active_alerts"])
        self.assertEqual(brief["top_opportunities"], [{"niche": "n2"}])
        self.assertEqual(brief["recommended_priorities"]["current_strategic_priority"], {"niche": "n2"})
        self.assertEqual(brief["products_to_accelerate"], [{"niche": "n4"}])
        self.assertEqual(brief["products_to_pause"], [{"niche": "n1"}])

    def test_research_needed_lists_every_real_not_enough_evidence_gap(self):
        horizons = {
            "horizons": {
                "30_days": {"answer": "NOT ENOUGH EVIDENCE", "reason": "no sales"},
                "90_days": {"answer": 5, "source": "x"},
            },
            "real_span_days": 0,
        }
        cost_trend = {"answer": "NOT ENOUGH EVIDENCE", "reason": "no requests"}
        patches = self._patches(horizons=horizons, cost_trend=cost_trend)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            brief = sic.build_executive_brief()

        topics = [r["topic"] for r in brief["research_needed"]]
        self.assertIn("أفق 30_days", topics)
        self.assertNotIn("أفق 90_days", topics)
        self.assertIn("اتجاه تكلفة مشاكل العملاء", topics)

    def test_research_needed_is_honestly_empty_when_every_signal_resolves(self):
        horizons = {"horizons": {"30_days": {"answer": 5, "source": "x"}}, "real_span_days": 900}
        cost_trend = {"worsening": False, "recent_daily_avg": 1.0, "trailing_daily_avg": 2.0}
        patches = self._patches(horizons=horizons, cost_trend=cost_trend)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            brief = sic.build_executive_brief()
        self.assertEqual(brief["research_needed"], [])

    def test_founder_decisions_required_passes_through_real_queue(self):
        founder_queue = {
            "pending_decisions": [{"niche": "n5"}],
            "pending_evolution_proposals": [{"proposal_id": "p1"}],
            "publish_emergency_stop": {"reason": "manual stop"},
        }
        patches = self._patches(founder_queue=founder_queue)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            brief = sic.build_executive_brief()
        self.assertEqual(brief["founder_decisions_required"], founder_queue)

    def test_top_bottlenecks_includes_customer_success_bottleneck(self):
        evolution_report = {
            "bottlenecks": {"detected": True, "items": [{"evidence": "slow builds"}]},
            "customer_success_bottleneck": {"detected": True, "proposal_id": "resolve_stuck_customer_requests"},
        }
        patches = self._patches(evolution_report=evolution_report)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            brief = sic.build_executive_brief()
        self.assertEqual(brief["top_bottlenecks"]["bottlenecks"]["detected"], True)
        self.assertEqual(brief["top_bottlenecks"]["customer_success_bottleneck"]["detected"], True)


if __name__ == "__main__":
    unittest.main()

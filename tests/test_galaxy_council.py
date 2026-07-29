"""Tests for galaxy_council.py (Galaxy Council directive, 2026-07-29):
the 9 real member-normalizer functions. Every real source is mocked --
each one's own logic has its own isolated unit tests elsewhere
(test_strategic_intelligence_core.py, test_competitor_discovery.py,
test_market_alerts.py, test_customer_pipeline.py, test_profit_oracle.py,
test_executive_quality_gate.py, test_ai_doctor.py, test_resilience_monitor.py,
test_evolution_engine.py, test_decision_engine_store.py).

    python -m unittest tests.test_galaxy_council -v
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

import galaxy_council as gc


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestResultShape(unittest.TestCase):
    def test_result_rejects_an_invalid_stance(self):
        with self.assertRaises(ValueError):
            gc._result("X", "o", 1.0, [], "r", "rec", False, stance="not_a_real_stance")

    def test_result_has_every_required_field(self):
        r = gc._result("X", "o", 1.0, ["e"], "r", "rec", True, stance="proceed", scope="niche")
        for key in ("member", "opinion", "confidence", "evidence", "risk", "recommendation",
                    "founder_approval_required", "stance", "scope"):
            self.assertIn(key, r)


class TestMemberStrategic(unittest.TestCase):
    def test_at_risk_gives_hold_stance_and_founder_approval(self):
        score = {
            "niche": "n",
            "market": {"value": "strong", "source": "s"},
            "risk": {"value": "at_risk", "source": "s", "reason": "board rejected"},
            "generated_at": "t",
        }
        with patch("strategic_intelligence_core.strategic_score", return_value=score):
            result = gc._member_strategic("n")
        self.assertEqual(result["stance"], "hold")
        self.assertTrue(result["founder_approval_required"])

    def test_not_flagged_gives_informational_stance(self):
        score = {
            "niche": "n",
            "market": {"value": "strong", "source": "s"},
            "risk": {"value": "not_flagged", "source": "s"},
            "generated_at": "t",
        }
        with patch("strategic_intelligence_core.strategic_score", return_value=score):
            result = gc._member_strategic("n")
        self.assertEqual(result["stance"], "informational_context")
        self.assertFalse(result["founder_approval_required"])

    def test_confidence_reflects_fraction_of_known_dimensions(self):
        score = {
            "market": {"value": "strong", "source": "s"},
            "demand": {"value": "Unknown", "source": "s", "reason": "x"},
            "risk": {"value": "not_flagged", "source": "s"},
            "generated_at": "t",
        }
        with patch("strategic_intelligence_core.strategic_score", return_value=score):
            result = gc._member_strategic("n")
        self.assertEqual(result["confidence"], round(2 / 3, 2))


class TestMemberMarket(unittest.TestCase):
    def test_no_snapshot_no_alerts_is_informational(self):
        with patch("competitor_discovery.load_database", return_value={}), \
             patch("market_alerts.get_active_alerts", return_value={"niche": "n", "total": 0, "by_severity_counts": {}, "alerts": []}):
            result = gc._member_market("n")
        self.assertEqual(result["stance"], "informational_context")

    def test_critical_alert_gives_hold_and_founder_approval(self):
        alerts = {
            "niche": "n", "total": 1,
            "by_severity_counts": {"Critical": 1, "High": 0, "Medium": 0, "Low": 0},
            "alerts": [{"event_type": "new_entrant", "severity": "Critical"}],
        }
        with patch("competitor_discovery.load_database", return_value={}), \
             patch("market_alerts.get_active_alerts", return_value=alerts):
            result = gc._member_market("n")
        self.assertEqual(result["stance"], "hold")
        self.assertTrue(result["founder_approval_required"])

    def test_real_snapshot_with_no_critical_alerts_is_proceed(self):
        snapshot = {"niche": "n"}
        threat = {
            "competitor_saturation": {"level": "low", "score": 10, "basis": "x"},
            "market_concentration": {"level": "Unknown", "score": None, "basis": "no data"},
            "new_entrant_trajectory": {"level": "stable", "score": 0, "basis": "x"},
            "computed_at": "t",
        }
        with patch("competitor_discovery.load_database", return_value={"n": snapshot}), \
             patch("competitor_discovery._normalize_key", return_value="n"), \
             patch("competitor_discovery.compute_threat_assessment", return_value=threat), \
             patch("market_alerts.get_active_alerts", return_value={"niche": "n", "total": 0, "by_severity_counts": {}, "alerts": []}):
            result = gc._member_market("n")
        self.assertEqual(result["stance"], "proceed")
        self.assertFalse(result["founder_approval_required"])


class TestMemberProduction(unittest.TestCase):
    def test_no_inspection_is_no_data(self):
        with patch("galaxy_council._latest_inspection_for_niche", return_value=None), \
             patch("executive_intelligence.engine_health.compute_engine_health", return_value={}):
            result = gc._member_production("n")
        self.assertEqual(result["stance"], "no_data")
        self.assertFalse(result["founder_approval_required"])

    def test_failed_inspection_is_stop_and_founder_approval(self):
        inspection = {"passed": False, "technical": {"failures": ["bad pdf"]}, "commercial": {"failures": []}, "timestamp": "t", "niche": "n"}
        with patch("galaxy_council._latest_inspection_for_niche", return_value=inspection), \
             patch("executive_intelligence.engine_health.compute_engine_health", return_value={"book_engine": {"maturity": "REAL"}}):
            result = gc._member_production("n")
        self.assertEqual(result["stance"], "stop")
        self.assertTrue(result["founder_approval_required"])
        self.assertIn("bad pdf", result["risk"])

    def test_passed_inspection_is_proceed(self):
        inspection = {"passed": True, "technical": {"failures": []}, "commercial": {"failures": []}, "timestamp": "t", "niche": "n"}
        with patch("galaxy_council._latest_inspection_for_niche", return_value=inspection), \
             patch("executive_intelligence.engine_health.compute_engine_health", return_value={}):
            result = gc._member_production("n")
        self.assertEqual(result["stance"], "proceed")
        self.assertFalse(result["founder_approval_required"])


class TestLatestInspectionForNiche(unittest.TestCase):
    def test_no_file_returns_none(self):
        path = _temp_path(".log")
        self.assertIsNone(gc._latest_inspection_for_niche("n", inspections_log=path))

    def test_returns_the_most_recent_matching_entry(self):
        path = _temp_path(".log")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"niche": "n", "passed": true, "timestamp": "1"}\n')
            f.write('{"niche": "other", "passed": false, "timestamp": "2"}\n')
            f.write('{"niche": "n", "passed": false, "timestamp": "3"}\n')
        try:
            result = gc._latest_inspection_for_niche("n", inspections_log=path)
            self.assertEqual(result["timestamp"], "3")
        finally:
            os.remove(path)


class TestMemberCustomer(unittest.TestCase):
    def test_all_empty_is_honestly_zero_confidence(self):
        with patch("customer_pipeline.funnel_conversion_summary", return_value={"answer": "Unknown", "reason": "x"}), \
             patch("customer_pipeline.delivery_delay_summary", return_value={"answer": "Unknown", "reason": "x"}), \
             patch("customer_pipeline.customer_problem_cost_trend", return_value={"answer": "Unknown", "reason": "x"}):
            result = gc._member_customer()
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["scope"], "company_wide")

    def test_worsening_cost_trend_requires_founder_approval(self):
        with patch("customer_pipeline.funnel_conversion_summary", return_value={"answer": "Unknown", "reason": "x"}), \
             patch("customer_pipeline.delivery_delay_summary", return_value={"answer": "Unknown", "reason": "x"}), \
             patch("customer_pipeline.customer_problem_cost_trend", return_value={"worsening": True, "recent_daily_avg": 2, "trailing_daily_avg": 1}):
            result = gc._member_customer()
        self.assertTrue(result["founder_approval_required"])


class TestMemberFinancial(unittest.TestCase):
    def test_accepted_is_proceed(self):
        score = {
            "opportunity_score": 80, "accepted": True, "min_required": 65,
            "components": {"market_demand": 70}, "components_basis": {"market_demand": "real"},
        }
        trend = {"recent_7d_revenue_usd": 0}
        with patch("profit_oracle.opportunity_score", return_value=score), \
             patch("channels.ledger.revenue_trend", return_value=trend):
            result = gc._member_financial("n")
        self.assertEqual(result["stance"], "proceed")
        self.assertFalse(result["founder_approval_required"])

    def test_not_accepted_is_hold_and_founder_approval(self):
        score = {
            "opportunity_score": 40, "accepted": False, "min_required": 65,
            "components": {"market_demand": 30}, "components_basis": {"market_demand": "estimated"},
        }
        trend = {"recent_7d_revenue_usd": 0}
        with patch("profit_oracle.opportunity_score", return_value=score), \
             patch("channels.ledger.revenue_trend", return_value=trend):
            result = gc._member_financial("n")
        self.assertEqual(result["stance"], "hold")
        self.assertTrue(result["founder_approval_required"])


class TestMemberSecurity(unittest.TestCase):
    def test_never_flags_founder_approval_always_informational(self):
        with patch("factory_orchestrator.find_decision", return_value=None), \
             patch("executive_quality_gate.check_constitution_alignment", return_value={"answer": "Unknown", "reason": "x"}), \
             patch("executive_quality_gate.check_platform_tos_awareness", return_value={"answer": "Unknown", "reason": "x"}), \
             patch("ai_doctor._check_python_pinning", return_value={"checked": 2, "pinned": 1, "unpinned": ["a"]}), \
             patch("ai_doctor._check_node_pinning", return_value={"checked": 2, "pinned": 2, "unpinned": []}):
            result = gc._member_security("n")
        self.assertEqual(result["stance"], "informational_context")
        self.assertFalse(result["founder_approval_required"])
        self.assertIn("1 اعتمادية غير مثبَّتة حقيقياً", result["risk"])


class TestMemberResilience(unittest.TestCase):
    def test_no_active_alerts(self):
        assessment = {"resilience_score": 93, "active_alerts": []}
        with patch("resilience_monitor.assess_resilience", return_value=assessment):
            result = gc._member_resilience()
        self.assertFalse(result["founder_approval_required"])

    def test_critical_alert_requires_founder_approval(self):
        assessment = {
            "resilience_score": 40,
            "active_alerts": [{"area": "safe_mode:ai_generation", "severity": "critical", "detail": "x"}],
        }
        with patch("resilience_monitor.assess_resilience", return_value=assessment):
            result = gc._member_resilience()
        self.assertTrue(result["founder_approval_required"])
        self.assertIn("safe_mode:ai_generation", result["risk"])


class TestMemberInnovation(unittest.TestCase):
    def test_no_bottlenecks_no_proposals(self):
        report = {"bottlenecks": {"detected": False, "reason": "none"}}
        with patch("evolution_engine.build_evolution_report", return_value=report), \
             patch("tool_intelligence.proposals.list_proposals", return_value=[]):
            result = gc._member_innovation()
        self.assertEqual(result["recommendation"], "لا إجراء عاجل")

    def test_detected_bottlenecks_surface_in_evidence(self):
        report = {"bottlenecks": {"detected": True, "items": [{"evidence": "slow builds"}]}}
        with patch("evolution_engine.build_evolution_report", return_value=report), \
             patch("tool_intelligence.proposals.list_proposals", return_value=[{"tool": "fix it", "id": "p1"}]):
            result = gc._member_innovation()
        self.assertIn("slow builds", result["risk"])
        self.assertIn("proposal: fix it", result["evidence"])


class TestMemberExecutiveMemory(unittest.TestCase):
    def test_no_history_is_no_data(self):
        with patch("decision_engine.store.find_decisions_by_niche", return_value=[]):
            result = gc._member_executive_memory("n")
        self.assertEqual(result["stance"], "no_data")

    def test_deferred_status_requires_founder_approval(self):
        history = [{"decision_id": "d1", "status": "DEFERRED", "decided_at": "t", "reasoning": ["x"]}]
        with patch("decision_engine.store.find_decisions_by_niche", return_value=history), \
             patch("decision_engine.store.read_outcomes", return_value=iter([])):
            result = gc._member_executive_memory("n")
        self.assertTrue(result["founder_approval_required"])

    def test_matched_outcome_is_cited_in_evidence(self):
        history = [{"decision_id": "d1", "status": "ACCEPTED", "decided_at": "t", "reasoning": []}]
        outcomes = [{"decision_id": "d1", "matched": True, "match_method": "niche_substring"}]
        with patch("decision_engine.store.find_decisions_by_niche", return_value=history), \
             patch("decision_engine.store.read_outcomes", return_value=iter(outcomes)):
            result = gc._member_executive_memory("n")
        self.assertTrue(any("real_outcome" in e for e in result["evidence"]))
        self.assertFalse(result["founder_approval_required"])


def _member(member, stance, confidence=1.0, founder_approval_required=False, evidence=None, risk="r", raw=None):
    return gc._result(
        member, f"opinion for {member}", confidence, evidence or [f"{member} evidence"], risk,
        f"recommendation for {member}", founder_approval_required, stance=stance, raw=raw,
    )


class TestConveneCouncil(unittest.TestCase):
    def _patches(self, strategic=None, market=None, production=None, customer=None,
                 financial=None, security=None, resilience=None, innovation=None, memory=None):
        strategic = strategic if strategic is not None else _member("Strategic Intelligence Core", "informational_context")
        market = market if market is not None else _member("Market Intelligence", "informational_context")
        production = production if production is not None else _member("Production Intelligence", "informational_context")
        customer = customer if customer is not None else _member("Customer Intelligence", "informational_context")
        financial = financial if financial is not None else _member("Financial Intelligence", "informational_context")
        security = security if security is not None else _member("Security Intelligence", "informational_context")
        resilience = resilience if resilience is not None else _member("Resilience Intelligence", "informational_context")
        innovation = innovation if innovation is not None else _member("Innovation Intelligence", "informational_context")
        memory = memory if memory is not None else _member("Executive Memory", "informational_context")
        return (
            patch("galaxy_council._member_strategic", return_value=strategic),
            patch("galaxy_council._member_market", return_value=market),
            patch("galaxy_council._member_production", return_value=production),
            patch("galaxy_council._member_customer", return_value=customer),
            patch("galaxy_council._member_financial", return_value=financial),
            patch("galaxy_council._member_security", return_value=security),
            patch("galaxy_council._member_resilience", return_value=resilience),
            patch("galaxy_council._member_innovation", return_value=innovation),
            patch("galaxy_council._member_executive_memory", return_value=memory),
        )

    def test_all_informational_gives_no_voting_members_honest_state(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            session = gc.convene_council("n")
        self.assertFalse(session["disagreement_detected"])
        self.assertEqual(session["council_confidence"], "Unknown")
        self.assertIn("لا عضو واحد لديه إشارة تصويت حقيقية", session["council_recommendation"])

    def test_unanimous_proceed_gives_a_real_aggregate_confidence(self):
        financial = _member("Financial Intelligence", "proceed", confidence=0.8)
        production = _member("Production Intelligence", "proceed", confidence=1.0)
        patches = self._patches(financial=financial, production=production)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            session = gc.convene_council("n")
        self.assertFalse(session["disagreement_detected"])
        self.assertEqual(session["council_confidence"], 0.9)
        self.assertIn("استمر", session["council_recommendation"])
        self.assertEqual(session["disagreeing_members"], [])

    def test_disagreeing_stances_are_never_averaged_into_a_fake_consensus(self):
        financial = _member("Financial Intelligence", "hold", founder_approval_required=True)
        production = _member("Production Intelligence", "proceed")
        patches = self._patches(financial=financial, production=production)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            session = gc.convene_council("n")
        self.assertTrue(session["disagreement_detected"])
        self.assertEqual(session["council_confidence"], "Unknown")
        self.assertEqual(session["council_recommendation"], "SPLIT — انظر disagreeing_members، لا إجماع حقيقي")
        member_names = {d["member"] for d in session["disagreeing_members"]}
        self.assertEqual(member_names, {"Financial Intelligence", "Production Intelligence"})

    def test_no_data_and_informational_members_never_count_toward_disagreement(self):
        production = _member("Production Intelligence", "no_data")
        market = _member("Market Intelligence", "informational_context")
        financial = _member("Financial Intelligence", "proceed")
        patches = self._patches(financial=financial, production=production, market=market)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            session = gc.convene_council("n")
        self.assertFalse(session["disagreement_detected"])

    def test_founder_approval_required_is_true_if_any_single_member_flags_it(self):
        resilience = _member("Resilience Intelligence", "informational_context", founder_approval_required=True)
        patches = self._patches(resilience=resilience)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            session = gc.convene_council("n")
        self.assertTrue(session["founder_approval_required"])

    def test_expected_impact_and_long_term_effect_cite_strategics_raw_dims_not_a_second_call(self):
        raw = {
            "strategic_value": {"value": 80, "source": "s", "reason": "r"},
            "long_term_value": {"value": "High", "source": "s2", "reason": "r2"},
        }
        strategic = _member("Strategic Intelligence Core", "informational_context", raw=raw)
        with patch("strategic_intelligence_core.strategic_score") as mock_score:
            patches = self._patches(strategic=strategic)
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
                session = gc.convene_council("n")
        mock_score.assert_not_called()
        self.assertEqual(session["expected_impact"]["value"], 80)
        self.assertEqual(session["long_term_effect"]["value"], "High")

    def test_supporting_evidence_and_risks_include_every_member(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            session = gc.convene_council("n")
        self.assertEqual(len(session["risks"]), 9)
        for member in ("Strategic Intelligence Core", "Market Intelligence", "Production Intelligence",
                       "Customer Intelligence", "Financial Intelligence", "Security Intelligence",
                       "Resilience Intelligence", "Innovation Intelligence", "Executive Memory"):
            self.assertTrue(any(member in r for r in session["risks"]))


class TestRecordCouncilRecommendation(unittest.TestCase):
    def _session(self, unified_stance="proceed", disagreement_detected=False, recommendation="استمر"):
        return {
            "niche": "n", "convened_at": "2026-07-29T00:00:00+00:00",
            "members": [_member("Financial Intelligence", "proceed")],
            "council_recommendation": recommendation,
            "unified_stance": unified_stance,
            "disagreement_detected": disagreement_detected,
        }

    def test_is_genuinely_append_only_across_two_calls(self):
        path = _temp_path()
        try:
            gc.record_council_recommendation(self._session(), path=path)
            gc.record_council_recommendation(self._session(), path=path)
            with open(path, encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            self.assertEqual(len(lines), 2)
        finally:
            os.remove(path)

    def test_record_carries_the_real_decision_id_when_given(self):
        path = _temp_path()
        try:
            record = gc.record_council_recommendation(self._session(), decision_id="d1", path=path)
            self.assertEqual(record["decision_id"], "d1")
        finally:
            os.remove(path)


class TestCouncilLearningSummary(unittest.TestCase):
    def test_no_recommendations_is_honestly_not_enough_evidence(self):
        path = _temp_path()
        result = gc.council_learning_summary(recommendations_path=path)
        self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")
        self.assertEqual(result["reviews"], [])

    def test_pending_when_no_founder_decision_followed_yet(self):
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"council_id":"c1","niche":"n","convened_at":"2026-07-29T00:00:00+00:00","council_recommendation":"استمر","unified_stance":"proceed","disagreement_detected":false}\n')
            with patch("decision_engine.store.find_decisions_by_niche", return_value=[]), \
                 patch("decision_engine.store.read_outcomes", return_value=iter([])):
                result = gc.council_learning_summary(recommendations_path=path)
            self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")
            self.assertEqual(result["reviews"][0]["recommendation_vs_decision"], "pending")
            self.assertEqual(result["reviews"][0]["decision_vs_outcome"], "too_soon_to_tell")
        finally:
            os.remove(path)

    def test_matched_when_council_proceed_and_founder_accepted(self):
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"council_id":"c1","niche":"n","convened_at":"2026-07-29T00:00:00+00:00","council_recommendation":"استمر","unified_stance":"proceed","disagreement_detected":false}\n')
            decision = {"decision_id": "d1", "status": "ACCEPTED", "decided_at": "2026-07-29T01:00:00+00:00"}
            outcome = {"decision_id": "d1", "matched": True, "match_method": "x"}
            with patch("decision_engine.store.find_decisions_by_niche", return_value=[decision]), \
                 patch("decision_engine.store.read_outcomes", return_value=iter([outcome])):
                result = gc.council_learning_summary(recommendations_path=path)
            review = result["reviews"][0]
            self.assertEqual(review["recommendation_vs_decision"], "matched")
            self.assertEqual(review["decision_vs_outcome"], "matched")
            self.assertEqual(result["real_triples"], 1)
            self.assertEqual(result["matched_all_the_way"], 1)
        finally:
            os.remove(path)

    def test_diverged_when_council_proceed_but_founder_rejected(self):
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"council_id":"c1","niche":"n","convened_at":"2026-07-29T00:00:00+00:00","council_recommendation":"استمر","unified_stance":"proceed","disagreement_detected":false}\n')
            decision = {"decision_id": "d1", "status": "REJECTED", "decided_at": "2026-07-29T01:00:00+00:00"}
            with patch("decision_engine.store.find_decisions_by_niche", return_value=[decision]), \
                 patch("decision_engine.store.read_outcomes", return_value=iter([])):
                result = gc.council_learning_summary(recommendations_path=path)
            self.assertEqual(result["reviews"][0]["recommendation_vs_decision"], "diverged")
        finally:
            os.remove(path)

    def test_split_council_gives_honest_no_clear_position_never_a_forced_match(self):
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"council_id":"c1","niche":"n","convened_at":"2026-07-29T00:00:00+00:00","council_recommendation":"SPLIT","unified_stance":null,"disagreement_detected":true}\n')
            decision = {"decision_id": "d1", "status": "ACCEPTED", "decided_at": "2026-07-29T01:00:00+00:00"}
            with patch("decision_engine.store.find_decisions_by_niche", return_value=[decision]), \
                 patch("decision_engine.store.read_outcomes", return_value=iter([])):
                result = gc.council_learning_summary(recommendations_path=path)
            self.assertEqual(result["reviews"][0]["recommendation_vs_decision"], "no_clear_council_position")
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()

"""Tests for executive_board.py (Executive Directive, 2026-07-22).

Runs with stdlib unittest. No live network calls, no live LLM calls --
every executive is a deterministic function over already-real,
already-computed evidence. enterprise_readiness.py's real functions are
mocked to control exactly what evidence each test exercises.

    python -m unittest tests.test_executive_board -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import executive_board as eb


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


def _crit(status, reason="x", evidence=None):
    return {"status": status, "evidence": evidence, "reason": reason}


class TestSharedVoteRule(unittest.TestCase):
    def test_a_real_fail_among_relevant_criteria_rejects(self):
        result = eb._vote_from({"a": _crit("FAIL"), "b": _crit("PASS")})
        self.assertEqual(result["vote"], "REJECT")

    def test_all_unknown_defers_never_guesses(self):
        result = eb._vote_from({"a": _crit("UNKNOWN"), "b": _crit("UNKNOWN")})
        self.assertEqual(result["vote"], "DEFER")
        self.assertEqual(result["confidence"], 0.0)

    def test_known_evidence_with_no_fails_approves(self):
        result = eb._vote_from({"a": _crit("PASS"), "b": _crit("INFO")})
        self.assertEqual(result["vote"], "APPROVE")
        self.assertEqual(result["confidence"], 1.0)

    def test_confidence_is_a_real_fraction_of_known_evidence(self):
        result = eb._vote_from({"a": _crit("PASS"), "b": _crit("UNKNOWN")})
        self.assertEqual(result["confidence"], 0.5)
        self.assertEqual(result["vote"], "APPROVE")  # known evidence has no fail

    def test_empty_relevant_criteria_defers(self):
        result = eb._vote_from({})
        self.assertEqual(result["vote"], "DEFER")


class TestIndividualExecutives(unittest.TestCase):
    def test_cto_rejects_on_real_technical_infeasibility(self):
        criteria = {"technical_feasibility": _crit("FAIL"), "infrastructure_readiness": _crit("FAIL"), "automation_readiness": _crit("PASS")}
        result = eb.analyze_as_cto(criteria, {})
        self.assertEqual(result["role"], "CTO")
        self.assertEqual(result["vote"], "REJECT")

    def test_cfo_defers_with_no_real_financial_data(self):
        criteria = {"operational_cost": _crit("UNKNOWN"), "revenue_model_sustainability": _crit("UNKNOWN")}
        result = eb.analyze_as_cfo(criteria, {})
        self.assertEqual(result["vote"], "DEFER")

    def test_cco_flags_real_customer_success_failure(self):
        criteria = {"customer_retention_potential": _crit("UNKNOWN")}
        product_review = {"customer_success": _crit("FAIL", "churn detected"), "support": _crit("PASS")}
        result = eb.analyze_as_cco(criteria, product_review)
        self.assertEqual(result["vote"], "REJECT")
        self.assertTrue(any("customer_success" in r for r in result["risks"]))

    def test_cro_risk_carries_real_exit_criteria_and_kill_switches(self):
        risk_register = {
            "market_risk": _crit("PASS"), "technical_risk": _crit("PASS"),
            "regulatory_risk": _crit("PASS"), "competitive_risk": _crit("PASS"),
            "execution_risk": _crit("PASS"),
            "exit_criteria": ["real exit rule"], "kill_switch_conditions": ["real kill rule"],
        }
        result = eb.analyze_as_cro_risk(risk_register)
        self.assertEqual(result["role"], "Chief Risk Officer")
        self.assertEqual(result["exit_criteria"], ["real exit rule"])
        self.assertEqual(result["kill_switch_conditions"], ["real kill rule"])

    def test_ceo_defers_on_pre_gate_product(self):
        result = eb.analyze_as_ceo({"final_status": "PRE_GATE — x", "hard_failures": [], "risk_register": {}})
        self.assertEqual(result["vote"], "DEFER")

    def test_ceo_rejects_on_real_hard_failures(self):
        result = eb.analyze_as_ceo({"final_status": "REJECTED", "hard_failures": ["support"], "risk_register": {}})
        self.assertEqual(result["vote"], "REJECT")

    def test_ceo_approves_clean_gate(self):
        result = eb.analyze_as_ceo({"final_status": "APPROVED", "hard_failures": [], "risk_register": {"gate_result": {"human_review_required": False}}})
        self.assertEqual(result["vote"], "APPROVE")

    def test_cmio_surfaces_real_undetected_risk_categories(self):
        criteria = {"market_saturation_competitor_quality": _crit("PASS"), "customer_pain_evidence": _crit("PASS")}
        risk_intel = {
            "customer_complaints": _crit("UNKNOWN"), "regulation_changes": _crit("UNKNOWN"),
            "pricing_changes": _crit("UNKNOWN"), "technology_disruption": _crit("UNKNOWN"), "demand_decline": _crit("UNKNOWN"),
        }
        result = eb.analyze_as_cmio(criteria, risk_intel)
        self.assertEqual(len(result["missing_evidence"]), 5)


class TestTally(unittest.TestCase):
    def _execs(self, votes):
        return [{"role": f"role{i}", "vote": v} for i, v in enumerate(votes)]

    def test_production_majority_approves_at_six_of_ten(self):
        votes = ["APPROVE"] * 6 + ["DEFER"] * 4
        tally = eb._tally(self._execs(votes), "production")
        self.assertEqual(tally["board_decision"], "APPROVED")

    def test_production_a_single_reject_blocks_even_with_majority_approve(self):
        votes = ["APPROVE"] * 8 + ["REJECT"] + ["DEFER"]
        tally = eb._tally(self._execs(votes), "production")
        self.assertEqual(tally["board_decision"], "NOT_APPROVED")

    def test_production_five_of_ten_is_not_a_majority(self):
        votes = ["APPROVE"] * 5 + ["DEFER"] * 5
        tally = eb._tally(self._execs(votes), "production")
        self.assertEqual(tally["board_decision"], "NOT_APPROVED")

    def test_irreversible_requires_unanimous_approval(self):
        votes = ["APPROVE"] * 9 + ["DEFER"]
        tally = eb._tally(self._execs(votes), "irreversible")
        self.assertEqual(tally["board_decision"], "NOT_APPROVED")

    def test_irreversible_unanimous_approves(self):
        votes = ["APPROVE"] * 10
        tally = eb._tally(self._execs(votes), "irreversible")
        self.assertEqual(tally["board_decision"], "APPROVED")

    def test_invalid_decision_type_raises(self):
        with self.assertRaises(ValueError):
            eb.convene_board({}, decision_type="not_a_real_type")


class TestConveneBoard(unittest.TestCase):
    def setUp(self):
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()

    def tearDown(self):
        for p in (self.board_path, self.alerts_path):
            if os.path.exists(p):
                os.remove(p)

    def _mock_readiness_result(self, all_pass=True):
        status = "PASS" if all_pass else "FAIL"
        criteria = {k: _crit(status) for k in (
            "customer_pain_evidence", "willingness_to_pay_evidence", "market_saturation_competitor_quality",
            "technical_feasibility", "legal_compliance_risk", "delivery_capability", "scalability",
            "defensibility", "long_term_strategic_value", "revenue_model_sustainability",
            "brand_reputation_risk", "operational_cost", "customer_acquisition_difficulty",
            "customer_retention_potential", "infrastructure_readiness", "automation_readiness",
            "data_confidence_score", "evidence_freshness",
        )}
        product_review = {k: _crit(status) for k in (
            "legal", "security", "privacy", "operational", "financial",
            "scalability", "maintenance", "customer_success", "support", "competitive_moat",
        )}
        return {
            "niche": "test niche", "title": "test niche", "pre_gate_product": False,
            "final_status": "APPROVED" if all_pass else "REJECTED",
            "hard_failures": [] if all_pass else ["support"],
            "product_review": product_review,
            "risk_register": {
                "market_risk": criteria["market_saturation_competitor_quality"], "technical_risk": criteria["technical_feasibility"],
                "regulatory_risk": criteria["legal_compliance_risk"], "competitive_risk": criteria["defensibility"],
                "execution_risk": criteria["data_confidence_score"],
                "exit_criteria": ["x"], "kill_switch_conditions": ["x"],
                "gate_result": {"criteria": criteria, "human_review_required": False, "human_review_reasons": []},
            },
            "documentation_completeness": {"changelog": _crit(status)},
        }

    def test_convene_board_writes_one_real_meeting(self):
        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result(all_pass=True)):
            meeting = eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path)
        self.assertEqual(len(meeting["executives"]), 10)
        with open(self.board_path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    def test_all_clean_evidence_approves_the_board(self):
        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result(all_pass=True)):
            meeting = eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path)
        self.assertEqual(meeting["tally"]["board_decision"], "APPROVED")

    def test_real_failures_reject_the_board(self):
        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result(all_pass=False)):
            meeting = eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path)
        self.assertEqual(meeting["tally"]["board_decision"], "NOT_APPROVED")

    def test_never_triggers_risk_intelligence_unless_explicitly_requested(self):
        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result()), \
             patch("enterprise_readiness.run_risk_intelligence_scan") as mock_scan:
            eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path, include_risk_intelligence=False)
            mock_scan.assert_not_called()
            eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path, include_risk_intelligence=True)
            mock_scan.assert_called_once()

    def test_meeting_carries_the_6_lens_strategic_brief_and_decision_summary(self):
        """Executive Board Integration (2026-07-23): every real board
        decision must automatically include the 6 lenses and produce the
        6-field decision summary."""
        risk_intel = {
            "market_saturation": _crit("PASS"), "customer_complaints": _crit("PASS"),
            "threat_assessment": {"competitor_saturation": {"level": "متوسط", "score": 50, "basis": "x"}},
        }
        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result(all_pass=True)), \
             patch("enterprise_readiness.run_risk_intelligence_scan", return_value=risk_intel), \
             patch("revenue_pipeline.plan.estimate_production_cost", return_value={"maturity": "DISCOVERY", "reason": "x"}):
            meeting = eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path)

        brief = meeting["strategic_brief"]
        for lens in ("threat_assessment", "opportunity_assessment", "market_intelligence",
                     "financial_impact", "technical_risk", "customer_trust_impact"):
            self.assertIn(lens, brief)
        self.assertEqual(brief["threat_assessment"]["competitor_saturation"], risk_intel["threat_assessment"]["competitor_saturation"])
        # Market Evidence & Alerting layer (2026-07-23): active_alerts is
        # attached on top of whatever run_risk_intelligence_scan() already
        # returned -- a real, isolated, read-only lookup, honestly empty here.
        self.assertEqual(brief["threat_assessment"]["active_alerts"]["total"], 0)

        summary = meeting["decision_summary"]
        for field in ("decision", "confidence", "evidence", "risks", "recommended_actions", "follow_up_tasks"):
            self.assertIn(field, summary)
        self.assertEqual(summary["decision"], "APPROVED")
        self.assertEqual(summary["risks"], [])

    def test_strategic_brief_surfaces_a_real_persisted_alert(self):
        """Market Evidence & Alerting layer (2026-07-23): a real,
        already-scanned alert for this niche must reach the board's
        Threat Assessment lens automatically, isolated to alerts_path."""
        import market_alerts
        me_evidence_path = _temp_path()
        try:
            import market_evidence as me
            me.record_evidence(
                "test niche", "competitor_pricing_change",
                {"competitor": "Acme", "source_url": "https://example.com/pricing"},
                evidence_path=me_evidence_path,
            )
            market_alerts.scan_market_alerts("test niche", evidence_path=me_evidence_path, alerts_path=self.alerts_path)
        finally:
            if os.path.exists(me_evidence_path):
                os.remove(me_evidence_path)

        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result(all_pass=True)), \
             patch("enterprise_readiness.run_risk_intelligence_scan", return_value=None), \
             patch("revenue_pipeline.plan.estimate_production_cost", return_value={"maturity": "DISCOVERY", "reason": "x"}):
            meeting = eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path)

        active_alerts = meeting["strategic_brief"]["threat_assessment"]["active_alerts"]
        self.assertEqual(active_alerts["total"], 1)
        self.assertEqual(active_alerts["by_severity_counts"]["High"], 1)

    def test_decision_summary_recommended_actions_trace_to_real_risks(self):
        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result(all_pass=False)), \
             patch("enterprise_readiness.run_risk_intelligence_scan", return_value=None), \
             patch("revenue_pipeline.plan.estimate_production_cost", return_value={"maturity": "DISCOVERY", "reason": "x"}):
            meeting = eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path)

        summary = meeting["decision_summary"]
        self.assertEqual(summary["decision"], "NOT_APPROVED")
        self.assertGreater(len(summary["risks"]), 0)
        self.assertTrue(any(r.replace("عالج: ", "") in summary["risks"][0] for r in summary["recommended_actions"][:1]))
        self.assertTrue(all(a.startswith("عالج:") or a.startswith("اجمع دليلاً") for a in summary["recommended_actions"]))

    def test_strategic_brief_threat_assessment_is_honest_when_risk_intelligence_skipped(self):
        with patch("enterprise_readiness.run_enterprise_readiness_gate", return_value=self._mock_readiness_result(all_pass=True)):
            meeting = eb.convene_board({"niche": "test niche"}, board_path=self.board_path, alerts_path=self.alerts_path, include_risk_intelligence=False)
        self.assertIn("note", meeting["strategic_brief"]["threat_assessment"])


class TestGetLatestBoardBrief(unittest.TestCase):
    def setUp(self):
        self.board_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.board_path):
            os.remove(self.board_path)

    def test_no_meeting_yet_is_honestly_reported(self):
        result = eb.get_latest_board_brief("never convened niche", board_path=self.board_path)
        self.assertFalse(result["has_meeting"])

    def test_returns_the_latest_real_meeting_for_the_niche(self):
        older = {"niche": "n", "convened_at": "2026-07-01T00:00:00+00:00",
                 "tally": {"board_decision": "NOT_APPROVED"}, "decision_summary": {"decision": "NOT_APPROVED"}}
        newer = {"niche": "n", "convened_at": "2026-07-23T00:00:00+00:00",
                 "tally": {"board_decision": "APPROVED"}, "decision_summary": {"decision": "APPROVED"}}
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(older) + "\n")
            f.write(json.dumps(newer) + "\n")
        result = eb.get_latest_board_brief("n", board_path=self.board_path)
        self.assertTrue(result["has_meeting"])
        self.assertEqual(result["board_decision"], "APPROVED")
        self.assertEqual(result["convened_at"], "2026-07-23T00:00:00+00:00")


class TestReviewBoardTrackRecord(unittest.TestCase):
    def setUp(self):
        self.board_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.board_path):
            os.remove(self.board_path)

    def _write_meeting(self, niche, board_decision):
        meeting = {"niche": niche, "convened_at": "2026-07-22T00:00:00+00:00", "tally": {"board_decision": board_decision}}
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meeting) + "\n")

    def test_no_real_evidence_since_is_honestly_too_soon(self):
        self._write_meeting("n", "APPROVED")
        with patch("market_evidence.summarize_niche", return_value={"total_events": 0}):
            reviews = eb.review_board_track_record("n", board_path=self.board_path)
        self.assertIsNone(reviews[0]["prediction_matched_reality"])
        self.assertIn("مبكر", reviews[0]["outcome_note"])

    def test_real_positive_evidence_confirms_a_real_approval(self):
        self._write_meeting("n", "APPROVED")
        summary = {"total_events": 2, "willingness_to_pay": {"positive_signals": 2, "pricing_objections": 0}}
        with patch("market_evidence.summarize_niche", return_value=summary):
            reviews = eb.review_board_track_record("n", board_path=self.board_path)
        self.assertTrue(reviews[0]["prediction_matched_reality"])

    def test_real_negative_evidence_contradicts_a_real_approval(self):
        self._write_meeting("n", "APPROVED")
        summary = {"total_events": 2, "willingness_to_pay": {"positive_signals": 0, "pricing_objections": 2}}
        with patch("market_evidence.summarize_niche", return_value=summary):
            reviews = eb.review_board_track_record("n", board_path=self.board_path)
        self.assertFalse(reviews[0]["prediction_matched_reality"])

    def test_empty_ledger_returns_empty_not_an_error(self):
        reviews = eb.review_board_track_record("anything", board_path=self.board_path)
        self.assertEqual(reviews, [])


if __name__ == "__main__":
    unittest.main()

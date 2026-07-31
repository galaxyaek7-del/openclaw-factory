"""Tests for enterprise_factory_audit.py (Enterprise End-to-End Factory
Audit, ADR-169, 2026-07-31): 17-subsystem audit + pipeline simulation +
score/question synthesis, over injected fixtures -- never depends on a
live 5+ minute reality_audit.py/truth_registry.py re-scan.

    python -m unittest tests.test_enterprise_factory_audit -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import enterprise_factory_audit as efa


class TestAuditSubsystem(unittest.TestCase):
    def test_all_17_named_subsystems_have_manual_citations(self):
        for name in efa.SUBSYSTEMS:
            self.assertIn(name, efa._MANUAL_CITATIONS, f"{name} missing a real citation entry")

    def test_no_subsystem_falls_back_to_generic_placeholder(self):
        placeholder_markers = ("No real risk signal captured", "Not assessed by this scan", "UNKNOWN -- no real signal")
        for name in efa.SUBSYSTEMS:
            manual = efa._MANUAL_CITATIONS[name]
            for field in ("risks", "missing", "business_value", "tech_debt", "priority"):
                self.assertNotIn(manual.get(field, ""), placeholder_markers)

    def test_unknown_subsystem_is_honest(self):
        entry = efa.audit_subsystem("Not A Real Subsystem", truth_reg=None, tr_report=None, cheap=None, test_count=None)
        self.assertEqual(entry["exists"], "UNKNOWN")


class TestPublishingProductionReadyOverride(unittest.TestCase):
    def test_publishing_ignores_code_level_ready_when_zero_real_published(self):
        # Even if truth_registry shows every Publishing-category module
        # as READY, real config/reality.json ground truth must win.
        fake_tr = [{"name": "channels.ledger", "category": "channels", "status": "READY"}] * 10
        entry = efa.audit_subsystem("Publishing", truth_reg=fake_tr, tr_report=None, cheap=None, test_count=None)
        self.assertEqual(entry["production_ready"], "NO")


class TestDecisionEngineProductionReadyOverride(unittest.TestCase):
    def test_decision_engine_reflects_real_live_accepted_count(self):
        entry = efa.audit_subsystem("Decision Engine", truth_reg=None, tr_report=None, cheap=None, test_count=None)
        # Real, live check -- whatever the true current ACCEPTED count is,
        # production_ready must match it exactly (YES iff > 0).
        import sys
        from decision_engine import store
        decs = store.latest_decision_per_niche()
        accepted = [n for n, d in decs.items() if d.get("status") == "ACCEPTED"]
        expected = "YES" if accepted else "NO"
        self.assertEqual(entry["production_ready"], expected)


class TestSimulatePipeline(unittest.TestCase):
    def test_returns_all_7_named_stages_in_order(self):
        result = efa.simulate_pipeline()
        names = [s["stage"] for s in result["stages"]]
        self.assertEqual(names, [
            "Market opportunity", "Decision", "Production", "Quality Control",
            "Publishing", "Monitoring", "Revenue Recording",
        ])

    def test_never_fakes_a_step_every_stage_has_real_evidence_string(self):
        result = efa.simulate_pipeline()
        for s in result["stages"]:
            self.assertTrue(s["evidence"])
            self.assertIsInstance(s["evidence"], str)

    def test_disclosed_never_asserts_broken_code_when_only_data_is_empty(self):
        result = efa.simulate_pipeline()
        self.assertIn("real CODE PATH is broken", result["note"])


class TestComputeEnterpriseScores(unittest.TestCase):
    def test_never_fabricates_a_numeric_score_for_qualitative_dimensions(self):
        fake_subsystems = [{"production_ready": "YES", "working": "YES"}] * 17
        fake_pipeline = {"stages": []}
        fake_extra = {"tr_report": {"10_enterprise_truth_score": {"score_0_to_100": 50.0}}, "cheap": {"resilience": {"resilience_score": 80}}, "test_count": 100}
        scores = efa.compute_enterprise_scores(fake_subsystems, fake_pipeline, fake_extra)
        for dim in ("automation", "scalability"):
            self.assertFalse(isinstance(scores[dim]["value"], (int, float)))

    def test_overall_excludes_non_numeric_dimensions_rather_than_forcing_zero(self):
        fake_subsystems = [{"production_ready": "YES", "working": "YES"}] * 17
        fake_pipeline = {"stages": []}
        fake_extra = {"tr_report": {}, "cheap": {"resilience": {}}, "test_count": 0}
        scores = efa.compute_enterprise_scores(fake_subsystems, fake_pipeline, fake_extra)
        overall = scores["overall_enterprise_score"]
        self.assertGreater(len(overall["excluded_dimensions"]), 0)


class TestAnswerFinalQuestions(unittest.TestCase):
    def test_ranks_by_disclosed_priority_not_just_binary_flag(self):
        subsystems = [
            {"name": "A", "production_ready": "NO", "working": "YES", "recommended_priority": "LOW -- fine", "risks": "r"},
            {"name": "B", "production_ready": "NO", "working": "YES", "recommended_priority": "CRITICAL -- urgent", "risks": "r"},
        ]
        answers = efa.answer_final_questions(subsystems, {"stages": []}, {})
        top = answers["2_ten_highest_priority_weaknesses"]
        self.assertIn("B [CRITICAL", top[0])

    def test_q1_answer_is_always_a_literal_yes_or_no(self):
        answers = efa.answer_final_questions([], {"stages": []}, {})
        self.assertIn(answers["1_can_operate_today_without_additional_coding"]["answer"], ("YES", "NO"))


if __name__ == "__main__":
    unittest.main()

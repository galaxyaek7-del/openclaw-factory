"""Tests for evolution_queue.py (Autonomous Company Evolution Engine,
2026-07-29): the real Observe->Think->Simulate->Decide->Learn pipeline,
with Execute always human-gated (the founder's own explicit choice).

Every test uses a temp state path and an injected proposal list -- never
the real data/evolution_queue_state.json or the real
tool_intelligence.proposals.list_proposals() output.

    python -m unittest tests.test_evolution_queue -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import evolution_queue as eq


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


def _sample_proposal(pid="test_proposal_1", tool="Test tool", evidence="some_module.py's some_function()"):
    return {
        "id": pid, "tool": tool, "status": "مقترَح، لا تنفيذ",
        "why_needed": "a real reason", "expected_business_value": "a real value",
        "implementation_effort": "low", "estimated_roi": "unmeasured",
        "dependencies": ["a real dependency"], "risks": ["a real risk"],
        "evidence": evidence,
    }


class BaseQueueTest(unittest.TestCase):
    def setUp(self):
        self.state_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.state_path):
            os.remove(self.state_path)


class TestIntakeProposals(BaseQueueTest):
    def test_new_proposal_creates_a_real_record(self):
        result = eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        self.assertEqual(result["added_count"], 1)
        state = eq._load_state(self.state_path)
        self.assertEqual(state["test_proposal_1"]["stage"], "PROPOSED")

    def test_intake_is_idempotent_never_recreates_an_existing_record(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        result = eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        self.assertEqual(result["added_count"], 0)
        state = eq._load_state(self.state_path)
        self.assertEqual(state["test_proposal_1"]["stage"], "SIMULATED", "must not be reset back to PROPOSED")

    def test_proposal_missing_id_is_skipped_never_crashes(self):
        result = eq.intake_proposals(proposals=[{"tool": "no id here"}], state_path=self.state_path)
        self.assertEqual(result["added_count"], 0)


class TestSimulateProposal(BaseQueueTest):
    def test_wrong_stage_is_rejected(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        result = eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_missing_record_is_rejected(self):
        result = eq.simulate_proposal("does_not_exist", state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_real_module_citation_is_extracted_as_affected_module(self):
        proposal = _sample_proposal(evidence="executive_intelligence.bottlenecks.detect_bottlenecks() found a real issue")
        eq.intake_proposals(proposals=[proposal], state_path=self.state_path)
        result = eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        self.assertTrue(result["success"])
        self.assertIn("executive_intelligence.bottlenecks.detect_bottlenecks", result["simulation"]["affected_modules"])

    def test_sensitive_keyword_forces_high_rollback_complexity(self):
        proposal = _sample_proposal(evidence="a real gap in profit_oracle.py's pricing logic")
        eq.intake_proposals(proposals=[proposal], state_path=self.state_path)
        result = eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        self.assertEqual(result["simulation"]["rollback_complexity"], "high")
        self.assertIn("financial", result["simulation"]["sensitive_areas_touched"])

    def test_no_sensitive_keyword_and_single_module_is_low_complexity(self):
        proposal = _sample_proposal(evidence="capability_registry_scanner.find_capability_gaps() flagged 2 gaps")
        eq.intake_proposals(proposals=[proposal], state_path=self.state_path)
        result = eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        self.assertEqual(result["simulation"]["rollback_complexity"], "low")
        self.assertEqual(result["simulation"]["sensitive_areas_touched"], [])


class TestDecideProposal(BaseQueueTest):
    def _simulated(self, evidence="capability_registry_scanner.find_capability_gaps() flagged 2 gaps"):
        eq.intake_proposals(proposals=[_sample_proposal(evidence=evidence)], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)

    def test_wrong_stage_is_rejected(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        result = eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_always_routes_to_awaiting_founder_approval_even_with_no_real_concerns(self):
        self._simulated()
        result = eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "AWAITING_FOUNDER_APPROVAL")
        self.assertFalse(result["decision_flags"]["policy_risk"])

    def test_sensitive_simulation_sets_policy_risk_flag_but_still_only_awaits_approval(self):
        self._simulated(evidence="a real gap in profit_oracle.py's pricing logic")
        result = eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        self.assertEqual(result["stage"], "AWAITING_FOUNDER_APPROVAL", "must never auto-reject, even for a sensitive area")
        self.assertTrue(result["decision_flags"]["policy_risk"])

    def test_three_distinct_modules_sets_duplicate_architecture_risk_flag(self):
        self._simulated(evidence="module_one.func() and module_two.func() and module_three.func()")
        result = eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        self.assertTrue(result["decision_flags"]["duplicate_architecture_risk"])


class TestApproveRejectMarkImplemented(BaseQueueTest):
    def _awaiting_approval(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        eq.decide_proposal("test_proposal_1", state_path=self.state_path)

    def test_approve_requires_awaiting_founder_approval_stage(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        result = eq.approve_proposal("test_proposal_1", state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_approve_succeeds_from_awaiting_founder_approval(self):
        self._awaiting_approval()
        result = eq.approve_proposal("test_proposal_1", decided_by="founder", note="looks good", state_path=self.state_path)
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "APPROVED")
        self.assertEqual(result["founder_decision"]["decision"], "APPROVED")

    def test_reject_succeeds_from_awaiting_founder_approval(self):
        self._awaiting_approval()
        result = eq.reject_proposal("test_proposal_1", reason="not worth it", state_path=self.state_path)
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "REJECTED")
        self.assertEqual(result["founder_decision"]["reason"], "not worth it")

    def test_mark_implemented_requires_approved_stage(self):
        self._awaiting_approval()
        result = eq.mark_implemented("test_proposal_1", state_path=self.state_path)
        self.assertFalse(result["success"], "must not be markable implemented before real founder approval")

    def test_mark_implemented_succeeds_after_approval(self):
        self._awaiting_approval()
        eq.approve_proposal("test_proposal_1", state_path=self.state_path)
        result = eq.mark_implemented("test_proposal_1", note="shipped in commit abc123", state_path=self.state_path)
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "IMPLEMENTED")

    def test_full_stage_history_is_preserved_the_real_learning_history(self):
        self._awaiting_approval()
        eq.approve_proposal("test_proposal_1", state_path=self.state_path)
        result = eq.mark_implemented("test_proposal_1", state_path=self.state_path)
        stages = [h["stage"] for h in result["stage_history"]]
        self.assertEqual(stages, ["PROPOSED", "SIMULATED", "AWAITING_FOUNDER_APPROVAL", "APPROVED", "IMPLEMENTED"])


class TestRunDailyCycle(BaseQueueTest):
    def test_never_advances_past_awaiting_founder_approval(self):
        result = eq.run_daily_cycle(proposals=[_sample_proposal()], state_path=self.state_path)
        self.assertEqual(result["added_count"], 1)
        state = eq._load_state(self.state_path)
        self.assertEqual(state["test_proposal_1"]["stage"], "AWAITING_FOUNDER_APPROVAL")
        self.assertIsNone(state["test_proposal_1"]["founder_decision"], "run_daily_cycle must never call approve/reject")

    def test_only_processes_newly_added_proposals_not_already_in_review(self):
        eq.intake_proposals(proposals=[_sample_proposal("p1")], state_path=self.state_path)
        result = eq.run_daily_cycle(proposals=[_sample_proposal("p1"), _sample_proposal("p2")], state_path=self.state_path)
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["processed"], ["p2"])


class TestListEvolutionQueue(BaseQueueTest):
    def test_empty_queue_is_honest_zero(self):
        result = eq.list_evolution_queue(state_path=self.state_path)
        self.assertEqual(result["stage_distribution"], {})
        self.assertEqual(result["awaiting_approval"], [])
        self.assertEqual(result["entries"], [])

    def test_stage_distribution_and_awaiting_approval_reflect_real_state(self):
        eq.run_daily_cycle(proposals=[_sample_proposal("p1"), _sample_proposal("p2")], state_path=self.state_path)
        eq.approve_proposal("p1", state_path=self.state_path)
        result = eq.list_evolution_queue(state_path=self.state_path)
        self.assertEqual(result["stage_distribution"], {"APPROVED": 1, "AWAITING_FOUNDER_APPROVAL": 1})
        self.assertEqual(len(result["awaiting_approval"]), 1)
        self.assertEqual(result["awaiting_approval"][0]["proposal_id"], "p2")

    def test_stuck_flag_is_honest_and_informational_only(self):
        import datetime as dt
        eq.run_daily_cycle(proposals=[_sample_proposal("p1")], state_path=self.state_path)
        far_future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=100)
        result = eq.list_evolution_queue(state_path=self.state_path, now=far_future)
        self.assertTrue(result["awaiting_approval"][0]["stuck"])
        # Still just informational -- stage must be unchanged.
        state = eq._load_state(self.state_path)
        self.assertEqual(state["p1"]["stage"], "AWAITING_FOUNDER_APPROVAL")


if __name__ == "__main__":
    unittest.main()

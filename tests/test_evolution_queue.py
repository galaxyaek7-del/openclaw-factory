"""Tests for evolution_queue.py (Autonomous Company Evolution Engine,
2026-07-29): the real Observe->Think->Simulate->Decide->Learn pipeline,
with Execute always human-gated (the founder's own explicit choice).

Every test uses a temp state path and an injected proposal list -- never
the real data/evolution_queue_state.json or the real
tool_intelligence.proposals.list_proposals() output.

    python -m unittest tests.test_evolution_queue -v
"""

import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


def _fake_snapshot(now, revenue_avg=None, health_status=None, funnel_answer="Unknown"):
    return {
        "captured_at": now.isoformat(),
        "revenue": {"recent_7d_revenue_usd": revenue_avg, "trailing_daily_avg_usd": revenue_avg, "source": "fake"},
        "reliability": {"latest_health_status": health_status, "source": "fake"},
        "customer_value": {"conversions": None, "answer": funnel_answer, "source": "fake"},
    }


class TestMarkImplementedBaseline(BaseQueueTest):
    """Autonomous Evolution Engine directive, Round 2 (2026-07-30):
    mark_implemented() must capture a real baseline snapshot -- the
    "before" half of the outcome-measurement pipeline."""

    def _approved(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        eq.approve_proposal("test_proposal_1", state_path=self.state_path)

    def test_baseline_snapshot_and_implemented_at_are_captured(self):
        self._approved()
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(dt.datetime.now(dt.timezone.utc), revenue_avg=10.0, health_status="healthy")):
            result = eq.mark_implemented("test_proposal_1", state_path=self.state_path)
        self.assertTrue(result["success"])
        self.assertEqual(result["baseline_snapshot"]["revenue"]["trailing_daily_avg_usd"], 10.0)
        self.assertIsNotNone(result["implemented_at"])
        self.assertEqual(result["outcome_measurements"], [])

    def test_snapshot_capture_failure_does_not_block_the_real_state_transition(self):
        self._approved()
        with patch.object(eq, "_capture_metrics_snapshot", side_effect=RuntimeError("boom")):
            result = eq.mark_implemented("test_proposal_1", state_path=self.state_path)
        self.assertTrue(result["success"], "a snapshot failure must never block the real IMPLEMENTED transition itself")
        self.assertIn("error", result["baseline_snapshot"])


class TestMeasureOutcome(BaseQueueTest):
    def _implemented(self, now, revenue_avg=10.0, health_status="healthy"):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        eq.approve_proposal("test_proposal_1", state_path=self.state_path)
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(now, revenue_avg=revenue_avg, health_status=health_status)):
            eq.mark_implemented("test_proposal_1", state_path=self.state_path, now=now)

    def test_wrong_stage_is_rejected(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        result = eq.measure_outcome("test_proposal_1", state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_refuses_to_measure_before_min_days_elapsed(self):
        now = dt.datetime.now(dt.timezone.utc)
        self._implemented(now)
        result = eq.measure_outcome("test_proposal_1", state_path=self.state_path, now=now + dt.timedelta(days=1))
        self.assertFalse(result["success"])
        self.assertTrue(result["not_enough_time"])

    def test_improved_revenue_and_reliability_are_reported_honestly(self):
        now = dt.datetime.now(dt.timezone.utc)
        self._implemented(now, revenue_avg=10.0, health_status="degraded")
        later = now + dt.timedelta(days=8)
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(later, revenue_avg=20.0, health_status="healthy")):
            result = eq.measure_outcome("test_proposal_1", state_path=self.state_path, now=later)
        self.assertTrue(result["success"])
        verdicts = result["measurement"]["verdicts"]
        self.assertEqual(verdicts["revenue"], "IMPROVED")
        self.assertEqual(verdicts["reliability"], "IMPROVED")
        self.assertIn("NO_REAL_SIGNAL", verdicts["scalability"])
        self.assertIn("NO_REAL_SIGNAL", verdicts["automation"])

    def test_degraded_revenue_is_reported_honestly_never_hidden(self):
        now = dt.datetime.now(dt.timezone.utc)
        self._implemented(now, revenue_avg=20.0, health_status="healthy")
        later = now + dt.timedelta(days=8)
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(later, revenue_avg=5.0, health_status="critical")):
            result = eq.measure_outcome("test_proposal_1", state_path=self.state_path, now=later)
        verdicts = result["measurement"]["verdicts"]
        self.assertEqual(verdicts["revenue"], "DEGRADED")
        self.assertEqual(verdicts["reliability"], "DEGRADED")

    def test_missing_data_is_not_ever_data(self):
        now = dt.datetime.now(dt.timezone.utc)
        self._implemented(now, revenue_avg=None, health_status=None)
        later = now + dt.timedelta(days=8)
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(later, revenue_avg=None, health_status=None)):
            result = eq.measure_outcome("test_proposal_1", state_path=self.state_path, now=later)
        verdicts = result["measurement"]["verdicts"]
        self.assertEqual(verdicts["revenue"], "NOT_ENOUGH_DATA")
        self.assertEqual(verdicts["reliability"], "NOT_ENOUGH_DATA")

    def test_repeated_measurement_does_not_reset_the_elapsed_time_clock(self):
        """Regression test for a real bug found during implementation:
        _record_history() appends a second stage_history row still tagged
        IMPLEMENTED every time a measurement logs its detail -- deriving
        implemented_at from stage_history each call silently reset the
        elapsed-time gate to zero on every second measurement."""
        now = dt.datetime.now(dt.timezone.utc)
        self._implemented(now)
        later = now + dt.timedelta(days=8)
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(later, revenue_avg=20.0, health_status="healthy")):
            first = eq.measure_outcome("test_proposal_1", state_path=self.state_path, now=later)
            second = eq.measure_outcome("test_proposal_1", state_path=self.state_path, now=later + dt.timedelta(hours=1))
        self.assertTrue(first["success"] and second["success"])
        self.assertGreater(second["measurement"]["elapsed_days"], 7.9, "must still reflect real time since IMPLEMENTED, not reset by the prior measurement")
        state = eq._load_state(self.state_path)
        self.assertEqual(len(state["test_proposal_1"]["outcome_measurements"]), 2)


class TestRunDailyOutcomeMeasurementCycle(BaseQueueTest):
    def test_skips_records_under_the_time_window_honestly(self):
        now = dt.datetime.now(dt.timezone.utc)
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        eq.approve_proposal("test_proposal_1", state_path=self.state_path)
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(now)):
            eq.mark_implemented("test_proposal_1", state_path=self.state_path, now=now)
        result = eq.run_daily_outcome_measurement_cycle(state_path=self.state_path, now=now + dt.timedelta(days=1))
        self.assertEqual(result["measured_count"], 0)
        self.assertEqual(len(result["skipped"]), 1)

    def test_only_touches_implemented_records(self):
        eq.run_daily_cycle(proposals=[_sample_proposal("p1")], state_path=self.state_path)
        result = eq.run_daily_outcome_measurement_cycle(state_path=self.state_path)
        self.assertEqual(result["measured_count"], 0)
        self.assertEqual(result["skipped"], [])


class TestListMeasuredOutcomes(BaseQueueTest):
    def test_empty_is_honest(self):
        result = eq.list_measured_outcomes(state_path=self.state_path)
        self.assertEqual(result["entries"], [])

    def test_implemented_without_measurement_is_honestly_not_yet_measured(self):
        now = dt.datetime.now(dt.timezone.utc)
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        eq.approve_proposal("test_proposal_1", state_path=self.state_path)
        with patch.object(eq, "_capture_metrics_snapshot", return_value=_fake_snapshot(now)):
            eq.mark_implemented("test_proposal_1", state_path=self.state_path, now=now)
        result = eq.list_measured_outcomes(state_path=self.state_path)
        self.assertEqual(result["entries"][0]["status"], "NOT_YET_MEASURED")


class TestRankProposal(BaseQueueTest):
    def test_revenue_keyword_is_tagged_revenue_linked(self):
        eq.intake_proposals(proposals=[_sample_proposal(evidence="customer_pipeline.py shows a real revenue issue")], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        record = eq._load_state(self.state_path)["test_proposal_1"]
        ranking = eq.rank_proposal(record)
        self.assertEqual(ranking["revenue_impact"], "revenue_linked")

    def test_strategic_value_is_honestly_not_computed_never_fabricated(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        record = eq._load_state(self.state_path)["test_proposal_1"]
        ranking = eq.rank_proposal(record)
        self.assertEqual(ranking["strategic_value"]["value"], "not_computed")

    def test_policy_risk_flag_raises_risk_to_high(self):
        eq.intake_proposals(proposals=[_sample_proposal(evidence="a real gap in profit_oracle.py's pricing logic")], state_path=self.state_path)
        eq.simulate_proposal("test_proposal_1", state_path=self.state_path)
        eq.decide_proposal("test_proposal_1", state_path=self.state_path)
        record = eq._load_state(self.state_path)["test_proposal_1"]
        ranking = eq.rank_proposal(record)
        self.assertEqual(ranking["risk"], "high")

    def test_ranking_is_attached_to_list_evolution_queue_entries(self):
        eq.run_daily_cycle(proposals=[_sample_proposal("p1")], state_path=self.state_path)
        result = eq.list_evolution_queue(state_path=self.state_path)
        self.assertIsNotNone(result["entries"][0]["ranking"])


class TestAtomicStateWrite(BaseQueueTest):
    """Resilience & Stress Hardening audit (2026-08-08), Section 5/10 --
    _save_state() now uses the same tmp-file-then-os.replace pattern as
    factory_state.py/safe_mode.py/channels/publish_protection.py."""

    def test_no_leftover_tmp_file_after_a_successful_write(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        directory = os.path.dirname(self.state_path) or "."
        leftover = [f for f in os.listdir(directory) if f.startswith(os.path.basename(self.state_path) + ".tmp-")]
        self.assertEqual(leftover, [])

    def test_existing_real_file_is_never_left_truncated_if_dump_raises(self):
        """Simulates a crash mid-serialization: json.dump() raising
        partway through must never leave the REAL state file
        (only the .tmp file, which is never renamed over it)."""
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        with open(self.state_path, encoding="utf-8") as f:
            original_content = f.read()

        class Unserializable:
            def __repr__(self):
                raise RuntimeError("simulated crash mid-write")

        state = eq._load_state(self.state_path)
        state["__poison__"] = Unserializable()
        with self.assertRaises(TypeError):
            eq._save_state(state, state_path=self.state_path)

        with open(self.state_path, encoding="utf-8") as f:
            after_content = f.read()
        self.assertEqual(original_content, after_content, "the real state file must be byte-for-byte unchanged after a failed write")

    def test_state_survives_and_is_valid_json_after_a_real_write(self):
        eq.intake_proposals(proposals=[_sample_proposal()], state_path=self.state_path)
        import json
        with open(self.state_path, encoding="utf-8") as f:
            parsed = json.load(f)  # must not raise
        self.assertIn("test_proposal_1", parsed)


if __name__ == "__main__":
    unittest.main()

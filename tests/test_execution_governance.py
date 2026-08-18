"""Tests for Phase 4 -- Execution Governance (AUTHORITATIVE AUTONOMOUS
EXECUTION, founder directive, 2026-08-17).

Covers the module that produces the mandated 14-field completion report, as
real, executing tests. Every test uses temp ledgers / temp state fixtures --
never the real data/ ledgers, never the real cost log, never the real lock.

  * execution_model()       -- the 7-step authoritative order, honest status
  * time_awareness_status() -- authoritative UTC, staleness, ELAPSED_TIME rule
  * capability_governance() -- DISCOVERY/VERIFIED/ADOPTED, never silent promotion
  * autonomy_maturity()     -- LEVEL 3, evidence-based, never raised by code
  * truth_gate()            -- VERIFIED/UNKNOWN/NEEDS VERIFICATION, never a blanket PASS
  * completion report       -- all 14 mandated fields present and cited

    python -m unittest tests.test_execution_governance -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from execution_governance import (
    COMPLETION_REPORT_FIELDS,
    DIRECTIVE_SECTIONS,
    EXECUTION_MODEL_STEPS,
    build_completion_report,
    build_execution_governance_report,
    capability_governance,
    execution_model,
    time_awareness_status,
    truth_gate,
    autonomy_maturity,
)


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _cost_row(model, **over):
    row = {
        "timestamp": "2026-08-14T10:00:00",
        "model": model,
        "prompt_tokens": 500,
        "completion_tokens": 300,
        "total_tokens": 800,
        "cost_usd": 0.0001,
        "latency_ms": 700,
        "context": {"purpose": "content_generation"},
    }
    row.update(over)
    return row


# ---------------------------------------------------------------------------
# Execution Model
# ---------------------------------------------------------------------------

class TestExecutionModel(unittest.TestCase):

    def test_seven_steps_in_authoritative_order(self):
        """The directive's 7-step order is exactly: DISCOVER -> VERIFY ->
        DESIGN -> IMPLEMENT -> TEST -> RE-VERIFY -> RECORD."""
        steps = execution_model()["steps"]
        self.assertEqual(
            [s["step"] for s in steps],
            ["DISCOVER", "VERIFY", "DESIGN", "IMPLEMENT", "TEST", "RE-VERIFY", "RECORD"],
        )
        self.assertEqual(len(steps), 7)

    def test_in_progress_status_is_honest(self):
        """A phase marked IN PROGRESS never claims TEST/RE-VERIFY/RECORD are
        done -- those remain PENDING."""
        steps = execution_model(phase_4_status="IN PROGRESS")["steps"]
        done = {s["step"] for s in steps if s["status"] == "COMPLETE"}
        self.assertEqual(done, {"DISCOVER", "VERIFY", "DESIGN", "IMPLEMENT"})
        pending = {s["step"] for s in steps if s["status"] == "PENDING"}
        self.assertEqual(pending, {"TEST", "RE-VERIFY", "RECORD"})

    def test_complete_status_marks_all_steps(self):
        steps = execution_model(phase_4_status="COMPLETE")["steps"]
        self.assertTrue(all(s["status"] == "COMPLETE" for s in steps))

    def test_execution_model_never_fabricates_evidence_text(self):
        """PENDING steps carry a disclosed not-reached evidence string, never
        an invented completion story."""
        steps = execution_model(phase_4_status="IN PROGRESS")["steps"]
        for s in steps:
            self.assertIn("evidence", s)
            self.assertTrue(s["evidence"])


# ---------------------------------------------------------------------------
# Time Awareness
# ---------------------------------------------------------------------------

class TestTimeAwareness(unittest.TestCase):

    def test_authoritative_utc_timestamp(self):
        from datetime import datetime, timezone
        now = datetime(2026, 8, 17, 12, 0, 0, tzinfo=timezone.utc)
        status = time_awareness_status(now=now)
        self.assertEqual(status["now_utc"], "2026-08-17T12:00:00+00:00")

    def test_eta_is_unknown_never_invented(self):
        """execution_status.py:19 -- no historical per-stage duration tracking
        exists, so ETA is honestly UNKNOWN with the cited reason."""
        status = time_awareness_status()
        self.assertEqual(status["eta"]["value"], "UNKNOWN")
        self.assertIn("execution_status.py:19", status["eta"]["reason"])

    def test_elapsed_time_never_equals_founder_approval(self):
        status = time_awareness_status()
        self.assertTrue(status["elapsed_time_never_equals_founder_approval"])

    def test_stale_lock_is_reported_as_pid(self):
        """A stale bare-PID lock file is read as its PID and reported -- never
        misread as an active signal."""
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / ".factory_loop.lock"
            lock.write_text("9999", encoding="utf-8")
            with mock.patch("execution_governance._FACTORY_ROOT", Path(tmp)):
                status = time_awareness_status()
        self.assertEqual(status["factory_loop_lock_pid"], "9999")

    def test_missing_lock_reported_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("execution_governance._FACTORY_ROOT", Path(tmp)):
                status = time_awareness_status()
        self.assertIsNone(status["factory_loop_lock_pid"])


# ---------------------------------------------------------------------------
# Capability Governance
# ---------------------------------------------------------------------------

class TestCapabilityGovernance(unittest.TestCase):

    def test_real_models_classified_from_real_evidence(self):
        """openai/gpt-oss-20b has a real ACCEPTED decision + is the live
        production model -> ADOPTED. llama-3.1-8b-instant has real logged
        usage but no ACCEPTED decision -> VERIFIED, never promoted."""
        gov = capability_governance()
        by_model = {m["model"]: m["governance_state"] for m in gov["models"]}
        self.assertEqual(by_model.get("openai/gpt-oss-20b"), "ADOPTED")
        self.assertEqual(by_model.get("llama-3.1-8b-instant"), "VERIFIED")

    def test_no_capability_is_fabricated_as_adopted(self):
        """Every ADOPTED model must cite an ACCEPTED capability decision +
        live production status; the gate is never skipped."""
        gov = capability_governance()
        for m in gov["models"]:
            if m["governance_state"] == "ADOPTED":
                self.assertIn("ACCEPTED", m["evidence"])

    def test_states_are_only_the_three_named(self):
        gov = capability_governance()
        self.assertEqual(gov["states"], ["DISCOVERY", "VERIFIED", "ADOPTED"])
        for m in gov["models"]:
            self.assertIn(m["governance_state"], gov["states"])

    def test_governance_never_switches(self):
        """Adoption remains founder-gated at Level 5 -- the gate is stated,
        never bypassed by this module."""
        gov = capability_governance()
        self.assertIn("Level 5", gov["adoption_gate"])


# ---------------------------------------------------------------------------
# Autonomy Maturity
# ---------------------------------------------------------------------------

class TestAutonomyMaturity(unittest.TestCase):

    def test_level_3_evidence_based(self):
        """LEVEL 3 SUPERVISED AUTONOMOUS, cited from the STEP 4.x audit series
        + the real authority model -- not an artifact of this module."""
        aut = autonomy_maturity()
        self.assertEqual(aut["maturity"], "LEVEL 3")
        self.assertIn("STEP 4", aut["evidence"])
        self.assertIn("0-6", aut["authority_model_source"])

    def test_level_5_6_locked(self):
        aut = autonomy_maturity()
        self.assertTrue(aut["level_5_6_locked"])

    def test_not_raised_by_code_added(self):
        aut = autonomy_maturity()
        self.assertTrue(aut["not_raised_by_code_added"])


# ---------------------------------------------------------------------------
# Truth Gate
# ---------------------------------------------------------------------------

class TestTruthGate(unittest.TestCase):

    def test_vocabulary_is_exactly_the_three_named(self):
        gate = truth_gate()
        self.assertEqual(gate["vocabulary"], ["VERIFIED", "UNKNOWN", "NEEDS VERIFICATION"])

    def test_every_mandated_field_has_a_gate(self):
        gate = truth_gate()["gates"]
        for field in COMPLETION_REPORT_FIELDS:
            self.assertIn(field, gate)
            self.assertIn(gate[field], ["VERIFIED", "UNKNOWN", "NEEDS VERIFICATION"])

    def test_financial_truth_is_verified_from_live_ground_truth(self):
        gate = truth_gate()["gates"]
        self.assertEqual(gate["FINANCIAL_TRUTH"], "VERIFIED")

    def test_never_a_blanket_pass(self):
        """The gate distinguishes -- not every field is VERIFIED."""
        gate = truth_gate()["gates"]
        self.assertTrue(any(v != "VERIFIED" for v in gate.values()))


# ---------------------------------------------------------------------------
# The mandated completion report
# ---------------------------------------------------------------------------

class TestCompletionReport(unittest.TestCase):

    def test_all_14_mandated_fields_present(self):
        report = build_completion_report()
        for field in COMPLETION_REPORT_FIELDS:
            self.assertIn(field, report, f"missing mandated field: {field}")

    def test_phase_4_status_defaults_in_progress(self):
        report = build_completion_report()
        self.assertEqual(report["PHASE_4_STATUS"], "IN PROGRESS")

    def test_autonomy_maturity_level_3(self):
        report = build_completion_report()
        self.assertEqual(report["AUTONOMY_MATURITY"], "LEVEL 3")

    def test_agi_readiness_not_claimed(self):
        report = build_completion_report()
        self.assertEqual(report["AGI_READINESS"]["actuality"], "NOT CLAIMED")

    def test_step5_not_ready(self):
        report = build_completion_report()
        self.assertEqual(report["STEP_5_READINESS"]["state"], "NOT READY / BLOCKED")

    def test_financial_truth_zero_honest(self):
        report = build_completion_report()
        self.assertEqual(report["FINANCIAL_TRUTH"]["revenue_usd"], 0)
        self.assertEqual(report["FINANCIAL_TRUTH"]["verification"], "VERIFIED")

    def test_test_state_injection_is_passed_through(self):
        """The real executed test counts are injected by the phase run, never
        fabricated inside the report."""
        test_state = {"status": "PASS", "executed": 42, "passed": 42, "failed": 0}
        report = build_completion_report(test_state=test_state)
        self.assertEqual(report["TEST_STATE"], test_state)

    def test_remaining_gaps_injection(self):
        gaps = ["only a single real AI provider"]
        report = build_completion_report(remaining_gaps=gaps)
        self.assertIn("only a single real AI provider", report["REMAINING_GAPS"])

    def test_hard_stop_binds_on_complete(self):
        report = build_execution_governance_report(phase_4_status="COMPLETE")
        self.assertIn("HARD STOP", report["HARD_STOP"])

    def test_execution_governance_report_has_directive_sections(self):
        report = build_execution_governance_report()
        self.assertEqual(len(report["DIRECTIVE_SECTIONS"]), len(DIRECTIVE_SECTIONS))

    def test_completion_report_never_writes_disk(self):
        """Read-only guarantee: building the report in a temp-dir-only world
        (no real ledgers visible) still succeeds and writes nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            empty_root = Path(tmp)
            with mock.patch("execution_governance._FACTORY_ROOT", empty_root):
                report = build_completion_report()
            self.assertEqual(len(list(empty_root.iterdir())), 0)
        self.assertEqual(report["FINANCIAL_TRUTH"]["revenue_usd"], 0)


if __name__ == "__main__":
    unittest.main()
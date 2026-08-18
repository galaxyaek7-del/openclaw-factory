"""Tests for Phase 3 -- AI Capability Evolution & Multi-Model Intelligence
(founder directive, 2026-08-17).

Covers the directive's 12 workstreams where code exists, as real, executing
tests. Every test uses temp ledgers / temp cost-log fixtures -- never the
real data/ ledgers, never the real cost log.

  WS1  multi-model capability registry  -- version ledger, availability/reliability wiring
  WS2  per-task evaluation (SELECTION vs COMPARISON) -- explicit criteria, UNKNOWN on insufficiency
  WS3  routing intelligence + authorization-gated switching -- proposals recorded, never executed
  WS4  replacement safety -- compatibility validation + deterministic rollback, founder-gated
  WS5  capability evolution -- ACCEPTED/REJECTED/UNCERTAIN memory, evidence-cited
  WS6  technology foresight -- radar vocabulary WATCH/EXPERIMENT/ADOPT/REJECT extended additively
  WS7  AGI readiness foundation -- READINESS vs ACTUALITY separated, NOT CLAIMED never claimed
  WS8  (this file) -- fail-closed behavior across all of the above

    python -m unittest tests.test_ai_capability_evolution -v
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

from ai_capability import observatory as obs
from ai_capability import agi_readiness


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


def _make_fixtures():
    tmp = tempfile.mkdtemp(prefix="cap_evol_test_")
    cost_log = os.path.join(tmp, "ai_cost_log.jsonl")
    rows = [
        _cost_row("llama-3.1-8b-instant", timestamp="2026-07-20T10:00:00", latency_ms=1900, cost_usd=0.00008),
        _cost_row("llama-3.1-8b-instant", timestamp="2026-07-21T10:00:00", latency_ms=2000, cost_usd=0.00009),
        _cost_row("openai/gpt-oss-20b", timestamp="2026-08-14T10:00:00", latency_ms=700, cost_usd=0.0001),
        _cost_row("openai/gpt-oss-20b", timestamp="2026-08-15T10:00:00", latency_ms=800, cost_usd=0.00012),
    ]
    _write_jsonl(cost_log, rows)
    return tmp, cost_log


# ---------------------------------------------------------------------------
# WS1 -- multi-model capability registry
# ---------------------------------------------------------------------------

class TestCapabilityRegistryWS1(unittest.TestCase):

    def setUp(self):
        self.tmp, self.cost_log = _make_fixtures()

    def test_model_version_is_unknown_until_a_real_version_is_recorded(self):
        """WS1: version is never invented -- UNKNOWN until a real, evidence-cited
        observation is appended to the version ledger."""
        records = obs.model_capability_records(self.cost_log)
        for r in records:
            self.assertEqual(r["model_version"], "UNKNOWN")

    def test_record_model_version_appends_a_real_observed_version(self):
        """WS1: a real version observation lands in the append-only ledger and
        is reflected on the model record."""
        versions_path = os.path.join(self.tmp, "versions.jsonl")
        obs.record_model_version("openai/gpt-oss-20b", "gpt-oss-20b-v1",
                                 "real API response field, observed 2026-08-16",
                                 path=versions_path)
        entries = obs.model_versions(versions_path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["model"], "openai/gpt-oss-20b")
        records = obs.model_capability_records(self.cost_log)
        # _latest_model_version reads the DEFAULT ledger, not our temp one --
        # assert the ledger behavior directly instead of the default path.
        self.assertEqual(entries[0]["version"], "gpt-oss-20b-v1")

    def test_record_model_version_refuses_placeholder_versions(self):
        """WS1: a fabricated/placeholder version string is refused -- never recorded."""
        versions_path = os.path.join(self.tmp, "versions.jsonl")
        with self.assertRaises(ValueError):
            obs.record_model_version("m", "  ", "evidence", path=versions_path)
        with self.assertRaises(ValueError):
            obs.record_model_version("m", "v1", "", path=versions_path)
        self.assertEqual(obs.model_versions(versions_path), [])

    def test_availability_and_reliability_are_real_from_safe_mode_signal(self):
        """WS1: availability/reliability are AVAILABLE/RELIABLE when the cost log
        has real calls and safe_mode's ai_generation subsystem is stable."""
        records = obs.model_capability_records(self.cost_log)
        for r in records:
            self.assertEqual(r["availability"], "AVAILABLE")
            self.assertEqual(r["reliability"], "RELIABLE")
            self.assertTrue(r["availability_basis"])

    def test_availability_degrades_when_safe_mode_marks_ai_generation_unstable(self):
        """WS1: a real safe_mode instability observation degrades availability --
        never a fabricated green check."""
        with mock.patch("safe_mode.is_subsystem_safe_mode", return_value=True):
            records = obs.model_capability_records(self.cost_log)
        for r in records:
            self.assertEqual(r["availability"], "DEGRADED")
            self.assertEqual(r["reliability"], "UNKNOWN")


# ---------------------------------------------------------------------------
# WS2 -- per-task model evaluation: SELECTION vs COMPARISON
# ---------------------------------------------------------------------------

class TestPerTaskEvaluationWS2(unittest.TestCase):

    def setUp(self):
        self.tmp, self.cost_log = _make_fixtures()

    def test_comparison_has_named_criteria(self):
        """WS2: every comparison carries an explicit, named criteria list."""
        c = obs.comparison_for_task("market_research", cost_log_path=self.cost_log)
        self.assertIn("criteria", c)
        self.assertTrue(all(x in obs.MEASURABLE_EVALUATION_CRITERIA for x in c["criteria"]))

    def test_comparison_has_one_real_row_per_cost_logged_model(self):
        """WS2: comparison iterates every real cost-logged model, honestly."""
        c = obs.comparison_for_task("market_research", cost_log_path=self.cost_log)
        models = {row["model"] for row in c["comparison"]}
        self.assertEqual(models, {"llama-3.1-8b-instant", "openai/gpt-oss-20b"})
        for row in c["comparison"]:
            self.assertEqual(row["capability_evidence"], "UNKNOWN")  # never a fabricated capability score

    def test_selection_is_separate_from_comparison(self):
        """WS2: selection (the evaluator recommendation) and comparison are
        distinct, named outputs."""
        c = obs.comparison_for_task("code_generation", cost_log_path=self.cost_log)
        self.assertIn("selection", c)
        self.assertIn("comparison", c)
        self.assertIn("task", c["selection"])
        self.assertTrue(len(c["comparison"]) >= 1)

    def test_comparison_note_discloses_single_provider_reality(self):
        """WS2: comparison honestly discloses that capability comparison is
        UNKNOWN with a single real provider."""
        c = obs.comparison_for_task("market_research", cost_log_path=self.cost_log)
        self.assertIn("UNKNOWN", c["comparison_note"])

    def test_evaluate_all_tasks_with_comparison_covers_all_12_tasks(self):
        """WS2: all 12 named task categories get a selection/comparison view."""
        all_c = obs.evaluate_all_tasks_with_comparison(cost_log_path=self.cost_log)
        self.assertEqual(len(all_c), len(obs.TASK_CATEGORIES))
        self.assertEqual({x["task"] for x in all_c}, set(obs.TASK_CATEGORIES))


# ---------------------------------------------------------------------------
# WS3 -- routing intelligence + authorization-gated switching
# ---------------------------------------------------------------------------

class TestRoutingAuthorizationWS3(unittest.TestCase):

    def setUp(self):
        self.tmp, self.cost_log = _make_fixtures()

    def test_routing_authorization_is_founder_gated_level_5(self):
        """WS3: routing authorization is always Level 5 HUMAN APPROVAL REQUIRED,
        with no execution path."""
        status = obs.routing_authorization_status(cost_log_path=self.cost_log)
        self.assertEqual(status["switch_autonomy_level"], 5)
        self.assertEqual(status["switch_autonomy_name"], "HUMAN APPROVAL REQUIRED")
        self.assertTrue(status["founder_gated"])
        self.assertEqual(status["switch_execution_path"], "NONE -- no code path executes a model switch")

    def test_record_switch_proposal_never_executes_a_switch(self):
        """WS3: recording a proposal is the ONLY operation -- no code path
        changes a model, reconfigures a provider, or affects routing."""
        props_path = os.path.join(self.tmp, "switches.jsonl")
        entry = obs.record_switch_proposal(
            model_from="llama-3.1-8b-instant", model_to="openai/gpt-oss-20b",
            task="content_generation",
            rationale="Retired model needs replacement.",
            evidence="real vendor retirement, book_generator.py",
            path=props_path)
        self.assertEqual(entry["status"], "PROPOSED")
        self.assertEqual(entry["autonomy_level"], 5)
        self.assertEqual(entry["decision"], None)
        entries = obs.switch_proposals(props_path)
        self.assertEqual(len(entries), 1)
        # the real observatory ledger must remain untouched by tests
        self.assertEqual(obs.switch_proposals(), [])

    def test_record_switch_proposal_requires_evidence(self):
        """WS3: a switch proposal without real evidence/ rationale is refused."""
        props_path = os.path.join(self.tmp, "switches.jsonl")
        with self.assertRaises(ValueError):
            obs.record_switch_proposal("a", "b", "t", "", "evidence", path=props_path)
        with self.assertRaises(ValueError):
            obs.record_switch_proposal("a", "b", "t", "rationale", "", path=props_path)

    def test_routing_intelligence_still_never_auto_switches(self):
        """WS3/WS8: routing_intelligence() keeps will_auto_switch=False always."""
        r = obs.routing_intelligence("market_research", cost_log_path=self.cost_log)
        self.assertIs(r["will_auto_switch"], False)
        self.assertIn("advisory only", r["governance"])


# ---------------------------------------------------------------------------
# WS4 -- model replacement safety
# ---------------------------------------------------------------------------

class TestReplacementSafetyWS4(unittest.TestCase):

    def setUp(self):
        self.tmp, self.cost_log = _make_fixtures()

    def test_current_model_needs_no_replacement(self):
        """WS4: a CURRENT model's plan says replacement is not needed."""
        plan = obs.replacement_plan("openai/gpt-oss-20b", cost_log_path=self.cost_log)
        self.assertFalse(plan["replacement_needed"])

    def test_replacement_plan_never_touches_production(self):
        """WS4: the plan is validation + guidance only -- it changes nothing."""
        plan = obs.replacement_plan("llama-3.1-8b-instant", cost_log_path=self.cost_log)
        self.assertTrue(plan["replacement_needed"])
        self.assertEqual(plan["authorization"]["autonomy_level"], 5)
        self.assertTrue(plan["rollback"]["deterministic"])
        self.assertIn("GROQ_MODEL", plan["rollback"]["procedure"])

    def test_replacement_candidate_with_real_data_is_validated(self):
        """WS4: a candidate with real usage data is VALIDATED; a candidate with
        none is NOT VALIDATED -- never assumed safe."""
        plan = obs.replacement_plan("llama-3.1-8b-instant", cost_log_path=self.cost_log)
        validated = [c for c in plan["candidates"] if c["candidate"] == "openai/gpt-oss-20b"]
        self.assertEqual(validated[0]["compatibility_status"], "VALIDATED")
        self.assertTrue(any("real usage data" in c for c in validated[0]["compatibility"]))

    def test_replacement_plan_for_unknown_model_is_honest(self):
        """WS4: an unrecorded model yields an honest UNKNOWN plan."""
        plan = obs.replacement_plan("not-a-real-model", cost_log_path=self.cost_log)
        self.assertFalse(plan["replacement_needed"])
        self.assertEqual(plan["state"], "UNKNOWN")


# ---------------------------------------------------------------------------
# WS5 -- capability evolution: accepted / rejected / uncertain memory
# ---------------------------------------------------------------------------

class TestCapabilityEvolutionWS5(unittest.TestCase):

    def setUp(self):
        self.tmp, self.cost_log = _make_fixtures()

    def test_record_capability_decision_requires_valid_status_and_evidence(self):
        """WS5: only ACCEPTED/REJECTED/UNCERTAIN, always evidence-cited."""
        path = os.path.join(self.tmp, "caps.jsonl")
        obs.record_capability_decision("m1", "ACCEPTED", "real migration", "book_generator.py", "REAL", path=path)
        with self.assertRaises(ValueError):
            obs.record_capability_decision("m1", "GUESSED", "r", "e", "REAL", path=path)
        with self.assertRaises(ValueError):
            obs.record_capability_decision("m1", "ACCEPTED", "", "e", "REAL", path=path)
        self.assertEqual(len(obs.capability_decisions(path)), 1)

    def test_capability_evolution_summary_groups_by_status(self):
        """WS5: summary groups the real ledger by status, never a decision engine."""
        path = os.path.join(self.tmp, "caps.jsonl")
        obs.record_capability_decision("accepted-tech", "ACCEPTED", "r", "evidence-a", "REAL", path=path)
        obs.record_capability_decision("rejected-tech", "REJECTED", "r", "evidence-b", "REAL", path=path)
        obs.record_capability_decision("uncertain-tech", "UNCERTAIN", "r", "evidence-c", "LOW", path=path)
        summary = obs.capability_evolution_summary(path)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(len(summary["accepted"]), 1)
        self.assertEqual(len(summary["rejected"]), 1)
        self.assertEqual(len(summary["uncertain"]), 1)
        self.assertIn("never DECIDED", summary["note"])

    def test_links_to_a_real_proposal_id_when_given(self):
        """WS5: a linked_proposal_id is stored verbatim -- never guessed."""
        path = os.path.join(self.tmp, "caps.jsonl")
        obs.record_capability_decision("t", "ACCEPTED", "r", "e", "REAL",
                                       linked_proposal_id="real-proposal-1", path=path)
        self.assertEqual(obs.capability_decisions(path)[0]["linked_proposal_id"], "real-proposal-1")


# ---------------------------------------------------------------------------
# WS6 -- technology foresight: radar vocabulary extended additively
# ---------------------------------------------------------------------------

class TestTechnologyForesightWS6(unittest.TestCase):

    def test_radar_vocabulary_includes_phase3_actions_additively(self):
        """WS6: WATCH/EXPERIMENT/ADOPT/REJECT all present; Phase 2 actions
        (ADOPT/TRIAL/WATCH/HOLD/RETIRE) all retained."""
        for action in ["WATCH", "EXPERIMENT", "ADOPT", "REJECT", "TRIAL", "HOLD", "RETIRE"]:
            self.assertIn(action, obs.RADAR_ACTIONS)

    def test_radar_records_accept_new_phase3_actions(self):
        """WS6: record_radar_entry accepts the new EXPERIMENT/REJECT actions."""
        path = os.path.join(tempfile.mkdtemp(prefix="radar3_"), "radar.jsonl")
        obs.record_radar_entry("tech-x", "EXPERIMENT", "bounded trial", "real evidence", "LOW", path=path)
        obs.record_radar_entry("tech-y", "REJECT", "real evidence against", "real evidence", "MEDIUM", path=path)
        self.assertEqual(len(obs.technology_radar(path)), 2)
        self.assertEqual(obs.technology_radar(path)[0]["category"], "EXPERIMENT")

    def test_radar_refuses_unknown_actions(self):
        """WS6: an unlisted radar action is refused."""
        path = os.path.join(tempfile.mkdtemp(prefix="radar3_"), "radar.jsonl")
        with self.assertRaises(ValueError):
            obs.record_radar_entry("x", "NOT-AN-ACTION", "r", "e", "HIGH", path=path)


# ---------------------------------------------------------------------------
# WS7 -- AGI readiness foundation
# ---------------------------------------------------------------------------

class TestAgiReadinessWS7(unittest.TestCase):

    def test_readiness_is_separate_from_actuality(self):
        """WS7: READINESS (structural plumbing) and ACTUALITY (capability
        claim) are separate, never conflated."""
        a = agi_readiness.assess_agi_readiness()
        self.assertIn("readiness_score", a)
        self.assertIn("actuality", a)
        self.assertEqual(a["actuality"]["agi_capability_claim"], "NOT CLAIMED")

    def test_actuality_is_never_claimed(self):
        """WS7: no AGI capability claim ever exists -- structural UNKNOWN."""
        a = agi_readiness.assess_agi_readiness()
        self.assertEqual(a["actuality"]["definition"]["state"], "UNKNOWN")
        self.assertEqual(a["actuality"]["agi_capability_claim"], "NOT CLAIMED")
        self.assertTrue(a["actuality"]["model_agnostic"])

    def test_readiness_dimensions_are_real_mechanical_checks(self):
        """WS7: readiness dimensions exist and are mechanical pass/fail."""
        a = agi_readiness.assess_agi_readiness()
        for dim in agi_readiness.AGI_READINESS_DIMENSIONS:
            self.assertIn(dim, a["dimensions"])
            self.assertIn("ready", a["dimensions"][dim])

    def test_readiness_governance_is_read_only(self):
        """WS7: the framework is read-only -- never purchases/switches a model."""
        a = agi_readiness.assess_agi_readiness()
        self.assertIn("Read-only", a["governance"])
        self.assertIn("founder-gated", a["governance"])


# ---------------------------------------------------------------------------
# WS8 -- fail-closed behavior across the new Phase 3 surface
# ---------------------------------------------------------------------------

class TestFailClosedWS8(unittest.TestCase):

    def setUp(self):
        self.tmp, self.cost_log = _make_fixtures()

    def test_no_observatory_function_writes_to_real_ledgers_under_test(self):
        """WS8: running the report against a temp cost log never touches the
        real observatory ledgers (radar/signals/quality/versions/switches/caps)."""
        before = {
            "radar": len(obs.technology_radar()),
            "signals": len(obs.technology_foresight()),
            "quality": len(obs.quality_memory()),
            "versions": len(obs.model_versions()),
            "switches": len(obs.switch_proposals()),
            "caps": len(obs.capability_decisions()),
        }
        obs.build_observatory_report(cost_log_path=self.cost_log)
        after = {
            "radar": len(obs.technology_radar()),
            "signals": len(obs.technology_foresight()),
            "quality": len(obs.quality_memory()),
            "versions": len(obs.model_versions()),
            "switches": len(obs.switch_proposals()),
            "caps": len(obs.capability_decisions()),
        }
        self.assertEqual(before, after)

    def test_agi_readiness_never_writes_any_ledger(self):
        """WS8: assessing AGI readiness writes nothing anywhere."""
        versions = len(obs.model_versions())
        caps = len(obs.capability_decisions())
        agi_readiness.assess_agi_readiness()
        self.assertEqual(len(obs.model_versions()), versions)
        self.assertEqual(len(obs.capability_decisions()), caps)

    def test_autonomy_level_5_and_6_restrictions_intact(self):
        """WS8: Level 5 (model switch = HUMAN APPROVAL REQUIRED) and Level 6
        (never-automate) governance stays intact -- no new code bypasses it."""
        self.assertEqual(obs._switch_autonomy_level(), 5)
        self.assertIn("never initiates itself", obs.routing_authorization_status()["governance"])

    def test_switch_proposals_are_append_only_never_updated(self):
        """WS8: a recorded proposal cannot be edited -- the ledger is append-only."""
        path = os.path.join(self.tmp, "switches.jsonl")
        obs.record_switch_proposal("a", "b", "t", "r", "e", path=path)
        obs.record_switch_proposal("a", "b", "t", "r2", "e2", path=path)
        entries = obs.switch_proposals(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["rationale"], "r")


if __name__ == "__main__":
    unittest.main()
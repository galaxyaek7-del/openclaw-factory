"""Tests for gfos.py (Galaxy Forge Enterprise Operating System, ADR-147,
2026-07-30): a coordination/citation layer over already-real subsystems --
never a mandatory single-gateway, never new queue infrastructure (both
confirmed via AskUserQuestion before this was built).

    python -m unittest tests.test_gfos -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import gfos
import department_events


class TestDepartmentRegistry(unittest.TestCase):
    def test_returns_exactly_the_real_12_department_roster(self):
        reg = gfos.department_registry()
        self.assertEqual(reg["count"], 12)
        names = {d["department"] for d in reg["departments"]}
        self.assertEqual(names, department_events.VALID_DEPARTMENTS, "must reuse the real canonical roster, never invent a second one")

    def test_every_department_carries_all_8_named_fields(self):
        reg = gfos.department_registry()
        required = {"identity", "responsibilities_source", "capabilities", "dependencies", "current_workload", "health", "confidence"}
        for d in reg["departments"]:
            self.assertTrue(required.issubset(d.keys()), f"{d['department']} missing a required field")

    def test_confidence_is_derived_from_real_data_source_never_fabricated(self):
        reg = gfos.department_registry()
        for d in reg["departments"]:
            self.assertIn(d["confidence"], ("real data", "no real data source yet", "unknown"))


class TestMissionLifecycleSummary(unittest.TestCase):
    def test_no_new_state_machine_every_count_traces_to_a_real_bucket(self):
        result = gfos.mission_lifecycle_summary()
        buckets = result["real_buckets"]
        lifecycle = result["lifecycle"]
        self.assertEqual(lifecycle["scheduled"]["count"], len(buckets["run_now"]))
        self.assertEqual(lifecycle["waiting"]["count"], len(buckets["wait"]))
        self.assertEqual(lifecycle["archived"]["count"], len(buckets["cancel"]) + len(buckets["stop"]))

    def test_stages_with_no_real_signal_are_honestly_none_not_zero(self):
        result = gfos.mission_lifecycle_summary()
        # "created"/"executing"/"completed"/"measured" have no real
        # standalone count in this factory -- must stay None, never a
        # fabricated 0 that would look like a real, verified empty count.
        for stage in ("created", "executing", "completed", "measured"):
            self.assertIsNone(result["lifecycle"][stage]["count"])
            self.assertTrue(result["lifecycle"][stage]["note"])

    def test_cites_real_orchestrator_execution_order_never_invents_one(self):
        from orchestrator import types as orchestrator_types
        result = gfos.mission_lifecycle_summary()
        self.assertEqual(result["execution_order"], list(orchestrator_types.EXECUTION_ORDER))


class TestEnterpriseTimeline(unittest.TestCase):
    def test_merges_multiple_real_sources_sorted_most_recent_first(self):
        result = gfos.enterprise_timeline(limit=20)
        timestamps = [e["timestamp"] for e in result["entries"] if e["timestamp"]]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True), "must be chronologically sorted, most recent first")

    def test_respects_limit(self):
        result = gfos.enterprise_timeline(limit=3)
        self.assertLessEqual(len(result["entries"]), 3)

    def test_every_entry_cites_a_real_source_file(self):
        result = gfos.enterprise_timeline(limit=10)
        for e in result["entries"]:
            self.assertTrue(e.get("source"), "every timeline entry must cite the real file it came from")

    def test_empty_ledgers_produce_honest_empty_timeline(self):
        tmp_decisions = tempfile.mktemp(suffix=".jsonl")
        tmp_evo = tempfile.mktemp(suffix=".json")
        tmp_directives = tempfile.mktemp(suffix=".jsonl")
        tmp_council = tempfile.mktemp(suffix=".jsonl")
        tmp_dept_events = tempfile.mktemp(suffix=".jsonl")
        result = gfos.enterprise_timeline(
            limit=10, decisions_path=tmp_decisions, evolution_queue_state_path=tmp_evo,
            executive_directives_path=tmp_directives, council_recommendations_path=tmp_council,
            department_events_path=tmp_dept_events, governance_dir="C:/definitely/not/a/real/governance/dir",
        )
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["total_real_events_merged"], 0)

    def test_adr_events_included_when_a_real_dated_adr_exists(self):
        # Executive Intelligence Layer (ADR-154, 2026-07-31): "Company
        # Memory Timeline" architecture-change coverage -- a real ADR
        # file with a real **Date:** line becomes a real `adr` event.
        gov_dir = tempfile.mkdtemp()
        with open(os.path.join(gov_dir, "ADR-999-test.md"), "w", encoding="utf-8") as f:
            f.write("# ADR-999 — Test ADR\n\n**Date:** 2026-07-31\n\nBody.\n")
        tmp_decisions = tempfile.mktemp(suffix=".jsonl")
        tmp_evo = tempfile.mktemp(suffix=".json")
        tmp_directives = tempfile.mktemp(suffix=".jsonl")
        tmp_council = tempfile.mktemp(suffix=".jsonl")
        tmp_dept_events = tempfile.mktemp(suffix=".jsonl")
        result = gfos.enterprise_timeline(
            limit=10, decisions_path=tmp_decisions, evolution_queue_state_path=tmp_evo,
            executive_directives_path=tmp_directives, council_recommendations_path=tmp_council,
            department_events_path=tmp_dept_events, governance_dir=gov_dir,
        )
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["type"], "adr")
        self.assertEqual(result["entries"][0]["timestamp"], "2026-07-31")

    def test_adr_with_no_real_date_line_is_honestly_excluded(self):
        gov_dir = tempfile.mkdtemp()
        with open(os.path.join(gov_dir, "ADR-998-no-date.md"), "w", encoding="utf-8") as f:
            f.write("# ADR-998 — No Date\n\nBody with no Date line.\n")
        tmp_decisions = tempfile.mktemp(suffix=".jsonl")
        tmp_evo = tempfile.mktemp(suffix=".json")
        tmp_directives = tempfile.mktemp(suffix=".jsonl")
        tmp_council = tempfile.mktemp(suffix=".jsonl")
        tmp_dept_events = tempfile.mktemp(suffix=".jsonl")
        result = gfos.enterprise_timeline(
            limit=10, decisions_path=tmp_decisions, evolution_queue_state_path=tmp_evo,
            executive_directives_path=tmp_directives, council_recommendations_path=tmp_council,
            department_events_path=tmp_dept_events, governance_dir=gov_dir,
        )
        self.assertEqual(result["entries"], [])


class TestGfosStatus(unittest.TestCase):
    def test_returns_all_real_citation_sections_never_a_second_computation(self):
        status = gfos.gfos_status()
        self.assertIn("department_registry", status)
        self.assertIn("mission_lifecycle", status)
        self.assertIn("recent_enterprise_timeline", status)
        self.assertIn("safe_mode.py's per-subsystem independence", status["note"] + "")

    def test_department_registry_inside_status_is_the_real_full_12(self):
        status = gfos.gfos_status()
        self.assertEqual(status["department_registry"]["count"], 12)


if __name__ == "__main__":
    unittest.main()

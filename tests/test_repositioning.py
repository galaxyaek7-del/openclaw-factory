"""Tests for golden_hunter/repositioning.py (Golden Hunter Repositioning
Engine, founder green-light 2026-08-14) and its Knowledge Graph
integration (knowledge_graph/build.py's RepositionAttempt nodes).

The real acceptance gate (profit_oracle.ladder_opportunity_score) is
mocked everywhere except the pure logic tests -- the engine itself never
runs a live network query, and this suite must never leak a real write
into data/repositioning_attempts.jsonl (same isolation discipline as
tests/test_golden_hunter.py).

    python -m unittest tests.test_repositioning -v
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

from golden_hunter import repositioning
from golden_hunter.repositioning import RepositioningAttempt
from knowledge_graph import build


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _write_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def _original_decision(**overrides):
    base = {
        "decision_id": "dec-rejected-1",
        "niche": "AI Agent Blueprint for Legal Case Research Automation for Solo Attorneys",
        "tier": "tier4",
        "decided_at": "2026-08-01T00:00:00+00:00",
        "status": "REJECTED",
        "ai_ceo_decision": "REJECT",
        "opportunity_score": 55.8,
        "opportunity_score_accepted": False,
        "reasoning": ["price $66 below the $97 floor", "no real proof of payment at recording time"],
        "evaluation_snapshot": {},
        "ladder": "automation_tools",
    }
    base.update(overrides)
    return base


class _FakeGate:
    """A scripted stand-in for profit_oracle.ladder_opportunity_score —
    returns a real-shaped result without any network call. Records the
    external_signal/evidence_path it is called with so tests can prove
    the engine forwards the original's real evidence context (never
    degrades the gate to a bare "Unknown pain" call)."""

    def __init__(self, accepted=True, ladder_score=68.7, price=194, reason="accepted: fixture"):
        self.accepted = accepted
        self.ladder_score = ladder_score
        self.price = price
        self.reason = reason
        self.last_kwargs = {}

    def __call__(self, niche, ladder="kdp_books", external_signal=None, evidence_path=None):
        self.last_kwargs = {
            "external_signal": external_signal,
            "evidence_path": evidence_path,
        }
        return {
            "niche": niche,
            "ladder": ladder,
            "ladder_score": self.ladder_score,
            "price": self.price,
            "accepted": self.accepted,
            "reason": self.reason,
        }


class TestProposeRepositionings(unittest.TestCase):
    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def test_proposes_premium_keyword_variants_mechanically(self):
        cands = repositioning.propose_repositionings(_original_decision())
        self.assertGreater(len(cands), 0)
        for c in cands:
            self.assertTrue(c["proposed_positioning"])
            self.assertEqual(c["original_niche"], _original_decision()["niche"])
            # The real premium keyword vocabulary must appear in proposed text
            self.assertTrue(
                any(k in c["proposed_positioning"].lower() for k in
                    ("system", "toolkit", "template", "bundle", "course", "masterclass"))
            )

    def test_weak_lead_in_token_is_dropped(self):
        """The proven maneuver: 'AI Agent Blueprint for X' -> 'X System'.
        The 'AI Agent Blueprint for ' lead must be stripped so the premium
        keyword lands before the target segment."""
        cands = repositioning.propose_repositionings(_original_decision())
        self.assertTrue(any(c["proposed_positioning"].startswith("Legal Case Research") for c in cands))

    def test_target_customer_segment_preserved(self):
        cands = repositioning.propose_repositionings(_original_decision())
        for c in cands:
            self.assertIn("for Solo Attorneys", c["proposed_positioning"])
            # regression: the target segment must appear exactly once
            self.assertEqual(c["proposed_positioning"].lower().count("for solo attorneys"), 1)

    def test_empty_original_returns_no_candidates_never_crashes(self):
        self.assertEqual(repositioning.propose_repositionings({}), [])
        self.assertEqual(repositioning.propose_repositionings(None), [])

    def test_does_not_duplicate_an_existing_keyword(self):
        """If the niche already carries a premium keyword, no candidate may
        add it again -- a mechanical, honest constraint."""
        decision = _original_decision(niche="Legal Case Research Automation System for Solo Attorneys")
        for c in repositioning.propose_repositionings(decision):
            self.assertEqual(c["proposed_positioning"].lower().count("system"), 1)


class TestRecordAndPersist(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()
        self._paths = [self.path]

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def _attempt(self):
        return RepositioningAttempt(
            attempt_id=repositioning.make_attempt_id("dec-1", "proposed", "2026-08-14T00:00:00+00:00"),
            original_decision_id="dec-1",
            original_niche="original niche",
            rejection_reason="price below floor",
            original_score=55.8,
            original_positioning="original niche",
            proposed_positioning="proposed niche System",
            changed_target_customer=None,
            changed_value_proposition="deliverable not blueprint",
            changed_pricing=194,
            resulting_score=68.7,
            final_outcome="ACCEPTED",
            recorded_at="2026-08-14T00:00:00+00:00",
        )

    def test_record_attempt_is_append_only_and_readable(self):
        repositioning.record_attempt(self._attempt(), attempts_path=self.path)
        repositioning.record_attempt(self._attempt(), attempts_path=self.path)
        records = repositioning.read_attempts(self.path)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["original_decision_id"], "dec-1")

    def test_never_overwrites_original_decision(self):
        """The original decision record must be untouched -- only referenced
        by id. A full-schema round trip preserves every required field."""
        a = self._attempt()
        repositioning.record_attempt(a, attempts_path=self.path)
        stored = repositioning.read_attempts(self.path)[0]
        for field in ("attempt_id", "original_decision_id", "original_niche", "rejection_reason",
                       "original_score", "original_positioning", "proposed_positioning",
                       "changed_target_customer", "changed_value_proposition", "changed_pricing",
                       "resulting_score", "final_outcome", "recorded_at"):
            self.assertIn(field, stored)

    def test_find_attempts_by_original_returns_only_that_decisions_history(self):
        a1 = self._attempt()
        a2 = RepositioningAttempt(
            attempt_id=repositioning.make_attempt_id("dec-2", "other", "2026-08-14T00:00:00+00:00"),
            original_decision_id="dec-2",
            original_niche="other", rejection_reason="x", original_score=40.0,
            original_positioning="other", proposed_positioning="other System",
            changed_target_customer=None, changed_value_proposition=None,
            changed_pricing=150, resulting_score=50.0, final_outcome="REJECTED",
            recorded_at="2026-08-14T00:00:00+00:00",
        )
        repositioning.record_attempt(a1, attempts_path=self.path)
        repositioning.record_attempt(a2, attempts_path=self.path)
        found = repositioning.find_attempts_by_original("dec-1", self.path)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["original_decision_id"], "dec-1")

    def test_missing_file_reads_empty_never_crashes(self):
        self.assertEqual(repositioning.read_attempts("C:/definitely/not/real.jsonl"), [])


class TestRepositionAndRecord(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()
        self._paths = [self.path]

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def test_records_real_gate_result_and_accepts_nothing_itself(self):
        """The engine runs the real-shaped gate; ACCEPTED/REJECTED comes
        only from the gate's own `accepted` field -- never from the engine."""
        gate = _FakeGate(accepted=True, ladder_score=68.7, price=194)
        with patch("profit_oracle.ladder_opportunity_score", gate):
            attempt = repositioning.reposition_and_record(
                _original_decision(),
                "Legal Case Research Automation System for Solo Attorneys",
                ladder="automation_tools",
                attempts_path=self.path,
            )
        self.assertEqual(attempt["final_outcome"], "ACCEPTED")
        self.assertEqual(attempt["resulting_score"], 68.7)
        self.assertEqual(attempt["changed_pricing"], 194)
        self.assertEqual(attempt["original_decision_id"], "dec-rejected-1")

    def test_gate_rejection_is_recorded_honestly_not_hidden(self):
        gate = _FakeGate(accepted=False, ladder_score=50.0, price=120, reason="no proof of payment")
        with patch("profit_oracle.ladder_opportunity_score", gate):
            attempt = repositioning.reposition_and_record(
                _original_decision(),
                "Legal Case Research Automation Toolkit for Solo Attorneys",
                attempts_path=self.path,
            )
        self.assertEqual(attempt["final_outcome"], "REJECTED")
        self.assertEqual(attempt["resulting_score"], 50.0)
        self.assertIsNotNone(attempt["note"])

    def test_requires_real_original_decision_id(self):
        with self.assertRaises(ValueError):
            repositioning.reposition_and_record({}, "some proposed positioning")

    def test_original_record_fields_never_overwritten(self):
        """After reposition_and_record, the original decision dict passed in
        must be byte-for-byte unchanged -- the engine is read-only over it."""
        gate = _FakeGate(accepted=False)
        original = _original_decision()
        before = json.dumps(original, sort_keys=True)
        with patch("profit_oracle.ladder_opportunity_score", gate):
            repositioning.reposition_and_record(original, "Proposed X System", attempts_path=self.path)
        self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_rejection_reason_and_original_score_read_from_real_record(self):
        gate = _FakeGate(accepted=False)
        with patch("profit_oracle.ladder_opportunity_score", gate):
            attempt = repositioning.reposition_and_record(
                _original_decision(), "Proposed X Toolkit", attempts_path=self.path,
            )
        self.assertEqual(attempt["original_score"], 55.8)
        self.assertIn("$97 floor", attempt["rejection_reason"])

    def test_forwards_real_evidence_context_to_the_gate(self):
        """The engine must run the gate with the SAME real evidence context
        the original decision was scored under (external_signal with real
        customer_pain + the real evidence ledger path). Dropping them would
        degrade the gate to a bare "Unknown pain" call and reject every
        repositioning even when real evidence exists -- the exact
        "computed then dropped" fidelity bug this factory has fixed
        repeatedly."""
        gate = _FakeGate(accepted=False)
        pain_signal = {"customer_pain": {"real_evidence": {"pain_language_hits": 4}}}
        with patch("profit_oracle.ladder_opportunity_score", gate):
            repositioning.reposition_and_record(
                _original_decision(),
                "Proposed X System",
                attempts_path=self.path,
                external_signal=pain_signal,
                evidence_path="data/market_evidence.jsonl",
            )
        self.assertEqual(gate.last_kwargs["external_signal"], pain_signal)
        self.assertEqual(gate.last_kwargs["evidence_path"], "data/market_evidence.jsonl")


class TestRepositioningLearningReport(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()
        self._paths = [self.path]

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def _record(self, original_id, proposed, outcome, score, pattern):
        repositioning.record_attempt({
            "attempt_id": repositioning.make_attempt_id(original_id, proposed, "2026-08-14T00:00:00+00:00"),
            "original_decision_id": original_id,
            "original_niche": "orig", "rejection_reason": "r", "original_score": 50.0,
            "original_positioning": "orig", "proposed_positioning": proposed,
            "changed_target_customer": None, "changed_value_proposition": None,
            "changed_pricing": 194, "resulting_score": score, "final_outcome": outcome,
            "recorded_at": "2026-08-14T00:00:00+00:00", "pattern": pattern,
        }, attempts_path=self.path)

    def test_no_attempts_learns_nothing_honestly(self):
        report = repositioning.repositioning_learning_report("C:/definitely/not/real.jsonl")
        self.assertFalse(report["learned"])
        self.assertIn("لا محاولات", report["reason"])

    def test_below_min_sample_reports_insufficient_data(self):
        self._record("d1", "p1", "ACCEPTED", 68.7, "added_keyword:system")
        self._record("d2", "p2", "REJECTED", 50.0, "added_keyword:toolkit")
        report = repositioning.repositioning_learning_report(self.path)
        self.assertFalse(report["learned"])
        self.assertEqual(report["total_attempts"], 2)
        self.assertEqual(report["min_required"], repositioning.MIN_SAMPLES_FOR_LEARNING)

    def test_reports_real_pattern_success_rates_at_minimum_sample(self):
        for i in range(3):
            self._record(f"d{i}", f"p{i} System", "ACCEPTED", 68.7, "added_keyword:system")
        report = repositioning.repositioning_learning_report(self.path)
        self.assertTrue(report["learned"])
        self.assertEqual(report["success_rate_pct"], 100.0)
        self.assertIn("added_keyword:system", report["by_pattern"])
        self.assertEqual(report["by_pattern"]["added_keyword:system"]["accepted"], 3)

    def test_report_never_modifies_live_gates(self):
        """The report is informational only -- it returns data, it must
        never touch scoring thresholds (checked structurally)."""
        import inspect
        src = inspect.getsource(repositioning.repositioning_learning_report)
        self.assertNotIn("MIN_LADDER_PROFIT_FLOOR", src)
        self.assertNotIn("record_ladder_decision", src)
        self.assertNotIn("ladder_opportunity_score", src)


class TestKnowledgeGraphIntegration(unittest.TestCase):
    """Golden Hunter Repositioning Engine -> Knowledge Graph: every real
    RepositionAttempt becomes a node, with an EXACT edge back to its
    original Decision node when that decision exists in the same build."""

    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def test_reposition_attempt_node_and_exact_edge_to_original_decision(self):
        decisions = _write_jsonl([
            {"niche": "original niche", "decision_id": "dec-1", "status": "REJECTED"},
        ])
        attempts = _write_jsonl([{
            "attempt_id": "att-1", "original_decision_id": "dec-1",
            "original_niche": "original niche", "proposed_positioning": "new System",
            "original_score": 55.8, "resulting_score": 68.7, "final_outcome": "ACCEPTED",
            "changed_pricing": 194, "ladder": "automation_tools",
            "recorded_at": "2026-08-14T00:00:00+00:00",
        }])
        self._paths.extend([decisions, attempts])
        empty = _write_jsonl([])
        self._paths.append(empty)
        graph = build.build_graph(
            decisions_path=decisions, analyses_path=empty, ledger_path=empty,
            ai_cost_log_path=empty, evidence_path=empty,
            lessons_dir="C:/definitely/not/a/real/lessons/dir",
            governance_dir="C:/definitely/not/a/real/governance/dir",
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
            decision_outcomes_path="C:/definitely/not/a/real/decision_outcomes.jsonl",
            executive_directives_path="C:/definitely/not/a/real/executive_directives.jsonl",
            affiliate_clicks_path="C:/definitely/not/a/real/affiliate_clicks.jsonl",
            affiliate_simulation_events_path="C:/definitely/not/a/real/affiliate_simulation_events.jsonl",
            council_recommendations_path="C:/definitely/not/a/real/council_recommendations.jsonl",
            competitor_database_path="C:/definitely/not/a/real/competitor_database.json",
            repositioning_attempts_path=attempts,
        )
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn("reposition_attempt:att-1", node_ids)
        repositions_edges = [e for e in graph["edges"] if e["relation"] == "repositions"]
        self.assertEqual(len(repositions_edges), 1)
        self.assertEqual(repositions_edges[0]["edge_confidence"], "exact")
        self.assertEqual(repositions_edges[0]["from"], "reposition_attempt:att-1")
        self.assertEqual(repositions_edges[0]["to"], "decision:dec-1")

    def test_attempt_without_its_decision_in_build_gets_standalone_node_no_fake_edge(self):
        attempts = _write_jsonl([{
            "attempt_id": "att-2", "original_decision_id": "dec-not-in-build",
            "original_niche": "x", "proposed_positioning": "y System",
            "original_score": None, "resulting_score": None, "final_outcome": "RECORDED",
            "changed_pricing": None, "ladder": None, "recorded_at": "2026-08-14T00:00:00+00:00",
        }])
        self._paths.append(attempts)
        empty = _write_jsonl([])
        self._paths.append(empty)
        graph = build.build_graph(
            decisions_path=empty, analyses_path=empty, ledger_path=empty,
            ai_cost_log_path=empty, evidence_path=empty,
            lessons_dir="C:/definitely/not/a/real/lessons/dir",
            governance_dir="C:/definitely/not/a/real/governance/dir",
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
            decision_outcomes_path="C:/definitely/not/a/real/decision_outcomes.jsonl",
            executive_directives_path="C:/definitely/not/a/real/executive_directives.jsonl",
            affiliate_clicks_path="C:/definitely/not/a/real/affiliate_clicks.jsonl",
            affiliate_simulation_events_path="C:/definitely/not/a/real/affiliate_simulation_events.jsonl",
            council_recommendations_path="C:/definitely/not/a/real/council_recommendations.jsonl",
            competitor_database_path="C:/definitely/not/a/real/competitor_database.json",
            repositioning_attempts_path=attempts,
        )
        types = {n["type"] for n in graph["nodes"]}
        self.assertIn("RepositionAttempt", types)
        self.assertEqual([e for e in graph["edges"] if e["relation"] == "repositions"], [])

    def test_empty_everything_never_throws(self):
        empty = _write_jsonl([])
        self._paths.append(empty)
        graph = build.build_graph(
            decisions_path=empty, analyses_path=empty, ledger_path=empty,
            ai_cost_log_path=empty, evidence_path=empty,
            lessons_dir="C:/definitely/not/a/real/lessons/dir",
            governance_dir="C:/definitely/not/a/real/governance/dir",
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
            decision_outcomes_path="C:/definitely/not/a/real/decision_outcomes.jsonl",
            executive_directives_path="C:/definitely/not/a/real/executive_directives.jsonl",
            affiliate_clicks_path="C:/definitely/not/a/real/affiliate_clicks.jsonl",
            affiliate_simulation_events_path="C:/definitely/not/a/real/affiliate_simulation_events.jsonl",
            council_recommendations_path="C:/definitely/not/a/real/council_recommendations.jsonl",
            competitor_database_path="C:/definitely/not/a/real/competitor_database.json",
            repositioning_attempts_path="C:/definitely/not/a/real/repositioning_attempts.jsonl",
        )
        self.assertEqual(graph["node_count"], 0)
        self.assertEqual(graph["edge_count"], 0)


class TestNoGateBypassStructural(unittest.TestCase):
    def test_module_source_never_contains_execute_production_true(self):
        """Same structural guarantee golden_hunter/hunt.py already carries:
        this capability can never accidentally trigger production."""
        with open(repositioning.__file__, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("execute_production=True", content)


if __name__ == "__main__":
    unittest.main()
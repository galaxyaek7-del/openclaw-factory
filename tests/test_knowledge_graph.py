"""Tests for knowledge_graph/build.py (EOS Phase 2, 2026-07-19): a real,
queryable company memory over already-recorded relationships.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_knowledge_graph -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from knowledge_graph import build


def _write_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


class TestBuildGraph(unittest.TestCase):
    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def _paths_for(self, decisions=None, analyses=None, ledger=None, ai_costs=None, evidence=None):
        d = _write_jsonl(decisions or [])
        a = _write_jsonl(analyses or [])
        l = _write_jsonl(ledger or [])
        c = _write_jsonl(ai_costs or [])
        e = _write_jsonl(evidence or [])
        self._paths.extend([d, a, l, c, e])
        return d, a, l, c, e

    def test_niche_and_decision_nodes_created_from_real_decisions(self):
        d, a, l, c, e = self._paths_for(decisions=[
            {"niche": "test niche", "decision_id": "dec1", "status": "ACCEPTED", "ladder": "kdp_books", "reasoning": ["ok"]},
        ])
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn("niche:test niche", node_ids)
        self.assertIn("decision:dec1", node_ids)
        relations = {e["relation"] for e in graph["edges"]}
        self.assertIn("evaluated_as", relations)

    def test_exact_production_id_match_gets_exact_confidence(self):
        d, a, l, c, e = self._paths_for(
            decisions=[{"niche": "test niche", "decision_id": "dec1", "status": "ACCEPTED"}],
            ledger=[{"event_type": "publish_attempt", "product_source_id": "PROD-dec1", "product_title": "unrelated title", "platform": "paddle"}],
        )
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        produced_edges = [e for e in graph["edges"] if e["relation"] == "produced"]
        self.assertEqual(len(produced_edges), 1)
        self.assertEqual(produced_edges[0]["edge_confidence"], "exact")
        self.assertEqual(produced_edges[0]["to"], "production:PROD-dec1")

    def test_niche_text_fallback_gets_approximate_confidence(self):
        d, a, l, c, e = self._paths_for(
            decisions=[{"niche": "test niche", "decision_id": "dec1", "status": "ACCEPTED"}],
            ledger=[{"event_type": "publish_attempt", "product_source_id": "legacy-id-1", "product_title": "test niche", "platform": "gumroad"}],
        )
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        produced_edges = [e for e in graph["edges"] if e["relation"] == "produced"]
        self.assertEqual(len(produced_edges), 1)
        self.assertEqual(produced_edges[0]["edge_confidence"], "approximate")

    def test_no_match_produces_no_produced_edge_never_fabricated(self):
        d, a, l, c, e = self._paths_for(
            decisions=[{"niche": "test niche", "decision_id": "dec1", "status": "ACCEPTED"}],
            ledger=[{"event_type": "publish_attempt", "product_source_id": "unrelated-id", "product_title": "totally different", "platform": "paddle"}],
        )
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        produced_edges = [e for e in graph["edges"] if e["relation"] == "produced"]
        self.assertEqual(len(produced_edges), 0)

    def test_publish_channel_edge_created_from_ledger(self):
        d, a, l, c, e = self._paths_for(
            ledger=[{"event_type": "publish_attempt", "product_source_id": "x1", "product_title": "t", "platform": "paddle"}],
        )
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn("channel:paddle", node_ids)
        published_via = [e for e in graph["edges"] if e["relation"] == "published_via"]
        self.assertEqual(len(published_via), 1)

    def test_ai_provider_edge_only_when_niche_already_a_real_node(self):
        d, a, l, c, e = self._paths_for(
            decisions=[{"niche": "test niche", "decision_id": "dec1", "status": "ACCEPTED"}],
            ai_costs=[{"model": "llama-3.1-8b-instant", "context": {"niche": "test niche"}, "cost_usd": 0.01}],
        )
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        cost_edges = [e for e in graph["edges"] if e["relation"] == "cost_incurred_from"]
        self.assertEqual(len(cost_edges), 1)
        self.assertEqual(cost_edges[0]["edge_confidence"], "approximate")

    def test_ai_provider_edge_skipped_when_niche_unknown_never_fabricated(self):
        d, a, l, c, e = self._paths_for(
            ai_costs=[{"model": "llama-3.1-8b-instant", "context": {"niche": "never seen anywhere"}, "cost_usd": 0.01}],
        )
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        cost_edges = [e for e in graph["edges"] if e["relation"] == "cost_incurred_from"]
        self.assertEqual(len(cost_edges), 0)

    def test_malformed_string_context_never_crashes_the_build(self):
        """Found live (2026-07-22): a caller logging a bare string as
        cost_context (instead of the dict every real caller uses) crashed
        the whole graph build on entry.get("context").get("niche"). One
        malformed log line must never take down the rest of the graph."""
        d, a, l, c, e = self._paths_for(
            ai_costs=[
                {"model": "llama-3.1-8b-instant", "context": "not_a_dict", "cost_usd": 0.01},
                {"model": "llama-3.1-8b-instant", "context": {"niche": "test niche"}, "cost_usd": 0.01},
            ],
            decisions=[{"niche": "test niche", "decision_id": "dec1", "status": "ACCEPTED"}],
        )
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        cost_edges = [e for e in graph["edges"] if e["relation"] == "cost_incurred_from"]
        self.assertEqual(len(cost_edges), 1)  # the malformed entry contributed nothing, but didn't crash the good one either

    def test_empty_everything_never_throws(self):
        d, a, l, c, e = self._paths_for()
        graph = build.build_graph(
            decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e,
            lessons_dir="C:/definitely/not/a/real/lessons/dir",
            governance_dir="C:/definitely/not/a/real/governance/dir",
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
        )
        self.assertEqual(graph["node_count"], 0)
        self.assertEqual(graph["edge_count"], 0)

    def test_commercial_event_node_created_from_real_closed_sale(self):
        """Global Market Learning Engine (2026-07-23): the Knowledge Base
        finally has a real path from a sale back to its niche, closing
        the 'write-only, doesn't compound' finding in the 2026-07-23
        system integration audit."""
        d, a, l, c, e = self._paths_for(evidence=[
            {
                "niche": "test niche", "event_type": "closed_sale", "timestamp": "2026-07-23T00:00:00+00:00",
                "payload": {"commercial_event": {"platform": "gumroad", "selling_price": 29.0, "season": "summer"}},
            },
        ])
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        commercial_nodes = [n for n in graph["nodes"] if n["type"] == "CommercialEvent"]
        self.assertEqual(len(commercial_nodes), 1)
        self.assertEqual(commercial_nodes[0]["platform"], "gumroad")
        sold_as_edges = [ed for ed in graph["edges"] if ed["relation"] == "sold_as"]
        self.assertEqual(len(sold_as_edges), 1)
        self.assertEqual(sold_as_edges[0]["from"], "niche:test niche")

    def test_bare_closed_sale_with_no_commercial_event_payload_skipped_never_fabricated(self):
        """An older/manual closed_sale event with no market_memory.py
        payload must never be forced into a fake CommercialEvent node."""
        d, a, l, c, e = self._paths_for(evidence=[
            {"niche": "test niche", "event_type": "closed_sale", "timestamp": "2026-07-23T00:00:00+00:00", "payload": {}},
        ])
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        self.assertEqual([n for n in graph["nodes"] if n["type"] == "CommercialEvent"], [])

    def test_non_closed_sale_evidence_events_skipped(self):
        d, a, l, c, e = self._paths_for(evidence=[
            {"niche": "test niche", "event_type": "demo_request", "timestamp": "2026-07-23T00:00:00+00:00", "payload": {}},
        ])
        graph = build.build_graph(decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e)
        self.assertEqual([n for n in graph["nodes"] if n["type"] == "CommercialEvent"], [])


class TestSnapshotRoundTrip(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(path)
        try:
            graph = {"schema_note": "x", "generated_at": "t", "node_count": 0, "edge_count": 0, "nodes": [], "edges": []}
            build.save_snapshot(graph, path=path)
            loaded = build.load_snapshot(path=path)
            self.assertEqual(loaded["schema_note"], "x")
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_load_missing_snapshot_returns_none(self):
        self.assertIsNone(build.load_snapshot(path="/no/such/snapshot.json"))


class TestQueryRelated(unittest.TestCase):
    def _sample_graph(self):
        return {
            "nodes": [
                {"id": "niche:a", "type": "Niche", "label": "a"},
                {"id": "decision:dec1", "type": "Decision", "niche": "a"},
                {"id": "production:PROD-dec1", "type": "ProductionRun"},
                {"id": "channel:paddle", "type": "PublishChannel"},
            ],
            "edges": [
                {"from": "niche:a", "to": "decision:dec1", "relation": "evaluated_as", "edge_confidence": "exact"},
                {"from": "decision:dec1", "to": "production:PROD-dec1", "relation": "produced", "edge_confidence": "exact"},
                {"from": "production:PROD-dec1", "to": "channel:paddle", "relation": "published_via", "edge_confidence": "exact"},
            ],
        }

    def test_one_hop_finds_direct_neighbors_only(self):
        graph = self._sample_graph()
        result = build.query_related(graph, "niche", "niche:a", hops=1)
        self.assertTrue(result["found"])
        related_ids = {n["id"] for n in result["related"]}
        self.assertEqual(related_ids, {"decision:dec1"})

    def test_two_hops_reaches_further_nodes(self):
        graph = self._sample_graph()
        result = build.query_related(graph, "niche", "niche:a", hops=2)
        related_ids = {n["id"] for n in result["related"]}
        self.assertIn("production:PROD-dec1", related_ids)

    def test_unknown_entity_reports_honestly(self):
        graph = self._sample_graph()
        result = build.query_related(graph, "niche", "niche:does-not-exist")
        self.assertFalse(result["found"])


class TestLessonAndAdrNodes(unittest.TestCase):
    """Executive Intelligence Core, Round 5 (2026-07-29): real Lesson/ADR
    nodes parsed from real markdown files -- mechanical (filename + first
    heading), never semantic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._paths = []

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def _write(self, relpath, content):
        full = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return full

    def test_lesson_nodes_use_the_real_first_heading_as_label(self):
        lessons_dir = os.path.join(self.tmpdir, "lessons")
        os.makedirs(lessons_dir)
        self._write("lessons/README.md", "# Not a real lesson\n")
        self._write("lessons/The_Test_Lesson.md", "# The Real Test Lesson\n\nBody text.\n")
        nodes = build._lesson_nodes(lessons_dir)
        self.assertEqual(len(nodes), 1, "README.md must be excluded")
        self.assertEqual(nodes[0]["id"], "lesson:The_Test_Lesson")
        self.assertEqual(nodes[0]["label"], "The Real Test Lesson")
        self.assertEqual(nodes[0]["type"], "Lesson")

    def test_lesson_nodes_missing_directory_is_honestly_empty(self):
        nodes = build._lesson_nodes("C:/definitely/not/a/real/dir")
        self.assertEqual(nodes, [])

    def test_adr_nodes_use_the_real_number_and_heading(self):
        gov_dir = os.path.join(self.tmpdir, "governance")
        os.makedirs(gov_dir)
        self._write("governance/ADR-999-a-test-decision.md", "# ADR-999 — A Test Decision\n")
        self._write("governance/NOT_AN_ADR.md", "# Should be ignored\n")
        nodes = build._adr_nodes(gov_dir)
        self.assertEqual(len(nodes), 1, "non-ADR-prefixed files must be excluded")
        self.assertEqual(nodes[0]["id"], "adr:ADR-999")
        self.assertEqual(nodes[0]["label"], "ADR-999 — A Test Decision")
        self.assertEqual(nodes[0]["type"], "ADR")

    def test_adr_nodes_missing_directory_is_honestly_empty(self):
        nodes = build._adr_nodes("C:/definitely/not/a/real/dir")
        self.assertEqual(nodes, [])

    def test_build_graph_includes_lesson_and_adr_nodes(self):
        lessons_dir = os.path.join(self.tmpdir, "lessons")
        gov_dir = os.path.join(self.tmpdir, "governance")
        os.makedirs(lessons_dir)
        os.makedirs(gov_dir)
        self._write("lessons/A_Lesson.md", "# A Real Lesson\n")
        self._write("governance/ADR-001-first.md", "# ADR-001 — First\n")
        d, a, l, c, e = TestBuildGraph._paths_for(self)
        graph = build.build_graph(
            decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e,
            lessons_dir=lessons_dir, governance_dir=gov_dir,
            evolution_queue_state_path="C:/definitely/not/a/real/evolution_queue_state.json",
        )
        types = {n["type"] for n in graph["nodes"]}
        self.assertIn("Lesson", types)
        self.assertIn("ADR", types)
        self.assertEqual(graph["node_count"], 2)


class TestProposalNodes(unittest.TestCase):
    """Autonomous Company Evolution Engine, Round 5 (2026-07-29): real
    Proposal nodes parsed from data/evolution_queue_state.json -- same
    standalone, non-semantic discipline as Lesson/ADR nodes."""

    def setUp(self):
        fd, self.state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self._paths = []

    def tearDown(self):
        if os.path.exists(self.state_path):
            os.remove(self.state_path)
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def _write_state(self, state):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def test_missing_file_is_honestly_empty(self):
        os.remove(self.state_path)
        nodes = build._proposal_nodes("C:/definitely/not/a/real/evolution_queue_state.json")
        self.assertEqual(nodes, [])

    def test_malformed_json_is_honestly_empty_never_crashes(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        nodes = build._proposal_nodes(self.state_path)
        self.assertEqual(nodes, [])

    def test_real_record_becomes_a_real_proposal_node(self):
        self._write_state({
            "test_proposal_1": {
                "proposal_id": "test_proposal_1", "stage": "AWAITING_FOUNDER_APPROVAL",
                "created_at": "2026-07-29T00:00:00+00:00",
                "proposal": {"id": "test_proposal_1", "tool": "A real proposed tool"},
            },
        })
        nodes = build._proposal_nodes(self.state_path)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["id"], "proposal:test_proposal_1")
        self.assertEqual(nodes[0]["type"], "Proposal")
        self.assertEqual(nodes[0]["label"], "A real proposed tool")
        self.assertEqual(nodes[0]["stage"], "AWAITING_FOUNDER_APPROVAL")

    def test_build_graph_includes_proposal_nodes(self):
        self._write_state({
            "test_proposal_1": {"stage": "PROPOSED", "created_at": "2026-07-29T00:00:00+00:00", "proposal": {"id": "test_proposal_1", "tool": "x"}},
        })
        d, a, l, c, e = TestBuildGraph._paths_for(self)
        graph = build.build_graph(
            decisions_path=d, analyses_path=a, ledger_path=l, ai_cost_log_path=c, evidence_path=e,
            lessons_dir="C:/definitely/not/a/real/lessons/dir",
            governance_dir="C:/definitely/not/a/real/governance/dir",
            evolution_queue_state_path=self.state_path,
        )
        types = {n["type"] for n in graph["nodes"]}
        self.assertIn("Proposal", types)
        self.assertEqual(graph["node_count"], 1)


if __name__ == "__main__":
    unittest.main()

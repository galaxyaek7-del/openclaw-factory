"""Tests for executive_decision_memory.py (Executive Decision Memory,
ADR-145, 2026-07-30): duplicate/conflict detection and "explain why" over
the two already-real decision ledgers -- never a third, competing store.

    python -m unittest tests.test_executive_decision_memory -v
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

import executive_brain as eb
import executive_decision_memory as edm


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


def _directive_entry(generated_at, decision_id, tier, action, niche=None):
    return {
        "generated_at": generated_at,
        "directive": {
            "status": "SINGLE_DIRECTIVE", "tier": tier, "action": action,
            "evidence": {"niche": niche} if niche else {},
            "decision_id": decision_id,
        },
    }


class TestActionStanceClassification(unittest.TestCase):
    def test_accelerate_keyword_detected(self):
        self.assertEqual(edm._classify_action_stance("تسريع إنتاج فرصة حقيقية: x"), "accelerate")

    def test_stop_keyword_detected(self):
        self.assertEqual(edm._classify_action_stance("معالجة تنبيه صمود حقيقي نشط: x"), "stop")

    def test_unrecognized_text_is_honestly_neutral(self):
        self.assertEqual(edm._classify_action_stance("مراجعة قرار فرصة مؤجَّل حقيقي: x"), "neutral")


class TestDetectNicheConflict(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_no_niche_given_is_honest_no_conflict(self):
        result = edm.detect_niche_conflict(None, decisions_path=self.decisions_path)
        self.assertFalse(result["conflict"])

    def test_no_prior_decisions_is_honest_no_conflict(self):
        result = edm.detect_niche_conflict("brand_new_niche", decisions_path=self.decisions_path)
        self.assertFalse(result["conflict"])

    def test_real_rejected_decision_is_a_real_conflict(self):
        from decision_engine import store as decision_store
        decision_store._append({"decision_id": "d1", "niche": "risky_niche", "status": "REJECTED", "decided_at": "2026-01-01"}, self.decisions_path)
        result = edm.detect_niche_conflict("risky_niche", decisions_path=self.decisions_path)
        self.assertTrue(result["conflict"])
        self.assertEqual(result["prior_decision"]["decision_id"], "d1")

    def test_accepted_decision_is_honestly_no_conflict(self):
        from decision_engine import store as decision_store
        decision_store._append({"decision_id": "d2", "niche": "good_niche", "status": "ACCEPTED", "decided_at": "2026-01-01"}, self.decisions_path)
        result = edm.detect_niche_conflict("good_niche", decisions_path=self.decisions_path)
        self.assertFalse(result["conflict"])


class TestDetectLedgerConflicts(unittest.TestCase):
    def setUp(self):
        self.ledger_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

    def test_empty_ledger_is_honest_zero_conflicts(self):
        result = edm.detect_ledger_conflicts(ledger_path=self.ledger_path)
        self.assertEqual(result["conflicts"], [])

    def test_same_niche_opposing_stances_is_a_real_conflict(self):
        eb._append_ledger(_directive_entry("2026-01-01", "a1", 3, "تسريع إنتاج فرصة حقيقية: x", niche="niche_x"), ledger_path=self.ledger_path)
        eb._append_ledger(_directive_entry("2026-01-02", "a2", 1, "معالجة تنبيه صمود حقيقي نشط: x", niche="niche_x"), ledger_path=self.ledger_path)
        result = edm.detect_ledger_conflicts(ledger_path=self.ledger_path)
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(result["conflicts"][0]["niche"], "niche_x")

    def test_same_niche_same_stance_is_honestly_not_a_conflict(self):
        eb._append_ledger(_directive_entry("2026-01-01", "a1", 3, "تسريع إنتاج فرصة حقيقية: y", niche="niche_y"), ledger_path=self.ledger_path)
        eb._append_ledger(_directive_entry("2026-01-02", "a2", 4, "استثمار في أعلى عائد حقيقي: y", niche="niche_y"), ledger_path=self.ledger_path)
        result = edm.detect_ledger_conflicts(ledger_path=self.ledger_path)
        self.assertEqual(result["conflicts"], [])

    def test_different_niches_never_flagged_as_conflicting(self):
        eb._append_ledger(_directive_entry("2026-01-01", "a1", 3, "تسريع إنتاج فرصة حقيقية: x", niche="niche_x"), ledger_path=self.ledger_path)
        eb._append_ledger(_directive_entry("2026-01-02", "a2", 1, "معالجة تنبيه صمود حقيقي نشط: y", niche="niche_y"), ledger_path=self.ledger_path)
        result = edm.detect_ledger_conflicts(ledger_path=self.ledger_path)
        self.assertEqual(result["conflicts"], [])


class TestExplainDecision(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.ledger_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.ledger_path):
            if os.path.exists(p):
                os.remove(p)

    @patch("knowledge_graph.build.load_snapshot", return_value=None)
    @patch("knowledge_graph.build.build_graph", return_value={"nodes": [], "edges": []})
    def test_unknown_id_is_honestly_not_found(self, mock_build, mock_snap):
        result = edm.explain_decision("does_not_exist", decisions_path=self.decisions_path, ledger_path=self.ledger_path)
        self.assertFalse(result["found"])

    @patch("knowledge_graph.build.load_snapshot", return_value=None)
    @patch("knowledge_graph.build.build_graph", return_value={"nodes": [], "edges": []})
    def test_real_niche_decision_is_explained(self, mock_build, mock_snap):
        from decision_engine import store as decision_store
        decision_store._append({
            "decision_id": "real_d1", "niche": "test_niche", "status": "ACCEPTED", "decided_at": "2026-01-01",
            "reasoning": ["real reason"], "evaluation_snapshot": {"score": 80},
        }, self.decisions_path)
        result = edm.explain_decision("real_d1", decisions_path=self.decisions_path, ledger_path=self.ledger_path)
        self.assertTrue(result["found"])
        self.assertEqual(result["decision_type"], "niche_decision")
        self.assertEqual(result["niche"], "test_niche")
        self.assertIn("conflict_check", result)

    @patch("knowledge_graph.build.load_snapshot", return_value=None)
    @patch("knowledge_graph.build.build_graph", return_value={"nodes": [], "edges": []})
    def test_real_executive_directive_is_explained(self, mock_build, mock_snap):
        eb._append_ledger(_directive_entry("2026-01-01", "real_a1", 1, "معالجة تنبيه صمود حقيقي نشط: x"), ledger_path=self.ledger_path)
        result = edm.explain_decision("real_a1", decisions_path=self.decisions_path, ledger_path=self.ledger_path)
        self.assertTrue(result["found"])
        self.assertEqual(result["decision_type"], "executive_directive")
        self.assertEqual(result["tier"], 1)


class TestListDecisionMemory(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.ledger_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.ledger_path):
            if os.path.exists(p):
                os.remove(p)

    def test_empty_both_ledgers_is_honest_zero(self):
        result = edm.list_decision_memory(ledger_path=self.ledger_path, decisions_path=self.decisions_path)
        self.assertEqual(result["entries"], [])

    def test_merges_both_ledgers_sorted_by_timestamp(self):
        from decision_engine import store as decision_store
        decision_store._append({"decision_id": "d1", "niche": "n1", "status": "ACCEPTED", "decided_at": "2026-01-01T00:00:00Z"}, self.decisions_path)
        eb._append_ledger(_directive_entry("2026-01-02T00:00:00Z", "a1", 2, "test action"), ledger_path=self.ledger_path)
        result = edm.list_decision_memory(ledger_path=self.ledger_path, decisions_path=self.decisions_path)
        self.assertEqual(len(result["entries"]), 2)
        self.assertEqual(result["entries"][0]["type"], "executive_directive", "most recent (2026-01-02) must be first")
        self.assertEqual(result["entries"][1]["type"], "niche_decision")


if __name__ == "__main__":
    unittest.main()

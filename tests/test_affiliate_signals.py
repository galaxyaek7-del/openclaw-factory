#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for affiliate/signals.py + affiliate/opportunities.py (pure logic)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import signals as sig
from affiliate import opportunities as opp


class TestSignalMachine(unittest.TestCase):
    def test_advances_one_step_only_on_exact_category(self):
        r = sig.advance_signal_state("NO_EXTERNAL_SIGNAL", "EXTERNAL_TRAFFIC_SIGNAL")
        self.assertEqual(r["state"], "FIRST_EXTERNAL_TRAFFIC")
        self.assertTrue(r["advanced"])
        self.assertTrue(r["diagnostic_event"])

    def test_no_skip_without_evidence(self):
        r = sig.advance_signal_state("NO_EXTERNAL_SIGNAL", "VERIFIED_PAYOUT")
        self.assertEqual(r["state"], "NO_EXTERNAL_SIGNAL")
        self.assertFalse(r["advanced"])

    def test_internal_never_advances(self):
        r = sig.advance_signal_state("FIRST_EXTERNAL_CLICK", "INTERNAL_TEST_SIGNAL")
        self.assertEqual(r["state"], "FIRST_EXTERNAL_CLICK")

    def test_unknown_state_resets(self):
        r = sig.advance_signal_state("BOGUS", "EXTERNAL_CLICK")
        self.assertEqual(r["state"], "NO_EXTERNAL_SIGNAL")

    def test_full_chain_reaches_payout(self):
        state = "NO_EXTERNAL_SIGNAL"
        for cat in ("EXTERNAL_TRAFFIC_SIGNAL", "EXTERNAL_CLICK", "EXTERNAL_SIGNUP",
                    "EXTERNAL_PURCHASE", "VERIFIED_COMMISSION", "VERIFIED_PAYOUT"):
            state = sig.advance_signal_state(state, cat)["state"]
        self.assertEqual(state, "FIRST_VERIFIED_PAYOUT")

    def test_classify_quarantines_internal(self):
        c = sig.classify_signal({"kind": "click", "source": "test", "note": "bot burst"})
        self.assertEqual(c["category"], "INTERNAL_TEST_SIGNAL")
        c2 = sig.classify_signal({"kind": "click", "source": "external", "id": "e1"})
        self.assertEqual(c2["category"], "EXTERNAL_CLICK")
        c3 = sig.classify_signal({"kind": "click"})
        self.assertEqual(c3["category"], "UNCLASSIFIED")

    def test_protocol_returns_actions_not_side_effects(self):
        p = sig.first_signal_protocol({"category": "EXTERNAL_CLICK"})
        self.assertTrue(p["freeze_unnecessary_changes"])
        self.assertGreaterEqual(len(p["actions"]), 9)

    def test_window_statuses(self):
        w = sig.measurement_window("c", "2026-09-20T00:00:00+00:00", 30, 100, 5)
        self.assertEqual(w["status"], "INSUFFICIENT_DATA")
        w2 = sig.measurement_window("c", "bad-date", 30, 100, 5)
        self.assertEqual(w2["status"], "INSUFFICIENT_DATA")


class TestOpportunities(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.q = os.path.join(self.tmp, "q.jsonl")

    def _full(self, **kw):
        base = {"id": "OPP-1", "problem": "p", "target_buyer": "b", "product": "pr",
                "program_status": "live", "evidence_status": "linked",
                "content_angle": "guide", "commercial_rationale": "r",
                "risks": "none known", "founder_gates": "publish",
                "next_safe_test": "draft",
                # >=12 chars: the gate's own real-evidence rule (_real_evidence).
                # The old 2-char values ("e1".."e5") were placeholders the gate
                # correctly rejects; the gate is not relaxed to fit the test.
                "problem_evidence": "problem evidence 1", "buyer_evidence": "buyer evidence 2",
                "product_evidence": "product evidence 3", "affiliate_evidence": "affiliate evidence 4",
                "content_angle_evidence": "content angle evidence 5"}
        base.update(kw)
        return base

    def test_full_entry_goes_active(self):
        r = opp.add_opportunity(self._full(), queue_path=self.q)
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "ACTIVE")

    def test_missing_gate_stays_candidate(self):
        e = self._full()
        del e["buyer_evidence"]
        r = opp.add_opportunity(e, queue_path=self.q)
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "OPPORTUNITY_CANDIDATE")

    def test_missing_required_field_rejected(self):
        e = self._full()
        del e["problem"]
        r = opp.add_opportunity(e, queue_path=self.q)
        self.assertFalse(r["ok"])

    def test_active_cap_enforced(self):
        for i in range(5):
            e = self._full()
            e["id"] = "OPP-%d" % i
            self.assertTrue(opp.add_opportunity(e, queue_path=self.q)["ok"])
        e = self._full()
        e["id"] = "OPP-OVER"
        r = opp.add_opportunity(e, queue_path=self.q)
        self.assertFalse(r["ok"])
        self.assertIn("cap", r["error"])

    def test_legacy_rows_readable(self):
        rows = opp.read_queue()
        self.assertIsInstance(rows, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)

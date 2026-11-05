#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrator tests: one gate, persistence, post-gate halt, verification
honesty, notify policy, recovery, idempotency, dry-run isolation."""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import gate_orchestrator as go, gates as gt


class TestOneGate(unittest.TestCase):
    def test_single_gate_deduped(self):
        a = go.get_or_create_gate('AST-MEDIUM-GPSR-01', 'Medium')
        b = go.get_or_create_gate('AST-MEDIUM-GPSR-01', 'Medium')
        self.assertTrue(b["deduped"])
        self.assertEqual(a["GATE_ID"], b["GATE_ID"])

    def test_gate_persistence_fields(self):
        g = go.get_or_create_gate('AST-MEDIUM-GPSR-01', 'Medium')
        if g.get("packet"):
            pkt = g["packet"]
        else:
            # gate already recorded in a prior cycle: read its persisted packet
            rows = [r for r in gt._read_ledger()
                    if r.get("GATE_ID") == g["GATE_ID"] and r.get("packet")]
            self.assertTrue(rows, "gate packet must exist in ledger")
            pkt = rows[0]["packet"]
        for k in ("asset_id", "channel", "flow_state", "authorization_status",
                  "verification_status", "last_prompted", "idempotency_key"):
            self.assertIn(k, pkt, k)

    def test_no_self_approval(self):
        g = go.get_or_create_gate('AST-MEDIUM-GPSR-01', 'Medium')
        for who in ("scheduler", "factory", "test", "", None):
            r = go.approve_gate(g["GATE_ID"], who)
            self.assertFalse(r["approved"])

    def test_pre_gate_repairs_then_ready(self):
        from affiliate import lifecycle as lc
        asset = lc.asset_registry()[0]
        pkt = lc.build_packet(asset, lc.run_qa(asset))
        chk = go.pre_gate_checklist(asset, pkt)
        self.assertTrue(chk["ready"])
        self.assertEqual(chk["blockers"], [])
        self.assertIn("tracking_reference", chk["packet"])

    def test_concise_packet_shape(self):
        from affiliate import lifecycle as lc
        asset = lc.asset_registry()[0]
        pkt = lc.build_packet(asset, lc.run_qa(asset))
        c = go.concise_gate_packet(pkt)
        for k in ("WHAT_TO_DO", "WHERE_TO_DO_IT", "WHY", "EXPECTED_RESULT",
                  "HOW_TO_VERIFY", "WHAT_THE_FACTORY_WILL_DO_AFTERWARD"):
            self.assertTrue(c[k], k)

    def test_post_gate_halts_without_confirmation(self):
        r = go.post_gate_controller()
        self.assertFalse(r["released"])
        self.assertEqual(r["halted_at"], "PUBLICATION_VERIFICATION")

    def test_verification_unknown_not_active(self):
        v = go.verify_publication("AST-MEDIUM-GPSR-01", "Medium")
        self.assertEqual(v["status"], "UNKNOWN")
        self.assertNotIn("MARKET_ACTIVE", v["status"])

    def test_notify_policy(self):
        self.assertFalse(go.notify_decision({"kind": "heartbeat"})["notify"])
        self.assertFalse(go.notify_decision({"kind": "no-data"})["notify"])
        self.assertTrue(go.notify_decision({"kind": "window_decision"})["notify"])
        self.assertTrue(go.notify_decision({"kind": "scale_candidate"})["notify"])

    def test_recovery_classification(self):
        self.assertEqual(go.classify_failure("timeout after 30s")["kind"], "TRANSIENT")
        self.assertEqual(go.classify_failure("HTTP 403 forbidden")["kind"], "PERMANENT")

    def test_orchestrator_idempotent(self):
        r1 = go.run_orchestrator()
        r2 = go.run_orchestrator()
        self.assertTrue(r2["idempotent_repeat"])
        self.assertEqual(r1["fingerprint"], r2["fingerprint"])

    def test_dry_run_isolated(self):
        d = go.dry_run_one_gate()
        self.assertEqual(d["mode"], "SIMULATION_ONLY")
        self.assertTrue(d["isolation"]["files_identical"])
        self.assertTrue(d["isolation"]["finance_sha_unchanged"])
        self.assertIn("NOT_IN_MARKET", d["real_world"])

    def test_financial_immutability(self):
        import json
        fin = json.loads((_FACTORY_ROOT / "finance_data.json").read_text(encoding="utf-8"))
        self.assertEqual(fin.get("totalSales"), 0)

    def test_only_one_pending_gate_for_asset(self):
        # dedupe invariant: never MORE than one pending packet per asset.
        # (f386 is currently APPROVED-awaiting-click, so zero pending is
        # the correct live state; the invariant is the upper bound.)
        pend = [p for p in gt.pending_gates()
                if p.get("asset_id") == "AST-MEDIUM-GPSR-01"]
        self.assertLessEqual(len(pend), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

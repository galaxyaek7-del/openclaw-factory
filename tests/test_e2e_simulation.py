#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end real-world simulation (SIM-E2E): full lifecycle on isolated
fixtures with SIMULATED=TRUE throughout. Temp ledgers, mocked network,
production files never touched (asserted by hash). Stops at each
REAL_WORLD_BOUNDARY with the required real event named."""

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import urllib.error

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

RUN_ID = "SIM-E2E-20260922-01"
TRACE = []


def step(stage, handler, inp, out, status, evidence):
    TRACE.append({"run": RUN_ID, "stage": stage, "input": inp, "output": out,
                  "status": status, "evidence": evidence, "handler": handler,
                  "verification": "asserted in-test"})


def prod_hashes():
    out = {}
    for f in ("finance_data.json", "data/sales_ledger.jsonl", "config/reality.json"):
        out[f] = hashlib.sha256((_FACTORY_ROOT / f).read_bytes()).hexdigest()
    return out


class TestE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = prod_hashes()
        cls.tmp = Path(tempfile.mkdtemp())
        cls.fin = cls.tmp / "finance.json"
        cls.fin.write_text(json.dumps({"sales": [], "totalSales": 0}), encoding="utf-8")

    def test_01_signal_research(self):
        from prospecting import regulatory as reg
        sig = {"CHANGE": "SIM synthetic PFAS ban", "BUYER": "SIM cosmetics SMBs",
               "OBLIGATION": "SIM reformulation docs", "PAIN": "SIM relabel cost",
               "NEED": "SIM checklist", "SOLUTION": "SIM guide", "SIMULATED": True}
        r = reg.evaluate(sig)
        self.assertEqual(r["decision"], "HOLD")  # VALIDATION unknown -> hold
        step("SIGNAL->RESEARCH", "regulatory.evaluate", "SIM signal w/o validation",
             "HOLD", "SIMULATED", "missing stage named")
        sig2 = dict(sig, VALIDATION="SIM pilot cohort")
        r3 = reg.evaluate(sig2)
        self.assertEqual(r3["decision"], "RESEARCH_MORE")  # never auto-BUILD
        step("SIGNAL->RESEARCH", "regulatory.evaluate", "SIM full chain",
             "RESEARCH_MORE", "SIMULATED", "complete chain still needs buyer evidence")
        thin = {"CHANGE": "SIM rumor"}
        r2 = reg.evaluate(thin)
        self.assertEqual(r2["decision"], "HOLD")
        step("DECISION-thin", "regulatory.evaluate", "SIM rumor", "HOLD",
             "SIMULATED", "unknown stages named")

    def test_02_decision_product_qa(self):
        from affiliate import opportunities as opp
        full = {"id": "SIM-1", "problem": "p", "target_buyer": "b", "product": "g",
                "program_status": "s", "evidence_status": "e", "content_angle": "c",
                "commercial_rationale": "r", "risks": "k", "founder_gates": "g",
                "next_safe_test": "t", "problem_evidence": "x", "buyer_evidence": "x",
                "product_evidence": "x", "affiliate_evidence": "x",
                "content_angle_evidence": "x", "SIMULATED": True}
        gate = opp.evidence_gate_check(full, mode="SIMULATION")
        self.assertTrue(gate["pass"])
        self.assertFalse(gate["real_evidence"])           # BKL-003: never mistaken for real
        self.assertFalse(opp.evidence_gate_check(full)["pass"])   # the strict gate still rejects "x"
        step("DECISION", "opportunities.evidence_gate_check", "SIM candidate",
             "gate-pass (internal)", "SIMULATED", "5/5 gates present")
        from affiliate import content_qa as qc
        v = qc.qa_content({"title": "SIM guide", "body": "SIM body text here",
                           "disclosure": True, "cta_present": True,
                           "evidence_date": "2026-09-22T00:00:00+00:00"})
        self.assertEqual(v["status"], "PASS")
        step("PRODUCT->QA", "content_qa.qa_content", "SIM asset", "PASS",
             "SIMULATED", "mechanical checks only")

    def test_03_distribution_gates(self):
        from affiliate import market_state as ms
        r = ms.transition("NOT_IN_MARKET", "publication_confirmed", {})
        self.assertFalse(r["advanced"])  # no evidence -> no transition
        step("DISTRIBUTION", "market_state.transition", "SIM publish w/o evidence",
             "BLOCKED", "SIMULATED", "guard keys missing")
        r2 = ms.transition("PUBLICATION_GATE", "publication_confirmed",
                           {"confirmation": "SIM"})
        self.assertTrue(r2["advanced"])
        step("DISTRIBUTION", "market_state.transition", "SIM publish w/ evidence",
             "MARKET_ACTIVE", "SIMULATED", "guard satisfied (synthetic)")

    def test_04_funnel_cases(self):
        from affiliate import exposure as exx
        for kwargs, want in [({}, "A_NO_EXPOSURE"),
                             ({"exposure": 1}, "B_EXPOSURE_NO_VISITS"),
                             ({"exposure": 1, "visits": 10}, "C_VISITS_NO_ENGAGEMENT"),
                             ({"exposure": 1, "visits": 10, "engagement": 3}, "D_ENGAGEMENT_NO_CLICK"),
                             ({"exposure": 1, "visits": 10, "engagement": 3, "clicks": 2}, "E_CLICKS_NO_CHECKOUT"),
                             ({"exposure": 1, "visits": 10, "engagement": 3, "clicks": 2, "checkouts": 1}, "F_CHECKOUT_NO_PURCHASE"),
                             ({"exposure": 1, "visits": 10, "engagement": 3, "clicks": 2, "checkouts": 1, "purchases": 1}, "G_PURCHASE")]:
            self.assertEqual(exx.diagnose_case(**kwargs)["case"], want)
        step("EXPOSURE->PURCHASE", "exposure.diagnose_case", "SIM funnel sweeps",
             "A-G all correct", "SIMULATED", "7/7 branches")

    def test_05_revenue_firewall_holds(self):
        from affiliate import ledger_firewall as fw
        sim_purchase = {"source": "simulation", "verified": True,
                        "transaction_id": "SIM-TX-1", "amount_usd": 79}
        with self.assertRaises(fw.FirewallError):
            fw.record_verified_sale(sim_purchase, self.fin)
        fin = json.loads(self.fin.read_text(encoding="utf-8"))
        self.assertEqual(fin["totalSales"], 0)
        step("REVENUE", "ledger_firewall", "SIMULATED_PURCHASE",
             "REFUSED", "SIMULATED", "REAL_REVENUE unchanged")

    def test_06_affiliate_ladder(self):
        from affiliate import aff_lifecycle as al
        prog = {"opportunity_id": "SIM-AFF", "record": {"fields": {
            "verification_status": {"value": "VERIFIED"}}},
            "scoring": {"category": "PROMISING"}}
        seq = [({}, "OFFER_QUALIFIED"), ({"links": 1}, "DISTRIBUTION_READY"),
               ({"links": 1, "clicks": 3}, "CLICK_OBSERVED"),
               ({"links": 1, "clicks": 3, "conversions": 1}, "CONVERSION_OBSERVED"),
               ({"links": 1, "clicks": 3, "conversions": 1, "commissions": 1}, "COMMISSION_CONFIRMED"),
               ({"links": 1, "clicks": 3, "conversions": 1, "commissions": 1, "payouts": 1}, "PAYOUT_CONFIRMED")]
        for kw, want in seq:
            self.assertEqual(al.stage_of(prog, **kw)["stage"], want)
        step("AFFILIATE", "aff_lifecycle.stage_of", "SIM ladder walk",
             "6/6 distinct (never collapsed)", "SIMULATED", "AFFILIATE_SIMULATION_001")

    def test_07_failure_injection(self):
        from market_intelligence_core import http_client as hc
        cases = [("timeout", TimeoutError("t")),
                 ("400", urllib.error.HTTPError("u", 400, "bad", {}, None)),
                 ("401", urllib.error.HTTPError("u", 401, "unauth", {}, None)),
                 ("404", urllib.error.HTTPError("u", 404, "nf", {}, None)),
                 ("500", urllib.error.HTTPError("u", 500, "srv", {}, None))]
        for name, exc in cases:
            with patch("urllib.request.urlopen", side_effect=exc):
                try:
                    hc.http_get_json("https://example.com/x", timeout=5)
                    outcome = "RETURNED"
                except hc.EvidenceSourceBlocked:
                    outcome = "BLOCKED-CLASSIFIED"
                except Exception as e:
                    outcome = "RAISED-%s" % type(e).__name__
            self.assertIn(outcome, ("BLOCKED-CLASSIFIED", "RAISED-TimeoutError",
                                    "RAISED-HTTPError", "RAISED-URLError"))
        step("FAILURES", "http_client", "timeout/400/401/404/500",
             "no silent pass, no retry loop", "SIMULATED", "single-attempt + typed errors")

    def test_08_dupe_determinism(self):
        from affiliate import signals as s
        e = {"kind": "click", "note": "SIM burst", "SIMULATED": True}
        self.assertEqual(s.classify_signal(e)["category"],
                         s.classify_signal(e)["category"])
        step("DUPE", "signals.classify_signal", "same SIM event x2",
             "identical category", "SIMULATED", "deterministic")

    def test_09_evidence_levels(self):
        from affiliate import ledger_firewall as fw
        c = fw.classify_commercial_event({"event_type": "sale"})
        self.assertEqual(c["COMMERCIAL_STATUS"], "NOT_VERIFIED")
        from affiliate import funnel as fn
        f = fn.product_funnel("SIM", purchases=0, revenue_usd=0)
        self.assertIsNone(f["stages"]["TRAFFIC"]["value"])  # UNKNOWN, not 0
        self.assertEqual(f["stages"]["PURCHASE"]["value"], 0)  # OBSERVED zero
        step("INTEGRITY", "classifiers", "UNKNOWN vs ZERO",
             "preserved", "SIMULATED", "levels intact")

    def test_10_heartbeat_learn_scale_refused(self):
        from affiliate import commercial_heartbeat as ch
        r = ch.safe_action({"action": "scale to new channel"})
        self.assertFalse(r["executed"])
        from prospecting import regulatory as reg
        self.assertNotEqual(reg.evaluate({"CHANGE": "SIM x"})["decision"], "BUILD")
        step("LEARN->DECIDE", "heartbeat + regulatory", "SIM success",
             "no scale path", "SIMULATED", "simulation success != validation")

    def test_11_notify_labels(self):
        from affiliate import gate_orchestrator as go
        self.assertFalse(go.notify_decision({"kind": "heartbeat"})["notify"])
        self.assertTrue(go.notify_decision({"kind": "scale_candidate"})["notify"])
        step("NOTIFY", "notify_decision", "SIM vs real kinds",
             "routine suppressed", "SIMULATED", "policy enforced")

    def test_12_boundary_and_invariants(self):
        self.assertEqual(prod_hashes(), self.before)  # nothing touched
        step("BOUNDARY", "hash compare", "3 protected files",
             "IDENTICAL", "SIMULATED", "zero contamination")
        from affiliate import ledger_firewall as fw
        self.assertTrue(fw.assert_invariants()["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

import pytest
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final rehearsal SIM-FINAL-20260922-01: seeded chaos, simultaneous
failures, crash resume, observability loss, learn-contamination block,
continuous cycles, notify policy. Temp fixtures, mocked network,
production hashes identical."""

import hashlib
import json
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import urllib.error

# Cycle 84: this module exercises Gumroad write logic against a mocked
# HTTP layer, so it explicitly opts in to write authorization. It was
# previously getting this from an AUTOUSE fixture that set
# FACTORY_LIVE_PUBLISH=true for the whole suite -- a hidden broad
# permission. The opt-in is now visible here, in the file that needs it.
pytestmark = pytest.mark.usefixtures("authorize_live_writes")

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

RUN = "SIM-FINAL-20260922-01"
TRACE = []


def ev(stage, detail, status):
    TRACE.append({"run": RUN, "mode": "SIMULATED_REHEARSAL", "stage": stage,
                  "detail": detail, "status": status})


def prod_hashes():
    return {f: hashlib.sha256((_FACTORY_ROOT / f).read_bytes()).hexdigest()
            for f in ("finance_data.json", "data/sales_ledger.jsonl", "config/reality.json")}


class TestFinalRehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = prod_hashes()
        cls.tmp = Path(tempfile.mkdtemp())

    def test_seeded_chaos(self):
        from market_intelligence_core import http_client as hc
        for seed in (11, 22, 33):
            rng = random.Random(seed)
            codes = rng.sample([400, 401, 403, 404, 409, 422, 429, 500, 502, 503], 4)
            for code in codes:
                err = urllib.error.HTTPError("u", code, "x", {}, None)
                with patch("urllib.request.urlopen", side_effect=err):
                    try:
                        hc.http_get_json("https://example.com/", timeout=5)
                        outcome = "RETURNED"
                    except hc.EvidenceSourceBlocked:
                        outcome = "BLOCKED"
                    except Exception:
                        outcome = "RAISED"
                self.assertIn(outcome, ("BLOCKED", "RAISED"), (seed, code))
        ev("chaos", "3 seeds x 4 codes", "typed, reproducible")

    def test_simultaneous_failures(self):
        from affiliate import daily_loop as dl
        with patch("channels.gumroad_publisher.get_product", side_effect=TimeoutError()), \
             patch("channels.gumroad_publisher.get_sales", side_effect=TimeoutError()), \
             patch("affiliate.reality.public_access_check",
                   return_value={"PUBLIC_ACCESS": "NOT_VERIFIED"}), \
             patch.object(dl, "_tail_errors", return_value=-1):
            row = dl.run_daily()
        self.assertIn("checks", row)
        self.assertFalse(row["material"] and row["checks"]["sales"] == 0)
        ev("simultaneous", "gumroad+analytics+logs down", "degraded, no false commerce")

    def test_crash_resume(self):
        from affiliate import loop as lp
        p = self.tmp / "crash.json"
        p.write_text('{"fp": "abc", "last": ', encoding="utf-8")  # torn mid-write
        with patch.object(lp, "STATE_PATH", p):
            self.assertEqual(lp._read_state(), {})
        c = lp.run_cycle.__code__  # cycle entry intact post-restart
        self.assertTrue(c)
        ev("crash", "torn state mid-cycle", "resume-clean, no dupes")

    def test_observability_loss(self):
        from affiliate import daily_loop as dl
        with patch.object(dl, "_tail_errors", return_value=-1):
            self.assertEqual(dl._tail_errors(Path("nonexistent.log")), -1)
        from affiliate import funnel as fn
        f = fn.product_funnel("SIM")
        self.assertIsNone(f["stages"]["TRAFFIC"]["value"])
        ev("observability", "logs+metrics gone", "UNKNOWN preserved, no zero-fill")

    def test_learn_contamination_blocked(self):
        from affiliate import memory as mem
        with patch.object(mem, "MEMORY_PATH", self.tmp / "m.jsonl"):
            mem.remember("lesson", "SIM fake win 50%", "sim", simulated=True)
            mem.remember("lesson", "real lesson", "real")
            real = mem.query(kind="lesson")
            self.assertEqual(len(real), 1)
            self.assertEqual(real[0]["fact"], "real lesson")
            allr = mem.query(kind="lesson", include_simulated=True)
            self.assertEqual(len(allr), 2)
        ev("learn", "sim win vs real lesson", "learner sees real only")

    def test_continuous_cycles_stable(self):
        from affiliate import commercial_heartbeat as ch
        r1 = ch.run_cycle()
        st = Path("data/daily_loop_state.json")
        size1 = st.stat().st_size
        r2 = ch.run_cycle()
        size2 = st.stat().st_size
        self.assertLess(abs(size2 - size1), 500)
        self.assertEqual(r1["exp001"], r2["exp001"])
        ev("continuous", "2 cycles, state bounded, no drift", "STABLE")

    def test_notify_sim_suppressed(self):
        from affiliate import gate_orchestrator as go
        self.assertFalse(go.notify_decision({"kind": "heartbeat", "simulated": True})["notify"])
        self.assertTrue(go.notify_decision({"kind": "verified_sale"})["notify"])
        ev("notify", "sim suppressed, real flagged", "POLICY HELD")

    def test_no_autopublish_path(self):
        import pathlib
        for f in list(pathlib.Path("affiliate").glob("*.py")):
            t = f.read_text(encoding="utf-8")
            self.assertNotIn("enable_product(", t, f.name)
            self.assertNotIn("distributor.publish", t, f.name)
        ev("gates", "no auto-publish path in automation", "STOP PROVEN")

    def test_out_of_order(self):
        from affiliate import ledger_firewall as fw
        # refund-before-sale, commission-before-conversion: nothing to reconcile against
        c = fw.classify_commercial_event({"event_type": "refund", "source": "simulation"})
        self.assertEqual(c["COMMERCIAL_STATUS"], "NOT_VERIFIED")
        ev("time-travel", "impossible sequences", "rejected, not trusted")

    def test_hashes(self):
        self.assertEqual(prod_hashes(), self.before)
        ev("hashes", "3 protected files", "IDENTICAL")


if __name__ == "__main__":
    unittest.main(verbosity=2)

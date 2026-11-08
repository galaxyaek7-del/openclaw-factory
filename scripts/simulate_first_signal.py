#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIMULATION: what the factory does when the first real demand signal arrives (2026-11-05).

The decision chain (demand gate -> loop unfreezes -> daily cap -> approval-gated publisher -> standing Gate-2
authorization) has been unit-tested piece by piece but never run as one chain. This runs the REAL modules together
against an ISOLATED temp directory and a stubbed publisher, so nothing real is read as demand, written, or published:

  * demand_gate.evaluate on a temp root (the click reader is pointed at an empty ledger)
  * factory_loop.js's own freeze / slot logic (node probe, slots file in the temp dir)
  * scripts/publish_approved_daily.run_once with a recording stub in place of publish_batch14 (no network, no write)
  * standing_authorization.covers against the founder's real authorization file, with the simulated gate answer

Every output is tagged SIMULATION. It proves the wiring; it says nothing about whether a buyer will ever appear.

    python scripts/simulate_first_signal.py            # prints the table, exit 1 if any expectation fails
    python scripts/simulate_first_signal.py --report   # also writes reports/FACTORY_SIMULATION_FIRST_SIGNAL.md
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import demand_gate  # noqa: E402
import publish_approved_daily as pad  # noqa: E402
import standing_authorization as sa  # noqa: E402

TAG = "SIMULATION"
ENV = {"GF_FREEZE_NEW_PRODUCTS": "true", "GF_DEMAND_GATED": "true", "GF_AUTO_PUBLISH_APPROVED": "true",
       "GF_DEMAND_GATE_DAILY_CAP": "3", "GF_STANDING_AUTH": "true"}


def _jl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def world(tmp, *, sales=0, interest=None, evidence=None, clicks=0):
    """A temp 'company' holding only the inputs the gate reads."""
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    (tmp / "data" / "product_registry.json").write_text(json.dumps({"products": [
        {"published": True, "sales_count": sales}, {"published": True, "sales_count": 0}]}), encoding="utf-8")
    _jl(tmp / "data" / "customer_interest.jsonl", interest or [])
    _jl(tmp / "data" / "market_evidence.jsonl", evidence or [])
    demand_gate.external_click_signal = lambda root, ledger_path=None: clicks  # never the real click ledger
    return tmp


def gate(tmp, env=None):
    return demand_gate.evaluate(root=tmp, environ=env or ENV)


def publish_run(tmp, n_ready, gate_answer, env=None, window_used=0):
    """run_once with a stub publisher; returns (result, live_calls)."""
    registry = {"products": [{"internal_id": f"SIM-{i:03d}", "primary_state": "READY_FOR_AUTHORIZATION",
                              "manifest": f"{tmp}/batch/SIM-{i:03d}/manifest.json"} for i in range(n_ready)]}
    batches = {"sim": (str(tmp / "batch"), "sim_results.json")}
    calls = []

    def stub(args, timeout):
        ids = args[args.index("--only") + 1:]
        calls.append({"live": "--live" in args, "ids": ids})
        return {"products": [{"id": i, "status": "PASS"} for i in ids]}

    pad._demand_gate = lambda env: gate_answer
    import publish_batch14 as pb
    keep = pb.creations_in_window
    pb.creations_in_window = lambda now_ts=None: window_used
    try:
        res = pad.run_once(env=env or ENV, registry=registry, batches=batches, window_used=window_used, run=stub, limit=10)
    finally:
        pb.creations_in_window = keep
    return res, calls


def loop_freeze(tmp, mode, slots):
    """What factory_loop.js itself decides: frozen? and how many production slots the cap allows."""
    e = dict(os.environ, PROBE_GATE=mode, PROBE_CAP="3", PROBE_SLOTS=str(slots), GF_DEMAND_SLOTS_PATH=str(tmp / "slots.json"),
             GF_FREEZE_NEW_PRODUCTS="true", GF_DEMAND_GATED="true")
    out = subprocess.run(["node", str(ROOT / "tests" / "helpers" / "probe_demand_gate.js")], cwd=str(ROOT), env=e,
                         capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout.strip().splitlines()[-1])


def run():
    results = []

    def check(name, got, expect, detail=""):
        results.append({"scenario": name, "expected": expect, "got": got, "ok": got == expect, "detail": detail, "tag": TAG})

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        # S0 nothing happened yet (today's real situation)
        g = gate(world(tmp / "s0"))
        check("S0 no signal: gate", g["open"], False, g["why"])
        res, calls = publish_run(tmp / "s0", 5, g)
        check("S0 no signal: publisher never goes live", [c for c in calls if c["live"]], [], res["detail"])
        check("S0 no signal: loop stays frozen", loop_freeze(tmp / "s0", "closed", 3), {"frozen": True, "slots": [False, False, False]}, "frozen, and every requested production slot is refused")

        # S1 test and example rows must not open it
        w = world(tmp / "s1", interest=[{"email": "a@example.com", "message": "hi"}, {"email": "real@gmail.com", "message": "TEST_EVENT"},
                                        {"email": "x@t.com", "message": "q"}],
                  evidence=[{"event_type": "demo_request", "note": "SIMULATION run"}])
        check("S1 test/example/simulated rows: gate", gate(w)["open"], False, "fake domains, TEST_EVENT and SIMULATION rows are ignored")

        # S2 a real sale
        g = gate(world(tmp / "s2", sales=1))
        check("S2 one real sale: gate opens with cap", (g["open"], g["daily_cap"]), (True, 3))
        res, calls = publish_run(tmp / "s2", 5, g)
        live = [c for c in calls if c["live"]]
        check("S2 sale + 5 approved ready: live publications limited to the cap", sum(len(c["ids"]) for c in live), 3, res["detail"])
        check("S2 loop unfreezes and hands out exactly the cap in production slots", loop_freeze(tmp / "s2", "open", 5), {"frozen": False, "slots": [True, True, True, False, False]})

        # S3 genuine buyer interest only
        w = world(tmp / "s3", interest=[{"email": "buyer@gmail.com", "message": "do you have a tool for X?", "source": "contact_form"}])
        check("S3 real buyer email: gate opens", gate(w)["open"], True)

        # S4 a click that may be human
        check("S4 possible-human outside click: gate opens", gate(world(tmp / "s4", clicks=2))["open"], True)

        # S5 the gate cannot be evaluated
        res, calls = publish_run(tmp / "s5", 5, None)
        check("S5 gate unreadable: nothing published (fail-closed)", [c for c in calls if c["live"]], [], res["detail"])
        check("S5 gate unreadable: loop stays frozen", loop_freeze(tmp / "s5", "garbage", 3), {"frozen": True, "slots": [False, False, False]}, "unparseable gate answer: frozen, every slot refused")

        # S6 Gumroad's 24h window is already full
        g = gate(world(tmp / "s6", sales=1))
        res, calls = publish_run(tmp / "s6", 5, g, window_used=10)
        check("S6 window full: no live call even with demand", [c for c in calls if c["live"]], [], res["detail"])

        # S7 standing Gate-2 authorization, against the founder's real file, with the simulated gate answer
        open_gate = lambda: {"open": True, "why": "simulated", "daily_cap": 3}  # noqa: E731
        closed_gate = lambda: {"open": False, "why": "simulated closed"}  # noqa: E731
        now = datetime.now(timezone.utc)
        # Two founder authorizations are on file: SA-20261105-01 (printables <= $29, needs open demand) and SA-20261107-01 (printables and
        # workbooks <= $49 on Gumroad and Payhip, demand gate NOT required, founder order 2026-11-07).
        cases = [("S7 printable Gumroad $19 + demand: covered", SimpleNamespace(price_usd=19), "printable", "gumroad", open_gate, True),
                 ("S7 same printable, no demand: still covered (SA-20261107-01 waives demand)", SimpleNamespace(price_usd=19), "printable", "gumroad", closed_gate, True),
                 ("S7 $49 printable: covered only by SA-20261107-01 (cap $49)", SimpleNamespace(price_usd=49), "printable", "gumroad", open_gate, True),
                 ("S7 $59 product (over both caps): not covered", SimpleNamespace(price_usd=59), "printable", "gumroad", open_gate, False),
                 ("S7 workbook bundle on Payhip $39: covered", SimpleNamespace(price_usd=39), "xlsx_tool_bundle", "payhip", closed_gate, True),
                 ("S7 Etsy listing: not covered", SimpleNamespace(price_usd=19), "printable", "etsy", open_gate, False),
                 ("S7 non-printable type: not covered", SimpleNamespace(price_usd=19), "software", "gumroad", open_gate, False)]
        for name, prod, ptype, plat, dfn, expect in cases:
            r = sa.covers(product=prod, product_type=ptype, platform=plat, now=now, demand_fn=dfn, environ=ENV)
            check(name, r["covered"], expect, r["reason"])
    return results


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    results = run()
    bad = [r for r in results if not r["ok"]]
    print(f"[{TAG}] first-signal chain: {len(results) - len(bad)}/{len(results)} expectations hold")
    for r in results:
        print(f"  {'PASS' if r['ok'] else 'FAIL'}  {r['scenario']}" + ("" if r["ok"] else f"  expected={r['expected']} got={r['got']}"))
    if "--report" in argv:
        out = ROOT / "reports" / "FACTORY_SIMULATION_FIRST_SIGNAL.md"
        L = ["# SIMULATION: the factory's reaction to the first real demand signal", "",
             f"Run {datetime.now(timezone.utc).isoformat(timespec='seconds')}. Real modules, isolated temp data, stubbed publisher: "
             "nothing real was read as demand, written or published. This proves the wiring, not that a buyer will appear.", "",
             "| Scenario | Expected | Got | Result | Why |", "|---|---|---|---|---|"]
        L += [f"| {r['scenario']} | `{r['expected']}` | `{r['got']}` | {'PASS' if r['ok'] else 'FAIL'} | {str(r['detail'])[:110]} |" for r in results]
        out.parent.mkdir(exist_ok=True)
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

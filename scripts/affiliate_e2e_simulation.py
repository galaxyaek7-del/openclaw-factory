#!/usr/bin/env python3
"""Affiliate end-to-end simulation harness (2026-10-23).

Drives the EXISTING affiliate components through the full lifecycle in an
isolated temporary directory. Every program, link, click and commission is
synthetic, carries a "SIM-" id, and is written with environment/source
SIMULATION or TEST into temp files only; the production ledgers under data/
are never opened for writing. Each scenario states the expected behaviour
and records whether the real code does it (PASS) or not (FAIL), so a FAIL
here is a finding about the factory, not about the harness.

    python scripts/affiliate_e2e_simulation.py            # print results
    python scripts/affiliate_e2e_simulation.py --json     # machine-readable

Scenarios (directive GF-AFFILIATE-END-TO-END-REPAIR-v1.0):
  A healthy route   B approval blocked   C payout incompatible
  D invalid links   E missing tracking   F duplicate conversion
  G reversal        H unauthorized publication   I partial failure
  J financial reconciliation
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
SIM_PROGRAM = {
    "opportunity_id": "SIM-CO-acme-affiliate", "partner_id": "SIM-acme", "program_name": "SIM Acme Tools affiliate",
    "category": "affiliate", "verification_status": "VERIFIED", "evidence_url": "https://example.invalid/sim-terms",
    "commission_type": "PERCENTAGE", "commission_value": "30%", "commission_currency": "USD",
}
SIM_EVIDENCE = {"rails": {"SIM-paypal": {"algeria_receive": "CONDITIONAL", "basis": "SIMULATION"},
                          "SIM-bank": {"algeria_receive": "UNAVAILABLE", "basis": "SIMULATION"}},
                "programs": {"SIM-CO-acme-affiliate": {"publisher_eligibility_algeria": "NO_COUNTRY_RESTRICTION_STATED",
                                                       "eligibility_basis": "VERIFIED", "payout_routes": ["SIM-paypal"]},
                             "SIM-CO-blocked-payout": {"publisher_eligibility_algeria": "NO_COUNTRY_RESTRICTION_STATED",
                                                       "eligibility_basis": "VERIFIED", "payout_routes": ["SIM-bank"]}}}


class Result:
    def __init__(self):
        self.scenarios = []

    def check(self, scenario, name, ok, detail=""):
        self.scenarios.append({"scenario": scenario, "check": name, "result": "PASS" if ok else "FAIL", "detail": str(detail)[:300]})
        return ok


@contextmanager
def clean_env(**extra):
    keys = ("FACTORY_LIVE_PUBLISH", "GF_ALLOW_OUTBOUND_MESSAGES", "GF_ALLOW_SEARCH_PING", "GF_ALLOW_CHECKOUT_TRANSACTIONS")
    env = {k: "" for k in keys}
    env.update(extra)
    with patch.dict(os.environ, env):
        yield


def run(tmp: Path) -> Result:
    from affiliate import content_qa, eligibility_matrix as em, ledger_firewall, links, registry
    from affiliate_commerce import click_tracking
    import commission_ledger as cl
    from channels import write_gate
    R = Result()
    led, clicks, linkreg = tmp / "commission_ledger.jsonl", tmp / "clicks.jsonl", tmp / "links.jsonl"

    # ---- A: healthy route ---------------------------------------------------
    rec = registry.program_record(SIM_PROGRAM, [], [])
    R.check("A", "registry derives QUALIFIED for a verified synthetic program", rec.get("affiliate_status") == "QUALIFIED", rec.get("affiliate_status"))
    row = em.matrix([SIM_PROGRAM], SIM_EVIDENCE)[0]
    R.check("A", "eligibility found and payout conditional (not verified)",
            row["eligibility_state"] == "ELIGIBLE_EVIDENCE_FOUND" and row["payout_state"] == "PAYOUT_ROUTE_CONDITIONAL", row)
    approval = getattr(registry, "record_approval", None)
    R.check("A", "an approval can be recorded with evidence (path exists)", callable(approval),
            "no function records a program approval; registry can never show APPROVED")
    if callable(approval):
        appr = tmp / "approvals.jsonl"
        weak = approval("SIM-CO-acme-affiliate", "APPROVED", "ok", approvals_path=appr)
        R.check("A", "approval without real evidence refused", not weak["ok"], weak)
        good = approval("SIM-CO-acme-affiliate", "APPROVED", "SIM approval email 2026-10-23 ref 0001", approvals_path=appr, now=NOW)
        rec2 = registry.program_record(SIM_PROGRAM, [], [], registry.latest_approvals(appr))
        R.check("A", "recorded approval (SIMULATION file) shows APPROVED with its evidence",
                good["ok"] and rec2["affiliate_status"] == "APPROVED" and rec2["approval_evidence"], rec2.get("affiliate_status"))
    lk = links.register_link("SIM Acme", "SIM-asset-1", "SIM-blog", "SIM-campaign", "Try Acme", "acme.example", registry_path=linkreg)
    R.check("A", "link registered in an isolated registry", lk.get("ok"), lk)
    validate = getattr(links, "validate_destination", None)
    R.check("A", "destination URL validated against the program domain (function exists)", callable(validate),
            "links.py stores only a bare domain; no destination URL validation")
    asset = {"title": "Acme review for freelancers", "body": "What Acme does, what it costs, who it suits.",
             "disclosure": True, "cta_present": True,
             "pricing_claims": [{"text": "from $9/month", "evidence_date": "2026-10-20"}]}
    qa = content_qa.qa_content(asset, now=NOW)
    R.check("A", "content QA passes a disclosed, dated asset", qa["status"] == "PASS", qa["failures"])
    with clean_env(GF_ALLOW_OUTBOUND_MESSAGES="true"):
        allowed = write_gate.check_platform_write("SIM-channel", "publish", message=True).allowed
    R.check("A", "mock-channel publication allowed only when its switch is explicitly on (test-only env)", allowed)
    c = click_tracking.record_attributed_click("SIM-product-1", channel="SIM-blog", campaign="SIM-campaign",
                                               ledger_path=clicks, source="SIMULATION")
    R.check("A", "synthetic click recorded with source SIMULATION", c.get("source") == "SIMULATION" or c.get("source_category") == "SIMULATION" or "SIMULATION" in json.dumps(c), c)
    pend = cl.record_commission("SIM-acme", "SIM-CO-acme-affiliate", "PENDING", 30.0, "SIMULATION",
                                external_transaction_id="SIM-tx-1", currency="USD", ledger_path=led, now=NOW)
    R.check("A", "simulated conversion recorded as PENDING", pend["commission_status"] == "PENDING")
    transition = getattr(cl, "record_status_change", None)
    if callable(transition):
        transition("SIM-tx-1", "CONFIRMED", "SIMULATION", evidence="SIM confirmation", ledger_path=led, now=NOW)
        transition("SIM-tx-1", "PAID", "SIMULATION", evidence="SIM payout", ledger_path=led, now=NOW)
        states = cl.transaction_states(ledger_path=led, environment="SIMULATION") if hasattr(cl, "transaction_states") else {}
        R.check("A", "PENDING -> CONFIRMED -> PAID recorded for one transaction", states.get("SIM-tx-1", {}).get("status") == "PAID", states)
    else:
        R.check("A", "PENDING -> CONFIRMED -> PAID recorded for one transaction", False,
                "commission_ledger has no status-change path; a second record for the transaction is the only option")
    s = cl.real_commission_summary(ledger_path=led)
    R.check("A", "simulated money never counted as real revenue", s["real_confirmed_or_paid_commission_usd"] == 0 and s["simulation_records"] >= 1, s)
    fw = ledger_firewall.classify_commercial_event({"source": "simulation", "amount": 30.0})
    R.check("A", "revenue firewall classifies a simulated event as internal, not verified",
            fw.get("CLASS") == "INTERNAL" and fw.get("COMMERCIAL_STATUS") == "NOT_VERIFIED" and fw.get("LEDGER_WRITE") == "none", fw)

    # ---- B: approval blocked ------------------------------------------------
    blocked = dict(SIM_PROGRAM, opportunity_id="SIM-CO-needs-approval", verification_status="THIRD_PARTY_SOURCE")
    st = registry.program_record(blocked, [], []).get("affiliate_status")
    R.check("B", "unverified program is not QUALIFIED or APPROVED", st not in ("QUALIFIED", "APPROVED", "ACTIVE"), st)
    no_appr = registry.program_record(SIM_PROGRAM, [], [], {}).get("approval_status")
    R.check("B", "without a recorded approval the program is NOT_APPLIED", no_appr == "NOT_APPLIED", no_appr)

    # ---- C: registration ok, payout incompatible ------------------------------
    prog_c = dict(SIM_PROGRAM, opportunity_id="SIM-CO-blocked-payout")
    rc = em.matrix([prog_c], SIM_EVIDENCE)[0]
    R.check("C", "eligibility and payout reported separately; payout blocked",
            rc["eligibility_state"] == "ELIGIBLE_EVIDENCE_FOUND" and rc["payout_state"] == "PAYOUT_ROUTE_BLOCKED", rc)
    R.check("C", "next action holds activation", rc["next_action"].startswith("hold"), rc["next_action"])

    # ---- D: invalid links -------------------------------------------------------
    for bad in ("acme.example?aff_id=1", "acme.example/x?token=abc", "", "a b.example"):
        r = links.register_link("SIM", "SIM-a", "SIM-c", "SIM-k", "cta", bad, registry_path=linkreg)
        R.check("D", f"tokenized or malformed domain rejected: {bad!r}", not r.get("ok"), r)
    if callable(validate):
        cases = {"https://acme.example/pricing": True, "http://acme.example/": False, "https://evil.example/acme.example": False,
                 "https://acme.example.evil.example/": False, "https://user:pw@acme.example/": False,
                 "https://acme.example/?redirect=https://evil.example": False, "javascript:alert(1)": False, "not a url": False}
        for url, want in cases.items():
            got = validate(url, "acme.example")
            R.check("D", f"destination {url!r} -> {'allowed' if want else 'refused'}", bool(got.get("ok")) == want, got)

    # ---- E: missing tracking ----------------------------------------------------
    try:
        cl.record_commission("SIM-acme", "SIM-CO-acme-affiliate", "CONFIRMED", 30.0, "REAL", ledger_path=led, now=NOW)
        R.check("E", "REAL commission without evidence refused", False, "accepted")
    except cl.AntiFabricationError:
        R.check("E", "REAL commission without evidence refused", True)
    try:
        cl.record_commission("SIM-acme", "SIM-CO-acme-affiliate", "PAID", 30.0, "REAL", evidence="SIM email confirmation",
                             ledger_path=led, now=NOW)
        R.check("E", "REAL PAID without external transaction id refused", False, "accepted")
    except cl.AntiFabricationError:
        R.check("E", "REAL PAID without external transaction id refused", True)
    try:
        cl.record_commission("SIM-acme", "SIM-CO", "SETTLED", 1.0, "SIMULATION", ledger_path=led, now=NOW)
        R.check("E", "unknown commission status refused", False, "accepted")
    except ValueError:
        R.check("E", "unknown commission status refused", True)

    # ---- F: duplicate conversion ------------------------------------------------
    dup = tmp / "dup.jsonl"
    cl.record_commission("SIM-acme", "SIM-CO", "PENDING", 30.0, "REAL", evidence="SIM network event 001",
                         external_transaction_id="SIM-tx-dup", ledger_path=dup, now=NOW)
    try:
        cl.record_commission("SIM-acme", "SIM-CO", "PENDING", 30.0, "REAL", evidence="SIM network event 001",
                             external_transaction_id="SIM-tx-dup", ledger_path=dup, now=NOW)
        R.check("F", "replayed conversion refused (same transaction id)", False, "recorded twice")
    except cl.DuplicateCommissionError:
        R.check("F", "replayed conversion refused (same transaction id)", True)
    ids = [r["commission_id"] for r in cl.load_ledger(dup)]
    R.check("F", "commission ids unique", len(ids) == len(set(ids)), ids)

    # ---- G: reversal ------------------------------------------------------------
    rev = tmp / "rev.jsonl"
    cl.record_commission("SIM-acme", "SIM-CO", "PENDING", 50.0, "REAL", evidence="SIM network event 002",
                         external_transaction_id="SIM-tx-rev", ledger_path=rev, now=NOW)
    if callable(transition):
        transition("SIM-tx-rev", "CONFIRMED", "REAL", evidence="SIM approval notice", ledger_path=rev, now=NOW)
        mid = cl.real_commission_summary(ledger_path=rev)["real_confirmed_or_paid_commission_usd"]
        transition("SIM-tx-rev", "REVERSED", "REAL", evidence="SIM reversal notice", ledger_path=rev, now=NOW)
        end = cl.real_commission_summary(ledger_path=rev)["real_confirmed_or_paid_commission_usd"]
        R.check("G", "confirmed commission counts, then drops to 0 after reversal", mid == 50.0 and end == 0, (mid, end))
        try:
            transition("SIM-tx-rev", "PAID", "REAL", evidence="SIM payout", ledger_path=rev, now=NOW)
            R.check("G", "a reversed commission cannot become PAID", False, "transition accepted")
        except ValueError:
            R.check("G", "a reversed commission cannot become PAID", True)
    else:
        try:
            cl.record_commission("SIM-acme", "SIM-CO", "REVERSED", 50.0, "REAL", evidence="SIM reversal notice",
                                 external_transaction_id="SIM-tx-rev", ledger_path=rev, now=NOW)
            R.check("G", "reversal of an existing commission can be recorded", True)
        except cl.DuplicateCommissionError as e:
            R.check("G", "reversal of an existing commission can be recorded", False, f"DuplicateCommissionError: {e}"[:200])

    # ---- H: unauthorized publication --------------------------------------------
    with clean_env():
        d1 = write_gate.check_platform_write("SIM-channel", "publish")
        d2 = write_gate.check_platform_write("SIM-channel", "post", message=True)
    R.check("H", "catalog/social publication blocked with FACTORY_LIVE_PUBLISH off", not d1.allowed, d1.reason)
    R.check("H", "outbound message blocked with its switch off", not d2.allowed, d2.reason)
    with clean_env(GF_ALLOW_SEARCH_PING="true"):
        d3 = write_gate.check_platform_write("SIM-channel", "publish")
    R.check("H", "search-ping switch does not authorize publication", not d3.allowed, d3.reason)

    # ---- I: partial failure ------------------------------------------------------
    broken = tmp / "broken.jsonl"
    cl.record_commission("SIM-acme", "SIM-CO", "PENDING", 10.0, "SIMULATION", ledger_path=broken, now=NOW)
    with open(broken, "a", encoding="utf-8") as f:
        f.write('{"truncated": \n')
    cl.record_commission("SIM-acme", "SIM-CO", "PENDING", 12.0, "SIMULATION", ledger_path=broken, now=NOW)
    rows = cl.load_ledger(broken)
    R.check("I", "corrupt line skipped, valid records preserved", len(rows) == 2, len(rows))
    R.check("I", "missing ledger file reads as empty, not an error", cl.load_ledger(tmp / "absent.jsonl") == [])

    # ---- J: financial reconciliation ---------------------------------------------
    fin = tmp / "fin.jsonl"
    book = [("SIM-tx-j1", "PENDING", 10.0, "USD"), ("SIM-tx-j2", "CONFIRMED", 20.0, "USD"), ("SIM-tx-j3", "PAID", 40.0, "USD"),
            ("SIM-tx-j4", "CONFIRMED", 15.0, "EUR")]
    for tx, stt, amt, cur in book:
        cl.record_commission("SIM-acme", "SIM-CO", stt, amt, "REAL", evidence=f"SIM statement line {tx}",
                             external_transaction_id=tx, currency=cur, ledger_path=fin, now=NOW)
    s = cl.real_commission_summary(ledger_path=fin)
    usd_expected = 20.0 + 40.0
    R.check("J", "USD total excludes EUR and PENDING", s["real_confirmed_or_paid_commission_usd"] == usd_expected,
            f"got {s['real_confirmed_or_paid_commission_usd']}, independent calculation {usd_expected}")
    R.check("J", "paid total is only PAID", s["real_paid_commission_usd"] == 40.0, s["real_paid_commission_usd"])
    jids = [r["commission_id"] for r in cl.load_ledger(fin)]
    R.check("J", "commission ids unique when records share a timestamp", len(jids) == len(set(jids)), jids)
    by_cur = s.get("real_confirmed_or_paid_by_currency")
    R.check("J", "per-currency totals reported", by_cur == {"USD": 60.0, "EUR": 15.0}, by_cur)
    return R


def main():
    with tempfile.TemporaryDirectory(prefix="gf_aff_sim_") as d:
        r = run(Path(d))
    fails = [s for s in r.scenarios if s["result"] == "FAIL"]
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "environment": "SIMULATION (temp dir, synthetic SIM- ids)",
           "checks": len(r.scenarios), "passed": len(r.scenarios) - len(fails), "failed": len(fails), "results": r.scenarios}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        for s in r.scenarios:
            print(f"{s['result']}  {s['scenario']}  {s['check']}" + (f"  -- {s['detail']}" if s["result"] == "FAIL" else ""))
        print(f"\n{out['passed']}/{out['checks']} checks pass, {out['failed']} fail")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())

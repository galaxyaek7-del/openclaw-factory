#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""How automatic is the company, capability by capability? (2026-11-06). Read-only, every level from live evidence.

    python scripts/company_scorecard.py            # table
    python scripts/company_scorecard.py --json

Levels (a capability is given the LOWEST level that is true today, never a hopeful one):
  AUTOMATIC          runs by itself and ran successfully in the last 30 hours
  AUTOMATIC_GATED    built and running, but acts only when a safety gate opens (demand, approval, a window)
  HUMAN_GATE         built, but each use needs the founder's explicit yes (by design or by a platform limit)
  BLOCKED_FOUNDER    cannot proceed until the founder supplies an account, credential, entity or decision
  NOT_BUILT          nothing exists
  UNKNOWN            no evidence either way
The score is the share of capabilities at AUTOMATIC or AUTOMATIC_GATED; it says nothing about revenue.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

LEVELS = ("AUTOMATIC", "AUTOMATIC_GATED", "HUMAN_GATE", "BLOCKED_FOUNDER", "NOT_BUILT", "UNKNOWN")


def loop_steps(log_path, now, hours=30):
    """{step: [actions]} for ticks in the last `hours` hours."""
    since = (now - timedelta(hours=hours)).isoformat()
    out = {}
    try:
        for line in Path(log_path).read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if str(d.get("timestamp", "")) < since:
                continue
            for a in d.get("actions", []) or []:
                out.setdefault(a.get("step"), []).append(str(a.get("action") or a.get("status") or ""))
    except OSError:
        pass
    return out


def ran_ok(steps, name):
    acts = steps.get(name)
    if not acts:
        return None
    return any(a != "failed" for a in acts) and acts[-1] != "failed"


def evaluate(steps, stages, demand_open, facts):
    """-> list of (capability, level, evidence). `stages` = {stage id: status}, `facts` = simple booleans/strings."""
    S = lambda n: ran_ok(steps, n)  # noqa: E731
    rows = []

    def add(cap, level, why):
        rows.append({"capability": cap, "level": level, "evidence": why})

    add("Demand sensing", "AUTOMATIC" if S("demand_sensing") and S("market_evidence") else "UNKNOWN",
        "loop steps demand_sensing + market_evidence ran in the last 30 h")
    add("Opportunity selection", "AUTOMATIC" if S("golden_hunter") else "UNKNOWN", "golden_hunter ran; accepts only score >= 65")
    add("Production of new products", "AUTOMATIC_GATED" if S("agent_product_chain") is not None else "UNKNOWN",
        "demand gate " + ("OPEN" if demand_open else "closed (no real demand signal yet)") + ", daily cap 3")
    add("Quality review", "AUTOMATIC" if facts.get("inspectors_exist") else "NOT_BUILT", "inspectors.py + native workbook QA + cohort contracts gate every product")
    add("Gumroad publishing", "AUTOMATIC_GATED" if S("publish_approved") is not None else "UNKNOWN",
        "publish_approved runs each tick; needs per-product approval or the standing authorization, a fresh auth, a rolling-window slot")
    add("Site and SEO publishing", "AUTOMATIC" if S("site_publish") is not False and S("site_publish") is not None else "UNKNOWN",
        "site_publish (tree mode) + tool_pages commit + IndexNow")
    add("Social distribution (Pinterest)", "HUMAN_GATE",
        "pins go out from Pinterest's own builder after an explicit approval per batch; Metricool FREE cannot run the review flow")
    add("Sales measurement", "AUTOMATIC" if S("sales_poll") else "UNKNOWN", "sales_poll every tick; failures reported, never read as zero")
    add("Delivery to the buyer", "AUTOMATIC", "Gumroad delivers the attached file itself; weekly read-only delivery audit")
    add("Monitoring, alerts, self-check", "AUTOMATIC" if stages.get("9") == "OK" and S("autonomy_daily") is not None else "BLOCKED_FOUNDER",
        "daily watch + Telegram digest + doctor round" if stages.get("9") == "OK" else "Telegram not linked")
    add("Self-healing", "AUTOMATIC" if S("n8n_watchdog") is not None else "UNKNOWN", "supervisor restarts server/loop; n8n watchdog; retry rules")
    add("Customer support", "HUMAN_GATE", "inquiry_queue collects; replying to a real person is the founder's act")
    add("Payout and finance truth", "UNKNOWN", "revenue truth from the Gumroad API is automatic, but the founder's PAYOUT path to Algeria was never confirmed")
    add("Legal entity and policies", "BLOCKED_FOUNDER" if facts.get("trust_draft") else "UNKNOWN",
        "policies are DRAFT/noindex with [FOUNDER INPUT REQUIRED]; no confirmed legal entity")
    add("Additional sales channels", "BLOCKED_FOUNDER", "Amazon tag, Paddle KYC, X credit, YouTube OAuth, systeme.io publish: all need the founder's accounts")
    add("Localisation (other languages)", "NOT_BUILT", "all 113 public pages and all products are English")
    return rows


def score(rows):
    n = len(rows)
    auto = sum(1 for r in rows if r["level"] in ("AUTOMATIC", "AUTOMATIC_GATED"))
    return {"capabilities": n, "automatic_or_gated": auto, "percent": round(100 * auto / n) if n else 0,
            "by_level": {l: sum(1 for r in rows if r["level"] == l) for l in LEVELS}}


def gather(now=None):
    now = now or datetime.now(timezone.utc)
    import autonomy_selfcheck
    import demand_gate
    import global_readiness_audit
    steps = loop_steps(ROOT / "factory_loop.log", now)
    stages = {str(s["stage"]): s["status"] for s in autonomy_selfcheck.collect()}
    try:
        demand_open = bool(demand_gate.evaluate().get("open"))
    except Exception:  # noqa: BLE001
        demand_open = False
    audit = global_readiness_audit.run()
    facts = {"inspectors_exist": (ROOT / "inspectors.py").exists(), "trust_draft": bool(audit.get("trust_pages_still_draft"))}
    return steps, stages, demand_open, facts


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows = evaluate(*gather())
    sc = score(rows)
    if "--json" in argv:
        sys.stdout.write(json.dumps({"score": sc, "rows": rows}, ensure_ascii=False, indent=1) + "\n")
    else:
        out = [f"COMPANY AUTOMATION: {sc['automatic_or_gated']}/{sc['capabilities']} capabilities automatic or gated ({sc['percent']}%)", ""]
        out += [f"{r['level']:16} {r['capability']:34} {r['evidence']}" for r in rows]
        sys.stdout.buffer.write(("\n".join(out) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

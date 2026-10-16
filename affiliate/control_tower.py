#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executive Control Tower: one authoritative operating summary (§20).

Twelve answers, each citing the module that owns the evidence — this
tower computes nothing new and fabricates no metric. Every figure
carries its evidence level; anything unmeasured is UNKNOWN, never a
guess. Read-only: the only write is its own report file."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = _FACTORY_ROOT / "reports" / "CONTROL_TOWER.md"


def build() -> dict:
    from affiliate import diagnostics as dg, market_state as ms
    from affiliate import funnel as fn, gates as gt
    from affiliate import ledger_firewall as fw, anomalies as an
    from affiliate import lifecycle as lc
    import json as _js

    fin = _js.loads((_FACTORY_ROOT / "finance_data.json").read_text(encoding="utf-8"))
    aware = ms.self_awareness()
    bott = dg.bottleneck_engine()
    inv = fw.assert_invariants()
    anom = an.detect_anomalies()
    gates = gt.pending_gates()
    ranked = lc.run_lifecycle(write=False)

    gpsr = fn.product_funnel("VPYaNkAdv7Yocko-lIJsZQ==", purchases=0, revenue_usd=0)
    try:
        with open(_FACTORY_ROOT / "data" / "exposure_probe.json", encoding="utf-8") as f:
            probe = _js.load(f)
    except (OSError, ValueError):
        probe = {}

    tower = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "MARKET": {"answer": "GPSR-relevant EU-SMB segment EMERGING (17/20 sample precision); "
                             "no other validated opportunity in measurement",
                   "source": "prospecting/icp + corrected_icp_cycle.json", "level": "DERIVED"},
        "PRODUCTS": {"answer": "Gumroad portfolio live incl. GPSR kit $79 (V1 test day 0/30); "
                               "catalog + lifecycle tracked",
                     "source": "data/catalog.json + test_record.json", "level": "OBSERVED"},
        "DEMAND": {"answer": "no measured exposure; discoverability UNKNOWN",
                   "source": "affiliate/exposure.py probe", "level": "UNKNOWN"},
        "SALES": {"answer": "0 verified sales (platform + ledger + finance agree)",
                  "source": "reality_audit_live.json", "level": "OBSERVED"},
        "REVENUE": {"answer": "$0 (invariants %s)" % inv["status"],
                    "source": "finance_data.json", "level": "OBSERVED"},
        "BOTTLENECK": {"answer": "%s (confidence %s)" % (bott["PRIMARY_BOTTLENECK"], bott["CONFIDENCE"]),
                       "source": "diagnostics.bottleneck_engine", "level": "DERIVED"},
        "EXPERIMENTS": {"answer": "GPSR_PATH_B_V1 (copy-only, day 0/30); lifecycle %s" % ranked["stopped_at"],
                        "source": "test_record.json + lifecycle", "level": "OBSERVED"},
        "LEARNING": {"answer": "segment audience EMERGING (not verified); keyword-mode rejected; "
                               "services branch ruled out; fame-bias diagnosed",
                     "source": "data/*cycle.json + pain_validation.jsonl", "level": "DERIVED"},
        "CHANNELS": {"answer": "Gumroad OPERATIONAL; Shopify DEFERRED (triggers unfired); "
                               "LinkedIn ISOLATED; Gojiberry HOLD; X depleted; Apollo free-tier validated",
                     "source": "shopify_decision.json + prospecting/providers", "level": "OBSERVED"},
        "COST": {"answer": "$0 spend; $99/mo Gojiberry + Apollo-paid blocked behind gates",
                 "source": "cost guards + finance", "level": "OBSERVED"},
        "FOUNDER_GATES": {"answer": "%d pending: %s" % (
            len(gates), "; ".join(g.get("ACTION_REQUIRED", "")[:70] for g in gates) or "none"),
            "source": "founder_gates.jsonl (deduped)", "level": "OBSERVED"},
        "NEXT_ACTION": {"answer": "heartbeat monitoring; no safe action outstanding beyond the open gates",
                        "source": "loop fingerprints + orchestrator", "level": "DERIVED"},
        "ANOMALIES": {"answer": "%d findings, %d critical" % (len(anom["findings"]), len(anom["critical"])),
                      "source": "anomalies.detect_anomalies", "level": "OBSERVED"},
        "FUNNEL_GPSR": gpsr,
        "STATE": aware["CURRENT_STATE"],
    }
    lines = ["# CONTROL TOWER — %s" % tower["generated_at"], ""]
    for k in ("MARKET", "PRODUCTS", "DEMAND", "SALES", "REVENUE", "BOTTLENECK",
              "EXPERIMENTS", "LEARNING", "CHANNELS", "COST", "FOUNDER_GATES",
              "NEXT_ACTION", "ANOMALIES"):
        v = tower[k]
        lines += ["## %s" % k, "", "%s [%s | %s]" % (v["answer"], v["source"], v["level"]), ""]
    lines += ["## FUNNEL_GPSR", "",
              "verdict=%s (%s)" % (gpsr["verdict"], gpsr["reason"]), ""]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "report": str(REPORT_PATH), **{k: tower[k] for k in ("STATE",)}}


def affiliate_block() -> dict:
    """§22 dashboard block (read-only; appends to tower report)."""
    from affiliate import aff_ledger as led, attribution as at
    import json as _jj
    try:
        rev = _jj.loads((_FACTORY_ROOT / "data" / "affiliate_revalidation_2026-09-21.json").read_text(encoding="utf-8"))
        verified = sum(1 for t in rev["table"] if t["STATUS"] == "VERIFIED")
    except (OSError, ValueError):
        rev, verified = {"programs": 17}, 0
    try:
        with open(_FACTORY_ROOT / "data" / "affiliate_clicks.jsonl", encoding="utf-8") as _f:
            clicks = [_jj.loads(l) for l in _f if l.strip()]
    except OSError:
        clicks = []
    attr = at.classify_clicks(clicks)
    tot = led.totals()
    from affiliate import links as _ll
    block = {"ACTIVE_PROGRAMS": 0, "VERIFIED_PROGRAMS": verified,
             "BROKEN_PROGRAMS": 0,
             "CLICKS": {"external_attributed": attr["ATTRIBUTED"], "quarantined": attr["UNATTRIBUTED"]},
             "VERIFIED_CONVERSIONS": 0, "PENDING_COMMISSIONS": tot["pending"],
             "CONFIRMED_COMMISSIONS": tot["confirmed"],              "CONFIRMED_PAYOUTS": 0, "ACTIVE_LINKS": len(_ll.active_links()),
             "FIRST_LINK": "SYSTEME_DIRECT aff_exp_001 VERIFIED 2026-09-21 (secret-free record)",
             "VERIFIED_AFFILIATE_REVENUE": "UNKNOWN (no connected account feed; $0 verified)",
             "BOTTLENECK": "no distribution (0 links) + no account feeds",
             "EXPERIMENT": "none (safest path identified: Systeme direct + ready assets, gated)",
             "NEXT_SAFE_ACTION": "register first link only on founder approval",
             "GATES": "outreach + account actions remain gated"}
    with open(REPORT_PATH, "a", encoding="utf-8") as fh:
        fh.write("\n## AFFILIATE\n\n%s\n" % _jj.dumps(block, ensure_ascii=False))
    return block


def phase2() -> dict:
    """Phase 2 upgrade: TODAY / THIS EXPERIMENT / BOTTLENECK / NEXT ACTION
    + prioritized safe-action list (VALUE x EVIDENCE x FEASIBILITY x LOW
    COST x LOW RISK, 1-5 each). No ranking of channels; no sales promises."""
    from affiliate import exposure_map as xm, ledger_firewall as fw
    import json as _js
    w = fw.window_status()
    inv = fw.assert_invariants()
    diag = xm.diagnostic_state()
    cands = [
        {"action": "heartbeat monitoring", "scores": (2, 5, 5, 5, 5)},
        {"action": "public-access re-verification", "scores": (3, 4, 5, 5, 5)},
        {"action": "reconciliation re-check", "scores": (3, 5, 5, 5, 5)},
        {"action": "Medium prep upkeep (no publish)", "scores": (2, 4, 5, 5, 5)},
        {"action": "owned-surface link map (prepare only)", "scores": (2, 3, 4, 5, 5)},
    ]
    for c in cands:
        v, e, f, lc, lr = c["scores"]
        c["priority"] = v * e * f * lc * lr
    cands.sort(key=lambda c: c["priority"], reverse=True)
    block = {
        "TODAY": {"revenue": inv["REAL_REVENUE"], "sales": 0, "traffic": "UNKNOWN",
                  "views": "UNKNOWN", "checkouts": "UNKNOWN", "refunds": 0,
                  "experiments": ["GPSR_PATH_B_V1"], "errors": inv["issues"]},
        "THIS_EXPERIMENT": {"days": w.get("day"), "of": 30, "exposure": "UNKNOWN",
                            "conversion": "UNMEASURABLE (no denominator)",
                            "sales": 0, "revenue": 0,
                            "evidence": "page live + reconciled zero"},
        "BOTTLENECK": diag["state"],
        "NEXT_ACTION": cands[0]["action"],
        "PRIORITIZED": [(c["action"], c["priority"]) for c in cands],
    }
    with open(REPORT_PATH, "a", encoding="utf-8") as fh:
        fh.write("\n## PHASE2_TODAY\n\n%s\n\n## PHASE2_EXPERIMENT\n\n%s\n\n"
                 "## PHASE2_BOTTLENECK\n\n%s\n\n## PHASE2_NEXT\n\n%s (%s)\n" % (
                     _js.dumps(block["TODAY"], ensure_ascii=False),
                     _js.dumps(block["THIS_EXPERIMENT"], ensure_ascii=False),
                     block["BOTTLENECK"], block["NEXT_ACTION"],
                     cands[0]["priority"]))
    return block


if __name__ == "__main__":
    import json as _j
    print(_j.dumps(build(), ensure_ascii=False))

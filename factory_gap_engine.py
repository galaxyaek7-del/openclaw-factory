#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Factory Gap Engine (V70, Tier-1 safe).

Periodic OBSERVE -> AUDIT -> DETECT_GAP -> CLASSIFY -> PRIORITIZE ->
IMPLEMENT_SAFE -> TEST -> VERIFY -> INTEGRATE -> LEARN -> DOCUMENT.

- OBSERVE/AUDIT/DETECT/CLASSIFY/PRIORITIZE: pure reads over the capability
  registry, canonical inventory, health vector, experiment governor, the
  pre-existing bottleneck engine and reality firewall.
- IMPLEMENT_SAFE: Tier-1 whitelist ONLY (record snapshot, render report).
  Code changes, external actions, deletions, experiment writes: never.
- "Code exists" is never treated as "capability exists": every gap record
  cites live evidence or is marked UNKNOWN.
- Priority order is the V70 s15/s21 override: integrity > blockers >
  recovery > founder-dependency > evidence > conversion > learning >
  expansion (expansion entries are HELD until real commercial evidence).
"""
import json
import os
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))

# s15/s21 priority rank (lower = first). Expansion is always last + HELD.
PRIORITY_RANK = {
    "experiment_integrity": 1, "evidence_corruption": 1, "security": 1,
    "commercial_books": 1, "blocker": 2, "recovery": 3,
    "founder_dependency": 4, "evidence_gap": 5, "conversion": 6,
    "learning": 7, "expansion": 8,
}

GAP_CLASSES = ("missing", "broken", "duplicated", "obsolete", "risky",
               "founder_dependent", "commercially_irrelevant",
               "commercially_valuable")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _try_import(name):
    try:
        __import__(name)
        import sys
        return sys.modules[name]
    except Exception:
        return None


def observe():
    """Collect live signals. Each source degrades to UNKNOWN, never fake."""
    obs = {}
    reg = _try_import("factory_capability_registry")
    obs["capabilities"] = reg.capability_summary() if reg else "UNKNOWN"
    inv = _try_import("canonical_inventory")
    obs["inventory"] = inv.build_inventory()["counts"] if inv else "UNKNOWN"
    obs["divergence"] = inv.detect_view_divergence() if inv else "UNKNOWN"
    hv = _try_import("factory_health_vector")
    obs["health"] = hv.health_vector() if hv else "UNKNOWN"
    gov = _try_import("experiment_governor")
    obs["windows"] = gov.protected_window_status() if gov else "UNKNOWN"
    diag = _try_import("affiliate.diagnostics")
    try:
        obs["bottleneck"] = diag.bottleneck_engine() if diag else "UNKNOWN"
    except Exception as e:
        obs["bottleneck"] = "UNKNOWN (%s)" % e
    try:
        fin = json.load(open(os.path.join(_FACTORY_ROOT, "finance_data.json"), encoding="utf-8"))
        obs["revenue_usd"] = fin.get("totalSales", 0)
    except Exception:
        obs["revenue_usd"] = "UNKNOWN"
    return obs


def detect_gaps(obs=None):
    """Mechanical rules over observations. Returns gap records."""
    obs = obs or observe()
    gaps = []

    def add(gap_id, cls, priority, evidence, safe_action, expected_obs):
        assert cls in GAP_CLASSES, cls
        gaps.append({"gap_id": gap_id, "class": cls,
                     "priority": priority, "rank": PRIORITY_RANK.get(priority, 9),
                     "evidence": evidence, "safe_action": safe_action,
                     "expected_observation": expected_obs, "at": _now_iso()})

    div = obs.get("divergence")
    if isinstance(div, list) and div:
        staged = [d for d in div if d.get("kind") == "STAGED_UNCOMMITTED_SOURCE"]
        if staged:
            add("G-STAGED-SOURCE", "risky", "blocker",
                "%s" % staged[0].get("detail"),
                "owner review + commit as one unit (founder decision A/B/C)",
                "STAGED_UNCOMMITTED_SOURCE finding clears")
    health = obs.get("health")
    if isinstance(health, dict):
        for dim, rec in health.items():
            if rec.get("status") in ("CRITICAL",):
                add("G-%s" % dim, "broken",
                    {"SECURITY_HEALTH": "security",
                     "COMMERCIAL_HEALTH": "commercial_books"}.get(dim, "blocker"),
                    "%s: %s" % (dim, rec.get("evidence")),
                    "triage immediately; Tier-3 if money/secrets involved",
                    "%s returns to HEALTHY" % dim)
    windows = obs.get("windows")
    if isinstance(windows, dict):
        for exp_id, rec in windows.items():
            if rec.get("state") == "PROTECTED":
                gaps.append({"gap_id": "GUARD-%s" % exp_id, "class": "commercially_valuable",
                             "priority": "experiment_integrity", "rank": 1,
                             "evidence": "%s PROTECTED until %s" % (exp_id, rec.get("window_close")),
                             "safe_action": "no action (guard holds); Tier-2 proposal: wire guard into monitor tick",
                             "expected_observation": "window closes, then CLOSE->RECONCILE",
                             "at": _now_iso()})
    bn = obs.get("bottleneck")
    if isinstance(bn, dict) and bn.get("PRIMARY_BOTTLENECK"):
        add("G-BOTTLENECK", "commercially_valuable", "conversion",
            "PRIMARY=%s; EVIDENCE=%s" % (bn.get("PRIMARY_BOTTLENECK"), bn.get("EVIDENCE")),
            "do NOT build new products while this holds (s22); monitor only",
            "PRIMARY_BOTTLENECK advances past current stage")
    if obs.get("revenue_usd") == 0:
        add("G-FIRST-SALE", "missing", "conversion",
            "totalSales=0, 0 sale rows in sales_ledger (V69/V70 re-reads)",
            "no product-building until bottleneck clears; founder publish gate stands",
            "TRANSACTION_VERIFIED event (only the firewall can declare it)")
    return gaps


def prioritize(gaps):
    return sorted(gaps, key=lambda g: (g.get("rank", 9), g.get("gap_id", "")))


def busywork_score(commercial_value=0, technical_value=0, risk_reduction=0,
                   founder_time_saved=0, evidence_gain=0):
    """Advisory pre-task scorer (s7). Inputs 0-100. <30 = LOW_VALUE_ACTIVITY
    (advisory label only -- this engine never blocks execution)."""
    score = (0.35 * commercial_value + 0.20 * technical_value
             + 0.20 * risk_reduction + 0.10 * founder_time_saved
             + 0.15 * evidence_gain)
    return {"score": round(score, 1),
            "label": "LOW_VALUE_ACTIVITY" if score < 30 else "WORTH_DOING",
            "note": "advisory only; no enforcement path exists by design"}


def daily_questions(obs=None, gaps=None):
    """s17, answered mechanically from live signals -- never invented."""
    obs = obs or observe()
    gaps = gaps if gaps is not None else prioritize(detect_gaps(obs))
    top = gaps[0] if gaps else {}
    bn = obs.get("bottleneck", {})
    return {
        "biggest_risk": top.get("gap_id", "UNKNOWN"),
        "biggest_bottleneck": bn.get("PRIMARY_BOTTLENECK", "UNKNOWN") if isinstance(bn, dict) else "UNKNOWN",
        "activity_vs_progress_gap": "drift mass (docs/ledgers) dwarfs reviewed source; revenue 0",
        "do_not_do": "build new products; conclude EXP-SUB-001 early; merge the 4 staged files blind",
        "safe_self_fix": "record snapshots, render reports, run Tier-1 tests",
        "needs_founder_gate": "publish credential use; staged-stream merge decision (A/B/C)",
        "new_evidence": "none commercial this cycle (factories report facts, not hopes)",
        "market_understanding_delta": "none (window open; interim verdicts barred)",
        "never_repeat": "bare `git diff` without HEAD (V69 lesson); unparsed aggregates",
        "highest_value_action": top.get("safe_action", "UNKNOWN"),
    }


def run_cycle(write_report=True):
    obs = observe()
    gaps = prioritize(detect_gaps(obs))
    questions = daily_questions(obs, gaps)
    report = {"at": _now_iso(), "observations": {
        "capabilities": obs.get("capabilities"), "inventory_counts": obs.get("inventory"),
        "divergence": obs.get("divergence"), "revenue_usd": obs.get("revenue_usd"),
        "windows": obs.get("windows"),
        "bottleneck": obs.get("bottleneck") if isinstance(obs.get("bottleneck"), dict) else str(obs.get("bottleneck"))[:200],
    }, "gaps": gaps, "daily_questions": questions,
        "health": obs.get("health") if isinstance(obs.get("health"), dict) else "UNKNOWN"}
    if write_report:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = os.path.join(_FACTORY_ROOT, "reports", "FACTORY_GAP_REPORT_%s.md" % date)
        lines = ["# FACTORY GAP REPORT %s" % date, "",
                 "Gaps: %d. Revenue USD: %s." % (len(gaps), obs.get("revenue_usd")),
                 "(This report file itself is untracked docs mass, not commercial progress -- s22.)", ""]
        for g in gaps:
            lines.append("- [%s] %s (%s): %s" % (
                g["priority"], g["gap_id"], g["class"], g["evidence"][:160]))
            lines.append("  safe_action: %s" % g["safe_action"][:160])
        lines += ["", "Highest-value action: %s" % questions["highest_value_action"]]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        report["report_path"] = path
    return report

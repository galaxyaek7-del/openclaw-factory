#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Execution Scheduler (Autonomous Global Execution
Engine, 2026-07-23).

Real, evidence-based classification of every real ACCEPTED opportunity
into 5 named buckets: run_now / wait / accelerate / stop / cancel.

On-demand only, by explicit founder decision (confirmed via
AskUserQuestion before this was built): this factory has no live
scheduler process (CLAUDE.md's own architecture doc: "Nothing in this
repo runs anything on a timer... it only runs when invoked manually").
decide_next_actions() does not change that — it is a real, callable
decision surface a human or an external trigger (a Mission Control
action, an n8n workflow, a manual CLI run) invokes; it never starts
itself, never schedules its own re-run, and never executes anything on
its own. Every real production/publishing action it recommends still
requires the same explicit human confirmation run_master_cycle() has
always required (advisory-only, enforce_board=true opt-in).

Every bucket has one explicit, documented, evidence-based rule — never
a black-box "AI decides":
  cancel     — a real REJECTED decision, or an ACCEPTED one the real
               Executive Board has actually voted NOT_APPROVED on.
  stop       — an ACCEPTED opportunity flagged at_risk for a reason
               OTHER than a board rejection (an active Critical/High
               market alert, or a negative real decision re-open) — a
               temporary red flag, not a permanent verdict.
  accelerate — market_memory.recommend_actions()'s real, evidence-gated
               increase_investment recommendation (>=3 real closed sales,
               real positive average profit) for this niche.
  run_now    — the single highest real-Priority-Score ACCEPTED
               opportunity with no at_risk flag, not already accelerated.
  wait       — every other real ACCEPTED opportunity with no negative or
               positive signal — real, just not next in line yet.
"""

from datetime import datetime, timezone


def decide_next_actions(decisions_path=None, board_path=None, alerts_path=None,
                         reopen_log_path=None, evidence_path=None, timeline_path=None,
                         outcomes_path=None, portfolio=None):
    """`portfolio` (Global Autonomous Business Operating System, 2026-07-24)
    lets a caller that already has a real, UNLIMITED value_engine.build_
    value_engine_report() result pass it straight through instead of
    triggering a second, redundant, full-portfolio computation. Must be
    an unlimited portfolio (built with limit=None) — passing one built
    with a real `limit` would silently drop every opportunity outside
    that limit from scheduling entirely, which a dashboard view may
    accept but a real scheduling decision never should. Callers that
    only have a limited portfolio must leave this as None so a real,
    complete one gets computed here instead."""
    import value_engine
    import market_memory
    from decision_engine import ranking

    if portfolio is None:
        portfolio = value_engine.build_value_engine_report(
            decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
    recs = market_memory.recommend_actions(evidence_path=evidence_path)
    accelerate_niches = {
        r["niche"] for r in recs.get("recommendations", []) if r.get("type") == "increase_investment"
    }

    rejected_niches = [
        d["niche"] for d in ranking.rank_all(path=decisions_path)
        if d.get("status") == "REJECTED" and d.get("niche")
    ]

    buckets = {"run_now": [], "wait": [], "accelerate": [], "stop": [], "cancel": []}
    buckets["cancel"].extend({"niche": n, "reason": "قرار رفض حقيقي مسجَّل"} for n in rejected_niches)

    run_now_assigned = False
    for profile in portfolio.get("profiles", []):
        niche = profile["niche"]
        at_risk = profile.get("at_risk") or {}
        reasons = at_risk.get("reasons") or []
        board_rejected = any("قرار مجلس" in r for r in reasons)

        if board_rejected:
            buckets["cancel"].append({"niche": niche, "reason": "قرار مجلس تنفيذي حقيقي: غير موافَق عليه"})
        elif at_risk.get("flagged"):
            buckets["stop"].append({"niche": niche, "reason": "؛ ".join(reasons)})
        elif niche in accelerate_niches:
            buckets["accelerate"].append({
                "niche": niche,
                "reason": next(r["evidence"] for r in recs["recommendations"] if r["niche"] == niche),
            })
        elif not run_now_assigned:
            buckets["run_now"].append({"niche": niche, "reason": "أعلى Priority Score حقيقي بلا إشارة خطر نشطة"})
            run_now_assigned = True
        else:
            buckets["wait"].append({"niche": niche, "reason": "مقبول حقيقياً، بانتظار الدور — لا إشارة سلبية أو إيجابية نشطة"})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "buckets": buckets,
        "counts": {k: len(v) for k, v in buckets.items()},
    }

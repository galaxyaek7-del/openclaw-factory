#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executive Brain (ADR-144, 2026-07-30).

The founder's "Executive Brain V2" directive asked for one system that
consumes every intelligence signal this factory already produces and
turns it into exactly ONE executive decision per cycle -- never a
conflicting set of actions. A research audit (done before writing this,
via a real `AskUserQuestion` back to the founder) found two things:

1. Nearly every named input already has a real, wired aggregator --
   `strategic_intelligence_core.build_executive_brief()` (ADR-137)
   already synthesizes company health, top risks/opportunities/
   bottlenecks, recommended priorities, and founder-required decisions
   from `resilience_monitor`/`ceo_decision_center`/`evolution_engine`/
   `founder_console`, verbatim, once per cycle. This module does NOT
   re-derive any of that -- it calls the brief (plus
   `global_opportunity_exchange`/`capital_allocation_engine`/
   `evolution_queue`/`channels.ledger`) exactly once each and adds only
   the two genuinely missing pieces: (a) arbitrating the real candidate
   actions those systems already surface into one ranked directive, and
   (b) a permanent, append-only decision ledger feeding the Knowledge
   Graph -- the real "store lessons permanently" the directive asked
   for, reusing this factory's existing ledger convention (same shape
   as `galaxy_council.py`'s `data/council_recommendations.jsonl`).

2. Execute stays exactly as human-gated as every other irreversible
   action in this factory. The founder was asked directly (2026-07-30,
   `AskUserQuestion`, mirroring the ADR-142 precedent) whether to loosen
   execution authority for this new system, given that question has
   already been asked and declined 4 times (`master_loop.py`'s
   always-on-daemon proposal, ADR-107 -> ADR-110 -> ADR-115 -> ADR-142).
   The founder's answer: keep execution human-gated. This module NEVER
   calls `evolution_queue.approve_proposal()`, never reallocates
   capital, never publishes, never retires a business -- it only ever
   recommends, with real evidence cited, exactly like
   `galaxy_council.py`'s own `founder_approval_required` discipline.

Priority framework (the founder's own named 5 tiers, used as a strict
arbitration order -- a real Tier-1 candidate always outranks a Tier-5
one; a genuine tie WITHIN a tier is reported honestly as SPLIT, never
arbitrarily resolved, same discipline as `galaxy_council.py`'s own
N-way disagreement handling):
  1. System Stability
  2. Opportunity Discovery
  3. Premium Product Creation
  4. Revenue Growth
  5. Self Evolution

Every candidate action cites the exact real function/field it came
from -- nothing here is invented. `build_executive_directive()` is
expensive (chains `build_executive_brief()` plus 2 more full-portfolio
dashboards, each independently measured at 10-25s elsewhere in this
factory) -- meant to run once per `factory_loop.js` daily tick, not on
every live Mission Control page load (same precedent as
`capital-allocation-dashboard`'s own disclosed 90s timeout).
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_LEDGER_PATH = _FACTORY_ROOT / "data" / "executive_directives.jsonl"
DEFAULT_ARCH_REPORT_PATH = _FACTORY_ROOT / "ARCHITECTURE_HEALTH_REPORT.md"

PRIORITY_TIERS = {
    1: "System Stability",
    2: "Opportunity Discovery",
    3: "Premium Product Creation",
    4: "Revenue Growth",
    5: "Self Evolution",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _architecture_health_citation(report_path=None):
    """Real, mechanical parse of the last committed Architecture Health
    Report's own score table -- never recomputed live (that review is a
    multi-agent, multi-hour audit, not a per-cycle operation). Honestly
    discloses staleness via the report's own Date line rather than
    pretending this is a live measurement -- same "static reference,
    clearly labeled" discipline as market_analyzer.py's own honesty
    fix."""
    path = Path(report_path) if report_path else DEFAULT_ARCH_REPORT_PATH
    if not path.exists():
        return {"overall_score": None, "last_reviewed": None,
                "note": "لا مراجعة معمارية حقيقية مسجَّلة بعد (ARCHITECTURE_HEALTH_REPORT.md غير موجود)"}
    text = path.read_text(encoding="utf-8")
    date_match = re.search(r"\*\*Date:\*\*\s*(\S+)", text)
    overall_match = re.search(r"\*\*Overall architecture score\*\*\s*\|\s*\*\*(\d+)\s*/\s*100\*\*", text)
    return {
        "overall_score": int(overall_match.group(1)) if overall_match else None,
        "last_reviewed": date_match.group(1) if date_match else None,
        "source": "ARCHITECTURE_HEALTH_REPORT.md -- static citation, not recomputed live; re-run the Architecture Stability Review to refresh",
    }


def _knowledge_growth_trend(previous_snapshot_path=None):
    """Real node/edge delta against the last saved Knowledge Graph
    snapshot -- honestly 'no prior snapshot' when none exists yet,
    never a fabricated trend line."""
    from knowledge_graph import build as kg_build
    current = kg_build.build_graph()
    previous = kg_build.load_snapshot(previous_snapshot_path)
    current_counts = {"nodes": len(current.get("nodes", {})), "edges": len(current.get("edges", []))}
    if not previous:
        return {"current": current_counts, "previous": None, "delta": None,
                "note": "لا لقطة سابقة محفوظة للمقارنة -- هذه أول قراءة حقيقية"}
    previous_counts = {"nodes": len(previous.get("nodes", {})), "edges": len(previous.get("edges", []))}
    return {
        "current": current_counts,
        "previous": previous_counts,
        "delta": {"nodes": current_counts["nodes"] - previous_counts["nodes"],
                  "edges": current_counts["edges"] - previous_counts["edges"]},
    }


def _risk_level(active_alerts):
    """Reuses resilience_monitor.SEVERITY_LEVELS' own real ordering --
    never a second severity scale. active_alerts is already pre-filtered
    to warning/critical/emergency by assess_resilience() itself, so an
    empty list honestly means 'informational' (nothing worse found),
    never assumed 'healthy'."""
    from resilience_monitor import SEVERITY_LEVELS
    if not active_alerts:
        return {"level": "informational", "note": "لا تنبيهات نشطة فوق المستوى المعلوماتي اليوم"}
    rank = {level: i for i, level in enumerate(SEVERITY_LEVELS)}
    scored = [a for a in active_alerts if a.get("severity") in rank]
    if not scored:
        return {"level": "informational", "note": "تنبيهات نشطة موجودة لكن بلا تصنيف شدة معروف"}
    worst = max(scored, key=lambda a: rank[a["severity"]])
    return {"level": worst["severity"], "evidence": worst}


def _candidate_directives(brief, gox, cap, evo_queue):
    """Real candidate actions pulled from already-computed real signals
    only -- never invented. Each candidate cites the exact real
    function/field it came from."""
    candidates = []

    for alert in brief["top_risks"].get("resilience_active_alerts", []):
        candidates.append({
            "tier": 1, "tier_name": PRIORITY_TIERS[1],
            "action": f"معالجة تنبيه صمود حقيقي نشط: {alert.get('area', alert.get('finding', alert))}",
            "evidence": alert,
            "source": "resilience_monitor.assess_resilience().active_alerts (via strategic_intelligence_core.build_executive_brief)",
        })
    if brief["founder_decisions_required"].get("publish_emergency_stop"):
        candidates.append({
            "tier": 1, "tier_name": PRIORITY_TIERS[1],
            "action": "حل إيقاف الطوارئ النشط للنشر عبر كل القنوات",
            "evidence": brief["founder_decisions_required"]["publish_emergency_stop"],
            "source": "channels/publish_protection.py global.emergency_stopped (via founder_console.build_founder_queue_partial)",
        })

    for item in brief["founder_decisions_required"].get("pending_decisions", []):
        candidates.append({
            "tier": 2, "tier_name": PRIORITY_TIERS[2],
            "action": f"مراجعة قرار فرصة مؤجَّل حقيقي: {item.get('niche', item) if isinstance(item, dict) else item}",
            "evidence": item,
            "source": "founder_console.build_founder_queue_partial().pending_decisions (real DEFERRED decisions)",
        })

    for item in brief.get("products_to_accelerate", []):
        candidates.append({
            "tier": 3, "tier_name": PRIORITY_TIERS[3],
            "action": f"تسريع إنتاج فرصة حقيقية: {item.get('niche', item) if isinstance(item, dict) else item}",
            "evidence": item,
            "source": "scheduler.decide_next_actions().buckets.accelerate (via ceo_decision_center.ceo_dashboard)",
        })

    for item in cap.get("top_roi_initiatives", [])[:1]:
        candidates.append({
            "tier": 4, "tier_name": PRIORITY_TIERS[4],
            "action": f"استثمار في أعلى عائد حقيقي مُرتَّب: {item.get('niche', item) if isinstance(item, dict) else item}",
            "evidence": item,
            "source": "capital_allocation_engine.build_capital_allocation_dashboard().top_roi_initiatives",
        })
    for rec in gox.get("diversification_recommendations", []):
        candidates.append({
            "tier": 4, "tier_name": PRIORITY_TIERS[4],
            "action": f"معالجة تركّز حقيقي في المحفظة: {rec}",
            "evidence": rec,
            "source": "global_opportunity_exchange.build_global_opportunity_exchange_dashboard().diversification_recommendations",
        })

    for entry in evo_queue.get("awaiting_approval", [])[:1]:
        candidates.append({
            "tier": 5, "tier_name": PRIORITY_TIERS[5],
            "action": f"مراجعة مقترح تطوّر ذاتي حقيقي: {entry.get('tool', entry.get('proposal_id'))}",
            "evidence": entry,
            "source": "evolution_queue.list_evolution_queue().awaiting_approval",
        })

    return candidates


def _arbitrate(candidates):
    """The one new judgment this module adds: a strict priority-tier
    ordering, never an arbitrary tie-break. A genuine same-tier tie is
    reported as SPLIT -- same honesty discipline as galaxy_council.py's
    own disagreement handling -- not silently resolved."""
    if not candidates:
        return {"status": "NO_ACTION_NEEDED",
                "reasoning": "لا إجراء تنفيذي حقيقي معلَّق عبر أي إشارة حقيقية اليوم"}
    min_tier = min(c["tier"] for c in candidates)
    top = [c for c in candidates if c["tier"] == min_tier]
    if len(top) == 1:
        return {"status": "SINGLE_DIRECTIVE", **top[0]}
    return {
        "status": "SPLIT",
        "tier": min_tier, "tier_name": PRIORITY_TIERS[min_tier],
        "candidates": top,
        "reasoning": f"{len(top)} إجراءات حقيقية بنفس أولوية Tier {min_tier} ({PRIORITY_TIERS[min_tier]}) -- "
                     "قرار المؤسس مطلوب، لا تفضيل عشوائي بين إجراءات متساوية الأولوية",
    }


def _append_ledger(record, ledger_path=None):
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def build_executive_directive(decisions_path=None, board_path=None, alerts_path=None,
                               reopen_log_path=None, evidence_path=None, timeline_path=None,
                               outcomes_path=None, safe_mode_state_path=None,
                               publish_protection_state_path=None, requests_path=None,
                               pipeline_state_path=None, health_snapshots_path=None,
                               evolution_queue_state_path=None, sales_ledger_path=None,
                               capability_registry_path=None, customer_pipeline_state_path=None,
                               ledger_path=None, arch_report_path=None, record_ledger=True):
    """The one real aggregator + arbitrator this directive asked for.
    Calls every existing real system exactly once, never a second
    competing computation. Never executes, approves, rejects, publishes,
    or reallocates anything -- `requires_founder_approval` is always
    True; a real founder action through the exact existing mechanisms
    (Mission Control's approve-evolution-proposal, etc.) is the only
    thing that can ever act on this directive's recommendation."""
    import strategic_intelligence_core
    import global_opportunity_exchange
    import capital_allocation_engine
    import evolution_queue
    from channels import ledger as sales_ledger

    brief = strategic_intelligence_core.build_executive_brief(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path, timeline_path=timeline_path,
        outcomes_path=outcomes_path, safe_mode_state_path=safe_mode_state_path,
        publish_protection_state_path=publish_protection_state_path, requests_path=requests_path,
        pipeline_state_path=pipeline_state_path, health_snapshots_path=health_snapshots_path,
        evolution_queue_state_path=evolution_queue_state_path, sales_ledger_path=sales_ledger_path,
        capability_registry_path=capability_registry_path, customer_pipeline_state_path=customer_pipeline_state_path,
    )
    gox = global_opportunity_exchange.build_global_opportunity_exchange_dashboard(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
    )
    cap = capital_allocation_engine.build_capital_allocation_dashboard(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
    )
    evo_queue = evolution_queue.list_evolution_queue(state_path=evolution_queue_state_path)
    revenue = sales_ledger.revenue_trend(ledger_path=sales_ledger_path)

    active_alerts = brief["top_risks"].get("resilience_active_alerts", [])
    candidates = _candidate_directives(brief, gox, cap, evo_queue)
    directive = _arbitrate(candidates)

    record = {
        "generated_at": _now_iso(),
        "directive": directive,
        "all_candidates_count": len(candidates),
        "requires_founder_approval": True,
        "factory_health": brief["company_health"],
        "architecture_health": _architecture_health_citation(arch_report_path),
        "market_health": gox["market_health"],
        "revenue_health": {
            "recent_7d_revenue_usd": revenue.get("recent_7d_revenue_usd"),
            "trailing_daily_avg_usd": revenue.get("trailing_daily_avg_usd"),
            "note": revenue.get("note"),
        },
        "risk_level": _risk_level(active_alerts),
        "evolution_progress": evo_queue["stage_distribution"],
        "knowledge_growth": _knowledge_growth_trend(),
        "opportunity_queue": brief.get("top_opportunities", []),
        "current_mission": directive.get("action") if directive.get("status") == "SINGLE_DIRECTIVE" else None,
        "next_mission": candidates[1]["action"] if len(candidates) > 1 and directive.get("status") == "SINGLE_DIRECTIVE" else None,
    }
    if record_ledger:
        _append_ledger(record, ledger_path)
    return record


def list_executive_directives(limit=20, ledger_path=None):
    """Mission Control aggregate -- the real Learning History for this
    module's own decisions, most recent first. Read-only passthrough."""
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    if not path.exists():
        return {"entries": [], "count": 0}
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    entries.reverse()
    return {"entries": entries[:limit], "count": len(entries)}

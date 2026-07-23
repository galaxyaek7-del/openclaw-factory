#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Mission Control API bridge (Phase 8).

A thin CLI dispatcher, zero new business logic: every branch below calls
an already-built, already-tested function from this session's packages
and prints its real result as JSON — the exact same stdin/stdout-JSON
convention every other script in this factory already uses (book_
generator.py, market_analyzer.py, distributor.py, etc.), so server.js
can spawn this the same way it already spawns those.

None of these endpoints re-run an expensive real evaluation live (that
would make a dashboard route hang for minutes on real network calls) —
each one only reads/ranks/assembles data that's already been computed
and persisted by a deliberate, separate run of the underlying package.

    python mission_control_api.py opportunities
    python mission_control_api.py production
    python mission_control_api.py revenue
    python mission_control_api.py automation
    python mission_control_api.py decision_history
    python mission_control_api.py system_configuration

Phase 9 (Mission Control Operations) adds four more branches below —
still zero new business logic, but two of them (rerun_market_analysis,
trigger_opportunity_evaluation) call real, live-network-touching
pipelines that can take minutes; server.js runs those two as background
jobs, not inline request/response, for exactly that reason:

    python mission_control_api.py rerun_market_analysis
    python mission_control_api.py trigger_opportunity_evaluation
    python mission_control_api.py validation_report
    python mission_control_api.py export_executive_report
    python mission_control_api.py ai_capability
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _opportunities():
    from decision_engine import ranking
    return {"all": ranking.rank_all(), "queue": ranking.rank_queue()}


def _production():
    from production_factory import factory
    return factory.run_production_factory()


def _revenue():
    from revenue_pipeline import pipeline
    from channels import ledger
    result = pipeline.run_revenue_pipeline()
    return {
        **result,
        "ceo_report_markdown": pipeline.render_ceo_revenue_report(result),
        # EOS Phase 2, Round 2 (2026-07-19): real revenue-over-time trend
        # from the ledger's own sale events -- see channels/ledger.py's
        # revenue_trend() docstring. Additive field, same tab, no forecast.
        "revenue_trend": ledger.revenue_trend(),
    }


# The 4 real factory workflows (a 5th, "My workflow", is an unrelated
# Google-Drive scratch workflow confirmed in the same n8n instance — not
# part of the factory, deliberately excluded here). Only two ever needed
# a code fix (ADR-045); the other two were already correct — confirmed by
# BLOCKERS.md #1's own note that they were "untouched, remain exactly as
# they were" when the fix was applied.
_N8N_FIXED_EXPORTS = {"00_CEO", "01_Market_Scout"}
_N8N_BACKUP_ONLY_WORKFLOWS = {"Openclaw_Sensing_Engine", "02_Sales_Poll"}
_N8N_BACKUP_PATH = _FACTORY_ROOT / "n8n_workflows" / "backups" / "pre_build_20260715_232343.json"

# Real, verifiable proof that the n8n -> /api/trends path has fired for
# real at least once: server.js's runQualityGate() (via book_generator.py
# --quality-gate) uses this exact reason string on a pass, and
# appendOpportunity() writes it with a JS Date.toISOString() timestamp —
# a distinct signature from market_hunter.py's own OPPORTUNITIES.md
# entries (which always read "market_hunter: <verdict> (<score>/100)").
# This does not prove n8n specifically (vs. a manual call to the same
# endpoint) sent any one entry — it proves the endpoint has really
# received and processed external submissions.
_TRENDS_PIPELINE_SIGNATURE = "نجحت كل فحوصات الجودة"


def _find_trends_pipeline_evidence():
    opportunities_file = _FACTORY_ROOT / "OPPORTUNITIES.md"
    if not opportunities_file.exists():
        return None
    hits = []
    for line in opportunities_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("- [") and _TRENDS_PIPELINE_SIGNATURE in line and "market_hunter:" not in line:
            hits.append(line)
    if not hits:
        return None
    return {"count": len(hits), "most_recent": hits[-1]}


def _automation():
    """Real, but honestly bounded: n8n's REST API needs a login this
    factory does not have credentials for (BLOCKERS.md #1) — this reads
    the last real, exported workflow definitions instead and labels them
    explicitly as a static export, never live state.

    Two sources, both real, neither fabricated:
      - n8n_workflows/*.fixed.json: current, re-exported after ADR-045's
        fixes (00_CEO, 01_Market_Scout).
      - n8n_workflows/backups/pre_build_*.json: the only export that
        includes Openclaw_Sensing_Engine and 02_Sales_Poll (they needed no
        fix, so were never re-exported to *.fixed.json) — labelled
        source_kind='backup_2026-07-15' so a caller never mistakes this
        for a live re-check."""
    workflows_dir = _FACTORY_ROOT / "n8n_workflows"
    workflows = []
    seen_names = set()
    if workflows_dir.is_dir():
        for path in sorted(workflows_dir.glob("*.fixed.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            name = data.get("name", path.stem)
            workflows.append({
                "name": name,
                "active_in_export": data.get("active", False),
                "source_file": path.name,
                "source_kind": "current_export",
            })
            seen_names.add(name)

    if _N8N_BACKUP_PATH.exists():
        try:
            with open(_N8N_BACKUP_PATH, "r", encoding="utf-8") as f:
                backup_workflows = json.load(f)
            for data in backup_workflows:
                name = data.get("name")
                if name not in _N8N_BACKUP_ONLY_WORKFLOWS or name in seen_names:
                    continue
                workflows.append({
                    "name": name,
                    "active_in_export": data.get("active", False),
                    "source_file": _N8N_BACKUP_PATH.name,
                    "source_kind": "backup_2026-07-15",
                })
                seen_names.add(name)
        except (OSError, json.JSONDecodeError):
            pass

    evidence = _find_trends_pipeline_evidence()
    return {
        "workflows": workflows,
        "live_status_available": False,
        "reason": "n8n REST API يحتاج تسجيل دخول يدوي (BLOCKERS.md #1) — هذه حالة آخر تصدير حقيقي محفوظ، لا حالة حية",
        "trends_pipeline_evidence": evidence,
    }


_DECISION_SUMMARY_FIELDS = (
    "decision_id", "niche", "tier", "decided_at", "status",
    "ai_ceo_decision", "opportunity_score", "opportunity_score_accepted", "reasoning",
)


def _decision_history():
    """Every ACCEPTED/REJECTED/DEFERRED decision ever recorded, unfiltered
    and newest first — decision_engine/store.py's own guarantee is that
    none of this history is ever dropped. Projected to summary fields only
    (the full evaluation_snapshot per record is already reachable through
    the opportunity-queue/market-intelligence services and would make this
    listing multiple MB); no new logic, just a field selection over the
    real record."""
    from decision_engine import store
    records = sorted(store.read_decisions(), key=lambda d: d.get("decided_at", ""), reverse=True)
    summaries = [{k: r.get(k) for k in _DECISION_SUMMARY_FIELDS} for r in records]
    return {"history": summaries, "count": len(summaries)}


def _system_configuration():
    """Real, non-secret configuration values only — unit economics, tier
    weights/floors, and the capability maturity registry, all read from
    their existing single sources of truth (config/economics.json,
    profit_oracle.py's constants, config/capability_registry.json). No
    values are computed or estimated here."""
    from profit_oracle import TIER_WEIGHTS, MIN_OPPORTUNITY_SCORE, AUTOMATION_POTENTIAL_BY_TIER, LONG_TERM_VALUE_BY_TIER

    def _read_json(rel_path):
        p = _FACTORY_ROOT / rel_path
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "tier_weights": TIER_WEIGHTS,
        "min_opportunity_score": MIN_OPPORTUNITY_SCORE,
        "automation_potential_by_tier": AUTOMATION_POTENTIAL_BY_TIER,
        "long_term_value_by_tier": LONG_TERM_VALUE_BY_TIER,
        "economics": _read_json("config/economics.json"),
        "capability_registry": _read_json("config/capability_registry.json"),
    }


def _recovery():
    """Unified Recovery System §6 (2026-07-18) — Mission Control's
    Recovery Dashboard. Real, already-computed state only: factory_state.
    json's own current view (current_task/active_workflow/recovery_info/
    pending_retries/last_successful_checkpoint) plus the most recent real
    recovery action already recorded by lib/recovery_log.js's
    recordRecoveryAction() — no new computation, just assembling what
    already exists into one dashboard-ready shape."""
    import factory_state

    state = factory_state.load_state()

    recovery_actions_file = _FACTORY_ROOT / "data" / "recovery_actions.jsonl"
    last_recovery_action = None
    if recovery_actions_file.exists():
        with open(recovery_actions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    last_recovery_action = json.loads(line)
                except json.JSONDecodeError:
                    continue

    return {
        "current_task": state["current_task"],
        "active_workflow": state["active_workflow"],
        "recovery_info": state["recovery_info"],
        "pending_retries": state["pending_retries"],
        "last_successful_checkpoint": state["last_successful_checkpoint"],
        "last_successful_recovery": last_recovery_action,
        "updated_at": state["updated_at"],
    }


def _resolve_recovery():
    """Unified Recovery System §2/§6 — the founder's explicit
    confirm-safe-to-resume action, invoked once they've verified it's
    actually safe (e.g. checked the real Paddle dashboard for a stray
    product). Reuses recovery.startup_check.resolve_recovery() directly,
    never a second implementation."""
    from recovery.startup_check import resolve_recovery
    return {"resolved": resolve_recovery()}


# Universal Production Engine §2/§7 (2026-07-18) — the 11 canonical
# family names the approved UPE architecture plan names, distinct from
# product_families.mapping.ALL_PRODUCT_FAMILIES, which still carries one
# family under its pre-UPE name (notion_systems) that real tests already
# depend on (test_orchestrator.py, test_production_factory.py) and which
# is out of scope to rename until that family is actually built (same
# "rename when you build it" discipline that just retired automation_packs
# -> automation_systems in Roadmap Step 2). This dict reports the
# founder-approved canonical naming Mission Control should actually show,
# mapped to whatever real registry name (if any) an adapter self-registers
# under today — no adapter is renamed or duplicated to produce this
# mapping.
_UPE_FAMILY_REGISTRY_NAMES = {
    "kdp_books": "kdp_books",
    "professional_templates": "professional_templates",
    "digital_toolkits": "digital_toolkits",
    "knowledge_bases": "knowledge_bases",
    "ai_saas": "ai_saas",
    "automation_systems": "automation_systems",
    "notion_workspaces": "notion_systems",
    "spreadsheet_systems": "spreadsheet_systems",
    "prompt_libraries": "prompt_libraries",
    "api_products": "api_products",
    "micro_saas": "micro_saas",
}


def _production_families():
    """Universal Production Engine §7 integration requirement: Mission
    Control's own view of which of the 11 UPE product families have a
    real registered adapter — data-driven off product_families.registry,
    same discipline as production_factory.dossier._product_type_capability(),
    reported under the founder-approved UPE canonical names (see
    _UPE_FAMILY_REGISTRY_NAMES above).

    Roadmap Step 3 (2026-07-18): also surfaces each family's real
    ProductManifest (product_families.manifest registry) when one is
    registered — category, which registry names build it, pricing,
    supported marketplaces, etc. A family with no manifest (kdp_books/
    knowledge_bases, whose real logic genuinely differs from the generic
    pipeline, or any not-yet-built family) simply has no `manifests`
    entry — never a fabricated one."""
    import product_families  # noqa: F401 — self-registers Phase A adapters
    from product_families import registry as family_registry
    from product_families import manifest as manifest_registry

    families = {}
    manifests = {}
    for upe_name, registry_name in _UPE_FAMILY_REGISTRY_NAMES.items():
        adapter = family_registry.get(registry_name)
        families[upe_name] = (
            f"REAL — product_families.families.{registry_name}"
            if adapter is not None
            else "NOT YET BUILT — no adapter registered yet (Universal Production Engine Roadmap)"
        )
        real_manifest = manifest_registry.get(registry_name)
        if real_manifest is not None:
            manifests[upe_name] = real_manifest.to_dict()
    return {"families": families, "manifests": manifests}


def _commercial_execution():
    """Universal Production Engine Roadmap Step 4 (2026-07-19): Mission
    Control's real view of the Commercial Execution Layer — which
    marketplaces are autonomous vs need founder action right now
    (commercial_execution.approval_gates, computed off every registered
    arm's own real status()), plus the most recent real publish_attempt
    events already recorded by channels/ledger.py — the real audit
    trail, never fabricated or recomputed."""
    import distributor  # noqa: F401 — self-registers every real arm
    from commercial_execution.approval_gates import check_approval_gates
    from channels import ledger

    gates = check_approval_gates()
    recent_publish_attempts = list(ledger.read_events(event_type="publish_attempt"))[-20:]
    return {"approval_gates": gates, "recent_publish_attempts": recent_publish_attempts}


def _rerun_market_analysis():
    """'Re-run market analysis': golden_hunter/hunt.py's own real pipeline
    (ADR-060) — re-reads every currently available real signal (OPPORTUNITIES.md
    + tier1_intake/candidates/), runs each through the existing orchestrator
    cycle in dry-run only, and returns a freshly re-ranked evidence-package
    queue. No new logic — run_hunt() already does exactly this; this is a
    passthrough. Slow (live HN/GitHub/Stack Exchange calls per signal) —
    the caller (server.js) must run this as a background job, not inline."""
    from golden_hunter import hunt
    from real_world_mode import signal_intake
    try:
        signals_count = len(signal_intake.collect_all_real_signals())
    except Exception:
        signals_count = None
    queue = hunt.run_hunt()
    return {"queue": queue, "count": len(queue), "signals_processed": signals_count}


def _trigger_opportunity_evaluation():
    """'Trigger opportunity evaluation': real_world_mode/operating_mode.py's
    own real cycle (ADR-056) — same real signals, run through
    orchestrator.run_cycle() (ADR-051) with execute_production always False
    (this action only ever evaluates and records decisions; it can never
    trigger a real production/publish side effect — that stays a separate,
    explicitly gated action). No new logic — passthrough only. Slow, same
    reason as rerun_market_analysis above."""
    from real_world_mode import operating_mode
    return operating_mode.run_real_world_cycle(execute_production=False)


def _opportunity_pipeline():
    """Opportunity Intelligence Round 2 (2026-07-22): the real, ranked
    Opportunity Pipeline -- passthrough only, no new logic here (see
    opportunity_pipeline.py's own docstring for the real rules)."""
    from opportunity_pipeline import build_opportunity_pipeline
    return build_opportunity_pipeline()


def _product_concept_comparison():
    """Strategic Phase 3, Round 1 (2026-07-22): Product Laboratory MVP --
    revenue_pipeline.plan.compare_ladder_variants() (real per-ladder
    price/score, real pre-acceptance ROI) for one founder-given niche.
    Fast, local-only (no live network calls) -- unlike go_deep_evidence,
    this can run inline, no background job needed.

    Reads its niche as a JSON payload in sys.argv[2]:
    `python mission_control_api.py product_concept_comparison '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        return {"success": False, "error": "niche is required"}

    from revenue_pipeline import plan
    return plan.compare_ladder_variants(niche)


def _go_deep_evidence():
    """Strategic Phase 3, Round 1 (2026-07-22) -- 'Go Deep' on-demand
    evidence action: the real, usable version of Market Validation's
    'collect evidence before production, multiple independent signals',
    for ONE opportunity the founder selects (unlike the fully-automatic
    ladder_fast_gate path, which stays honestly single-signal -- see
    decision_engine/engine.py::record_ladder_decision()). Runs 3 already-
    real, independent evidence sources -- never a new one -- and never
    gates any decision itself, purely informational, same discipline as
    revenue_pipeline/plan.py's ROI estimate. Slow (multiple live network
    calls) -- the caller (server.js) must run this as a background job.

    Reads its niche as a JSON payload in sys.argv[2]:
    `python mission_control_api.py go_deep_evidence '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        return {"success": False, "error": "niche is required"}

    from market_intelligence_engine import analyze_customer_pain
    import competitor_discovery
    from multi_source_intelligence.coverage import evidence_coverage_score

    def _safe(label, fn):
        try:
            return {"ok": True, "result": fn()}
        except Exception as e:
            return {"ok": False, "error": f"{label} failed: {e}"}

    return {
        "niche": niche,
        "customer_pain": _safe("analyze_customer_pain", lambda: analyze_customer_pain(niche)),
        "competitors": _safe("get_or_refresh_competitors", lambda: competitor_discovery.get_or_refresh_competitors(niche)),
        "evidence_coverage": _safe("evidence_coverage_score", lambda: evidence_coverage_score(niche)),
    }


def _validation_report():
    """'Run validation': validation_layer/daily_report.py (ADR-053) — the
    same real daily validation report this factory already generates,
    passthrough only."""
    from validation_layer import daily_report
    report = daily_report.generate_daily_report()
    return {"report": report, "markdown": daily_report.render_markdown(report)}


def _ai_capability():
    """Autonomous Digital Company v1, Track B2 (2026-07-19): the real AI
    Capability Registry — every named provider candidate (Claude, GPT,
    Gemini, Grok, DeepSeek, Qwen, Mistral, local models, plus Groq itself),
    Groq's metrics computed live from data/ai_cost_log.jsonl, every other
    provider honestly DISCOVERY-level (never a fabricated benchmark for a
    provider never actually called). Passthrough only, no new logic here."""
    from ai_capability import registry
    return {
        "providers": registry.list_providers(),
        "recent_requests": registry.read_capability_requests()[-20:],
    }


def _ai_capability_request():
    """Records a real department request for a different/better AI model
    (Autonomous Digital Company v1 §8) — an append-only logged request,
    never an autonomous model switch (too risky with zero comparative
    data across providers today; see ai_capability/evaluator.py). Reads
    its payload as a JSON string in sys.argv[2]:
    `python mission_control_api.py ai_capability_request '{"department":"builder","task_type":"reasoning","requested_provider":"anthropic","reason":"..."}'`"""
    from ai_capability import registry
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    record = registry.record_capability_request(
        department=payload.get("department", "unknown"),
        task_type=payload.get("task_type", "unknown"),
        requested_provider=payload.get("requested_provider", "unknown"),
        reason=payload.get("reason", ""),
    )
    recommendation = None
    if payload.get("task_type"):
        from ai_capability import evaluator
        recommendation = evaluator.recommend_for_task(payload["task_type"])
    return {"recorded": record, "current_recommendation": recommendation}


def _tool_intelligence():
    """Autonomous Digital Company v1, Track B3 (2026-07-19): real,
    evidence-cited software/AI-tool integration proposals -- '(مقترَح، لا
    تنفيذ)', matching ADR-024's existing convention. Passthrough only, no
    new logic here."""
    from tool_intelligence import proposals
    return {"proposals": proposals.list_proposals()}


def _strategic_report():
    """'Strategic Recommendations' Mission Control tab: strategic_intelligence's
    own real decision-pattern/rejection/technical-debt report (ADR-054),
    previously only reachable bundled inside the combined executive report
    -- exposed standalone here the same way _validation_report() already
    exposes validation_layer's report standalone, alongside the real
    software/AI-tool integration proposals (Track B3). No new logic —
    passthrough only."""
    from strategic_intelligence import report as strat_report
    from tool_intelligence import proposals
    report = strat_report.generate_strategic_report()
    return {
        "report": report,
        "markdown": strat_report.render_markdown(report),
        "tool_proposals": proposals.list_proposals(),
    }


def _get_infrastructure_status(timeout=15):
    """EOS Phase 2 (2026-07-19): now a thin wrapper over
    infrastructure_bridge.py, extracted as a shared module so
    ai_doctor.py can reuse the same real bridge without depending on
    this CLI dispatcher."""
    from infrastructure_bridge import get_infrastructure_status
    return get_infrastructure_status(timeout=timeout)


def _render_infrastructure_markdown(status):
    from infrastructure_bridge import render_infrastructure_markdown
    return render_infrastructure_markdown(status)


def _read_jsonl_entries(path):
    """Shared, module-local JSONL reader for the small endpoints below
    that need one (golden_hunter_status/pioneer_status) -- same
    convention every other module in this factory already follows for
    this exact pattern (no single shared Python JSONL module exists
    yet, confirmed across the codebase; each store reimplements this
    same 10-line, skip-corrupt-line read)."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _golden_hunter_status():
    """Golden Hunter Evolution -- EOS Phase 2 (2026-07-19): real recent
    activity (data/golden_hunter_events.jsonl) plus the top currently
    scored opportunities, each with a real pre-acceptance ROI estimate
    (revenue_pipeline.plan.estimate_pre_acceptance_roi() -- informational
    only, never changes the real accept/reject gate). No duplicate-
    opportunity risk here -- this only reads golden_opportunities.json
    and the event log, both already the real, single source of truth
    factory_loop.js's own goldenNicheAlreadyAttempted() circuit breaker
    already protects."""
    import json as _json
    from department_health import recent_activity_count, GOLDEN_HUNTER_EVENTS_FILE
    from revenue_pipeline import plan as revenue_plan

    opp_path = _FACTORY_ROOT / "golden_opportunities.json"
    opportunities = []
    if opp_path.exists():
        with open(opp_path, "r", encoding="utf-8") as f:
            opportunities = _json.load(f).get("results", [])

    top = sorted(opportunities, key=lambda o: o.get("profit_score", 0), reverse=True)[:5]
    enriched = []
    for o in top:
        price = o.get("ladder_price") if o.get("ladder_accepted") else None
        if price is None:
            raw = str(o.get("recommended_price", "")).replace("$", "").strip()
            try:
                price = float(raw)
            except ValueError:
                price = None
        roi = revenue_plan.estimate_pre_acceptance_roi(price) if price else {"maturity": "DISCOVERY", "reason": "لا سعر صالح لتقدير عائد مسبق"}
        enriched.append({
            "niche": o.get("niche"), "profit_score": o.get("profit_score"), "verdict": o.get("verdict"),
            "ladder": o.get("ladder"), "ladder_accepted": o.get("ladder_accepted"),
            "confidence": o.get("confidence"), "pre_acceptance_roi": roi,
        })

    events = _read_jsonl_entries(GOLDEN_HUNTER_EVENTS_FILE)
    activity = recent_activity_count([e for e in events if e.get("action") in ("attempted", "skipped")])

    return {
        "top_opportunities": enriched, "recent_activity_count_7d": activity,
        "total_scored": len(opportunities),
    }


def _pioneer_status():
    """Pioneer -- EOS Phase 2 (2026-07-19): real discovery activity.
    Pioneer's candidates feed into market_hunter.hunt_market()'s
    existing loop and are logged into the SAME golden_hunter_events.jsonl
    (no separate Pioneer-only log exists -- honestly disclosed, not
    fabricated as a distinct counter). Passthrough only."""
    from department_health import recent_activity_count, GOLDEN_HUNTER_EVENTS_FILE
    import json as _json

    def _read_jsonl(path):
        if not os.path.exists(path):
            return []
        out = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(_json.loads(line))
                except _json.JSONDecodeError:
                    continue
        return out

    events = _read_jsonl_entries(GOLDEN_HUNTER_EVENTS_FILE)
    activity = recent_activity_count([e for e in events if e.get("action") in ("attempted", "skipped")])
    return {
        "combined_activity_count_7d": activity,
        "note": "لا عدّاد نشاط منفصل لـPioneer اليوم -- اكتشافاته تُدمَج في نفس حلقة Golden Hunter ونفس سجل الأحداث",
        "source": "golden_hunter/pioneer.py discover_candidates() -> market_hunter.hunt_market()",
    }


def _knowledge_graph():
    """Knowledge Graph v1 -- EOS Phase 2 (2026-07-19): a real, queryable
    company memory built fresh from real data on every call (small
    enough today not to need snapshot caching for a live request;
    save_snapshot() is available for a disposable on-disk copy if
    needed elsewhere). Passthrough only -- see knowledge_graph/build.py."""
    from knowledge_graph import build
    graph = build.build_graph()
    return {
        "node_count": graph["node_count"], "edge_count": graph["edge_count"],
        "nodes": graph["nodes"], "edges": graph["edges"],
    }


def _department_health():
    """Department Health -- EOS Phase 2 (2026-07-19): pure assembly of
    already-computed real health signals per named department, zero new
    health computation. Passthrough only -- see department_health.py."""
    import department_health
    report = department_health.build_department_health()
    return {"report": report, "markdown": department_health.render_markdown(report)}


def _research_department():
    """Research Department -- EOS Phase 2 (2026-07-19): real analysis
    assembled under 7 named categories, no new analysis logic.
    Passthrough only -- see research_department.py."""
    import research_department
    report = research_department.build_research_report()
    return {"report": report, "markdown": research_department.render_markdown(report)}


def _ai_doctor():
    """AI Doctor -- EOS Phase 2 (2026-07-19): the real, non-fabricated
    replacement for quality_doctor.py's confirmed-fake pattern.
    Passthrough only -- see ai_doctor.py for what's actually combined."""
    import ai_doctor
    report = ai_doctor.build_ai_doctor_report()
    return {"report": report, "markdown": ai_doctor.render_markdown(report)}


def _integration_registry():
    """Integration Registry -- EOS Phase 2 (2026-07-19): real, adapter-
    based extension points for every founder-named future vendor, plus
    AI providers/commerce channels referenced from their own real
    registries. Passthrough only -- see integration_registry.py."""
    from integration_registry import list_integrations
    return {"integrations": list_integrations()}


def _founder_console():
    """Founder Console -- EOS Phase 1 (2026-07-19): the Python-side half
    (blocked channels + DEFERRED decisions). server.js merges this with
    the JS-native attention/review flags and BLOCKERS.md read. Passthrough
    only -- see founder_console.py for what's actually assembled."""
    from founder_console import build_founder_queue_partial
    return build_founder_queue_partial()


def _evolution_report():
    """'Company Evolution Engine' -- EOS Phase 1 (2026-07-19): combines
    bottleneck detection, technical debt, high-ROI ranking, tool
    proposals, and the new capability-gap scanner into one report.
    Passthrough only -- see evolution_engine.py for what's actually
    combined."""
    import evolution_engine
    report = evolution_engine.build_evolution_report()
    return {"report": report, "markdown": evolution_engine.render_markdown(report)}


def _market_review():
    """'Market Review' -- EOS Phase 1 (2026-07-19), the one genuinely
    missing weekly Continuous Improvement Engine review type. Exposed
    standalone here the same way _validation_report()/_strategic_report()
    already expose their own reports -- passthrough only."""
    from market_intelligence_core import market_review as mr
    report = mr.generate_market_review()
    return {"report": report, "markdown": mr.render_markdown(report)}


def _build_combined_executive_report_markdown(title):
    """Concatenates already-existing real report renderers —
    validation_layer's daily report, revenue_pipeline's CEO revenue
    report, executive_intelligence's bottleneck/opportunity report,
    strategic_intelligence's decision-pattern/technical-debt report
    (Autonomous Digital Company v1, 2026-07-19), and (EOS Phase 1,
    2026-07-19) ai_capability's provider registry — into one markdown
    string. No new metric, no new business logic here; every section
    reuses an already-real, already-tested report renderer.

    Shared by _export_executive_report() and _full_cycle()'s own
    executive_reports stage, which previously re-implemented this exact
    combination independently (found live, 2026-07-19) — one real
    report-building function now, not two competing copies."""
    from validation_layer import daily_report as dr
    from revenue_pipeline import pipeline as rp
    from executive_intelligence import report as exec_report
    from strategic_intelligence import report as strat_report
    from ai_capability import registry as ai_registry
    from market_intelligence_core import market_review

    validation = dr.generate_daily_report()
    validation_md = dr.render_markdown(validation)
    revenue = rp.run_revenue_pipeline()
    revenue_md = rp.render_ceo_revenue_report(revenue)
    executive = exec_report.generate_report()
    executive_md = exec_report.render_markdown(executive)
    strategic = strat_report.generate_strategic_report()
    strategic_md = strat_report.render_markdown(strategic)
    ai_providers = ai_registry.list_providers()
    ai_md = ai_registry.render_markdown(ai_providers)
    infra_status = _get_infrastructure_status()
    infra_md = _render_infrastructure_markdown(infra_status)
    market = market_review.generate_market_review()
    market_md = market_review.render_markdown(market)

    combined_md = (
        f"# {title}\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        "---\n\n## Executive Summary\n\n" + executive_md +
        "\n\n---\n\n## Strategic Recommendations\n\n" + strategic_md +
        "\n\n---\n\n## Validation\n\n" + validation_md +
        "\n\n---\n\n## Revenue\n\n" + revenue_md +
        "\n\n---\n\n## AI Capability\n\n" + ai_md +
        "\n\n---\n\n## Infrastructure\n\n" + infra_md +
        "\n\n---\n\n## Market Review\n\n" + market_md + "\n"
    )
    return combined_md, revenue


def _export_executive_report():
    """'Export executive report' Mission Control action — see
    _build_combined_executive_report_markdown() for what's actually
    combined."""
    combined_md, _revenue = _build_combined_executive_report_markdown("OpenClaw Executive Report")

    reports_dir = _FACTORY_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    fname = f"executive_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
    fpath = reports_dir / fname
    fpath.write_text(combined_md, encoding="utf-8")

    return {"path": f"reports/{fname}", "markdown": combined_md}


def _full_cycle():
    """Executive Directive Phase 11 ('Autonomous Production Launch') —
    scoped, per explicit decision in this session, to a manually-triggered,
    complete run through every real stage of the business lifecycle in one
    deliberate call, NOT an unattended scheduler (this factory's
    documented "no scheduler exists" architecture — CLAUDE.md — protects
    against paid-API costs and irreversible actions firing without a
    human triggering them; that reasoning is unchanged by this directive).

    Reuses every existing module — no new business logic, no new engine.
    Every stage is independently wrapped so a single stage's failure never
    prevents the rest from running (graceful degradation, objective 10).
    """
    cycle_id = f"cycle_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    stages = {}

    def _run(name, fn):
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            stages[name] = {"ok": True, "started_at": started_at, "result": fn()}
        except Exception as e:
            stages[name] = {"ok": False, "started_at": started_at, "error": str(e)}

    def _market_intelligence_and_evaluation():
        # Objectives 1+2: Market Intelligence -> Decision Engine ranking/
        # evaluation, real_world_mode's own real pipeline (ADR-056).
        from real_world_mode import operating_mode
        return operating_mode.run_real_world_cycle(execute_production=False)
    _run("market_intelligence_and_evaluation", _market_intelligence_and_evaluation)

    def _production():
        # Objectives 3+4: Production Candidate creation + pipeline
        # execution for every currently ACCEPTED opportunity (Phase 7).
        from production_factory import factory
        return factory.run_production_factory()
    _run("production", _production)

    def _quality_validation():
        # Objective 5: reuses validation_layer's real daily report
        # (ADR-053) — failures/bottlenecks/stalled items are exactly
        # "quality validation before publication" for this factory.
        from validation_layer import daily_report
        report = daily_report.generate_daily_report()
        return {
            "opportunities_discovered": report["opportunities_discovered"],
            "opportunities_accepted": report["opportunities_accepted"],
            "failures": report["failures"],
            "bottlenecks": report["bottlenecks"],
            "stalled_opportunities": report["stalled_opportunities"],
        }
    _run("quality_validation", _quality_validation)

    def _executive_reports():
        # Objective 6: the exact same combined report
        # export_executive_report() produces (Autonomous Digital Company
        # v1, 2026-07-19: this used to independently re-implement the
        # same validation+revenue combination — now shares the one real
        # builder, and gains the executive_intelligence/
        # strategic_intelligence sections for free), saved under this
        # cycle's own id.
        combined_md, revenue = _build_combined_executive_report_markdown(f"Full Cycle Executive Report — {cycle_id}")
        reports_dir = _FACTORY_ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        fname = f"{cycle_id}_executive_report.md"
        (reports_dir / fname).write_text(combined_md, encoding="utf-8")
        return {"path": f"reports/{fname}", "revenue_processed": revenue.get("processed", 0)}
    _run("executive_reports", _executive_reports)

    def _automation_snapshot():
        # Objective 7 (Automation): reuses _automation() verbatim — no
        # second implementation of the same n8n status read.
        return _automation()
    _run("automation_snapshot", _automation_snapshot)

    def _security_snapshot():
        # Objective 7 (Security): reuses safety_filter.py's own circuit-
        # breaker record (REJECTED_NICHES.md, CONSTITUTION.md §17) — a
        # real count of content that already failed safety/quality
        # checks and is blocked from immediate retry. No new security
        # engine; this factory has no other real security signal today.
        rejected_file = _FACTORY_ROOT / "REJECTED_NICHES.md"
        rejected_count = 0
        if rejected_file.exists():
            rejected_count = rejected_file.read_text(encoding="utf-8").count("## \U0001f6ab ")
        return {"rejected_niches_recorded": rejected_count}
    _run("security_snapshot", _security_snapshot)

    def _learning():
        # Objective 8: reuses decision_engine's existing, real feedback/
        # learning modules — never fabricates a lesson when no real sales
        # exist yet to learn from (both honestly report zero if so).
        from decision_engine import feedback, learning
        sync = feedback.sync_outcomes()
        recalibration = learning.recalibration_report()
        return {"sync_outcomes": sync, "recalibration": recalibration}
    _run("learning", _learning)

    def _knowledge_base_update():
        # Objective 9: a real, appended, machine-readable record of this
        # cycle — same append-only JSONL convention every other real log
        # in this factory already uses (market_hunter_runs.log,
        # golden_hunter_events.jsonl, decisions.jsonl), not a new
        # subsystem. Deliberately NOT a narrative file under
        # OpenClaw_Brain/18_Daily_Logs/ — that folder's own README
        # documents it as a human-curated day-boundary summary, not a
        # per-run machine log.
        log_path = _FACTORY_ROOT / "data" / "full_cycle_runs.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "cycle_id": cycle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stages_summary": {name: s["ok"] for name, s in stages.items()},
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"logged_to": "data/full_cycle_runs.jsonl"}
    _run("knowledge_base_update", _knowledge_base_update)

    ok_count = sum(1 for s in stages.values() if s["ok"])
    return {
        "cycle_id": cycle_id,
        "stages": stages,
        "stages_completed": ok_count,
        "stages_total": len(stages),
    }


def _executive_quality_gate():
    """Executive Quality Gate (Executive Directive, 2026-07-22) -- the
    permanent core layer every opportunity/product must pass before
    entering production. Reads the real, already-recorded decision for
    the given niche (never re-scores it) and runs all 20 real/honest
    criteria against it. Reads its niche as a JSON payload in
    sys.argv[2]: `python mission_control_api.py executive_quality_gate
    '{"niche":"..."}'`."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    from decision_engine import ranking
    import executive_quality_gate as eqg

    decisions = ranking.rank_all()
    decision = next((d for d in decisions if d.get("niche") == niche), None)
    if decision is None:
        raise ValueError(f"لا قرار مسجَّل لهذا النيتش: {niche!r}")

    return eqg.run_executive_quality_gate({
        "niche": decision.get("niche"),
        "ladder": decision.get("ladder"),
        "evaluation_snapshot": decision.get("evaluation_snapshot"),
        "decided_at": decision.get("decided_at"),
    })


def _record_market_evidence():
    """Market Learning Loop (Executive Directive, 2026-07-22): the
    human-driven entry point for the 12+ evidence categories nothing in
    this factory can automatically observe (a real discovery call, a
    real cold-email reply, a real objection heard on a call). Once
    logged here, the Executive Quality Gate consumes it automatically
    from that point forward. Reads its payload from sys.argv[2]:
    `python mission_control_api.py record_market_evidence
    '{"niche":"...","event_type":"...","payload":{...}}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    event_type = (payload.get("event_type") or "").strip()
    if not niche or not event_type:
        raise ValueError("{ niche, event_type } are both required")

    import market_evidence
    event = market_evidence.record_evidence(niche, event_type, payload.get("payload"), source="mission_control")
    return {"event": event}


def _enterprise_readiness_gate():
    """Enterprise Readiness Layer (Executive Directive, 2026-07-22) --
    the full product review + risk register + documentation-completeness
    + transparency report, composed. Applies PROSPECTIVELY ONLY per the
    founder's explicit decision -- a pre-gate product (the 5 shipped
    2026-07-22) is reported with its real pre-gate status, never
    silently rejected. Reads its niche as a JSON payload in sys.argv[2]:
    `python mission_control_api.py enterprise_readiness_gate '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    from decision_engine import ranking
    import enterprise_readiness as er

    decisions = ranking.rank_all()
    decision = next((d for d in decisions if d.get("niche") == niche), None)
    if decision is None:
        raise ValueError(f"لا قرار مسجَّل لهذا النيتش: {niche!r}")

    return er.run_enterprise_readiness_gate({
        "niche": decision.get("niche"),
        "title": decision.get("niche"),
        "ladder": decision.get("ladder"),
        "evaluation_snapshot": decision.get("evaluation_snapshot"),
        "decided_at": decision.get("decided_at"),
    })


def _risk_intelligence_scan():
    """On-demand Risk Intelligence Engine scan (Executive Directive,
    2026-07-22) -- never continuous, this factory has no scheduler. Only
    refreshes live competitor data when explicitly requested via
    refresh_competitors=true, matching the same live-network-call
    discipline as go_deep_evidence. Reads its payload from sys.argv[2]:
    `python mission_control_api.py risk_intelligence_scan
    '{"niche":"...","refresh_competitors":false}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import enterprise_readiness as er
    return er.run_risk_intelligence_scan(niche, refresh_competitors=bool(payload.get("refresh_competitors")))


def _convene_executive_board():
    """AI Executive Board (Executive Directive, 2026-07-22) -- the
    highest decision-making authority in this factory. All 10 executive
    roles are deterministic real-evidence analyses (never a free-form
    LLM opinion) over the same underlying Executive Quality Gate/
    Enterprise Readiness evaluation. No single executive's vote is ever
    a standalone approval -- only the aggregated board tally is. Reads
    its payload from sys.argv[2]:
    `python mission_control_api.py convene_executive_board
    '{"niche":"...","decision_type":"production"}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    from decision_engine import ranking
    import executive_board as eb

    decisions = ranking.rank_all()
    decision = next((d for d in decisions if d.get("niche") == niche), None)
    if decision is None:
        raise ValueError(f"لا قرار مسجَّل لهذا النيتش: {niche!r}")

    return eb.convene_board({
        "niche": decision.get("niche"),
        "title": decision.get("niche"),
        "ladder": decision.get("ladder"),
        "evaluation_snapshot": decision.get("evaluation_snapshot"),
        "decided_at": decision.get("decided_at"),
    }, decision_type=payload.get("decision_type", "production"))


def _review_board_track_record():
    """On-demand (not continuous -- no scheduler exists in this
    factory): compares real past board decisions against whatever real
    market evidence has accumulated since. Reads its payload from
    sys.argv[2]: `python mission_control_api.py review_board_track_record
    '{"niche":"..."}'` (niche optional -- omit for every real meeting)."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    import executive_board as eb
    return {"reviews": eb.review_board_track_record(payload.get("niche"))}


def _scan_market_alerts():
    """Market Evidence & Alerting layer (2026-07-23): the real, on-demand
    alert scan -- no scheduler exists in this factory (CLAUDE.md), so
    this only runs when explicitly triggered here. Detects real,
    auto-observable competitor changes (competitor_discovery.py's
    already-computed new/disappeared/growth-signal diff) plus real,
    human-recorded competitor-landscape events (market_evidence.py's 9
    new event types), dedupes against every already-recorded alert for
    this niche, and persists only the genuinely new ones. Reads its
    payload from sys.argv[2]:
    `python mission_control_api.py scan_market_alerts '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import market_alerts
    return market_alerts.scan_market_alerts(niche)


def _get_market_alerts():
    """Read-only lookup of every real alert already recorded for one
    niche (Critical/High/Medium/Low), grouped by severity -- never
    triggers a new scan itself (use scan_market_alerts for that). Reads
    its payload from sys.argv[2]:
    `python mission_control_api.py get_market_alerts '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import market_alerts
    return market_alerts.get_active_alerts(niche)


def _get_board_brief():
    """Executive Board Integration (2026-07-23): read-only lookup of
    whatever the board already decided for one niche (the 6-lens
    strategic brief + the 6-field decision summary), without convening a
    new meeting. Reads its payload from sys.argv[2]:
    `python mission_control_api.py get_board_brief '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import executive_board as eb
    return eb.get_latest_board_brief(niche)


def _check_decision_reopen_trigger():
    """Decision Re-open Trigger (2026-07-23): read-only -- would this
    niche's board decision be reopened right now, given whatever real
    alerts are already active? Never convenes a new meeting itself.
    Reads its payload from sys.argv[2]:
    `python mission_control_api.py check_decision_reopen_trigger '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import decision_reopen
    return decision_reopen.check_for_reopen_trigger(niche)


def _scan_and_maybe_reopen_decision():
    """Decision Re-open Trigger (2026-07-23): the one real, on-demand,
    do-everything entrypoint -- runs a real market-alert scan, then
    reopens the board's decision for this niche ONLY if that scan finds
    a materially new Critical alert (or 2+ new High alerts) since the
    last real board meeting. Never reopens on speculation. Reads its
    payload from sys.argv[2]:
    `python mission_control_api.py scan_and_maybe_reopen_decision '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import decision_reopen
    return decision_reopen.scan_and_maybe_reopen(niche)


def _get_decision_reopen_history():
    """Read-only -- the full real audit trail of every real reopen event
    for one niche. Reads its payload from sys.argv[2]:
    `python mission_control_api.py get_decision_reopen_history '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import decision_reopen
    return {"reopen_history": decision_reopen.get_reopen_history(niche)}


def _run_master_cycle():
    """Factory Master Orchestrator (Full Architecture Review, 2026-07-22)
    -- the single real call that composes Executive Quality Gate + AI
    Executive Board (which itself calls Enterprise Readiness) + Revenue
    Pipeline production for one real, already-accepted niche, instead of
    3+ separate manual actions. advisory_only defaults true: the Board's
    verdict is reported but does not block execute=True's own real
    production run (avoids silently freezing all production given zero
    real market evidence exists today) -- pass "enforce_board": true to
    make a real board rejection actually block production. Reads its
    payload from sys.argv[2]: `python mission_control_api.py
    run_master_cycle '{"niche":"...","execute":false,"enforce_board":false}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import factory_orchestrator as fo
    return fo.run_master_cycle(
        niche, execute=bool(payload.get("execute")),
        advisory_only=not bool(payload.get("enforce_board")),
    )


def _check_paddle_checkout_status():
    """ADR-085/ADR-086: re-attempts Paddle checkout-link creation for
    every real product in data/paddle_products.json (5 as of ADR-086 --
    the original $388 techdoc plus 4 more queued the same night). Sends a
    real, one-time Arabic Telegram message per product the moment
    Paddle's account-onboarding gate clears (direct Bot API send --
    bypasses n8n, same precedent as ADR-072/ADR-074's addenda). Reports
    honestly, with no message sent, while transaction_checkout_not_enabled
    is still the real Paddle response -- this is the expected result on
    every run before the founder finishes onboarding in vendors.paddle.com."""
    from scripts import check_paddle_checkout_status
    return check_paddle_checkout_status.check_and_notify_all()


_ENDPOINTS = {
    "opportunities": _opportunities,
    "production": _production,
    "revenue": _revenue,
    "automation": _automation,
    "decision_history": _decision_history,
    "system_configuration": _system_configuration,
    "recovery": _recovery,
    "resolve_recovery": _resolve_recovery,
    "production_families": _production_families,
    "commercial_execution": _commercial_execution,
    "rerun_market_analysis": _rerun_market_analysis,
    "trigger_opportunity_evaluation": _trigger_opportunity_evaluation,
    "validation_report": _validation_report,
    "export_executive_report": _export_executive_report,
    "ai_capability": _ai_capability,
    "ai_capability_request": _ai_capability_request,
    "tool_intelligence": _tool_intelligence,
    "strategic_report": _strategic_report,
    "market_review": _market_review,
    "evolution_report": _evolution_report,
    "founder_console": _founder_console,
    "integration_registry": _integration_registry,
    "ai_doctor": _ai_doctor,
    "research_department": _research_department,
    "department_health": _department_health,
    "knowledge_graph": _knowledge_graph,
    "golden_hunter_status": _golden_hunter_status,
    "pioneer_status": _pioneer_status,
    "full_cycle": _full_cycle,
    "go_deep_evidence": _go_deep_evidence,
    "product_concept_comparison": _product_concept_comparison,
    "opportunity_pipeline": _opportunity_pipeline,
    "check_paddle_checkout_status": _check_paddle_checkout_status,
    "executive_quality_gate": _executive_quality_gate,
    "record_market_evidence": _record_market_evidence,
    "enterprise_readiness_gate": _enterprise_readiness_gate,
    "risk_intelligence_scan": _risk_intelligence_scan,
    "convene_executive_board": _convene_executive_board,
    "review_board_track_record": _review_board_track_record,
    "get_board_brief": _get_board_brief,
    "scan_market_alerts": _scan_market_alerts,
    "get_market_alerts": _get_market_alerts,
    "check_decision_reopen_trigger": _check_decision_reopen_trigger,
    "scan_and_maybe_reopen_decision": _scan_and_maybe_reopen_decision,
    "get_decision_reopen_history": _get_decision_reopen_history,
    "run_master_cycle": _run_master_cycle,
}


def main():
    endpoint = sys.argv[1] if len(sys.argv) > 1 else None
    fn = _ENDPOINTS.get(endpoint)
    if fn is None:
        print(json.dumps({"success": False, "error": f"unknown endpoint: {endpoint!r}, expected one of {list(_ENDPOINTS)}"}, ensure_ascii=False))
        sys.exit(1)

    try:
        result = fn()
        print(json.dumps({"success": True, **result}, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

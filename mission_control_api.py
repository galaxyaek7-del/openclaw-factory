#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Mission Control API bridge (Phase 8).

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
        # Autonomous Company Runtime (ADR-157, 2026-07-31): Objective 7
        # "Self-Healing" folded into this existing panel rather than a
        # 4th new one -- pending_retries above already IS the real
        # "retry transient failures" mechanism; this adds the one
        # genuinely missing citation, the real escalation path.
        "escalation_when_recovery_fails": "factory_loop.js::checkNeedsAttention()/writeNeedsAttention() -- real, writes NEEDS_ATTENTION.md and notifies the founder via the existing Telegram channel on a real recovery failure. Never a silent auto-retry loop, never a new auto-restart daemon.",
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
    """Autonomous Digital Company v1, Track B2 (2026-07-19); extended for
    the Technology Investment Council directive (2026-07-23): the real AI
    Capability Registry — every named provider candidate (Claude, GPT,
    Gemini, Grok, DeepSeek, Qwen, Mistral, Kimi, Doubao, local models, plus
    Groq itself), Groq's metrics computed live from data/ai_cost_log.jsonl
    across all 8 named criteria (quality/cost/speed/availability/security/
    maintainability/customer_value/business_impact), every other provider
    honestly DISCOVERY-level (never a fabricated benchmark for a provider
    never actually called). Passthrough only, no new logic here."""
    from ai_capability import registry
    return {
        "providers": registry.list_providers(),
        "recent_requests": registry.read_capability_requests()[-20:],
    }


def _evidence_network_status():
    """Evidence Network (ADR-128, 2026-07-25): the real, honest connector
    inventory -- which evidence sources are actually callable today
    (competitor_discovery.py, market_intelligence_engine.py) vs.
    declared-but-not-built (job postings, pricing pages, marketplaces,
    patents, enterprise demand, iteration tracking). Passthrough only, no
    new logic here."""
    import evidence_network
    return evidence_network.network_status_report()


def _evidence_coverage_status():
    """Evidence Network (ADR-128, 2026-07-25): real, aggregate Evidence
    Coverage / Freshness / Unknown Count / Research Queue / Top Missing
    Signals — across every real decision that carries a persisted
    evidence_completeness snapshot (ADR-127 onward), plus real freshness
    stats over the two real persistent evidence caches. Passthrough only,
    no new logic here."""
    import evidence_network
    return {
        "aggregate": evidence_network.aggregate_evidence_report(),
        "freshness": evidence_network.evidence_freshness_report(),
    }


def _customer_pipeline_status():
    """Galaxy Forge Customer Platform, Phase 2 Round 1 (ADR-130, 2026-07-25):
    the real Mission Control supervision view over every real customer
    request's pipeline state -- stage distribution, per-request Status/
    Progress/Logs/Failures/Recovery/Estimated-completion, and which
    requests need a real founder action right now (blocked on Paddle
    onboarding, needs a bespoke product, or failed). Passthrough only, no
    new logic here."""
    import customer_pipeline
    return customer_pipeline.list_pipeline_overview()


def _advance_customer_pipeline():
    """Batch-sweeps every real customer request still in NEW through real
    Qualification + Opportunity Evaluation + Price Generation + Proposal
    (customer_pipeline.advance_all_new_requests()). This factory has no
    scheduler (CLAUDE.md) -- this is the one-click-away manual trigger,
    same convention as check-paddle-checkout-status. Slow: each NEW
    request runs a real live Groq market-research call, same reason
    rerun-market-analysis/trigger-opportunity-evaluation run as
    background jobs in server.js."""
    import customer_pipeline
    return customer_pipeline.advance_all_new_requests()


def _customer_fulfillment_queue():
    """Customer Platform Round 6 (2026-07-29): real Production/QA/
    Packaging/Delivery queue for Mission Control's executive cockpit --
    passthrough over customer_pipeline.list_fulfillment_queue(), no new
    logic here."""
    import customer_pipeline
    return customer_pipeline.list_fulfillment_queue()


def _customer_invoices():
    """Customer Platform Round 6 (2026-07-29): real invoices generated
    from actual completed Paddle payments -- passthrough over
    customer_pipeline.list_invoices(), no new logic here."""
    import customer_pipeline
    return customer_pipeline.list_invoices()


def _check_customer_payments():
    """Customer Platform Round 3 (2026-07-29): batch-sweeps every real
    customer request currently AWAITING_PAYMENT against Paddle's real
    transaction list, transitioning to PAID + generating a real invoice
    for any that actually completed. Same one-click-away manual trigger
    convention as _advance_customer_pipeline (no scheduler exists)."""
    import customer_pipeline
    return customer_pipeline.check_all_awaiting_payments()


def _executive_score():
    """Executive Score, Python-side sub-scores only (Executive
    Intelligence Core, Round 6, 2026-07-29) -- Operational Stability and
    Customer Happiness are merged in by server.js's Mission Control panel
    handler (JS-native signals, see executive_score.py's own docstring
    for why). Passthrough only -- see executive_score.py."""
    import executive_score
    return executive_score.compute_executive_score()


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


def _publish_protection_status():
    """Global Commercial Hardening, Phase 1 (2026-07-29): read-only Mission
    Control panel over channels/publish_protection.py's real per-arm state
    (publish counts, cooldowns, risk_score) plus the global emergency-stop
    flag. Passthrough only."""
    from channels import publish_protection
    return publish_protection.list_publish_protection_status()


def _publish_emergency_stop():
    """The founder's own real, immediate halt across every marketplace
    arm. Reads its payload from sys.argv[2]:
    `python mission_control_api.py publish_emergency_stop '{"reason":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise ValueError("{ reason } is required")

    from channels import publish_protection
    return publish_protection.trigger_emergency_stop(reason, triggered_by="founder")


def _publish_emergency_resume():
    """Reverses publish_emergency_stop."""
    from channels import publish_protection
    return publish_protection.clear_emergency_stop()


def _safe_mode_status():
    """Global Trust & Resilience Layer, Round 2 (2026-07-29): read-only
    Mission Control panel over safe_mode.py's real per-subsystem
    isolation state (ai_generation, market_intelligence -- their own
    real flags; marketplace_publishing -- a real passthrough to
    channels/publish_protection.py's global emergency stop). Passthrough
    only."""
    import safe_mode
    return safe_mode.list_safe_mode_status()


def _mark_subsystem_unstable():
    """The founder's own real action to isolate one named subsystem
    without halting the rest of the company. Reads its payload from
    sys.argv[2]:
    `python mission_control_api.py mark_subsystem_unstable '{"name":"ai_generation","reason":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    name = (payload.get("name") or "").strip()
    reason = (payload.get("reason") or "").strip()
    if not name or not reason:
        raise ValueError("{ name, reason } are required")

    import safe_mode
    return safe_mode.mark_subsystem_unstable(name, reason, triggered_by="founder")


def _clear_subsystem_unstable():
    """Reverses mark_subsystem_unstable. Reads its payload from sys.argv[2]:
    `python mission_control_api.py clear_subsystem_unstable '{"name":"ai_generation"}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("{ name } is required")

    import safe_mode
    return safe_mode.clear_subsystem_unstable(name)


def _approve_first_publish():
    """Founder Protection (Global Trust & Resilience Layer, Round 4,
    2026-07-29): the founder's own real, explicit clearance for a
    genuinely new arm's very first real publish. Reads its payload from
    sys.argv[2]:
    `python mission_control_api.py approve_first_publish '{"arm_name":"kdp"}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    arm_name = (payload.get("arm_name") or "").strip()
    if not arm_name:
        raise ValueError("{ arm_name } is required")

    from channels import publish_protection
    return publish_protection.approve_first_publish(arm_name, approved_by="founder")


def _approve_elevated_risk_publish():
    """The founder's own real, explicit, single-use clearance for one
    publish attempt whose computed risk_score crossed the real
    high-risk threshold. Reads its payload from sys.argv[2]:
    `python mission_control_api.py approve_elevated_risk_publish '{"arm_name":"gumroad"}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    arm_name = (payload.get("arm_name") or "").strip()
    if not arm_name:
        raise ValueError("{ arm_name } is required")

    from channels import publish_protection
    return publish_protection.approve_elevated_risk_publish(arm_name, approved_by="founder")


def _autonomous_operations_status():
    """Final Executive Directive (2026-07-29): a real, citation-only
    status map answering the directive's own implicit question -- "is
    Galaxy Forge running autonomously right now, and exactly what does
    that include." Passthrough only -- see autonomous_operations_status.py."""
    import autonomous_operations_status
    return {
        "activities": autonomous_operations_status.activity_status()["activities"],
        "summary": autonomous_operations_status.autonomous_operations_summary(),
    }


def _resilience_status():
    """Continuous Trust & Resilience Monitoring (2026-07-29): the real
    Python-side half of Monitor+Classify+Report -- resilience_monitor.py's
    assess_resilience(), reusing every signal (safe_mode, publish_
    protection, customer risk, security drift, health trend) verbatim.
    server.js merges in the 2 JS-native signals (storage_integrity,
    customer reviews/support tickets), same executiveScoreService()
    merge pattern. Passthrough only."""
    import resilience_monitor
    return resilience_monitor.assess_resilience()


def _resilience_incidents():
    """Read-only Mission Control panel: the real incident history
    (Learn) -- resilience_monitor.py's list_incidents(). Passthrough
    only."""
    import resilience_monitor
    return {"incidents": resilience_monitor.list_incidents()}


def _resilience_monitor_tick():
    """The one real automatic path -- Monitor + Classify (Python signals
    only) + Learn (record any new critical/emergency incident). Never
    calls trigger_emergency_stop()/mark_subsystem_unstable() -- those
    stay exclusively founder-triggered Mission Control actions."""
    import resilience_monitor
    result = resilience_monitor.assess_resilience()
    recorded = resilience_monitor.record_incidents_for_findings(result["findings"])
    return {"resilience_score": result["resilience_score"], "active_alert_count": len(result["active_alerts"]), "recorded_incidents": recorded}


def _executive_brief():
    """Strategic Intelligence Core (2026-07-29): the real, read-only
    Executive Brief -- company_health/top_risks/top_opportunities/
    top_bottlenecks/recommended_priorities/products_to_accelerate/
    products_to_pause/research_needed/founder_decisions_required, every
    field a citation of an already-real function
    (strategic_intelligence_core.build_executive_brief() itself never
    computes a new signal). Same {report, markdown} shape as
    _evolution_report()/_ai_doctor()/_department_health() -- this one
    section serves both the live Mission Control panel and
    factory_loop.js's daily dated-report generation. Passthrough only --
    Constitution-first and no-autonomous-high-risk-decisions are both
    already real everywhere an irreversible action exists in this
    factory; this endpoint reads, never acts."""
    import strategic_intelligence_core
    report = strategic_intelligence_core.build_executive_brief()
    return {"report": report, "markdown": strategic_intelligence_core.render_markdown(report)}


def _strategic_score():
    """Real, read-only Strategic Score for one niche -- the directive's
    11 named dimensions, each `{value, source, reason}` citing an
    already-real source. Reads its payload from sys.argv[2]:
    `python mission_control_api.py strategic_score '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import strategic_intelligence_core
    return strategic_intelligence_core.strategic_score(niche)


def _convene_galaxy_council():
    """Galaxy Council (2026-07-29): the real 9-member intelligence
    convening for one niche -- every member's opinion/confidence/
    evidence/risk/recommendation/founder_approval_required, honest
    disagreement detection (never a fabricated consensus). Read-only --
    does not persist anything by itself; use record_council_
    recommendation to append it to institutional memory. Reads its
    payload from sys.argv[2]:
    `python mission_control_api.py convene_galaxy_council '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import galaxy_council
    return galaxy_council.convene_council(niche)


def _record_council_recommendation():
    """Explicit, human-triggered append only -- never automatic (this
    factory has no scheduler). Re-convenes the Council fresh for this
    niche (never records a stale/passed-in session) and immediately
    appends the real result to data/council_recommendations.jsonl, the
    real substrate council_learning_summary() needs. Reads its payload
    from sys.argv[2]:
    `python mission_control_api.py record_council_recommendation
    '{"niche":"...","decision_id":"..."}'` (decision_id optional)."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import galaxy_council
    session = galaxy_council.convene_council(niche)
    return galaxy_council.record_council_recommendation(session, decision_id=payload.get("decision_id"))


def _council_learning_summary():
    """Galaxy Council Learning (2026-07-29): the real 3-way join
    (Council Recommendation -> real Founder Decision -> real Outcome).
    Honestly NOT ENOUGH EVIDENCE until real recommendation/decision/
    outcome triples accumulate -- never backfilled. Passthrough only."""
    import galaxy_council
    return galaxy_council.council_learning_summary()


def _investment_score():
    """Capital Allocation Engine (2026-07-29): the real 14-dimension
    Investment Score for one niche -- 7 delegated verbatim to
    strategic_intelligence_core.strategic_score(), 7 new real citations
    from value_engine.compute_value_profile(). Reads its payload from
    sys.argv[2]: `python mission_control_api.py investment_score
    '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import capital_allocation_engine
    return capital_allocation_engine.investment_score(niche)


def _opportunity_cost_report():
    """Capital Allocation Engine (2026-07-29): real opportunity-cost
    pairing across the whole real portfolio -- which real ACCEPTED
    opportunities are effectively delaying which other, higher real
    Priority Score opportunities. Passthrough only."""
    import capital_allocation_engine
    return capital_allocation_engine.opportunity_cost()


def _executive_brain_directive():
    """Executive Brain (ADR-144, 2026-07-30): a LIVE, read-only preview of
    the current Executive Directive -- reuses strategic_intelligence_
    core.build_executive_brief() + global_opportunity_exchange +
    capital_allocation_engine + evolution_queue verbatim, arbitrates their
    real candidate actions into exactly ONE recommendation via the
    founder's own named Priority 1-5 framework. Deliberately does NOT
    record to the permanent ledger (record_ledger=False) -- a Mission
    Control page view must never itself grow the "permanent lessons"
    ledger, or every refresh would append a near-duplicate entry,
    directly violating the directive's own "no duplicated knowledge"
    requirement. Only the daily tick (generate_daily_executive_directive
    below) ever records. Expensive (chains 3 full-portfolio scans,
    measured live ~55-60s) -- read-only/recommend-only; requires_founder_
    approval is always True, nothing here executes, approves, rejects,
    publishes, or reallocates anything."""
    import executive_brain
    return executive_brain.build_executive_directive(record_ledger=False)


def _generate_daily_executive_directive():
    """The one real path that grows the permanent ledger -- called once
    per day by factory_loop.js's tick (see maybeGenerateDailyExecutive
    Directive), never on a live Mission Control view. record_ledger=True
    here is the deliberate exception to _executive_brain_directive()'s
    own read-only default above."""
    import executive_brain
    return executive_brain.build_executive_directive(record_ledger=True)


def _executive_directives_history():
    """Read-only Mission Control panel: the real Learning History of every
    Executive Directive this factory has ever generated, most recent
    first. Passthrough only."""
    import executive_brain
    return executive_brain.list_executive_directives()


def _gfos_status():
    """GF-OS (ADR-147, 2026-07-30): the single real coordination/citation
    aggregate -- department registry (all 12 real departments), mission
    lifecycle (real scheduler.py buckets + orchestrator.py stages, no
    new queue), and the 10 most recent real Enterprise Timeline entries.
    A citation layer only -- every module cited is still called directly
    by every other real caller exactly as before; safe_mode.py's per-
    subsystem independence (ADR-135) is unchanged. Expensive (~13s,
    department_health.build_department_health() touches multiple real
    subsystems) -- read-only."""
    import gfos
    return gfos.gfos_status()


def _engine_registry():
    """Galaxy Operating System (ADR-172, 2026-08-05): the real 9-engine
    map -- every entry a citation of an already-real module. Cheap, no
    live scan."""
    import gfos
    return gfos.engine_registry()


def _if_i_were_the_ceo_report():
    """Galaxy Operating System (ADR-172, 2026-08-05): the real weekly
    self-governance report, answering the directive's 7 named questions
    entirely from already-real citations (ceo_decision_center.py,
    evolution_engine.py). Expensive (~56s, chains ceo_decision_center.
    answer_ceo_questions()'s own real sub-calls) -- read-only."""
    import gfos
    return gfos.if_i_were_the_ceo_report()


def _gfos_enterprise_timeline():
    """GF-OS (ADR-147, 2026-07-30): the full real Enterprise Timeline
    (up to 50 entries, vs. gfos-status's own 10-entry preview) -- a pure
    merge of every real ledger this factory already keeps, most recent
    first. Cheap (~0.2s measured live)."""
    import gfos
    return gfos.enterprise_timeline(limit=50)


def _affiliate_products():
    """Affiliate Commerce (ADR-149, 2026-07-30): the real, static,
    disclosed-source product dataset -- reads sys.argv[2] for an
    optional {"category": "..."} payload, defaults to
    standing_desk_converters (the one real category this round built).
    Public route -- called from server.js's unauthenticated
    /api/affiliate/products, since customer-facing pages have no
    Mission Control login."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    category = payload.get("category", "standing_desk_converters")

    from affiliate_commerce import products
    return products.list_products(category=category)


def _affiliate_click():
    """Affiliate Commerce (ADR-149, 2026-07-30): records one real click
    and returns the real Amazon URL to redirect to (with a real
    Associates tag if one is configured, honestly without one if not).
    Reads {"product_id": "...", "referrer": "..."} from sys.argv[2]."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    product_id = (payload.get("product_id") or "").strip()
    if not product_id:
        raise ValueError("{ product_id } is required")

    from affiliate_commerce import products, networks, click_tracking
    product = products.get_product(product_id)
    if not product:
        # "success" here means the RPC itself succeeded, not that the
        # product was found -- runPythonService() rejects on a literal
        # success:false, which would turn an honest "no such product"
        # into a generic 500 on the server.js side. "found" is the real
        # honesty signal the caller checks.
        return {"success": True, "found": False, "error": f"no real product with id {product_id!r}"}

    click_tracking.record_click(product_id, referrer=payload.get("referrer"))
    url = networks.build_amazon_url(product["asin"])
    return {"success": True, "found": True, "url": url, "tag_configured": networks.amazon_associate_tag_configured()}


def _affiliate_commerce_status():
    """Affiliate Commerce (ADR-149, 2026-07-30): the real Mission
    Control status panel -- real click counts per product, real
    Associates-tag configuration status. Never a fabricated conversion
    rate or commission figure -- both require the real affiliate
    network's postback, which does not exist yet."""
    from affiliate_commerce import networks, click_tracking, products
    return {
        "network": networks.network_status(),
        "clicks": click_tracking.click_summary(),
        "products": products.list_products(),
        "not_implemented_yet": [
            "Real Amazon Associates account (needs the founder's own real signup -- this system cannot create it)",
            "Real conversion/commission tracking (needs the affiliate network's real postback API)",
            "SEO engine, multi-partner comparison, auto-discovery (explicitly excluded by the founder's own directive as premature)",
        ],
    }


def _affiliate_simulation_report():
    """Simulation-First Company Build (ADR-153, 2026-07-30): triggers one
    real simulation cycle over the real click ledger (never a real
    financial ledger -- see affiliate_commerce/simulation.py's own
    guards) and returns the real, honestly SIMULATED funnel report.
    Every field is explicitly labeled -- never presented as real
    revenue, never merged with the real affiliate-commerce-status
    panel's real click counts."""
    from affiliate_commerce import simulation
    if simulation.is_simulation_mode("affiliate_commerce"):
        simulation.run_simulation_cycle()
    return simulation.simulation_funnel_report()


def _launch_readiness_score():
    """Simulation-First Company Build (ADR-153, 2026-07-30): the real,
    per-division 8-dimension Launch Readiness Score. Every dimension is
    a real, mechanical, disclosed-heuristic check -- never a semantic
    quality judgment, never fabricated for a division with no real
    architecture yet."""
    from launch_readiness import launch_readiness_score
    return launch_readiness_score()


def _executive_intelligence_questions():
    """Executive Intelligence Layer (ADR-154, 2026-07-31): the real
    answers to the founder's 8 named strategic questions -- almost
    entirely citation of already-real functions (executive_brain.py,
    capital_allocation_engine.py, strategic_intelligence_core.py).
    Named executive_questions.py (not executive_intelligence.py -- a
    real, pre-existing, differently-scoped package of that exact name
    already exists, ADR-052)."""
    from executive_questions import answer_strategic_questions
    return answer_strategic_questions()


def _company_pulse():
    """Enterprise Operations Center (ADR-155, 2026-07-31): the real
    "Company Pulse" -- 7 named questions, each citing an already-real
    source. Never a fabricated composite health score."""
    from enterprise_operations import company_pulse
    return company_pulse()


def _dependency_matrix():
    """Enterprise Operations Center (ADR-155, 2026-07-31): a real,
    mechanical, AST-based Python-import dependency analysis
    (dependency_graph.py) over each department's one real primary
    module -- a disclosed code-level proxy for operational dependency,
    never a fabricated business-relationship graph."""
    from enterprise_operations import dependency_matrix
    return dependency_matrix()


def _executive_analytics():
    """Enterprise Operations Center (ADR-155, 2026-07-31): real trends
    over time -- health_trend.py, channels/ledger.py's revenue_trend(),
    evolution_queue.py's real outcome measurements -- consolidated,
    zero new computation."""
    from enterprise_operations import executive_analytics
    return executive_analytics()


def _unified_decision_engine():
    """Enterprise Executive Brain (ADR-156, 2026-07-31): the real
    prioritized action list + conflicts + duplicated work + idle
    divisions + bottlenecks + missing dependencies, each citing an
    already-real function."""
    from enterprise_executive_brain import unified_decision_engine
    return unified_decision_engine()


def _executive_kpi_system():
    """Enterprise Executive Brain (ADR-156, 2026-07-31): the real
    per-division 8-KPI scorecard, reusing launch_readiness.py's real
    5-division registry. Intelligence Score and Production Capacity
    are honestly NOT_ARCHITECTED -- no real source exists."""
    from enterprise_executive_brain import executive_kpi_system
    return executive_kpi_system()


def _enterprise_dependency_graph():
    """Enterprise Executive Brain (ADR-156, 2026-07-31): extends
    enterprise_operations.py's dependency_matrix() with real reverse-
    dependents, cascade-impact, and cycle detection (dependency_graph.py)."""
    from enterprise_executive_brain import enterprise_dependency_graph
    return enterprise_dependency_graph()


def _enterprise_scheduler():
    """Enterprise Executive Brain (ADR-156, 2026-07-31): merges
    capital_allocation_engine's real ROI ranking with gfos.py's real
    scheduler buckets into one ranked view -- no new ranking algorithm."""
    from enterprise_executive_brain import enterprise_scheduler
    return enterprise_scheduler()


def _executive_scenario_simulator():
    """Enterprise Executive Brain (ADR-156, 2026-07-31): 3 real,
    disclosed-assumption HYPOTHETICAL projections (revenue growth, AI
    cost increase, infrastructure-failure cascade) + 4 honestly
    NOT_ARCHITECTED scenarios. Never a prediction, never written to any
    ledger. Reads sys.argv[2] for optional {"cascade_department": "..."}."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    from enterprise_executive_brain import executive_scenario_simulator
    return executive_scenario_simulator(cascade_department=payload.get("cascade_department"))


def _executive_replay():
    """Autonomous Company Runtime (ADR-157, 2026-07-31): real
    chronological replay over gfos.py::enterprise_timeline(), optionally
    date-filtered, plus executive_decision_memory.py's real explain
    detail for one decision_id. Reads sys.argv[2] for optional
    {"from_date":"...", "to_date":"...", "decision_id":"..."}."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    from company_runtime import executive_replay
    return executive_replay(
        from_date=payload.get("from_date"), to_date=payload.get("to_date"), decision_id=payload.get("decision_id"),
    )


def _autonomous_daily_cycle_status():
    """Autonomous Company Runtime (ADR-157, 2026-07-31): a real,
    disclosed, static citation of factory_loop.js's real tick-driven
    functions for each of the directive's 9 named daily-cycle stages --
    never adds a new automatic call."""
    from company_runtime import autonomous_daily_cycle_status
    return autonomous_daily_cycle_status()


def _growth_stage_status():
    """Enterprise Growth Engine (ADR-158, 2026-07-31): the real Executive
    Growth Dashboard -- current Growth Stage (0-5, non-cached, recomputed
    fresh every call), remaining requirements/blocking factors, estimated
    readiness, per-division stage objectives, and the highest-ROI action
    to advance (pure citation of enterprise_scheduler()). Expensive
    (chains enterprise_scheduler() -> capital_allocation_engine, measured
    live ~30s) -- read-only, never triggers any action."""
    import growth_stages
    dashboard = growth_stages.build_growth_dashboard()
    return {"dashboard": dashboard, "questions": growth_stages.answer_growth_questions(dashboard)}


def _simulate_growth_stage_progression():
    """Enterprise Growth Engine (ADR-158, 2026-07-31): Simulation Mode
    integration -- recomputes the Growth Stage against hypothetical
    overrides (e.g. {"total_revenue_usd": 500}), writes nothing to disk.
    Reads sys.argv[2] for the hypothetical override dict."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    import growth_stages
    return growth_stages.simulate_stage_progression(**payload)


def _company_state():
    """Autonomous Company Runtime (ADR-157, 2026-07-31): a real,
    priority-ordered, read-only status label -- never a live behavioral
    switch. SCALING is defined but never selected -- no real scale-out
    signal exists anywhere in this factory."""
    from company_runtime import company_state
    return company_state()


def _truth_first_compliance():
    """Truth First Constitution (ADR-160, 2026-07-31): the real
    vocabulary census + citations of the 3 already-real standing
    controls this directive's other requirements are satisfied by --
    cheap (a local *.py file scan, no full-portfolio computation)."""
    import truth_first
    return truth_first.truth_first_compliance_report()


def _evidence_coverage_report():
    """Enterprise Evidence Engine (ADR-163, 2026-07-31): the real
    Evidence Coverage Report deliverable -- for each of the 10 named
    evidence types, cites the real existing evidence source(s) already
    confirmed in this factory, or honestly lists it as lacking."""
    import evidence_engine
    return evidence_engine.evidence_coverage_report()


def _evidence_viewer():
    """Enterprise Evidence Engine (ADR-163, 2026-07-31): real
    chronological reader over data/evidence_ledger.jsonl. Reads
    sys.argv[2] for optional {"evidence_type": "...", "module": "..."}."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    import evidence_engine
    return {"entries": evidence_engine.read_evidence(evidence_type=payload.get("evidence_type"), module=payload.get("module"))}


def _executive_evidence_dashboard():
    """Enterprise Evidence Engine (ADR-163, 2026-07-31): merges verify()
    (per named type) + the Evidence Coverage Report summary -- the
    Executive Evidence Dashboard deliverable."""
    import evidence_engine
    verification_by_type = {etype: evidence_engine.verify(evidence_type=etype) for etype in evidence_engine.EVIDENCE_TYPES}
    return {"verification_by_type": verification_by_type, "coverage": evidence_engine.evidence_coverage_report()}


def _enterprise_capital_allocation_dashboard():
    """Enterprise Capital Allocation Engine (ADR-165, 2026-07-31):
    extends -- never duplicates -- capital_allocation_engine.py's real
    14-dim Investment Score + dashboard (ADR-139). Adds the 10-named-
    strategic-resource allocation map, company capacity utilization,
    and a real, disclosed 'projects overfunded' heuristic."""
    import enterprise_capital_allocation as eca
    return eca.build_enterprise_capital_allocation_dashboard()


def _capital_decisions_report():
    """Capital Allocation Engine: Investment Decisions & Portfolio
    Balance (ADR-176, 2026-08-05): the real INVEST NOW/BUILD LATER/
    EXPERIMENT/REJECT decision + written reasoning for every real niche
    in scheduler.py's real buckets, portfolio balance by real ladder
    character, and resource-optimization citation. A real relabeling of
    already-real systems, never a second decision engine."""
    import enterprise_capital_allocation as eca
    return eca.build_capital_decisions_report()


def _goos_evaluate_opportunity():
    """Galaxy Opportunity Operating System (ADR-171, 2026-08-05): the
    real 15-section Opportunity Intelligence Report + 20-dimension
    evaluation + advisory 0-100 score for one real niche. Consolidation
    layer only -- never a second decision engine, never gates
    production itself (decision_engine's real ACCEPTED/REJECTED/
    DEFERRED status + profit_oracle.py's real 65/100 weighted floor are
    unchanged). Reads its payload from sys.argv[2]:
    `python mission_control_api.py goos_evaluate_opportunity '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import goos
    return goos.build_opportunity_intelligence_report(niche)


def _brand_dna_report():
    """Customer Experience & Brand DNA (ADR-170, 2026-08-05): the real
    Company Personality / Communication Standards / Customer Journey
    Standards / Trust Framework / Customer Memory Architecture / Continuous
    Improvement citation report. Cheap -- no live scan, all inputs static
    or already-computed."""
    import brand_dna
    return brand_dna.brand_dna_report()


def _truth_registry_report():
    """Enterprise Truth Registry (ADR-168, 2026-07-31): the real,
    mechanical per-component inventory (name/category/purpose/location/
    owner/dependencies/dependents/status/production usage/live
    verified/test coverage/last verification/last commit/confidence/
    criticality) over all ~246 real internal Python modules, plus the
    directive's 10 named summary sections and Enterprise Truth Score.
    Expensive -- re-invokes reality_audit.py's own live 152-endpoint
    scan internally (measured live ~255s for the registry alone)."""
    import truth_registry as tr
    registry = tr.build_truth_registry()
    return tr.build_truth_registry_report(registry=registry)


def _automation_revenue_dashboard():
    """AI Automation Revenue Engine (ADR-164, 2026-07-31): real
    opportunity discovery/scoring for automation-product categories --
    reuses profit_oracle.py::ladder_opportunity_score() verbatim, never
    a second scoring algorithm. Honestly returns NO VERIFIED
    OPPORTUNITY FOUND when no real candidate clears the real hard
    gates -- never invents one. Never triggers golden_hunter.hunt.
    run_hunt() (a real, passive-only scanner)."""
    import automation_dashboard
    return automation_dashboard.build_automation_dashboard()


def _market_domination_dashboard():
    """Global Market Domination Engine (ADR-175, 2026-08-05): real
    candidate discovery across all 6 real ladders (not automation-only)
    + real GOOS 10-dimension evaluation, ranked by profit_oracle.py's
    real LADDER_RANKS priority. 6 of the directive's 8 named regions
    are honestly NOT_MEASURABLE -- a standing, 3x-reconfirmed founder
    deferral (2026-07-23), never fabricated. Passive-only, never
    triggers a new evaluation cycle."""
    import market_domination_engine
    return market_domination_engine.build_market_domination_dashboard()


def _digital_twin_dashboard():
    """Enterprise Digital Twin (ADR-161, 2026-07-31): advisory-only real
    REAL STATE + DIGITAL TWIN view across 17 named domains, 8 named
    what-if scenarios, and the real preview-action registry. Never
    calls a real approve/reject/publish/reallocate function -- see
    digital_twin.py's own top docstring for the founder-confirmed
    architecture (AskUserQuestion, advisory preview only)."""
    import digital_twin
    return digital_twin.build_digital_twin_dashboard()


def _preview_production_action():
    """Enterprise Digital Twin (ADR-161, 2026-07-31): PREVIEW/SIMULATE/
    ESTIMATE IMPACT/ROLLBACK PLAN for one real, named production action
    type. Reads sys.argv[2] for {"action_type": "...", ...params}."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    action_type = payload.pop("action_type", None)
    if not action_type:
        raise ValueError("{ action_type } is required")
    import digital_twin
    return digital_twin.preview_action(action_type, **payload)


def _strategic_planning_dashboard():
    """Enterprise Strategic Planning System (ADR-159, 2026-07-31): the
    real rolling roadmap (5 time horizons), per-division status board,
    Enterprise Priority Matrix, instant Mission Control Q&A, and
    extended Executive Timeline -- almost entirely a citation layer
    over gfos.py/growth_stages.py/executive_questions.py/execution_
    status.py, each computed exactly once. Expensive (chains
    answer_strategic_questions() + build_growth_dashboard() +
    build_execution_status_report(), measured live ~70s)."""
    import strategic_planning
    return strategic_planning.build_strategic_planning_dashboard()


def _simulate_roadmap_execution():
    """Enterprise Strategic Planning System (ADR-159, 2026-07-31):
    Simulation Mode integration -- recomputes the rolling roadmap
    against a hypothetical Growth Stage result, writes nothing to disk.
    Reads sys.argv[2] for the hypothetical override dict."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    import strategic_planning
    return strategic_planning.simulate_roadmap_execution(**payload)


def _record_daily_growth_stage_snapshot():
    """Enterprise Strategic Planning System (ADR-159, 2026-07-31): the
    ONE real write path for Growth Stage history -- called only by
    factory_loop.js's own once-per-calendar-day tick gate, never from a
    live Mission Control view (same discipline as generate_daily_
    executive_directive avoiding a page-refresh-duplicates-the-ledger
    bug, ADR-144)."""
    import growth_stages
    return {"snapshot": growth_stages.record_growth_stage_snapshot()}


def _market_intelligence_source_status():
    """Executive Command Center (ADR-146, 2026-07-30): the real,
    registered external-evidence-source inventory for the Market
    Intelligence panel -- reuses multi_source_intelligence.registry.
    get_connectors() verbatim, never a second connector list. For
    sources that are UNCONDITIONALLY unavailable regardless of niche
    (reddit, product_hunt, google_trends -- confirmed by reading each
    connector: none of the three even touches its own `niche` argument
    before returning a static unavailable_result), a real check(None)
    call is safe and cheap -- it triggers no live network call, just
    returns the same real, honest, already-written reason
    (missing credentials / requires prior commercial contact / n8n gate
    not activated). For sources that DO make a real live call given a
    real niche (hacker_news, github, stack_overflow, public_search),
    this deliberately does NOT invoke them with a placeholder niche --
    same 'avoid an accidental live-call side effect from a read path'
    discipline research_department.py already established -- they are
    reported as real/registered/query-capable without being triggered."""
    import multi_source_intelligence.connectors  # noqa: F401 -- triggers pkgutil auto-registration, see that package's own docstring
    from multi_source_intelligence.registry import get_connectors

    _STATIC_UNAVAILABLE = {"reddit", "product_hunt", "google_trends"}
    connectors = get_connectors()
    sources = []
    for name, check_fn in sorted(connectors.items()):
        if name in _STATIC_UNAVAILABLE:
            result = check_fn(None)
            sources.append({"name": name, "status": "unavailable", "reason": result.reason})
        else:
            sources.append({"name": name, "status": "registered_query_capable",
                             "note": "متصل حقيقي وقابل للاستدعاء الحي -- غير مُستدعى هنا لتفادي أي استدعاء شبكي حي عرضي من مسار قراءة سلبي؛ يُستدعى فعلياً فقط عبر مسارات البحث الحقيقية (go-deep-evidence وغيرها)"})
    return {"sources": sources, "total_registered": len(connectors)}


def _decision_memory_list():
    """Executive Decision Memory (ADR-145, 2026-07-30): the real unified
    recent-decision view across both real ledgers (niche decisions +
    Executive Directives), most recent first. Read-only, cheap (two real
    file reads + a merge-sort, no dashboard rebuild)."""
    import executive_decision_memory
    return executive_decision_memory.list_decision_memory()


def _decision_memory_conflicts():
    """Executive Decision Memory (ADR-145, 2026-07-30): real, mechanical
    conflict detection across the most recent Executive Directives --
    the same real niche recommended both 'accelerate' and 'stop' within
    the lookback window. Never a semantic/AI judgment. Read-only."""
    import executive_decision_memory
    return executive_decision_memory.detect_ledger_conflicts()


def _decision_memory_explain():
    """Executive Decision Memory (ADR-145, 2026-07-30): the real
    'explain why' function -- works for either a real niche Decision or
    a real Executive Directive, whichever real ledger actually carries
    the given decision_id. Reads its payload from sys.argv[2]:
    `python mission_control_api.py decision_memory_explain '{"decision_id":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    decision_id = (payload.get("decision_id") or "").strip()
    if not decision_id:
        raise ValueError("{ decision_id } is required")

    import executive_decision_memory
    return executive_decision_memory.explain_decision(decision_id)


def _capital_allocation_dashboard():
    """Capital Allocation Engine (2026-07-29): the real aggregator --
    Top ROI Initiatives, Projects Losing Value, Projects Consuming
    Resources Without Results, Resource Distribution, Expected Portfolio
    Return, and the real opportunity-cost pairings. Passthrough only --
    read-only, recommend-only; the Founder remains final authority on
    every real reallocation."""
    import capital_allocation_engine
    return capital_allocation_engine.build_capital_allocation_dashboard()


def _global_opportunity_exchange_dashboard():
    """Global Opportunity Exchange (2026-07-29): the real aggregator --
    Global Opportunity Map, Capital Flow Between Markets, Market Health/
    Saturation, Opportunity Ranking, Revenue Distribution, Market
    Dependency Index, and real diversification recommendations. Honestly
    DISCOVERY-heavy today (only 4 of 15 named marketplaces have a real
    channel arm, 0 real sale events exist, country dependency is a
    permanent structural DISCOVERY per CLAUDE.md's own founder-confirmed
    decision) -- never fabricated to look more built-out. Passthrough
    only; the Founder remains final authority on every real
    reallocation."""
    import global_opportunity_exchange
    return global_opportunity_exchange.build_global_opportunity_exchange_dashboard()


def _concentration_risk_report():
    """Global Opportunity Exchange (2026-07-29): the real 4 named
    concentration-risk checks (platform/product_family/country/
    ai_provider) on their own, without the full dashboard. Passthrough
    only."""
    import global_opportunity_exchange
    return global_opportunity_exchange.concentration_risk_report()


def _business_blueprint():
    """Autonomous Business Builder (2026-07-29): the real 12-section/
    8-estimate Business Blueprint for one niche -- reshapes business_
    dossier.py/production_blueprint.py/capital_allocation_engine.py's
    already-real output, never a second, competing blueprint generator.
    Reads its payload from sys.argv[2]:
    `python mission_control_api.py business_blueprint '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import autonomous_business_builder
    return autonomous_business_builder.business_blueprint(niche)


def _business_pipeline_summary():
    """Autonomous Business Builder (2026-07-29): "Business Pipeline"/
    "Blueprint Status" -- a thin citation of production_blueprint.py's
    already-real 6-bucket production missions board. Passthrough
    only."""
    import autonomous_business_builder
    return autonomous_business_builder.business_pipeline_summary()


def _execution_phases():
    """Autonomous Business Builder (2026-07-29): the real, company-wide
    5-phase execution roadmap (orchestrator.types.EXECUTION_ORDER),
    each phase's real engine health + a real, disclosed deterministic
    rollback plan. Passthrough only."""
    import autonomous_business_builder
    return autonomous_business_builder.execution_phases()


def _generate_pending_business_blueprints():
    """Final Executive Directive (2026-07-29): the real, capped, idempotent
    autonomous-generation step -- every real ACCEPTED decision without an
    already-recorded real Business Blueprint gets one, up to a small batch
    per call (each blueprint costs real compute, ~16s measured live).
    Read-only/no-execution, safe for factory_loop.js's daily tick. Reads
    an optional payload from sys.argv[2] for `limit`:
    `python mission_control_api.py generate_pending_business_blueprints '{"limit":2}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    limit = payload.get("limit", 2)

    import autonomous_business_builder
    return autonomous_business_builder.generate_pending_business_blueprints(limit=limit)


def _evolution_queue_daily_cycle():
    """Autonomous Company Evolution Engine, Round 4 (2026-07-29): the one
    automatic path the founder approved -- intake real proposals, simulate
    them, and decide (route to AWAITING_FOUNDER_APPROVAL). Never approves,
    rejects, or marks implemented -- those three stay exclusively
    founder-triggered Mission Control actions (see _evolution_queue below
    and the corresponding server.js routes)."""
    from tool_intelligence import proposals
    import evolution_queue
    return evolution_queue.run_daily_cycle(proposals=proposals.list_proposals())


def _evolution_queue():
    """Read-only Mission Control panel: the real Evolution Queue state --
    stage distribution, entries awaiting founder approval (with a stuck
    flag when one has sat unreviewed too long), and the full learning
    history. Passthrough only."""
    import evolution_queue
    return evolution_queue.list_evolution_queue()


def _approve_evolution_proposal():
    """The founder's own real approval -- the one concrete code enforcement
    of 'human-gated always' for Execute: no proposal, whatever its
    computed risk tier, reaches APPROVED without this real, explicit
    call. Reads its payload from sys.argv[2]:
    `python mission_control_api.py approve_evolution_proposal '{"proposal_id":"...","note":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    proposal_id = (payload.get("proposal_id") or "").strip()
    if not proposal_id:
        raise ValueError("{ proposal_id } is required")

    import evolution_queue
    return evolution_queue.approve_proposal(proposal_id, decided_by="founder", note=payload.get("note"))


def _reject_evolution_proposal():
    """The founder's own real rejection. Reads its payload from
    sys.argv[2]:
    `python mission_control_api.py reject_evolution_proposal '{"proposal_id":"...","reason":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    proposal_id = (payload.get("proposal_id") or "").strip()
    if not proposal_id:
        raise ValueError("{ proposal_id } is required")

    import evolution_queue
    return evolution_queue.reject_proposal(proposal_id, decided_by="founder", reason=payload.get("reason"))


def _evolution_outcome_daily_cycle():
    """Autonomous Evolution Engine directive, Round 2 (2026-07-30): the
    real automatic Measure path -- runs measure_outcome() for every real
    IMPLEMENTED proposal whose real elapsed time has crossed the real
    minimum window, honestly skipping (not silently) any still too new.
    Read-only against every decision field; only ever appends to a
    record's own outcome_measurements."""
    import evolution_queue
    return evolution_queue.run_daily_outcome_measurement_cycle()


def _evolution_measured_outcomes():
    """Read-only Mission Control panel: the real Measured Outcomes for
    every IMPLEMENTED proposal -- latest verdict plus the full real
    measurement trend. Passthrough only."""
    import evolution_queue
    return evolution_queue.list_measured_outcomes()


def _mark_evolution_proposal_implemented():
    """Closes the loop after a real, separately-reviewed Claude Code
    session has actually shipped an APPROVED proposal -- never called
    automatically. Reads its payload from sys.argv[2]:
    `python mission_control_api.py mark_evolution_proposal_implemented '{"proposal_id":"...","note":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    proposal_id = (payload.get("proposal_id") or "").strip()
    if not proposal_id:
        raise ValueError("{ proposal_id } is required")

    import evolution_queue
    return evolution_queue.mark_implemented(proposal_id, note=payload.get("note"))


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


def _knowledge_graph_daily_snapshot():
    """Final Executive Directive (2026-07-29): the real, genuinely-new
    daily tick step for "maintain institutional knowledge" -- builds the
    same real graph _knowledge_graph() above reads live, and persists it
    via knowledge_graph.build.save_snapshot() (already existed, never
    called from anywhere until now). Pure read of existing real data,
    zero side effects on any decision/production/publish state -- safe
    for factory_loop.js's daily tick."""
    from knowledge_graph import build
    graph = build.build_graph()
    path = build.save_snapshot(graph)
    return {"node_count": graph["node_count"], "edge_count": graph["edge_count"], "path": path}


def _department_health():
    """Department Health -- EOS Phase 2 (2026-07-19): pure assembly of
    already-computed real health signals per named department, zero new
    health computation. Passthrough only -- see department_health.py.

    Round 4 (2026-07-29) adds `weakness`: a real, honest classification
    (no_data / below_threshold / healthy) over the same report -- never a
    blended cross-department score, see department_health.rank_department_
    weakness()'s own docstring for why."""
    import department_health
    report = department_health.build_department_health()
    return {
        "report": report,
        "weakness": department_health.rank_department_weakness(report),
        "markdown": department_health.render_markdown(report),
    }


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


def _galaxy_evolution_report():
    """Company Evolution Protocol V1 (ADR-173, 2026-08-05): the real
    monthly Galaxy Evolution Report -- relabels/extends evolution_
    engine.build_evolution_report() (this same module, EOS Phase 1)
    onto the directive's 10 named sections, ROI-ranked via capital_
    allocation_engine.py's real top_roi_initiatives. Potential Monthly
    Revenue Impact and Estimated Implementation Effort are honestly
    NOT_MEASURABLE (zero real signal exists for either anywhere in this
    factory); Global Benchmark is honestly NOT_BUILT (no real external
    company-research pipeline exists). Passthrough only."""
    import evolution_engine
    report = evolution_engine.build_galaxy_evolution_report()
    return {"report": report, "markdown": evolution_engine.render_galaxy_evolution_report_markdown(report)}


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

    # Galaxy Operating System (ADR-172, 2026-08-05): the real weekly
    # self-governance report, reusing this already-real Sunday-gated
    # weekly export as its own delivery mechanism -- no new scheduling.
    import gfos
    ceo_md = gfos.render_if_i_were_the_ceo_markdown()

    combined_md = (
        f"# {title}\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        "---\n\n## Executive Summary\n\n" + executive_md +
        "\n\n---\n\n## If I Were The CEO\n\n" + ceo_md +
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
    combined_md, _revenue = _build_combined_executive_report_markdown("Galaxy Forge Executive Report")

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


def _get_value_profile():
    """Value Engine (2026-07-23): the real per-niche synthesis (Priority
    Score, Expected ROI, Strategic Value, cost/lifetime-value estimates,
    Recommendation, and all 17 requested dimensions). Honest null when
    this niche has no real ACCEPTED decision on record. Reads its
    payload from sys.argv[2]:
    `python mission_control_api.py get_value_profile '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")

    import value_engine
    return {"value_profile": value_engine.compute_value_profile(niche)}


def _get_value_engine_report():
    """Value Engine (2026-07-23): the real, whole-portfolio resource-
    allocation report — every real ACCEPTED opportunity, ranked by real
    Priority Score descending. No payload required:
    `python mission_control_api.py get_value_engine_report`"""
    import value_engine
    return value_engine.build_value_engine_report()


def _get_niche_commercial_profile():
    """Global Market Learning Engine (2026-07-23): the real Market Memory
    aggregate for one niche (sample size, total real revenue, average
    price, platforms, seasons). Honestly empty until real sales exist.
    `python mission_control_api.py get_niche_commercial_profile '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")
    import market_memory
    return {"commercial_profile": market_memory.niche_commercial_profile(niche)}


def _get_monthly_market_evolution_report():
    """Global Market Learning Engine (2026-07-23): the founder-named
    monthly report (top growing niches, best platforms, etc.), gated on
    a real minimum sample size — honestly reports insufficient data
    rather than a fabricated trend. No payload required."""
    import market_memory
    return market_memory.monthly_evolution_report()


def _get_commercial_recommendations():
    """Global Market Learning Engine (2026-07-23): evidence-gated
    autonomous recommendations (increase investment, review pricing).
    Emits nothing for a niche below the real evidence threshold — an
    empty list is the correct, honest output while real sales are
    scarce, not a bug. No payload required."""
    import market_memory
    return market_memory.recommend_actions()


def _get_growth_report():
    """Global Growth Engine (2026-07-24): the real Product Multiplication
    + Channel Expansion evaluation for one niche. Honest null when this
    niche has no real ACCEPTED decision on record. Reads its payload
    from sys.argv[2]:
    `python mission_control_api.py get_growth_report '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")
    import growth_engine
    return {"growth_report": growth_engine.build_growth_report(niche)}


def _get_channel_expansion_status():
    """Global Growth Engine (2026-07-24): the real, factory-wide (not
    niche-specific) channel readiness view across the 10 founder-named
    channels. No payload required."""
    import growth_engine
    return growth_engine.evaluate_channel_expansion()


def _get_commercial_intelligence_report():
    """Real World Commercial Expansion (2026-07-24): the real, unified
    Commercial Intelligence report for one niche (demand, willingness to
    pay, competition, price ranges, buying behavior, product
    opportunities, customer pain — regional_differences always honestly
    unavailable). Honest null when this niche has no real decision on
    record at all. Reads its payload from sys.argv[2]:
    `python mission_control_api.py get_commercial_intelligence_report '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")
    import commercial_intelligence
    return {"commercial_intelligence": commercial_intelligence.build_commercial_intelligence_report(niche)}


def _get_premium_product_catalog_status():
    """Real World Commercial Expansion, Priority 3 (2026-07-24): the
    real status of the 7 founder-named $100-$5000 premium categories
    against this factory's actual product_families adapters, plus the
    real, disclosed pricing-ceiling finding. No payload required."""
    import growth_engine
    return growth_engine.premium_product_catalog_status()


def _get_investment_pipeline_entry():
    """Global Revenue Discovery Engine (2026-07-24): the real, unified
    Investment Pipeline entry for one niche (10 ranking dimensions, 12
    named fields). Honest null when this niche has no real decision on
    record at all. Reads its payload from sys.argv[2]:
    `python mission_control_api.py get_investment_pipeline_entry '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")
    import investment_pipeline
    return {"investment_pipeline_entry": investment_pipeline.build_investment_pipeline_entry(niche)}


def _get_investment_pipeline():
    """Global Revenue Discovery Engine (2026-07-24): the real, whole-
    factory Investment Pipeline, ranked by real opportunity_score
    descending. Optional payload `{"limit": N}` — same real scale valve
    as get-global-execution-view. No payload required for the
    unlimited view."""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    limit = payload.get("limit")
    import investment_pipeline
    return investment_pipeline.build_investment_pipeline(limit=limit)


def _get_portfolio_entry():
    """Global Product Portfolio Engine (2026-07-24): the real, unified
    portfolio entry for one niche (13-class classification, NOW/NEXT/
    LATER/REJECT via scheduler.py reuse). Honest null when this niche
    has no real decision on record. Reads its payload from sys.argv[2]:
    `python mission_control_api.py get_portfolio_entry '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")
    import portfolio_engine
    return {"portfolio_entry": portfolio_engine.build_portfolio_entry(niche)}


def _get_portfolio_report():
    """Global Product Portfolio Engine (2026-07-24): the real,
    whole-factory portfolio report the Executive Board sees (Top 100
    worldwide, Top 25 enterprise, Top 25 recurring revenue; Top 50
    China always honestly empty — same deferred reason as every other
    China ask today). No payload required."""
    import portfolio_engine
    return portfolio_engine.build_portfolio_report()


def _get_production_blueprint():
    """Global Product Factory (2026-07-24): the real, unified 15-
    component Production Blueprint for one niche. Honest null when
    this niche has no real decision on record. Reads its payload from
    sys.argv[2]:
    `python mission_control_api.py get_production_blueprint '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")
    import production_blueprint
    return {"production_blueprint": production_blueprint.build_production_blueprint(niche)}


def _get_production_missions_board():
    """Global Product Factory (2026-07-24): Mission Control's real,
    continuous view — every real ACCEPTED opportunity bucketed under
    the 6 named production states (READY TO BUILD, BUILDING, QUALITY
    REVIEW, READY TO SELL, LIVE, LEARNING). No payload required."""
    import production_blueprint
    return production_blueprint.build_production_missions_board()


def _get_lifecycle_trace():
    """Complete Autonomous Company Master Loop (2026-07-24): the real,
    20-named-stage evidence trace for one niche — pure remap over
    already-real signals, zero new evidence computed. Honest null when
    this niche has no real decision on record. Reads its payload from
    sys.argv[2]:
    `python mission_control_api.py get_lifecycle_trace '{"niche":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    niche = (payload.get("niche") or "").strip()
    if not niche:
        raise ValueError("{ niche } is required")
    import master_loop
    return {"lifecycle_trace": master_loop.trace_lifecycle(niche)}


def _get_mission_control_heartbeat():
    """Complete Autonomous Company Master Loop (2026-07-24): the real,
    6-field heartbeat (Current Opportunity/Product/Stage/Revenue/
    Learning/Next Action) — thin reuse of scheduler.py, production_
    blueprint.py, and this module's own _revenue(). No payload
    required."""
    import master_loop
    return master_loop.mission_control_heartbeat()


def _get_company_reality_score():
    """Reality Mode (2026-07-24): the real, transparent Company Reality
    Score Mission Control must display — built entirely from real
    counts (real closed sales, real market evidence events, real
    cached competitor snapshots, real convened board meetings), never a
    fabricated single number. No payload required."""
    import reality_mode
    return reality_mode.compute_company_reality_score()


def _get_ceo_questions():
    """Global CEO Decision Center (2026-07-24): real, evidence-based
    answers to the 10 named CEO questions. No payload required."""
    import ceo_decision_center
    return ceo_decision_center.answer_ceo_questions()


def _get_capital_allocation_snapshot():
    """Global CEO Decision Center (2026-07-24): the real, descriptive
    snapshot of where real opportunities/evidence currently concentrate
    across the 10 named functions — never a fabricated dollar budget.
    No payload required."""
    import ceo_decision_center
    return ceo_decision_center.capital_allocation_snapshot()


def _get_ceo_dashboard():
    """Global CEO Decision Center (2026-07-24): the real 8-field CEO
    dashboard (Company Health, Capital Allocation, Growth Rate, Revenue
    Trend, Top Opportunities, Top Risks, Current Strategic Priority,
    Next Executive Decision). No payload required."""
    import ceo_decision_center
    return ceo_decision_center.ceo_dashboard()


def _get_weekly_progress_report():
    """Build in Public (2026-07-24): the real, honest-numbers-only
    weekly progress report. No payload required."""
    import build_in_public
    return build_in_public.build_weekly_progress_report()


def _draft_adr_post():
    """Build in Public (2026-07-24): a real AI-generated public post
    draft from one real ADR file — never auto-published, always
    returned for the caller to queue via queue-draft-for-approval.
    Reads its payload from sys.argv[2]:
    `python mission_control_api.py draft_adr_post '{"adr_path":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    adr_path = (payload.get("adr_path") or "").strip()
    if not adr_path:
        raise ValueError("{ adr_path } is required")
    import build_in_public
    return build_in_public.draft_adr_post(adr_path)


def _queue_draft_for_approval():
    """Build in Public (2026-07-24): writes a real draft to a real
    pending-review file and sends a real Arabic Telegram approval
    notification — never auto-publishes anything. Reads its payload
    from sys.argv[2]:
    `python mission_control_api.py queue_draft_for_approval '{"draft_type":"...","title":"...","content_markdown":"...","telegram_summary_arabic":"..."}'`"""
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    for field in ("draft_type", "title", "content_markdown", "telegram_summary_arabic"):
        if not (payload.get(field) or "").strip():
            raise ValueError(f"{{ {field} }} is required")
    import build_in_public
    return build_in_public.queue_draft_for_approval(
        payload["draft_type"], payload["title"], payload["content_markdown"], payload["telegram_summary_arabic"],
    )


def _get_global_execution_view():
    """Autonomous Global Execution Engine (2026-07-23): the single real
    operational window the founder named, assembled entirely from
    already-real, already-tested sources — never a second computation
    of anything shown elsewhere:
      - execution: execution_status.py's real per-opportunity status
      - scheduling: scheduler.py's real 5-bucket classification
        (on-demand only — this call does not execute anything, it only
        reports what the real evidence currently supports)
      - revenue / production: this module's own existing _revenue()/
        _production() actions, reused verbatim
      - market_learning / commercial_recommendations: market_memory.py
      - ai_utilization: ai_capability.registry.list_providers() (real
        measured usage) + orchestrator.resource_allocation_status()
        (real, zero-cost provider selection per named task category)

    Health and Security are deliberately NOT re-derived here — GET
    /health (lib/health_checks.js) and the existing risk-intelligence-
    scan/enterprise-readiness-gate Mission Control actions are already
    the real, live views for those; duplicating them here would be
    exactly the kind of second, competing computation this factory's
    own discipline refuses.

    Optional payload `{"limit": N}` (Autonomous Global Commercial
    Company Layer, 2026-07-24): forwarded to execution_status.py's own
    real scale valve (measured ~3s/opportunity today) so this Command
    Center view stays usable if the real accepted-opportunity count ever
    grows large — see value_engine.build_value_engine_report()'s
    docstring for the exact, honest tradeoff. `scheduling` intentionally
    stays unlimited: classification decisions must cover every real
    opportunity, never silently drop one from a bucket.

    Global Autonomous Business Operating System (2026-07-24) added:
      - portfolio_growth: growth_engine.py's real "Premium Products" /
        "AI Products" / "Automation Status" CEO-dashboard tally.
      - production_capacity: real historical throughput (never a
        forecast — this factory has no live worker pool to size).
      - growth_forecast: real and evidence-gated; honestly reports no
        forecast is computable while real sales evidence is this
        scarce, rather than projecting from nothing.
      - `commercial_recommendations` above already IS the real
        "Strategic Recommendations" the founder named — not duplicated
        under a second key.
    Deliberately NOT added: "Global Markets" / "China Division" — the
    same ADR-103 deferral reaffirmed twice already today (ADR-106,
    ADR-108); nothing has changed to unblock it. "Every completed
    commercial event automatically improves future decisions" (real
    scoring-weight auto-adjustment) — unchanged from ADR-109's own
    deliberate non-build, for the same real-risk reason."""
    import execution_status
    import scheduler
    import growth_engine
    import market_memory
    from ai_capability import registry as ai_registry
    from ai_capability import orchestrator as ai_orchestrator

    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    limit = payload.get("limit")

    return {
        "execution": execution_status.build_execution_status_report(limit=limit),
        "scheduling": scheduler.decide_next_actions(),
        "revenue": _revenue(),
        "production": _production(),
        "production_capacity": growth_engine.production_capacity_summary(),
        "market_learning": market_memory.monthly_evolution_report(),
        "commercial_recommendations": market_memory.recommend_actions(),
        "portfolio_growth": growth_engine.portfolio_growth_summary(),
        "growth_forecast": growth_engine.growth_forecast(),
        "ai_utilization": {
            "providers": ai_registry.list_providers(),
            "resource_allocation": ai_orchestrator.resource_allocation_status(),
        },
        "note": "Health -> GET /health. Security -> risk-intelligence-scan / enterprise-readiness-gate actions (not duplicated here). Global Markets/China Division deliberately deferred (ADR-103, reaffirmed ADR-106/108) -- see this action's own docstring.",
    }


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
    "evidence_network_status": _evidence_network_status,
    "evidence_coverage_status": _evidence_coverage_status,
    "customer_pipeline_status": _customer_pipeline_status,
    "advance_customer_pipeline": _advance_customer_pipeline,
    "check_customer_payments": _check_customer_payments,
    "customer_fulfillment_queue": _customer_fulfillment_queue,
    "customer_invoices": _customer_invoices,
    "executive_score": _executive_score,
    "tool_intelligence": _tool_intelligence,
    "strategic_report": _strategic_report,
    "market_review": _market_review,
    "evolution_report": _evolution_report,
    "galaxy_evolution_report": _galaxy_evolution_report,
    "founder_console": _founder_console,
    "integration_registry": _integration_registry,
    "ai_doctor": _ai_doctor,
    "research_department": _research_department,
    "department_health": _department_health,
    "knowledge_graph": _knowledge_graph,
    "knowledge_graph_daily_snapshot": _knowledge_graph_daily_snapshot,
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
    "get_value_profile": _get_value_profile,
    "get_value_engine_report": _get_value_engine_report,
    "get_niche_commercial_profile": _get_niche_commercial_profile,
    "get_monthly_market_evolution_report": _get_monthly_market_evolution_report,
    "get_commercial_recommendations": _get_commercial_recommendations,
    "get_global_execution_view": _get_global_execution_view,
    "get_growth_report": _get_growth_report,
    "get_channel_expansion_status": _get_channel_expansion_status,
    "get_commercial_intelligence_report": _get_commercial_intelligence_report,
    "get_premium_product_catalog_status": _get_premium_product_catalog_status,
    "get_investment_pipeline_entry": _get_investment_pipeline_entry,
    "get_investment_pipeline": _get_investment_pipeline,
    "get_portfolio_entry": _get_portfolio_entry,
    "get_portfolio_report": _get_portfolio_report,
    "get_production_blueprint": _get_production_blueprint,
    "get_production_missions_board": _get_production_missions_board,
    "get_lifecycle_trace": _get_lifecycle_trace,
    "get_mission_control_heartbeat": _get_mission_control_heartbeat,
    "get_company_reality_score": _get_company_reality_score,
    "get_ceo_questions": _get_ceo_questions,
    "get_capital_allocation_snapshot": _get_capital_allocation_snapshot,
    "get_ceo_dashboard": _get_ceo_dashboard,
    "get_weekly_progress_report": _get_weekly_progress_report,
    "draft_adr_post": _draft_adr_post,
    "queue_draft_for_approval": _queue_draft_for_approval,
    "run_master_cycle": _run_master_cycle,
    "generate_pending_business_blueprints": _generate_pending_business_blueprints,
    "evolution_queue_daily_cycle": _evolution_queue_daily_cycle,
    "evolution_queue": _evolution_queue,
    "approve_evolution_proposal": _approve_evolution_proposal,
    "reject_evolution_proposal": _reject_evolution_proposal,
    "mark_evolution_proposal_implemented": _mark_evolution_proposal_implemented,
    "evolution_outcome_daily_cycle": _evolution_outcome_daily_cycle,
    "evolution_measured_outcomes": _evolution_measured_outcomes,
    "publish_protection_status": _publish_protection_status,
    "publish_emergency_stop": _publish_emergency_stop,
    "publish_emergency_resume": _publish_emergency_resume,
    "safe_mode_status": _safe_mode_status,
    "mark_subsystem_unstable": _mark_subsystem_unstable,
    "clear_subsystem_unstable": _clear_subsystem_unstable,
    "approve_first_publish": _approve_first_publish,
    "approve_elevated_risk_publish": _approve_elevated_risk_publish,
    "autonomous_operations_status": _autonomous_operations_status,
    "resilience_status": _resilience_status,
    "resilience_incidents": _resilience_incidents,
    "resilience_monitor_tick": _resilience_monitor_tick,
    "executive_brief": _executive_brief,
    "strategic_score": _strategic_score,
    "convene_galaxy_council": _convene_galaxy_council,
    "record_council_recommendation": _record_council_recommendation,
    "council_learning_summary": _council_learning_summary,
    "investment_score": _investment_score,
    "opportunity_cost_report": _opportunity_cost_report,
    "executive_brain_directive": _executive_brain_directive,
    "generate_daily_executive_directive": _generate_daily_executive_directive,
    "executive_directives_history": _executive_directives_history,
    "gfos_status": _gfos_status,
    "engine_registry": _engine_registry,
    "if_i_were_the_ceo_report": _if_i_were_the_ceo_report,
    "gfos_enterprise_timeline": _gfos_enterprise_timeline,
    "affiliate_products": _affiliate_products,
    "affiliate_click": _affiliate_click,
    "affiliate_commerce_status": _affiliate_commerce_status,
    "affiliate_simulation_report": _affiliate_simulation_report,
    "launch_readiness_score": _launch_readiness_score,
    "executive_intelligence_questions": _executive_intelligence_questions,
    "company_pulse": _company_pulse,
    "dependency_matrix": _dependency_matrix,
    "executive_analytics": _executive_analytics,
    "unified_decision_engine": _unified_decision_engine,
    "executive_kpi_system": _executive_kpi_system,
    "enterprise_dependency_graph": _enterprise_dependency_graph,
    "enterprise_scheduler": _enterprise_scheduler,
    "executive_scenario_simulator": _executive_scenario_simulator,
    "executive_replay": _executive_replay,
    "autonomous_daily_cycle_status": _autonomous_daily_cycle_status,
    "company_state": _company_state,
    "market_intelligence_source_status": _market_intelligence_source_status,
    "decision_memory_list": _decision_memory_list,
    "decision_memory_conflicts": _decision_memory_conflicts,
    "decision_memory_explain": _decision_memory_explain,
    "capital_allocation_dashboard": _capital_allocation_dashboard,
    "global_opportunity_exchange_dashboard": _global_opportunity_exchange_dashboard,
    "concentration_risk_report": _concentration_risk_report,
    "business_blueprint": _business_blueprint,
    "business_pipeline_summary": _business_pipeline_summary,
    "execution_phases": _execution_phases,
    "growth_stage_status": _growth_stage_status,
    "simulate_growth_stage_progression": _simulate_growth_stage_progression,
    "strategic_planning_dashboard": _strategic_planning_dashboard,
    "simulate_roadmap_execution": _simulate_roadmap_execution,
    "record_daily_growth_stage_snapshot": _record_daily_growth_stage_snapshot,
    "truth_first_compliance": _truth_first_compliance,
    "digital_twin_dashboard": _digital_twin_dashboard,
    "preview_production_action": _preview_production_action,
    "evidence_coverage_report": _evidence_coverage_report,
    "evidence_viewer": _evidence_viewer,
    "executive_evidence_dashboard": _executive_evidence_dashboard,
    "automation_revenue_dashboard": _automation_revenue_dashboard,
    "market_domination_dashboard": _market_domination_dashboard,
    "enterprise_capital_allocation_dashboard": _enterprise_capital_allocation_dashboard,
    "capital_decisions_report": _capital_decisions_report,
    "truth_registry_report": _truth_registry_report,
    "brand_dna_report": _brand_dna_report,
    "goos_evaluate_opportunity": _goos_evaluate_opportunity,
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

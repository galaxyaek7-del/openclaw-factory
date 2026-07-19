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
    result = pipeline.run_revenue_pipeline()
    return {**result, "ceo_report_markdown": pipeline.render_ceo_revenue_report(result)}


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


def _build_combined_executive_report_markdown(title):
    """Concatenates four already-existing real report renderers —
    validation_layer's daily report, revenue_pipeline's CEO revenue
    report, and (Autonomous Digital Company v1, 2026-07-19)
    executive_intelligence's bottleneck/opportunity report and
    strategic_intelligence's decision-pattern/technical-debt report —
    into one markdown string. No new metric, no new business logic here
    — the two added reports were already real and tested (ADR-052/
    ADR-054) but only ever run as standalone CLI tools (`python -m
    executive_intelligence.report` / `python -m
    strategic_intelligence.report`).

    Shared by _export_executive_report() and _full_cycle()'s own
    executive_reports stage, which previously re-implemented this exact
    combination independently (found live, 2026-07-19) — one real
    report-building function now, not two competing copies."""
    from validation_layer import daily_report as dr
    from revenue_pipeline import pipeline as rp
    from executive_intelligence import report as exec_report
    from strategic_intelligence import report as strat_report

    validation = dr.generate_daily_report()
    validation_md = dr.render_markdown(validation)
    revenue = rp.run_revenue_pipeline()
    revenue_md = rp.render_ceo_revenue_report(revenue)
    executive = exec_report.generate_report()
    executive_md = exec_report.render_markdown(executive)
    strategic = strat_report.generate_strategic_report()
    strategic_md = strat_report.render_markdown(strategic)

    combined_md = (
        f"# {title}\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        "---\n\n## Executive Summary\n\n" + executive_md +
        "\n\n---\n\n## Strategic Recommendations\n\n" + strategic_md +
        "\n\n---\n\n## Validation\n\n" + validation_md +
        "\n\n---\n\n## Revenue\n\n" + revenue_md + "\n"
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
    "full_cycle": _full_cycle,
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Autonomous Business Builder (ABB) (2026-07-29) — "AUTONOMOUS BUSINESS
BUILDER" directive: a Business Blueprint per Founder-approved
opportunity, 8 named estimates, and a phased execution roadmap.

A research audit before writing any code found near-total overlap with
two already-real, already-wired modules: business_dossier.py (8 real
sections, deterministic template, zero LLM narrative -- already called
inside opportunity_pipeline.annotate_decision() for every real
opportunity, and already rendered live in mission_control.html's
renderBusinessDossier()) and production_blueprint.py (a real
15-component blueprint reusing business_dossier + value_engine +
growth_engine + ai_capability.orchestrator verbatim -- its own
docstring literally says "near-zero new computation"). This module's
real job is narrow: reshape those two into ABB's exact 12-section/
8-estimate shape, adding exactly 3 genuinely new citations (competitor
map, risk assessment, a phased execution roadmap) -- never a second,
competing blueprint generator.

Every function here is read-only/recommend-only. No autonomous
publishing, payments, or legal commitments -- this factory's universal
recommend-only discipline, already real everywhere an irreversible
action exists, is unchanged by this module."""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_GENERATED_BLUEPRINTS_PATH = _FACTORY_ROOT / "data" / "generated_business_blueprints.jsonl"

# orchestrator/types.py::EXECUTION_ORDER's 5 real stages, mapped onto
# the directive's phase shape. objectives/tasks/dependencies/success_
# metrics/rollback_plan below are real, deterministic descriptions of
# what this factory's own real pipeline modules actually do at each
# stage -- never a fabricated business task list this factory doesn't
# track. Modeled on business_dossier.py's own "deterministic template,
# zero LLM narrative" discipline.
_PHASE_TEMPLATE = {
    "market_intelligence": {
        "objectives": "اكتشاف وتقييم فرص حقيقية جديدة",
        "tasks": ["market_hunter.py::discover_and_score", "profit_oracle.py::opportunity_score"],
        "dependencies": [],
        "success_metrics": "قرار حقيقي واحد على الأقل مسجَّل (ACCEPTED/REJECTED/DEFERRED/RESEARCH_REQUIRED)",
        "rollback_plan": "لا نشر أو دفع حقيقي حدث بعد في هذه المرحلة -- لا حاجة لتراجع؛ نتيجتها الوحيدة قرار discovery حقيقي، قابل للمراجعة لاحقاً عبر decision_engine.",
    },
    "decision": {
        "objectives": "اعتماد قرار استثمار رسمي بناءً على أدلة حقيقية",
        "tasks": ["decision_engine.engine.evaluate_and_decide / record_ladder_decision"],
        "dependencies": ["market_intelligence"],
        "success_metrics": "status == ACCEPTED (decision_engine.types.STATUSES)",
        "rollback_plan": "قرار DEFERRED/RESEARCH_REQUIRED هو آلية التراجع الحقيقية الوحيدة -- decision_engine لا يحذف قراراً أبداً، السجل الكامل يبقى قابلاً للبحث (decision_engine/store.py::find_decisions_by_niche()).",
    },
    "production": {
        "objectives": "إنتاج منتج حقيقي يجتاز بوابة الجودة",
        "tasks": ["book_generator.py / production pipeline", "inspectors.py Dual Inspection"],
        "dependencies": ["decision"],
        "success_metrics": "Dual Inspection PASS حقيقي (inspectors.py::final_inspection())",
        "rollback_plan": "فشل حقيقي في Dual Inspection يوقف النشر ويُسجَّل في QUARANTINE.md عبر inspectors.py::_log_quarantine() -- لا نشر جزئي أبداً.",
    },
    "publishing": {
        "objectives": "توزيع حقيقي عبر قناة موزَّعة حقيقية",
        "tasks": ["distributor.py::distribute"],
        "dependencies": ["production"],
        "success_metrics": "نشر حقيقي ناجح مسجَّل في channels/ledger.py",
        "rollback_plan": "channels/publish_protection.py::trigger_emergency_stop() هو التراجع الحقيقي المتاح -- يوقف كل قناة فوراً، فعل بشري صريح فقط (Founder-gated).",
    },
    "learning": {
        "objectives": "مطابقة النتيجة الحقيقية مع القرار الأصلي",
        "tasks": ["decision_engine/feedback.py::sync_outcomes"],
        "dependencies": ["publishing"],
        "success_metrics": "نتيجة حقيقية مطابقة (Outcome.matched == True)",
        "rollback_plan": "لا تراجع مطلوب -- مرحلة تعلّم سلبية/رصدية فقط، لا تُغيّر أي قرار حي أو حالة نشر (data/decision_outcomes.jsonl إضافة فقط أبداً).",
    },
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def competitor_map(niche, decisions_path=None, board_path=None, alerts_path=None, reopen_log_path=None, profile=None):
    """New, tiny: assembles opportunity_pipeline.annotate_decision()'s
    real `competition` field + value_engine's real `competitive_moat`
    Strategic Investment Layer dimension into one named section --
    a citation of 2 already-real signals, never a new competitor-
    discovery engine.

    `profile` (optional): lets business_blueprint() below inject its
    own already-computed real value_engine.compute_value_profile()
    result instead of triggering a second, redundant real computation
    -- the same injection pattern capital_allocation_engine.py's
    opportunity_cost() already established. Omitting it (every
    standalone caller) computes it fresh here."""
    import factory_orchestrator as fo
    import opportunity_pipeline as op
    import value_engine

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return {"niche": niche, "answer": "Unknown", "reason": f"لا قرار حقيقي مسجَّل لـ'{niche}' بعد"}

    annotated = op.annotate_decision(decision, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path)
    competition = annotated.get("competition")

    if profile is None:
        profile = value_engine.compute_value_profile(niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path)
    moat = (profile.get("dimensions") or {}).get("competitive_moat") if profile else None

    return {
        "niche": niche,
        "competition_favorability": competition,
        "competitive_moat": moat,
        "generated_at": _now_iso(),
    }


def risk_assessment(niche, decisions_path=None, board_path=None, alerts_path=None, reopen_log_path=None, evidence_path=None, profile=None):
    """New, tiny: cites value_engine.compute_value_profile()'s real
    `at_risk` flag verbatim -- not currently surfaced in either
    business_dossier.py or production_blueprint.py.

    `profile` (optional): same injection pattern as competitor_map()
    above -- lets business_blueprint() avoid a second real
    compute_value_profile() call."""
    import value_engine

    if profile is None:
        profile = value_engine.compute_value_profile(
            niche, decisions_path=decisions_path, board_path=board_path,
            alerts_path=alerts_path, reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        )
    if profile is None:
        return {"niche": niche, "answer": "Unknown", "reason": f"لا قرار ACCEPTED حقيقي مسجَّل لـ'{niche}' بعد"}

    return {"niche": niche, "at_risk": profile.get("at_risk"), "generated_at": _now_iso()}


def execution_phases(cost_log_path=None):
    """Real, company-wide phased execution roadmap: orchestrator.types.
    EXECUTION_ORDER's 5 real pipeline stages, each with a real,
    deterministic objectives/tasks/dependencies/success_metrics/
    rollback_plan citation (never a fabricated business task this
    factory doesn't track), plus real per-stage health (executive_
    intelligence.engine_health.compute_engine_health(), already built)
    for "duration"/execution-progress. required_ai_models is cited
    once, company-wide (ai_capability.orchestrator.
    resource_allocation_status(), the same real source production_
    blueprint.py's own required_ai_models field already uses) -- this
    factory does not yet break AI-provider allocation down per
    pipeline stage, disclosed honestly rather than a fabricated
    per-phase split."""
    from orchestrator.types import EXECUTION_ORDER
    from executive_intelligence import engine_health as engine_health_module
    from ai_capability import orchestrator as ai_orchestrator

    health = engine_health_module.compute_engine_health()
    required_ai_models = ai_orchestrator.resource_allocation_status(cost_log_path=cost_log_path)

    phases = []
    for stage in EXECUTION_ORDER:
        template = _PHASE_TEMPLATE[stage]
        phases.append({
            "phase": stage,
            "objectives": template["objectives"],
            "tasks": template["tasks"],
            "dependencies": template["dependencies"],
            "success_metrics": template["success_metrics"],
            "rollback_plan": template["rollback_plan"],
            "real_engine_health": health.get(stage),
        })

    return {
        "phases": phases,
        "required_ai_models": required_ai_models,
        "required_ai_models_note": "مُستشهَد به على مستوى الشركة بأكملها -- لا تفصيل حقيقي لكل مرحلة على حدة موجود بعد",
        "generated_at": _now_iso(),
    }


def business_blueprint(niche, decisions_path=None, board_path=None, alerts_path=None,
                        reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """The aggregator: ABB's exact 12 named sections + 8 named
    estimates. Calls production_blueprint.build_production_blueprint()
    + value_engine.compute_value_profile() + capital_allocation_engine.
    investment_score() exactly once each -- never a second, competing
    blueprint generator, and never a redundant real compute_value_
    profile() call (threaded into competitor_map()/risk_assessment()
    via their own `profile` injection point). Returns None (never
    fabricated) when this niche has no real decision on record,
    matching both underlying blueprints' own convention."""
    import production_blueprint
    import capital_allocation_engine
    import value_engine
    import growth_engine

    blueprint = production_blueprint.build_production_blueprint(
        niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    if blueprint is None:
        return None

    profile = value_engine.compute_value_profile(
        niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    score = capital_allocation_engine.investment_score(
        niche, decisions_path=decisions_path, board_path=board_path,
        alerts_path=alerts_path, reopen_log_path=reopen_log_path, evidence_path=evidence_path,
    )
    competitor = competitor_map(niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path, profile=profile)
    risk = risk_assessment(niche, profile=profile)
    forecast = growth_engine.growth_forecast(evidence_path=evidence_path)

    board_summary = (profile or {}).get("board_summary") or {}

    sections = {
        "business_model": blueprint.get("unique_value_proposition"),
        "revenue_model": blueprint.get("revenue_projection"),
        "customer_profile": blueprint.get("customer_persona"),
        "competitor_map": competitor,
        "product_roadmap": {"specification": blueprint.get("product_specification"), "architecture": blueprint.get("product_architecture")},
        "pricing_strategy": blueprint.get("pricing_strategy"),
        "marketing_strategy": blueprint.get("marketing_assets"),
        "distribution_strategy": blueprint.get("distribution_channels"),
        "launch_checklist": blueprint.get("production_checklist"),
        "risk_assessment": risk,
        "growth_plan": blueprint.get("expansion_strategy"),
        "automation_plan": {
            "required_ai_models": blueprint.get("required_ai_models"),
            "automation_potential": score.get("automation_potential"),
        },
    }

    # 4 of 8 named estimates are real citations of already-built fields;
    # 4 (monthly/yearly revenue, break-even time, market durability) have
    # zero real signal anywhere in this factory (confirmed by repo-wide
    # grep before writing this function) -- honestly Unknown, never
    # invented from this factory's near-zero real sales history.
    forecast_value = (forecast.get("forecast") or {}).get("value")
    revenue_reason = forecast.get("reason") or (forecast.get("forecast") or {}).get("reason") or "لا نظام تنبّؤ إيراد حقيقي مبني بعد"
    estimates = {
        "development_effort": score.get("engineering_cost"),
        "expected_monthly_revenue": {
            "value": forecast_value if forecast_value is not None else "Unknown",
            "source": "growth_engine.growth_forecast()", "reason": revenue_reason,
        },
        "expected_yearly_revenue": {
            "value": "Unknown", "source": "growth_engine.growth_forecast()",
            "reason": "لا أفق تنبّؤ سنوي حقيقي مبني بعد -- يحتاج نافذتين زمنيتين حقيقيتين على الأقل (12 شهراً) للمقارنة",
        },
        "roi": board_summary.get("expected_roi") or {"maturity": "DISCOVERY", "reason": "لا قرار ACCEPTED حقيقي بعد لحساب عائد استثمار"},
        "break_even_time": {
            "value": "Unknown", "source": None,
            "reason": "لا بيانات مبيعات حقيقية كافية بعد لحساب زمن تعادل حقيقي",
        },
        "recurring_revenue_potential": score.get("recurring_revenue_potential"),
        "market_durability": {
            "value": "Unknown", "source": None,
            "reason": "لا نافذة مبيعات حقيقية كافية بعد لتقييم متانة السوق عبر الزمن",
        },
        "ai_automation_percentage": score.get("automation_potential"),
    }

    return {
        "niche": niche,
        "sections": sections,
        "estimates": estimates,
        "generated_at": _now_iso(),
    }


def business_pipeline_summary(decisions_path=None, board_path=None, alerts_path=None,
                               reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """ABB's "Business Pipeline"/"Blueprint Status" Mission Control ask
    -- a thin citation of production_blueprint.build_production_
    missions_board() verbatim, reframed under ABB's own naming. No new
    bucketing logic; the real 6 named production statuses (READY TO
    BUILD/BUILDING/QUALITY REVIEW/READY TO SELL/LIVE/LEARNING) already
    cover exactly this question."""
    import production_blueprint

    return production_blueprint.build_production_missions_board(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )


# ── Autonomous generation (Final Executive Directive, 2026-07-29) ──
# Real, capped, idempotent: every real ACCEPTED decision gets its real
# Business Blueprint generated exactly once, ever -- never regenerated
# on a later call. Append-only ledger, same convention as data/
# board_meetings.jsonl/data/incidents.jsonl. Read-only/no-execution --
# a blueprint is pure analysis, never a publish or spend, which is why
# this is safe to run automatically (factory_loop.js's tick) without
# touching any of the 4 Founder-protected gates.

def _read_generated_blueprint_niches(path=None):
    path = Path(path) if path else DEFAULT_GENERATED_BLUEPRINTS_PATH
    if not path.exists():
        return set()
    niches = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("niche"):
                niches.add(record["niche"])
    return niches


def _record_generated_blueprint(niche, decision_id, path=None):
    record = {"niche": niche, "decision_id": decision_id, "generated_at": _now_iso()}
    out_path = Path(path) if path else DEFAULT_GENERATED_BLUEPRINTS_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def generate_pending_business_blueprints(limit=2, decisions_path=None, board_path=None, alerts_path=None,
                                          reopen_log_path=None, evidence_path=None, timeline_path=None,
                                          outcomes_path=None, generated_path=None):
    """For every real ACCEPTED decision without an already-recorded
    real Business Blueprint, generates and records up to `limit` new
    ones this call -- bounding real cost per call (each blueprint costs
    real compute, ~16s measured live) regardless of how many real
    ACCEPTED decisions exist. Safe to call every real tick: the dedup
    check itself is cheap, and cost is only incurred for genuinely new,
    real ACCEPTED niches."""
    from decision_engine import ranking

    accepted = [d for d in ranking.rank_all(path=decisions_path) if d.get("status") == "ACCEPTED" and d.get("niche")]
    already_covered = _read_generated_blueprint_niches(generated_path)
    pending = [d for d in accepted if d["niche"] not in already_covered]

    generated = []
    for decision in pending[:max(0, limit)]:
        niche = decision["niche"]
        blueprint = business_blueprint(
            niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
        if blueprint is None:
            continue
        _record_generated_blueprint(niche, decision.get("decision_id"), generated_path)
        generated.append({"niche": niche, "decision_id": decision.get("decision_id")})

    return {
        "total_accepted": len(accepted),
        "generated": generated,
        "remaining_pending": max(0, len(pending) - len(generated)),
        "generated_at": _now_iso(),
    }

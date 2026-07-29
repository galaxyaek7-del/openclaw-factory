#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strategic Intelligence Core (2026-07-29) — Galaxy Forge's permanent
executive brain.

The founder's directive asks for a top-level decision layer answering
10 strategic questions, a named 11-dimension "Strategic Score," an
"Executive Brief" once per operational cycle, multi-year thinking, and
a Constitution-first compliance gate over everything.

A field-by-field research audit this session found most of this
already real and built, under different names, before this module
existed:

  - `ceo_decision_center.py::answer_ceo_questions()`/`ceo_dashboard()`
    already answer most of the 10 named questions.
  - `value_engine.py::compute_value_profile()`'s 17-dimension,
    WHY-explained `dimensions` dict already maps near-1:1 onto the
    requested 11 named Strategic Score dimensions.
  - `scheduler.py::decide_next_actions()` already produces real
    accelerate/stop/cancel/run_now/wait buckets ("products to
    accelerate/pause"), each with one documented evidence rule.
  - Markets to enter/abandon is already a founder-confirmed, explicitly
    deferred decision (CLAUDE.md's "التوسّع العالمي" section).
  - Constitution-first (`executive_quality_gate.py::
    check_constitution_alignment()`) and no-autonomous-high-risk-
    decisions (`evolution_queue.py`/`channels/publish_protection.py`/
    `safe_mode.py`, all already human-gated for anything irreversible)
    are both already real and already applied everywhere a real
    decision is made in this factory.

This module's real job is therefore narrow: (1) multi-year horizon
evaluation, genuinely absent anywhere before now; (2) a real citation
layer assembling the directive's named Strategic Score dimensions from
the sources above, never recomputing one; (3) the one real aggregator
this factory never had -- a single Executive Brief merging all of the
above into the directive's exact shape.

Every function here is READ-ONLY and RECOMMEND-ONLY. Nothing in this
module spends money, publishes anything, deletes data, or changes any
legal/payment/strategy setting -- matching the directive's own "no
autonomous high-risk decisions" rule, which this factory already
enforces structurally everywhere a real irreversible action exists.
"""

from datetime import datetime, timezone

# Multi-year thinking: 30/90-day horizons reuse growth_engine.py's own
# real DISCOVERY/REAL gate verbatim. 1/3/10-year horizons need a real
# elapsed sales-history span of at least 2 comparable windows of that
# length -- this factory (founded 2026-07-05) cannot possibly have real
# multi-year data yet, so these honestly report NOT ENOUGH EVIDENCE
# today by design, never a projected guess.
_LONG_HORIZONS_NEEDED_SPAN_DAYS = {
    "1_year": 365 * 2,
    "3_years": 365 * 3 * 2,
    "10_years": 365 * 10 * 2,
}

# Strategic Score: the directive's 11 named dimensions, each a real
# citation of an already-computed value from an already-real source --
# never a new scoring engine. "source_fn" documents where a caller
# would look to see the real, underlying computation.
_STRATEGIC_SCORE_SOURCES = {
    "market": "value_engine.compute_value_profile()'s global_demand dimension (opportunity_pipeline's market_signal)",
    "competition": "opportunity_pipeline.annotate_decision()'s competition field",
    "demand": "opportunity_pipeline.annotate_decision()'s pain_level field (real customer-pain-based demand signal)",
    "difficulty": "opportunity_pipeline.annotate_decision()'s technical_complexity field",
    "automation": "value_engine.compute_value_profile()'s automation_potential dimension",
    "scalability": "value_engine.compute_value_profile()'s scalability dimension",
    "recurring_revenue": "value_engine.compute_value_profile()'s recurring_revenue_potential dimension",
    "strategic_value": "value_engine.compute_value_profile()'s board_summary.strategic_value",
    "risk": "value_engine.compute_value_profile()'s at_risk assessment",
    "trust": "executive_score._trust()",
    "long_term_value": "value_engine.compute_value_profile()'s long_term_strategic_value dimension",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def evaluate_strategic_horizons(evidence_path=None, ledger_path=None, now=None):
    """Multi-year strategic thinking -- 5 named horizons (30 days/
    90 days/1 year/3 years/10 years), each independently, honestly
    gated. Never invents a projection; every horizon either cites a
    real value from growth_engine.py's own real forecast, or reports
    "NOT ENOUGH EVIDENCE" with the real reason (real elapsed sales-
    history span vs. what's actually needed)."""
    import growth_engine
    from channels import ledger as ledger_module

    horizons = {}

    short_forecast = growth_engine.growth_forecast(evidence_path=evidence_path)
    forecast_value = (short_forecast.get("forecast") or {}).get("value")
    for name in ("30_days", "90_days"):
        if short_forecast.get("maturity") == "REAL" and forecast_value is not None:
            horizons[name] = {"answer": forecast_value, "source": "growth_engine.growth_forecast()"}
        else:
            reason = short_forecast.get("reason") or (short_forecast.get("forecast") or {}).get("reason") or "لا اتجاه نمو حقيقي قابل للحساب بعد"
            horizons[name] = {"answer": "NOT ENOUGH EVIDENCE", "reason": reason, "source": "growth_engine.growth_forecast()"}

    trend = ledger_module.revenue_trend(now=now, ledger_path=ledger_path)
    by_day = trend.get("by_day") or {}
    if by_day:
        dates = sorted(by_day.keys())
        real_span_days = (datetime.strptime(dates[-1], "%Y-%m-%d") - datetime.strptime(dates[0], "%Y-%m-%d")).days
    else:
        real_span_days = 0

    for name, needed_span in _LONG_HORIZONS_NEEDED_SPAN_DAYS.items():
        if real_span_days >= needed_span:
            reason = (
                f"يوجد {real_span_days} يوماً من مبيعات حقيقية (يكفي شكلياً الحد المطلوب {needed_span} يوماً) "
                "لكن لا خوارزمية تنبّؤ حقيقية متعددة السنوات مبنية بعد -- لا تُخمَّن نتيجة بلا حساب حقيقي"
            )
        else:
            reason = f"يحتاج {needed_span} يوماً على الأقل من مبيعات حقيقية قابلة للمقارنة (نافذتان حقيقيتان) -- يوجد اليوم {real_span_days} يوماً فقط"
        horizons[name] = {
            "answer": "NOT ENOUGH EVIDENCE", "reason": reason,
            "real_span_days": real_span_days, "needed_span_days": needed_span,
        }

    return {"horizons": horizons, "real_span_days": real_span_days, "generated_at": _now_iso()}


def _extract_signal(raw, source):
    """Real dimension values in this factory arrive in several
    genuinely different, already-established shapes depending on which
    real function produced them (`{"value":...}` from executive_score/
    strategic-investment fields, `{"level":...}` from opportunity_
    pipeline's market_signal/ai_leverage/defensibility, `{"favorability_
    score":...}` from its competition field, `{"score":...}` from value_
    engine's strategic_value composite, a bare number for ladder-
    component fields, or `{"answer":"Unknown","reason":...}` wherever no
    real source function has a signal yet). Normalizes all of them into
    one `{value, source, reason}` shape without recomputing anything --
    a pure citation, never a new judgment."""
    if raw is None:
        return {"value": "Unknown", "source": source, "reason": "لا بيانات محفوظة لهذا القرار بعد"}
    if isinstance(raw, dict):
        if raw.get("answer") == "Unknown":
            return {"value": "Unknown", "source": source, "reason": raw.get("reason")}
        if "value" in raw:
            return {"value": raw.get("value"), "source": source, "reason": raw.get("note") or raw.get("reason")}
        if "level" in raw:
            return {"value": raw.get("level"), "source": source, "reason": raw.get("reason") or raw.get("note")}
        if "favorability_score" in raw:
            competitors = raw.get("real_competitors")
            reason = f"منافسون حقيقيون مسجَّلون: {competitors}" if competitors else None
            return {"value": raw.get("favorability_score"), "source": source, "reason": reason}
        if "score" in raw:
            return {"value": raw.get("score"), "source": source, "reason": raw.get("note")}
        return {"value": "Unknown", "source": source, "reason": f"شكل بيانات غير متوقع من المصدر الحقيقي: {sorted(raw.keys())}"}
    return {"value": raw, "source": source, "reason": None}


def strategic_score(niche, decisions_path=None, board_path=None, alerts_path=None,
                     reopen_log_path=None, inspections_log=None):
    """The directive's 11 named Strategic Score dimensions -- a real
    citation layer only. Pulls value_engine.compute_value_profile()'s
    real dimensions/board_summary/at_risk, opportunity_pipeline.
    annotate_decision()'s real per-decision fields (competition,
    pain_level, technical_complexity -- none of which value_engine
    re-exposes in its own `dimensions` dict), and executive_score's
    trust sub-score, and maps them onto the requested names; never
    recomputes a single one of them. Each dimension is `{value, source,
    reason}`, honestly `"Unknown"` (never fabricated) wherever the
    underlying real source has no signal yet for this niche, or where
    this niche has no real ACCEPTED decision on record at all."""
    import factory_orchestrator as fo
    import opportunity_pipeline as op
    import value_engine
    import executive_score

    dimension_keys = (
        "market", "competition", "demand", "difficulty", "automation", "scalability",
        "recurring_revenue", "strategic_value", "risk", "trust", "long_term_value",
    )

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        reason = f"لا قرار ACCEPTED حقيقي مسجَّل لـ '{niche}' بعد"
        return {
            "niche": niche,
            **{key: {"value": "Unknown", "source": _STRATEGIC_SCORE_SOURCES.get(key), "reason": reason} for key in dimension_keys},
            "generated_at": _now_iso(),
        }

    annotated = op.annotate_decision(decision, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path)
    profile = value_engine.compute_value_profile(
        niche, decisions_path=decisions_path, board_path=board_path,
        alerts_path=alerts_path, reopen_log_path=reopen_log_path,
    ) or {}
    dims = profile.get("dimensions") or {}
    board = profile.get("board_summary") or {}
    at_risk = profile.get("at_risk") or {}

    trust_sub_score = executive_score._trust(inspections_log)

    return {
        "niche": niche,
        "market": _extract_signal(dims.get("global_demand"), _STRATEGIC_SCORE_SOURCES["market"]),
        "competition": _extract_signal(annotated.get("competition"), _STRATEGIC_SCORE_SOURCES["competition"]),
        "demand": _extract_signal(annotated.get("pain_level"), _STRATEGIC_SCORE_SOURCES["demand"]),
        "difficulty": _extract_signal(annotated.get("technical_complexity"), _STRATEGIC_SCORE_SOURCES["difficulty"]),
        "automation": _extract_signal(dims.get("automation_potential"), _STRATEGIC_SCORE_SOURCES["automation"]),
        "scalability": _extract_signal(dims.get("scalability"), _STRATEGIC_SCORE_SOURCES["scalability"]),
        "recurring_revenue": _extract_signal(dims.get("recurring_revenue_potential"), _STRATEGIC_SCORE_SOURCES["recurring_revenue"]),
        "strategic_value": _extract_signal(board.get("strategic_value"), _STRATEGIC_SCORE_SOURCES["strategic_value"]),
        "risk": {
            "value": "at_risk" if at_risk.get("flagged") else "not_flagged",
            "source": _STRATEGIC_SCORE_SOURCES["risk"],
            "reason": "؛ ".join(at_risk.get("reasons") or []) or "لا إشارات خطر حوكمة حقيقية نشطة حالياً",
        },
        "trust": {
            "value": trust_sub_score.get("value", "Unknown"),
            "source": _STRATEGIC_SCORE_SOURCES["trust"],
            "reason": trust_sub_score.get("reason"),
        },
        "long_term_value": _extract_signal(dims.get("long_term_strategic_value"), _STRATEGIC_SCORE_SOURCES["long_term_value"]),
        "generated_at": _now_iso(),
    }


def build_executive_brief(decisions_path=None, board_path=None, alerts_path=None,
                           reopen_log_path=None, evidence_path=None, timeline_path=None,
                           outcomes_path=None, safe_mode_state_path=None,
                           publish_protection_state_path=None, requests_path=None,
                           pipeline_state_path=None, health_snapshots_path=None,
                           evolution_queue_state_path=None, sales_ledger_path=None,
                           capability_registry_path=None, customer_pipeline_state_path=None):
    """The Executive Brief -- the one real aggregator this factory never
    had. Every one of its 9 named fields cites an already-real function
    (resilience_monitor.assess_resilience(), ceo_decision_center.
    ceo_dashboard(), evolution_engine.build_evolution_report(),
    founder_console.build_founder_queue_partial(), this module's own
    evaluate_strategic_horizons(), customer_pipeline.
    customer_problem_cost_trend()) -- nothing here is a second,
    competing computation. Deliberately does NOT call scheduler.
    decide_next_actions() itself: ceo_dashboard() already computes it
    internally (a real, ~10s+ full-portfolio scan) and now additively
    exposes the full `scheduling_buckets` (2026-07-29) -- a second call
    here would silently double that real cost for zero new information.
    `research_needed` lists exactly the real NOT ENOUGH EVIDENCE gaps
    this cycle actually found; it is empty when every signal it checks
    is honestly resolved, never padded with an invented research
    topic."""
    import resilience_monitor
    import ceo_decision_center
    import evolution_engine
    import founder_console
    import customer_pipeline

    resilience = resilience_monitor.assess_resilience(
        safe_mode_state_path=safe_mode_state_path,
        publish_protection_state_path=publish_protection_state_path,
        requests_path=requests_path, pipeline_state_path=pipeline_state_path,
        health_snapshots_path=health_snapshots_path,
    )
    dashboard = ceo_decision_center.ceo_dashboard(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    evolution_report = evolution_engine.build_evolution_report(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
        sales_ledger_path=sales_ledger_path, capability_registry_path=capability_registry_path,
    )
    scheduling_buckets = dashboard["scheduling_buckets"]
    founder_queue = founder_console.build_founder_queue_partial(
        decisions_path=decisions_path, evolution_queue_state_path=evolution_queue_state_path,
        publish_protection_state_path=publish_protection_state_path,
    )
    horizons = evaluate_strategic_horizons(evidence_path=evidence_path)
    cost_trend = customer_pipeline.customer_problem_cost_trend(state_path=customer_pipeline_state_path)

    research_needed = []
    for name, horizon in horizons["horizons"].items():
        if horizon.get("answer") == "NOT ENOUGH EVIDENCE":
            research_needed.append({"topic": f"أفق {name}", "reason": horizon.get("reason")})
    if cost_trend.get("answer") == "NOT ENOUGH EVIDENCE":
        research_needed.append({"topic": "اتجاه تكلفة مشاكل العملاء", "reason": cost_trend.get("reason")})

    return {
        "company_health": {
            "resilience_score": resilience["resilience_score"],
            "resilience_score_note": resilience["resilience_score_note"],
            "active_alerts_count": len(resilience["active_alerts"]),
        },
        "top_risks": {
            **dashboard["top_risks"],
            "resilience_active_alerts": resilience["active_alerts"],
        },
        "top_opportunities": dashboard["top_opportunities"],
        "top_bottlenecks": {
            "bottlenecks": evolution_report["bottlenecks"],
            "customer_success_bottleneck": evolution_report["customer_success_bottleneck"],
        },
        "recommended_priorities": {
            "current_strategic_priority": dashboard["current_strategic_priority"],
            "next_executive_decision": dashboard["next_executive_decision"],
        },
        "products_to_accelerate": scheduling_buckets["accelerate"],
        "products_to_pause": scheduling_buckets["stop"],
        "research_needed": research_needed,
        "founder_decisions_required": {
            "pending_decisions": founder_queue["pending_decisions"],
            "pending_evolution_proposals": founder_queue["pending_evolution_proposals"],
            "publish_emergency_stop": founder_queue["publish_emergency_stop"],
        },
        "generated_at": _now_iso(),
    }


def render_markdown(brief):
    """Deterministic, mechanical rendering of an already-built Executive
    Brief -- same convention as evolution_engine.py/ai_doctor.py's own
    render_markdown(): every line is a direct read of a real field
    above, never freely-generated text."""
    lines = []

    lines.append("## الصحة العامة للشركة")
    health = brief["company_health"]
    lines.append(f"- Resilience Score: {health['resilience_score']} ({health['active_alerts_count']} تنبيه نشط)")
    lines.append(f"- {health['resilience_score_note']}")

    lines.append("\n## أكبر المخاطر")
    risks = brief["top_risks"]
    for n in risks.get("stop", []):
        lines.append(f"- إيقاف مؤقّت: {n['niche']} — {n['reason']}")
    for n in risks.get("cancel", []):
        lines.append(f"- إلغاء: {n['niche']} — {n['reason']}")
    for a in risks.get("resilience_active_alerts", []):
        lines.append(f"- {a['area']} [{a['severity']}]: {a.get('detail')}")

    lines.append("\n## أكبر الفرص")
    for o in brief.get("top_opportunities") or []:
        lines.append(f"- {o.get('niche')}")

    lines.append("\n## أكبر الاختناقات")
    bottlenecks = brief["top_bottlenecks"]["bottlenecks"]
    if bottlenecks.get("detected"):
        for b in bottlenecks["items"]:
            lines.append(f"- {b['evidence']}")
    else:
        lines.append(f"- {bottlenecks.get('reason')}")
    customer_bottleneck = brief["top_bottlenecks"]["customer_success_bottleneck"]
    if customer_bottleneck.get("detected"):
        lines.append(f"- (نجاح العميل) {customer_bottleneck.get('summary')}")
    else:
        lines.append(f"- (نجاح العميل) {customer_bottleneck.get('reason')}")

    lines.append("\n## الأولويات الموصى بها")
    priorities = brief["recommended_priorities"]
    if priorities.get("current_strategic_priority"):
        lines.append(f"- الأولوية الحالية: {priorities['current_strategic_priority'].get('niche')}")
    if priorities.get("next_executive_decision"):
        lines.append(f"- القرار التنفيذي التالي: {priorities['next_executive_decision'].get('niche')}")

    lines.append("\n## منتجات للتسريع")
    for p in brief.get("products_to_accelerate") or []:
        lines.append(f"- {p['niche']}: {p['reason']}")

    lines.append("\n## منتجات للإيقاف المؤقّت")
    for p in brief.get("products_to_pause") or []:
        lines.append(f"- {p['niche']}: {p['reason']}")

    lines.append("\n## أبحاث مطلوبة (لا أدلة كافية بعد)")
    if brief.get("research_needed"):
        for r in brief["research_needed"]:
            lines.append(f"- {r['topic']}: {r['reason']}")
    else:
        lines.append("- لا فجوة أدلة حقيقية مكتشَفة هذه الدورة")

    lines.append("\n## قرارات تحتاج قراراً من المؤسس")
    founder = brief["founder_decisions_required"]
    lines.append(f"- {len(founder['pending_decisions'])} قرار DEFERRED بانتظار مراجعة")
    lines.append(f"- {len(founder['pending_evolution_proposals'])} اقتراح تطوّر بانتظار موافقة")
    if founder.get("publish_emergency_stop"):
        lines.append(f"- إيقاف طوارئ نشر نشط: {founder['publish_emergency_stop']}")

    return "\n".join(lines) + "\n"

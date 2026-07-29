#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Council (2026-07-29) — "THE UNIFIED EXECUTIVE BOARD" directive.

Ten named members, each producing {opinion, confidence, evidence, risk,
recommendation, founder_approval_required}. Same founding discipline as
executive_board.py (already this factory's real precedent for this exact
problem, built 2026-07-22): every field here is a real CITATION of an
already-computed, already-real signal elsewhere in this factory --
never a free-form generated "opinion." Nothing here calls an LLM.

The Council answers a different question than the Executive Board:
"what does each intelligence domain currently believe about this niche,
laid out honestly side by side" (Council) vs. "should we approve this
one already-evaluated decision" (Board, `executive_board.py`). Both
stay -- deliberately distinct bodies, see ADR-138.

Nine of the ten directive-named members are real signal PRODUCERS,
normalized here into the 6-field shape. The tenth, Mission Control, is
the display venue for the other nine -- it has no analytical opinion of
its own the way the other 9 do, so it is deliberately NOT given a
fabricated 10th vote here (see `convene_council()`'s own docstring).

Four members (Customer, Security, Resilience, Innovation) are
structurally company-wide-only today -- no niche field exists anywhere
in their real underlying data models. `convene_council()` still calls
them every time, tagged `scope: "company_wide"`, never silently
skipped and never forced to fake a per-niche answer they don't have.

`stance` (proceed/hold/stop/no_data/informational_context) is set ONLY
where a member's real source already emits something genuinely
comparable to a go/no-go signal -- forcing every member onto one
synthetic scale would itself be a fabricated consensus. See
`convene_council()` for how disagreement across members is detected
from these stances, never averaged away.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

STANCES = ("proceed", "hold", "stop", "no_data", "informational_context")

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_COUNCIL_RECOMMENDATIONS_PATH = _FACTORY_ROOT / "data" / "council_recommendations.jsonl"


def _result(member, opinion, confidence, evidence, risk, recommendation,
            founder_approval_required, stance="informational_context", scope="niche", raw=None):
    """`raw` (optional): the member's own already-computed real source
    object, attached verbatim -- lets convene_council() cite a specific
    sub-field (e.g. Strategic's own strategic_value/long_term_value, for
    the directive's "Expected Impact"/"Long-term Effect" fields) without
    a second, redundant call to the same real source. Additive only --
    never required, never changes the 8 base fields above."""
    if stance not in STANCES:
        raise ValueError(f"stance must be one of {STANCES}, got {stance!r}")
    return {
        "member": member,
        "opinion": opinion,
        "confidence": confidence,
        "evidence": evidence,
        "risk": risk,
        "recommendation": recommendation,
        "founder_approval_required": founder_approval_required,
        "stance": stance,
        "scope": scope,
        "raw": raw,
    }


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── 1. Strategic Intelligence Core ──

def _member_strategic(niche, decisions_path=None):
    """Cites strategic_intelligence_core.strategic_score(niche) verbatim
    -- an already-real 11-dimension citation layer, never recomputed."""
    import strategic_intelligence_core as sic

    score = sic.strategic_score(niche, decisions_path=decisions_path)
    dims = {k: v for k, v in score.items() if isinstance(v, dict) and "value" in v}
    known = {k: v for k, v in dims.items() if v.get("value") != "Unknown"}
    confidence = round(len(known) / len(dims), 2) if dims else 0.0

    risk_dim = score.get("risk") or {}
    stance = "hold" if risk_dim.get("value") == "at_risk" else "informational_context"

    opinion = (
        f"تقييم استراتيجي حقيقي عبر {len(known)}/{len(dims)} بُعد معروف: "
        + "؛ ".join(f"{k}={v['value']}" for k, v in known.items())
    ) if known else "لا أبعاد استراتيجية حقيقية معروفة لهذا النيتش بعد"
    evidence = [f"{k}: {v.get('source')}" for k, v in dims.items()]
    risk = f"{risk_dim.get('value', 'Unknown')} — {risk_dim.get('reason') or 'لا سبب مسجَّل'}"
    recommendation = (
        "مراجعة المخاطر الاستراتيجية قبل الاستمرار" if stance == "hold"
        else ("استمر — لا إشارة خطر استراتيجي حقيقية نشطة" if known else "اجمع أدلة استراتيجية حقيقية أولاً")
    )
    return _result(
        "Strategic Intelligence Core", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=(stance == "hold"), stance=stance, scope="niche", raw=score,
    )


# ── 2. Market Intelligence ──

def _member_market(niche, alerts_path=None, db_file=None):
    """Cites competitor_discovery.py's real CACHED snapshot (never a live
    network call, same discipline as ceo_decision_center.py's own
    _market_saturation_and_strength()) + market_alerts.get_active_alerts()
    verbatim."""
    import competitor_discovery as cd
    import market_alerts

    db = cd.load_database(db_file=db_file)
    snapshot = db.get(cd._normalize_key(niche))
    if snapshot:
        threat = cd.compute_threat_assessment(snapshot)
        real_dims = {k: v for k, v in threat.items() if k != "computed_at" and isinstance(v, dict) and v.get("level") != "Unknown"}
        unknown_dims = {k: v for k, v in threat.items() if k != "computed_at" and isinstance(v, dict) and v.get("level") == "Unknown"}
        threat_confidence = round(len(real_dims) / (len(real_dims) + len(unknown_dims)), 2) if (real_dims or unknown_dims) else 0.0
    else:
        threat, real_dims, unknown_dims, threat_confidence = None, {}, {}, 0.0

    alerts = market_alerts.get_active_alerts(niche, alerts_path=alerts_path)
    critical_count = alerts["by_severity_counts"].get("Critical", 0)
    high_count = alerts["by_severity_counts"].get("High", 0)

    if not snapshot and alerts["total"] == 0:
        stance, confidence = "informational_context", 0.0
        opinion = "لا مسح منافسين حقيقي ولا تنبيهات سوق حقيقية لهذا النيتش بعد"
    elif critical_count or high_count:
        stance, confidence = "hold", threat_confidence
        opinion = f"{critical_count} تنبيه حرج (Critical) و{high_count} تنبيه عالٍ (High) نشط حقيقي لهذا النيتش"
    else:
        stance, confidence = "proceed", threat_confidence
        opinion = (
            f"تقييم تهديد حقيقي عبر {len(real_dims)}/{len(real_dims) + len(unknown_dims)} بُعد معروف، لا تنبيهات حرجة/عالية نشطة"
            if snapshot else f"{alerts['total']} تنبيه سوق حقيقي نشط، لا تصنيف حرج/عالٍ"
        )

    evidence = [f"{k}: {v['basis']}" for k, v in real_dims.items()] + [f"alert: {a['event_type']} ({a['severity']})" for a in alerts["alerts"]]
    risk = (
        f"{critical_count + high_count} تنبيه سوق حرج/عالٍ نشط" if (critical_count or high_count)
        else "لا مخاطر سوق حقيقية نشطة معروفة"
    )
    recommendation = (
        "راجع تنبيهات السوق الحرجة/العالية قبل الاستمرار" if stance == "hold"
        else ("استمر — لا تهديد سوق حقيقي نشط" if stance == "proceed" else "شغّل مسح منافسين حقيقي أولاً")
    )
    return _result(
        "Market Intelligence", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=bool(critical_count), stance=stance, scope="niche",
    )


# ── 3. Production Intelligence ──

def _latest_inspection_for_niche(niche, inspections_log=None):
    """New (2026-07-29), tiny, mechanical reader over inspectors.py's own
    already-real per-line inspections.log ({passed, technical, commercial,
    niche, timestamp}) -- inspectors.py itself has no exported function
    to read this back filtered by niche; this is a citation of that log,
    never a new inspection engine."""
    from inspectors import INSPECTIONS_LOG

    path = inspections_log or INSPECTIONS_LOG
    if not os.path.exists(path):
        return None
    matches = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("niche") == niche:
                matches.append(entry)
    return matches[-1] if matches else None


def _member_production(niche, timeline_path=None, inspections_log=None):
    """Cites inspectors.py's real Dual Inspection gate (via the new
    _latest_inspection_for_niche() reader above) + executive_intelligence.
    engine_health.compute_engine_health() verbatim -- company-wide engine
    maturity as supporting context, never recomputed."""
    from executive_intelligence import engine_health as engine_health_module

    inspection = _latest_inspection_for_niche(niche, inspections_log=inspections_log)
    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    real_engines = {k: v for k, v in health.items() if v.get("maturity") == "REAL"}

    if inspection:
        stance = "proceed" if inspection.get("passed") else "stop"
        confidence = 1.0
        opinion = f"آخر فحص إنتاج حقيقي (Dual Inspection) لهذا النيتش: {'ناجح' if inspection.get('passed') else 'فاشل'} بتاريخ {inspection.get('timestamp')}"
        failures = list((inspection.get("technical") or {}).get("failures") or []) + list((inspection.get("commercial") or {}).get("failures") or [])
        risk = "؛ ".join(failures) if failures else "لا مخاطر فنية/تجارية حقيقية نشطة"
    else:
        stance, confidence = "no_data", 0.0
        opinion = "لا فحص إنتاج حقيقي (Dual Inspection) مسجَّل لهذا النيتش بعد"
        risk = "غير معروف — لا بيانات فحص حقيقية"

    evidence = [f"{len(real_engines)}/{len(health)} محرّك حقيقي (REAL maturity) في data/orchestrator_timeline.jsonl"]
    recommendation = (
        "استمر — فحص إنتاج حقيقي ناجح" if stance == "proceed"
        else ("أوقف — فشل فحص إنتاج حقيقي" if stance == "stop" else "شغّل فحص إنتاج حقيقي (Dual Inspection) أولاً")
    )
    return _result(
        "Production Intelligence", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=(stance == "stop"), stance=stance, scope="niche",
    )


# ── 4. Customer Intelligence (company-wide only — no niche field exists in customer request records) ──

def _member_customer(state_path=None):
    """Cites customer_pipeline.py's 3 real Observe signals verbatim --
    company-wide only, no per-niche field exists in this factory's real
    customer request schema."""
    import customer_pipeline as cp

    funnel = cp.funnel_conversion_summary(state_path=state_path)
    delay = cp.delivery_delay_summary(state_path=state_path)
    cost_trend = cp.customer_problem_cost_trend(state_path=state_path)

    known = [s for s in (funnel, delay, cost_trend) if s.get("answer") != "Unknown" and "answer" not in s]
    confidence = round(len(known) / 3, 2)

    worsening = cost_trend.get("worsening")
    opinion_parts = []
    if funnel.get("total_requests") is not None:
        opinion_parts.append(f"{funnel['total_requests']} طلب عميل حقيقي مسجَّل")
    if delay.get("average_hours") is not None:
        opinion_parts.append(f"متوسط تسليم حقيقي {delay['average_hours']} ساعة")
    if worsening is not None:
        opinion_parts.append(f"اتجاه مشاكل العملاء: {'يتفاقم' if worsening else 'مستقر/يتحسّن'}")
    opinion = "؛ ".join(opinion_parts) if opinion_parts else "لا بيانات عملاء حقيقية كافية بعد"

    evidence = [
        f"funnel: {funnel.get('reason', 'بيانات قمع تحويل حقيقية متاحة')}",
        f"delivery: {delay.get('reason', 'بيانات تأخير تسليم حقيقية متاحة')}",
        f"cost_trend: {cost_trend.get('reason', 'اتجاه تكلفة حقيقي متاح')}",
    ]
    risk = "اتجاه حقيقي متفاقم في مشاكل العملاء" if worsening else "لا اتجاه تفاقم حقيقي نشط معروف"
    recommendation = (
        "راجع مشاكل العملاء المتفاقمة" if worsening else "لا إجراء عاجل — لا اتجاه سلبي حقيقي نشط"
    )
    return _result(
        "Customer Intelligence", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=bool(worsening), stance="informational_context", scope="company_wide",
    )


# ── 5. Financial Intelligence ──

def _member_financial(niche, tier="tier4", external_signal=None, ledger_path=None):
    """Cites profit_oracle.opportunity_score(niche) + channels.ledger.
    revenue_trend() verbatim -- components_basis's real/estimated tagging
    (Human Trust, Global Trust & Resilience Layer Round 5) is surfaced
    as-is, never blended away."""
    import profit_oracle
    from channels import ledger

    score = profit_oracle.opportunity_score(niche, tier=tier, external_signal=external_signal)
    trend = ledger.revenue_trend(ledger_path=ledger_path)

    basis = score.get("components_basis") or {}
    real_components = [k for k, v in basis.items() if v == "real"]
    confidence = round(len(real_components) / len(basis), 2) if basis else 0.0

    stance = "proceed" if score.get("accepted") else "hold"
    opinion = f"درجة فرصة حقيقية {score['opportunity_score']}/100 (الحد الأدنى {score['min_required']}) — {'تجاوز الحد' if score.get('accepted') else 'دون الحد'}"
    evidence = [f"{k}: {v} ({basis.get(k, 'estimated')})" for k, v in (score.get("components") or {}).items()]
    evidence.append(f"إيراد حقيقي آخر 7 أيام: ${trend.get('recent_7d_revenue_usd', 0)}")
    risk = "دون الحد الأدنى الحقيقي للفرصة" if not score.get("accepted") else "لا مخاطر مالية حقيقية نشطة معروفة"
    recommendation = "استمر — تجاوز الحد الأدنى الحقيقي" if stance == "proceed" else "لا تستثمر أكثر — دون الحد الأدنى الحقيقي حالياً"
    return _result(
        "Financial Intelligence", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=(stance == "hold"), stance=stance, scope="niche", raw=score,
    )


# ── 6. Security Intelligence (company-wide only) ──

def _member_security(niche, decisions_path=None):
    """Cites executive_quality_gate.py's Global Policy Engine checks
    (both honestly UNKNOWN-by-design where this factory has no real
    check yet) + ai_doctor.py's real dependency-pinning drift verbatim.
    Never a hold/stop stance -- both real sources are informational-only
    by their own docstrings."""
    import factory_orchestrator as fo
    import executive_quality_gate as eqg
    import ai_doctor

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    constitution = eqg.check_constitution_alignment(decision)
    tos = eqg.check_platform_tos_awareness(None)
    python_pinning = ai_doctor._check_python_pinning()
    node_pinning = ai_doctor._check_node_pinning()

    total_pinned = python_pinning.get("pinned", 0) + node_pinning.get("pinned", 0)
    total_checked = python_pinning.get("checked", 0) + node_pinning.get("checked", 0)
    pinning_ratio = round(total_pinned / total_checked, 2) if total_checked else None

    confidence = 1.0 if constitution.get("answer") != "Unknown" else 0.5

    opinion = (
        f"{constitution.get('reason', constitution.get('answer'))}؛ "
        f"نسبة تثبيت حقيقية للاعتمادية: {total_pinned}/{total_checked}" if total_checked
        else constitution.get("reason", constitution.get("answer"))
    )
    evidence = [
        f"constitution_alignment: {constitution.get('reason') or constitution.get('answer')}",
        f"platform_tos_awareness: {tos.get('reason')}",
        f"python_pinning: {python_pinning.get('pinned')}/{python_pinning.get('checked')}",
        f"node_pinning: {node_pinning.get('pinned')}/{node_pinning.get('checked')}",
    ]
    risk = (
        f"{total_checked - total_pinned} اعتمادية غير مثبَّتة حقيقياً" if (total_checked and total_pinned < total_checked)
        else "لا مخاطر أمنية حقيقية نشطة معروفة"
    )
    recommendation = "راجع الاعتماديات غير المثبَّتة" if (pinning_ratio is not None and pinning_ratio < 1.0) else "لا إجراء عاجل"
    return _result(
        "Security Intelligence", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=False, stance="informational_context", scope="company_wide",
    )


# ── 7. Resilience Intelligence (company-wide only) ──

def _member_resilience(**kwargs):
    """Cites resilience_monitor.assess_resilience() verbatim -- an
    already near-verbatim fit (4-tier severity + evidence + a
    transparent score)."""
    import resilience_monitor

    assessment = resilience_monitor.assess_resilience(**kwargs)
    score = assessment.get("resilience_score")
    active_alerts = assessment.get("active_alerts") or []
    critical_or_emergency = [a for a in active_alerts if a.get("severity") in ("critical", "emergency")]

    confidence = round(score / 100, 2) if isinstance(score, (int, float)) else 0.0
    opinion = f"Resilience Score حقيقي: {score} — {len(active_alerts)} تنبيه نشط، {len(critical_or_emergency)} حرج/طارئ"
    evidence = [f"{a['area']} [{a['severity']}]: {a.get('detail')}" for a in active_alerts]
    risk = (
        "؛ ".join(f"{a['area']}: {a.get('detail')}" for a in critical_or_emergency) if critical_or_emergency
        else "لا نتائج حرجة/طارئة حقيقية نشطة"
    )
    recommendation = "راجع النتائج الحرجة/الطارئة فوراً" if critical_or_emergency else "لا إجراء عاجل"
    return _result(
        "Resilience Intelligence", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=bool(critical_or_emergency), stance="informational_context", scope="company_wide",
    )


# ── 8. Innovation Intelligence (company-wide only) ──

def _member_innovation(decisions_path=None, outcomes_path=None, timeline_path=None):
    """Cites evolution_engine.build_evolution_report() + tool_intelligence.
    proposals.list_proposals() verbatim."""
    import evolution_engine
    from tool_intelligence import proposals as tool_proposals

    report = evolution_engine.build_evolution_report(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
    )
    proposals = tool_proposals.list_proposals()

    bottlenecks = report.get("bottlenecks") or {}
    detected = bottlenecks.get("detected", False)
    confidence = 1.0 if "reason" not in bottlenecks or detected else 0.5

    opinion = (
        f"{len(bottlenecks.get('items', []))} اختناق حقيقي مكتشَف، {len(proposals)} اقتراح أداة حقيقي بانتظار المراجعة"
        if detected else (bottlenecks.get("reason") or "لا اختناقات حقيقية مكتشَفة هذه الدورة")
    )
    evidence = [f"bottleneck: {b['evidence']}" for b in bottlenecks.get("items", [])] + [f"proposal: {p['tool']}" for p in proposals]
    risk = "؛ ".join(b["evidence"] for b in bottlenecks.get("items", [])) if detected else "لا مخاطر ابتكار حقيقية نشطة معروفة"
    recommendation = "راجع الاختناقات والاقتراحات الحقيقية بانتظار موافقة المؤسس" if (detected or proposals) else "لا إجراء عاجل"
    return _result(
        "Innovation Intelligence", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=False, stance="informational_context", scope="company_wide",
    )


# ── 9. Executive Memory ──

def _member_executive_memory(niche, decisions_path=None, outcomes_path=None):
    """Cites this niche's own real decision history (decision_engine.
    store.find_decisions_by_niche()) -- alternatives_rejected/
    expected_outcome (Decision Memory, Global Trust & Resilience Layer
    Round 6) -- + any real matched Outcome (decision_engine.store.
    read_outcomes(), joined by decision_id) verbatim. Institutional
    memory's real opinion: what does this factory already know about
    this niche's past decisions."""
    from decision_engine import store

    history = store.find_decisions_by_niche(niche, path=decisions_path)
    if not history:
        return _result(
            "Executive Memory", "لا قرار حقيقي مسجَّل لهذا النيتش بعد", 0.0,
            [], "غير معروف — لا تاريخ قرارات حقيقي", "لا سجل مؤسسي حقيقي بعد لهذا النيتش",
            founder_approval_required=False, stance="no_data", scope="niche",
        )

    latest = history[-1]
    matched_outcome = next(
        (o for o in store.read_outcomes(path=outcomes_path) if o.get("decision_id") == latest.get("decision_id")),
        None,
    )

    known_fields = sum(1 for f in (latest.get("alternatives_rejected"), latest.get("expected_outcome")) if f)
    confidence = round((known_fields + (1 if matched_outcome else 0)) / 3, 2)

    opinion = f"{len(history)} قرار حقيقي سابق لهذا النيتش — آخر حالة: {latest.get('status')} ({latest.get('decided_at')})"
    evidence = [f"reasoning: {r}" for r in (latest.get("reasoning") or [])]
    if latest.get("expected_outcome"):
        evidence.append(f"expected_outcome: {latest['expected_outcome']}")
    if latest.get("alternatives_rejected"):
        evidence.extend(f"alternative_rejected: {a}" for a in latest["alternatives_rejected"])
    if matched_outcome:
        evidence.append(f"real_outcome: matched={matched_outcome.get('matched')} ({matched_outcome.get('match_method')})")

    risk = "قرار DEFERRED سابق بانتظار مراجعة المؤسس" if latest.get("status") == "DEFERRED" else "لا مخاطر ذاكرة مؤسسية حقيقية نشطة"
    recommendation = "راجع القرار المؤجَّل (DEFERRED) السابق" if latest.get("status") == "DEFERRED" else "لا إجراء عاجل من الذاكرة المؤسسية"
    return _result(
        "Executive Memory", opinion, confidence, evidence, risk, recommendation,
        founder_approval_required=(latest.get("status") == "DEFERRED"), stance="informational_context", scope="niche",
    )


# ── The Council itself ──

_STANCE_RECOMMENDATION = {
    "proceed": "استمر — إجماع حقيقي بين كل الأعضاء ذوي موقف تصويت فعلي",
    "hold": "أوقف مؤقتاً — إجماع حقيقي على وجود خطر بين كل الأعضاء ذوي موقف تصويت فعلي",
    "stop": "أوقف — إجماع حقيقي على فشل حقيقي بين كل الأعضاء ذوي موقف تصويت فعلي",
}


def convene_council(niche, decisions_path=None, outcomes_path=None, alerts_path=None,
                     db_file=None, timeline_path=None, inspections_log=None,
                     customer_state_path=None, tier="tier4", external_signal=None,
                     ledger_path=None, safe_mode_state_path=None, publish_protection_state_path=None,
                     requests_path=None, pipeline_state_path=None, health_snapshots_path=None):
    """The real aggregator -- calls all 9 members, applies the honest
    disagreement algorithm below (never averaging real disagreement into
    a fake consensus), returns the full Council session.

    Mission Control (the directive's 10th named member) is deliberately
    NOT given a fabricated 10th opinion here -- it is the display venue
    for the 9 below (mission_control_api.py/server.js/the HTML
    dashboards), not an analytical producer the way the other 9 are.
    This is a disclosed scope decision (ADR-138), not a silent omission.

    Disagreement algorithm: each member already tags itself with a
    `stance` (proceed/hold/stop) ONLY where its own real source emits
    something genuinely comparable to a go/no-go signal; members with
    no real axis for that (`no_data`/`informational_context`) are
    excluded from the vote entirely, never coerced onto it.
    `disagreement_detected` is True iff 2+ voting members hold genuinely
    different stances -- generalizing decision_engine.engine's real
    2-signal-must-agree rule to N members. When members agree,
    `council_recommendation`/`council_confidence` are a real citation of
    that agreement (mean confidence, same `_aggregate_confidence()`
    precedent as executive_board.py); when they disagree, both are
    honestly non-numeric ("SPLIT...") -- never a blended fake verdict.

    `expected_impact`/`long_term_effect` (the directive's own named
    display fields) cite Strategic Intelligence Core's own already-real
    strategic_value/long_term_value dimensions via its `raw` field --
    never a second call to strategic_score()."""
    members = [
        _member_strategic(niche, decisions_path=decisions_path),
        _member_market(niche, alerts_path=alerts_path, db_file=db_file),
        _member_production(niche, timeline_path=timeline_path, inspections_log=inspections_log),
        _member_customer(state_path=customer_state_path),
        _member_financial(niche, tier=tier, external_signal=external_signal, ledger_path=ledger_path),
        _member_security(niche, decisions_path=decisions_path),
        _member_resilience(
            safe_mode_state_path=safe_mode_state_path, publish_protection_state_path=publish_protection_state_path,
            requests_path=requests_path, pipeline_state_path=pipeline_state_path, health_snapshots_path=health_snapshots_path,
        ),
        _member_innovation(decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path),
        _member_executive_memory(niche, decisions_path=decisions_path, outcomes_path=outcomes_path),
    ]

    voting_members = [m for m in members if m["stance"] not in ("no_data", "informational_context")]
    stances = {m["stance"] for m in voting_members}
    disagreement_detected = len(stances) > 1

    stance_summary = {
        "proceed_count": sum(1 for m in members if m["stance"] == "proceed"),
        "hold_count": sum(1 for m in members if m["stance"] == "hold"),
        "stop_count": sum(1 for m in members if m["stance"] == "stop"),
        "no_data_count": sum(1 for m in members if m["stance"] == "no_data"),
        "informational_count": sum(1 for m in members if m["stance"] == "informational_context"),
    }

    if disagreement_detected:
        council_recommendation = "SPLIT — انظر disagreeing_members، لا إجماع حقيقي"
        council_confidence = "Unknown"
        unified_stance = None
        disagreeing_members = [
            {"member": m["member"], "stance": m["stance"], "recommendation": m["recommendation"], "risk": m["risk"]}
            for m in voting_members
        ]
    elif voting_members:
        unified_stance = voting_members[0]["stance"]
        council_recommendation = _STANCE_RECOMMENDATION[unified_stance]
        council_confidence = round(sum(m["confidence"] for m in voting_members) / len(voting_members), 2)
        disagreeing_members = []
    else:
        council_recommendation = "لا عضو واحد لديه إشارة تصويت حقيقية بعد — كل الأعضاء معلوماتيون أو بلا بيانات"
        council_confidence = "Unknown"
        unified_stance = None
        disagreeing_members = []

    strategic_member = next(m for m in members if m["member"] == "Strategic Intelligence Core")
    strategic_raw = strategic_member.get("raw") or {}
    expected_impact = strategic_raw.get("strategic_value") or {"value": "Unknown", "reason": "لا تقييم استراتيجي حقيقي متاح"}
    long_term_effect = strategic_raw.get("long_term_value") or {"value": "Unknown", "reason": "لا تقييم استراتيجي حقيقي متاح"}

    return {
        "niche": niche,
        "members": members,
        "stance_summary": stance_summary,
        "disagreement_detected": disagreement_detected,
        "disagreeing_members": disagreeing_members,
        "council_recommendation": council_recommendation,
        "council_confidence": council_confidence,
        "unified_stance": unified_stance,
        "supporting_evidence": [f"{m['member']}: {e}" for m in members for e in m["evidence"]],
        "risks": [f"{m['member']}: {m['risk']}" for m in members],
        "expected_impact": expected_impact,
        "long_term_effect": long_term_effect,
        "founder_approval_required": any(m["founder_approval_required"] for m in members),
        "convened_at": _now_iso(),
    }


# ── Learning: Recommendation vs Founder Decision vs Real Outcome ──
# Append-only, same convention as decision_engine/store.py and
# data/incidents.jsonl -- never overwrites, never rewrites history.

def _read_council_recommendations(path=None):
    path = Path(path) if path else DEFAULT_COUNCIL_RECOMMENDATIONS_PATH
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def record_council_recommendation(session, decision_id=None, path=None):
    """Explicit, human/caller-invoked append -- never auto-recorded from
    a scheduler (this factory has none, CLAUDE.md). One row per real
    convene_council() session, recording what the Council actually
    recommended AT THE TIME it was convened -- the real substrate
    council_learning_summary() below needs that no prior module in this
    factory persisted (only the eventual Decision + Outcome existed,
    a 2-way link; this is the missing first leg)."""
    record = {
        "council_id": hashlib.sha256(f"{session['niche']}|{session['convened_at']}".encode("utf-8")).hexdigest()[:16],
        "niche": session["niche"],
        "decision_id": decision_id,
        "convened_at": session["convened_at"],
        "members": [
            {"member": m["member"], "stance": m["stance"], "recommendation": m["recommendation"], "confidence": m["confidence"]}
            for m in session["members"]
        ],
        "council_recommendation": session["council_recommendation"],
        "unified_stance": session["unified_stance"],
        "disagreement_detected": session["disagreement_detected"],
    }
    out_path = Path(path) if path else DEFAULT_COUNCIL_RECOMMENDATIONS_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def council_learning_summary(recommendations_path=None, decisions_path=None, outcomes_path=None):
    """Real, mechanical 3-way join: Council Recommendation -> real
    Founder Decision (decision_engine.store) -> real Outcome
    (decision_engine.store) -- same True/False/None non-forced-verdict
    discipline as executive_board.review_board_track_record(). Every
    leg is honestly 'pending'/'too_soon_to_tell' when no real match
    exists yet -- never backfilled for a niche/decision that predates
    the Council's existence."""
    from decision_engine import store

    recommendations = _read_council_recommendations(recommendations_path)
    if not recommendations:
        return {
            "answer": "NOT ENOUGH EVIDENCE",
            "reason": "لا توصية مجلس حقيقية مسجَّلة بعد (record_council_recommendation() لم يُستدعَ بعد)",
            "reviews": [],
        }

    all_outcomes = list(store.read_outcomes(path=outcomes_path))
    reviews = []
    for rec in recommendations:
        niche = rec.get("niche")
        convened_at = rec.get("convened_at") or ""
        unified_stance = rec.get("unified_stance")

        history = store.find_decisions_by_niche(niche, path=decisions_path) if niche else []
        later_decisions = [d for d in history if (d.get("decided_at") or "") >= convened_at]
        founder_decision = later_decisions[-1] if later_decisions else None

        if founder_decision is None:
            recommendation_vs_decision = "pending"
            decision_note = "لم يُتخذ قرار مؤسس حقيقي بعد منذ هذا الاجتماع"
        elif unified_stance is None:
            recommendation_vs_decision = "no_clear_council_position"
            decision_note = f"المجلس كان منقسماً (SPLIT) — لا موقف واحد للمقارنة؛ قرار المؤسس الحقيقي: {founder_decision.get('status')}"
        else:
            council_says_proceed = unified_stance == "proceed"
            founder_says_accepted = founder_decision.get("status") == "ACCEPTED"
            recommendation_vs_decision = "matched" if council_says_proceed == founder_says_accepted else "diverged"
            decision_note = f"قرار المؤسس الحقيقي: {founder_decision.get('status')}"

        matched_outcome = next(
            (o for o in all_outcomes if founder_decision and o.get("decision_id") == founder_decision.get("decision_id")),
            None,
        )
        if matched_outcome is None:
            decision_vs_outcome = "too_soon_to_tell"
            outcome_note = "لا نتيجة حقيقية مسجَّلة بعد لهذا القرار"
        else:
            decision_vs_outcome = "matched" if matched_outcome.get("matched") else "diverged"
            outcome_note = f"نتيجة حقيقية: matched={matched_outcome.get('matched')} ({matched_outcome.get('match_method')})"

        reviews.append({
            "council_id": rec.get("council_id"), "niche": niche, "convened_at": convened_at,
            "council_recommendation": rec.get("council_recommendation"),
            "recommendation_vs_decision": recommendation_vs_decision, "decision_note": decision_note,
            "decision_vs_outcome": decision_vs_outcome, "outcome_note": outcome_note,
        })

    real_triples = [
        r for r in reviews
        if r["recommendation_vs_decision"] in ("matched", "diverged") and r["decision_vs_outcome"] in ("matched", "diverged")
    ]
    if not real_triples:
        return {
            "answer": "NOT ENOUGH EVIDENCE",
            "reason": f"{len(reviews)} توصية مجلس حقيقية مسجَّلة، لكن 0 ثلاثية حقيقية كاملة (توصية+قرار+نتيجة) بعد",
            "reviews": reviews,
        }

    matched_all_the_way = sum(1 for r in real_triples if r["recommendation_vs_decision"] == "matched" and r["decision_vs_outcome"] == "matched")
    return {
        "total_recommendations": len(recommendations),
        "real_triples": len(real_triples),
        "matched_all_the_way": matched_all_the_way,
        "reviews": reviews,
        "generated_at": _now_iso(),
    }

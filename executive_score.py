#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executive Score (Executive Intelligence Core, Round 6, 2026-07-29).

The founder's directive asks for one global company score plus named
sub-scores (Trust, Automation, Customer Happiness, Production Quality,
Delivery Quality, Operational Stability, Architecture Health, Security
Health, Technical Debt, Growth). This factory already has a strong,
explicit standing rule against exactly the failure mode a naive
"Executive Score" invites: SERVICE_LAYER_API.md documents real priority
signals shown "never merged into one fabricated composite score", and
value_engine.py/reality.py both already prove the safe alternative --
a transparent, documented average built ONLY from real components, with
an honest "Unknown" (never a silently-assumed 0 or 100) wherever no real
signal exists yet.

This module follows that exact precedent. Every sub-score here is either
a real number computed from an existing real function (never invented),
or "Unknown" with the real reason stated. compute_executive_score()
never touches any accept/reject/production gate -- purely informational,
surfaced only in Mission Control.

Two sub-scores (Operational Stability, Customer Happiness) are computed
JS-side (lib/health_checks.js, lib/dashboard_data.js's
readCustomerReviewsSummary()) and merged in by server.js's Mission
Control panel handler -- this module only owns the Python-side signals
it can compute without crossing a language boundary. See
mission_control_executive_v1.html's 'executive-score' panel wiring.
"""

import json
import os

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
INSPECTIONS_LOG = os.path.join(FACTORY_DIR, 'inspections.log')


def _real(value, source, **extra):
    return {"value": value, "source": source, **extra}


def _unknown(reason, **extra):
    return {"value": "Unknown", "reason": reason, **extra}


def _dual_inspection_pass_rate(inspections_log=None, limit=20):
    """Same real computation as self_awareness.js's own
    getDualInspectionPassRate() -- the JS original this factory already
    trusts, reimplemented here in Python since executive_score.py has no
    Node runtime to call into. Same log, same real result either way."""
    path = inspections_log or INSPECTIONS_LOG
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        lines = [ln for ln in f.read().split('\n') if ln.strip()][-limit:]
    total, passed = 0, 0
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        if entry.get("passed"):
            passed += 1
    if not total:
        return None
    return {"total": total, "passed": passed, "rate": round(passed / total * 100)}


def _production_quality(inspections_log=None):
    result = _dual_inspection_pass_rate(inspections_log)
    if result is None:
        return _unknown("لا سجل فحص مزدوج حقيقي كافٍ بعد (inspections.log)")
    return _real(result["rate"], "inspections.log (Dual Inspection pass rate, آخر 20 فحصاً حقيقياً)", detail=result)


def _trust(inspections_log=None):
    """Real aggregate via enterprise_readiness.compute_trust_score() --
    quality reuses the exact same real Dual Inspection pass rate as
    Production Quality above (never a second, divergent computation);
    support-contact/refund-policy are real, direct file checks (this
    factory's real, live customer_site/ Support Center section and
    trust/refund-policy.html), not assumed true."""
    from enterprise_readiness import compute_trust_score

    quality = _dual_inspection_pass_rate(inspections_log)
    has_support_contact = 'id="support"' in _read_text(os.path.join(FACTORY_DIR, 'customer_site', 'index.html'))
    has_refund_policy = os.path.exists(os.path.join(FACTORY_DIR, 'trust', 'refund-policy.html'))

    trust_obj = compute_trust_score(
        quality_score=quality["rate"] if quality else None,
        evidence_score=None,  # honestly unavailable at a company-wide (not per-niche) level today
        has_support_contact=has_support_contact,
        has_refund_policy=has_refund_policy,
    )
    if quality is None:
        return _unknown("لا معدّل فحص مزدوج حقيقي بعد لحساب مكوّن الجودة", detail=trust_obj)
    return _real(quality["rate"], "enterprise_readiness.compute_trust_score()", detail=trust_obj)


def _read_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ""


def _technical_debt():
    from strategic_intelligence import technical_debt as tech_debt_module

    result = tech_debt_module.components_at_risk_of_technical_debt()
    if result.get("answer") == "Unknown":
        return _unknown(result["reason"], source=result.get("source"))
    # A real, named list of at-risk components exists -- no honest 0-100
    # scale exists without a real total-component baseline to divide by
    # (same reasoning department_health.py's own docstring already
    # applies to itself), so this stays Unknown numerically while still
    # surfacing the real, specific list.
    return _unknown(
        f"{len(result['answer'])} مكوّن حقيقي معرَّض -- لا معيار عدد إجمالي موثوق لتحويله إلى نسبة صادقة",
        components_at_risk=result["answer"], source=result.get("source"),
    )


def _security_health():
    import ai_doctor

    python_pinning = ai_doctor._check_python_pinning()
    node_pinning = ai_doctor._check_node_pinning()
    ratios = []
    for check in (python_pinning, node_pinning):
        if check.get("checked"):
            ratios.append(check["pinned"] / check["checked"] * 100)
    if not ratios:
        return _unknown("لا اعتماديات مُدرَجة في requirements.txt أو package.json بعد", detail={"python": python_pinning, "node": node_pinning})
    return _real(round(sum(ratios) / len(ratios)), "ai_doctor.py dependency-pinning check (requirements.txt/package.json)",
                 detail={"python": python_pinning, "node": node_pinning})


def _delivery_quality():
    """Real encoding of reality.py's own verdict -- the single existing
    truth-telling composite this factory already trusts (its status can
    only make Mission Control's health verdict worse, never better).
    Reusing its categorical verdict as a number here, not recomputing a
    second, competing delivery signal."""
    import reality

    result = reality.scorecard()
    verdict = result.get("verdict")
    mapping = {"OK": 100, "WARNING": 50, "CRITICAL": 0}
    if verdict not in mapping:
        return _unknown(f"reality.py رجع حالة غير متوقَّعة: {verdict!r}", detail=result)
    return _real(mapping[verdict], "reality.py scorecard() verdict (OK=100/WARNING=50/CRITICAL=0)", detail=result)


def _automation():
    """Narrow, honestly-labeled proxy: real AI-provider configuration
    ratio (ai_capability.registry) -- NOT a claim about overall factory
    automation, which has no single real measurable signal today."""
    from ai_capability import registry as ai_registry

    providers = ai_registry.list_providers()
    if not providers:
        return _unknown("لا مزوّدي AI مُسجَّلين")
    configured = sum(1 for p in providers if p.get("configured"))
    return _real(
        round(configured / len(providers) * 100),
        "ai_capability.registry.list_providers() -- نسبة مزوّدي AI بيانات اعتماد حقيقية (ليس مقياس أتمتة شامل للمصنع)",
        detail={"configured": configured, "total": len(providers)},
    )


def _growth():
    """Honestly Unknown by design until growth_engine.py's own real gate
    (>=2 real comparable sales windows) is satisfied -- see
    growth_engine.py's growth_forecast(), which never returns a bare
    number itself (even at REAL maturity its own forecast.value is
    honestly None until 2 comparable real windows exist)."""
    import growth_engine

    result = growth_engine.growth_forecast()
    value = (result.get("forecast") or {}).get("value") if result.get("maturity") == "REAL" else None
    if value is None:
        reason = result.get("reason") or (result.get("forecast") or {}).get("reason") or "لا اتجاه نمو حقيقي قابل للحساب بعد"
        return _unknown(reason, source="growth_engine.growth_forecast()", detail=result)
    return _real(value, "growth_engine.growth_forecast()", detail=result)


def _architecture_health():
    """Always Unknown -- ai_doctor.py's own docstring already declined to
    build real architecture-drift detection ('no architecture baseline
    exists to diff against... building it now would risk exactly the
    fabrication quality_doctor.py is the cautionary tale for'). Repeating
    that real, deliberate non-goal here rather than inventing a number."""
    return _unknown("لا كاشف انحراف معماري حقيقي مبنيّ بعد -- قرار مؤسَّس صريح، راجع ai_doctor.py")


def compute_executive_score(inspections_log=None):
    """Python-side sub-scores only -- see this module's own docstring for
    why Operational Stability/Customer Happiness are merged in JS-side."""
    sub_scores = {
        "trust": _trust(inspections_log),
        "production_quality": _production_quality(inspections_log),
        "technical_debt": _technical_debt(),
        "security_health": _security_health(),
        "delivery_quality": _delivery_quality(),
        "automation": _automation(),
        "growth": _growth(),
        "architecture_health": _architecture_health(),
    }
    return {"sub_scores": sub_scores}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — AI Executive Board (Executive Directive, 2026-07-22).

The single most important design decision in this module, made before
any code was written: each of the 10 executive roles is a fully
DETERMINISTIC function over already-real, already-computed evidence
(executive_quality_gate.py's 20 criteria, enterprise_readiness.py's 10
product reviews and risk register, market_evidence.py's real logged
events) -- never a free-form LLM-generated "opinion." This factory
already found, live, earlier this same session, that its content model
(llama-3.1-8b-instant) fabricates confident-sounding claims about
infrastructure that doesn't exist when asked to write freely. Asking
that same model to roleplay "as the CFO, what do you think" over the
identical evidence would risk exactly that failure mode dressed up as
executive judgment. Every recommendation, risk, opportunity, and
missing-evidence item below traces to one specific real field computed
elsewhere in this factory -- nothing here is generated narrative.

Each of the 10 roles looks at a different, real SUBSET of the same
underlying evidence -- genuinely distinct lenses, not 10 copies of one
number. The shared vote rule, applied identically by every role: a real
FAIL among their relevant criteria votes REJECT; zero real (non-Unknown)
evidence among their relevant criteria votes DEFER (never guesses);
otherwise APPROVE. Confidence is a real fraction of how much of their
relevant evidence is actually known, never invented.

"No single agent may approve strategic decisions alone" is enforced
structurally: only convene_board() produces a board decision. No
individual executive function is wired anywhere as a standalone
approval path.

"Continuously learn from previous decisions" does NOT mean an
autonomous background process -- this factory has no scheduler
(CLAUDE.md). review_board_track_record() is the real, honest,
on-demand version: it compares a real past board vote against whatever
real market evidence has actually accumulated since, for that niche,
via market_evidence.py (ADR-088). Zero evidence since a meeting means an
honest "too soon to tell", never a fabricated verdict either way.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_BOARD_PATH = _FACTORY_ROOT / "data" / "board_meetings.jsonl"

EXECUTIVE_ROLES = (
    "CEO", "CTO", "CFO", "COO", "CPO",
    "Chief Market Intelligence Officer", "Chief Risk Officer",
    "Chief Revenue Officer", "Chief Customer Officer", "Chief Innovation Officer",
)

# Irreversible decisions require unanimous board approval; production
# decisions require a real majority. Matches this factory's own standing
# "5 things need explicit approval" taxonomy (unrecoverable data
# deletion, paid services, prod deploy, outside-workspace changes,
# secrets access) -- the same class of action, formalized here as a
# board-level rule rather than a one-off human check each time.
DECISION_TYPES = ("production", "irreversible")


def _extract(criteria, keys):
    """Pulls a role-specific real subset out of an already-computed
    criteria dict -- never recomputes, never invents a missing key."""
    return {k: criteria[k] for k in keys if k in criteria}


def _vote_from(relevant, extra_risks=None, extra_opportunities=None, extra_missing=None):
    """The one shared, real vote rule every executive uses identically."""
    statuses = [v["status"] for v in relevant.values()]
    risks = [f"{k}: {v['reason']}" for k, v in relevant.items() if v["status"] == "FAIL"]
    opportunities = [f"{k}: {v['reason']}" for k, v in relevant.items() if v["status"] in ("PASS", "INFO")]
    missing = [f"{k}: {v['reason']}" for k, v in relevant.items() if v["status"] == "UNKNOWN"]
    risks += extra_risks or []
    opportunities += extra_opportunities or []
    missing += extra_missing or []

    known = sum(1 for s in statuses if s != "UNKNOWN")
    confidence = round(known / len(statuses), 2) if statuses else 0.0

    if risks:
        vote = "REJECT"
    elif known == 0:
        vote = "DEFER"
    else:
        vote = "APPROVE"

    return {
        "risks": risks, "opportunities": opportunities, "missing_evidence": missing,
        "confidence": confidence, "vote": vote,
    }


def _executive_result(role, relevant, recommendation_template, extra_risks=None, extra_opportunities=None, extra_missing=None):
    outcome = _vote_from(relevant, extra_risks, extra_opportunities, extra_missing)
    recommendation = recommendation_template.format(vote=outcome["vote"])
    return {"role": role, "recommendation": recommendation, **outcome}


# ── The 10 executives — each a real, distinct, evidence-only lens ──

def analyze_as_ceo(readiness_result):
    """Not a separate criteria subset -- the CEO's real, distinct lens
    is the aggregate view: the master gate's own final_status and
    whether human review is required across the whole evaluation, the
    one thing only the chair role looks at directly."""
    final_status = readiness_result.get("final_status", "")
    hard_failures = readiness_result.get("hard_failures", [])
    gate_result = (readiness_result.get("risk_register") or {}).get("gate_result", {})
    human_review = gate_result.get("human_review_required", False)

    risks = [f"مراجعة قسم: {f}" for f in hard_failures]
    missing = list(gate_result.get("human_review_reasons") or [])
    opportunities = [] if hard_failures else ["لا فشل حرج في مراجعات المنتج العشر"]

    if "PRE_GATE" in final_status:
        vote, confidence = "DEFER", 0.0
        risks = ["هذا منتج ما قبل البوابة (PRE_GATE) — لم يُقيَّم بعد وفق هذه البوابة"]
    elif hard_failures:
        vote, confidence = "REJECT", 1.0
    elif human_review:
        vote, confidence = "DEFER", 0.5
    else:
        vote, confidence = "APPROVE", 1.0

    return {
        "role": "CEO",
        "recommendation": f"الحالة الإجمالية الحقيقية: {final_status} — التصويت: {vote}",
        "risks": risks, "opportunities": opportunities, "missing_evidence": missing,
        "confidence": confidence, "vote": vote,
    }


def analyze_as_cto(criteria, product_review):
    relevant = _extract(criteria, ("technical_feasibility", "infrastructure_readiness", "automation_readiness"))
    security = product_review.get("security")
    extra_risks = [f"security: {security['reason']}"] if security and security["status"] == "FAIL" else []
    extra_missing = [f"security: {security['reason']}"] if security and security["status"] == "UNKNOWN" else []
    return _executive_result("CTO", relevant, "الجاهزية التقنية والبنية التحتية: {vote}", extra_risks, None, extra_missing)


def analyze_as_cfo(criteria, product_review):
    relevant = _extract(criteria, ("operational_cost", "revenue_model_sustainability"))
    financial = product_review.get("financial")
    extra_risks = [f"financial: {financial['reason']}"] if financial and financial["status"] == "FAIL" else []
    extra_missing = [f"financial: {financial['reason']}"] if financial and financial["status"] == "UNKNOWN" else []
    return _executive_result("CFO", relevant, "الاستدامة المالية والتكلفة التشغيلية: {vote}", extra_risks, None, extra_missing)


def analyze_as_coo(criteria, product_review, documentation):
    relevant = _extract(criteria, ("delivery_capability", "infrastructure_readiness"))
    op = product_review.get("operational")
    maint = product_review.get("maintenance")
    doc_fails = [f"{k}: {v['reason']}" for k, v in (documentation or {}).items() if v["status"] == "FAIL"]
    extra_risks = doc_fails.copy()
    for r in (op, maint):
        if r and r["status"] == "FAIL":
            extra_risks.append(f"{r}")
    return _executive_result("COO", relevant, "القدرة التشغيلية والتوثيق الحقيقي: {vote}", extra_risks)


def analyze_as_cpo(criteria, product_review):
    security = product_review.get("security")
    privacy = product_review.get("privacy")
    support = product_review.get("support")
    relevant = _extract(criteria, ("defensibility",))
    extras_risks, extras_missing = [], []
    for name, r in (("security", security), ("privacy", privacy), ("support", support)):
        if r and r["status"] == "FAIL":
            extras_risks.append(f"{name}: {r['reason']}")
        elif r and r["status"] == "UNKNOWN":
            extras_missing.append(f"{name}: {r['reason']}")
    return _executive_result("CPO", relevant, "جودة المنتج (أمان/خصوصية/دعم) والدفاعية: {vote}", extras_risks, None, extras_missing)


def analyze_as_cmio(criteria, risk_intel=None):
    relevant = _extract(criteria, ("market_saturation_competitor_quality", "customer_pain_evidence"))
    extra_risks, extra_missing = [], []
    if risk_intel:
        complaints = risk_intel.get("customer_complaints")
        if isinstance(complaints, dict) and complaints.get("status") == "UNKNOWN":
            extra_missing.append(f"customer_complaints: {complaints['reason']}")
        for gap_key in ("regulation_changes", "pricing_changes", "technology_disruption", "demand_decline"):
            gap = risk_intel.get(gap_key)
            if isinstance(gap, dict) and gap.get("status") == "UNKNOWN":
                extra_missing.append(f"{gap_key}: {gap['reason']}")
    return _executive_result("Chief Market Intelligence Officer", relevant, "تشبّع السوق ودليل ألم العملاء الحقيقي: {vote}", extra_risks, None, extra_missing)


def analyze_as_cro_risk(risk_register):
    relevant = {
        "market_risk": risk_register["market_risk"], "technical_risk": risk_register["technical_risk"],
        "regulatory_risk": risk_register["regulatory_risk"], "competitive_risk": risk_register["competitive_risk"],
        "execution_risk": risk_register["execution_risk"],
    }
    result = _executive_result("Chief Risk Officer", relevant, "سجل المخاطر الثماني الحقيقي: {vote}")
    result["exit_criteria"] = risk_register["exit_criteria"]
    result["kill_switch_conditions"] = risk_register["kill_switch_conditions"]
    return result


def analyze_as_cro_revenue(criteria):
    relevant = _extract(criteria, ("willingness_to_pay_evidence", "customer_acquisition_difficulty", "revenue_model_sustainability"))
    return _executive_result("Chief Revenue Officer", relevant, "الاستعداد للدفع وصعوبة الاكتساب والإيراد المتكرر: {vote}")


def analyze_as_cco(criteria, product_review):
    relevant = _extract(criteria, ("customer_retention_potential",))
    cs = product_review.get("customer_success")
    support = product_review.get("support")
    extra_risks, extra_missing = [], []
    for name, r in (("customer_success", cs), ("support", support)):
        if r and r["status"] == "FAIL":
            extra_risks.append(f"{name}: {r['reason']}")
        elif r and r["status"] == "UNKNOWN":
            extra_missing.append(f"{name}: {r['reason']}")
    return _executive_result("Chief Customer Officer", relevant, "الاحتفاظ بالعملاء ونجاح العملاء والدعم: {vote}", extra_risks, None, extra_missing)


def analyze_as_cio_innovation(criteria):
    relevant = _extract(criteria, ("long_term_strategic_value", "automation_readiness", "evidence_freshness"))
    return _executive_result("Chief Innovation Officer", relevant, "القيمة الاستراتيجية طويلة المدى وجاهزية الأتمتة: {vote}")


# ── The board itself ──

def _tally(executives, decision_type):
    votes = {e["role"]: e["vote"] for e in executives}
    approve_count = sum(1 for v in votes.values() if v == "APPROVE")
    reject_count = sum(1 for v in votes.values() if v == "REJECT")
    defer_count = sum(1 for v in votes.values() if v == "DEFER")
    total = len(executives)

    if decision_type == "irreversible":
        board_decision = "APPROVED" if approve_count == total else "NOT_APPROVED"
        rule = f"إجماع مطلوب للقرارات غير القابلة للرجوع: {approve_count}/{total} موافقة"
    else:
        board_decision = "APPROVED" if approve_count > total / 2 and reject_count == 0 else "NOT_APPROVED"
        rule = f"أغلبية مطلوبة: {approve_count}/{total} موافقة، {reject_count} رفض"

    return {
        "votes": votes, "approve_count": approve_count, "reject_count": reject_count,
        "defer_count": defer_count, "total": total, "board_decision": board_decision, "rule_applied": rule,
    }


def _write_meeting(meeting, board_path=None):
    path = Path(board_path) if board_path else DEFAULT_BOARD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(meeting, ensure_ascii=False, default=str) + "\n")


def convene_board(spec, decision_type="production", include_risk_intelligence=False, board_path=None):
    """The ONLY function in this module that produces a real board
    decision -- no individual executive function above is ever wired as
    a standalone approval path, enforcing "no single agent may approve
    strategic decisions alone" structurally, not just by convention.

    decision_type: "production" (real majority) or "irreversible" (real
    unanimity) -- matches this factory's own standing "5 things need
    explicit approval" taxonomy."""
    if decision_type not in DECISION_TYPES:
        raise ValueError(f"decision_type must be one of {DECISION_TYPES}, got {decision_type!r}")

    import enterprise_readiness as er

    readiness_result = er.run_enterprise_readiness_gate(spec)
    criteria = (readiness_result.get("risk_register") or {}).get("gate_result", {}).get("criteria", {})
    product_review = readiness_result.get("product_review", {})
    risk_register = readiness_result.get("risk_register", {})
    documentation = readiness_result.get("documentation_completeness", {})

    risk_intel = None
    if include_risk_intelligence and spec.get("niche"):
        risk_intel = er.run_risk_intelligence_scan(spec["niche"])

    executives = [
        analyze_as_ceo(readiness_result),
        analyze_as_cto(criteria, product_review),
        analyze_as_cfo(criteria, product_review),
        analyze_as_coo(criteria, product_review, documentation),
        analyze_as_cpo(criteria, product_review),
        analyze_as_cmio(criteria, risk_intel),
        analyze_as_cro_risk(risk_register),
        analyze_as_cro_revenue(criteria),
        analyze_as_cco(criteria, product_review),
        analyze_as_cio_innovation(criteria),
    ]

    tally = _tally(executives, decision_type)

    meeting = {
        "niche": spec.get("niche"),
        "title": spec.get("title") or spec.get("niche"),
        "decision_type": decision_type,
        "pre_gate_product": readiness_result.get("pre_gate_product"),
        "executives": executives,
        "tally": tally,
        "convened_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_meeting(meeting, board_path)
    return meeting


# ── Learning from real outcomes (on-demand -- no scheduler exists) ──

def _read_meetings(niche=None, board_path=None):
    path = Path(board_path) if board_path else DEFAULT_BOARD_PATH
    if not path.exists():
        return []
    meetings = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if niche is not None and m.get("niche") != niche:
                continue
            meetings.append(m)
    return meetings


def review_board_track_record(niche=None, board_path=None):
    """On-demand, not continuous (no scheduler exists in this factory --
    CLAUDE.md). Compares each real past board decision against whatever
    real market evidence has actually accumulated since, for that same
    niche, via market_evidence.py. Zero real evidence since a meeting is
    an honest "too soon to tell", never a fabricated verdict."""
    import market_evidence

    meetings = _read_meetings(niche, board_path)
    reviews = []
    for m in meetings:
        m_niche = m.get("niche")
        summary = market_evidence.summarize_niche(m_niche) if m_niche else None
        board_decision = m["tally"]["board_decision"]

        if not summary or summary["total_events"] == 0:
            outcome_note = "لا دليل سوق حقيقي تراكم بعد منذ هذا الاجتماع — من المبكر جداً معرفة النتيجة"
            matched = None
        else:
            wtp = summary.get("willingness_to_pay")
            positive_real = bool(wtp and wtp["positive_signals"] > wtp["pricing_objections"])
            negative_real = bool(wtp and wtp["pricing_objections"] >= wtp["positive_signals"] and wtp["pricing_objections"] > 0)
            if board_decision == "APPROVED" and positive_real:
                outcome_note, matched = "القرار الحقيقي اللاحق يدعم موافقة المجلس", True
            elif board_decision == "APPROVED" and negative_real:
                outcome_note, matched = "الدليل الحقيقي اللاحق يتعارض مع موافقة المجلس", False
            elif board_decision == "NOT_APPROVED" and negative_real:
                outcome_note, matched = "الدليل الحقيقي اللاحق يدعم عدم موافقة المجلس", True
            else:
                outcome_note, matched = "الدليل الحقيقي المتاح غير حاسم بعد", None

        reviews.append({
            "niche": m_niche, "convened_at": m.get("convened_at"), "board_decision": board_decision,
            "real_evidence_since": summary, "outcome_note": outcome_note, "prediction_matched_reality": matched,
        })
    return reviews

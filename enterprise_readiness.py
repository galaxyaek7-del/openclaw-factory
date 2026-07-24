#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Enterprise Readiness Layer (Executive Directive,
2026-07-22).

Founder-confirmed scope before any code was written (two clarifying
questions, both answered):
  1. Legal/security/privacy reviews are built as honest, clearly-labeled
     PROXY checks (deterministic, real signals) -- never presented as a
     genuine expert legal/security/privacy review, since this factory
     employs no lawyer, security professional, or privacy officer.
  2. This gate applies PROSPECTIVELY -- to new products from here
     forward. The 5 already-shipped, checkout-ready products keep an
     honest "pre-gate" status (see PRE_GATE_STATUS below), not a
     retroactive rejection or un-publish.

Reuses every real signal this factory already computes -- "wrap don't
rewrite" applied at the largest scale yet: executive_quality_gate.py
(ADR-087) is the scoring backbone, market_evidence.py (ADR-088) is the
evidence source, competitor_discovery.py/inspectors.py/recovery/
product_families.registry are reused directly, never reimplemented.

Two architecture facts shape every "continuous"/"automatic" claim below,
same as every other module in this factory: (1) no scheduler exists
(CLAUDE.md) -- anything described as "continuous" here is actually
on-demand, triggered explicitly, and says so; (2) several requested
capabilities (regulation-change tracking, technology-disruption
detection, demand-decline tracking, ongoing customer-complaint intake
beyond what's manually logged) have no real, funded data source in this
factory -- they are documented as permanent, disclosed gaps rather than
faked with a plausible-looking check that isn't real intelligence.

PRE_GATE_STATUS is a real, honest record of what shipped before this
gate existed -- not an excuse to avoid ever reviewing them, but proof
this ADR does not retroactively act on decisions the founder didn't ask
it to.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_CHANGELOG_PATH = _FACTORY_ROOT / "data" / "product_changelog.jsonl"

# The 5 real products shipped before this gate existed (2026-07-22 night
# session, ADR-086) -- explicitly "pre-gate", per the founder's own
# "prospective only" decision. Never silently re-flagged as REJECTED by
# this module; a human decision to actually re-review them is separate
# and deliberate.
PRE_GATE_PRODUCTS = (
    "AI-Powered Compliance Automation System for Accounting Firms",
    "AI Customer Support Automation Platform for E-Commerce Businesses",
    "Workflow Automation System for Logistics Companies",
    "Inventory Management System for Wholesale Distributors",
    "How I Built an Autonomous AI Company Solo",
)

SECURITY_RISK_PHRASES = [
    "share your password", "disable 2fa", "disable two-factor", "turn off two-factor",
    "store your api key in the code", "hardcode your api key", "commit your password",
    "share your api key with", "email your password",
]


def _unknown(reason):
    return {"status": "UNKNOWN", "evidence": None, "reason": reason}


def _real(status, evidence, reason):
    return {"status": status, "evidence": evidence, "reason": reason}


_PRE_GATE_PRODUCTS_LOWER = {p.strip().lower() for p in PRE_GATE_PRODUCTS}


def is_pre_gate_product(title):
    """Real bug found live (2026-07-22): the real Paddle product title
    ("Workflow Automation System...") and the real market_hunter seed
    niche text it was scored under ("workflow automation system...")
    differ only in case -- an exact, case-sensitive match silently
    failed to recognize an already-shipped product as pre-gate, which
    would have incorrectly REJECTED it instead of reporting its honest
    PRE_GATE status. Case-insensitive comparison fixes this for real."""
    return bool(title) and title.strip().lower() in _PRE_GATE_PRODUCTS_LOWER


# ══════════════════════════════════════════════════════════════════
# PART 1 — Product Review Gate (10 named reviews)
# ══════════════════════════════════════════════════════════════════

def review_legal(niche):
    """Honest proxy, not a real legal review: reuses executive_quality_
    gate.check_legal_compliance_risk() (safety_filter.py + QUARANTINE.md
    history) directly, no new logic. Always disclosed as partial."""
    import executive_quality_gate as eqg
    result = eqg.check_legal_compliance_risk(niche)
    result = dict(result)
    result["reason"] = "[مراجعة تقريبية، ليست مراجعة قانونية حقيقية] " + result["reason"]
    return result


def review_security(product_chapters=None):
    """Honest proxy, not a real security review: a real, deterministic
    scan for content that advises an insecure practice. No penetration
    test, no code audit -- this factory ships no software to audit."""
    if not product_chapters:
        return _unknown("لا محتوى منتج مُقدَّم للفحص — [مراجعة تقريبية فقط، ليست مراجعة أمنية حقيقية]")
    combined = " ".join((c.get("content") or "") for c in product_chapters if isinstance(c, dict)).lower()
    hits = [p for p in SECURITY_RISK_PHRASES if p in combined]
    if hits:
        return _real("FAIL", hits, f"[مراجعة تقريبية] المحتوى ينصح بممارسة غير آمنة: {', '.join(hits)}")
    return _real("PASS", None, "[مراجعة تقريبية، ليست مراجعة أمنية حقيقية] لا نصائح غير آمنة معروفة في النص")


def review_privacy(product_chapters=None, collects_real_customer_data=False):
    """Honest proxy: for the static-blueprint products this factory
    ships today, no customer data is collected through the product
    itself -- collects_real_customer_data defaults False and should only
    ever be set True once a real data-collecting product actually
    exists, which none does today."""
    if not collects_real_customer_data:
        return _real("PASS", None, "[مراجعة تقريبية] لا جمع بيانات عملاء حقيقي يحدث عبر هذا المنتج")
    if not product_chapters:
        return _unknown("المنتج يجمع بيانات عملاء حقيقية حسب الوصف لكن لا محتوى مُقدَّم لفحص وجود ضمانات خصوصية حقيقية")
    combined = " ".join((c.get("content") or "") for c in product_chapters if isinstance(c, dict)).lower()
    if "privacy" not in combined and "خصوصية" not in combined:
        return _real("FAIL", None, "[مراجعة تقريبية] المنتج يجمع بيانات عملاء حسب الوصف، لكن لا ذِكر لضمانات خصوصية في المحتوى")
    return _real("PASS", None, "[مراجعة تقريبية] المحتوى يذكر ضمانات خصوصية حقيقية")


def review_operational(ladder, product_family=None):
    import executive_quality_gate as eqg
    return eqg.check_delivery_capability(ladder, product_family)


def review_financial(cost_log_file=None):
    import executive_quality_gate as eqg
    return eqg.check_operational_cost(cost_log_file)


def review_scalability(components):
    import executive_quality_gate as eqg
    return eqg.check_scalability(components)


def review_maintenance(production_id=None, changelog_path=None):
    """Real check: does a real changelog entry exist (dossier_bundle.
    build_bundle._append_changelog()'s real, already-existing history)?
    Honestly FAIL/absent for any product generated outside that
    pipeline -- true of all 5 pre-gate products, which is a real,
    disclosed finding, not something to paper over."""
    path = Path(changelog_path) if changelog_path else DEFAULT_CHANGELOG_PATH
    if not production_id or not path.exists():
        return _real("FAIL", None, "لا معرّف إنتاج (production_id) أو لا سجل تغييرات موجود لهذا المنتج")
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("production_id") == production_id:
                return _real("PASS", entry, f"سجل تغييرات حقيقي موجود، الإصدار {entry.get('version')}")
    return _real("FAIL", None, f"لا سجل تغييرات حقيقي موجود لـ production_id={production_id!r}")


def review_customer_success(niche):
    """Auto-consumes market_evidence.py's real retention/objection
    signals for this niche (Market Learning Loop, ADR-088). Honestly
    Unknown while zero real customer interactions have been logged --
    true for every niche in this factory today."""
    import market_evidence
    retention = market_evidence.get_retention_signal(niche)
    objections = market_evidence.read_evidence(niche, "customer_objection")
    if retention is None and not objections:
        return _unknown("صفر تفاعل عملاء حقيقي مسجَّل بعد لهذا النيتش في Market Evidence Ledger")
    if retention and retention["churned"] > retention["renewed"]:
        return _real("FAIL", retention, f"{retention['churned']} تسرّب حقيقي أكثر من {retention['renewed']} تجديد")
    return _real("INFO", {"retention": retention, "objections": len(objections)}, f"دليل عملاء حقيقي: {len(objections)} اعتراض مسجَّل")


def review_support(has_support_contact=False, has_refund_policy=False):
    """Real, honest boolean check -- not a subjective score. Correctly
    FAILs today for all 5 pre-gate products: the Commercialization Audit
    (2026-07-22) confirmed zero refund policy and zero support contact
    exist anywhere in this factory as of this writing."""
    missing = []
    if not has_support_contact:
        missing.append("لا جهة اتصال دعم حقيقية منشورة")
    if not has_refund_policy:
        missing.append("لا سياسة استرجاع حقيقية منشورة")
    if missing:
        return _real("FAIL", {"has_support_contact": has_support_contact, "has_refund_policy": has_refund_policy}, "؛ ".join(missing))
    return _real("PASS", {"has_support_contact": True, "has_refund_policy": True}, "جهة اتصال دعم وسياسة استرجاع حقيقيتان موجودتان")


def review_competitive_moat(defensibility_field):
    import executive_quality_gate as eqg
    return eqg.check_defensibility(defensibility_field)


REVIEW_TYPES = (
    "legal", "security", "privacy", "operational", "financial",
    "scalability", "maintenance", "customer_success", "support", "competitive_moat",
)


def run_product_review(spec):
    """Runs all 10 named reviews. `spec` mirrors executive_quality_gate's
    spec shape, plus product-review-specific fields: product_chapters,
    production_id, collects_real_customer_data, has_support_contact,
    has_refund_policy."""
    snap = spec.get("evaluation_snapshot") or {}
    components = snap.get("components") or {}
    return {
        "legal": review_legal(spec.get("niche")),
        "security": review_security(spec.get("product_chapters")),
        "privacy": review_privacy(spec.get("product_chapters"), spec.get("collects_real_customer_data", False)),
        "operational": review_operational(spec.get("ladder"), spec.get("product_family")),
        "financial": review_financial(spec.get("cost_log_file")),
        "scalability": review_scalability(components),
        "maintenance": review_maintenance(spec.get("production_id"), spec.get("changelog_path")),
        "customer_success": review_customer_success(spec.get("niche")),
        "support": review_support(spec.get("has_support_contact", False), spec.get("has_refund_policy", False)),
        "competitive_moat": review_competitive_moat(snap.get("defensibility")),
    }


# ══════════════════════════════════════════════════════════════════
# PART 2 — Opportunity Risk Register
# ══════════════════════════════════════════════════════════════════

def build_risk_register(spec):
    """Reframes real, already-computed Executive Quality Gate fields
    into the 8 named risk categories -- no new scoring, pure re-
    presentation of real data under risk-framed headers. Exit criteria
    and kill-switch conditions are real, evidence-triggered rules (same
    pattern as the Kill-Test Verdict's decision framework, 2026-07-22),
    never a predicted probability."""
    import executive_quality_gate as eqg
    gate_result = eqg.run_executive_quality_gate(spec)
    c = gate_result["criteria"]
    return {
        "niche": spec.get("niche"),
        "market_risk": c["market_saturation_competitor_quality"],
        "technical_risk": c["technical_feasibility"],
        "regulatory_risk": c["legal_compliance_risk"],
        "competitive_risk": c["defensibility"],
        "execution_risk": c["data_confidence_score"],
        "exit_criteria": [
            "لا رد حقيقي واحد بعد أسبوع + متابعة واحدة على التواصل البارد (انظر Validation Sprint)",
            "اعتراض سعري حقيقي واحد على الأقل يفوق أي إشارة إيجابية (willingness_to_pay_evidence)",
            "منافس رائد حقيقي (Enterprise Leader) جديد يظهر بعد القبول",
        ],
        "failure_scenarios": [
            "صفر مبيعات حقيقية خلال 90 يوماً من إطلاق تواصل حقيقي فعلي",
            "قرار المصنع نفسه يتحول لاحقاً من ACCEPTED إلى DEFERRED (انظر ADR-086/087 لحالة حقيقية سابقة)",
        ],
        "kill_switch_conditions": [
            "human_review_required=True لأكثر من 3 معايير حرجة في نفس الوقت",
            "final_decision=REJECTED من Executive Quality Gate",
        ],
        "gate_result": gate_result,
    }


# ══════════════════════════════════════════════════════════════════
# PART 3 — Documentation completeness (product-type-aware, honest)
# ══════════════════════════════════════════════════════════════════

def check_documentation_completeness(product_type="static_pdf", changelog_entry_exists=False):
    """Honest, product-type-aware: this factory ships static PDF
    blueprints, not hosted software. Admin/disaster-recovery/incident-
    response documentation are real requirements for a hosted product
    with an admin panel and live infrastructure -- neither exists for a
    static PDF, so they are marked N/A, never fabricated with invented
    content to fill a checklist."""
    if product_type == "static_pdf":
        return {
            "technical_documentation": _real("PASS", None, "المحتوى نفسه هو التوثيق التقني/الاستخدامي"),
            "user_documentation": _real("PASS", None, "المحتوى نفسه هو التوثيق التقني/الاستخدامي"),
            "admin_documentation": _real("NOT_APPLICABLE", None, "لا لوحة تحكم إدارية لملف PDF ثابت"),
            "maintenance_documentation": _real("PASS", None, "دليل الإرشادات ضمن المحتوى نفسه") if changelog_entry_exists else _real("FAIL", None, "لا سجل تغييرات حقيقي بعد"),
            "disaster_recovery_documentation": _real("NOT_APPLICABLE", None, "لا بنية تحتية حية تُدار لملف PDF ثابت — انظر DISASTER_RECOVERY_PLAN.md لحماية المصنع نفسه"),
            "incident_response_documentation": _real("NOT_APPLICABLE", None, "لا خدمة حية لملف PDF ثابت لتتطلب استجابة حوادث"),
            "version_history": _real("PASS", None, "موجود") if changelog_entry_exists else _real("FAIL", None, "لا سجل إصدارات حقيقي بعد"),
            "changelog": _real("PASS", None, "موجود") if changelog_entry_exists else _real("FAIL", None, "لا سجل تغييرات حقيقي بعد"),
        }
    return {k: _unknown(f"نوع منتج غير مغطّى بعد بمنطق حقيقي: {product_type}") for k in (
        "technical_documentation", "user_documentation", "admin_documentation",
        "maintenance_documentation", "disaster_recovery_documentation",
        "incident_response_documentation", "version_history", "changelog",
    )}


# ══════════════════════════════════════════════════════════════════
# PART 4 — Risk Intelligence Engine (on-demand -- no scheduler exists)
# ══════════════════════════════════════════════════════════════════

def run_risk_intelligence_scan(niche, refresh_competitors=False):
    """On-demand, not continuous -- this factory has no scheduler
    (CLAUDE.md), and pretending otherwise here would repeat the exact
    fabrication this whole engagement has refused everywhere else. Real
    signals: new/changed competitors (competitor_discovery.py, cache-
    only unless refresh_competitors=True is explicitly requested by a
    human), customer complaints (market_evidence.py), market saturation
    (executive_quality_gate.py), and (Executive Board Integration,
    2026-07-23) the real Threat Engine assessment (competitor_discovery.
    compute_threat_assessment()) over whatever competitor snapshot is
    already cached -- never a fresh network call from this path.
    Regulation changes, pricing changes elsewhere in the market, broad
    technology disruption, and demand decline have NO real, funded data
    source in this factory today -- reported as permanent, disclosed
    gaps, never faked with a shallow check dressed up as real
    intelligence."""
    import executive_quality_gate as eqg
    import market_evidence
    import competitor_discovery

    if refresh_competitors:
        competitor_discovery.get_or_refresh_competitors(niche, force=True)

    saturation = eqg.check_market_saturation(niche)
    complaints = market_evidence.read_evidence(niche, "customer_objection")

    cache_key = re.sub(r"\s+", " ", (niche or "").strip().lower())
    cached_snapshot = competitor_discovery.load_database().get(cache_key)
    if cached_snapshot:
        threat_assessment = competitor_discovery.compute_threat_assessment(cached_snapshot)
    else:
        threat_assessment = {
            dim: {
                "level": "Unknown", "score": None,
                "basis": "لا بيانات منافسين مخزَّنة لهذا النيتش بعد — لم يُشغَّل اكتشاف منافسين حقيقي",
            }
            for dim in (
                "competitor_saturation", "market_concentration", "new_entrant_trajectory",
                *competitor_discovery.THREAT_DIMENSIONS_WITHOUT_REAL_DATA.keys(),
            )
        }

    return {
        "niche": niche,
        "new_competitors": saturation,
        "market_saturation": saturation,
        "customer_complaints": {
            "count": len(complaints), "detail": complaints,
        } if complaints else _unknown("صفر شكاوى عملاء حقيقية مسجَّلة بعد لهذا النيتش"),
        "regulation_changes": _unknown("لا مصدر بيانات حقيقي ممول لتتبع تغييرات تنظيمية في هذا المصنع — فجوة دائمة، غير مُغطّاة"),
        "pricing_changes": _unknown("لا تتبّع تاريخي حقيقي لأسعار المنافسين مخزَّن بعد — يحتاج تشغيلات متكررة حقيقية لمقارنتها"),
        "technology_disruption": _unknown("لا مصدر بيانات حقيقي موثوق لرصد اضطراب تقني واسع في هذا المصنع — فجوة دائمة، غير مُغطّاة"),
        "demand_decline": _unknown("لا آلية تتبّع طلب حقيقية عبر الزمن في هذا المصنع — فجوة دائمة، غير مُغطّاة"),
        "threat_assessment": threat_assessment,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════════
# PART 5 — Business Continuity Engine (reuses real recovery/ infra)
# ══════════════════════════════════════════════════════════════════

def run_backup_now(reason, paths=None):
    """Thin wrapper over recovery.snapshot.snapshot_before() -- the
    real, already-existing backup mechanism (Unified Recovery System
    §7). Not reimplemented."""
    from recovery import snapshot
    return snapshot.snapshot_before(reason, paths=paths)


def check_dependency_health():
    """Real, on-demand config-presence check for this factory's real
    external dependencies (Groq, Paddle, Telegram) -- confirms each key
    is configured, not that the live service is currently reachable
    (a real network ping is a separate, heavier on-demand action, same
    "no live call from inside a cheap check" discipline as every other
    scoring path here). Missing configuration is reported honestly, not
    assumed fine."""
    import os
    checks = {}
    for name, env_var in (("groq", "GROQ_KEY"), ("paddle", "PADDLE_API_KEY"), ("telegram", "TELEGRAM_BOT_TOKEN")):
        configured = bool(os.environ.get(env_var))
        checks[name] = _real("PASS" if configured else "FAIL", {"env_var": env_var}, "مُهيَّأ" if configured else f"{env_var} غير مُهيَّأ")
    return checks


# ══════════════════════════════════════════════════════════════════
# PART 6 — Customer Trust Layer
# ══════════════════════════════════════════════════════════════════

def compute_quality_score(inspection_result):
    """Reuses inspectors.py's real Dual Inspection result directly --
    no new quality logic."""
    if not isinstance(inspection_result, dict):
        return _unknown("لا نتيجة فحص جودة حقيقية (Dual Inspection) متاحة")
    technical_passed = (inspection_result.get("technical") or {}).get("passed")
    commercial_passed = (inspection_result.get("commercial") or {}).get("passed")
    if technical_passed and commercial_passed:
        return _real("PASS", inspection_result, "فحص جودة حقيقي (Dual Inspection) ناجح بالكامل")
    return _real("FAIL", inspection_result, f"فحص تقني={technical_passed}، فحص تجاري={commercial_passed}")


def compute_evidence_score(gate_result):
    """Real ratio of KNOWN vs UNKNOWN criteria from a real Executive
    Quality Gate run -- never a fabricated 0-100 number, an honest
    fraction of real evidence coverage."""
    if not isinstance(gate_result, dict) or "criteria" not in gate_result:
        return _unknown("لا نتيجة Executive Quality Gate حقيقية متاحة")
    criteria = gate_result["criteria"]
    known = sum(1 for v in criteria.values() if v["status"] != "UNKNOWN")
    total = len(criteria)
    return _real("INFO", {"known": known, "total": total}, f"{known}/{total} معيار حقيقي معروف (الباقي Unknown صادق)")


def compute_trust_score(quality_score, evidence_score, has_support_contact=False, has_refund_policy=False):
    """Real aggregate of three already-real signals -- never a single
    invented number presented as an objective 'trust' metric on its
    own."""
    return {
        "quality": quality_score,
        "evidence": evidence_score,
        "support_contact_exists": has_support_contact,
        "refund_policy_exists": has_refund_policy,
        "note": "تجميع معلوماتي لثلاث إشارات حقيقية مستقلة -- ليس رقماً واحداً مُختلَقاً",
    }


def build_transparency_report(spec):
    """The real, honest report a real customer or the founder could
    read: what's actually known, what's actually unknown, sourced
    directly from the Executive Quality Gate's own written explanation
    plus real market evidence -- zero new narrative generated."""
    import executive_quality_gate as eqg
    import market_evidence
    gate_result = eqg.run_executive_quality_gate(spec)
    evidence_summary = market_evidence.summarize_niche(spec.get("niche")) if spec.get("niche") else None
    return {
        "niche": spec.get("niche"),
        "gate_written_explanation": gate_result["written_explanation"],
        "final_decision": gate_result["final_decision"],
        "market_evidence_summary": evidence_summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


_CITATION_PATTERN = re.compile(r"(according to|per|source:|\bcites?\b)", re.IGNORECASE)


def check_source_verification(product_chapters, cited_sources=None):
    """Real check: if content makes an attributed claim ("according
    to...", "per...") with no corresponding real source listed, that is
    an honest FAIL -- an unverifiable claim dressed as sourced. Products
    with zero attributed claims (most of this factory's hand-written
    blueprints) correctly PASS with nothing to verify."""
    if not product_chapters:
        return _unknown("لا محتوى منتج مُقدَّم للفحص")
    combined = " ".join((c.get("content") or "") for c in product_chapters if isinstance(c, dict))
    attributed_claims = _CITATION_PATTERN.findall(combined)
    if attributed_claims and not cited_sources:
        return _real("FAIL", {"attributed_claims": len(attributed_claims)}, f"{len(attributed_claims)} ادّعاء مُنسَب حقيقي في النص بلا مصدر حقيقي مرفق")
    return _real("PASS", None, "لا ادّعاءات مُنسَبة بلا مصدر في النص")


def get_audit_trail(niche):
    """Formalizes real, already-existing audit trails this factory
    built long before this directive -- data/decisions.jsonl (every real
    scoring decision), books/_generation_log.jsonl (every real
    generation attempt), data/product_changelog.jsonl (every real
    version). Not rebuilt -- queried directly."""
    from decision_engine import ranking
    trail = {"niche": niche, "decisions": [], "generations": [], "changelog_entries": []}

    for d in ranking.rank_all():
        if d.get("niche") == niche:
            trail["decisions"].append({"decided_at": d.get("decided_at"), "status": d.get("status"), "decision_id": d.get("decision_id")})

    gen_log = _FACTORY_ROOT / "books" / "_generation_log.jsonl"
    if gen_log.exists():
        with open(gen_log, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("topic") == niche or entry.get("title") == niche:
                    trail["generations"].append({"logged_at": entry.get("timestamp"), "file": entry.get("file")})

    if DEFAULT_CHANGELOG_PATH.exists():
        with open(DEFAULT_CHANGELOG_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("title") == niche:
                    trail["changelog_entries"].append(entry)

    return trail


# ══════════════════════════════════════════════════════════════════
# MASTER GATE — prospective only, per the founder's explicit decision
# ══════════════════════════════════════════════════════════════════

def run_enterprise_readiness_gate(spec):
    """The full Enterprise Readiness Layer, composed. Applies
    PROSPECTIVELY ONLY, per the founder's explicit 2026-07-22 decision:
    a pre-gate product (PRE_GATE_PRODUCTS) is reported honestly with its
    real pre-gate status, never silently re-flagged as REJECTED by this
    function alone."""
    title = spec.get("title") or spec.get("niche")
    pre_gate = is_pre_gate_product(title)

    product_review = run_product_review(spec)
    risk_register = build_risk_register(spec)
    documentation = check_documentation_completeness(
        spec.get("product_type", "static_pdf"), bool(spec.get("production_id")),
    )
    transparency_report = build_transparency_report(spec)

    hard_fails = [name for name, r in product_review.items() if r["status"] == "FAIL"]

    if pre_gate:
        final_status = "PRE_GATE — لم يُطبَّق هذا الحاجز عليه رجعياً بقرار المؤسس الصريح 2026-07-22"
    elif hard_fails:
        final_status = "REJECTED"
    else:
        final_status = "APPROVED"

    return {
        "niche": spec.get("niche"),
        "title": title,
        "pre_gate_product": pre_gate,
        "product_review": product_review,
        "risk_register": risk_register,
        "documentation_completeness": documentation,
        "transparency_report": transparency_report,
        "hard_failures": hard_fails,
        "final_status": final_status,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

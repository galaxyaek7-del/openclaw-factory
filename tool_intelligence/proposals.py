"""
Tool Intelligence -- Autonomous Digital Company v1, Track B3 (2026-07-19).
Made dynamic -- Executive Intelligence Core, Round 2 (2026-07-29).

"The system should produce integration proposals instead of assuming
tools exist" (the founder's own instruction, verbatim). Every proposal
here is a real, dated, evidence-cited recommendation grounded in a gap
this session's own work actually found -- never a generic "you should
use X" pitch with no tie to this factory's real state. Matches the
existing ADR-024-style "(مقترَح، لا تنفيذ)" -- "proposed, not
implemented" -- convention already used in OpenClaw_Brain/00_Governance/:
a proposal is a structured recommendation, not an installation or a live
integration.

Every proposal carries exactly the six fields the founder asked for --
why it's needed, expected business value, implementation effort,
estimated ROI, dependencies, and risks -- each grounded in a real,
specific, cited fact about this factory. Where a real number (ROI, risk
probability) doesn't exist yet, the field says so honestly instead of
inventing one -- same discipline as economics.py's price_landscape()
("NO DEMAND MODEL EXISTS...").

Round 2 (2026-07-29): list_proposals() used to return only the 3
hand-written entries below, unchanged since 2026-07-19 -- real and
evidence-cited when written, but never regenerated as new evidence
accumulated, which the founder's "generates improvement proposals
automatically... nothing evolves randomly" Executive Intelligence Core
directive calls out directly. list_proposals() now also computes fresh
proposals at call time from the SAME real signals evolution_engine.py
already assembles (bottlenecks, technical debt, capability gaps) --
deterministic templating, never an LLM call (same discipline as
contract_generator.py/invoice_generator.py), and honestly produces zero
dynamic proposals when a signal detects nothing real to act on.
"""

from datetime import datetime, timezone

SEED_PROPOSALS = [
    {
        "id": "vector_store_for_evidence_corpus",
        "tool": "A local, embeddable vector store (e.g. sqlite-vec or Chroma) for Golden Hunter/Pioneer's evidence corpus",
        "status": "مقترَح، لا تنفيذ",
        "why_needed": (
            "Golden Hunter + Pioneer append real evidence continuously to "
            "data/golden_hunter_events.jsonl and reports/tier1_intake candidates. "
            "The only lookup mechanism today is a linear JSONL scan "
            "(factory_loop.js's checkGoldenStagnation()/goldenNicheAlreadyAttempted()) "
            "-- fine at today's real volume, but growing linearly with every real "
            "cycle, with no way to detect a niche that's semantically similar "
            "(not just string-identical) to one already rejected or attempted."
        ),
        "expected_business_value": (
            "Faster, smarter opportunity de-duplication as the real evidence "
            "corpus grows -- avoids re-evaluating niches that are semantically "
            "similar to ones already rejected/attempted, not just exact string matches."
        ),
        "implementation_effort": (
            "متوسط -- needs an embedding step at the existing append points "
            "(could reuse Groq or a small local model) plus a new query module; "
            "no schema migration, since the JSONL files stay the real source of "
            "truth and the vector store is a derived, rebuildable index."
        ),
        "estimated_roi": "غير مقاس بعد -- لا يوجد دليل حقيقي على تقييم مكرَّر تم إهداره حتى الآن؛ يصبح قابلاً للقياس عند رصد أول حالة تشابه حقيقية.",
        "dependencies": [
            "حجم حقيقي كافٍ من الأدلة المتراكمة (اليوم: حقيقي لكن ما زال صغيراً)",
            "مصدر تضمين (embedding) -- Groq أو نموذج محلي",
        ],
        "risks": [
            "تعقيد إضافي مقابل فائدة غير مقاسة بعد على الحجم الحقيقي",
            "فهرس مشتق قد ينحرف بصمت عن مصدر الحقيقة (JSONL) إن لم يُعَد بناؤه بانضباط",
        ],
        "evidence": "factory_loop.js's own checkGoldenStagnation()/goldenNicheAlreadyAttempted() -- both real, both currently linear-scan only.",
    },
    {
        "id": "image_diff_for_visual_cover_qa",
        "tool": "A lightweight image-diff library (e.g. Pillow-based pixel/structural diff) for generated book covers -- Playwright only if the cover pipeline ever moves to HTML/CSS rendering",
        "status": "مقترَح، لا تنفيذ",
        "why_needed": (
            "quality_doctor.py was found (Strategic Phase audit, 2026-07-19) to be "
            "functionally fake -- every _check_*() method fabricates a fix string "
            "without ever rendering or visually inspecting the actual generated "
            "cover. inspectors.py's Dual Inspection is the real QA gate today, but "
            "it has no visual check of cover_designer_v2.py's real PNG output "
            "beyond file-existence."
        ),
        "expected_business_value": (
            "A real, automated visual regression check (e.g. cover text isn't "
            "clipped, colors render as configured) before a product reaches KDP -- "
            "catching a real class of defect no current check covers."
        ),
        "implementation_effort": (
            "منخفض إلى متوسط -- cover_designer_v2.py already outputs a real PIL-"
            "rendered PNG, so a Pillow-based image diff is the lighter-weight fit; "
            "Playwright (a full browser binary) would only be justified if the "
            "cover pipeline moves to HTML/CSS rendering, which it doesn't today."
        ),
        "estimated_roi": "غير مقاس بعد -- لا يوجد رفض حقيقي من KDP يُعزى لعيب بصري في الغلاف حتى الآن لقياس الأثر عليه.",
        "dependencies": ["قرار مؤسِّس بشأن ما إذا كان مسار الأغلفة سيبقى قائماً على PIL أم ينتقل إلى HTML/CSS"],
        "risks": [
            "اقتراح Playwright تحديداً يضيف تبعية ثقيلة حقيقية (متصفح كامل) لمشكلة قد تُحل بأداة أخف بكثير إن بقي مسار الأغلفة على PIL",
            "لا يوجد عيب حقيقي مرصود بعد لتحديد أولوية هذا مقابل أعمال أخرى",
        ],
        "evidence": "OpenClaw_Brain/00_Governance's own Strategic Phase audit finding on quality_doctor.py's fabricated _check_*() methods; cover_designer_v2.py as the real, live cover engine.",
    },
    {
        "id": "second_ai_provider_credential_for_comparison",
        "tool": "One additional AI provider credential (e.g. ANTHROPIC_API_KEY or OPENAI_API_KEY) -- not a software tool, but the single highest-leverage unblock for ai_capability/'s own registry",
        "status": "مقترَح، لا تنفيذ",
        "why_needed": (
            "ai_capability/registry.py (Track B2, 2026-07-19) can only ever report "
            "DISCOVERY-level (unmeasured) metrics for every provider except Groq, "
            "because zero credentials for any other provider exist in .env. This is "
            "the literal blocker on the founder's own explicit ask -- 'compare AI "
            "systems using measurable metrics only' -- ever becoming a real multi-"
            "provider comparison."
        ),
        "expected_business_value": (
            "Turns the AI Capability Registry from a single-provider report into a "
            "genuinely comparative one -- real quality/speed/cost data across at "
            "least two providers, informing real model-routing decisions per task type."
        ),
        "implementation_effort": (
            "منخفض -- قرار مؤسِّس + سطر واحد في .env؛ الكود في registry.py/"
            "evaluator.py يدعم بالفعل أي مزوّد له استخدام حقيقي مسجَّل دون أي تعديل "
            "إضافي بمجرد وجود بيانات اعتماد واستدعاء حقيقي واحد على الأقل."
        ),
        "estimated_roi": "غير مقاس بعد -- يعتمد كلياً على المزوّد ونوع المهمة؛ يصبح قابلاً للقياس فور وجود بيانات مقارنة حقيقية.",
        "dependencies": ["قرار الرئيس بشأن أي مزوّد يُضاف أولاً", "بيانات اعتماد حقيقية + استدعاء حقيقي واحد على الأقل مسجَّل"],
        "risks": ["مزوّد API ثانٍ مدفوع يضيف تكلفة متكرِّرة حقيقية دون عائد مثبت بعد -- يُفضَّل البدء بأصغر حِمل عمل حقيقي، لا استبدال شامل"],
        "evidence": "ai_capability/registry.py's own PROVIDER_CATALOG -- 8 من 9 مزوّدين اليوم DISCOVERY-level لسبب واحد فقط: غياب بيانات الاعتماد.",
    },
]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _bottleneck_proposal(decisions_path=None, outcomes_path=None, timeline_path=None):
    from executive_intelligence import bottlenecks as bottleneck_module
    from executive_intelligence import engine_health as engine_health_module

    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    result = bottleneck_module.detect_bottlenecks(health, decisions_path=decisions_path, outcomes_path=outcomes_path)
    if not result.get("detected"):
        return None

    items = result["items"]
    evidence_lines = [i["evidence"] for i in items]
    return {
        "id": "fix_detected_bottlenecks",
        "tool": f"Investigate and resolve {len(items)} real detected bottleneck(s)",
        "status": "مقترَح، لا تنفيذ",
        "why_needed": "اختناقات حقيقية اكتُشِفت اليوم من بيانات المصنع الفعلية: " + "؛ ".join(evidence_lines[:5]),
        "expected_business_value": "إزالة عائق حقيقي يبطئ دورة القرار→الإنتاج→النشر لكل فرصة تعتمد على المرحلة المتأثرة.",
        "implementation_effort": "غير مقاس بعد -- يحتاج تشخيصاً هندسياً حقيقياً لكل حالة على حدة.",
        "estimated_roi": "غير مقاس بعد -- الأثر يعتمد على عدد الفرص الحقيقية المتأثرة فعلياً بهذا الاختناق.",
        "dependencies": ["تشخيص هندسي حقيقي للسبب الجذري لكل اختناق مُدرَج قبل أي إصلاح"],
        "risks": ["استمرار الاختناق يؤخر كل فرصة حقيقية تمر بهذه المرحلة"],
        "evidence": "executive_intelligence.bottlenecks.detect_bottlenecks() -- " + "؛ ".join(evidence_lines[:5]),
        "generated_at": _now(),
    }


def _technical_debt_proposal(decisions_path=None, timeline_path=None, sales_ledger_path=None):
    from strategic_intelligence import technical_debt as tech_debt_module

    result = tech_debt_module.components_at_risk_of_technical_debt(
        decisions_path=decisions_path, timeline_path=timeline_path, sales_ledger_path=sales_ledger_path,
    )
    if result.get("answer") == "Unknown":
        return None

    components = result["answer"]
    return {
        "id": "review_inactive_components",
        "tool": f"Review {len(components)} real component(s) at risk of technical debt: {', '.join(components)}",
        "status": "مقترَح، لا تنفيذ",
        "why_needed": "مكوّنات حقيقية لم تشهد أي نشاط فعلي بعد (data/orchestrator_timeline.jsonl/sales_ledger.jsonl) -- قد تكون معطَّلة بصمت أو غير مُستخدَمة فعلياً.",
        "expected_business_value": "تأكيد أن كل مكوّن مسجَّل يعمل فعلاً أو إزالته إن كان زائداً -- يقلّل سطح الصيانة الحقيقي.",
        "implementation_effort": "منخفض -- مراجعة يدوية قصيرة لكل مكوّن مُدرَج.",
        "estimated_roi": "غير مقاس بعد.",
        "dependencies": [],
        "risks": ["مكوّن حقيقي ولكنه نادر الاستخدام قد يُزال بالخطأ إن لم تُراجَع الأسباب أولاً"],
        "evidence": result["source"],
        "generated_at": _now(),
    }


def _capability_gap_proposal(capability_registry_path=None):
    from capability_registry_scanner import find_capability_gaps

    gaps = find_capability_gaps(registry_path=capability_registry_path)
    discovery = gaps.get("discovery_level", [])
    if not discovery:
        return None

    names = [c.get("name", c.get("id")) for c in discovery[:5]]
    return {
        "id": "close_capability_gaps",
        "tool": f"Close {len(discovery)} real capability gap(s) at DISCOVERY level: {', '.join(str(n) for n in names)}",
        "status": "مقترَح، لا تنفيذ",
        "why_needed": f"config/capability_registry.json يُدرِج {len(discovery)} قدرة عند مستوى DISCOVERY (غير مقاسة بعد) من أصل {gaps.get('total_capabilities', 0)}.",
        "expected_business_value": "قرارات حقيقية مبنية على قياس فعلي بدل تقدير غير مؤكَّد لكل قدرة مُدرَجة.",
        "implementation_effort": "يختلف حسب القدرة المحدَّدة -- راجع كل إدخال في السجل على حدة.",
        "estimated_roi": "غير مقاس بعد.",
        "dependencies": ["مصدر قياس حقيقي لكل قدرة (استخدام فعلي مسجَّل، أو اختبار مباشر)"],
        "risks": ["الاستمرار دون قياس يعني قرارات مبنية على تقدير غير مؤكَّد"],
        "evidence": gaps.get("source", "config/capability_registry.json"),
        "generated_at": _now(),
    }


def _customer_funnel_proposal(requests_path=None, state_path=None):
    """Autonomous Company Evolution Engine, Round 3 (2026-07-29): a real
    proposal from customer_pipeline.py's own Observe signals (stuck-NEW,
    abandoned-at-PROPOSED) -- honestly returns None while zero real
    customer requests exist, same discipline as every other generator
    here."""
    from customer_pipeline import list_pipeline_overview

    overview = list_pipeline_overview(requests_path=requests_path, state_path=state_path)
    stuck = [a for a in overview.get("needs_attention", []) if a.get("stage") in ("NEW", "PROPOSED")]
    if not stuck:
        return None

    request_ids = [a["request_id"] for a in stuck[:5]]
    return {
        "id": "resolve_stuck_customer_requests",
        "tool": f"Resolve {len(stuck)} real customer request(s) stuck in the funnel: {', '.join(str(r) for r in request_ids)}",
        "status": "مقترَح، لا تنفيذ",
        "why_needed": f"customer_pipeline.list_pipeline_overview() يُظهر {len(stuck)} طلب عميل حقيقي عالق (NEW بلا تقدّم، أو PROPOSED بلا رد) -- إشارة تسرّب حقيقية في القمع.",
        "expected_business_value": "استرجاع عملاء حقيقيين محتملين قبل أن يُهجروا نهائياً -- تأثير مباشر على الإيرادات، لا تحسين تقني.",
        "implementation_effort": "يختلف حسب السبب -- راجع 'recovery' الحقيقي لكل طلب في القائمة.",
        "estimated_roi": "غير مقاس بعد -- يعتمد على قيمة كل طلب عالق فعلياً.",
        "dependencies": ["مراجعة يدوية لكل طلب عالق عبر Mission Control قبل أي إجراء تلقائي"],
        "risks": ["التواصل الآلي مع عميل حقيقي دون مراجعة بشرية قد يضر بالثقة -- هذا الاقتراح لا يُنفَّذ تلقائياً"],
        "evidence": "customer_pipeline.list_pipeline_overview()'s needs_attention",
        "generated_at": _now(),
    }


def _dynamic_proposals(decisions_path=None, outcomes_path=None, timeline_path=None,
                        sales_ledger_path=None, capability_registry_path=None,
                        requests_path=None, state_path=None):
    """Real proposals generated fresh from current factory signals -- the
    same signals evolution_engine.py/customer_pipeline.py already assemble,
    reused (not recomputed) here. Honestly returns fewer than 4 (down to
    zero) when a signal detects nothing real to act on -- never pads the
    list."""
    generators = [
        lambda: _bottleneck_proposal(decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path),
        lambda: _technical_debt_proposal(decisions_path=decisions_path, timeline_path=timeline_path, sales_ledger_path=sales_ledger_path),
        lambda: _capability_gap_proposal(capability_registry_path=capability_registry_path),
        lambda: _customer_funnel_proposal(requests_path=requests_path, state_path=state_path),
    ]
    return [p for p in (gen() for gen in generators) if p is not None]


def list_proposals(decisions_path=None, outcomes_path=None, timeline_path=None,
                    sales_ledger_path=None, capability_registry_path=None,
                    requests_path=None, state_path=None):
    """The hand-curated seed proposals (still real, still evidence-cited)
    plus proposals generated fresh from current factory signals -- computed
    at call time, not static after Round 2 (2026-07-29)."""
    return SEED_PROPOSALS + _dynamic_proposals(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
        sales_ledger_path=sales_ledger_path, capability_registry_path=capability_registry_path,
        requests_path=requests_path, state_path=state_path,
    )


def get_proposal(proposal_id, **kwargs):
    return next((p for p in list_proposals(**kwargs) if p["id"] == proposal_id), None)


def render_markdown_proposal(proposal):
    lines = [
        f"# {proposal['tool']}",
        "",
        f"**الحالة:** {proposal['status']}",
        "",
        "## لماذا يُحتاج إليه",
        proposal["why_needed"],
        "",
        "## القيمة التجارية المتوقَّعة",
        proposal["expected_business_value"],
        "",
        "## جهد التنفيذ",
        proposal["implementation_effort"],
        "",
        "## العائد المقدَّر",
        proposal["estimated_roi"],
        "",
        "## الاعتماديات",
    ]
    lines += [f"- {d}" for d in proposal["dependencies"]]
    lines += ["", "## المخاطر"]
    lines += [f"- {r}" for r in proposal["risks"]]
    lines += ["", "## الدليل", proposal["evidence"]]
    return "\n".join(lines)


def render_markdown_all():
    return "\n\n---\n\n".join(render_markdown_proposal(p) for p in list_proposals())

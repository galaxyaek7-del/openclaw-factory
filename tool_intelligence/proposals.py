"""
Tool Intelligence -- Autonomous Digital Company v1, Track B3 (2026-07-19).

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
"""

PROPOSALS = [
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


def list_proposals():
    return PROPOSALS


def get_proposal(proposal_id):
    return next((p for p in PROPOSALS if p["id"] == proposal_id), None)


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
    return "\n\n---\n\n".join(render_markdown_proposal(p) for p in PROPOSALS)

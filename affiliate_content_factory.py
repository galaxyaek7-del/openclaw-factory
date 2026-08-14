#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate Content Factory (directive 2026-08-14, section 5).

Generates ORIGINAL, useful, educational content for an adopted affiliate
program along the directive's chain:

  Problem -> Educational content -> Comparison -> Use case -> Tutorial
  -> Recommendation -> Affiliate CTA.

Honesty contract (hard, tested):
  * Content is written from the REAL fields of the portfolio opportunity
    (program name, commission/qualification data) and from the content
    input the caller supplies -- never from a guessed product.
  * We NEVER claim hands-on experience with a product we did not test.
    A "tried" claim only appears if the caller passes verified_usage=True;
    otherwise the tutorial is framed as "how this category solves the
    problem" + a link, never as personal hands-on usage.
  * Every generated piece ends with an explicit affiliate disclosure
    (required by the directive).
  * The company's description is never copied -- we write an original
    problem-first framing.
  * Deterministic: same inputs -> same output (no LLM, no randomness).
  * Zero cost: no API, no paid tool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class AffiliateContentInput:
    opportunity_id: str
    program_name: str
    product_category: str            # e.g. "cloud infrastructure"
    solves_problem: str              # the problem space it addresses
    target_audience: str
    commission_disclosure: str = ""  # short, e.g. "30% recurring for 12 months"
    verified_usage: bool = False     # TRUE only if we really tested it
    audience_angle: str = ""         # optional SEO/context angle


@dataclass
class AffiliateContentPiece:
    opportunity_id: str
    format: str                      # educational / comparison / usecase / tutorial / recommendation
    title: str
    body: str
    cta: str
    disclosure: str
    generated_at: Optional[str] = None


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


DISCLOSURE_TEMPLATE = (
    "إفصاح: هذا المحتوى يشمل روابط Affiliate لـ {program}. قد نتلقى عمولة "
    "عند الشراء عبر روابطنا بدون أي تكلفة إضافية عليك. نحن لا نوصي إلا بما "
    "نعتقد أنه مفيد لجمهورنا."
)


def _sentence(frag: str) -> str:
    return frag.strip().capitalize()


def build_affiliate_content(inp: AffiliateContentInput,
                            now: Optional[datetime] = None) -> List[AffiliateContentPiece]:
    """Generate the full Problem->CTA content chain for one adopted program."""
    ts = _now_iso(now)
    disclosure = DISCLOSURE_TEMPLATE.format(program=inp.program_name)

    pieces = []

    # 1) Educational content — problem-first, original framing
    educational_body = (
        f"{_sentence(inp.solves_problem)} هذا النوع من المشكلات شائع لدى {inp.target_audience}، "
        f"وغالبًا ما تؤدي المعالجة اليدوية إلى ضياع وقت ونتائج غير متسقة. "
        f"أفضل الممارسات في هذه الفئة ({inp.product_category}) تبدأ بفهم المطلوب بوضوح، ثم "
        f"اختيار أداة تلبي الحاجة دون تعقيد، ثم وضع روتين صغير قابل للتكرار. "
        f"هذا المقال تعليمي ولا يفرض خيارًا بعينه — انظر دائمًا إلى الخيارات المتعددة في الفئة."
    )
    pieces.append(AffiliateContentPiece(
        opportunity_id=inp.opportunity_id, format="educational",
        title=f"كيف تتعامل مع مشكلة {inp.solves_problem.strip().rstrip('.')}؟",
        body=educational_body,
        cta=f"للمقارنة مع أدوات عملية في {inp.product_category}، تابع القراءة.",
        disclosure=disclosure, generated_at=ts,
    ))

    # 2) Comparison — honest, category-level (we never copy the vendor)
    comparison_body = (
        f"عند مقارنة حلول {inp.product_category}، انظر إلى: التكلفة الحقيقية على المدى الطويل، "
        f"سهولة البدء، الجودة، والدعم. الأدوات في هذه الفئة تختلف في نقاط قوتها؛ "
        f"برنامج {inp.program_name} مصمم لفئة {inp.product_category} ويلائم {inp.target_audience}، "
        f"لكن المقارنة العادلة تقارن الاحتياج أولًا ثم الأداة. هذه فقرة مقارنة عامة على مستوى "
        f"الفئة — لا تدّعي أننا اختبرنا كل أداة."
    )
    pieces.append(AffiliateContentPiece(
        opportunity_id=inp.opportunity_id, format="comparison",
        title=f"مقارنة حلول {inp.product_category}: متى يكون {inp.program_name} خيارًا جيدًا؟",
        body=comparison_body,
        cta="شاهد حالة استخدام عملية أدناه.",
        disclosure=disclosure, generated_at=ts,
    ))

    # 3) Use case — real-world scenario, no hands-on claim unless verified
    if inp.verified_usage:
        usage_line = (
            f"استخدمنا {inp.program_name} لحل هذه الحالة، والنتيجة كانت متسقة مع المطلوب. "
            f"التجربة هنا مبنية على استخدامنا الفعلي."
        )
    else:
        usage_line = (
            f"لم نختبر {inp.program_name} بأيدينا بعد، لذا لا ندّعي تجربة شخصية. "
            f"هذه الحالة تعرض الخطوات المنطقية المتوقعة في هذه الفئة استنادًا إلى المواصفات الرسمية."
        )
    usecase_body = (
        f"سيناريو: لدى {inp.target_audience} مشكلة {inp.solves_problem.strip().rstrip('.')}. "
        f"{usage_line} الخطوة الأولى: تحديد المتطلبات الأساسية. الثانية: مراجعة خيارات "
        f"{inp.product_category} المتاحة. الثالثة: تقييم الشروط والعناية بالتجربة. "
        f"في هذه الفئة، ابدأ صغيرًا ثم قيّم النتيجة قبل التوسع."
    )
    pieces.append(AffiliateContentPiece(
        opportunity_id=inp.opportunity_id, format="usecase",
        title=f"حالة استخدام: {inp.solves_problem.strip().rstrip('.')}",
        body=usecase_body,
        cta="راجع الدليل العملي (tutorial) للخطوات التفصيلية.",
        disclosure=disclosure, generated_at=ts,
    ))

    # 4) Tutorial — process guidance, always honest about experience
    if inp.verified_usage:
        tutorial_step = (
            "بعد التجربة الفعلية، نوصي بالتسلسل: أنشئ حسابك، ارفع مشروعك الأول، "
            "اضبط الإعدادات الأساسية، ثم قيّم النتائج على أسبوع."
        )
    else:
        tutorial_step = (
            "هذا دليل إجرائي عام للفئة (ليس دليل استخدام موثّقًا لأننا لم نختبر الأداة): "
            "حدّد النتيجة المرجوة، أنشئ حساب تجريبي في الحل المختار، اتبع معالج الإعداد الرسمي، "
            "ثم قيّم التوافق مع حاجتك. تحقق من الشروط الرسمية قبل الالتزام."
        )
    tutorial_body = (
        f"{_sentence(inp.solves_problem)} يتطلب خطوات واضحة: "
        f"(1) {tutorial_step} "
        f"(2) قارن قبل الدفع ولا توقع على التزام طويل دون فهم الشروط. "
        f"(3) احتفظ بسجل لتقييم النتيجة."
    )
    pieces.append(AffiliateContentPiece(
        opportunity_id=inp.opportunity_id, format="tutorial",
        title=f"دليل خطوة بخطوة: التعامل مع {inp.product_category}",
        body=tutorial_body,
        cta="إلى التوصية والرابط.",
        disclosure=disclosure, generated_at=ts,
    ))

    # 5) Recommendation + CTA — only frames the program as a candidate
    rec_body = (
        f"بناءً على المعايير أعلاه، {inp.program_name} يعد خيارًا معقولًا ضمن "
        f"فئة {inp.product_category} لمن هم ضمن {inp.target_audience} — ليس التوصية الوحيدة، "
        f"ولكنه يستحق التقييم. إن اخترت المتابعة عبر الرابط أدناه فقد ندعم تحسين هذا المحتوى "
        f"بدون كلفة إضافية عليك."
    )
    pieces.append(AffiliateContentPiece(
        opportunity_id=inp.opportunity_id, format="recommendation",
        title=f"توصية: {inp.program_name} لمن يبحث عن {inp.product_category}",
        body=rec_body,
        cta=f"زر الموقع الرسمي لـ {inp.program_name} (رابط Affiliate): {inp.program_name}",
        disclosure=disclosure, generated_at=ts,
    ))

    return pieces


def render_all_formats(inp: AffiliateContentInput,
                       now: Optional[datetime] = None) -> Dict[str, str]:
    """Render the full chain as a dict {format: full_text_with_title} for
    easy distribution to the 8 repurposing channels."""
    pieces = build_affiliate_content(inp, now=now)
    out = {}
    for p in pieces:
        out[p.format] = f"# {p.title}\n\n{p.body}\n\n---\nCTA: {p.cta}\n\n{p.disclosure}"
    return out


def from_portfolio_opportunity(opportunity: dict,
                               audience_angle: str = "",
                               verified_usage: bool = False,
                               now: Optional[datetime] = None) -> List[AffiliateContentPiece]:
    """Adapter: build content directly from a real portfolio opportunity
    (commission_opportunities.jsonl entry). Uses only real fields; any
    missing field is handled honestly (never fabricated)."""
    name = opportunity.get("program_name") or opportunity.get("partner_name") or opportunity.get("opportunity_id", "")
    product = opportunity.get("product_or_service") or opportunity.get("program_name") or "المنتج"
    problem = opportunity.get("customer_problem") or opportunity.get("product_or_service") or "اختيار الحل المناسب"
    audience = opportunity.get("target_customer") or "الأشخاص الذين يواجهون هذه المشكلة"
    commission = opportunity.get("commission_value") or ""
    disclosure = (
        f"إفصاح: هذا المحتوى يشمل روابط Affiliate لـ {name}. قد نتلقى عمولة عند الشراء عبر روابطنا "
        f"بدون أي تكلفة إضافية عليك. نحن لا نوصي إلا بما نعتقد أنه مفيد لجمهورنا."
        + (f" شروط العمولة الرسمية: {commission}." if commission else "")
    )
    inp = AffiliateContentInput(
        opportunity_id=opportunity.get("opportunity_id", ""),
        program_name=name,
        product_category=product,
        solves_problem=problem,
        target_audience=audience,
        commission_disclosure=commission,
        verified_usage=verified_usage,
        audience_angle=audience_angle,
    )
    pieces = build_affiliate_content(inp, now=now)
    for p in pieces:
        p.disclosure = disclosure
    return pieces
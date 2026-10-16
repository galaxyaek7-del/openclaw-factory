# -*- coding: utf-8 -*-
"""Larger, diverse controlled benchmark corpus (v2).

Produced to satisfy the founder's next-step directive: representative Arabic
content, multiple writing styles, short and long samples, clean/high-quality
samples, deliberately weak samples, repeated/near-duplicate samples, edge
cases, and enough diversity to test threshold stability.

GROUND-TRUTH LIMITATION (declared up front, per directive rule 7):
The `dense` and `copy` labels are the author's (deterministic) *judgment*
applied while constructing this synthetic corpus — they are DERIVED/ESTIMATED
labels, NOT independently OBSERVED ground truth. No real Arabic product
corpus with independently-verified "defect" labels exists in this factory
today (zero real published books, per config/reality.json). Therefore the
benchmark measures the tools against *controlled, author-labeled* cases; the
labels are reproducible and disclosed, but they are not proof of
real-market generalizability. This is stated explicitly rather than implied.

Each case carries a `kind` and `ground_truth` for the metric it exercises,
plus metadata (style, length_bucket). Edge/near-duplicate/weak cases are
included explicitly.
"""

# ---------------------------------------------------------------------------
# READABILITY CASES (ground_truth "dense" = judged low-readability/worth
# flagging for the OSMAN proxy; "natural" = judged acceptably readable).
# ---------------------------------------------------------------------------

SHORT_NATURAL = (
    "هذا كتاب بسيط عن الطبخ. نتعلم فيه وصفات سهلة وسريعة تناسب الجميع،"
    " ونشرح كل خطوة بأسلوب واضح وقصير."
)
LONG_NATURAL = (
    "في هذا الدليل اليومي نشرح بأسلوب بسيط كيف تنظم وقتك وتخطط لمهامك الأسبوعية."
    " نبدأ بالأهداف الصغيرة، ونقسمها إلى خطوات واضحة يسهل تنفيذها، ثم نراجع"
    " تقدّمنا كل مساء للتأكد أننا على الطريق الصحيح. نعطي أمثلة عملية من واقع"
    " الحياة اليومية، ونتجنب لغة معقدة لا تضيف قيمة للقارئ."
)
SHORT_DENSE = (
    "إن إعمال مقتضيات النصوص والقواعد الموضوعة من أجل تنظيم العلاقات بين الأفراد"
    " والطوائف والمؤسسات يستلزم استقراء بنية من التعقيدات البنيوية المتمفصلة."
)
LONG_DENSE = (
    "تتمثل أهمية اعتماد المعايير الدولية المتنامية في ضوء المتغيرات المتراكبة"
    " والمترابطة في الأطر التشريعية المعاصرة المتعددة المشارب في الاستنتاج المنطقي"
    " المتفرع عن مقتضيات النصوص الموضوعة لتنظيم العلاقات بين الأفراد والطوائف"
    " والمؤسسات، الأمر الذي يستلزم استقراء بنية من التعقيدات البنيوية غير المباشرة"
    " إذ لا يمكن حصرها في نطاق محدد دون الإحاطة الشاملة بالمتغيرات المتناسبة"
    " والمتداخلة التي تشكل معًا منظومة من القرائن المركبة ذات الدلالات المتشابكة."
)
DIALECTAL_NATURAL = (
    "مرحبًا بيكو هني. النهاردة هنتكلم عن طريقة بسيطة تجهز بيها وصفة سريعة في عشر"
    " دقايق، من غير ما تعقد الأمور. جرب الكلام ده وتوصلنا بقه لو عجبتك الطريقة."
)
EDGE_MIXED = (
    "Notes and simple English are fine here. هذا الكتاب عن الطبخ. نتعلم فيه"
    " وصفات سهلة وسريعة، ونشرح كل خطوة بأسلوب واضح وقصير لجميع القراء."
)
EDGE_EMPTY = ""
EDGE_NON_ARABIC = "This is a plain English sample with no Arabic characters at all."
EDGE_VERY_SHORT = "شكرًا. تعلمنا وصفة سريعة."
WEAK_RUNON = (
    "سنتحدث عن أشياء كثيرة منها التخطيط ومنها التنفيذ ومنها المراجعة ومنها الادخار"
    " ومنها الاستثمار ومنها النمو ومنها الصبر ومنها الاستمرار ومنها الانضباط ومنها"
    " التقييم ومنها التحسين المستمر ومنها بناء العادات ومنها إدارة الوقت ومنها"
    " تحديد الأولويات ومنها التعامل مع الفشل ومنها التعلم ومنها التكيف مع المتغيرات"
    " المختلفة التي تطرأ على الحياة بشكل عام وعلى الأعمال بشكل خاص وخصوصًا في"
    " المراحل المبكرة من أي مشروع."
)
WEAK_FORMULAIC = (
    "كما هو معروف عالميًا، فإن أهمية الموضوعات المعاصرة المتعلقة بالتحول الرقمي"
    " لا تقتصر على مجرد توظيف التكنولوجيا، بل تمتد إلى إعادة صياغة المفاهيم"
    " التقليدية بما يتوافق ومتطلبات المرحلة الراهنة والمحددات العامة المعتمدة"
    " والمتفق عليها عالميًا في هذا الشأن تحديدًا."
)


# ---------------------------------------------------------------------------
# DISTINCTIVENESS: one reference pack (a "free documented alternative" style)
# plus a bank of candidate texts with ground_truth "copy" vs "distinctive".
# ---------------------------------------------------------------------------

DISTINCTIVENESS_REFERENCE = (
    "هذا الدليل يشرح كيف تبدأ مشروعًا صغيرًا. الخطوات الأولى مهمة في أي مشروع جديد."
)


def _ref_paraphrase_of_ref(shift=0):
    """Deterministic near-duplicate (paraphrase) of the reference, with whole
    reference chunks reused so the lcs guard and word overlap both trip."""
    body = "في هذا الدليل نعرض كيف تبدأ مشروعًا صغيرًا، فالخطوات الأولى مهمة في أي مشروع جديد."
    return body


def _long_reuse_of_ref():
    """Long sample that reuses a contiguous substring of the reference amid
    otherwise-distinct content (tests lcs guard on long inputs)."""
    pre = "سنتناول في هذا الكتيب الموسّع عدة مواضيع منها تخطيط المشاريع وإدارة الموارد."
    return pre + " كيف تبدأ مشروعًا صغيرًا " + "الخطوات الأولى مهمة في أي مشروع جديد." + \
        " ثم ننتقل إلى مناقشة أدق التفاصيل التنظيمية والمالية لمدة عشرين صفحة إضافية."


DISTINCTIVE_BANK = [
    "في هذا الكتيب نعرض أسرار إدارة الترتيبات اليومية لمحترفي العمل الحر، مع "
    "أمثلة واقعية عن تنظيم المهام الأسبوعية وتوزيع الطاقة.",
    "دراسة متعمقة في بناء خطط تسويقية مخصصة للعاملين المستقلين، تستند إلى قواعد "
    "البيانات وملاحظات السوق الحية لا إلى نماذج جاهزة.",
    "دليل عملي لزراعة الخضروات الورقية في الشرفات، نتحدث فيه عن تربة مغذية، "
    "وريّ متوازن، ومكافحة الآفات بطرق طبيعية آمنة على الأسرة.",
    "أساسيات تحرير الصور الرقمية للمصممين المبتدئين: فهم الطبقات، وضبط الألوان، "
    "وحفظ الملفات بالصيغ المناسبة لكل منصة نشر.",
]


ARABIC_READABILITY_CASES_V2 = [
    # clean / high-quality (natural)
    {"id": "r_clean_style_prose", "ground_truth": "natural", "style": "prose",
     "length": "short", "kind": "readability",
     "text": SHORT_NATURAL},
    {"id": "r_clean_style_instruction", "ground_truth": "natural", "style": "instructional",
     "length": "long", "kind": "readability",
     "text": LONG_NATURAL},
    {"id": "r_clean_style_dialect", "ground_truth": "natural", "style": "dialectal",
     "length": "short", "kind": "readability",
     "text": DIALECTAL_NATURAL},
    # deliberately weak / dense (low readability)
    {"id": "r_weak_short_dense", "ground_truth": "dense", "style": "formal_legalese",
     "length": "short", "kind": "readability",
     "text": SHORT_DENSE},
    {"id": "r_weak_long_dense", "ground_truth": "dense", "style": "formal_legalese",
     "length": "long", "kind": "readability",
     "text": LONG_DENSE},
    {"id": "r_weak_formulaic", "ground_truth": "dense", "style": "academic_formulaic",
     "length": "long", "kind": "readability",
     "text": WEAK_FORMULAIC},
    {"id": "r_weak_runon", "ground_truth": "dense", "style": "run_on",
     "length": "long", "kind": "readability",
     "text": WEAK_RUNON},
    # edge cases
    {"id": "r_edge_mixed_en_ar", "ground_truth": "natural", "style": "mixed",
     "length": "short", "kind": "readability",
     "text": EDGE_MIXED},
    {"id": "r_edge_very_short", "ground_truth": "natural", "style": "fragment",
     "length": "tiny", "kind": "readability",
     "text": EDGE_VERY_SHORT},
    {"id": "r_edge_non_arabic", "ground_truth": "no_arabic", "style": "english",
     "length": "short", "kind": "readability",
     "text": EDGE_NON_ARABIC},
    {"id": "r_edge_empty", "ground_truth": "empty", "style": "empty",
     "length": "empty", "kind": "readability",
     "text": EDGE_EMPTY},
]


DISTINCTIVENESS_CASES_V2 = [
    # clean / distinctive
    {"id": "d_clean_1", "ground_truth": "distinctive", "style": "prose",
     "length": "short", "kind": "distinctiveness",
     "text": DISTINCTIVE_BANK[0]},
    {"id": "d_clean_2", "ground_truth": "distinctive", "style": "academic",
     "length": "medium", "kind": "distinctiveness",
     "text": DISTINCTIVE_BANK[1]},
    {"id": "d_clean_3", "ground_truth": "distinctive", "style": "hobby",
     "length": "medium", "kind": "distinctiveness",
     "text": DISTINCTIVE_BANK[2]},
    {"id": "d_clean_4", "ground_truth": "distinctive", "style": "tutorial",
     "length": "medium", "kind": "distinctiveness",
     "text": DISTINCTIVE_BANK[3]},
    # repeated / near-duplicate
    {"id": "d_dup_exact", "ground_truth": "copy", "style": "verbatim",
     "length": "short", "kind": "distinctiveness",
     "text": DISTINCTIVENESS_REFERENCE},
    {"id": "d_dup_paraphrase", "ground_truth": "copy", "style": "paraphrase",
     "length": "short", "kind": "distinctiveness",
     "text": _ref_paraphrase_of_ref()},
    {"id": "d_dup_long_reuse", "ground_truth": "copy", "style": "long_embedded_reuse",
     "length": "long", "kind": "distinctiveness",
     "text": _long_reuse_of_ref()},
    # edge cases
    {"id": "d_edge_empty", "ground_truth": "empty", "style": "empty",
     "length": "empty", "kind": "distinctiveness",
     "text": ""},
    {"id": "d_edge_non_arabic", "ground_truth": "no_arabic", "style": "english",
     "length": "short", "kind": "distinctiveness",
     "text": "A completely unrelated English sentence about gardening tools."},
]


ARABIC_READABILITY_CASES = None  # v1 superseded; keep module exports clear
DISTINCTIVENESS_CASES = None
DISTINCTIVENESS_REFERENCE_V2 = DISTINCTIVENESS_REFERENCE
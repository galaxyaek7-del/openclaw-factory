// Galaxy Forge -- Scout brief prompt and parser, moved verbatim from server.js
// (2026-10-23) so the research step can be tested without loading the server.

function scoutBriefPrompt(trendsHint) {
  return `اقترح نيتش كتاب رقمي واحد فقط (الأقوى) مناسب للنشر الفوري على Amazon KDP${trendsHint ? `، مستفيداً من هذه الترندات الحالية: ${trendsHint}` : ''}.

عند تحديد ##PRICE##: سعّر هذا الكتاب كمنتج احترافي متميز (Premium)، وليس كتاباً رقمياً عادياً رخيصاً. اعتبارات التسعير:
- عمق المحتوى ومدى تخصصه (كلما كان أعمق وأكثر تخصصاً، كلما استحق سعراً أعلى)
- الجمهور المستهدف: هل هم محترفون/أصحاب أعمال مستعدون للدفع مقابل قيمة حقيقية؟
- أسعار المنتجات المماثلة في السوق (Market comparables) لنفس الفئة والجمهور
- الحد الأدنى المقبول هو 30 دولاراً (مستوى "الزبدة" — Butter-tier)، ولا تقترح رقماً أقل من ذلك أبداً
اجعل السعر مبرَّراً بالقيمة التي يقدّمها الكتاب فعلياً، لا رقماً افتراضياً.

هذا مثال على الشكل المطلوب فقط (نيتش مختلف تماماً — لا تكرر محتواه أبداً):
##TITLE##
دليل العادات الذهبية للصباح المنتج
##TOPIC##
كتاب عملي يعلّم القارئ بناء روتين صباحي يرفع تركيزه وطاقته خلال 30 يوماً
##AUDIENCE##
الموظفون وأصحاب الأعمال الذين يعانون من قلة التركيز
##PRICE##
39
##CHAPTERS##
6

الآن، بنفس التنسيق الحرفي بالضبط (##TITLE## ثم ##TOPIC## ثم ##AUDIENCE## ثم ##PRICE## ثم ##CHAPTERS##)، اكتب اقتراحك الخاص لنيتش مختلف تماماً بمحتوى حقيقي جديد. لا تعد أي شرح خارج هذه الأقسام، ولا تكرر نص المثال.`;
}

function parseScoutBrief(text) {
  // The small/fast Groq model is inconsistent run-to-run: sometimes it follows
  // the literal ##TITLE##/##TOPIC##/... tags exactly; other times it invents
  // its own '## <actual title text> ##' header and inline Arabic labels
  // ("وصف النيش:", "الجمهور المستهدف:", ...) instead of separate tag lines.
  // Handle both shapes explicitly rather than guessing from one heuristic
  // (same lesson learned in book_generator.py's content parser).
  if (/##TITLE##/i.test(text) && /##TOPIC##/i.test(text)) {
    const section = (tag) => {
      const m = text.match(new RegExp(`##${tag}##\\s*([\\s\\S]*?)(?=##[A-Z]+##|$)`, 'i'));
      return m ? m[1].trim() : '';
    };
    const priceMatch = section('PRICE').match(/[\d.]+/);
    const chaptersMatch = section('CHAPTERS').match(/\d+/);
    return {
      title: section('TITLE'),
      topic: section('TOPIC'),
      audience: section('AUDIENCE') || 'القارئ العام',
      price: priceMatch ? parseFloat(priceMatch[0]) : 9.99,
      chapters: chaptersMatch ? Math.max(4, Math.min(10, parseInt(chaptersMatch[0], 10))) : 6,
    };
  }

  // Loose fallback: first '## ... ##' line is the title (whatever it says),
  // the rest is scanned for inline Arabic field labels.
  const headerMatch = text.match(/^#{1,4}\s*(.+?)\s*#{0,4}\s*$/m);
  const title = headerMatch ? headerMatch[1].trim() : '';
  let body = headerMatch ? text.slice(headerMatch.index + headerMatch[0].length) : text;
  body = body.replace(/^\/+/gm, ''); // strip a stray leading "/" the model sometimes emits before a label

  // Bare word stems (no "ال" prefix, no fixed multi-word phrase) — the model
  // has been observed using "نيش"/"موضوع", "جمهور"/"الجمهور المستهدف",
  // "سعر"/"السعر المقترح", "فصول"/"عدد الفصول المتوقعة" interchangeably.
  const STEMS = { topic: '(?:نيش|موضوع)', audience: 'جمهور', price: 'سعر', chapters: 'فصول' };
  const LABELS = `(?:${STEMS.topic}|${STEMS.audience}|${STEMS.price}|${STEMS.chapters})`;
  const grab = (stem) => {
    // Skip the rest of the label's own line (and an optional inline ":"),
    // then capture up to the next label line (matched within its first ~30
    // chars, so the word can't accidentally match deep inside a paragraph).
    const re = new RegExp(`${stem}[^\\n:]*[:#]?\\s*([\\s\\S]*?)(?=\\n\\s*#*\\s*[^\\n]{0,30}?${LABELS}|$)`, 'i');
    const m = body.match(re);
    return m ? m[1].trim() : '';
  };

  const topic = grab(STEMS.topic);
  const audience = grab(STEMS.audience) || 'القارئ العام';
  const priceMatch = grab(STEMS.price).match(/[\d.]+/);
  const chaptersMatch = grab(STEMS.chapters).match(/\d+/);
  return {
    title,
    topic,
    audience,
    price: priceMatch ? parseFloat(priceMatch[0]) : 9.99,
    chapters: chaptersMatch ? Math.max(4, Math.min(10, parseInt(chaptersMatch[0], 10))) : 6,
  };
}

module.exports = { scoutBriefPrompt, parseScoutBrief };

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Profit Oracle (The Commercial Brain)

Before any product is made, this oracle scores its profit potential (0-100)
across four weighted signal groups, per CONSTITUTION.md §16 (The Butter
Principle — Profit-First): no product is built on hope alone.

Honesty note (read before trusting a score): several signals this tool is
asked for — live Google Trends momentum, real search volume, live competitor
counts — have no connected data source anywhere in this factory yet (see
FACTORY_STATUS.md's documented gap: n8n does not return real trend-volume
numbers, and niche_validator_v2.py is deliberately offline/manual, not a
live API — see that file's own docstring). Rather than fabricate a fake API
call, every such signal is either:
  (a) computed from REAL data when it exists — niche_validator_v2.py's saved
      reports in niche_reports/, via the same lookup quality_gate() already
      uses in book_generator.py — or
  (b) a documented, deterministic heuristic (keyword/date-based), explicitly
      labeled as an estimate in the result's `reasoning`.
Nothing here silently pretends to be live market data that it isn't.
"""

import os
import re
import sys
import json
from datetime import datetime

# When spawned as a child process without a real console, Python's stdin/
# stdout can silently fall back to the OS locale codepage instead of UTF-8,
# corrupting Arabic text (same fix as book_generator.py/cover_designer_v2.py).
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Optional: reuse niche_validator_v2.py's competition threshold + saved
# reports for real data when available. Guarded the same way book_generator.py
# guards it — an absent optional dependency (bs4) must not crash the oracle.
try:
    import niche_validator_v2 as NICHE_VALIDATOR
except (Exception, SystemExit):
    NICHE_VALIDATOR = None

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
OPPORTUNITIES_FILE = os.path.join(FACTORY_DIR, 'OPPORTUNITIES.md')
GOLDEN_MD_FILE = os.path.join(FACTORY_DIR, 'GOLDEN_OPPORTUNITIES.md')
GOLDEN_JSON_FILE = os.path.join(FACTORY_DIR, 'golden_opportunities.json')
NICHE_REPORTS_DIR = os.path.join(FACTORY_DIR, 'niche_reports')
CHANNELS_CONFIG_FILE = os.path.join(FACTORY_DIR, 'config', 'channels.json')

MAX_COMPETITION = NICHE_VALIDATOR.CRITERIA['max_competition'] if NICHE_VALIDATOR else 50000
MIN_BUTTER_PRICE = 30   # CONSTITUTION.md §16 — the Butter Principle's floor
MAX_BUTTER_PRICE = 100  # a KDP-realistic ceiling for a single digital book

# ── Keyword heuristics — documented estimates, not live APIs ──

SEASONAL_KEYWORDS = {
    # substring -> peak months (1-12); matched niches get a boost only when
    # "now" actually falls in that window, a penalty otherwise.
    'رمضان': (2, 3, 4),
    'عيد': (2, 3, 4, 9, 10),
    'summer': (4, 5, 6), 'صيف': (4, 5, 6),
    'winter': (10, 11, 12), 'شتاء': (10, 11, 12),
    'christmas': (10, 11),
    'new year': (11, 12), 'رأس السنة': (11, 12),
    'back to school': (7, 8), 'العودة للمدارس': (7, 8), 'العودة للمدرسة': (7, 8),
    'resolution': (12, 1), 'قرارات': (12, 1),
    'valentine': (1, 2),
}

PREMIUM_KEYWORDS = ['template', 'course', 'masterclass', 'system', 'bundle', 'toolkit',
                    'قوالب', 'دورة', 'نظام', 'حزمة', 'اشتراك']
MID_KEYWORDS = ['planner', 'tracker', 'workbook', 'مخطط', 'متتبع', 'ورشة']
RECURRING_KEYWORDS = ['membership', 'subscription', 'monthly', 'community', 'coaching',
                      'اشتراك', 'شهري', 'مجتمع', 'تدريب']
SUBNICHE_QUALIFIERS = ['for beginners', 'for teens', 'for women', 'for men', 'for kids',
                       'للمبتدئين', 'للمراهقين', 'للنساء', 'للرجال', 'للأطفال']
PHYSICAL_PRODUCT_KEYWORDS = ['jewelry', 'مجوهرات', 'قهوة', 'coffee beans', 'clothing',
                             'ملابس', 'furniture', 'أثاث', 'perfume', 'عطور']


def _find_niche_report(niche):
    """Mirrors book_generator.py's quality_gate() lookup — reuses a real
    saved Amazon competition report when one exists for this niche."""
    if not niche or not os.path.isdir(NICHE_REPORTS_DIR):
        return None
    niche_lower = str(niche).lower()
    for fname in sorted(os.listdir(NICHE_REPORTS_DIR), reverse=True):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(NICHE_REPORTS_DIR, fname), 'r', encoding='utf-8') as f:
                report = json.load(f)
        except Exception:
            continue
        keyword = str(report.get('keyword', '')).strip().lower()
        if keyword and (keyword in niche_lower or niche_lower in keyword):
            return report
    return None


def _score_demand(niche, now=None):
    """40% weight. Seasonality is real (today's date vs. a keyword calendar).
    Search volume and momentum are explicitly-labeled estimates — no live
    Trends connection exists in this factory yet."""
    now = now or datetime.now()
    niche_lower = niche.lower()
    notes = []

    season_score = 60  # neutral/evergreen default
    matched_season = None
    for kw, months in SEASONAL_KEYWORDS.items():
        if kw in niche_lower:
            matched_season = kw
            season_score = 90 if now.month in months else 35
            break
    if matched_season:
        in_season = "في موسمه الآن" if season_score >= 90 else "خارج موسمه حالياً"
        notes.append(f"موسمية: يطابق '{matched_season}' ({in_season})")
    else:
        notes.append("لا كلمة موسمية — يُفترض نيتش دائم (evergreen)")

    word_count = len(niche.split())
    if 2 <= word_count <= 4:
        volume_score = 75
        notes.append(f"تقدير حجم البحث: جيد (تخصص متوازن، {word_count} كلمات) [تقدير]")
    elif word_count == 1:
        volume_score = 55
        notes.append("تقدير حجم البحث: عام جداً (كلمة واحدة) [تقدير غير موثوق بلا بيانات حقيقية]")
    else:
        volume_score = 45
        notes.append(f"تقدير حجم البحث: محدود (نيتش طويل جداً، {word_count} كلمة) [تقدير]")

    momentum_score = 50
    notes.append("زخم الترند: لا يوجد اتصال حقيقي بـ Google Trends بعد — قيمة محايدة افتراضية")

    demand_score = round(season_score * 0.40 + volume_score * 0.35 + momentum_score * 0.25)
    return demand_score, notes


def _score_competition(niche):
    """30% weight. Real data when a saved niche_validator_v2.py report
    matches; otherwise a specificity-based estimate, clearly labeled."""
    notes = []
    report = _find_niche_report(niche)
    if report and report.get('status') == 'success':
        total_results = report.get('metrics', {}).get('total_results', 0)
        comp_score = max(0, round(100 * (1 - min(total_results, MAX_COMPETITION) / MAX_COMPETITION)))
        notes.append(f"منافسة حقيقية من تقرير محفوظ: {total_results:,} نتيجة (الحد: {MAX_COMPETITION:,})")
    else:
        word_count = len(niche.split())
        comp_score = 70 if word_count >= 3 else 45
        notes.append("لا بحث Amazon محفوظ لهذا النيتش — تقدير من درجة التخصص [تقدير]")

    if any(q in niche.lower() for q in SUBNICHE_QUALIFIERS):
        comp_score = min(100, comp_score + 10)
        notes.append("تخصيص جمهور واضح — فجوة/underserved sub-niche محتملة")

    return comp_score, notes


def _score_margin(niche):
    """20% weight. Price tier + recurring potential are keyword estimates;
    production cost is a real, always-true fact for this factory (digital)."""
    notes = []
    niche_lower = niche.lower()
    if any(k in niche_lower for k in PREMIUM_KEYWORDS):
        price, price_score = 39, 90
    elif any(k in niche_lower for k in MID_KEYWORDS):
        price, price_score = 19, 65
    else:
        price, price_score = 9, 45
    notes.append(f"السعر المقترح: ${price} [تقدير حسب فئة الكلمات المفتاحية]")

    cost_score = 100
    notes.append("تكلفة الإنتاج: ~$0 (منتج رقمي — حقيقة ثابتة لهذا المصنع)")

    if any(k in niche_lower for k in RECURRING_KEYWORDS):
        recurring_score = 90
        notes.append("إمكانية اشتراك متكرر: مرتفعة")
    else:
        recurring_score = 40
        notes.append("إمكانية اشتراك متكرر: منخفضة (منتج لمرة واحدة على الأرجح)")

    margin_score = round(price_score * 0.5 + cost_score * 0.2 + recurring_score * 0.3)
    return margin_score, notes, price


def _load_channel_automation():
    """Real automation status per platform from config/channels.json (the
    same data channels/registry.py's arms fulfill for Gumroad today) —
    'api' (an arm can push it automatically) vs 'manual' (a human still has
    to upload it by hand). Optional/guarded the same way the
    niche_validator_v2 import above is: a missing or malformed file must
    never crash scoring, it just means no automation claim is made."""
    try:
        with open(CHANNELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        channels = data.get('channels', [])
        return {
            c['id']: c.get('automation')
            for c in channels if isinstance(c, dict) and c.get('id')
        }
    except Exception:
        return {}


def _label_channel(automation, channel_id, display_name):
    """Appends a real automation status to a platform's display name.
    Unknown/missing status makes no claim either way, rather than guessing."""
    status = automation.get(channel_id)
    if status == 'api':
        return f"{display_name} (آلي)"
    if status == 'manual':
        return f"{display_name} (رفع يدوي)"
    return display_name


def _score_execution(niche):
    """10% weight. Grounded in real, current factory capability: only
    book_engine is active (FACTORY_STATUS.md) — everything is scored against
    whether it can become a digital book/planner/guide today. The platform
    recommendation is labeled with each channel's REAL automation status
    (config/channels.json / channels/registry.py) rather than a flat
    hardcoded string — Gumroad is wired to an actual arm today, KDP/Etsy
    still require a human to upload, and this should say so honestly."""
    notes = []
    niche_lower = niche.lower()
    automation = _load_channel_automation()

    if any(k in niche_lower for k in PHYSICAL_PRODUCT_KEYWORDS):
        fit_score = 15
        notes.append("يبدو منتجاً مادياً — المصنع ينتج كتباً/طباعات رقمية فقط اليوم (book_engine)")
        platform = "غير مناسب لقدرات المصنع الحالية"
    else:
        fit_score = 90
        notes.append("يناسب book_engine (المحرك الوحيد الفعّال حالياً) كدليل/كتاب رقمي")
        kdp_label = _label_channel(automation, 'kdp_paperback', 'KDP')
        if any(k in niche_lower for k in MID_KEYWORDS) or any(k in niche_lower for k in PREMIUM_KEYWORDS):
            etsy_label = _label_channel(automation, 'etsy_digital', 'Etsy')
            gumroad_label = _label_channel(automation, 'gumroad', 'Gumroad')
            platform = f"{kdp_label} + {etsy_label} + {gumroad_label}"
        else:
            platform = kdp_label

    return fit_score, notes, platform


def score_opportunity(niche, now=None):
    niche = str(niche or '').strip()
    if not niche:
        raise ValueError("النيتش (niche) مطلوب")

    demand_score, demand_notes = _score_demand(niche, now)
    competition_score, competition_notes = _score_competition(niche)
    margin_score, margin_notes, price = _score_margin(niche)
    execution_score, execution_notes, platform = _score_execution(niche)

    profit_score = round(
        demand_score * 0.40 +
        competition_score * 0.30 +
        margin_score * 0.20 +
        execution_score * 0.10
    )
    profit_score = max(0, min(100, profit_score))

    if profit_score >= 80:
        verdict = "GOLDEN"
    elif profit_score >= 60:
        verdict = "GOOD"
    else:
        verdict = "SKIP"

    if profit_score >= 80:
        butter_count = 5
    elif profit_score >= 70:
        butter_count = 4
    elif profit_score >= 60:
        butter_count = 3
    elif profit_score >= 40:
        butter_count = 2
    else:
        butter_count = 1

    reasoning = "؛ ".join(demand_notes + competition_notes + margin_notes + execution_notes)

    return {
        "niche": niche,
        "profit_score": profit_score,
        "verdict": verdict,
        "recommended_price": f"${price}",
        "recommended_platform": platform,
        "reasoning": reasoning,
        "butter_rating": "🧈" * butter_count,
        "needs_galaxy_approval": profit_score >= 80,
        "scores": {
            "demand": demand_score,
            "competition": competition_score,
            "margin": margin_score,
            "execution": execution_score,
        },
    }


def butter_price(niche):
    """Smart Publishing + Butter Principle (OPENCLAW_OS_CONSTITUTION.md /
    CONSTITUTION.md §16): given a niche, returns a defensible price in the
    $30–$100 butter-tier band — never a flat $30 for everything, never a
    fabricated number. The starting tier reuses the same keyword vocabulary
    _score_margin() already scores this niche's margin against (premium/
    recurring signals → a higher defensible starting point), then this
    niche's OWN profit_score scales it upward within the remaining headroom
    to $100 — a stronger niche (higher demand, lower competition) can
    defensibly ask for more, rather than every repriced niche landing on
    the same number.

    Callers are expected to only invoke this for niches that are not
    genuinely weak (see score_opportunity()'s verdict != 'SKIP') — a niche
    with real thin demand or saturated competition doesn't become viable
    just because a bigger number was attached to it."""
    niche = str(niche or '').strip()
    if not niche:
        raise ValueError("النيتش (niche) مطلوب")

    result = score_opportunity(niche)
    score = result['profit_score']
    niche_lower = niche.lower()

    if any(k in niche_lower for k in PREMIUM_KEYWORDS):
        base = 60
    elif any(k in niche_lower for k in MID_KEYWORDS):
        base = 45
    else:
        base = MIN_BUTTER_PRICE + 5  # $35 — still comfortably above the floor

    if any(k in niche_lower for k in RECURRING_KEYWORDS):
        base += 10  # a subscription-able product defensibly commands more

    base = min(base, MAX_BUTTER_PRICE)
    headroom = MAX_BUTTER_PRICE - base
    scaled = base + headroom * max(0, score - 60) / 40  # score 60→base, 100→ceiling

    return round(min(MAX_BUTTER_PRICE, max(MIN_BUTTER_PRICE, scaled)))


def _read_opportunities():
    """Parses OPPORTUNITIES.md entries of the form:
    '- [timestamp] niche — quality-gate reason' (see server.js /api/trends)."""
    if not os.path.exists(OPPORTUNITIES_FILE):
        return []
    line_re = re.compile(r'^-\s*\[(.+?)\]\s*(.+?)\s*—\s*(.+)$')
    niches = []
    with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            m = line_re.match(line.strip())
            if m:
                niches.append(m.group(2).strip())
    return niches


def _verdict_label(result):
    label = {"GOLDEN": "🏆 GOLDEN", "GOOD": "✅ GOOD", "SKIP": "⛔ SKIP"}[result["verdict"]]
    if result["needs_galaxy_approval"]:
        label += " (يحتاج موافقة Galaxy)"
    return label


def _write_golden_report(results, generated_at):
    lines = [
        "# 🏆 Golden Opportunities — مرتَّبة حسب Profit Score",
        "",
        f"**آخر تحديث:** {generated_at}",
        f"**تم بواسطة:** `profit_oracle.py` — CONSTITUTION.md §16 (The Butter Principle)",
        "",
    ]
    if not results:
        lines.append("لا فرص مُقيَّمة بعد — لا يوجد إدخالات في `OPPORTUNITIES.md`.")
    else:
        lines.append("| # | النيتش | النتيجة | الحكم | 🧈 | السعر | المنصة |")
        lines.append("|---|---|---|---|---|---|---|")
        for i, r in enumerate(results, 1):
            lines.append(
                f"| {i} | {r['niche']} | {r['profit_score']} | {_verdict_label(r)} | "
                f"{r['butter_rating']} | {r['recommended_price']} | {r['recommended_platform']} |"
            )
        lines.append("")
        lines.append("## التفاصيل")
        for i, r in enumerate(results, 1):
            lines.append("")
            lines.append(f"### {i}. {r['niche']} — {r['profit_score']}/100 {r['butter_rating']}")
            lines.append(f"**الحكم:** {_verdict_label(r)}")
            lines.append(f"**السعر المقترح:** {r['recommended_price']} | **المنصة:** {r['recommended_platform']}")
            lines.append(f"**السبب:** {r['reasoning']}")

    content = "\n".join(lines) + "\n"
    with open(GOLDEN_MD_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    with open(GOLDEN_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump({"generated_at": generated_at, "count": len(results), "results": results},
                   f, ensure_ascii=False, indent=2)


def run_oracle():
    """Reads OPPORTUNITIES.md, scores every niche, writes GOLDEN_OPPORTUNITIES.md
    (human-readable, ranked) and golden_opportunities.json (machine-readable,
    for server.js's /oracle endpoint) — both sorted by profit_score descending."""
    niches = _read_opportunities()
    results = [score_opportunity(n) for n in niches]
    results.sort(key=lambda r: r['profit_score'], reverse=True)
    generated_at = datetime.now().isoformat()
    _write_golden_report(results, generated_at)
    return results


def main():
    if '--run' in sys.argv:
        results = run_oracle()
        golden_count = sum(1 for r in results if r['verdict'] == 'GOLDEN')
        print(json.dumps({"success": True, "count": len(results), "golden_count": golden_count}, ensure_ascii=False))
        return

    if '--score' in sys.argv:
        try:
            data = json.loads(sys.stdin.read())
            result = score_opportunity(data.get('niche', ''))
            print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        return

    # Demo: 3 sample niches chosen to land on 3 different verdicts.
    samples = [
        "العودة للمدارس اشتراك للمبتدئين",  # in-season + premium/recurring + sub-niche -> GOLDEN (80+)
        "دليل التأمل واليقظة الذهنية",       # evergreen, balanced, no premium/recurring signal -> GOOD (60-79)
        "كتاب",                              # single generic word, no signals at all -> SKIP (<60)
    ]
    for niche in samples:
        result = score_opportunity(niche)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("---")


if __name__ == '__main__':
    main()

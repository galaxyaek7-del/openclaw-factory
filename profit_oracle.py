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
import math
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

# ADR-039: safety_filter.py's evaluate() is a pure function (no stdin
# reading happens on import — that only happens under main()'s own
# `if __name__ == '__main__'` guard) and safety_filter.py never imports
# profit_oracle, so this carries none of the circular-import risk that
# importing inspectors.py directly would (inspectors.py imports
# profit_oracle itself — see ADR-039's note on why a duplicate-check
# dimension wasn't added here).
try:
    import safety_filter as SAFETY_FILTER
except (Exception, SystemExit):
    SAFETY_FILTER = None

# ADR-041: economics.py never imports profit_oracle (only sys/json) — zero
# circular-import risk, same as safety_filter.py above. Reused for real
# platform-fee math instead of the flat "digital = free" assumption.
try:
    import economics as ECONOMICS
except (Exception, SystemExit):
    ECONOMICS = None

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
OPPORTUNITIES_FILE = os.path.join(FACTORY_DIR, 'OPPORTUNITIES.md')
AI_COST_LOG_FILE = os.path.join(FACTORY_DIR, 'data', 'ai_cost_log.jsonl')  # book_generator.py's real per-call Groq cost log (ADR-041)
GOLDEN_MD_FILE = os.path.join(FACTORY_DIR, 'GOLDEN_OPPORTUNITIES.md')
GOLDEN_JSON_FILE = os.path.join(FACTORY_DIR, 'golden_opportunities.json')
NICHE_REPORTS_DIR = os.path.join(FACTORY_DIR, 'niche_reports')
CHANNELS_CONFIG_FILE = os.path.join(FACTORY_DIR, 'config', 'channels.json')
REJECTED_NICHES_FILE = os.path.join(FACTORY_DIR, 'REJECTED_NICHES.md')  # factory_loop.js's circuit breaker

MAX_COMPETITION = NICHE_VALIDATOR.CRITERIA['max_competition'] if NICHE_VALIDATOR else 50000
MIN_BUTTER_PRICE = 30   # CONSTITUTION.md §16 — the Butter Principle's floor
MAX_BUTTER_PRICE = 100  # a KDP-realistic ceiling for a single digital book

# ADR-020: EU/US English printables (Gumroad) have a completely different
# psychological price ceiling than a KDP ebook — $30 reads as absurd for a
# 10-30 page planner/tracker, whereas $5-15 is the real market band (see
# PRICING_AND_FIRST_PRODUCTS.md). Separate constants, not a replacement —
# MIN/MAX_BUTTER_PRICE above stay exactly as-is for every existing book
# caller.
MIN_BUTTER_PRICE_PRINTABLE = 5
MAX_BUTTER_PRICE_PRINTABLE = 15

# ADR-024: human+Claude-authored premium bundles (HIGH_VALUE_STRATEGY.md) —
# a third, independent band. Separate constants, not a replacement — book
# and printable bands above stay exactly as-is.
MIN_BUTTER_PRICE_PREMIUM = 50
MAX_BUTTER_PRICE_PREMIUM = 300

# ADR-027/ELITE_ASSET_DOCTRINE.md: Tier 1 elite assets — a fourth,
# independent band. Separate constants, not a replacement — book/
# printable/premium bands above stay exactly as-is.
MIN_BUTTER_PRICE_ELITE = 97
MAX_BUTTER_PRICE_ELITE = 497

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


# ADR-038 (STRUCTURAL_DIAGNOSIS.md follow-up, ADR-035/036): real engagement
# evidence gathered during the Tier-1 research batches (Hacker News points
# 1-226, GitHub stars 330-13443 across 8 real candidates) — anchors below
# are calibrated against that actual observed range, not invented. Log-scale
# because both are heavily right-skewed (most posts/repos get very little
# traction; a handful get a lot). This is a first-pass calibration with no
# real sales-conversion data behind it yet — same honesty discipline as the
# rest of this file: a better proxy for real-world attention than keyword
# matching, not a validated predictor of revenue. Revisit with real outcome
# data once any exists.
def _normalize_hn_points(points):
    return max(20, min(100, round(30 + 22 * math.log10(max(points, 1) + 1))))


def _normalize_github_stars(stars):
    return max(20, min(100, round(15 + 18 * math.log10(max(stars, 1) + 1))))


def _score_momentum_from_recency(created_at, now=None):
    """Simple recency banding (same fixed-tier style as SEASONAL_KEYWORDS'
    in-season/out-of-season split) — a recent post/repo getting real
    engagement suggests current momentum; an old one, even a popular one,
    proves past interest more than present. Degrades to neutral 50 on any
    missing/unparseable date, never raises."""
    if not created_at:
        return 50, "لا تاريخ نشر متوفر مع الإشارة الخارجية — قيمة محايدة"
    try:
        now = now or datetime.now()
        created = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
        # Compare naive-to-naive: strip tzinfo if present so this never
        # raises on an aware-vs-naive subtraction — a day-count this rough
        # doesn't need timezone precision.
        created = created.replace(tzinfo=None)
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        days_old = (now_naive - created).days
    except Exception:
        return 50, "تاريخ نشر غير صالح مع الإشارة الخارجية — قيمة محايدة"

    if days_old <= 30:
        return 80, f"نشر حديث ({days_old} يوماً) — زخم عالٍ محتمل [بيانات حقيقية]"
    if days_old <= 90:
        return 60, f"نشر خلال آخر 3 أشهر ({days_old} يوماً) [بيانات حقيقية]"
    return 40, f"أقدم من 3 أشهر ({days_old} يوماً) — زخم أقل احتمالاً [بيانات حقيقية]"


def _score_from_external_signal(signal, now=None):
    """Real per-candidate evidence (ADR-036's own recommendation) instead of
    the word-count guess below — same pattern _score_competition() already
    uses for a saved Amazon report: real data when available, clearly
    labeled otherwise."""
    notes = []
    source = signal.get('source')
    if source == 'hacker_news':
        points = signal.get('points', 0)
        volume_score = _normalize_hn_points(points)
        notes.append(f"حجم حقيقي من Hacker News: {points} نقطة → {volume_score}/100 [بيانات حقيقية، ADR-036]")
    elif source == 'github':
        stars = signal.get('stars', 0)
        volume_score = _normalize_github_stars(stars)
        notes.append(f"حجم حقيقي من GitHub: {stars} نجمة → {volume_score}/100 [بيانات حقيقية، ADR-036]")
    else:
        volume_score = 50
        notes.append(f"مصدر إشارة خارجية غير معروف ({source}) — قيمة محايدة")

    momentum_score, momentum_note = _score_momentum_from_recency(signal.get('created_at'), now)
    notes.append(momentum_note)
    return volume_score, momentum_score, notes


def _score_demand(niche, now=None, external_signal=None):
    """40% weight. Seasonality is real (today's date vs. a keyword calendar).
    Without external_signal, search volume and momentum are explicitly-
    labeled estimates — no live Trends connection exists in this factory
    yet. With external_signal (real HN points / GitHub stars gathered
    during Tier-1 research, ADR-036), volume and momentum use that real
    evidence instead — never both at once, real data always wins when
    present. Omitting external_signal (every current live caller) reproduces
    today's exact behavior, unchanged."""
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

    if external_signal:
        volume_score, momentum_score, signal_notes = _score_from_external_signal(external_signal, now)
        notes.extend(signal_notes)
    else:
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


def _score_competition(niche, external_signal=None):
    """30% weight. Real data in priority order: a saved niche_validator_v2.py
    Amazon report first (unchanged, existing path); otherwise a real
    competitor-count from external_signal['competition'] when a research
    batch gathered one (ADR-041 — same log-scale honesty as ADR-038's
    demand normalization, calibrated as a first pass, not a validated
    predictor); otherwise the original word-count guess, clearly labeled.
    Omitting external_signal (every current live caller) reproduces
    today's exact behavior unchanged."""
    notes = []
    report = _find_niche_report(niche)
    comp_signal = (external_signal or {}).get('competition')
    if report and report.get('status') == 'success':
        total_results = report.get('metrics', {}).get('total_results', 0)
        comp_score = max(0, round(100 * (1 - min(total_results, MAX_COMPETITION) / MAX_COMPETITION)))
        notes.append(f"منافسة حقيقية من تقرير محفوظ: {total_results:,} نتيجة (الحد: {MAX_COMPETITION:,})")
    elif comp_signal and comp_signal.get('related_results_count') is not None:
        related_count = comp_signal['related_results_count']
        comp_score = max(0, min(100, round(95 - 20 * math.log10(related_count + 1))))
        notes.append(f"منافسة حقيقية: {related_count} نتيجة مشابهة فعلية (بحث حي) → {comp_score}/100 [بيانات حقيقية، ADR-041]")
    else:
        word_count = len(niche.split())
        comp_score = 70 if word_count >= 3 else 45
        notes.append("لا بحث Amazon محفوظ ولا عدد نتائج حقيقي آخر لهذا النيتش — تقدير من درجة التخصص [تقدير]")

    if any(q in niche.lower() for q in SUBNICHE_QUALIFIERS):
        comp_score = min(100, comp_score + 10)
        notes.append("تخصيص جمهور واضح — فجوة/underserved sub-niche محتملة")

    return comp_score, notes


def _real_average_ai_cost_per_call(log_file=None):
    """Real average, computed only from actual logged Groq calls
    (book_generator.py's _log_ai_cost(), ADR-041). Returns (None, 0) when
    no real call has been logged yet — never a guessed placeholder cost."""
    log_file = log_file or AI_COST_LOG_FILE
    if not os.path.exists(log_file):
        return None, 0
    costs = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get('cost_usd') is not None:
                    costs.append(rec['cost_usd'])
    except Exception:
        return None, 0
    if not costs:
        return None, 0
    return sum(costs) / len(costs), len(costs)


def _real_ai_cost_trend(log_file=None, now=None):
    """Autonomous Digital Company v1 follow-up (2026-07-19): "data flows,
    not isolated modules" — the same real cost-rate-trend signal
    lib/infrastructure_intelligence.js's getCostTrend() already computes
    for the dashboard (recent 7-day average vs. the real trailing daily
    average, flagged as an outlier only when a real baseline exists and
    the recent average is genuinely more than double it), reimplemented
    here in Python so _score_margin() below can use a real, CURRENT cost
    figure instead of a flat all-time average that would understate a
    genuine recent cost spike. Two independent readers of the same real
    log for two different purposes (a dashboard display vs. a scoring
    input) — not duplicated business logic, since neither reuses the
    other's decision.

    Returns (recent_7d_avg_cost_per_call, is_outlier) — recent_7d_avg is
    None when there's no real data in the last 7 days to average (never
    a fabricated recent figure)."""
    log_file = log_file or AI_COST_LOG_FILE
    now = now or datetime.now()
    if not os.path.exists(log_file):
        return None, False

    recent_costs, trailing_costs = [], []
    seven_days_ago = now.timestamp() - 7 * 24 * 60 * 60
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                cost = rec.get('cost_usd')
                ts = rec.get('timestamp')
                if cost is None or not ts:
                    continue
                try:
                    when = datetime.fromisoformat(ts).timestamp()
                except (TypeError, ValueError):
                    continue
                (recent_costs if when >= seven_days_ago else trailing_costs).append(cost)
    except Exception:
        return None, False

    if not recent_costs:
        return None, False

    recent_avg = sum(recent_costs) / len(recent_costs)
    if not trailing_costs:
        return recent_avg, False

    trailing_avg = sum(trailing_costs) / len(trailing_costs)
    is_outlier = trailing_avg > 0 and recent_avg > trailing_avg * 2
    return recent_avg, is_outlier


def _score_margin(niche):
    """20% weight. Price tier and recurring-revenue potential were pure
    keyword estimates until this fix (2026-07-16, Revenue Activation
    phase): _score_competition() already checked _find_niche_report()
    for a real saved Amazon report first, keyword estimate only as
    fallback (ADR-041/042) — this function never did the equivalent for
    price, despite _find_niche_report() already being imported and used
    two functions away in this same file. Now it does: a real saved
    report's actual average competitor price is used when one exists,
    normalized the same way market_intelligence_core.scoring.
    pricing_power.py already scores a real price (price / MAX_BUTTER_PRICE
    * 100) for consistency with that existing convention. Recurring-
    revenue potential remains a keyword estimate — no real repeat-purchase
    data exists anywhere in this factory yet (config/capability_registry.
    json's own DISCOVERY entry for it), and this fix does not invent one.

    Omitting a saved report (every niche this factory has evaluated so
    far — niche_reports/ is empty) reproduces the exact prior keyword-tier
    behavior unchanged."""
    notes = []
    niche_lower = niche.lower()

    report = _find_niche_report(niche)
    real_avg_price = (
        (report.get('metrics', {}) or {}).get('price', {}).get('avg')
        if report and report.get('status') == 'success' else None
    )

    if real_avg_price:
        price = real_avg_price
        price_score = max(0, min(100, round(price / MAX_BUTTER_PRICE * 100)))
        notes.append(f"متوسط سعر منافسين حقيقي من تقرير Amazon محفوظ: ${price} → {price_score}/100 [بيانات حقيقية]")
    elif any(k in niche_lower for k in PREMIUM_KEYWORDS):
        price, price_score = 39, 90
        notes.append(f"السعر المقترح: ${price} [تقدير حسب فئة الكلمات المفتاحية]")
    elif any(k in niche_lower for k in MID_KEYWORDS):
        price, price_score = 19, 65
        notes.append(f"السعر المقترح: ${price} [تقدير حسب فئة الكلمات المفتاحية]")
    else:
        price, price_score = 9, 45
        notes.append(f"السعر المقترح: ${price} [تقدير حسب فئة الكلمات المفتاحية]")

    avg_ai_cost, sample_size = _real_average_ai_cost_per_call()
    # Autonomous Digital Company v1 follow-up (2026-07-19): when a real
    # recent cost spike exists (recent 7-day average genuinely more than
    # double the real trailing baseline — same threshold
    # infrastructure_intelligence.js's dashboard already uses), the flat
    # all-time average understates what this will actually cost RIGHT NOW.
    # Use the real recent average instead — still real, still never a
    # guess, just a more current real figure. No real outlier -> byte-for-
    # byte the same behavior as before this change.
    recent_avg_ai_cost, is_cost_outlier = _real_ai_cost_trend()
    cost_outlier_note = None
    if is_cost_outlier and recent_avg_ai_cost is not None:
        cost_outlier_note = (
            f"⚠️ ارتفاع حقيقي في تكلفة Groq الأخيرة (متوسط 7 أيام ${recent_avg_ai_cost:.4f} "
            f"يفوق ضعف المتوسط التاريخي) — استُخدم المتوسط الأخير بدل المتوسط الكلي لتقدير أدق للتكلفة الحالية"
        )
        avg_ai_cost = recent_avg_ai_cost
    if ECONOMICS is not None:
        try:
            # Absolute path — economics.py's own default is CWD-relative
            # ("config/economics.json"), which would silently break if this
            # module is ever invoked from a different working directory.
            config = ECONOMICS.load_config(os.path.join(FACTORY_DIR, 'config', 'economics.json'))
            net_after_fees = ECONOMICS.net_profit(price, "gumroad_digital", config)
            net_after_ai_cost = net_after_fees - (avg_ai_cost or 0)
            cost_score = max(0, min(100, round(100 * net_after_ai_cost / price))) if price else 0
            ai_cost_note = (
                f"متوسط تكلفة Groq حقيقية من {sample_size} استدعاء فعلي مسجَّل: ${avg_ai_cost:.4f}"
                if avg_ai_cost is not None
                else "لا استدعاءات Groq حقيقية مسجَّلة بعد (ADR-041) — تُحتسَب صفراً مؤقتاً، لا تخميناً"
            )
            notes.append(
                f"هامش صافٍ حقيقي بعد رسوم gumroad_digital الفعلية (config/economics.json): "
                f"${net_after_fees:.2f} من ${price} — {ai_cost_note}"
            )
            if cost_outlier_note:
                notes.append(cost_outlier_note)
        except Exception as e:
            cost_score = 100
            notes.append(f"تعذّر حساب الهامش الحقيقي ({e}) — عاد لافتراض 'رقمي=صفر تكلفة' القديم")
    else:
        cost_score = 100
        notes.append("economics.py غير متوفر — تكلفة الإنتاج: ~$0 [افتراض قديم، لا حساب حقيقي]")

    if any(k in niche_lower for k in RECURRING_KEYWORDS):
        recurring_score = 90
        notes.append("إمكانية اشتراك متكرر: مرتفعة [تقدير كلمات مفتاحية — لا بيانات مبيعات حقيقية بعد]")
    else:
        recurring_score = 40
        notes.append("إمكانية اشتراك متكرر: منخفضة [تقدير كلمات مفتاحية]")

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


# ADR-039: real risk signals only — reuses the two safety mechanisms this
# factory already has (safety_filter.py's blocklist, REJECTED_NICHES.md's
# circuit breaker) rather than inventing a "legal risk"/"competitive
# threat" number with nothing behind it. Informational only — never part
# of profit_score's weighted formula, so it can't silently change any
# existing accept/reject decision.
def _is_in_rejected_niches(niche, rejected_file=None):
    rejected_file = rejected_file or REJECTED_NICHES_FILE
    if not niche or not os.path.exists(rejected_file):
        return False
    try:
        with open(rejected_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
    except Exception:
        return False
    return niche.strip().lower() in content


def _score_risk(niche):
    notes = []
    risk_score = 90  # 100 = no known risk today; only real deductions below
    risk_level = "low"

    if SAFETY_FILTER is None:
        notes.append("safety_filter.py غير متوفر — لا حكم أمان، لا افتراض")
    else:
        try:
            result = SAFETY_FILTER.evaluate({"title": niche, "description": niche})
            if not result.get("allowed", True):
                risk_level, risk_score = "blocked", 0
                notes.append(f"محجوب بواسطة safety_filter.py ({result.get('risk_level')}): {', '.join(result.get('reasons', [])) or 'بلا تفاصيل'}")
            elif result.get("risk_level") == "medium":
                risk_level, risk_score = "medium", 60
                notes.append(f"safety_filter.py: خطر متوسط — {', '.join(result.get('reasons', []))}")
            else:
                notes.append("safety_filter.py: لا مخاطر محتوى معروفة")
        except Exception as e:
            notes.append(f"تعذّر تشغيل safety_filter.py: {e} — لا حكم أمان، لا افتراض")

    if _is_in_rejected_niches(niche):
        risk_level = "high" if risk_level == "low" else risk_level
        risk_score = min(risk_score, 30)
        notes.append("مرفوض سابقاً في REJECTED_NICHES.md — قاطع الدائرة نشط")
    else:
        notes.append("لا رفض سابق في REJECTED_NICHES.md")

    return risk_score, risk_level, notes


# ADR-039: honest meta-score — how much of THIS result is real evidence
# versus a keyword/word-count estimate, not a new invented dimension. The
# whole point is to say "we don't actually know" plainly instead of
# dressing an estimate up as a measurement.
def _score_confidence(niche, external_signal):
    real_signals_used = []
    if external_signal:
        real_signals_used.append("الطلب (HN/GitHub)")
    report = _find_niche_report(niche)
    if report and report.get('status') == 'success':
        real_signals_used.append("المنافسة (تقرير Amazon محفوظ)")

    if len(real_signals_used) >= 2:
        return 80, "عالية نسبياً", f"بيانات حقيقية في: {'، '.join(real_signals_used)}"
    if len(real_signals_used) == 1:
        return 55, "متوسطة", f"بيانات حقيقية في {real_signals_used[0]} فقط — الباقي تقدير كلمات مفتاحية"
    return 30, "منخفضة", "كل المكوّنات تقديرات كلمات مفتاحية — لا بيانات سوق حقيقية بعد"


def score_opportunity(niche, now=None, external_signal=None):
    niche = str(niche or '').strip()
    if not niche:
        raise ValueError("النيتش (niche) مطلوب")

    demand_score, demand_notes = _score_demand(niche, now, external_signal)
    competition_score, competition_notes = _score_competition(niche, external_signal)
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

    risk_score, risk_level, risk_notes = _score_risk(niche)
    confidence_score, confidence_level, confidence_note = _score_confidence(niche, external_signal)

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
        # ADR-039: additive, informational only — never factored into
        # profit_score/verdict above, so no existing accept/reject decision
        # changes because of these two fields.
        "risk": {"score": risk_score, "level": risk_level, "notes": risk_notes},
        "confidence": {"score": confidence_score, "level": confidence_level, "note": confidence_note},
    }


# ── OPPORTUNITY SCORE (ADR-026, ELITE_ASSET_DOCTRINE.md §4) ──
# Tier-aware composite score for the Elite Digital Asset doctrine — reuses
# score_opportunity()'s real demand/competition/margin signals UNCHANGED
# (never re-derived), and adds two tier-derived factors this factory has
# no real per-niche signal for yet: automation_potential and
# long_term_value. These are documented, fixed-per-tier constants, not
# per-niche guesses — inventing a fake per-niche automation/LTV score
# would be exactly the "fabricated number" this factory's economics
# engine was built to stop doing (see economics.py's own docstring).

TIER_WEIGHTS = {"tier1": 1.3, "tier2": 1.15, "tier3": 1.0, "tier4": 0.8}

# Tier 1 today needs real hosting/billing/support infrastructure that does
# not exist (ELITE_ASSET_DOCTRINE.md §6) — its automation_potential is
# LOW until that's built, not high just because "AI Agent" sounds
# automated. Tier 4 (create_book()/generate_printable()) is the one
# actually fully automatic today.
AUTOMATION_POTENTIAL_BY_TIER = {"tier1": 40, "tier2": 85, "tier3": 80, "tier4": 100}

# Tier 1's recurring-revenue ceiling is highest IF it ever gets built;
# Tier 4 is one-off with no recurring/lifetime-value signal at all.
LONG_TERM_VALUE_BY_TIER = {"tier1": 95, "tier2": 70, "tier3": 60, "tier4": 25}

# ADR-026: stricter than inspectors.py's MIN_PROFIT_SCORE=60 — "fewer,
# better assets" means a higher bar, not the same bar applied to a
# fancier-sounding label.
MIN_OPPORTUNITY_SCORE = 65


def opportunity_score(niche, tier="tier4", external_signal=None):
    """Tier-aware composite score (ADR-026). Returns a dict with the final
    0-100 score, whether it clears MIN_OPPORTUNITY_SCORE, and every
    component so a caller/log can show its work — never a bare number with
    no way to audit how it was reached. external_signal (ADR-038): optional
    real engagement evidence ({"source": "hacker_news", "points": N} or
    {"source": "github", "stars": N}, optionally "created_at") — omitting it
    (every current live caller, factory_loop.js always passes tier4 with
    none) reproduces today's exact behavior unchanged."""
    tier = tier if tier in TIER_WEIGHTS else "tier4"
    result = score_opportunity(niche, external_signal=external_signal)
    scores = result["scores"]

    market_demand = scores["demand"]
    competition_favorability = scores["competition"]  # already high=favorable, see score_opportunity()
    profit_potential = scores["margin"]
    automation_potential = AUTOMATION_POTENTIAL_BY_TIER[tier]
    long_term_value = LONG_TERM_VALUE_BY_TIER[tier]

    raw = (
        0.25 * market_demand +
        0.20 * competition_favorability +
        0.20 * profit_potential +
        0.15 * automation_potential +
        0.20 * long_term_value
    )
    weighted = round(min(100.0, raw * TIER_WEIGHTS[tier]), 1)
    # ADR-035: `weighted >= MIN_OPPORTUNITY_SCORE` alone made tier1 trivially
    # easy to pass — automation_potential/long_term_value are fixed per-tier
    # bonuses (not per-niche signal), and tier1's combination of a high
    # long_term_value (95) with the largest tier_weight (1.3) meant even a
    # single-character niche cleared 65. The tier weight still lets an
    # ACCEPTED candidate rank/display higher at a higher tier (unchanged,
    # see test_same_niche_scores_higher_at_higher_tier) — it just no longer
    # buys entry into "accepted" by itself. Acceptance now requires the same
    # underlying raw quality bar tier4 already uses in production
    # (MIN_OPPORTUNITY_SCORE / tier4's own weight), applied tier-invariantly.
    # This is provably a no-op for tier4 itself (raw_floor is literally
    # derived from tier4's existing calibration) and only tightens tier1-3,
    # which have no live caller today (factory_loop.js only ever passes
    # tier4) — zero risk to current production behavior.
    raw_floor = MIN_OPPORTUNITY_SCORE / TIER_WEIGHTS["tier4"]
    accepted = raw >= raw_floor

    return {
        "niche": niche,
        "tier": tier,
        "tier_weight": TIER_WEIGHTS[tier],
        "opportunity_score": weighted,
        "accepted": accepted,
        "min_required": MIN_OPPORTUNITY_SCORE,
        "components": {
            "market_demand": market_demand,
            "competition_favorability": competition_favorability,
            "profit_potential": profit_potential,
            "automation_potential": automation_potential,
            "long_term_value": long_term_value,
        },
        # Red-team audit (Phase 10 follow-up) — MEDIUM finding, fixed: this
        # used to compare `weighted` against the literal MIN_OPPORTUNITY_SCORE
        # constant, but `accepted` is actually decided by `raw >= raw_floor`
        # (tier-invariant, see ADR-035 above) — a different comparison for
        # every tier except tier4. For tier1-3 this produced a false
        # inequality string (e.g. "70/100 < 65" for a niche that was
        # correctly rejected because 70 < 81.25, not because 70 < 65).
        # Dormant today (factory_loop.js's only live caller always passes
        # tier4, where raw_floor's comparison and this one are identical —
        # see test_fix_is_a_no_op_for_tier4's algebraic proof), but a real,
        # permanently-recorded (decisions.jsonl) latent bug for any future
        # tier1-3 caller. Now shows the actual comparison that decided it.
        "reason": (
            f"accepted: opportunity_score {weighted}/100 (raw {raw:.1f} >= {raw_floor:.1f} floor, tier={tier})" if accepted
            else f"rejected: opportunity_score {weighted}/100 (raw {raw:.1f} < {raw_floor:.1f} floor, tier={tier})"
        ),
        # ADR-043: risk/confidence were already computed inside
        # score_opportunity() above (ADR-039) but silently discarded here —
        # same "real data thrown away" pattern ADR-041 found in
        # groq_chat(). Purely additive: two new keys, nothing existing
        # changed, so every current caller is unaffected.
        "risk": result["risk"],
        "confidence": result["confidence"],
        "recommended_price": result["recommended_price"],
        "recommended_platform": result["recommended_platform"],
    }


# ── LADDER OPPORTUNITY SCORE (ADR-065, MASTER_CHARTER.md §2) ──
# A second, additive composite gate for the Strategic Production Priority
# Ladder pivot (2026-07-17) — never modifies opportunity_score() above or
# any of its existing callers/tests. factory_loop.js's Golden Hunter Bridge
# keeps calling opportunity_score() exactly as before; this is the gate a
# ladder-aware caller (market_hunter.py's retooled seed categories, Step 4
# of the same mission) is meant to call instead, once a niche is tagged
# with which of the six ladder ranks it belongs to.
#
# Recurring revenue and reusability are now the two highest-weighted
# factors (mission instruction), reusing score_opportunity()'s real demand/
# competition/margin components UNCHANGED, the same "reuse before
# inventing" discipline as opportunity_score() itself.

LADDER_RANKS = ["ai_saas", "b2b_systems", "automation_tools", "reusable_assets", "educational", "kdp_books"]

# Fixed, documented per-rank constants — same honesty discipline as
# AUTOMATION_POTENTIAL_BY_TIER/LONG_TERM_VALUE_BY_TIER above: no per-niche
# recurring-revenue/reusability signal exists anywhere in this factory yet,
# so these are category-level estimates grounded in MASTER_CHARTER.md §2's
# own stated reasoning for the ladder order, not per-niche guesses.
RECURRING_REVENUE_BY_LADDER = {
    "ai_saas": 100, "b2b_systems": 85, "automation_tools": 55,
    "reusable_assets": 20, "educational": 20, "kdp_books": 10,
}
REUSABILITY_BY_LADDER = {
    "ai_saas": 95, "b2b_systems": 85, "automation_tools": 80,
    "reusable_assets": 90, "educational": 45, "kdp_books": 20,
}

# Which existing butter_price() band each ladder rank is priced against —
# reuses the bands that already exist rather than inventing new pricing
# math: SaaS/B2B command elite pricing ($97-497, ADR-027), automation
# tools/reusable assets sit in the premium band ($50-300, ADR-024),
# educational/KDP stay in the original book band ($30-100).
LADDER_PRICE_BAND = {
    "ai_saas": "elite", "b2b_systems": "elite",
    "automation_tools": "premium", "reusable_assets": "premium",
    "educational": "book", "kdp_books": "book",
}

# Mission-specified hard floor (Step 2): reject anything priced below $97,
# independent of how well it scores otherwise — a separate gate from
# LADDER_MIN_SCORE below, not folded into the weighted formula.
MIN_LADDER_PROFIT_FLOOR = 97

LADDER_MIN_SCORE = 65  # same bar as MIN_OPPORTUNITY_SCORE, applied to this new formula


def ladder_opportunity_score(niche, ladder="kdp_books", external_signal=None):
    """Ladder-aware composite score (ADR-065). Reuses score_opportunity()'s
    real demand/competition/margin components unchanged and adds two new
    ladder-derived factors, weighted highest per the mission's instruction
    ('recurring revenue + reusability weighted highest'). Also enforces a
    hard $97 profit floor via the ladder's real butter_price() band —
    independent of the weighted score, so a well-scoring but cheaply-priced
    niche still can't pass. Unknown ladder values fall back to "kdp_books"
    (the strictest band), never silently accepted."""
    ladder = ladder if ladder in RECURRING_REVENUE_BY_LADDER else "kdp_books"
    result = score_opportunity(niche, external_signal=external_signal)
    scores = result["scores"]

    market_demand = scores["demand"]
    competition_favorability = scores["competition"]
    profit_potential = scores["margin"]
    recurring_revenue_potential = RECURRING_REVENUE_BY_LADDER[ladder]
    reusability = REUSABILITY_BY_LADDER[ladder]

    raw = (
        0.15 * market_demand +
        0.15 * competition_favorability +
        0.15 * profit_potential +
        0.25 * recurring_revenue_potential +
        0.30 * reusability
    )
    ladder_score = round(min(100.0, raw), 1)

    price_band = LADDER_PRICE_BAND[ladder]
    price = butter_price(niche, product_type=price_band)
    clears_profit_floor = price >= MIN_LADDER_PROFIT_FLOOR
    clears_score_floor = ladder_score >= LADDER_MIN_SCORE
    accepted = clears_score_floor and clears_profit_floor

    if not clears_profit_floor:
        reason = f"rejected: price ${price} below ${MIN_LADDER_PROFIT_FLOOR} profit floor (ladder={ladder})"
    elif not clears_score_floor:
        reason = f"rejected: ladder_score {ladder_score}/100 < {LADDER_MIN_SCORE} (ladder={ladder})"
    else:
        reason = f"accepted: ladder_score {ladder_score}/100 >= {LADDER_MIN_SCORE}, price ${price} >= ${MIN_LADDER_PROFIT_FLOOR} (ladder={ladder})"

    return {
        "niche": niche,
        "ladder": ladder,
        "ladder_score": ladder_score,
        "price": price,
        "accepted": accepted,
        "reason": reason,
        "components": {
            "market_demand": market_demand,
            "competition_favorability": competition_favorability,
            "profit_potential": profit_potential,
            "recurring_revenue_potential": recurring_revenue_potential,
            "reusability": reusability,
        },
        "risk": result["risk"],
        "confidence": result["confidence"],
    }


def butter_price(niche, product_type="book"):
    """Smart Publishing + Butter Principle (OPENCLAW_OS_CONSTITUTION.md /
    CONSTITUTION.md §16): given a niche, returns a defensible price — never
    a flat number for everything, never a fabricated one. The starting tier
    reuses the same keyword vocabulary _score_margin() already scores this
    niche's margin against (premium/recurring signals → a higher defensible
    starting point), then this niche's OWN profit_score scales it upward
    within the remaining headroom to the ceiling — a stronger niche (higher
    demand, lower competition) can defensibly ask for more, rather than
    every repriced niche landing on the same number.

    product_type="book" (default, unchanged): $30-$100 KDP-ebook band.
    product_type="printable" (ADR-020): $5-$15 EU/US Gumroad-printable band
    — $30 reads as absurd for a 10-30 page planner/tracker in that market.
    product_type="premium" (ADR-024): $50-$300 EU/US Gumroad premium-bundle
    band (HIGH_VALUE_STRATEGY.md) — human+Claude-authored content, not
    Groq, is what justifies this band; profit_score alone never does.
    product_type="elite" (ADR-027/ELITE_ASSET_DOCTRINE.md): $97-$497 Tier 1
    band — highest bar, gated further upstream by opportunity_score()'s
    tier1 weighting, never approved on profit_score alone either.
    Every existing caller that doesn't pass product_type gets byte-for-byte
    the same book pricing as before this parameter existed.

    Callers are expected to only invoke this for niches that are not
    genuinely weak (see score_opportunity()'s verdict != 'SKIP') — a niche
    with real thin demand or saturated competition doesn't become viable
    just because a bigger number was attached to it."""
    niche = str(niche or '').strip()
    if not niche:
        raise ValueError("النيتش (niche) مطلوب")

    if product_type == "printable":
        min_price, max_price = MIN_BUTTER_PRICE_PRINTABLE, MAX_BUTTER_PRICE_PRINTABLE
    elif product_type == "premium":
        min_price, max_price = MIN_BUTTER_PRICE_PREMIUM, MAX_BUTTER_PRICE_PREMIUM
    elif product_type == "elite":
        min_price, max_price = MIN_BUTTER_PRICE_ELITE, MAX_BUTTER_PRICE_ELITE
    else:
        min_price, max_price = MIN_BUTTER_PRICE, MAX_BUTTER_PRICE

    result = score_opportunity(niche)
    score = result['profit_score']
    niche_lower = niche.lower()

    if product_type == "printable":
        # Same keyword signals, rescaled proportionally into the $5-15 band
        # instead of book pricing's $30/$45/$60 tiers. Formula untouched
        # since ADR-020 shipped this morning — verified byte-for-byte
        # identical across 12 real niches before adding the "premium"
        # branch below.
        if any(k in niche_lower for k in PREMIUM_KEYWORDS):
            base = min_price + (max_price - min_price) * 0.5   # ~$10
        elif any(k in niche_lower for k in MID_KEYWORDS):
            base = min_price + (max_price - min_price) * 0.25  # ~$7.5
        else:
            base = min_price + 1  # $6 — still comfortably above the floor
        if any(k in niche_lower for k in RECURRING_KEYWORDS):
            base += (max_price - min_price) * 0.15  # ~$1.5 more for a subscription-able product
    elif product_type == "premium":
        # ADR-024: same keyword signals, rescaled proportionally into the
        # $50-300 band — a separate branch from "printable" (not a shared
        # formula) so shipped printable pricing can never shift as a side
        # effect of adding this one.
        if any(k in niche_lower for k in PREMIUM_KEYWORDS):
            base = min_price + (max_price - min_price) * 0.5   # ~$175
        elif any(k in niche_lower for k in MID_KEYWORDS):
            base = min_price + (max_price - min_price) * 0.25  # ~$112.5
        else:
            base = min_price + 10  # $60 — still comfortably above the floor
        if any(k in niche_lower for k in RECURRING_KEYWORDS):
            base += (max_price - min_price) * 0.15  # ~$37.5 more for a subscription-able product
    elif product_type == "elite":
        # ADR-027: same keyword signals, rescaled proportionally into the
        # $97-497 band — its own branch, never shares a formula with
        # "premium"/"printable" so neither shifts as a side effect of
        # adding this one.
        if any(k in niche_lower for k in PREMIUM_KEYWORDS):
            base = min_price + (max_price - min_price) * 0.5   # ~$297
        elif any(k in niche_lower for k in MID_KEYWORDS):
            base = min_price + (max_price - min_price) * 0.25  # ~$197
        else:
            base = min_price + 20  # $117 — still comfortably above the floor
        if any(k in niche_lower for k in RECURRING_KEYWORDS):
            base += (max_price - min_price) * 0.15  # ~$60 more for a subscription-able product
    else:
        if any(k in niche_lower for k in PREMIUM_KEYWORDS):
            base = 60
        elif any(k in niche_lower for k in MID_KEYWORDS):
            base = 45
        else:
            base = min_price + 5  # $35 — still comfortably above the floor
        if any(k in niche_lower for k in RECURRING_KEYWORDS):
            base += 10  # a subscription-able product defensibly commands more

    base = min(base, max_price)
    headroom = max_price - base
    scaled = base + headroom * max(0, score - 60) / 40  # score 60→base, 100→ceiling

    return round(min(max_price, max(min_price, scaled)))


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


# ADR-070 (mission follow-up, 2026-07-17): a second, separate reader from
# _read_opportunities() above rather than changing that function's return
# shape — real_world_mode/signal_intake.py's intake_from_opportunities_md()
# already depends on _read_opportunities() returning a plain list of niche
# strings (tests/test_real_world_mode.py), so extending it in place would
# break a real, working consumer for no benefit to it. This extracts the
# same OPPORTUNITIES.md lines PLUS an optional ladder=<rank> tag from the
# reason text — the exact tag market_hunter.py's _append_to_opportunities()
# writes for every real ACCEPTED candidate (ADR-068). Entries with no tag
# (every Sensing Engine signal, every pre-ladder entry) get ladder=None.
_LADDER_TAG_RE = re.compile(r'ladder=(\w+)')


def _read_opportunities_with_ladder():
    if not os.path.exists(OPPORTUNITIES_FILE):
        return []
    line_re = re.compile(r'^-\s*\[(.+?)\]\s*(.+?)\s*—\s*(.+)$')
    entries = []
    with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            m = line_re.match(line.strip())
            if not m:
                continue
            niche = m.group(2).strip()
            reason = m.group(3).strip()
            ladder_match = _LADDER_TAG_RE.search(reason)
            entries.append({"niche": niche, "ladder": ladder_match.group(1) if ladder_match else None})
    return entries


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
    for server.js's /oracle endpoint and factory_loop.js's Golden Hunter
    Bridge). score_opportunity() still runs for every niche unchanged (the
    human report / every pre-ladder consumer keeps working byte-for-byte
    the same); a niche carrying a ladder=<rank> tag (ADR-068) also gets
    scored via ladder_opportunity_score() (ADR-066), and its result is
    merged in as additive ladder/ladder_score/ladder_accepted/ladder_price
    fields.

    ADR-070: sort order now puts every ladder_accepted=True result first
    (ranked among themselves by ladder_score), THEN falls back to the
    original profit_score descending order for everything else — the
    concrete fix for the gap ADR-069 disclosed (factory_loop.js's
    automatic tick still picking old KDP niches over newly-accepted AI
    SaaS/B2B ones). A file with no ladder-tagged entries at all sorts
    exactly as before (every result has ladder_accepted=None -> falsy ->
    same profit_score-only ordering)."""
    entries = _read_opportunities_with_ladder()
    results = []
    for entry in entries:
        niche = entry["niche"]
        result = score_opportunity(niche)
        ladder = entry["ladder"]
        if ladder and ladder in LADDER_RANKS:
            ladder_result = ladder_opportunity_score(niche, ladder=ladder)
            result["ladder"] = ladder
            result["ladder_score"] = ladder_result["ladder_score"]
            result["ladder_accepted"] = ladder_result["accepted"]
            result["ladder_price"] = ladder_result["price"]
        results.append(result)

    results.sort(
        key=lambda r: (
            bool(r.get('ladder_accepted')),
            r['ladder_score'] if r.get('ladder_accepted') else r['profit_score'],
        ),
        reverse=True,
    )
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

    # ADR-010: a purely additive invocation surface for the EXISTING
    # butter_price() — no scoring/pricing logic changed here. Added so
    # factory_loop.js's Golden Hunter bridge can route through the real
    # constitutional price (CONSTITUTION.md §16) instead of trusting
    # score_opportunity()'s recommended_price field, which is _score_margin()'s
    # keyword-tier estimate and can land below the $30 floor.
    if '--butter-price' in sys.argv:
        try:
            data = json.loads(sys.stdin.read())
            product_type = data.get('product_type', 'book')  # ADR-020: "printable" -> $5-15 EU/US band
            price = butter_price(data.get('niche', ''), product_type=product_type)
            print(json.dumps({"success": True, "niche": data.get('niche', ''), "product_type": product_type, "butter_price": price}, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        return

    # ADR-026: purely additive invocation surface for the EXISTING
    # opportunity_score() — so factory_loop.js can call it the same way it
    # already calls --butter-price, no new spawn pattern needed.
    if '--opportunity-score' in sys.argv:
        try:
            data = json.loads(sys.stdin.read())
            result = opportunity_score(data.get('niche', ''), tier=data.get('tier', 'tier4'), external_signal=data.get('external_signal'))
            print(json.dumps({"success": True, **result}, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        return

    # ADR-065: purely additive invocation surface for the EXISTING
    # ladder_opportunity_score() — same spawn pattern as --opportunity-score,
    # for market_hunter.py/factory_loop.js to call once a niche is tagged
    # with a Strategic Production Priority Ladder rank (Step 4).
    if '--ladder-score' in sys.argv:
        try:
            data = json.loads(sys.stdin.read())
            result = ladder_opportunity_score(
                data.get('niche', ''),
                ladder=data.get('ladder', 'kdp_books'),
                external_signal=data.get('external_signal'),
            )
            print(json.dumps({"success": True, **result}, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        return

    # Autonomous Digital Company v1 follow-up (2026-07-19): real, narrow
    # gate reusing executive_intelligence's already-tested engine-health
    # detection (ADR-052) -- "data flows, not isolated modules". Needs no
    # stdin (checks real, factory-wide production-engine history, not a
    # per-niche input) — same spawn pattern as --opportunity-score/
    # --ladder-score, for factory_loop.js's Golden Hunter Bridge to call
    # right before dispatching a real production run.
    if '--production-health-gate' in sys.argv:
        try:
            from executive_intelligence.production_gate import check_production_engine_health
            result = check_production_engine_health()
            print(json.dumps({"success": True, **result}, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
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

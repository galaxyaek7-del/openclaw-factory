#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — FACTORY_AUTO_PRODUCE Readiness Certificate (ADR-011)

Answers exactly one question, with evidence, not feeling:
  "Has the factory proven in dry_run that it's ready for FACTORY_AUTO_PRODUCE=true?"

Read-only. This script never writes to, deletes, or triggers anything in
the production pipeline — it only reads existing files (data/
golden_hunter_events.jsonl, factory_loop.log, golden_opportunities.json,
market_hunter_runs.log, NEEDS_ATTENTION.md) and appends one summary line
per run to data/readiness_history.jsonl (its own tracking log, the same
append-only pattern as every other ledger in this factory). It does not
set FACTORY_AUTO_PRODUCE, does not call book_generator.py or distributor.py,
and does not modify golden_hunter_events.jsonl or any business-logic file.

The final activation decision stays with Chairman Abdelkader — this script
only signs a certificate for him to read.

Usage:
    python scripts/readiness_certificate.py

Exit codes: READY=0, NOT_READY_YET=1, BLOCKED=2, (unexpected)=3
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent

GOLDEN_HUNTER_EVENTS_FILE = FACTORY_DIR / 'data' / 'golden_hunter_events.jsonl'
FACTORY_LOOP_LOG = FACTORY_DIR / 'factory_loop.log'
GOLDEN_JSON_FILE = FACTORY_DIR / 'golden_opportunities.json'
HUNTER_LOG = FACTORY_DIR / 'market_hunter_runs.log'
NEEDS_ATTENTION_FILE = FACTORY_DIR / 'NEEDS_ATTENTION.md'
READINESS_HISTORY_FILE = FACTORY_DIR / 'data' / 'readiness_history.jsonl'

# Criteria thresholds (ADR-011) — the exact numbers requested, with reasoning
# recorded there, not just here.
CONTINUOUS_OPERATION_HOURS = 48
MAX_TICK_GAP_MINUTES = 20          # 2x the 10-minute tick interval
MIN_DISTINCT_NICHES = 3
ATTENTION_FREE_WINDOW_HOURS = 24
STREAK_THRESHOLD = 3               # mirrors factory_loop.js's ATTENTION_STREAK_THRESHOLD
MIN_BUTTER_PRICE = 30              # CONSTITUTION.md §16 — mirrors profit_oracle.py's MIN_BUTTER_PRICE
FRESHNESS_HOURS = 24
DISCOVERY_WINDOW_HOURS = 48


# ── UTIL ──

def _parse_timestamp(ts_str):
    """This factory uses two timestamp conventions across different files:
    real UTC with a 'Z' suffix (factory_loop.js's own writes — golden_hunter_
    events.jsonl, factory_loop.log) and naive local time (Python's
    datetime.now().isoformat() — golden_opportunities.json, market_hunter_
    runs.log). Both are normalized to an aware UTC datetime here so every
    comparison in this script is apples-to-apples. Returns None, never
    raises, on anything unparseable."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    try:
        normalized = ts_str.replace('Z', '+00:00') if ts_str.endswith('Z') else ts_str
        dt = datetime.fromisoformat(normalized)
        # aware -> normalizes to UTC; naive -> Python treats it as system
        # local time and converts, matching every other timestamp-parsing
        # spot in this factory (see factory_loop.js's own note on this).
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _load_jsonl(path):
    """Defensive JSONL reader — mirrors channels/ledger.py's own pattern.
    Missing file -> []. A malformed line is skipped, never crashes the run."""
    path = Path(path)
    if not path.exists():
        return []
    records = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except (TypeError, ValueError):
                    continue
    except Exception:
        return []
    return records


def _load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


# ── CRITERION 1: continuous operation ──

def check_continuous_operation(now, log_path=FACTORY_LOOP_LOG,
                                window_hours=CONTINUOUS_OPERATION_HOURS,
                                max_gap_minutes=MAX_TICK_GAP_MINUTES):
    """Measures the CURRENT unbroken run, not "was there ever a gap
    somewhere in the last 48h" — a manual `--once` test run hours before
    the continuous loop started is not a crash and must not be counted as
    one. Walks backward from the most recent tick and stops at the first
    gap wider than max_gap_minutes or the first action:"error" tick; that
    boundary is the start of the current streak. A real crash-and-restart
    naturally shows up here too: the streak resets and span_hours drops,
    without needing a separate error path."""
    entries = _load_jsonl(log_path)
    parsed = []
    for e in entries:
        ts = _parse_timestamp(e.get('timestamp'))
        if ts:
            parsed.append((ts, e))
    parsed.sort(key=lambda x: x[0])

    if not parsed:
        return {
            'name': 'continuous_operation_48h',
            'status': 'PENDING',
            'detail': f'لا سجلات دورات في factory_loop.log — العملية المستمرة لم تبدأ بعد.',
            'evidence': {'ticks_in_streak': 0, 'span_hours': 0},
        }

    streak = [parsed[-1]]
    for i in range(len(parsed) - 2, -1, -1):
        ts, e = parsed[i]
        prev_ts = streak[-1][0]
        gap_min = (prev_ts - ts).total_seconds() / 60
        has_error = any(a.get('action') == 'error' for a in (e.get('actions') or []))
        if gap_min > max_gap_minutes or has_error:
            break
        streak.append((ts, e))
    streak.reverse()

    streak_start = streak[0][0]
    span_hours = (now - streak_start).total_seconds() / 3600
    status = 'PASS' if span_hours >= window_hours else 'PENDING'

    detail = (
        f'التشغيل المستمر الحالي بلا انقطاع منذ {streak_start.isoformat()} '
        f'({round(span_hours, 1)} ساعة من أصل {window_hours} مطلوبة، {len(streak)} دورة مسجَّلة)'
    )

    return {
        'name': 'continuous_operation_48h',
        'status': status,
        'detail': detail,
        'evidence': {
            'streak_start': streak_start.isoformat(),
            'span_hours': round(span_hours, 1),
            'ticks_in_streak': len(streak),
            'total_ticks_ever_logged': len(parsed),
        },
    }


# ── CRITERION 2: distinct niches exercised ──

def check_distinct_niches(events, min_distinct=MIN_DISTINCT_NICHES):
    attempted = [e for e in events if e.get('action') == 'attempted' and e.get('niche')]
    distinct = {}
    for e in attempted:
        key = str(e['niche']).strip().lower()
        distinct.setdefault(key, e['niche'])

    status = 'PASS' if len(distinct) >= min_distinct else 'PENDING'
    detail = f'{len(distinct)} نيتش مختلف ظهر في محاولات dry_run حتى الآن (الهدف: {min_distinct})'
    if len(distinct) == 1 and len(attempted) >= 3:
        detail += (' — نفس النيتش الوحيد يتكرر رغم عدة دورات؛ راجع ما إذا كانت قائمة مرشَّحي '
                    'Golden Hunter محدودة التنوع فعلياً قبل افتراض أنها مسألة وقت فقط (ADR-011)')

    return {
        'name': 'distinct_niches_ge_3',
        'status': status,
        'detail': detail,
        'evidence': {'distinct_niches': list(distinct.values()), 'count': len(distinct), 'total_attempts': len(attempted)},
    }


# ── CRITERION 3: no NEEDS_ATTENTION.md trigger in the last 24h ──

def check_needs_attention_free(now, events, log_path=FACTORY_LOOP_LOG,
                                attention_file=NEEDS_ATTENTION_FILE,
                                window_hours=ATTENTION_FREE_WINDOW_HOURS,
                                streak=STREAK_THRESHOLD):
    """NEEDS_ATTENTION.md itself has no persisted history (it's a live flag
    factory_loop.js creates/deletes) — so its past 24h of activity is
    reconstructed here by replaying factory_loop.js's own trigger logic
    (checkNeedsAttention() in factory_loop.js) against the event history,
    not by reading a log of past appearances that doesn't exist."""
    window_start = now - timedelta(hours=window_hours)

    windowed = []
    for e in events:
        ts = _parse_timestamp(e.get('timestamp'))
        if ts and ts >= window_start:
            windowed.append(e)

    currently_flagged = Path(attention_file).exists()

    stale_streak_found = False
    for i in range(len(windowed) - streak + 1):
        chunk = windowed[i:i + streak]
        if all(e.get('action') == 'skipped' and e.get('reason') in ('stale', 'missing_or_unreadable') for e in chunk):
            stale_streak_found = True
            break

    attempted_windowed = [e for e in windowed if e.get('action') == 'attempted']
    fallback_streak_found = False
    for i in range(len(attempted_windowed) - streak + 1):
        chunk = attempted_windowed[i:i + streak]
        if all((e.get('brief') or {}).get('_price_source') == 'fallback_floor_clamped' for e in chunk):
            fallback_streak_found = True
            break

    log_entries = _load_jsonl(log_path)
    failed_ticks = []
    for e in log_entries:
        ts = _parse_timestamp(e.get('timestamp'))
        if not ts or ts < window_start:
            continue
        for a in (e.get('actions') or []):
            if a.get('step') in ('golden_hunter_bridge', 'distribute') and a.get('action') == 'failed':
                failed_ticks.append({'timestamp': ts.isoformat(), 'step': a.get('step'), 'detail': a.get('detail')})

    problem_found = currently_flagged or stale_streak_found or fallback_streak_found or bool(failed_ticks)
    status = 'FAIL' if problem_found else 'PASS'

    reasons = []
    if currently_flagged:
        reasons.append('NEEDS_ATTENTION.md موجود الآن')
    if stale_streak_found:
        reasons.append(f'سلسلة {streak} تخطّيات متتالية (stale/missing) خلال آخر {window_hours} ساعة')
    if fallback_streak_found:
        reasons.append(f'سلسلة {streak} محاولات تسعير fallback_floor_clamped متتالية خلال آخر {window_hours} ساعة')
    if failed_ticks:
        reasons.append(f'{len(failed_ticks)} دورة بفشل حقيقي (golden_hunter_bridge/distribute) خلال آخر {window_hours} ساعة')

    return {
        'name': 'needs_attention_free_24h',
        'status': status,
        'detail': '؛ '.join(reasons) if reasons else f'لا مشاكل مكتشَفة خلال آخر {window_hours} ساعة (إعادة تشغيل منطق NEEDS_ATTENTION.md ضد التاريخ)',
        'evidence': {
            'currently_flagged': currently_flagged,
            'stale_streak_found': stale_streak_found,
            'fallback_streak_found': fallback_streak_found,
            'failed_ticks': failed_ticks[:5],
        },
    }


# ── CRITERION 4: every RECENT attempted price respected the constitutional floor ──

def check_constitutional_pricing(now, events, min_price=MIN_BUTTER_PRICE,
                                  window_hours=ATTENTION_FREE_WINDOW_HOURS):
    """Scoped to a recent window, not "ever in history" — a one-time bug
    that was found and fixed same-day (ADR-010) should be able to age out
    and let this criterion legitimately go PASS again once enough clean
    recent evidence exists, rather than blocking forever on a resolved
    issue. Older violations are never hidden, just reported separately in
    evidence['historical_violations_outside_window'] so nothing silently
    disappears from the record."""
    attempted = [e for e in events if e.get('action') == 'attempted' and e.get('brief')]
    if not attempted:
        return {
            'name': 'constitutional_pricing',
            'status': 'PENDING',
            'detail': 'لا محاولات dry_run مسجَّلة بعد للتحقق من التسعير.',
            'evidence': {'total_attempted': 0, 'violations': [], 'historical_violations_outside_window': []},
        }

    window_start = now - timedelta(hours=window_hours)

    def _is_violation(e):
        brief = e['brief']
        price = brief.get('price')
        source = brief.get('_price_source')
        return price is None or price < min_price or source == 'fallback_floor_clamped'

    recent = []
    recent_violations = []
    older_violations = []
    for e in attempted:
        ts = _parse_timestamp(e.get('timestamp'))
        in_window = ts is not None and ts >= window_start
        if in_window:
            recent.append(e)
        if _is_violation(e):
            entry = {'niche': e.get('niche'), 'price': e['brief'].get('price'),
                      'price_source': e['brief'].get('_price_source'), 'timestamp': e.get('timestamp')}
            (recent_violations if in_window else older_violations).append(entry)

    if not recent:
        return {
            'name': 'constitutional_pricing',
            'status': 'PENDING',
            'detail': f'لا محاولات dry_run خلال آخر {window_hours} ساعة للتحقق من التسعير الحالي.',
            'evidence': {'total_attempted': len(attempted), 'violations': [], 'historical_violations_outside_window': older_violations[:5]},
        }

    status = 'PASS' if not recent_violations else 'FAIL'
    detail = (
        f'كل {len(recent)} محاولة تسعير خلال آخر {window_hours} ساعة التزمت بالحد الدستوري (≥{min_price}$) عبر butter_price() الحقيقية (ADR-010)'
        if not recent_violations else
        f'{len(recent_violations)} من {len(recent)} محاولة خلال آخر {window_hours} ساعة خالفت الحد الدستوري أو استخدمت السقوط الآمن'
    )
    if older_violations:
        detail += f' (+ {len(older_violations)} مخالفة تاريخية أقدم من النافذة، غير محتسَبة هنا لكن مذكورة في الدليل)'

    return {
        'name': 'constitutional_pricing',
        'status': status,
        'detail': detail,
        'evidence': {
            'total_attempted': len(attempted),
            'violations': recent_violations[:5],
            'historical_violations_outside_window': older_violations[:5],
        },
    }


# ── CRITERION 5: Golden Hunter discovers fresh opportunities regularly ──

def check_fresh_discovery(now, golden_json_path=GOLDEN_JSON_FILE, hunter_log_path=HUNTER_LOG,
                           window_hours=DISCOVERY_WINDOW_HOURS, freshness_hours=FRESHNESS_HOURS):
    data = _load_json(golden_json_path)
    current_age_hours = None
    if data and data.get('generated_at'):
        ts = _parse_timestamp(data['generated_at'])
        if ts:
            current_age_hours = round((now - ts).total_seconds() / 3600, 1)
    current_fresh = current_age_hours is not None and current_age_hours <= freshness_hours

    hunter_entries = _load_jsonl(hunter_log_path)
    window_start = now - timedelta(hours=window_hours)
    runs_in_window = []
    for e in hunter_entries:
        ts = _parse_timestamp(e.get('timestamp'))
        if ts and ts >= window_start:
            runs_in_window.append(ts)
    runs_in_window.sort()

    expected_runs = max(1, window_hours // 24)  # ~1 run/day expected
    regular = len(runs_in_window) >= expected_runs

    if data is None:
        status = 'FAIL'
    elif current_fresh and regular:
        status = 'PASS'
    else:
        status = 'PENDING'

    parts = []
    parts.append(
        f'آخر تحديث لـ golden_opportunities.json منذ {current_age_hours} ساعة (الحد: {freshness_hours})'
        if current_age_hours is not None else
        'golden_opportunities.json غير موجود أو تاريخه غير صالح'
    )
    parts.append(f'{len(runs_in_window)} تشغيلة لـ market_hunter خلال آخر {window_hours} ساعة (المتوقَّع: {expected_runs}+)')

    return {
        'name': 'fresh_discovery_regular',
        'status': status,
        'detail': '؛ '.join(parts),
        'evidence': {
            'current_age_hours': current_age_hours,
            'runs_in_window': len(runs_in_window),
            'run_timestamps': [t.isoformat() for t in runs_in_window],
        },
    }


# ── ETA (only for NOT_READY_YET) ──

def _estimate_eta(now, checks):
    by_name = {c['name']: c for c in checks}
    parts = []
    concrete_hours = []
    uncertain = False

    cont = by_name['continuous_operation_48h']
    if cont['status'] == 'PENDING':
        span = cont['evidence'].get('span_hours', 0)
        remaining = max(0.0, CONTINUOUS_OPERATION_HOURS - span)
        concrete_hours.append(remaining)
        parts.append(f'التشغيل المستمر: ~{round(remaining, 1)} ساعة متبقية إن استمر بلا انقطاع')

    niches = by_name['distinct_niches_ge_3']
    if niches['status'] == 'PENDING':
        count = niches['evidence'].get('count', 0)
        parts.append(f'التنوّع: {count}/{MIN_DISTINCT_NICHES} نيتش مختلف — يعتمد على تنوّع نتائج market_hunter القادمة، لا معدل ثابت يمكن ضمانه')
        uncertain = True

    fresh = by_name['fresh_discovery_regular']
    if fresh['status'] == 'PENDING':
        parts.append('انتظام اكتشاف Golden Hunter غير مؤكَّد بعد بما يكفي من السجل التاريخي')
        uncertain = True

    pricing = by_name['constitutional_pricing']
    if pricing['status'] == 'PENDING':
        parts.append('لا محاولات تسعير كافية بعد للحكم')
        uncertain = True

    if not parts:
        return None

    if concrete_hours and not uncertain:
        eta_time = now + timedelta(hours=max(concrete_hours))
        headline = f'أقرب تقدير: {eta_time.isoformat()} (إن استمرت كل المؤشرات دون تراجع)'
    elif concrete_hours:
        eta_time = now + timedelta(hours=max(concrete_hours))
        headline = f'لا يقل عن {eta_time.isoformat()} — لكن معياراً آخر غير قابل للتقدير الزمني بثقة (انظر التفاصيل)'
    else:
        headline = 'غير قابل للتقدير الزمني بثقة — يعتمد على تنوّع بيانات مستقبلية، لا معدل ثابت'

    return headline + ' | ' + '؛ '.join(parts)


# ── CERTIFICATE ──

def build_certificate(now=None, events_path=GOLDEN_HUNTER_EVENTS_FILE, log_path=FACTORY_LOOP_LOG,
                       golden_json_path=GOLDEN_JSON_FILE, hunter_log_path=HUNTER_LOG,
                       attention_file=NEEDS_ATTENTION_FILE):
    now = now or datetime.now(timezone.utc)
    events = _load_jsonl(events_path)

    checks = [
        check_continuous_operation(now, log_path=log_path),
        check_distinct_niches(events),
        check_needs_attention_free(now, events, log_path=log_path, attention_file=attention_file),
        check_constitutional_pricing(now, events),
        check_fresh_discovery(now, golden_json_path=golden_json_path, hunter_log_path=hunter_log_path),
    ]

    statuses = [c['status'] for c in checks]
    if any(s == 'FAIL' for s in statuses):
        verdict = 'BLOCKED'
    elif all(s == 'PASS' for s in statuses):
        verdict = 'READY'
    else:
        verdict = 'NOT_READY_YET'

    eta = _estimate_eta(now, checks) if verdict == 'NOT_READY_YET' else None

    return {
        'timestamp': now.isoformat(),
        'verdict': verdict,
        'checks': checks,
        'eta_estimate': eta,
    }


def append_readiness_history(certificate, history_path=READINESS_HISTORY_FILE):
    summary = {
        'timestamp': certificate['timestamp'],
        'verdict': certificate['verdict'],
        'checks': {c['name']: c['status'] for c in certificate['checks']},
        'eta_estimate': certificate.get('eta_estimate'),
    }
    try:
        Path(history_path).parent.mkdir(parents=True, exist_ok=True)
        with open(history_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(summary, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f'[readiness_certificate] تحذير: تعذّرت الكتابة إلى {history_path}: {e}', file=sys.stderr)
    return summary


STATUS_LABELS = {'PASS': '✅ PASS', 'FAIL': '❌ FAIL', 'PENDING': '⏳ PENDING'}
VERDICT_LABELS = {
    'READY': '🟢 READY — المصنع أثبت جاهزيته بالأدلة. القرار النهائي يبقى للرئيس.',
    'NOT_READY_YET': '🟡 NOT_READY_YET — لم يكتمل الإثبات بعد. التقدير أدناه.',
    'BLOCKED': '🔴 BLOCKED — مشكلة فعلية موجودة الآن، لا مسألة وقت. راجع الأسباب قبل أي انتظار.',
}


def format_report(cert):
    lines = []
    lines.append('=' * 70)
    lines.append('شهادة الجاهزية لتفعيل FACTORY_AUTO_PRODUCE')
    lines.append(f'التاريخ: {cert["timestamp"]}')
    lines.append('=' * 70)
    lines.append('')
    for c in cert['checks']:
        lines.append(f'[{STATUS_LABELS[c["status"]]}] {c["name"]}')
        lines.append(f'  الدليل: {c["detail"]}')
        lines.append('')
    lines.append('-' * 70)
    lines.append(f'القرار: {VERDICT_LABELS[cert["verdict"]]}')
    if cert.get('eta_estimate'):
        lines.append(f'التقدير: {cert["eta_estimate"]}')
    lines.append('-' * 70)
    lines.append('هذا السكريبت شاهد فقط — لا يفعّل FACTORY_AUTO_PRODUCE ولا أي شيء آخر بنفسه.')
    lines.append('القرار النهائي يبقى للرئيس عبد القادر، بعد قراءة هذه الشهادة.')
    return '\n'.join(lines)


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except Exception:
            pass

    cert = build_certificate()
    print(format_report(cert))
    append_readiness_history(cert)

    exit_codes = {'READY': 0, 'NOT_READY_YET': 1, 'BLOCKED': 2}
    sys.exit(exit_codes.get(cert['verdict'], 3))


if __name__ == '__main__':
    main()

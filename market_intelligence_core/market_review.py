"""
Weekly Market Review (EOS Phase 1, 2026-07-19) — the one genuinely
missing "Continuous Improvement Engine" review type. Pure aggregation
over data this factory already logs; no new scoring, no new judgment.

- Niches scanned in the period: real counts from data/golden_hunter_events.jsonl's
  own "attempted"/"skipped" actions (Golden Hunter's fixed seed list AND
  Pioneer's real discoveries both funnel through market_hunter.hunt_market()'s
  existing loop into this same file -- no separate Pioneer count needed).
- Opportunity-gap / customer-pain trend: real averages from
  data/market_intelligence_analyses.jsonl, period vs. all-time (a
  DISCOVERY-level answer, not a forecast, when too little history exists).
- Top rejection reasons: reuses strategic_intelligence.rejection_patterns
  .most_frequent_rejection_reasons() verbatim -- already real, tested,
  and deliberately limited to the honest categorical ai_ceo_decision
  field rather than free-text clustering (ADR-054). Not reimplemented here.
"""

import json
import os
from datetime import datetime, timedelta, timezone

FACTORY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_HUNTER_EVENTS_FILE = os.path.join(FACTORY_DIR, 'data', 'golden_hunter_events.jsonl')
MARKET_INTELLIGENCE_ANALYSES_FILE = os.path.join(FACTORY_DIR, 'data', 'market_intelligence_analyses.jsonl')


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _parse_ts(value):
    if not value:
        return None
    try:
        text = str(value).replace('Z', '+00:00')
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _scan_summary(days, now, events_path):
    events = _read_jsonl(events_path)
    since = now - timedelta(days=days)
    period_niches = set()
    for e in events:
        if e.get('action') not in ('attempted', 'skipped'):
            continue
        ts = _parse_ts(e.get('timestamp'))
        if ts is None or ts < since:
            continue
        niche = e.get('niche')
        if niche:
            period_niches.add(niche)
    return {
        "niches_scanned": len(period_niches),
        "source": "data/golden_hunter_events.jsonl (attempted+skipped actions, Golden Hunter + Pioneer combined)",
    }


def _opportunity_trend(days, now, analyses_path):
    analyses = _read_jsonl(analyses_path)
    since = now - timedelta(days=days)

    period_gaps, all_gaps = [], []
    period_pain, all_pain = [], []
    for a in analyses:
        gap = a.get('opportunity_gap')
        pain = (a.get('customer_pain') or {}).get('pain_score')
        ts = _parse_ts(a.get('analyzed_at'))
        if isinstance(gap, (int, float)):
            all_gaps.append(gap)
            if ts and ts >= since:
                period_gaps.append(gap)
        if isinstance(pain, (int, float)):
            all_pain.append(pain)
            if ts and ts >= since:
                period_pain.append(pain)

    if not all_gaps:
        return {
            "answer": "Unknown",
            "reason": "لا تحليلات ذكاء سوق حقيقية مسجَّلة بعد في data/market_intelligence_analyses.jsonl",
        }

    def _avg(values):
        return round(sum(values) / len(values), 1) if values else None

    return {
        "period_avg_opportunity_gap": _avg(period_gaps),
        "all_time_avg_opportunity_gap": _avg(all_gaps),
        "period_avg_pain_score": _avg(period_pain),
        "all_time_avg_pain_score": _avg(all_pain),
        "period_sample_size": len(period_gaps),
        "all_time_sample_size": len(all_gaps),
        "source": "data/market_intelligence_analyses.jsonl",
    }


def generate_market_review(days=7, now=None, events_path=None, analyses_path=None, decisions_path=None):
    from strategic_intelligence import rejection_patterns

    now = now or datetime.now(timezone.utc)
    events_path = events_path or GOLDEN_HUNTER_EVENTS_FILE
    analyses_path = analyses_path or MARKET_INTELLIGENCE_ANALYSES_FILE

    return {
        "generated_at": now.isoformat(),
        "period_days": days,
        "scan_summary": _scan_summary(days, now, events_path),
        "opportunity_trend": _opportunity_trend(days, now, analyses_path),
        "top_rejection_reasons": rejection_patterns.most_frequent_rejection_reasons(decisions_path=decisions_path),
    }


def render_markdown(report):
    lines = [f"**الفترة:** آخر {report['period_days']} يوماً"]

    scan = report["scan_summary"]
    lines.append(f"**نيتشات مُمسوحة:** {scan['niches_scanned']} (المصدر: {scan['source']})")

    trend = report["opportunity_trend"]
    if trend.get("answer") == "Unknown":
        lines.append(f"**اتجاه الفرص:** غير متاح — {trend['reason']}")
    else:
        lines.append(
            f"**متوسط فجوة الفرصة (الفترة):** {trend['period_avg_opportunity_gap']} "
            f"مقابل المتوسط التاريخي {trend['all_time_avg_opportunity_gap']} "
            f"(عينة الفترة: {trend['period_sample_size']})"
        )
        lines.append(
            f"**متوسط درجة الألم (الفترة):** {trend['period_avg_pain_score']} "
            f"مقابل المتوسط التاريخي {trend['all_time_avg_pain_score']}"
        )

    rej = report["top_rejection_reasons"]
    if rej.get("answer") == "Unknown":
        lines.append(f"**أكثر أسباب الرفض:** غير متاح — {rej['reason']}")
    else:
        lines.append(f"**أكثر أسباب الرفض:** {rej['answer']} (من أصل {rej['total_rejected']} رفض)")

    return "\n\n".join(lines) + "\n"

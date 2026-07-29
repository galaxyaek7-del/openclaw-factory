#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Health Trend Tracking, Python side (Global Trust &
Resilience Layer, Round 1, 2026-07-29).

The real recording happens in `lib/health_trend.js` (factory_loop.js's
own tick already fetches a real `GET /health` status every ~10 minutes
via `diagnose()` -- this just appends it). This module is the exact same
real computation, reimplemented Python-side so `tool_intelligence/
proposals.py` (Python) can read the same real `data/health_snapshots.jsonl`
without a Node runtime -- same "same real computation, Python
reimplementation" precedent `executive_score.py`'s own
`_dual_inspection_pass_rate()` already established for
`self_awareness.js`'s `getDualInspectionPassRate()`. Never a second,
divergent detection algorithm -- kept in lockstep with the JS original.
"""

import json
import os

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SNAPSHOTS_PATH = os.path.join(FACTORY_DIR, 'data', 'health_snapshots.jsonl')

SEVERITY_RANK = {"healthy": 0, "degraded": 1, "critical": 2}


def read_health_snapshots(snapshots_path=None, limit=50):
    path = snapshots_path or DEFAULT_SNAPSHOTS_PATH
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
    return entries[-limit:]


def detect_health_degradation(snapshots_path=None, window_size=3):
    """Two real, narrow signals, never blended into one fabricated
    score: strictly_worsening (each of the last window_size real
    readings is worse than the one before it), sustained_unhealthy
    (every one of the last window_size real readings is not "healthy").
    `degrading` is true if either real signal fires."""
    recent = read_health_snapshots(snapshots_path, limit=window_size)
    if len(recent) < window_size:
        return {
            "degrading": False,
            "reason": f"أقل من {window_size} قراءات صحة حقيقية مسجَّلة بعد لحساب اتجاه موثوق",
            "window": recent,
        }

    statuses = [e.get("status") for e in recent]
    ranks = [SEVERITY_RANK.get(s) for s in statuses]
    if any(r is None for r in ranks):
        return {"degrading": False, "reason": "قراءة واحدة أو أكثر في النافذة الأخيرة غير صالحة", "window": recent}

    strictly_worsening = all(ranks[i] > ranks[i - 1] for i in range(1, len(ranks)))
    sustained_unhealthy = all(r > 0 for r in ranks)

    if strictly_worsening:
        reason = f"{window_size} قراءات صحة حقيقية متتالية تزداد سوءاً: {' -> '.join(statuses)}"
    elif sustained_unhealthy:
        reason = f"{window_size} قراءات صحة حقيقية متتالية غير سليمة (لم تعد healthy): {' -> '.join(statuses)}"
    else:
        reason = "لا اتجاه تدهور حقيقي في آخر القراءات"

    return {"degrading": strictly_worsening or sustained_unhealthy, "reason": reason, "window": recent}

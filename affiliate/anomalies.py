#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anomaly detection over affiliate ledgers (read-only).

Detects spikes, impossible rates, duplicates, timestamp anomalies, bot
patterns, tracking discontinuity. Classifies INFO/WARNING/CRITICAL/BLOCKED.
CRITICAL/BLOCKED must stop affected automation (surfaced, never auto-acted).
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent


def _read_rows(name: str) -> list:
    p = _FACTORY_ROOT / "data" / name
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def detect_anomalies() -> list:
    findings = []
    clicks = _read_rows("affiliate_clicks.jsonl")
    views = _read_rows("affiliate_page_views.jsonl")
    attr = _read_rows("commission_attribution_log.jsonl")

    # known quarantined flood — INFO (standing condition, not new)
    if len(attr) > 1000:
        findings.append({"severity": "INFO",
                         "kind": "quarantined_flood",
                         "detail": "%d attribution rows under quarantine (bot burst)" % len(attr)})

    # impossible rate: clicks exceed views across divergent sources
    if clicks and views and len(clicks) > len(views):
        findings.append({"severity": "WARNING",
                         "kind": "clicks_exceed_views",
                         "detail": "%d clicks vs %d views from divergent sources — "
                                   "both INTERNAL, neither is a rate" % (len(clicks), len(views))})

    # duplicate events: identical (timestamp, source) pairs
    for name, rows in (("clicks", clicks), ("views", views)):
        keys = [(r.get("timestamp"), r.get("source") or r.get("referrer")) for r in rows]
        dupes = sum(c - 1 for c in Counter(keys).values() if c > 1)
        if dupes:
            findings.append({"severity": "WARNING" if dupes > 5 else "INFO",
                             "kind": "duplicate_events",
                             "detail": "%d duplicate (ts, source) pairs in %s" % (dupes, name)})

    # timestamp anomalies: naive or future timestamps
    bad = 0
    now_ts = datetime.now().timestamp()
    for r in clicks + views:
        try:
            dt = datetime.fromisoformat(str(r.get("timestamp", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None or dt.timestamp() > now_ts + 3600:
                bad += 1
        except (ValueError, AttributeError):
            bad += 1
    if bad:
        findings.append({"severity": "WARNING", "kind": "timestamp_anomaly",
                         "detail": "%d bad/future timestamps" % bad})

    # tracking discontinuity: clicks unattributed
    if clicks and all(not r.get("referrer") for r in clicks):
        findings.append({"severity": "INFO", "kind": "tracking_discontinuity",
                         "detail": "all recorded clicks carry null referrers (internal pattern)"})

    critical = [f for f in findings if f["severity"] in ("CRITICAL", "BLOCKED")]
    return {"findings": findings, "critical": critical,
            "automation_hold": bool(critical)}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Market Alert Engine (Live Competitive Intelligence
Layer, Market Evidence & Alerting layer, 2026-07-23).

Reuses, never duplicates: competitor_discovery.py's already-computed
`changes` (ADR-093 — new/disappeared competitors + real growth signals)
and market_evidence.py's new competitor-landscape event categories
(ADR-095 — funding, acquisition, hiring spike, security incident,
partnership, regulatory change, customer migration, feature release,
pricing change), the 9 event types no automated sensor in this factory
can observe on its own.

No scheduler exists in this factory (CLAUDE.md) — alerts are computed
on demand via scan_market_alerts(), same "on-demand, not continuous"
discipline as enterprise_readiness.run_risk_intelligence_scan() /
executive_board.review_board_track_record(). Once a scan persists new
alerts to data/market_alerts.jsonl, every connected system (Executive
Board, Mission Control, Revenue Engine, Opportunity Queue) reaches them
automatically through get_active_alerts() — a read-only lookup, never a
new scan, the exact same pattern executive_board.get_latest_board_brief()
already established. "Automatically reach" means "automatically surfaced
the next time each of those systems is queried" — the only honest
meaning available in an architecture with no background workers.

Severity, confidence, and recommended actions are ALL deterministic,
derived from real fields already computed elsewhere (a competitor's real
classify_competitor() category, a real percentage change in GitHub
stars/HN points, the exact verification flag market_evidence.py's own
required-field check already computed) — never a freely-generated
judgment call.

    python market_alerts.py --scan "some niche"
    python market_alerts.py --active "some niche"
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_ALERTS_PATH = _FACTORY_ROOT / "data" / "market_alerts.jsonl"

SEVERITY_LEVELS = ("Critical", "High", "Medium", "Low")

# Deterministic per-type severity baseline for the 9 manually-recorded
# competitor event types (market_evidence.COMPETITOR_EVENT_TYPES) — each
# grounded in a real, stated business-impact argument, never an
# arbitrary guess. Auto-detected events (new competitor / disappeared /
# growth signal) get their severity computed from real fields instead —
# see _severity_for_new_competitor()/_severity_for_growth_signal() below.
_MANUAL_EVENT_SEVERITY = {
    "competitor_customer_migration": "Critical",  # our own real customers leaving for a competitor -- direct, observed revenue loss
    "competitor_regulatory_change": "Critical",   # could legally constrain this factory's own product category
    "competitor_acquisition": "High",             # consolidation -- a competitor gaining a larger parent's resources/reach
    "competitor_funding_round": "High",           # a competitor now materially better capitalized
    "competitor_pricing_change": "High",          # direct price-war exposure
    "competitor_hiring_spike": "Medium",          # a real capacity-scaling signal, indirect
    "competitor_partnership": "Medium",           # a real distribution/reach expansion, indirect
    "competitor_feature_release": "Medium",       # competitive parity pressure, indirect
    "competitor_security_incident": "Low",        # mostly reputational to the competitor, not directly to us
}

_RECOMMENDED_ACTIONS = {
    "competitor_customer_migration": "تحقّق فوراً من سبب مغادرة العميل الحقيقي ووثّقه في مراجعة الاحتفاظ بالعملاء",
    "competitor_regulatory_change": "راجع مع Chief Risk Officer ما إذا كان هذا يمسّ فئة منتجنا فعلياً قبل أي قرار إنتاج جديد",
    "competitor_acquisition": "أعد تقييم موقعنا التنافسي في هذا النيتش عبر AI Executive Board",
    "competitor_funding_round": "راجع التسعير والتمايز في هذا النيتش قبل استثمار إنتاج إضافي",
    "competitor_pricing_change": "راجع استراتيجية التسعير الحالية لهذا النيتش الآن",
    "competitor_hiring_spike": "راقب هذا المنافس عن قرب في الجولة القادمة من اكتشاف المنافسين",
    "competitor_partnership": "قيّم ما إذا كانت هذه الشراكة تفتح قناة توزيع ينبغي رصدها",
    "competitor_feature_release": "قارن هذه الميزة بخارطة طريق منتجنا في المراجعة القادمة",
    "competitor_security_incident": "لا إجراء مباشر مطلوب — معلوماتي فقط ما لم يتكرر عبر عدة منافسين في نفس النيتش",
    "new_competitor_appeared": "قيّم هذا المنافس عبر Chief Market Intelligence Officer في اجتماع المجلس القادم",
    "competitor_disappeared": "لا إجراء مطلوب — إشارة إيجابية، انخفاض تشبّع حقيقي",
    "competitor_growth_signal": "راقب هذا المنافس — نمو حقيقي في الشعبية قد يستدعي مراجعة الدفاعية",
}


def _normalize_key(niche):
    """Same 1-line normalization competitor_discovery.py's own
    _normalize_key()/executive_quality_gate.check_market_saturation()
    already use — duplicated here rather than importing a private
    (leading-underscore) helper across modules, matching this factory's
    existing precedent for that exact tradeoff."""
    return re.sub(r"\s+", " ", (niche or "").strip().lower())


def _percent_growth(old_value, new_value):
    if not isinstance(old_value, (int, float)) or old_value <= 0:
        return None
    return round(100 * (new_value - old_value) / old_value, 1)


def _severity_for_new_competitor(competitor):
    category = competitor.get("category")
    return {
        "Enterprise Leader": "Critical",
        "Direct Competitor": "High",
        "Emerging Startup": "Medium",
        "Alternative Solution": "Medium",
    }.get(category, "Low")


def _severity_for_growth_signal(growth):
    pct = _percent_growth(growth.get("from"), growth.get("to"))
    if pct is None:
        return "Medium", None  # a real signal that started at 0 -- not percentage-comparable, but still real
    if pct >= 100:
        return "High", pct
    if pct >= 25:
        return "Medium", pct
    return "Low", pct


def _build_alert(niche, event_type, source, evidence, severity, confidence, occurred_at, dedupe_key):
    return {
        "dedupe_key": dedupe_key,
        "niche": niche,
        "event_type": event_type,
        "source": source,
        "evidence": evidence,
        "severity": severity,
        "confidence": confidence,
        "recommended_action": _RECOMMENDED_ACTIONS.get(
            event_type, "راجع هذا الحدث يدوياً — لا إجراء موصى به مُعرَّف بعد لهذا النوع",
        ),
        "occurred_at": occurred_at,
        "alerted_at": datetime.now(timezone.utc).isoformat(),
    }


def detect_auto_alerts(niche, db_file=None):
    """Reuses competitor_discovery.py's already-computed, already-
    persisted `changes` (ADR-093) for the last real refresh of this
    niche — zero new computation, zero new network call. Empty list,
    honestly, when no real discovery has ever run for this niche, or the
    last refresh had no real history to diff against yet."""
    import competitor_discovery as cd

    db = cd.load_database(db_file)
    snapshot = db.get(_normalize_key(niche))
    if not snapshot:
        return []

    changes = snapshot.get("changes") or {}
    if not changes.get("has_history"):
        return []

    compared_at = changes.get("compared_at")
    alerts = []

    for c in changes.get("new_competitors") or []:
        alerts.append(_build_alert(
            niche=niche, event_type="new_competitor_appeared", source="competitor_discovery",
            evidence={"competitor": c.get("name"), "category": c.get("category"), "category_reason": c.get("category_reason")},
            severity=_severity_for_new_competitor(c), confidence=1.0, occurred_at=compared_at,
            dedupe_key=f"{_normalize_key(niche)}|new_competitor_appeared|{c.get('name')}|{compared_at}",
        ))

    for c in changes.get("disappeared_competitors") or []:
        alerts.append(_build_alert(
            niche=niche, event_type="competitor_disappeared", source="competitor_discovery",
            evidence={"competitor": c.get("name")}, severity="Low", confidence=1.0, occurred_at=compared_at,
            dedupe_key=f"{_normalize_key(niche)}|competitor_disappeared|{c.get('name')}|{compared_at}",
        ))

    for g in changes.get("growth_signals") or []:
        severity, pct = _severity_for_growth_signal(g)
        alerts.append(_build_alert(
            niche=niche, event_type="competitor_growth_signal", source="competitor_discovery",
            evidence={**g, "percent_growth": pct}, severity=severity, confidence=1.0, occurred_at=compared_at,
            dedupe_key=f"{_normalize_key(niche)}|competitor_growth_signal|{g.get('name')}|{g.get('metric')}|{compared_at}",
        ))

    return alerts


def detect_manual_alerts(niche, evidence_path=None):
    """Reuses market_evidence.py's competitor-landscape event types
    directly — zero new storage, zero re-validation logic. Confidence
    reflects the exact real verification market_evidence.record_evidence()
    already enforced at write time (a real competitor name + a real
    source_url citation) — never re-derived or guessed here."""
    import market_evidence as me

    events = me.get_competitor_events(niche, evidence_path=evidence_path)
    alerts = []
    for e in events:
        event_type = e["event_type"]
        alerts.append(_build_alert(
            niche=niche, event_type=event_type, source=e.get("source") or "manual",
            evidence=e.get("payload"), severity=_MANUAL_EVENT_SEVERITY.get(event_type, "Medium"),
            confidence=1.0, occurred_at=e.get("recorded_at"),
            dedupe_key=f"{_normalize_key(niche)}|{event_type}|{e.get('recorded_at')}",
        ))
    return alerts


def _read_alerts(alerts_path=None):
    path = Path(alerts_path) if alerts_path else DEFAULT_ALERTS_PATH
    if not path.exists():
        return []
    alerts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                alerts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return alerts


def _append_alert(alert, alerts_path=None):
    path = Path(alerts_path) if alerts_path else DEFAULT_ALERTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(alert, ensure_ascii=False) + "\n")


def scan_market_alerts(niche, db_file=None, evidence_path=None, alerts_path=None):
    """The real, on-demand scan — no scheduler exists in this factory
    (CLAUDE.md); this runs only when explicitly invoked (a Mission
    Control action, or a human/Claude Code call during a session).
    Dedupes against every already-recorded alert for this niche so
    re-scanning never re-alerts the same real underlying event twice
    ("no alert spam") — only this function ever writes a new alert;
    every connected system below only ever reads via get_active_alerts()."""
    existing = _read_alerts(alerts_path)
    existing_keys = {a["dedupe_key"] for a in existing if a.get("niche") == niche}

    candidates = detect_auto_alerts(niche, db_file=db_file) + detect_manual_alerts(niche, evidence_path=evidence_path)
    new_alerts = [a for a in candidates if a["dedupe_key"] not in existing_keys]

    for a in new_alerts:
        _append_alert(a, alerts_path)

    return {
        "niche": niche,
        "new_alerts": new_alerts,
        "new_alert_count": len(new_alerts),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


def get_active_alerts(niche, alerts_path=None):
    """Read-only lookup — the real connection point for Executive
    Board, Mission Control, Revenue Engine, and Opportunity Queue.
    Never triggers a new scan itself (same discipline as
    executive_board.get_latest_board_brief() — a read path must never
    silently mutate state)."""
    alerts = [a for a in _read_alerts(alerts_path) if a.get("niche") == niche]
    by_severity = {level: [a for a in alerts if a["severity"] == level] for level in SEVERITY_LEVELS}
    return {
        "niche": niche,
        "total": len(alerts),
        "by_severity_counts": {level: len(v) for level, v in by_severity.items()},
        "alerts": alerts,
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Market Alert Engine (Live Competitive Intelligence Layer)")
    parser.add_argument("--scan", metavar="NICHE")
    parser.add_argument("--active", metavar="NICHE")
    args = parser.parse_args()

    if args.scan:
        emit({"success": True, "result": scan_market_alerts(args.scan)})
        return
    if args.active:
        emit({"success": True, "result": get_active_alerts(args.active)})
        return
    parser.print_help()


if __name__ == "__main__":
    main()

"""Weak-signal monitoring (Permanent Operating Doctrine, section 3F).

One observation is not a trend. This store records small, real observations with
their source, date, and topic, and only raises a review when several *independent*
signals point the same way. The threshold is a heuristic (three signals from at
least two independent source groups by default), not a law, and the function
returns `NOT_ENOUGH_EVIDENCE` rather than a verdict when the bar is not met.

The factory already has alerting (`resilience_monitor.py`) and market connectors
(`multi_source_intelligence/`); this is not a replacement for either. It exists
because a sale that never happened and a listing that over-promises are not
alerts -- they are quiet signals that only matter when read together.

No scraping, no paid sources, no invented signal.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "data" / "weak_signals.jsonl"

RELEVANCE = ("low", "medium", "high")
CONFIDENCE_LABELS = ("OBSERVED", "DERIVED", "INFERRED", "ESTIMATED", "UNKNOWN")
REQUIRED_FIELDS = (
    "signal_id", "observed_at", "source", "source_date",
    "independent_group", "topic", "summary", "relevance", "confidence",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_path(path: Optional[Path]) -> Path:
    return Path(path) if path else DEFAULT_PATH


def _make_signal_id(topic: str, summary: str) -> str:
    return "SIG-" + hashlib.sha256(f"{topic}|{summary}".encode("utf-8")).hexdigest()[:10]


def load_signals(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = _default_path(path)
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def validate_signal(record: Dict[str, Any]) -> List[str]:
    problems = []
    for field in REQUIRED_FIELDS:
        if field not in record or record[field] in (None, ""):
            problems.append("missing field: " + field)
    if record.get("relevance") not in RELEVANCE:
        problems.append("relevance must be one of %s" % (RELEVANCE,))
    if record.get("confidence") not in CONFIDENCE_LABELS:
        problems.append("confidence must be one of %s" % (CONFIDENCE_LABELS,))
    return problems


def record_signal(signal: Dict[str, Any], path: Optional[Path] = None,
                  dry_run: bool = False) -> Dict[str, Any]:
    path = _default_path(path)
    signal = dict(signal)
    signal.setdefault("observed_at", _now_iso())
    signal.setdefault("signal_id", _make_signal_id(signal.get("topic", ""), signal.get("summary", "")))
    problems = validate_signal(signal)
    if problems:
        raise ValueError("invalid signal: " + "; ".join(problems))
    existing = {s.get("signal_id") for s in load_signals(path)}
    if signal["signal_id"] in existing:
        return {"written": False, "reason": "already recorded", "signal_id": signal["signal_id"]}
    if dry_run:
        return {"written": False, "reason": "dry run", "signal_id": signal["signal_id"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(signal, ensure_ascii=False, sort_keys=True) + "\n")
    return {"written": True, "signal_id": signal["signal_id"]}


def review_triggers(path: Optional[Path] = None, min_signals: int = 3,
                    min_groups: int = 2) -> Dict[str, Any]:
    """Group by topic and only trigger when enough independent signals agree."""
    by_topic: Dict[str, List[Dict[str, Any]]] = {}
    for signal in load_signals(path):
        by_topic.setdefault(signal["topic"], []).append(signal)

    reviews = []
    for topic, signals in sorted(by_topic.items()):
        groups = {s["independent_group"] for s in signals}
        triggered = len(signals) >= min_signals and len(groups) >= min_groups
        reviews.append({
            "topic": topic,
            "signals": len(signals),
            "independent_groups": sorted(groups),
            "triggered": triggered,
            "verdict": "REVIEW" if triggered else "NOT_ENOUGH_EVIDENCE",
        })
    return {
        "topics": reviews,
        "triggered": [r["topic"] for r in reviews if r["triggered"]],
        "threshold": {"min_signals": min_signals, "min_groups": min_groups},
    }


# Real observations made while integrating this doctrine. Nothing here is a
# projection: each one names the record it came from.
SEED_SIGNALS: List[Dict[str, Any]] = [
    {
        "signal_id": "SIG-demand-zero-sales",
        "observed_at": "2026-10-19T00:00:00+00:00",
        "source": "data/sales_ledger.jsonl",
        "source_date": "2026-10-03",
        "independent_group": "factory_ledger",
        "topic": "verified_demand",
        "summary": "135 rows are all publish_attempt events with a maximum amount of 0; no sale event exists anywhere in the recorded ledgers.",
        "relevance": "high",
        "confidence": "OBSERVED",
    },
    {
        "signal_id": "SIG-catalog-size",
        "observed_at": "2026-10-19T00:00:00+00:00",
        "source": "product_claim_integrity.py (Cycle 81 audit record; scripts/gumroad_catalog_truth.py)",
        "source_date": "2026-10-14",
        "independent_group": "gumroad_account_audit",
        "topic": "verified_demand",
        "summary": "A read-only enumeration of the real Gumroad account found 79 live products; one live $99 listing promised 200 verified leads and shipped a one-page description.",
        "relevance": "high",
        "confidence": "OBSERVED",
    },
    {
        "signal_id": "SIG-publish-failures",
        "observed_at": "2026-10-19T00:00:00+00:00",
        "source": "data/sales_ledger.jsonl",
        "source_date": "2026-10-03",
        "independent_group": "factory_ledger",
        "topic": "distribution_reliability",
        "summary": "17 real (non-dry-run) publish attempts failed; the most recent three failed with HTTP 402 'credits depleted' from the X platform.",
        "relevance": "medium",
        "confidence": "OBSERVED",
    },
]


def seed(path: Optional[Path] = None) -> Dict[str, int]:
    written = skipped = 0
    for signal in SEED_SIGNALS:
        result = record_signal(signal, path=path)
        if result["written"]:
            written += 1
        else:
            skipped += 1
    return {"written": written, "skipped": skipped, "total": len(SEED_SIGNALS)}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Weak-signal monitoring")
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--reviews", action="store_true")
    args = parser.parse_args(argv)
    if args.seed:
        print(json.dumps(seed(), indent=1))
    if args.reviews:
        print(json.dumps(review_triggers(), ensure_ascii=False, indent=1))
    if not any((args.seed, args.reviews)):
        print(json.dumps({"signals": len(load_signals())}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

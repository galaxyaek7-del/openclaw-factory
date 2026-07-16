"""
Decision Engine — append-only persistence (ADR-050).

Same discipline as channels/ledger.py: one JSON object per line, append
only. Never overwrites, never rewrites history — a corrupt write can't
destroy prior decisions/outcomes. "Latest decision per niche" views are
computed by reading the full history and taking the last one; the
underlying file is never mutated to produce them.
"""

import json
import re
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DECISIONS_PATH = _FACTORY_ROOT / "data" / "decisions.jsonl"
DEFAULT_OUTCOMES_PATH = _FACTORY_ROOT / "data" / "decision_outcomes.jsonl"


def _normalize_key(niche):
    return re.sub(r"\s+", " ", str(niche or "").strip().lower())


def _append(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_all(path):
    path = Path(path)
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def append_decision(decision, path=None):
    record = decision.to_dict() if hasattr(decision, "to_dict") else decision
    _append(record, path or DEFAULT_DECISIONS_PATH)
    return record


def read_decisions(path=None):
    yield from _read_all(path or DEFAULT_DECISIONS_PATH)


def find_decisions_by_niche(niche, path=None):
    """Every decision ever recorded for this niche, oldest first — the
    guarantee that 'every rejected opportunity must remain searchable'.
    Never filtered by status; a REJECTED decision is exactly as findable
    as an ACCEPTED one."""
    key = _normalize_key(niche)
    return [d for d in read_decisions(path) if _normalize_key(d.get("niche")) == key]


def latest_decision_per_niche(path=None):
    """One entry per niche: the most recently decided_at record. Used for
    ranking/queue views, which reflect current status — full history for
    a niche always remains in the file, reachable via
    find_decisions_by_niche()."""
    latest = {}
    for d in read_decisions(path):
        key = _normalize_key(d.get("niche"))
        if not key:
            continue
        existing = latest.get(key)
        if existing is None or d.get("decided_at", "") >= existing.get("decided_at", ""):
            latest[key] = d
    return latest


def append_outcome(outcome, path=None):
    record = outcome.to_dict() if hasattr(outcome, "to_dict") else outcome
    _append(record, path or DEFAULT_OUTCOMES_PATH)
    return record


def read_outcomes(path=None):
    yield from _read_all(path or DEFAULT_OUTCOMES_PATH)

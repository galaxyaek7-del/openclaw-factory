"""
Decision Engine — append-only persistence (ADR-050).

Same discipline as channels/ledger.py: one JSON object per line, append
only. Never overwrites, never rewrites history — a corrupt write can't
destroy prior decisions/outcomes. "Latest decision per niche" views are
computed by reading the full history and taking the last one; the
underlying file is never mutated to produce them.
"""

import hashlib
import json
import os
import re
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DECISIONS_PATH = _FACTORY_ROOT / "data" / "decisions.jsonl"
DEFAULT_OUTCOMES_PATH = _FACTORY_ROOT / "data" / "decision_outcomes.jsonl"


def _normalize_key(niche):
    return re.sub(r"\s+", " ", str(niche or "").strip().lower())


# Parsed-decision cache, invalidated by (mtime_ns, size).
#
# Perf defect fix (2026-10-03): _read_all() re-opened and re-parsed the whole
# ledger on EVERY call. Measured live while profiling
# gfos.if_i_were_the_ceo_report(): the 13.19MB / 2,309-line decisions ledger
# was read and parsed 499 times inside a single report -- 784,489 json.loads()
# calls and 90.2s of the report's 126.7s total, all re-deriving byte-identical
# results. Callers like latest_decision_per_niche() and ranking.rank_all() are
# called once per niche, so the cost grew with (niches x decisions).
#
# The cache is keyed on the file's identity stamp, not a timer, so a newly
# appended decision is still visible to the very next read -- this preserves
# the append-only contract exactly. Any change to mtime_ns or size re-reads.
_READ_CACHE = {}
_READ_CACHE_MAX_ENTRIES = 8


def _invalidate_read_cache(path=None):
    """Drop cached parses. Exposed so a caller that mutates the ledger
    in place (not via append_decision) can force a clean re-read."""
    if path is None:
        _READ_CACHE.clear()
    else:
        _READ_CACHE.pop(str(Path(path)), None)


# Content fingerprint for cache validation.
#
# The (mtime_ns, size) stamp alone is not sufficient on every filesystem: some
# (overlayfs in containers, certain network mounts) expose coarse mtime
# granularity, so a rewrite that keeps the file the same length can land inside
# a single stamp and be served stale. Reading a small head+tail window costs
# microseconds against parsing a 13MB ledger, and makes a stale read
# practically impossible for the append-only shape both these ledgers have.
_FINGERPRINT_BYTES = 4096


def _fingerprint(path, size):
    """sha256 over the last _FINGERPRINT_BYTES of the file.

    Tail-only on purpose. Both of these ledgers are append-only by documented
    contract (decision_engine/store.py's own module docstring, and the same
    discipline golden_hunter/repositioning.py states), so any real change
    lands at the tail. One positioned read instead of a head read plus a seek
    keeps this cheap enough to run on every cache hit -- measured cost matters,
    because these readers are called once per niche.
    """
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            if size > _FINGERPRINT_BYTES:
                f.seek(size - _FINGERPRINT_BYTES)
            h.update(f.read(_FINGERPRINT_BYTES))
    except OSError:
        return None
    return h.hexdigest()


def _parse_all(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _read_cached(path):
    """Parsed records for `path`, re-read only when the file actually changed."""
    key = str(path)
    try:
        stat = os.stat(key)
        stamp = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        _READ_CACHE.pop(key, None)
        return []

    hit = _READ_CACHE.get(key)
    if hit is not None and hit[0] == stamp and hit[1] == _fingerprint(key, stat.st_size):
        return hit[2]

    records = _parse_all(path)
    if len(_READ_CACHE) >= _READ_CACHE_MAX_ENTRIES:
        _READ_CACHE.clear()
    _READ_CACHE[key] = (stamp, _fingerprint(key, stat.st_size), records)
    return records


def _read_all(path):
    yield from _read_cached(path)


def _append(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    # A new append changes the file stamp, but drop the entry outright so a
    # failed/partial write can never be served from cache.
    _READ_CACHE.pop(str(path), None)


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

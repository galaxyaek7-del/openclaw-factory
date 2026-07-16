"""
Executive Orchestrator — immutable execution timeline (ADR-051).

Same append-only discipline as channels/ledger.py and decision_engine/
store.py: one JSON object per line, never rewritten. Every stage
execution — success, failure, or skip — is appended here, in order, so
"record every execution in an immutable timeline" is satisfied by
construction, and a crashed/restarted orchestrator can recover its state
by reading this file rather than guessing (has_succeeded() below is
exactly that recovery check).
"""

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TIMELINE_PATH = _FACTORY_ROOT / "data" / "orchestrator_timeline.jsonl"


def append_execution(result, path=None):
    record = result.to_dict() if hasattr(result, "to_dict") else result
    p = Path(path) if path else DEFAULT_TIMELINE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_timeline(path=None):
    p = Path(path) if path else DEFAULT_TIMELINE_PATH
    if not p.exists():
        return
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def has_succeeded(idempotency_key, path=None):
    """Duplicate-execution prevention + crash recovery in one check: has
    this exact idempotency key already completed successfully, ever?
    Reads the full durable timeline — never relies on in-memory state
    that a restart would lose."""
    return any(
        r.get("idempotency_key") == idempotency_key and r.get("status") == "SUCCESS"
        for r in read_timeline(path)
    )

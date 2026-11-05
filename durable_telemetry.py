"""
Run-Identity Durable Telemetry (Phase 2C, ADR-245) — append-only, observational.

A single append-only durable ledger of REAL runtime execution events at
data/runtime_telemetry.jsonl, carrying the run_id seeded in Phase 2B so a
recorded event is attributable to the specific sensing->publish run that
produced it.

Hard contract (all binding, Phase 2C):
  * APPEND-ONLY. One JSON object per line, opened in append mode ("a"),
    never truncated, never rewritten. Prior records are never lost or
    modified.
  * OBSERVATIONAL ONLY. This module RECORDS events that have ALREADY
    occurred. It never authorizes anything and never gates anything: its
    return value is a plain bool (did the append land?), and NOTHING —
    neither Gate-1, Gate-2, CircuitBreakerState, nor channels/publish_
    protection — reads this file or this module's return value to decide
    whether to proceed. A telemetry failure cannot create a path around any
    barrier.
  * NO FABRICATION. A record's `status` is only ever the real, resolved
    outcome passed in by the caller. `append_stage_outcome()` never mints
    a SUCCESS on its own; SUCCESS is recorded only when the caller passes a
    genuine SUCCESS status. A stage that did not run, or failed, is recorded
    with exactly that real status/outcome.
  * SAFE ON FAILURE. Any write/validation problem returns False and is
    swallowed — it never raises through the caller and never weakens a
    quality/publishing barrier.
  * run_id INTEGRITY. run_id is carried verbatim when the caller supplies a
    real resolved id; when absent, `None` is recorded in the field (the
    caller decides applicability, not this module) — see coerce in
    orchestrator/run_id.py for the trusted-mint boundary.
  * STDLIB ONLY. json + pathlib. No new dependency.

Record schema (one JSON per line):
  {
    "event": str,             one of the registered EVENT_TYPES below
    "run_id": str | None,     the Phase 2B run identity when applicable
    "at": str,                UTC ISO timestamp of when the event occurred
    "source": str,            which subsystem recorded it
    ...other real fields...   e.g. engine/status for stage outcomes
  }

Why this does not duplicate the orchestrator timeline: the timeline
(orchestrator_timeline.jsonl) is the focused per-stage execution ledger the
orchestrator already recovers from; this file is the cross-subsystem durable
runtime telemetry that also carries the JS-dispatch boundary (factory_loop)
and the resolved run_id — a projection OF the events that already happened,
never a second source of truth that could disagree and gate on itself.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_TELEMETRY_PATH = _FACTORY_ROOT / "data" / "runtime_telemetry.jsonl"

# The only accepted event types. A caller must supply one of these; anything
# else is refused (returns False) — this is the malformed-record guard that
# stops junk/synthetic rows from ever being appended.
EVENT_TYPES = ("stage_outcome", "run_dispatched", "run_completed", "observational_note")


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def append_telemetry(record, path=None):
    """Append ONE telemetry record. Returns True on success, False (never
    raises) on any validate/write failure. Observational only."""
    try:
        if not isinstance(record, dict):
            return False
        event = record.get("event")
        if event not in EVENT_TYPES:
            return False
        if "at" not in record:
            record = dict(record)
            record["at"] = _now_iso()
        # Normalise run_id: accept only a genuine string (else None). A
        # dict/list/etc cannot be a run identity and must never be stored.
        run_id = record.get("run_id")
        record["run_id"] = run_id if isinstance(run_id, str) and run_id else None
        payload = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        p = Path(path) if path else DEFAULT_TELEMETRY_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        # Append-only: "a" never truncates. Every write lands a full line;
        # a short write would produce a partial line, and the read side
        # (read_telemetry) silently skips any line it cannot parse, so a
        # crashed mid-write can never corrupt the rest of the file.
        with open(p, "a", encoding="utf-8") as f:
            f.write(payload)
        return True
    except Exception:
        return False


def append_stage_outcome(result, source="orchestrator", path=None):
    """Record a REAL already-resolved orchestrator stage outcome, tied to its
    run_id. `result` is the ExecutionResult the run already produced. status/
    attempts are copied verbatim from the real result — never synthesized.
    Returns bool."""
    try:
        run_id = getattr(result, "run_id", None)
        status = getattr(result, "status", None)
    except Exception:
        return False
    return append_telemetry(
        {
            "event": "stage_outcome",
            "run_id": run_id,
            "source": source,
            "engine": getattr(result, "engine", None),
            "status": status,
            "attempts": getattr(result, "attempts", None),
            "idempotency_key": getattr(result, "idempotency_key", None),
            "error": getattr(result, "error", None),
        },
        path=path,
    )


def append_run_dispatched(run_id, details=None, source="factory_loop", path=None):
    """Record a REAL run dispatch (the JS spawn boundary). `details` is a dict
    of real dispatch context (niche/ladder/tier) when provided. Observational."""
    details = details if isinstance(details, dict) else {}
    record = {
        "event": "run_dispatched",
        "run_id": run_id,
        "source": source,
        "niche": details.get("niche"),
        "ladder": details.get("ladder"),
        "tier": details.get("tier"),
    }
    return append_telemetry(record, path=path)


def append_run_completed(run_id, result, source="orchestrator", path=None):
    """Record a REAL run completion (the CLI's resolved publishing result),
    tied to its run_id. `result` is the real dict already resolved by the CLI.
    Observational."""
    return append_telemetry(
        {
            "event": "run_completed",
            "run_id": run_id,
            "source": source,
            "success": bool(result.get("success")) if isinstance(result, dict) else None,
            "production_status": result.get("production_status") if isinstance(result, dict) else None,
            "publishing_status": result.get("publishing_status") if isinstance(result, dict) else None,
            "production_id": result.get("production_id") if isinstance(result, dict) else None,
        },
        path=path,
    )


def read_telemetry(path=None, limit=None):
    """Read appended records, silently skipping any unparseable partial line
    (crash-safe). Returns a list of dicts in append order. [path] isolation
    only — this is the read mirror of append_telemetry, never a gate input."""
    p = Path(path) if path else DEFAULT_TELEMETRY_PATH
    records = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    if limit is not None:
        return records[-limit:]
    return records
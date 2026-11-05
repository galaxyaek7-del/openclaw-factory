"""
Run-Identity Carrier (Phase 2B, ADR-245) — additive run_id.

One run = one coordinated sensing -> decision -> production -> publishing ->
learning pass over a single opportunity signal (one ``run_cycle()``
invocation). Every log record written for that run must share a single,
stable identity so distinct run boundaries are never confused with each other.

This module is deliberately the ONLY place run ids are minted/validated, so
"same run -> same run_id" and "unrelated runs never silently share an
identity" are guaranteed by construction, not by scattered call-site
discipline.

Design constraints (Phase 2B, all binding):
  * Additive only. run_cycle(..., run_id=None) reproduces legacy behavior
    exactly when run_id is omitted (None -> a fresh id is minted per run, so
    two runs initiated without an id NEVER share an identity).
  * stdlib only (secrets + datetime + re + uuid). No new dependency.
  * No durable telemetry, no event bus, no daemon, no new ledger — this just
    decorates the existing log records (the orchestrator timeline) with a
    single per-run identity.
"""

import re
import secrets
from datetime import datetime, timezone
from typing import Optional

# A caller-supplied identity must be a non-empty string that looks like a
# genuine identifier token. This is a deliberate conservative gate: a
# malformed/None value is never silently propagated (it would risk two
# unrelated runs sharing a junk identity), it just falls back to minting a
# fresh one for this run.
_VALID_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def new_run_id(now=None) -> str:
    """Mint a fresh, unique run identity. Two calls never return the same
    value (time-based prefix + cryptographic randomness)."""
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%S%f")
    return f"run_{ts}_{secrets.token_hex(4)}"


def coerce_run_id(value) -> Optional[str]:
    """Validate + normalize a caller-supplied run_id. Returns the id as a
    clean string when it is a usable identifier, else None (meaning the
    caller should mint a fresh one — never propagate a junk identity)."""
    if value is None:
        return None
    if isinstance(value, (int, float, bytes)):
        # numbers/b'raw' are not text identifiers; do not guess.
        return None
    if not isinstance(value, str):
        # e.g. a dict/list/uuid object we can't trust as a token.
        return None
    s = value.strip()
    if not s or not _VALID_RUN_ID_RE.match(s):
        return None
    return s


def resolve_run_id(value) -> str:
    """The single entry point every run boundary calls: honor a VALID
    caller-supplied run_id (cross-engine carrier, e.g. JS -> Python), else
    mint a fresh per-run id. Never returns None."""
    coerced = coerce_run_id(value)
    if coerced is not None:
        return coerced
    return new_run_id()
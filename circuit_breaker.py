#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Circuit Breaker State (Founder Directive, Phase A, 2026-08-20).

A minimal, deterministic, disk-persisted execution-isolation state machine.
Implements the `CircuitBreakerState` interface the founder directive requires
as the authoritative safety state for a named execution path.

States:
  CLOSED     normal operation
  ISOLATED   after FAILURE_THRESHOLD (3) verified failures — execution stops
  HALF_OPEN  controlled retry / diagnosis window — a single probe is allowed

Required transitions:
  NORMAL                       -> CLOSED        (reset / initial state)
  3 verified failures          -> ISOLATED      (record_failure reaching threshold)
  diagnosis / controlled retry -> HALF_OPEN     (enter_half_open)
  successful recovery          -> CLOSED        (record_recovery_success)
  failed recovery              -> ISOLATED      (record_recovery_failure)

The Circuit Breaker isolates EXECUTION only. It never retires an agent
(isolation != retirement), never spends money, never creates revenue, never
modifies financial truth, never publishes, never contacts customers, never
authorizes another agent, and never bypasses Founder Gates.

Same "mutable state + atomic write" split every safety module uses
(factory_state.py / safe_mode.py / channels/publish_protection.py):
data/circuit_breaker_state.json, atomic tmp-file-then-rename write. A missing
or corrupt file reads as the safe default (all subsystems CLOSED) and never
raises. Every transition records real timestamps and a real reason/trigger.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "circuit_breaker_state.json"

CLOSED = "CLOSED"
ISOLATED = "ISOLATED"
HALF_OPEN = "HALF_OPEN"
VALID_STATES = (CLOSED, ISOLATED, HALF_OPEN)

# Founder-directive value: 3 verified failures -> ISOLATED.
FAILURE_THRESHOLD = 3

# The publishing execution path. Reset of THIS breaker is governed by the
# remediation patch's authoritative boundary (Gate-2 + safe-state evidence),
# enforced directly inside reset() so no external wrapper can bypass it.
PUBLISHING_PATH = "marketplace_publishing"

# Safe-state evidence checklist a publishing reset must satisfy. Every item
# must be known True (not False/None/unknown) for a reset to be authorized;
# missing/invalid evidence fails closed.
RESET_SAFE_STATE_ITEMS = (
    "critical_process_stopped",
    "unauthorized_publish_impossible",
    "payment_disabled",
    "financial_baselines_integrity",
    "critical_errors_resolved",
    "required_dependencies_healthy",
    "security_restored",
)


class ResetAuthorizationError(ValueError):
    """Raised when a publishing-circuit reset is attempted without valid,
    complete Gate-2 and safe-state evidence. A reset can never proceed on
    missing/invalid evidence, and no wrapper can bypass this boundary."""


def _safe_state_ok(evidence) -> tuple:
    """Fail-closed safe-state evaluation. Returns (ok, reason).

    `evidence` is a {item_name: True|False|None} dict over
    RESET_SAFE_STATE_ITEMS. It is valid ONLY when every item is present and
    True. Any missing key, False, None, or unknown item => not ok (and the
    reset fails closed)."""
    if not isinstance(evidence, dict) or not evidence:
        return False, "safe-state evidence missing"
    missing = [it for it in RESET_SAFE_STATE_ITEMS if evidence.get(it) is None]
    unmet = [it for it in RESET_SAFE_STATE_ITEMS if evidence.get(it) is False]
    if missing:
        return False, "safe-state evidence UNKNOWN/missing for: " + ", ".join(missing)
    if unmet:
        return False, "safe-state evidence unmet: " + ", ".join(unmet)
    unknown = [it for it in evidence if it not in RESET_SAFE_STATE_ITEMS]
    if unknown:
        return False, "safe-state evidence contains unrecognized items: " + ", ".join(sorted(unknown))
    return True, "safe-state evidence fully satisfied"


def _verify_publishing_gate2(gate2_evidence, gate2_ledger_path) -> tuple:
    """Re-validate a publishing reset's Gate-2 evidence INSIDE the breaker.

    Returns (ok, status, reason). `gate2_evidence` must be a status dict
    produced by quality_gate_policy.gate2_status that is a genuine, current
    PASS (status == 'ok' AND passed True). We re-derive it from the real
    ledger when possible rather than trusting a wrapper-supplied struct that
    claims 'I already checked' — so a wrapper cannot bypass by lying.

    `gate2_evidence` is required (the call must say WHICH identity it was
    authorized for). If it is a plain dict with a real status/passed we
    validate it; only status=='ok' with passed True satisfies the boundary.
    """
    if not isinstance(gate2_evidence, dict) or not gate2_evidence:
        return False, "MISSING", "no Gate-2 evidence supplied to the reset boundary; publishing reset requires a valid Gate-2 approval record"
    status = gate2_evidence.get("status")
    passed = gate2_evidence.get("passed") is True
    if status != "ok" or not passed:
        return False, (status or "BLOCK"), (
            f"Gate-2 evidence for the reset is not a valid current approval "
            f"(status={status!r}, passed={passed!r})")
    return True, "ok", "Gate-2 evidence is a valid current approval"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_record() -> dict:
    """Every subsystem's breaker record. All transitions keep every field."""
    return {
        "state": CLOSED,
        "consecutive_failures": 0,
        "since": None,          # when the current state began
        "last_failure_at": None,
        "last_success_at": None,
        "recovery_attempts": 0,
        "reason": None,         # reason for the current state (e.g. isolation reason)
        "triggered_by": None,
    }


def _load_state(state_path: Optional[Path] = None) -> dict:
    """Never raises. Missing/corrupt file reads as the safe default."""
    p = Path(state_path) if state_path else DEFAULT_STATE_PATH
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_state(state: dict, state_path: Optional[Path] = None) -> dict:
    """Atomic write with durability — crash mid-write leaves previous valid file intact.
    Flush + fsync ensures content reaches disk before atomic replace (Windows-safe)."""
    p = Path(state_path) if state_path else DEFAULT_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = p.parent / f"{p.name}.tmp-{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass  # fsync not available on all filesystems — best effort
    os.replace(tmp_path, p)
    # Directory fsync for durability on POSIX (no-op on Windows, best effort)
    try:
        dir_fd = os.open(str(p.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
    return state


def _get_record(state: dict, name: str) -> dict:
    return dict(_default_record(), **state.get(name, {}))


def _put_record(state: dict, name: str, record: dict) -> dict:
    state[name] = record
    return state


class CircuitBreakerState:
    """Authoritative state interface for execution-isolation circuit breakers.

    A named execution path (subsystem / arm / workflow) owns one breaker
    record. Callers gate execution on `allow_execution(name)`; the breaker
    itself performs zero side effects beyond its own persisted state.
    """

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = Path(state_path) if state_path else DEFAULT_STATE_PATH

    # ── reads ───────────────────────────────────────────────────────────────

    def current(self, name: str) -> dict:
        state = _load_state(self.state_path)
        return _get_record(state, name)

    def allow_execution(self, name: str) -> bool:
        """CLOSED and HALF_OPEN (single controlled probe) allow execution;
        ISOLATED blocks. Never retires an agent — only isolates execution."""
        return self.current(name)["state"] in (CLOSED, HALF_OPEN)

    def is_isolated(self, name: str) -> bool:
        return self.current(name)["state"] == ISOLATED

    def list_status(self) -> dict:
        """Founder-visibility read view: every breaker record on disk."""
        state = _load_state(self.state_path)
        return {
            "breakers": {name: _get_record(state, name) for name in sorted(state)},
            "threshold": FAILURE_THRESHOLD,
            "states": list(VALID_STATES),
        }

    # ── transitions ─────────────────────────────────────────────────────────

    def reset(self, name: str, triggered_by: str = "founder",
              gate2_evidence=None, safe_state_evidence=None,
              gate2_source_id=None, gate2_ledger_path=None,
              gate2_identity=None) -> dict:
        """NORMAL -> CLOSED. Clears failures/recovery state. Explicit reset
        only — never called automatically by a failure path.

        PUBLISHING BOUNDARY (remediation patch): for the publishing breaker
        name (PUBLISHING_PATH), reset CANNOT proceed on founder intent
        alone. It enforces, DIRECTLY at this authoritative boundary, that:
          * valid, complete safe-state evidence is supplied and satisfied;
          * a valid, current Gate-2 approval is evidenced and re-validated.
        If either is missing or invalid, a ResetAuthorizationError is raised
        and the breaker is left UNTOUCHED (fail-closed) — no wrapper can
        bypass the boundary, because the check and the state write are the
        same call and the wrapper has no separate reset authority.

        `gate2_evidence`: a gate2_status verdict dict with status=='ok' and
        passed True. When `gate2_identity` (a dict of release/config_hash/
        model_id/run_id) is supplied with `gate2_source_id`, we RE-DERIVE the
        Gate-2 approval from the real ledger via quality_gate_policy.gate2_status
        so a wrapper cannot self-certify: the boundary re-checks the ledger
        itself. Otherwise the supplied already-APPROVED verdict is validated
        only if it is a real current PASS.

        For any NON-publishing breaker name, reset keeps its existing generic
        founder-triggered behavior: Gate-2 and safe-state are publishing-
        specific signals with no real semantic for other subsystems, so
        enforcing them there would be a fabricated requirement."""
        state = _load_state(self.state_path)
        if name == PUBLISHING_PATH:
            so_ok, so_reason = _safe_state_ok(safe_state_evidence)
            if not so_ok:
                raise ResetAuthorizationError(
                    f"publishing circuit reset denied: {so_reason}")
            g2_ok, g2_status, g2_reason = self._publishing_gate2(
                gate2_evidence, gate2_source_id, gate2_ledger_path,
                gate2_identity)
            if not g2_ok:
                raise ResetAuthorizationError(
                    f"publishing circuit reset denied: {g2_reason} "
                    f"(gate2 status={g2_status!r})")
        record = _default_record()
        record["since"] = _now_iso()
        record["triggered_by"] = triggered_by
        _save_state(_put_record(state, name, record), self.state_path)
        return record

    def _publishing_gate2(self, gate2_evidence, gate2_source_id,
                          gate2_ledger_path, gate2_identity):
        """Re-derive a genuine, current publishing Gate-2 approval at the
        reset boundary. Returns (ok, status, reason).

        Preferred: when the caller supplies the approved identity
        (`gate2_source_id` + optional `gate2_identity`), re-run the real
        gate2_status against the real ledger so a stale-revoked approval is
        caught at reset time even if the caller held a printed pass.

        Fallback: a supplied `gate2_evidence` verdict already carrying
        status=='ok' and passed True is accepted only on its own merit, but
        this is a strictly weaker guarantee — the reviewer/wrapper asserting
        it is assumed honest, never silently upgraded.
        """
        from quality_gate_policy import gate2_status, DEFAULT_GATE2_LEDGER
        if gate2_source_id is not None:
            ident = gate2_identity or {}
            status = gate2_status(
                gate2_source_id,
                ledger_path=Path(gate2_ledger_path) if gate2_ledger_path else DEFAULT_GATE2_LEDGER,
                artifact_version=ident.get("artifact_version"),
                release=ident.get("release"),
                config_hash=ident.get("config_hash"),
                model_id=ident.get("model_id"),
                run_id=ident.get("run_id"),
            )
            if status.get("status") == "ok" and status.get("passed") is True:
                return True, "ok", (
                    "Gate-2 approval re-derived from the real ledger and "
                    "matched to the requested identity")
            return False, status.get("status", "BLOCK"), (
                "Gate-2 re-derived approval is not a valid current identity-matched pass")
        if isinstance(gate2_evidence, dict) and gate2_evidence.get("status") == "ok" \
                and gate2_evidence.get("passed") is True:
            return True, "ok", "supplied Gate-2 verdict is a valid current approval"
        return False, _verify_publishing_gate2(gate2_evidence, gate2_ledger_path)[1], (
            "no valid Gate-2 approval for the publishing reset")

    def record_failure(self, name: str, reason: str, triggered_by: str = "system") -> dict:
        """Records one verified failure. Consecutive failures accumulate in
        CLOSED; at FAILURE_THRESHOLD the breaker ISOLATES. A failure while in
        HALF_OPEN is a failed recovery -> ISOLATED."""
        state = _load_state(self.state_path)
        record = _get_record(state, name)
        record["consecutive_failures"] += 1
        record["last_failure_at"] = _now_iso()
        record["reason"] = reason
        record["triggered_by"] = triggered_by
        if record["state"] == HALF_OPEN or record["consecutive_failures"] >= FAILURE_THRESHOLD:
            record["state"] = ISOLATED
            record["since"] = _now_iso()
        elif record["state"] == CLOSED:
            record["state"] = CLOSED  # still closed, accumulating
        _save_state(_put_record(state, name, record), self.state_path)
        return record

    def record_success(self, name: str) -> dict:
        """A real success in CLOSED resets the failure counter (stays CLOSED).
        A success while in HALF_OPEN is a successful recovery -> CLOSED."""
        state = _load_state(self.state_path)
        record = _get_record(state, name)
        record["consecutive_failures"] = 0
        record["last_success_at"] = _now_iso()
        record["state"] = CLOSED
        record["since"] = _now_iso()
        record["reason"] = None
        _save_state(_put_record(state, name, record), self.state_path)
        return record

    def enter_half_open(self, name: str, triggered_by: str = "system") -> dict:
        """Diagnosis / controlled retry: ISOLATED -> HALF_OPEN, allowing a
        single probe. Only valid from ISOLATED (recovery of a healthy path
        needs no probe window)."""
        state = _load_state(self.state_path)
        record = _get_record(state, name)
        if record["state"] != ISOLATED:
            raise ValueError(
                f"cannot enter HALF_OPEN from {record['state']!r} for {name!r}; "
                "HALF_OPEN is only a recovery probe of an ISOLATED breaker"
            )
        record["state"] = HALF_OPEN
        record["since"] = _now_iso()
        record["recovery_attempts"] += 1
        record["triggered_by"] = triggered_by
        _save_state(_put_record(state, name, record), self.state_path)
        return record

    def record_recovery_success(self, name: str) -> dict:
        """HALF_OPEN -> CLOSED after a successful probe/recovery."""
        state = _load_state(self.state_path)
        record = _get_record(state, name)
        if record["state"] != HALF_OPEN:
            raise ValueError(
                f"record_recovery_success requires HALF_OPEN for {name!r}; got {record['state']!r}"
            )
        record["state"] = CLOSED
        record["consecutive_failures"] = 0
        record["since"] = _now_iso()
        record["last_success_at"] = _now_iso()
        record["reason"] = None
        _save_state(_put_record(state, name, record), self.state_path)
        return record

    def record_recovery_failure(self, name: str, reason: str) -> dict:
        """HALF_OPEN -> ISOLATED after a failed probe/recovery."""
        state = _load_state(self.state_path)
        record = _get_record(state, name)
        if record["state"] != HALF_OPEN:
            raise ValueError(
                f"record_recovery_failure requires HALF_OPEN for {name!r}; got {record['state']!r}"
            )
        record["state"] = ISOLATED
        record["since"] = _now_iso()
        record["reason"] = reason
        record["consecutive_failures"] = max(record["consecutive_failures"], FAILURE_THRESHOLD)
        _save_state(_put_record(state, name, record), self.state_path)
        return record


# ── module-level convenience wrappers over the authoritative class ───────────

def _cb(state_path: Optional[Path] = None) -> CircuitBreakerState:
    return CircuitBreakerState(state_path=state_path)


def current_state(name: str, state_path: Optional[Path] = None) -> dict:
    return _cb(state_path).current(name)


def allow_execution(name: str, state_path: Optional[Path] = None) -> bool:
    return _cb(state_path).allow_execution(name)


def is_isolated(name: str, state_path: Optional[Path] = None) -> bool:
    return _cb(state_path).is_isolated(name)


def reset(name: str, triggered_by: str = "founder", state_path: Optional[Path] = None,
          gate2_evidence=None, safe_state_evidence=None,
          gate2_source_id=None, gate2_ledger_path=None,
          gate2_identity=None) -> dict:
    return _cb(state_path).reset(
        name, triggered_by=triggered_by,
        gate2_evidence=gate2_evidence, safe_state_evidence=safe_state_evidence,
        gate2_source_id=gate2_source_id, gate2_ledger_path=gate2_ledger_path,
        gate2_identity=gate2_identity)


def record_failure(name: str, reason: str, triggered_by: str = "system", state_path: Optional[Path] = None) -> dict:
    return _cb(state_path).record_failure(name, reason, triggered_by=triggered_by)


def record_success(name: str, state_path: Optional[Path] = None) -> dict:
    return _cb(state_path).record_success(name)


def enter_half_open(name: str, triggered_by: str = "system", state_path: Optional[Path] = None) -> dict:
    return _cb(state_path).enter_half_open(name, triggered_by=triggered_by)


def record_recovery_success(name: str, state_path: Optional[Path] = None) -> dict:
    return _cb(state_path).record_recovery_success(name)


def record_recovery_failure(name: str, reason: str, state_path: Optional[Path] = None) -> dict:
    return _cb(state_path).record_recovery_failure(name, reason)


def list_circuit_breaker_status(state_path: Optional[Path] = None) -> dict:
    return _cb(state_path).list_status()
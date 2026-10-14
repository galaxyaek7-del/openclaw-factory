"""Centralized write-authorization gate for the Gumroad publisher.

WHY THIS EXISTS -- a real, OBSERVED enforcement gap
----------------------------------------------------
`gumroad_auth_watch.py` computes a credential state (VERIFIED /
UNVERIFIED_COMPROMISED / INVALID / UNKNOWN), but nothing in the write path
read it. `grep` over the repository showed gumroad_auth_watch imported only by
ops_snapshot.py, audit_credential_exposure.py and cycle85_verify_affiliate.py
-- never by channels/gumroad_publisher.py. The write functions
create_product / update_product / update_product_file / enable_product
performed NO auth-state check whatsoever.

Several cycles of this factory reported "Gumroad writes are blocked". That was
a convention honoured by convention, not a control. Any caller holding a
credential could write. This module makes the check a real, in-code,
fail-closed precondition inside every mutation function.

FAIL-CLOSED CONTRACT
--------------------
A write is ALLOWED only when every one of these holds. Anything else denies:

  1. FACTORY_LIVE_PUBLISH is explicitly true   (project's existing convention)
  2. an auth state file exists
  3. that state is exactly VERIFIED
  4. it is fresh (not stale beyond STALE_AFTER_SECONDS)
  5. the live credential still matches the fingerprint that state recorded

Denials cover: missing state, INVALID, UNKNOWN, UNVERIFIED_COMPROMISED,
stale, fingerprint drift, and the live-publish flag being off. There is no
"assume ok" branch and no way for this module to mark a credential verified.
It only reads the authoritative state written by gumroad_auth_watch.

MUTATION SURFACE COVERED
------------------------
  create_product        POST /products            (+ S3 multipart via _upload_file)
  update_product        POST /products/{id}
  update_product_file   S3 upload + POST /products/{id}
  enable_product        POST /products/{id}/enable   <- also a mutation, easy to
                                                       forget; it publishes

The gate runs BEFORE any other validation, so a denied write cannot start an
S3 multipart session on Gumroad's side.

Pure: no network, no clock read except via an injectable `now`.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

VERIFIED = "VERIFIED"
DEFAULT_STALE_AFTER_SECONDS = 3600  # 1 hour


class WriteNotAuthorized(RuntimeError):
    """Raised instead of performing a mutation. Fail closed, loudly."""


@dataclass
class WriteAuthDecision:
    allowed: bool
    reason: str
    state: str = "UNKNOWN"
    fingerprint_match: bool = False
    live_publish_flag: bool = False

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "state": self.state,
            "fingerprint_match": self.fingerprint_match,
            "live_publish_flag": self.live_publish_flag,
        }


def _live_publish_requested() -> bool:
    """Reuses the project's existing FACTORY_LIVE_PUBLISH convention."""
    return str(os.environ.get("FACTORY_LIVE_PUBLISH", "")).strip().lower() in (
        "1", "true", "yes", "on")


def check_write_authorization(
    operation: str,
    *,
    state_path: str | None = None,
    now: float | None = None,
    fingerprint_fn=None,
    scope_id: str | None = None,
    product_id: str | None = None,
    payload: dict | None = None,
) -> WriteAuthDecision:
    """
    Central authorization check. Denies by default.

    Cycle 84: the FACTORY_LIVE_PUBLISH requirement is now CONDITIONAL. An
    unscoped operation still needs the global flag, so the factory never
    becomes generally live-capable. A single-use, fully bound authorization
    from channels/write_scope.py can satisfy it for ONE scoped operation
    instead -- which is the founder's explicit engineering preference and
    avoids granting a permanent capability to authorise a one-off edit.

    Scoping narrows WHO may do WHAT. It never relaxes authentication: the
    auth-state checks below run identically on both paths.

    `state_path`, `now` and `fingerprint_fn` remain injectable so every
    denial branch is testable without touching real state or a real
    credential.
    """
    scoped_ok = False
    scope_reason = ""
    if scope_id and product_id and payload is not None:
        from channels.write_scope import consume_scope
        d = consume_scope(scope_id=scope_id, product_id=product_id,
                          payload=payload, operation=operation, now=now)
        scoped_ok = d.allowed
        scope_reason = d.reason

    flag = _live_publish_requested()
    if not flag and not scoped_ok:
        return WriteAuthDecision(
            False,
            "no scoped authorization and FACTORY_LIVE_PUBLISH is not true; "
            "live mutation is disabled"
            + (f" (scope refused: {scope_reason})" if scope_id else ""),
            state="NOT_CHECKED", live_publish_flag=flag)

    if state_path is None:
        state_path = os.environ.get("FACTORY_WRITE_GATE_STATE_PATH") or None

    try:
        import gumroad_auth_watch as auth
    except Exception as exc:  # noqa: BLE001 -- missing module means deny
        return WriteAuthDecision(False,
                                 f"authoritative auth module unavailable "
                                 f"({type(exc).__name__}); denying",
                                 state="UNKNOWN", live_publish_flag=True)

    state = auth.read_state(state_path) or {}
    status = str(state.get("status") or "").strip()
    if not status:
        return WriteAuthDecision(False, "no auth state on record; denying",
                                 state="MISSING", live_publish_flag=True)
    if status != VERIFIED:
        return WriteAuthDecision(False,
                                 f"auth state is {status}, not {VERIFIED}; denying",
                                 state=status, live_publish_flag=True)

    stamp = state.get("at")
    if not stamp:
        return WriteAuthDecision(False, "auth state carries no timestamp; denying",
                                 state="STALE", live_publish_flag=True)
    try:
        from datetime import datetime, timezone
        at = datetime.fromisoformat(str(stamp))
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        age = (time.time() if now is None else now) - at.timestamp()
    except Exception:  # noqa: BLE001
        return WriteAuthDecision(False, "auth state timestamp unparseable; denying",
                                 state="STALE", live_publish_flag=True)
    if age > DEFAULT_STALE_AFTER_SECONDS:
        return WriteAuthDecision(
            False, f"auth state is {int(age)}s old (> {DEFAULT_STALE_AFTER_SECONDS}s); "
                   f"denying until gumroad_auth_watch.poll() refreshes it",
            state="STALE", live_publish_flag=True)

    fp_fn = fingerprint_fn or auth.credential_fingerprint
    try:
        live_fp = fp_fn()
    except Exception as exc:  # noqa: BLE001
        return WriteAuthDecision(False,
                                 f"could not fingerprint live credential "
                                 f"({type(exc).__name__}); denying",
                                 state="UNKNOWN", live_publish_flag=True)
    if not live_fp:
        return WriteAuthDecision(False, "live credential unreadable; denying",
                                 state="UNKNOWN", live_publish_flag=True)

    recorded = str(state.get("fingerprint_prefix") or "")
    if not recorded:
        return WriteAuthDecision(False, "auth state records no fingerprint; denying",
                                 state="UNKNOWN", live_publish_flag=True)
    if not str(live_fp).startswith(recorded):
        return WriteAuthDecision(
            False, "live credential no longer matches the fingerprint the "
                   "auth state recorded; re-run poll() and re-authorise",
            state=VERIFIED, fingerprint_match=False, live_publish_flag=True)

    return WriteAuthDecision(True, f"authorised: state VERIFIED, fresh, "
                                  f"fingerprint matches ({operation})"
                                  + (f" via scoped authorization" if scoped_ok
                                     else ""),
                             state=VERIFIED, fingerprint_match=True,
                             live_publish_flag=flag)


def require_write_authorization(operation: str, **kw) -> WriteAuthDecision:
    """Gate for use as the first statement of every mutation function."""
    d = check_write_authorization(operation, **kw)
    if not d.allowed:
        raise WriteNotAuthorized(
            f"BLOCKED live Gumroad mutation '{operation}': {d.reason}")
    return d
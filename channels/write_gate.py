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
) -> WriteAuthDecision:
    """
    Central authorization check. Denies by default.

    `state_path`, `now` and `fingerprint_fn` are injectable purely so tests can
    exercise every denial branch without touching the real state file or the
    real credential. Production callers pass none of them.

    When `state_path` is omitted the authoritative location is used, which
    FACTORY_WRITE_GATE_STATE_PATH may redirect. That variable selects WHERE the
    state is read from; it never relaxes what counts as authorised. A test can
    point it at a fixture file, but it cannot use it to invent a VERIFIED
    state the gate would otherwise reject -- the same status, freshness and
    fingerprint rules still apply, unchanged.
    """
    flag = _live_publish_requested()
    if not flag:
        return WriteAuthDecision(
            False, "FACTORY_LIVE_PUBLISH is not set to a true value; "
                   "live mutation is disabled", state="NOT_CHECKED",
            live_publish_flag=False)

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
                                  f"fingerprint matches ({operation})",
                             state=VERIFIED, fingerprint_match=True,
                             live_publish_flag=True)


def require_write_authorization(operation: str, **kw) -> WriteAuthDecision:
    """Gate for use as the first statement of every mutation function."""
    d = check_write_authorization(operation, **kw)
    if not d.allowed:
        raise WriteNotAuthorized(
            f"BLOCKED live Gumroad mutation '{operation}': {d.reason}")
    return d
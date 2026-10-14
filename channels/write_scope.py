"""Galaxy Forge -- single-use, operation-scoped write authorization (Cycle 84).

WHY NOT THE GLOBAL FLAG
-----------------------
The founder's engineering decision is explicit: prefer operation-scoped
authorization over enabling factory-wide live publishing. Phase 3 audit
confirmed the global flag is the ONLY authorization input in write_gate.py
beyond the auth state, and that `FACTORY_LIVE_PUBLISH` lives in .env -- so
using it to authorise one two-number description edit would grant the factory
a permanent live-write capability to accomplish a one-off task.

WHAT THIS IS NOT
----------------
Not a random token, and not a backdoor. A random token is proof of nothing:
anyone holding it could apply it to a different product, a different field,
or entirely different text. The security here does NOT come from the token's
secrecy. It comes from BINDING.

THE BINDING, WHICH IS THE ACTUAL SECURITY
------------------------------------------
An authorization is valid only when ALL of these match exactly:
  * target product id            (no other product)
  * operation                    (description update only)
  * allowed field set            (description only -- never price, files,
                                  title, or published)
  * SHA-256 of the EXACT payload (so it cannot authorise different text)
  * not expired
  * not already consumed         (single use; replay is refused)

Because the payload is hash-bound, a captured or leaked authorization is
useless for anything other than the one edit it was issued for. The token is
an identifier, not a secret.

IT DOES NOT REPLACE AUTHENTICATION
----------------------------------
Consuming a scope still requires gumroad_auth_watch's state to be exactly
VERIFIED, fresh, and fingerprint-matched. Scoping narrows WHO may do WHAT;
it never grants a weak credential the ability to write.

STORAGE
-------
Authorizations live OUTSIDE the repository. Default is a per-user state
directory; FACTORY_WRITE_SCOPE_DIR may override it. Nothing here is written
into the repo, into .env, or into any report file, and no credential or token
value is ever persisted or logged.

SINGLE USE, ATOMIC
-------------------
Consume is a compare-and-set under an exclusive lock: read, verify, mark
CONSUMED, write. A second attempt to consume the same id -- concurrently or
afterwards -- fails. Creation of an authorization is NOT success of a write:
`consume_scope()` returns a decision, and the caller must still perform and
then independently verify the external write.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

SCOPE_VERSION = 1
DEFAULT_TTL_SECONDS = 900  # 15 minutes: long enough to run, short to expire

# The only field a description-scope authorization may ever touch.
DESCRIPTION_ONLY = ("description",)
ALLOWED_OPERATIONS = ("update_description",)


def scope_dir() -> Path:
    """Where authorizations live. Deliberately OUTSIDE the repository."""
    override = os.environ.get("FACTORY_WRITE_SCOPE_DIR")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "GalaxyForge" / "write_scopes"


_LOCK = threading.Lock()


@dataclass
class WriteScope:
    scope_id: str
    product_id: str
    slug: str
    operation: str
    allowed_fields: tuple[str, ...]
    payload_sha256: str
    created_utc: float
    expires_utc: float
    state: str = "PENDING"          # PENDING | CONSUMED | REVOKED
    consumed_utc: float | None = None
    note: str = ""


@dataclass
class ScopeDecision:
    allowed: bool
    reason: str
    scope_id: str | None = None
    detail: dict = field(default_factory=dict)


def _store_path(scope_id: str) -> Path:
    return scope_dir() / f"{scope_id}.json"


def _payload_digest(payload: dict, fields) -> str:
    """Hash EXACTLY the authorised fields, canonically ordered."""
    subset = {k: payload.get(k) for k in sorted(fields)}
    blob = json.dumps(subset, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def issue_scope(*, product_id: str, slug: str, payload: dict,
                operation: str = "update_description",
                allowed_fields=DESCRIPTION_ONLY,
                ttl_seconds: int = DEFAULT_TTL_SECONDS,
                note: str = "") -> WriteScope:
    """
    Mint a single-use, fully bound authorization.

    Refuses outright anything that is not a description-only operation, so a
    scope for a price or file change cannot be created here by mistake.
    """
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError(f"operation {operation!r} is not scopable")
    extra = [f for f in allowed_fields if f not in DESCRIPTION_ONLY]
    if extra:
        raise ValueError(
            f"fields {extra} are outside the scopeable set {DESCRIPTION_ONLY}; "
            f"price, files, title and published must never be scoped this way")

    scope_id = secrets.token_urlsafe(24)
    now = time.time()
    scope = WriteScope(
        scope_id=scope_id, product_id=product_id, slug=slug,
        operation=operation, allowed_fields=tuple(allowed_fields),
        payload_sha256=_payload_digest(payload, allowed_fields),
        created_utc=now, expires_utc=now + int(ttl_seconds),
        note=note)

    d = scope_dir()
    d.mkdir(parents=True, exist_ok=True)
    _store_path(scope_id).write_text(json.dumps(asdict(scope), indent=2),
                                     encoding="utf-8")
    return scope


def revoke_scope(scope_id: str) -> bool:
    p = _store_path(scope_id)
    if not p.exists():
        return False
    with _LOCK:
        scope = WriteScope(**json.loads(p.read_text(encoding="utf-8")))
        if scope.state == "CONSUMED":
            return False
        scope.state = "REVOKED"
        p.write_text(json.dumps(asdict(scope), indent=2), encoding="utf-8")
    return True


def consume_scope(*, scope_id: str, product_id: str, payload: dict,
                  operation: str = "update_description",
                  now: float | None = None) -> ScopeDecision:
    """
    Verify every binding and atomically consume. Single use.

    Any mismatch is a refusal. There is no partial acceptance and no way to
    consume a scope for a different product, operation or text.
    """
    now = time.time() if now is None else now
    p = _store_path(scope_id) if scope_id else None

    if not scope_id:
        return ScopeDecision(False, "no authorization supplied")
    if p is None or not p.exists():
        return ScopeDecision(False, "authorization not found")

    with _LOCK:
        try:
            scope = WriteScope(**json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            return ScopeDecision(False,
                                 f"authorization unreadable ({type(exc).__name__})")

        if scope.state == "CONSUMED":
            return ScopeDecision(False, "authorization already used",
                                 scope_id, {"state": scope.state})
        if scope.state == "REVOKED":
            return ScopeDecision(False, "authorization was revoked",
                                 scope_id, {"state": scope.state})
        if now > scope.expires_utc:
            return ScopeDecision(False, "authorization expired",
                                 scope_id,
                                 {"expired_by_s": int(now - scope.expires_utc)})
        if scope.product_id != product_id:
            return ScopeDecision(False,
                                 f"authorization is bound to a different product "
                                 f"({scope.slug})", scope_id,
                                 {"bound_product": scope.product_id,
                                  "requested_product": product_id})
        if scope.operation != operation:
            return ScopeDecision(False,
                                 f"authorization is bound to {scope.operation!r}, "
                                 f"not {operation!r}", scope_id)

        touched = set(payload) - {"product_id"}
        illegal = sorted(touched - set(scope.allowed_fields))
        if illegal:
            return ScopeDecision(False,
                                 f"payload touches fields outside the "
                                 f"authorization: {illegal}", scope_id,
                                 {"illegal_fields": illegal})

        actual = _payload_digest(payload, scope.allowed_fields)
        if actual != scope.payload_sha256:
            return ScopeDecision(False,
                                 "payload does not match the authorized text; "
                                 "refusing", scope_id,
                                 {"authorized_sha256": scope.payload_sha256,
                                  "actual_sha256": actual})

        scope.state = "CONSUMED"
        scope.consumed_utc = now
        p.write_text(json.dumps(asdict(scope), indent=2), encoding="utf-8")

    return ScopeDecision(
        True, f"authorization consumed for {scope.slug} "
              f"({scope.operation}, fields {list(scope.allowed_fields)})",
        scope_id, {"payload_sha256": scope.payload_sha256})


def describe_scope(scope_id: str) -> dict | None:
    """Read-only inspection for reporting. Never logs a credential."""
    p = _store_path(scope_id) if scope_id else None
    if not p or not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return {k: d.get(k) for k in
            ("scope_id", "slug", "operation", "allowed_fields", "state",
             "created_utc", "expires_utc", "consumed_utc", "payload_sha256")}
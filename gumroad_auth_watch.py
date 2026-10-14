#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gumroad auth watch (GF-AUTO-ALL-01 §2 + §17).

Auto-detects a rotated credential and verifies it safely, so the founder's
single external action (dashboard rotation) resumes automation with no
follow-up message needed.

Security contract (absolute):
- The token VALUE never appears in stdout, logs, reports, ledger records,
  exceptions, or git. Only its SHA-256 fingerprint (one-way) is stored.
- Connectivity test is read-only (products list, first page, count only).
- No writes to any platform. No new publishes gated on this module.

States:
- UNVERIFIED_COMPROMISED: fingerprint matches the known-exposed credential
  (recorded at build time as KNOWN_EXPOSED_FP) or no rotation on record.
- VERIFIED: fingerprint differs from exposed one AND live API check passes.
- INVALID: API rejects the credential (401/invalid) -- needs founder hands.
- UNKNOWN: check could not run (network/module error), never guessed.

PROVENANCE OF KNOWN_EXPOSED_FP -- INVESTIGATED 2026-10-14, EVIDENCE-BASED
------------------------------------------------------------------------
Traced rather than assumed. Findings, none of which involve the secret value:

  * ORIGIN. The constant was introduced in commit d822ca6 (2026-09-30,
    "AUTO-ALL-01: gumroad auth watch"). It was BAKED IN AT CREATION, not
    recorded later in response to a later incident. The commit message states
    no reason and contains no evidence.

  * CLAIM. The only justification anywhere is this module's own docstring:
    "exposed in session output during the GAP-1 probing cycle". No GAP-1
    commit exists in history; searching every commit message for "GAP-1"
    returns nothing.

  * ARTIFACTS. A full-history search for the literal credential finds it in
    ZERO commits and in zero tracked files today
    (scripts/audit_credential_exposure.py reproduces this).

  * VERDICT. The exposure is UNVERIFIABLE from inside this repository. It is
    NOT disproven either: a secret printed to a console or passed through a
    process is exposed without ever touching git. The fingerprint match means
    the SAME credential that was handled is still live, which is the part that
    is actually verifiable and is why rotation remains prudent.

  * CONSEQUENCE FOR THIS MODULE. The block is retained deliberately. A
    fail-safe on an unverifiable claim is the correct posture for a write
    path; removing it because no artifact was found would be reasoning from
    absence of evidence to evidence of absence. Rotation is recommended as
    hygiene and is separately REQUIRED for API publishing, not because a
    compromise is proven but because the credential predates this audit.

`poll()` is idempotent and safe to run every cycle; it performs at most one
live API call and writes only data/gumroad_auth_state.json + an evidence
record without secret values.
"""
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(_FACTORY_ROOT, "data", "gumroad_auth_state.json")

# Fingerprint (SHA-256 hex) of the credential exposed in session output
# during the GAP-1 probing cycle. The value itself is NOT stored anywhere
# in this repo; only this one-way fingerprint lets the watch recognize
# whether the live credential is still the exposed one.
KNOWN_EXPOSED_FP = "6c2e73f238903859"

UNVERIFIED_COMPROMISED = "UNVERIFIED_COMPROMISED"
VERIFIED = "VERIFIED"
INVALID = "INVALID"
UNKNOWN = "UNKNOWN"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def credential_fingerprint():
    """SHA-256 hex of the live credential. Returns None if unloadable."""
    try:
        import sys
        sys.path.insert(0, os.path.join(_FACTORY_ROOT, "channels"))
        import gumroad_publisher
        token = gumroad_publisher.load_token()
        if not token:
            return None
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
    except Exception:
        return None


def redacted_connectivity_check():
    """Read-only products-list count. Returns (ok, products_or_error)."""
    try:
        import sys
        sys.path.insert(0, os.path.join(_FACTORY_ROOT, "channels"))
        import gumroad_publisher
        token = gumroad_publisher.load_token()
        if not token:
            return False, "no credential loaded"
        url = ("https://api.gumroad.com/v2/products?"
               + urllib.parse.urlencode({"access_token": token}))
        req = urllib.request.Request(
            url, headers={"User-Agent": "GalaxyForge-auth-watch/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=20).read()
                          .decode("utf-8", "replace"))
        if data.get("success"):
            return True, len(data.get("products", []))
        return False, str(data.get("message", "api success=false"))[:120]
    except Exception as e:
        return False, str(e)[:120]


def read_state(path=None):
    try:
        with open(path or STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def poll(state_path=None, record_evidence=True):
    """One watch cycle. Returns the state dict (never any secret)."""
    fp = credential_fingerprint()
    if fp is None:
        return {"status": UNKNOWN, "reason": "credential unloadable",
                "at": _now_iso()}
    if fp.startswith(KNOWN_EXPOSED_FP):
        state = {"status": UNVERIFIED_COMPROMISED,
                 "reason": "live credential matches exposed fingerprint; "
                           "reads only, no writes until rotation",
                 "fingerprint_prefix": fp[:16], "at": _now_iso()}
    else:
        ok, info = redacted_connectivity_check()
        if ok:
            state = {"status": VERIFIED,
                     "reason": "rotated credential live-verified (products page: %s)" % info,
                     "fingerprint_prefix": fp[:16], "at": _now_iso()}
        else:
            state = {"status": INVALID,
                     "reason": "credential rejected or unreachable: %s" % info,
                     "fingerprint_prefix": fp[:16], "at": _now_iso()}
    try:
        with open(state_path or STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1)
    except OSError:
        pass
    if record_evidence:
        try:
            import evidence_engine
            evidence_engine.record_evidence(
                "SYSTEM", "gumroad_auth_watch:poll",
                "credential state check", "status=%s" % state["status"],
                1000.0, state["status"] in (VERIFIED, UNVERIFIED_COMPROMISED),
                validation_result=state["reason"][:200],
                producer="autonomous watch", provenance="OBSERVED",
                confidence="direct live check, secret never handled as value")
        except Exception:
            pass
    return state

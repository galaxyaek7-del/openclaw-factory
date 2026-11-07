#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Founder STANDING authorization for Gate 2 (the per-product human sign-off).

Gate 2 in quality_gate_policy.py is a real, persisted founder sign-off per product. On
2026-11-05 the founder ordered the factory to run production, review, upload and publication
with no human step, and chose "option 1": a standing authorization. A fake per-product
"approved_by: founder" row would be a fabrication, so this module records what actually happened
instead: ONE durable, quoted, bounded, revocable founder authorization that covers a CLASS of
products, and says so in every verdict ("standing:<id>").

A product is covered only when ALL of these hold (otherwise Gate 2 stays MISSING and blocks):
  - the authorization is ACTIVE, granted_by "founder", carries a verbatim reference, is inside
    valid_from..expires_at and is not revoked;
  - the platform is in scope, the product type is in scope and the price is known and <= max_price_usd;
  - the demand gate (demand_gate.py) is open: no recorded demand, no automatic publication.

It never overrides an explicit founder decision: quality_gate_policy calls this ONLY when Gate 2 is
MISSING (no sign-off at all). A recorded BLOCK / REJECT / REVOKED / STALE / MISMATCH keeps blocking.
Gate 1 (the real QA toolchain) and the circuit breaker still decide on top.

Kill switch: set "status": "REVOKED" in data/standing_authorization.json, or delete the file, or
remove GF_STANDING_AUTH from .env. Nothing else needs to change.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "data" / "standing_authorization.json"
ENV_SWITCH = "GF_STANDING_AUTH"


def _parse(ts):
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def load(path=None):
    p = Path(path) if path else DEFAULT_PATH
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = doc.get("authorizations") if isinstance(doc, dict) else None
    return [a for a in (items or []) if isinstance(a, dict)]


def _valid(auth, now):
    if auth.get("status") != "ACTIVE" or auth.get("granted_by") != "founder":
        return "not ACTIVE or not granted by the founder"
    if len(str(auth.get("reference") or "").strip()) < 20:
        return "no verbatim founder reference"
    start, end = _parse(auth.get("valid_from")), _parse(auth.get("expires_at"))
    if not start or not end:
        return "valid_from / expires_at missing or unparseable"
    if not (start <= now <= end):
        return "outside the validity window"
    return None


def covers(product=None, product_type=None, platform="gumroad", *, path=None, now=None,
           demand_fn=None, environ=None):
    """Return {covered, authorization_id, reason}. Fail-closed on every doubt."""
    env = os.environ if environ is None else environ
    if str(env.get(ENV_SWITCH, "")).lower() != "true":
        return {"covered": False, "reason": "standing authorization is not switched on (%s)" % ENV_SWITCH}
    now = now or datetime.now(timezone.utc)
    auths = load(path)
    if not auths:
        return {"covered": False, "reason": "no standing authorization on file"}
    price = getattr(product, "price_usd", None)
    try:
        price = float(price) if price is not None else None
    except (TypeError, ValueError):
        price = None
    why_not = []
    for auth in auths:
        bad = _valid(auth, now)
        if bad:
            why_not.append("%s: %s" % (auth.get("authorization_id"), bad))
            continue
        scope = auth.get("scope") or {}
        if platform not in (scope.get("platforms") or []):
            why_not.append("%s: platform %r not in scope" % (auth.get("authorization_id"), platform))
            continue
        if product_type not in (scope.get("product_types") or []):
            why_not.append("%s: product type %r not in scope" % (auth.get("authorization_id"), product_type))
            continue
        cap = scope.get("max_price_usd")
        if price is None or cap is None or price <= 0 or price > float(cap):
            why_not.append("%s: price %r not within 0..%r" % (auth.get("authorization_id"), price, cap))
            continue
        if scope.get("demand_gate_required") is False:
            # The founder's explicit, quoted order 2026-11-07 removed the demand condition for THIS authorization only.
            return {"covered": True, "authorization_id": auth.get("authorization_id"), "reference": auth.get("reference"),
                    "reason": "inside the founder's standing authorization (demand gate not required by its scope)"}
        try:
            if demand_fn is None:
                import demand_gate
                demand = demand_gate.evaluate(environ=env)
            else:
                demand = demand_fn()
        except Exception as e:  # fail closed
            return {"covered": False, "reason": "demand gate could not be evaluated: %s" % e}
        if not demand.get("open"):
            return {"covered": False, "reason": "demand gate closed: " + str(demand.get("why"))}
        return {"covered": True, "authorization_id": auth.get("authorization_id"),
                "reference": auth.get("reference"), "reason": "inside the founder's standing authorization"}
    return {"covered": False, "reason": "; ".join(why_not) or "no matching authorization"}

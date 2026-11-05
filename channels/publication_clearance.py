#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publication clearance for creating a paid listing (backlog B4, 2026-11-05).

The write gate (channels/write_gate.py) answers WHO may write: live switch or
a scoped authorization, a fresh VERIFIED auth state, a matching credential.
It does not answer WHETHER this product was cleared for sale. Before this
module, only scripts/publish_batch14.py checked a per-product founder
approval; any other caller of gumroad_publisher.create_product() (the
affiliate publish queue, cohort and sprint scripts, the distribution adapter,
the arm when the distributor's opt-in Quality Gate was not configured) could
create a paid listing with no approval and no gate evidence whenever the live
switch was on.

create_product() now calls require_clearance() right after the write gate and
before any upload. Exactly two kinds of clearance are accepted:

  founder_approval  the per-product approval record from
                    data/publication_approvals.json, validated by
                    channels.publication_authorization (id, price, currency,
                    actions, expiry, revision over the real file bytes), and
                    the listing spec must match that approved product: title,
                    price, description and the bundle's sha256.

  quality_gate      a central Quality Gate decision
                    (quality_gate_policy.quality_gate_allowed) with
                    allowed=True and both Gate 1 and Gate 2 passed.

Anything else (no clearance, an unknown kind, a failed check) raises
PublicationNotCleared. There is no override argument.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_APPROVALS = ROOT / "data" / "publication_approvals.json"


class PublicationNotCleared(Exception):
    """Raised when a listing creation carries no valid publication clearance."""


def _sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _founder_approval(clearance: dict, spec: dict) -> dict:
    from channels import publication_authorization as pa

    product = clearance.get("product")
    if not isinstance(product, dict):
        raise PublicationNotCleared("founder_approval clearance carries no product manifest")
    root = clearance.get("root") or ROOT
    try:
        approvals = clearance.get("approvals")
        if approvals is None:
            approvals = pa.load_approvals(clearance.get("approvals_path") or DEFAULT_APPROVALS)
        record = pa.require_approval(approvals, product, root=root, now=clearance.get("now"),
                                     max_age_seconds=clearance.get("max_age_seconds"))
    except pa.AuthorizationError as exc:
        raise PublicationNotCleared(f"founder approval not valid: {exc}") from exc

    problems = []
    if spec.get("title") != product.get("title"):
        problems.append("title differs from the approved product")
    try:
        if int(spec.get("price_cents")) != product.get("price_cents"):
            problems.append("price differs from the approved product")
    except (TypeError, ValueError):
        problems.append("price is not an integer")
    approved_desc = ((product.get("qa") or {}).get("listing") or {}).get("description_html")
    if spec.get("description", "") != approved_desc:
        problems.append("description differs from the approved listing text")
    try:
        bundle = pa._product_file(product, "bundle", root)
        if bundle is None or _sha256_file(spec.get("file_path")) != _sha256_file(bundle):
            problems.append("file is not the approved bundle")
    except (OSError, TypeError, pa.AuthorizationError) as exc:
        problems.append(f"file could not be compared with the approved bundle ({type(exc).__name__})")
    if problems:
        raise PublicationNotCleared("listing does not match its founder approval: " + "; ".join(problems))
    return {"kind": "founder_approval", "approval_id": record.get("approval_id"),
            "revision_sha256": record.get("revision_sha256")}


def _quality_gate(clearance: dict) -> dict:
    decision = clearance.get("decision")
    if not isinstance(decision, dict):
        raise PublicationNotCleared("quality_gate clearance carries no gate decision")
    if decision.get("allowed") is not True:
        raise PublicationNotCleared(
            f"central Quality Gate did not allow this product "
            f"({decision.get('blocked_by') or decision.get('reason') or 'no reason given'})")
    for name in ("gate1", "gate2"):
        if (decision.get(name) or {}).get("passed") is not True:
            raise PublicationNotCleared(f"central Quality Gate decision does not show {name} passed")
    return {"kind": "quality_gate", "source_id": decision.get("source_id")}


def require_clearance(clearance, spec: dict) -> dict:
    """Return a short record of the clearance, or raise PublicationNotCleared."""
    if clearance is None:
        raise PublicationNotCleared(
            "no publication clearance: creating a paid listing needs the product's founder "
            "approval (scripts/publish_batch14.py) or a central Quality Gate decision (distributor)")
    if not isinstance(clearance, dict):
        raise PublicationNotCleared("publication clearance must be a mapping")
    kind = clearance.get("kind")
    if kind == "founder_approval":
        return _founder_approval(clearance, spec)
    if kind == "quality_gate":
        return _quality_gate(clearance)
    raise PublicationNotCleared(f"unknown publication clearance kind {kind!r}")

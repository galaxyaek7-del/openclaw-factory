#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPSR_PATH_B_V1 market test: V1 listing doc, final QA, hash, rollback,
publish (description-only), independent verification, test record.

Variable discipline: LISTING_COPY_ONLY — name and $79 price untouched.
Token lives in memory only (via channels layer); never printed, logged,
or persisted. Tests import only the pure parts (V1_COPY, qa, hash)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = _FACTORY_ROOT / "data" / "market_test_gpsr_path_b_v1"
PRODUCT_ID = "VPYaNkAdv7Yocko-lIJsZQ=="

V1_COPY = {
    "name": "GPSR EU Seller Action Kit",
    "_note": "name intentionally UNCHANGED (single-variable discipline: description only)",
    "description": (
        "The DIY compliance route for NON-EU sellers (US, UK, elsewhere) offering "
        "consumer products to EU buyers on Etsy, Amazon EU, eBay EU or Shopify.\n\n"
        "WHAT IT COVERS: Responsible Person route (what the role covers, observed rates, "
        "provider selection, per-SKU traps), technical file skeleton + row-by-row risk assessment "
        "method, label and packaging specs, Etsy field-by-field guide, Amazon/eBay/Shopify "
        "enforcement notes, cost-planner workbook, enforcement-response playbook, category "
        "deep-dives, worked 4-week example, marketplace reply skeletons, FAQ.\n\n"
        "YOU RECEIVE: PDF guide + XLSX cost planner (Cost planner / SKU tracker / Listing fields / "
        "Enforcement log). Instant download.\n\n"
        "WHO IT IS FOR: non-EU sellers placing consumer products on the EU market.\n"
        "WHO IT IS NOT FOR: EU-established businesses (you use a different route — this kit's "
        "Responsible Person chapters do not apply to you); cosmetics/electronics/toys sellers needing "
        "lab testing or legal disputes (seek qualified advice).\n\n"
        "WHAT IT DOES NOT DO: this is a practical self-help guide, not legal advice; no attorney-client "
        "relationship; no outcome guaranteed. Buying this kit does not itself make you compliant — "
        "compliance comes from your completed documents, not from this purchase. Figures, fees and "
        "marketplace fields change — verify current wording before acting.\n\n"
        "WHY DIY: consultant document work is quoted ~GBP 150-400/product; this kit builds the same "
        "artifacts yourself over weekends. One month of protected EU revenue dwarfs $79.\n\n"
        "CTA: Buy now — instant download. Work the 5-minute decision tree first; if GPSR does not apply "
        "to you, do not buy."
    ),
    "price": 79,
    "price_note": "unchanged (single-variable discipline)",
}

CHECKS = ("title_present", "path_b_explicit", "deliverables_listed",
          "limitations_present", "disclosure_present", "cta_present",
          "no_legal_guarantee", "no_compliance_by_purchase")


def qa_v1_listing(copy: dict | None = None) -> dict:
    """Final local QA over the V1 doc. All 8 must PASS."""
    c = copy or V1_COPY
    d = (c.get("description") or "")
    low = d.lower()
    results = {
        "title_present": bool((c.get("name") or "").strip()),
        "path_b_explicit": "non-eu" in low and "eu-established" in low,
        "deliverables_listed": "pdf" in low and "xlsx" in low,
        "limitations_present": "not legal advice" in low,
        "disclosure_present": "no outcome guaranteed" in low,
        "cta_present": "buy now" in low,
        "no_legal_guarantee": not any(k in low for k in (
            "guarantee compliance", "guaranteed compliant", "certifies",
            "legally compliant", "compliance guaranteed")),
        "no_compliance_by_purchase": "does not itself make you compliant" in low,
    }
    failed = [k for k, v in results.items() if not v]
    return {"checks": results, "PASS": not failed, "failed": failed,
            "checked_at": datetime.now(timezone.utc).isoformat()}


def v1_hash(copy: dict | None = None) -> str:
    blob = json.dumps(copy or V1_COPY, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def rollback_snapshot(token: str) -> dict:
    """GET live state BEFORE edit; persist as rollback (token never stored)."""
    from channels import gumroad_publisher as gp
    prod = gp.get_product(token, PRODUCT_ID)
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    snap = {"product_id": PRODUCT_ID, "fetched_at": datetime.now(timezone.utc).isoformat(),
            "live": prod}
    (TEST_DIR / "rollback_pre_test.json").write_text(
        json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return snap


def publish_v1(token: str) -> dict:
    """PUT description only (name + price untouched). Returns live state."""
    from channels import gumroad_publisher as gp
    updated = gp.update_product(token, PRODUCT_ID,
                                {"description": V1_COPY["description"]})
    return updated


def verify_publication(token: str, timeout: int = 30) -> dict:
    """Independent verification: API re-read matches V1 hash + public page 200."""
    import urllib.request
    from channels import gumroad_publisher as gp
    prod = gp.get_product(token, PRODUCT_ID)
    live_desc = (prod.get("description") or "")
    desc_match = live_desc.strip() == V1_COPY["description"].strip()
    url = prod.get("short_url") or prod.get("url") or ""
    page_ok, page_status = False, "no url in product data"
    if url:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GalaxyForge-verify/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                page_ok = (r.status == 200)
                page_status = "HTTP %d" % r.status
        except Exception as e:
            page_status = "%s: %s" % (type(e).__name__, str(e)[:120])
    verified = bool(desc_match and page_ok)
    return {"verified": verified, "status": "VERIFIED" if verified else "NOT_VERIFIED",
            "description_match": desc_match, "public_page": page_status, "url": url,
            "checked_at": datetime.now(timezone.utc).isoformat()}

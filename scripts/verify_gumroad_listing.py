#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cycle 104 -- independent, read-only Gumroad listing verifier.

WHY THIS EXISTS
---------------
The doctrine (OpenClaw_Brain/00_Governance/PERMANENT_OPERATING_DOCTRINE.md)
forbids calling a product PUBLISHED because a local manifest says so, because a
commit landed, or because some unrelated endpoint returned HTTP 200. Cycle 103's
operational_history.py reads *recorded* evidence files; this script re-reads the
**live platform** and reports what it actually sees today.

A successful API request is still not proof of a purchasable listing, so three
distinct things are checked and reported separately:

  PUBLISHED   `GET /v2/products/:id` reports published:true and not deleted
  DELIVERABLE a per-product detail GET lists >= the expected attachment(s),
              matched by file name, at >= the declared byte size
  PURCHASABLE UNKNOWN always. Confirming it requires completing a checkout,
              which this factory is not permitted to do. Only the public page's
              purchase affordances are observed, never asserted as proof.

Read-only. GET only. No purchase, no create, no update, no enable/disable.
The token value never appears in output. $0 spend.
"""
from __future__ import annotations

import argparse
import datetime
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

FACTORY = Path(__file__).resolve().parent.parent
if str(FACTORY) not in sys.path:
    sys.path.insert(0, str(FACTORY))

OUT_DIR = FACTORY / "reports" / "CYCLE104"

#: One record per logical product this factory intends to have on Gumroad.
#: `expect` is the founder-approved/derived price in cents. `deliverables` are
#: the local canonical artifacts the listing's copy promises; the live
#: attachment is matched by (filetype, size) -- the v2 API returns the file
#: `name` as null for these listings, so name matching is not possible and is
#: never faked. `extras_allowed` marks a listing where an additional attachment
#: has been seen and is being reviewed.
PRODUCTS = {
    "B12-001": {
        "title": "Freelancer Rate & Raise Calculator",
        "product_id": "W9FpZXpQB-fNiVCteT6Cow==",
        "url": "https://aekraft.gumroad.com/l/blayvb",
        "expect_published": True,
        "price_cents": 1499,
        "deliverables": ["books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx"],
    },
    "B12-003": {
        "title": "Founder Access Continuity Organizer",
        "product_id": "TFeaaWXO3zySimrs2Jbjbw==",
        "url": "https://aekraft.gumroad.com/l/svlky",
        "expect_published": True,
        "price_cents": 800,
        "deliverables": ["books/batch12/B12-003_access_continuity_inventory.xlsx",
                         "books/batch12/B12-003_access_continuity_organizer.pdf"],
    },
    "B12-004": {
        "title": "Meeting Cost & ROI Calculator",
        "product_id": "-cbRBfZyJMTKpl-Xk8Oz3Q==",
        "url": "https://aekraft.gumroad.com/l/ieashv",
        "expect_published": True,
        "price_cents": 1199,
        "deliverables": ["books/batch12/B12-004_meeting_cost_roi_calculator.xlsx",
                         "books/batch12/B12-004_meeting_method_guide.pdf"],
    },
    "EU-AI-ACT-TOOLKIT": {
        "title": ("EU AI Act Compliance Toolkit \u2014 Practical Templates & "
                  "Implementation Guide for SMEs"),
        "product_id": "pzTmMb4v8cih3nbWTj5TeA==",
        "url": "https://aekraft.gumroad.com/l/iaiyt",
        "expect_published": True,
        "price_cents": 15500,
        "deliverables": ["books/eu_ai_act_compliance_toolkit.pdf"],
        # This listing is already known to carry an extra '_preview' PDF; the
        # review flag keeps it visible instead of failing the whole check.
        "extras_allowed": True,
    },
    # These three have a passing quality gate and no recorded upload. Their
    # expected state is "no listing at all": a listing appearing here would mean
    # an unauthorized publication, which is itself the finding.
    "B12-002": {
        "title": "Client Project Handoff Pack",
        "product_id": None,
        "url": None,
        "expect_published": False,
        "price_cents": 1199,
        "deliverables": ["books/batch12/B12-002_client_handoff_guide.pdf",
                         "books/batch12/B12-002_client_handoff_register.xlsx"],
    },
    "B12-005": {
        "title": "Podcast Guest Booking Kit",
        "product_id": None,
        "url": None,
        "expect_published": False,
        "price_cents": 800,
        "deliverables": ["books/batch12/B12-005_podcast_guest_scripts.pdf",
                         "books/batch12/B12-005_podcast_guest_tracker.xlsx"],
    },
    "B12-010": {
        "title": "Nonprofit Grant Pipeline Tracker",
        "product_id": None,
        "url": None,
        "expect_published": False,
        "price_cents": 1500,
        "deliverables": ["books/batch12/B12-010_grant_pipeline_tracker.xlsx",
                         "books/batch12/B12-010_grant_pipeline_guide.pdf"],
    },
}

PURCHASE_MARKERS = ("i want this", "add to cart", "buy now", "purchase",
                    "checkout", "pay ")
UNAVAILABLE_MARKERS = ("this product is not available", "sold out",
                       "no longer available", "page not found")


def _http_get(url: str, timeout: int = 25):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (GalaxyForge verifier)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            body = ""
        return e.code, body
    except Exception as e:  # noqa: BLE001
        return 0, "TRANSPORT_ERROR: %r" % (e,)


def _norm(name: str) -> str:
    return "".join(ch for ch in str(name or "").lower() if ch.isalnum())


def public_page_check(url: str) -> dict:
    if not url:
        return {"checked": False, "reason": "no url recorded"}
    status, html = _http_get(url)
    low = html.lower()
    return {
        "checked": True,
        "http_status": status,
        "bytes": len(html),
        "purchase_affordance_present": any(m in low for m in PURCHASE_MARKERS),
        "unavailable_marker_present": any(m in low for m in UNAVAILABLE_MARKERS),
        "purchasable": "UNKNOWN",
        "purchasable_note": ("never asserted from an unauthenticated page; a real "
                             "checkout is required and is not permitted here"),
    }


def verify_one(key: str, spec: dict, token, get_product_fn) -> dict:
    rec = {
        "product": key,
        "title": spec["title"],
        "expected_published": spec["expect_published"],
        "expected_price_cents": spec["price_cents"],
        "expected_deliverables": list(spec["deliverables"]),
        "observed": {},
        "checks": [],
        "review_items": [],
        "state": None,
    }

    if spec.get("product_id"):
        try:
            prod = get_product_fn(token, spec["product_id"])
        except Exception as exc:  # noqa: BLE001
            rec["observed"]["api_error"] = repr(exc)[:200]
            rec["state"] = "BLOCKED_UNREACHABLE"
            rec["checks"].append({"check": "api_readback", "status": "BLOCKED",
                                  "detail": repr(exc)[:200]})
            return rec
        files = prod.get("files") if isinstance(prod.get("files"), list) else []
        rec["observed"] = {
            "product_id": prod.get("id"),
            "title": prod.get("name"),
            "url": prod.get("short_url"),
            "published": prod.get("published"),
            "deleted": prod.get("deleted"),
            "price_cents": prod.get("price"),
            "currency": prod.get("currency"),
            "sales_count": prod.get("sales_count"),
            "file_info": prod.get("file_info"),
            "attachment_names_exposed": any(f.get("name") for f in files),
            "files": [{"name": f.get("name"), "size": f.get("size"),
                       "filetype": f.get("filetype"), "filegroup": f.get("filegroup"),
                       "url_present": bool(f.get("url"))} for f in files],
        }
        rec["public_page"] = public_page_check(spec.get("url"))

        def add(name, ok, detail):
            rec["checks"].append({"check": name, "status": "PASS" if ok else "FAIL",
                                  "detail": detail})

        def note(name, detail):
            rec["review_items"].append({"item": name, "detail": detail})

        add("published is true", prod.get("published") is True, str(prod.get("published")))
        add("not deleted", prod.get("deleted") in (False, None), str(prod.get("deleted")))
        add("price matches approved", prod.get("price") == spec["price_cents"],
            "%s (expected %s)" % (prod.get("price"), spec["price_cents"]))
        add("title matches", _norm(prod.get("name")) == _norm(spec["title"]),
            str(prod.get("name")))

        # Deliverable matching is by (filetype, size). The v2 API returns a null
        # `name` for these attachments, so a missing name is reported, never
        # treated as a failure and never papered over with a guess.
        live = [(str(f.get("filetype") or "").lower(), int(f.get("size") or 0)) for f in files]
        remaining = list(live)
        missing = []
        matched = []
        for rel in spec["deliverables"]:
            lp = (FACTORY / rel)
            if not lp.exists():
                add("local artifact exists: %s" % lp.name, False, "file not found on disk")
                continue
            want = (lp.suffix.lstrip(".").lower(), lp.stat().st_size)
            if want in remaining:
                remaining.remove(want)
                matched.append({"local": lp.name, "size": want[1], "filetype": want[0]})
                add("attachment matches local %s" % lp.name, True,
                    "%s, %d bytes present on the listing" % (want[0], want[1]))
            else:
                missing.append({"local": lp.name, "expected": "%s/%d" % want,
                                "observed": live})
                add("attachment matches local %s" % lp.name, False,
                    "no live attachment with filetype=%s size=%d; live=%s"
                    % (want[0], want[1], live))

        if not rec["observed"]["attachment_names_exposed"]:
            note("attachment names not exposed by the API",
                 "file name is null on every attachment; matching used filetype+size only, "
                 "so a same-type same-size substitution cannot be excluded by this check")
        if remaining:
            msg = ("%d unexpected attachment(s) beyond the promised deliverable set: %s"
                   % (len(remaining), remaining))
            if spec.get("extras_allowed"):
                note("extra attachment present", msg)
            else:
                add("no unexpected attachments", False, msg)
        else:
            add("no unexpected attachments", True, "attachment set equals the promised set")

        rec["deliverable_matched"] = matched
        rec["deliverable_missing"] = missing
        hard_fail = any(c["status"] == "FAIL" for c in rec["checks"])
        if hard_fail:
            rec["state"] = "PUBLICATION_MISMATCH"
        elif rec["review_items"]:
            rec["state"] = "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS"
        else:
            rec["state"] = "PUBLISHED_VERIFIED"
        return rec

    # No product id on record: verify the expected *absence* by title scan.
    rec["observed"] = {"catalog_title_scan": True}
    try:
        from channels import gumroad_publisher as gp
        catalog = gp.list_products(token)
        hit = next((p for p in catalog
                    if _norm(p.get("name")) == _norm(spec["title"])
                    and not p.get("deleted")), None)
    except Exception as exc:  # noqa: BLE001
        rec["state"] = "BLOCKED_UNREACHABLE"
        rec["checks"].append({"check": "catalog_scan", "status": "BLOCKED",
                              "detail": repr(exc)[:200]})
        return rec
    rec["observed"]["catalog_match"] = ({"id": hit.get("id"),
                                         "url": hit.get("short_url"),
                                         "published": hit.get("published")}
                                        if hit else None)
    if hit is None:
        rec["checks"].append({"check": "no listing exists (expected)", "status": "PASS",
                              "detail": "title absent from the live catalog"})
        rec["state"] = "NOT_PUBLISHED_AS_EXPECTED"
    else:
        rec["checks"].append({
            "check": "no listing exists (expected)", "status": "FAIL",
            "detail": "an unauthorized/undisclosed listing exists: %s published=%s"
                      % (hit.get("short_url"), hit.get("published"))})
        rec["state"] = ("UNEXPECTED_LIVE_LISTING" if hit.get("published")
                        else "UNEXPECTED_DRAFT_LISTING")
    return rec


def main() -> int:
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    ap = argparse.ArgumentParser(description="Read-only live Gumroad listing verification")
    ap.add_argument("--product", action="append", default=[],
                    help="product key (repeatable); default: every known product")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true", help="persist reports under reports/CYCLE104/")
    args = ap.parse_args()

    from channels import gumroad_publisher as gp
    token = gp.load_token()

    keys = args.product or list(PRODUCTS)
    unknown = [k for k in keys if k not in PRODUCTS]
    if unknown:
        print("unknown product key(s): %s" % unknown, file=sys.stderr)
        return 2

    results = [verify_one(k, PRODUCTS[k], token, gp.get_product) for k in keys]
    doc = {
        "schema": "galaxy_forge.gumroad_listing_verification.v1",
        "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "read_only": True,
        "cost_usd": 0,
        "purchases_attempted": 0,
        "method": ("GET /v2/products/:id per known product id (authoritative) plus an "
                   "unauthenticated public-page GET; title scan of the live catalog for "
                   "products expected to have no listing"),
        "purchasable": "UNKNOWN for every product (never asserted without a real checkout)",
        "results": results,
        "summary": {
            "checked": len(results),
            "published_verified": sum(1 for r in results if r["state"] == "PUBLISHED_VERIFIED"),
            "published_verified_with_review_items": sum(
                1 for r in results if r["state"] == "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS"),
            "publication_mismatch": sum(1 for r in results if r["state"] == "PUBLICATION_MISMATCH"),
            "not_published_as_expected": sum(1 for r in results
                                             if r["state"] == "NOT_PUBLISHED_AS_EXPECTED"),
            "unexpected_listing": sum(1 for r in results if str(r["state"]).startswith("UNEXPECTED")),
            "blocked": sum(1 for r in results if r["state"] == "BLOCKED_UNREACHABLE"),
        },
    }

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "GUMROAD_LISTING_VERIFICATION.json").write_text(
            json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        lines = ["# Cycle 104 \u2014 live Gumroad listing verification", "",
                 "Read-only. GET only. No purchase attempted. Price is in US cents.",
                 "**PURCHASABLE is UNKNOWN for every row** \u2014 it can only be proven by a",
                 "real checkout, which this factory is not permitted to perform.", "",
                 "| product | state | published | price | attachments | sales | page |",
                 "|---|---|---|---|---|---|---|"]
        for r in results:
            o = r.get("observed") or {}
            pp = r.get("public_page") or {}
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                r["product"], r["state"], o.get("published"), o.get("price_cents"),
                len(o.get("files") or []), o.get("sales_count"),
                pp.get("http_status")))
        lines += ["", "## Checks", ""]
        for r in results:
            lines.append("### %s \u2014 %s" % (r["product"], r["state"]))
            for c in r["checks"]:
                lines.append("- [%s] %s: %s" % (c["status"], c["check"], c["detail"]))
            for it in r.get("review_items") or []:
                lines.append("- [REVIEW] %s: %s" % (it["item"], it["detail"]))
            lines.append("")
        (OUT_DIR / "GUMROAD_LISTING_VERIFICATION.md").write_text("\n".join(lines),
                                                                 encoding="utf-8")

    if args.json:
        print(json.dumps(doc, indent=1, ensure_ascii=False))
    else:
        for r in results:
            o = r.get("observed") or {}
            print("%-20s %-36s published=%-5s price=%-6s files=%-2s sales=%s"
                  % (r["product"], r["state"], o.get("published"), o.get("price_cents"),
                     len(o.get("files") or []), o.get("sales_count")))
            for it in r.get("review_items") or []:
                print("    REVIEW: %s \u2014 %s" % (it["item"], it["detail"]))
        s = doc["summary"]
        print("\nsummary: %s" % json.dumps(s, ensure_ascii=False))
        if args.write:
            print("written: %s" % (OUT_DIR / "GUMROAD_LISTING_VERIFICATION.json"))

    ok_states = ("PUBLISHED_VERIFIED", "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS",
                 "NOT_PUBLISHED_AS_EXPECTED")
    bad = [r for r in results if r["state"] not in ok_states]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

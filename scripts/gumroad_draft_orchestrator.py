#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guarded B12-001 Gumroad DRAFT orchestrator (Cycle 115, revised Cycle 116).

WHY THIS MODULE EXISTS
----------------------
Cycle 115 asked whether the existing Gumroad integration can safely create an
*unpublished draft*, and answered NO for **our integration**. Cycle 116 research
into the *documented* Gumroad API refined that answer: the **platform documents**
an unpublished-create route, but our wrapper omits it and no live verification
exists. This module encodes both facts as executable code: an honest capability
contract, a fail-closed narrow draft interface, and a read-back verifier.

PLATFORM (documented -- see reports/CYCLE116_GUMROAD_API_CONTRACT.md)
--------------------------------------------------------------------
* `POST /v2/products` accepts `draft=true` / `published=false` to "save as an
  unpublished draft"; default is documented as *published*.
* `PUT /v2/products/:id/enable` publishes; `PUT /v2/products/:id/disable`
  unpublishes; `DELETE /v2/products/:id` deletes.
* `GET /v2/products/:id` returns the authoritative `published` boolean.
* Creation is NOT idempotent; no idempotency key is documented.

OUR INTEGRATION (observed)
--------------------------
1. `channels/gumroad_publisher.create_product()` sends `POST /v2/products`
   WITHOUT any `published`/`draft` field (Cycle 115 payload test pins this).
2. A real live creation returned `published:true` with a publicly rendering page
   (`channels/gumroad_arm.py:8-13`); no delete/archive endpoint is wired.
3. Every mutation is gated by `channels/write_gate.require_write_authorization`,
   which fails closed unless `FACTORY_LIVE_PUBLISH` is true AND a fresh VERIFIED
   auth state exists with a matching fingerprint (or a single-use scope is
   supplied). `channels/write_scope.ALLOWED_OPERATIONS` has **no
   `create_product`** operation.

SAFETY POSTURE
--------------
The default path performs NO network. `create_draft_live()` is the ONLY function
that could ever create a product, and it refuses by default: it requires an
authorization that is blocked today, an explicit `draft_authorized=True`, an
explicit `published=false` payload, and a `GET` read-back proving `published`
is still `false`. Publication is deliberately kept on a separate path. No secret
is ever printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent

TITLE = "Freelancer Rate & Raise Calculator"
PRICE_CENTS = 1499
WORKBOOK = FACTORY_DIR / "books" / "batch12" / "B12-001_freelancer_rate_raise_calculator.xlsx"
WORKBOOK_BYTES = 8922
WORKBOOK_SHA256 = "aee8fc0b100345e7abc6e8a41487ddf551b5b7f235c6f4324827d1c6ab8a092d"
COVER = FACTORY_DIR / "reports" / "B12-001" / "cover.png"
TAGS = ["freelancing", "pricing", "rate calculator", "consultant",
        "spreadsheet", "raise", "excel template", "solo consultant"]
DESCRIPTION = (
    "Stop guessing your rates. This spreadsheet computes YOUR minimum hourly rate from your own costs: "
    "target take-home pay, tax buffer, business expenses, billable weeks and hours, plus a safety margin "
    "for scope creep and late payers.\n\n"
    "Inside (4 sheets): Inputs (your numbers in, computed rate out), ClientMix (rank every client by "
    "revenue-per-hassle and see who to fire first), RaisePlanner (raise only on logged triggers, never on "
    "feelings), README (4-step instructions).\n\n"
    "New product from Galaxy Forge: no sales recorded yet, no reviews. Arithmetic on your inputs -- not "
    "financial advice; confirm tax figures with your accountant.\n\n"
    "Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload). Instant XLSX download after "
    "purchase. Support: reply to your Gumroad receipt email."
)

B12_004_DESCRIPTION = (
    "Your recurring meetings have a price tag \u2014 this workbook calculates it. Give each meeting its "
    "attendee count and a fully-loaded hourly rate, and it returns the weekly and annual cost, the "
    "person-hours, and the one number worth arguing about: cost per decision. Sort by annual cost and "
    "cut from the top.\n\n"
    "Built for the person who suspects the weekly round-robin is expensive and wants the number, not a "
    "productivity tip. Includes a worked example (a 7-person daily standup at $65/hr runs about "
    "$26,160/year \u2014 the same team shortens one biweekly planning meeting and recovers around "
    "$5,200/year), a polite decline script, and a quarterly kill-review process.\n\n"
    "Inside (2 files):\n"
    "- Meeting Cost & ROI Calculator workbook (.xlsx, 5 sheets): Setup (your loaded rate and threshold), "
    "MeetingLog (one row per meeting, with input validation and guarded formulas), Dashboard (annual cost, "
    "cost per decision, zero-decision savings, most expensive meeting), Rules, and a README.\n"
    "- Meeting Cost & ROI Method Guide (.pdf, 4 pages): how to price a meeting honestly (the loaded rate "
    "plus employer surcharge), how to run the quarterly kill review, five mistakes that ruin the number, "
    "and answers to the usual objections.\n\n"
    "New product from Galaxy Forge: no sales recorded yet, no reviews.\n\n"
    "Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload) for the workbook; any PDF "
    "reader for the guide. Instant download after purchase. Support: reply to your Gumroad receipt email."
)

B12_003_DESCRIPTION = (
    "A one-person business has one single point of failure: you. If you are in hospital, offline for a week, "
    "or simply unreachable, the business does not pause \u2014 it fails quietly, because nobody else knows what "
    "it runs on or how to get back in. This is the organizer that fixes that, without ever writing a password "
    "on paper.\n\n"
    "Built for solo founders and one-person businesses. The rule is the same one the best products in this "
    "category use: this is a map, not a vault. It records what exists, where it lives, and who is allowed to "
    "touch it \u2014 and it routes every secret through a password manager's emergency access, so the plan is "
    "useful to a successor without ever being a liability in a drawer.\n\n"
    "Inside (2 files):\n"
    "- Founder Access Continuity Inventory workbook (.xlsx, 6 sheets): Systems (one row per thing the business "
    "runs on \u2014 what it is, where it lives, who can reach it, the recovery route, whether a second person "
    "can get in, criticality 1-5, and when it was last verified), Holders (who may touch what, and the "
    "authority basis for it), Envelopes (the three-envelope custody method pre-filled: the map, the keys via "
    "password-manager emergency access, and a sealed letter), DrillLog (the annual 30-minute drill, with "
    "next-due dates computed), Dashboard (coverage %, critical-gap count, days since the last drill and a "
    "single Continuity readiness verdict), and a README. Includes worked example rows.\n"
    "- Founder Access Continuity Guide (.pdf, 8 pages): the inventory-not-vault rule, what \"unreachable\" "
    "actually means, the three-envelope method, how to name holders inside legal boundaries, the "
    "password-manager emergency-access walk-through, the 30-day keep-alive plan, the annual drill, your "
    "successor's first 72 hours, ten failure modes this plan prevents, boundaries (this is an organizing "
    "system, not a will and not legal advice), an FAQ, and a completion checklist.\n\n"
    "New product from Galaxy Forge: no sales recorded yet, no reviews.\n\n"
    "Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload) for the workbook; any PDF "
    "reader for the guide. Instant download after purchase. Support: reply to your Gumroad receipt email."
)

# ---------------------------------------------------------------------------
# Product profile registry (Cycle 98).
#
# The historical module was hard-coded to a single product (B12-001). This
# registry is the single source of truth for every product's create inputs, so
# the same proven, fail-closed mechanism serves more than one product without a
# second, drifting copy. `DEFAULT_PRODUCT` preserves the original behavior
# exactly: every function's default resolves to B12-001, so existing callers
# (and their tests) are unchanged.
# ---------------------------------------------------------------------------
DEFAULT_PRODUCT = "B12-001"

PROFILES = {
    "B12-001": {
        "id": "B12-001",
        "slug": "b12-001",
        "title": TITLE,
        "price_cents": PRICE_CENTS,
        "files": [str(WORKBOOK)],
        "expected": {str(WORKBOOK): {"bytes": WORKBOOK_BYTES, "sha256": WORKBOOK_SHA256}},
        "cover_local_path": str(COVER),
        "cover_public_url": ("https://raw.githubusercontent.com/galaxyaek7-del/"
                             "openclaw-factory/main/reports/B12-001/cover.png"),
        "tags": list(TAGS),
        "description": DESCRIPTION,
    },
    "B12-004": {
        "id": "B12-004",
        "slug": "b12-004",
        "title": "Meeting Cost & ROI Calculator",
        "price_cents": 1199,
        "files": [
            str(FACTORY_DIR / "books" / "batch12" / "B12-004_meeting_cost_roi_calculator.xlsx"),
            str(FACTORY_DIR / "books" / "batch12" / "B12-004_meeting_method_guide.pdf"),
        ],
        "expected": {
            str(FACTORY_DIR / "books" / "batch12" / "B12-004_meeting_cost_roi_calculator.xlsx"):
                {"bytes": 12865,
                 "sha256": "87ecb1cd223ebf615c46bf49a74c1feb70ea5131a1da9c14dcedff470ccac820"},
            str(FACTORY_DIR / "books" / "batch12" / "B12-004_meeting_method_guide.pdf"):
                {"bytes": 9639,
                 "sha256": "2c964edcfc8a9dcfb45d6bfcde23da85871ec6b3deacc39a10c71cf227972a46"},
        },
        "cover_local_path": str(FACTORY_DIR / "reports" / "B12-004" / "cover.png"),
        "cover_public_url": ("https://raw.githubusercontent.com/galaxyaek7-del/"
                             "openclaw-factory/main/reports/B12-004/cover.png"),
        "tags": ["meetings", "productivity", "management", "calculator",
                 "spreadsheet", "roi", "cost", "team"],
        "description": B12_004_DESCRIPTION,
    },
    "B12-003": {
        "id": "B12-003",
        "slug": "b12-003",
        "title": "Founder Access Continuity Organizer",
        # Cycle 99: price set to USD 8.00, the highest price that clears this
        # factory's own market-realism policy for an 8-page guide
        # (economics.market_realism_check: min($1.00 x 8 pages, $15) = $8.00).
        # The prior recorded $19.00 failed that mandatory gate. See
        # reports/B12-003/GATE_FINAL_2026-10-19.json for the decision record.
        "price_cents": 800,
        "files": [
            str(FACTORY_DIR / "books" / "batch12" / "B12-003_access_continuity_inventory.xlsx"),
            str(FACTORY_DIR / "books" / "batch12" / "B12-003_access_continuity_organizer.pdf"),
        ],
        "expected": {
            str(FACTORY_DIR / "books" / "batch12" / "B12-003_access_continuity_inventory.xlsx"):
                {"bytes": 13594,
                 "sha256": "7cf3e46fa8c2470e1a14c91ff983bf186542fb92f005a0305ff3cacdf9d5edd5"},
            str(FACTORY_DIR / "books" / "batch12" / "B12-003_access_continuity_organizer.pdf"):
                {"bytes": 19095,
                 "sha256": "c9c18a4b0505828a1eabaf6a72a2aba8cc6ef5024c8ebe543e47f971889000fb"},
        },
        "cover_local_path": str(FACTORY_DIR / "reports" / "B12-003" / "cover.png"),
        "cover_public_url": ("https://raw.githubusercontent.com/galaxyaek7-del/"
                             "openclaw-factory/main/reports/B12-003/cover.png"),
        "tags": ["business continuity", "solo founder", "checklist", "spreadsheet",
                 "emergency", "access", "succession", "template"],
        "description": B12_003_DESCRIPTION,
    },
}


def get_profile(product=None) -> dict:
    """Resolve a product profile by id (None -> DEFAULT_PRODUCT). Fails closed."""
    pid = product or DEFAULT_PRODUCT
    profile = PROFILES.get(pid)
    if profile is None:
        raise DraftBlocked(f"unknown product {pid!r}; known: {sorted(PROFILES)}")
    return profile


GUMROAD_API_BASE = "https://api.gumroad.com/v2"
# Pinned, explicit draft flags. Both are sent; neither is ever defaulted.
DRAFT_CREATE_PARAMS = {"published": "false", "draft": "true"}

# ---------------------------------------------------------------------------
# Capability contract (6 named states)
# ---------------------------------------------------------------------------
CAP_SUPPORTED_AND_VERIFIED = "DRAFT_CREATION_SUPPORTED_AND_VERIFIED"
CAP_UNSUPPORTED = "DRAFT_CREATION_UNSUPPORTED"
CAP_CAPABILITY_UNKNOWN = "DRAFT_CREATION_CAPABILITY_UNKNOWN"
CAP_BLOCKED_BY_AUTHORIZATION = "DRAFT_CREATION_BLOCKED_BY_AUTHORIZATION"
CAP_CREATED_BUT_STATE_UNVERIFIED = "DRAFT_CREATED_BUT_STATE_UNVERIFIED"
CAP_CREATED_AND_UNPUBLISHED_STATE_VERIFIED = "DRAFT_CREATED_AND_UNPUBLISHED_STATE_VERIFIED"

#: The documented route exists but has never been exercised against a live
#: account (this cycle forbids a live create). Flip to True only after a real,
#: observed create confirmed an unpublished state.
LIVE_VERIFIED = False

# Retained name; the reason text now reflects the Cycle-116 corrected finding.
NO_SAFE_DRAFT_REASON = (
    "No LIVE-VERIFIED unpublished-create path. The Gumroad API *documents* "
    "POST /v2/products with published=false / draft=true (returns an unpublished "
    "product) plus PUT /:id/disable and DELETE /:id -- so the platform supports "
    "drafts and reversibility. But our integration's create_product() omits the "
    "field, a real live creation defaulted to published:true with a public page "
    "(channels/gumroad_arm.py:8-13), the docs are internally inconsistent about "
    "the default, and creation is non-idempotent. Until a live draft is verified, "
    "this remains an unverified capability and automated creation stays blocked."
)


class DraftBlocked(RuntimeError):
    """Raised instead of performing any unsafe/unsupported draft action."""


def _norm_title(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _live_publish_enabled() -> bool:
    return str(os.environ.get("FACTORY_LIVE_PUBLISH", "")).strip().lower() in ("1", "true", "yes", "on")


def build_spec(product=None, *, cover=None, workbook=None) -> dict:
    """Deterministic create-spec for a product profile (same inputs -> identical).

    `product` defaults to B12-001, so build_spec() is byte-for-byte the original
    single-product spec plus the additive `product`/`files` keys. `workbook`
    retains its historical "override the primary file" meaning for callers that
    pass it positionally or by keyword.
    """
    profile = get_profile(product)
    files = list(profile["files"])
    if workbook is not None:
        files = [str(workbook)] + files[1:]
    primary = files[0]
    expected = (profile.get("expected") or {}).get(primary) or {}
    return {
        "product": profile["id"],
        "title": profile["title"],
        "price_cents": profile["price_cents"],
        "file_path": primary,
        "files": files,
        "expected_sha256": expected.get("sha256"),
        "cover_path": str(cover) if cover is not None else profile["cover_local_path"],
        "tags": list(profile["tags"]),
        "description": profile["description"],
    }


def validate_package(workbook=WORKBOOK, cover=COVER) -> dict:
    """Local-only validation against the canonical B12-001 package. No network."""
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    wb = Path(workbook)
    add("workbook exists", wb.is_file(), str(wb))
    size = wb.stat().st_size if wb.is_file() else None
    add("workbook size", size == WORKBOOK_BYTES, f"{size} (expected {WORKBOOK_BYTES})")
    sha = hashlib.sha256(wb.read_bytes()).hexdigest() if wb.is_file() else None
    add("workbook sha256", sha == WORKBOOK_SHA256, (sha or "")[:16] + "...")
    add("price = $14.99", PRICE_CENTS == 1499, str(PRICE_CENTS))
    add("title", TITLE == "Freelancer Rate & Raise Calculator", TITLE)
    add("tags (8)", TAGS == ["freelancing", "pricing", "rate calculator", "consultant",
                             "spreadsheet", "raise", "excel template", "solo consultant"], str(len(TAGS)))
    add("cover exists", Path(cover).is_file(), str(cover))

    ready = all(c["status"] == "PASS" for c in checks)
    return {"ready": ready, "checks": checks}


def validate_spec(spec) -> dict:
    """Profile-aware, local-only validation of a create-spec. No network.

    Validates every declared file (existence always; size/sha256 when the
    profile pins them), the price, the title, and the cover. Unlike
    `validate_package()` (kept unchanged for its B12-001 contract), this takes
    the spec itself so it serves any product. `file_path` is always validated
    too, even if it is not listed in `files`, so a spec whose primary path was
    tampered with still fails closed.
    """
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    product_id = spec.get("product") or DEFAULT_PRODUCT
    profile = PROFILES.get(product_id) or {}
    expected = profile.get("expected") or {}
    lookup = {}
    for key, val in expected.items():
        lookup[str(key)] = val
        lookup[str(Path(key).resolve())] = val

    paths = []
    for pth in [spec.get("file_path")] + list(spec.get("files") or []):
        if pth and str(pth) not in paths:
            paths.append(str(pth))

    for pth in paths:
        p = Path(pth)
        add(f"file exists: {p.name}", p.is_file(), str(p))
        exp = lookup.get(pth) or lookup.get(str(p.resolve()))
        if exp and p.is_file():
            data = p.read_bytes()
            add(f"file size: {p.name}", len(data) == exp.get("bytes"),
                f"{len(data)} (expected {exp.get('bytes')})")
            if exp.get("sha256"):
                sha = hashlib.sha256(data).hexdigest()
                add(f"file sha256: {p.name}", sha == exp["sha256"], sha[:16] + "...")

    want_price = profile.get("price_cents")
    if want_price is not None:
        try:
            add("price", int(spec.get("price_cents", 0)) == int(want_price),
                f"{spec.get('price_cents')} (expected {want_price})")
        except (TypeError, ValueError):
            add("price", False, repr(spec.get("price_cents")))
    if profile.get("title") is not None:
        add("title", spec.get("title") == profile["title"], str(spec.get("title")))

    cover = spec.get("cover_path")
    add("cover exists", bool(cover) and Path(cover).is_file(), str(cover))

    ready = all(c["status"] == "PASS" for c in checks)
    return {"ready": ready, "checks": checks}


def draft_creation_capability() -> dict:
    """The honest capability contract.

    Returns the pre-operation capability state, the required guarantees, the
    documented reversibility levers, and the known unknowns. Never a fabricated
    green light.
    """
    platform_documented = True
    authorization = "AVAILABLE" if _live_publish_enabled() else "BLOCKED"

    if not platform_documented:
        state = CAP_UNSUPPORTED
    elif not LIVE_VERIFIED:
        state = CAP_CAPABILITY_UNKNOWN
    elif authorization != "AVAILABLE":
        state = CAP_BLOCKED_BY_AUTHORIZATION
    else:
        state = CAP_SUPPORTED_AND_VERIFIED

    blockers = []
    if authorization != "AVAILABLE":
        blockers.append("FACTORY_LIVE_PUBLISH is false")
    if not LIVE_VERIFIED:
        blockers.append("no live-verified unpublished create")

    return {
        "state": state,
        "platform_documented": platform_documented,
        "live_verified": LIVE_VERIFIED,
        "authorization": authorization,
        "required_guarantees": [
            "explicit published=false (and draft=true) in the create payload",
            "create response has product.published == false",
            "GET /v2/products/:id read-back confirms published == false and id/title/price match",
        ],
        "documented_reversibility": ["PUT /v2/products/:id/disable", "DELETE /v2/products/:id"],
        "unknowns": [
            "default create publication state (docs internally inconsistent)",
            "whether published:true implies purchasable",
        ],
        "blockers": blockers,
        "reason": NO_SAFE_DRAFT_REASON,
        "source": "gumroad.com/api + mintlify overview, retrieved 2026-10-18",
    }


def safe_draft_creation_supported() -> tuple:
    """Backward-compatible boolean view of the capability contract.

    True only when the capability is documented AND live-verified AND authorized.
    Today that is False.
    """
    cap = draft_creation_capability()
    supported = cap["state"] == CAP_SUPPORTED_AND_VERIFIED
    return supported, f"{cap['state']}: {cap['reason']}"


def duplicate_scan(spec: dict, list_products_fn) -> dict:
    """READ-ONLY uniqueness check. Fails closed if the catalog cannot be read."""
    if list_products_fn is None:
        raise DraftBlocked("duplicate_scan requires a catalog reader; none supplied")
    try:
        existing = list_products_fn()
    except Exception as exc:  # noqa: BLE001
        raise DraftBlocked(f"cannot verify uniqueness, catalog unreadable: {exc!r}")
    want = _norm_title(spec.get("title"))
    for product in existing or []:
        if isinstance(product, dict) and not product.get("deleted") \
                and _norm_title(product.get("name")) == want:
            return {"found": True, "match": product.get("short_url") or product.get("id")}
    return {"found": False, "match": None}


def _preconditions(spec, list_products_fn):
    """Shared fail-closed precondition checks (no network)."""
    profile = PROFILES.get(spec.get("product") or DEFAULT_PRODUCT) or {}
    want_price = int(profile.get("price_cents", PRICE_CENTS))
    if int(spec.get("price_cents", 0)) != want_price:
        raise DraftBlocked(f"price mismatch: {spec.get('price_cents')} != {want_price}")
    report = validate_spec(spec)
    if not report["ready"]:
        raise DraftBlocked("package not ready: " + ", ".join(
            c["check"] for c in report["checks"] if c["status"] != "PASS"))
    dup = duplicate_scan(spec, list_products_fn)
    if dup["found"]:
        raise DraftBlocked(f"a listing already exists for this title ({dup['match']}); refusing to duplicate")
    return dup


def create_draft(token, spec, *, list_products_fn, create_fn=None, draft_authorized=False, now=None) -> dict:
    """Legacy single entry point that NEVER performs a live create.

    Kept as a permanent guard: even if `create_fn` is supplied and
    `draft_authorized=True`, it refuses, because the capability is not
    live-verified. Use `create_draft_live()` for the narrow, verified interface.
    """
    _preconditions(spec, list_products_fn)

    cap = draft_creation_capability()
    if cap["state"] != CAP_SUPPORTED_AND_VERIFIED:
        # An authorization cannot create a capability that is not live-verified.
        raise DraftBlocked(f"no live-verified draft-creation path: {cap['state']}: {cap['reason']}")

    if create_fn is None:  # unreachable today; kept for a future supported path
        raise DraftBlocked("no create implementation wired")
    if not draft_authorized:
        raise DraftBlocked("create would be a real, irreversible public action; draft_authorized is required")
    return create_fn(token, spec)


def _safe_disable(token, product_id, disable_fn) -> bool:
    """Best-effort revert used only when a create turned out not to be a draft."""
    if disable_fn is None or not product_id:
        return False
    try:
        disable_fn(token, product_id)
        return True
    except Exception:  # noqa: BLE001
        return False


def create_draft_live(token, spec, *, list_products_fn, get_product_fn, post_fn,
                      upload_fn=None, upload_many_fn=None, authorize_fn=None,
                      disable_fn=None, draft_authorized=False) -> dict:
    """The narrow, fail-closed unpublished-draft interface (the documented route).

    Refuses by default. It performs a create ONLY when ALL hold:
      * `authorize_fn("create_product")` succeeds (blocked today: flag off / no
        create_product scope);
      * the local package validates and the price is exactly $14.99;
      * no live listing already carries this title (non-idempotent guard);
      * `draft_authorized=True` is passed explicitly;
      * a `file_url` is supplied or an `upload_fn` produces one.

    It then sends an EXPLICIT `published=false` + `draft=true` payload and
    REQUIRES the response and a `GET` read-back to confirm an unpublished
    product. Any ambiguity -> it attempts a `disable` revert and raises
    `DraftBlocked`. It never calls a publish/enable function.
    """
    if authorize_fn is None:
        from channels import write_gate
        authorize_fn = write_gate.require_write_authorization
    authorize_fn("create_product")  # raises WriteNotAuthorized unless live-authorized

    _preconditions(spec, list_products_fn)

    if not draft_authorized:
        raise DraftBlocked("draft_authorized is required for a live create")

    paths = list(spec.get("files") or ([spec["file_path"]] if spec.get("file_path") else []))
    file_urls = spec.get("file_urls")
    if file_urls:
        file_urls = [str(u) for u in file_urls if u]
    else:
        single = spec.get("file_url")
        if single:
            file_urls = [single]
        elif len(paths) > 1 and upload_many_fn is not None:
            file_urls = [str(u) for u in (upload_many_fn(token, spec, paths) or []) if u]
        else:
            if upload_fn is None:
                raise DraftBlocked("no file_url and no upload implementation; cannot create")
            single = upload_fn(token, spec)
            file_urls = [single] if single else []
            if len(paths) > 1:
                raise DraftBlocked(
                    "spec declares multiple files but no upload_many_fn was supplied; "
                    "refusing a partial (single-file) create")
    if not file_urls or any(not u for u in file_urls):
        raise DraftBlocked("upload produced no file_url; cannot create")

    # A dict overwrites on a repeated key, so a multi-file create is sent as an
    # ordered list of (key, value) pairs -- the form requests encodes into a
    # repeated multipart field, exactly how `files[][url]` already works.
    data = [
        ("access_token", token),
        ("name", spec["title"]),
        ("price", int(spec["price_cents"])),
        ("description", spec.get("description", "")),
        ("customizable_price", "false"),
        ("published", DRAFT_CREATE_PARAMS["published"]),
        ("draft", DRAFT_CREATE_PARAMS["draft"]),
    ]
    for u in file_urls:
        data.append(("files[][url]", u))
    try:
        resp = post_fn(f"{GUMROAD_API_BASE}/products", data)
    except Exception as exc:  # noqa: BLE001
        raise DraftBlocked(
            "UNCERTAIN create result (network error). Do NOT retry blindly; use "
            f"recover_after_uncertain_create() to check for a landed listing. Cause: {exc!r}")

    if not isinstance(resp, dict) or resp.get("success") is not True:
        raise DraftBlocked(f"create failed/ambiguous response: {resp!r}")

    product = resp.get("product")
    if not isinstance(product, dict):
        raise DraftBlocked("create response has no product object")

    pid = product.get("id")
    if "published" not in product:
        reverted = _safe_disable(token, pid, disable_fn)
        raise DraftBlocked(
            f"{CAP_CREATED_BUT_STATE_UNVERIFIED}: create response omitted publication state "
            f"(disable attempted: {reverted})")
    if product.get("published") is not False:
        reverted = _safe_disable(token, pid, disable_fn)
        raise DraftBlocked(
            f"create returned published != false (not a draft); disable attempted: {reverted}")
    if not pid:
        raise DraftBlocked("create response has no product id; cannot verify state")

    fresh = get_product_fn(token, pid)
    if not isinstance(fresh, dict):
        reverted = _safe_disable(token, pid, disable_fn)
        raise DraftBlocked(
            f"{CAP_CREATED_BUT_STATE_UNVERIFIED}: read-back failed (disable attempted: {reverted})")

    problems = []
    if fresh.get("published") is not False:
        problems.append("read-back published != false")
    if str(fresh.get("id")) != str(pid):
        problems.append("id mismatch")
    if _norm_title(fresh.get("name")) != _norm_title(spec["title"]):
        problems.append("title mismatch")
    if int(fresh.get("price", -1)) != int(spec["price_cents"]):
        problems.append("price mismatch")
    if problems:
        reverted = _safe_disable(token, pid, disable_fn)
        raise DraftBlocked(
            f"{CAP_CREATED_BUT_STATE_UNVERIFIED}: " + "; ".join(problems) +
            f" (disable attempted: {reverted})")

    return {"state": CAP_CREATED_AND_UNPUBLISHED_STATE_VERIFIED, "product": fresh}


def recover_after_uncertain_create(spec: dict, *, list_products_fn, draft_authorized=False) -> dict:
    """After an uncertain create, decide whether a listing actually landed.

    Never retries the POST — it only re-scans (non-idempotent create)."""
    if not draft_authorized:
        raise DraftBlocked("draft_authorized is required")
    dup = duplicate_scan(spec, list_products_fn)
    if dup["found"]:
        return {"found": True, "match": dup["match"],
                "advice": "a listing with this title exists; treat it as the create result and do NOT re-POST"}
    return {"found": False, "match": None,
            "advice": "no listing found; a fresh create may be attempted (creation is not idempotent)"}


def preflight(list_products_fn=None) -> dict:
    pkg = validate_package()
    cap = draft_creation_capability()
    out = {
        "product": "B12-001",
        "title": TITLE,
        "price_cents": PRICE_CENTS,
        "package_ready": pkg["ready"],
        "checks": pkg["checks"],
        "safe_draft_creation_supported": cap["state"] == CAP_SUPPORTED_AND_VERIFIED,
        "capability": cap,
        "reason": cap["reason"],
        "spec": build_spec(),
    }
    if list_products_fn is not None:
        out["duplicate_scan"] = duplicate_scan(build_spec(), list_products_fn)
    return out


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="B12-001 Gumroad DRAFT preflight (never publishes)")
    ap.add_argument("--scan", action="store_true",
                    help="READ-ONLY live duplicate scan of the catalog (needs GUMROAD_ACCESS_TOKEN)")
    ap.add_argument("--capability", action="store_true",
                    help="print the draft-creation capability contract and exit")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.capability:
        print(json.dumps(draft_creation_capability(), ensure_ascii=False, indent=1))
        return 0

    reader = None
    if args.scan:
        try:
            if str(FACTORY_DIR) not in sys.path:
                sys.path.insert(0, str(FACTORY_DIR))  # repo root -> importable `channels`
            from channels import gumroad_publisher as gp
            token = gp.load_token()
            reader = lambda: gp.list_products(token)  # noqa: E731
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"scan": "BLOCKED", "reason": repr(exc)}, ensure_ascii=False))
            return 2

    report = preflight(list_products_fn=reader)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        for c in report["checks"]:
            print(f"  {c['status']:<4} {c['check']:<18} {c['detail']}")
        if "duplicate_scan" in report:
            d = report["duplicate_scan"]
            print(f"  duplicate scan: {'FOUND ' + str(d['match']) if d['found'] else 'none (title absent)'}")
        print(f"\nPACKAGE READY: {report['package_ready']}")
        print(f"DRAFT CAPABILITY: {report['capability']['state']}")
        print(f"SAFE DRAFT AUTOMATION: {report['safe_draft_creation_supported']}")
        print("ACTION: no automated draft creation is attempted. Founder manual draft, or a "
              "live-verified capability, is required.")
    return 0 if report["package_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())

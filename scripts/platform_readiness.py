#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Where can a product be sold besides Gumroad, and what is the real path to each? (2026-11-07). Local, read-only.

    python scripts/platform_readiness.py                 # matrix
    python scripts/platform_readiness.py --json
    python scripts/platform_readiness.py --kit B18-007 payhip   # writes drafts/platform_kits/B18-007/payhip.md (git-ignored)

The facts about each platform are the research of 2026-11-07 (docs/factory/PLATFORMS_2026-11-07.md). Every fact carries its evidence class:
OBSERVED = verified in this repository against the live platform; SECONDARY = read in third-party comparison pages and not yet verified on
the platform's own page; UNKNOWN = not established. The matrix never invents an API: where a platform has no product-creation endpoint,
the path is a manual or browser-driven upload by the founder's logged-in session, with a ready listing kit.
Doctrine: zero new spend and no unauthorised publishing: a platform that needs a paid plan is NEEDS_SPEND_APPROVAL, never "ready".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# name -> facts. api_create: YES / NO / UNKNOWN. spend: NONE / PAID / UNKNOWN. cls: the evidence class of the fees/API statements.
PLATFORMS = {
    "gumroad": {"fees": "10% flat, $0/month", "api_create": "YES", "spend": "NONE", "cls": "OBSERVED",
                "account": "exists (aekraft)", "payout": "PayPal outside bank-supported countries (SECONDARY; Algeria not confirmed)",
                "path": "API publish (scripts/publish_batch14.py, per-product founder approval)", "arm": "gumroad"},
    "payhip": {"fees": "5% on the free plan (SECONDARY)", "api_create": "NO", "spend": "NONE", "cls": "OBSERVED",
               "account": "none", "payout": "UNKNOWN for Algeria",
               "path": "manual or browser-driven upload in the founder's logged-in session, from a listing kit; API covers coupons and licence keys only",
               "arm": "payhip"},
    "lemonsqueezy": {"fees": "5% + $0.50 per sale (SECONDARY); owned by Stripe", "api_create": "NO", "spend": "NONE", "cls": "SECONDARY",
                     "account": "none", "payout": "PayPal for most countries, 3% international (SECONDARY; Algeria not confirmed)",
                     "path": "products made in the dashboard (API lists/reads products and creates checkouts); a listing kit for manual entry", "arm": None},
    "shopify": {"fees": "3-day trial, then about $1/month for 3 months, then plan price from about $39/month (SECONDARY)", "api_create": "YES", "spend": "PAID",
                "cls": "SECONDARY", "account": "none (the Shopify connector also needs re-authentication)", "payout": "Shopify Payments availability UNKNOWN for Algeria",
                "path": "Admin GraphQL productCreate as DRAFT (built, dry-run, write-gated); file delivery needs the free Digital Downloads app: NOT IMPLEMENTED",
                "arm": "shopify"},
    "etsy": {"fees": "per-listing fee plus transaction fees (UNKNOWN today; verify)", "api_create": "UNKNOWN", "spend": "PAID", "cls": "UNKNOWN",
             "account": "none", "payout": "UNKNOWN", "path": "skeleton arm exists, never tested live", "arm": "etsy"},
    "kofi": {"fees": "0-5% (SECONDARY)", "api_create": "UNKNOWN", "spend": "NONE", "cls": "SECONDARY", "account": "none", "payout": "UNKNOWN",
             "path": "manual shop item from a listing kit", "arm": None},
    "sellfy": {"fees": "about $22/month, no transaction fee (SECONDARY)", "api_create": "UNKNOWN", "spend": "PAID", "cls": "SECONDARY",
               "account": "none", "payout": "UNKNOWN", "path": "not pursued: monthly fee", "arm": None},
    "paddle": {"fees": "merchant of record; plan terms UNKNOWN", "api_create": "YES", "spend": "UNKNOWN", "cls": "OBSERVED",
               "account": "exists, blocked by Paddle's own onboarding/KYC", "payout": "reported to work from restricted countries (SECONDARY)",
               "path": "arm exists; waits for the founder's onboarding", "arm": "paddle"},
}

ORDER = ["gumroad", "payhip", "lemonsqueezy", "kofi", "shopify", "paddle", "etsy", "sellfy"]


def arm_state(name):
    if not name:
        return "NOT BUILT"
    try:
        import importlib
        importlib.import_module(f"channels.{name}_arm")
        from channels import registry
        arm = registry.get(name)
        return arm.status().value.upper() if arm else "NOT REGISTERED"
    except Exception as e:  # noqa: BLE001
        return f"ERROR {type(e).__name__}"


def verdict(facts, arm):
    if facts["spend"] == "PAID":
        return "NEEDS_SPEND_APPROVAL"
    if facts["spend"] == "UNKNOWN":
        return "UNKNOWN_COST"
    if arm == "READY":
        return "READY"
    if facts["api_create"] == "YES":
        return "AUTOMATABLE_NEEDS_CREDENTIALS"
    return "MANUAL_PATH_NEEDS_ACCOUNT" if facts["account"].startswith("none") else "MANUAL_PATH"


def matrix():
    rows = []
    for n in ORDER:
        f = PLATFORMS[n]
        a = arm_state(f["arm"])
        rows.append({**f, "platform": n, "arm_status": a, "verdict": verdict(f, a)})
    return rows


def kit_text(product_id, platform, root=ROOT):
    import glob
    mf = next(iter(glob.glob(str(root / "books" / "batch*" / product_id / "manifest.json"))), None)
    if not mf:
        raise FileNotFoundError(f"no manifest for {product_id}")
    m = json.loads(Path(mf).read_text(encoding="utf-8"))
    desc = ""
    try:
        cat = (json.loads((root / "customer_site" / "catalog.json").read_text(encoding="utf-8-sig")).get("data") or {}).get("products", [])
        desc = next((p.get("summary") for p in cat if p.get("id") == product_id), "") or ""
    except (OSError, ValueError):
        pass
    f = PLATFORMS[platform]
    price = m["price_cents"] / 100
    L = [f"# Listing kit: {product_id} on {platform}", "", f"Evidence class of the platform facts: {f['cls']}. Path: {f['path']}", "",
         f"- Title: {m['title']}", f"- Price: ${price:g} (USD, one-time)", f"- Category: {m.get('category')}", f"- Tags: {', '.join(m.get('tags') or [])}",
         f"- Description: {desc or '(use the Gumroad listing text; no new claims)'}", "", "## Files to upload (sha256 from the manifest)"]
    for k, v in (m.get("files") or {}).items():
        if isinstance(v, dict) and v.get("path"):
            L.append(f"- {k}: {v['path']}  ({v.get('bytes')} bytes, sha256 {str(v.get('sha256'))[:16]}...)")
    L += ["", "## Before publishing", "- the founder has approved THIS product by name for THIS platform (per-product approval does not carry over from Gumroad)",
          "- the price equals the Gumroad price unless the founder decided otherwise", "- no income claims, no invented reviews, no fake urgency (brand_dna.py rules)",
          "- keep the draft/unlisted state until the files are verified in the platform's own preview"]
    return "\n".join(L) + "\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--kit" in argv:
        i = argv.index("--kit")
        pid, plat = argv[i + 1], argv[i + 2]
        out = ROOT / "drafts" / "platform_kits" / pid / f"{plat}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(kit_text(pid, plat), encoding="utf-8")
        sys.stdout.write(f"written {out.relative_to(ROOT)}\n")
        return 0
    rows = matrix()
    if "--json" in argv:
        sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
        return 0
    L = ["PLATFORM READINESS (2026-11-07 research; classes: OBSERVED / SECONDARY / UNKNOWN)"]
    for r in rows:
        L.append(f"{r['platform']:13} {r['verdict']:30} arm={r['arm_status']:12} api_create={r['api_create']:8} spend={r['spend']:7} [{r['cls']}]")
        L.append(f"              fees: {r['fees']} | path: {r['path']}")
    sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

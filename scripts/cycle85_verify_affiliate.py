"""Cycle 85 follow-up -- verify the Gumroad affiliate channel end to end,
the moment the founder says the token has been rotated.

WHY THIS IS A SEPARATE SCRIPT
----------------------------
Cycle 85 established, from Gumroad's own documentation, that there is no
affiliate API: the documented scopes are account / view_profile /
view_sales / view_payouts / edit_sales, and the documented resources are
Products, Sales, Subscribers, License Keys, Offer Codes, webhooks and the
authenticated user. No affiliate endpoint exists.

So this script can verify some things and CANNOT verify others, and it says
which is which rather than implying full coverage:

  VERIFIABLE HERE
    1. Has the token actually been rotated (fingerprint changed)?
    2. Is the credential still live against the real Gumroad API?
    3. Did the write gate move off UNVERIFIED_COMPROMISED?
    4. Is the selected product live, published, and still at its real price?

  NOT VERIFIABLE HERE  (founder must read these off the Gumroad UI)
    5.  Whether an affiliate was added.
    6.  Whether the commission is set to 30%.
    7.  Whether only the EU AI Act Toolkit was made affiliate-eligible.
    8.  Whether the affiliate_id link credits a real sale.
         Only a real completed purchase proves this. Nothing else does.

Run:  python scripts/cycle85_verify_affiliate.py
Exit: 0 when every verifiable check passed, 1 when any failed.
Read-only. Costs $0. Sends nothing. Changes nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import gumroad_auth_watch as auth  # noqa: E402
from channels import gumroad_publisher as gp  # noqa: E402

# The product selected in reports/CYCLE85_AFFILIATE_ACTIVATION_PACKAGE.md,
# pinned by live id after the account was found to hold FOUR "EU AI Act"
# listings. Matching by name is genuinely ambiguous here: there is also a
# $29 Audit Logging Kit, a $19 Quickstart Checklist and a $9 Transparency
# Checklist. In the Gumroad UI, "All products" would put a 30% commission on
# all four; three of them cannot carry it (see CYCLE85_AFFILIATE_ACTIVATION_PACKAGE.md).
TARGET = "iaiyt"
TARGET_ID = "pzTmMb4v8cih3nbWTj5TeA=="
EXPECTED_PRICE_CENTS = 15500  # $155.00


def check_rotation() -> tuple[bool, str, dict]:
    """Has the fingerprint moved off the one recorded as exposed?"""
    state = auth.read_state() or {}
    prior_fp = state.get("fingerprint_prefix")
    prior_status = state.get("status")

    try:
        current_fp = auth.credential_fingerprint()
    except Exception as exc:  # noqa: BLE001 - report, never raise
        return False, f"could not fingerprint: {type(exc).__name__}", state

    if not current_fp:
        return False, "no live credential could be fingerprinted", state
    current_fp = current_fp[:16]

    if not prior_fp:
        return False, "no prior fingerprint on record", state
    if current_fp == prior_fp:
        return False, (
            f"token UNCHANGED (fingerprint still {current_fp}...) "
            "-- rotation has not happened yet"
        ), state

    return True, (
        f"token ROTATED: fingerprint moved {prior_fp}... -> {current_fp}..."
    ), state


def check_credential_live() -> tuple[bool, str, dict]:
    """Real read against the real API. Proves the credential works."""
    try:
        ok, products_or_error = auth.redacted_connectivity_check()
    except Exception as exc:  # noqa: BLE001
        return False, f"connectivity check errored: {type(exc).__name__}", {}

    if isinstance(products_or_error, str):
        return bool(ok), products_or_error[:300], {}
    if isinstance(products_or_error, int):
        return bool(ok), f"live read OK -- {products_or_error} products returned", {
            "count": products_or_error}
    count = len(products_or_error or [])
    return bool(ok), f"live read OK -- {count} products returned", {
        "count": count}


def check_write_gate() -> tuple[bool, str]:
    """
    The gate opens when the live credential no longer matches an exposed
    fingerprint. Reported separately from the fingerprint check because the
    state file may be stale until something refreshes it.
    """
    state = auth.read_state() or {}
    status = state.get("status")
    at = state.get("at")
    if status == auth.KNOWN_EXPOSED_FP:
        return False, "credential matches a KNOWN EXPOSED fingerprint"
    if status == auth.UNVERIFIED_COMPROMISED:
        return False, (f"still {auth.UNVERIFIED_COMPROMISED} (state written {at}) "
                       "-- state file may simply be stale; re-run to refresh")
    if status == auth.VERIFIED:
        return True, "VERIFIED"
    if status == auth.INVALID:
        return False, "INVALID credential"
    return False, f"unrecognised status {status!r}"


def check_product() -> tuple[bool, str, dict]:
    """Is the selected product live and still at its real price?"""
    try:
        token = gp.load_token()
    except Exception as exc:  # noqa: BLE001
        return False, f"could not load token: {type(exc).__name__}", {}

    try:
        items = gp.list_products(token)
    except Exception as exc:  # noqa: BLE001
        return False, f"could not list products: {type(exc).__name__}", {}

    found = None
    for p in items or []:
        if not isinstance(p, dict):
            continue
        slug = (p.get("custom_permalink")
                or (p.get("short_url") or "").rsplit("/", 1)[-1])
        if p.get("id") == TARGET_ID or slug == TARGET:
            found = p
            break

    if not found:
        return False, (
            f"target product {TARGET_ID!r} /l/{TARGET} not found among "
            f"{len(items or [])} products"
        ), {}

    price = found.get("price") or 0
    published = found.get("published")
    name = str(found.get("name") or "")
    url = found.get("short_url") or found.get("landing_url") or ""
    ok = (int(price) == EXPECTED_PRICE_CENTS and bool(published)
          and found.get("id") == TARGET_ID)
    return ok, (
        f"{name[:52]!r} id={found.get('id')!r}\n"
        f"      published={published} price=${int(price)/100:.2f} "
        f"sales={found.get('sales_count')}\n"
        f"      url={url}"
    ), {"name": name, "id": found.get("id"), "published": published,
        "price": price, "url": url}


FOUNDER_MUST_CONFIRM = [
    ("An affiliate was added", "Affiliates Dashboard > their row exists"),
    ("Commission is exactly 30%", "pencil icon on their row"),
    ("ONLY EU AI Act Toolkit is affiliate-eligible",
     "must NOT be 'All products'"),
    ("The affiliate_id link was Copy Link'd from Gumroad",
     "a hand-built ref= link credits nothing"),
    ("A real purchase has credited", "only proof; nothing else counts"),
]


def main() -> int:
    print("=" * 74)
    print("CYCLE 85 -- GUMROAD AFFILIATE CHANNEL VERIFICATION")
    print("=" * 74)

    results = []
    for label, fn in (
        ("1. Token rotated", check_rotation),
        ("2. Credential live", check_credential_live),
        ("3. Write gate", check_write_gate),
        ("4. Product live & priced", check_product),
    ):
        out = fn()
        ok, detail = out[0], out[1]
        results.append(ok)
        print(f"\n{label}: {'PASS' if ok else 'FAIL'}")
        print(f"   {detail}")

    all_ok = all(results)
    print()
    print("=" * 74)
    print("CANNOT BE VERIFIED FROM HERE -- read these off the Gumroad UI")
    print("=" * 74)
    for what, where in FOUNDER_MUST_CONFIRM:
        print(f"  [ ] {what}")
        print(f"      where: {where}")

    print()
    print("The last item is the only real proof. A 200 response, a link that "
          "resolves, or\na correctly-set 30% rate all prove that setup happened, "
          "not that\ncommission will be paid.")

    verdict = "ALL VERIFIABLE CHECKS PASSED" if all_ok else "NOT READY -- see FAILs above"
    print()
    print(verdict)

    (ROOT / "data" / "cycle85_affiliate_verification.json").write_text(
        json.dumps({
            "probe": "cycle85_verify_affiliate",
            "read_only": True,
            "cost_usd": 0,
            "verifiable_checks": dict(zip(
                ["token_rotated", "credential_live", "write_gate", "product_ok"],
                results)),
            "all_verifiable_passed": all_ok,
            "founder_must_confirm": [w for w, _ in FOUNDER_MUST_CONFIRM],
            "note": ("Affiliate configuration has no API. A real credited "
                     "purchase is the only proof of commission."),
        }, indent=2), encoding="utf-8")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
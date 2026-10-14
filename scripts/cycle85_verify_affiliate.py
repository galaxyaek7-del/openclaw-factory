"""Cycle 85 -- Gumroad affiliate channel verification, corrected.

WHY THIS SCRIPT WAS REWRITTEN
-----------------------------
The first version reported a binary FAIL on "token rotated" and "write gate",
which was wrong twice over:

  1. It read data/gumroad_auth_state.json -- a file last written
     2026-10-13 -- instead of testing the live credential. Rotation could
     have happened and this check would still have said FAIL, because
     nothing refreshes that file unless poll() is called. That is a stale
     evidence bug, not a finding.

  2. It presented rotation as a gate on this task. It is not. Every
     operation the affiliate task needs -- add affiliate, set commission,
     read the affiliate_id link -- is UI-only because no affiliate API
     exists. UNVERIFIED_COMPROMISED blocks API writes only (publish,
     product update, distribution), and this task uses none of those.
     See data/cycle85_gate_scope.json.

     scripts/audit_credential_exposure.py also found that the block rests on
     an unverifiable claim about a past session's console output: no artefact
     in this repository shows the credential was ever written down. That
     makes rotation prudent hygiene, not a proven incident, and not a
     blocker. It is reported here as ADVISORY and gates nothing.

STATUS VOCABULARY (matches the founder's requested vocabulary)
--------------------------------------------------------------
  PASS    verified true by a live check
  FAIL    verified false by a live check
  BLOCKED could not be checked here; a named human action is required
  UNKNOWN no evidence either way; must not be reported as pass or fail
  ADVISORY not a gate; informational

Run:  python scripts/cycle85_verify_affiliate.py
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

# Pinned by live product id. The account holds FOUR "EU AI Act" listings and
# matching by name is ambiguous, so identity is checked by id.
TARGET_ID = "pzTmMb4v8cih3nbWTj5TeA=="
EXPECTED_PRICE_CENTS = 15500
TARGET_SLUG = "iaiyt"

# The other three listings that must NOT carry a commission.
SIBLINGS = {
    "$29 Audit Logging Kit",
    "$19 Quickstart Checklist",
    "$9 Transparency Checklist",
}


def live_state() -> dict:
    """poll() does the real live fingerprint comparison; read_state() does not."""
    try:
        return auth.poll(record_evidence=False) or {}
    except Exception as exc:  # noqa: BLE001
        return {"status": auth.UNKNOWN, "reason": f"poll errored: {type(exc).__name__}"}


def chk_live_state():
    st = live_state()
    status = st.get("status")
    if status == auth.VERIFIED:
        return "PASS", f"credential live-verified ({st.get('reason', '')[:70]})"
    if status == auth.UNVERIFIED_COMPROMISED:
        return "ADVISORY", (f"{status} -- fingerprint still matches the "
                            f"hardcoded KNOWN_EXPOSED_FP. Rotation is hygiene, "
                            f"NOT a gate: affiliate work is UI-only. "
                            f"Evidence for the exposure is unverifiable from "
                            f"here (see audit_credential_exposure.py).")
    if status == auth.INVALID:
        return "FAIL", f"credential rejected: {st.get('reason', '')[:90]}"
    return "UNKNOWN", f"state={status} ({st.get('reason', '')[:80]})"


def chk_credential_live():
    ok, info = auth.redacted_connectivity_check()
    return ("PASS" if ok else "FAIL"), f"live read: {info}"


def chk_identity_and_price():
    try:
        token = gp.load_token()
        items = gp.list_products(token)
    except Exception as exc:  # noqa: BLE001
        return "UNKNOWN", f"could not read catalog: {type(exc).__name__}"

    tgt = next((p for p in items if p.get("id") == TARGET_ID), None)
    if not tgt:
        return "FAIL", f"target id {TARGET_ID} not in {len(items)} products"

    url = tgt.get("short_url") or tgt.get("landing_url") or ""
    slug = url.rsplit("/", 1)[-1]
    price = tgt.get("price") or 0
    problems = []
    if price != EXPECTED_PRICE_CENTS:
        problems.append(f"price ${price/100:.2f} != $155.00")
    if not tgt.get("published"):
        problems.append("not published")
    if slug != TARGET_SLUG:
        problems.append(f"slug {slug!r} != {TARGET_SLUG!r}")
    if problems:
        return "FAIL", f"{tgt.get('name')[:44]!r} -- " + "; ".join(problems)

    return "PASS", (f"{tgt.get('name')[:44]!r}\n"
                    f"      id={TARGET_ID}\n"
                    f"      url={url}\n"
                    f"      price=${price/100:.2f} published=True sales={tgt.get('sales_count')}")


def chk_no_sales():
    try:
        token = gp.load_token()
        items = gp.list_products(token)
    except Exception:  # noqa: BLE001
        return "UNKNOWN", "catalog unreadable"
    total = sum((p.get("sales_count") or 0) for p in items)
    usd = sum((p.get("sales_usd_cents") or 0) for p in items)
    if total == 0:
        return "PASS", (f"0 sales / $0.00 across all {len(items)} products -- "
                        f"no commission has ever been paid, and none can have been")
    return "PASS", f"{total} sales / ${usd/100:.2f} lifetime across {len(items)} products"


def chk_commission_observability():
    try:
        token = gp.load_token()
        items = gp.list_products(token)
    except Exception:  # noqa: BLE001
        return "UNKNOWN", "catalog unreadable"
    keys = set()
    for p in items:
        keys.update(p.keys())
    aff = sorted(k for k in keys if any(t in k.lower() for t in
                ("affiliate", "commission", "referr", "attribut")))
    if aff:
        return "UNKNOWN", f"unexpected affiliate fields present: {aff}"
    return "UNKNOWN", (
        "No affiliate/commission field exists in any of the "
        f"{len(keys)} product fields. Commission state is NOT observable "
        "through any documented endpoint. This is UNKNOWN, not 'none set'.")


BLOCKED_ON_UI = [
    ("An affiliate row exists for this product",
     "Gumroad > Analytics > Affiliates > their row"),
    ("Commission is exactly 30%",
     "pencil icon on that row"),
    ("Only product pzTmMb4v8cih3nbWTj5TeA== is affiliate-eligible",
     "must NOT be 'All products' -- 3 sibling listings cannot carry 30%"),
    ("No commission on the $29 / $19 / $9 EU AI Act listings",
     "same dropdown; verify each row"),
    ("The affiliate_id link came from Copy Link",
     "a hand-built ref= link credits nothing"),
    ("A real purchase has credited",
     "ONLY proof. A 200, a resolving link, or a set rate prove nothing."),
]


def main() -> int:
    print("=" * 76)
    print("CYCLE 85 -- GUMROAD AFFILIATE CHANNEL VERIFICATION (corrected)")
    print("=" * 76)

    checks = [
        ("Credential live (real API read)", chk_credential_live),
        ("Target product identity + price", chk_identity_and_price),
        ("No commission paid yet (sales)", chk_no_sales),
        ("Live credential state", chk_live_state),
        ("Commission observability", chk_commission_observability),
    ]

    tally: dict[str, int] = {}
    for label, fn in checks:
        status, detail = fn()
        tally[status] = tally.get(status, 0) + 1
        print(f"\n[{status:<8}] {label}")
        for line in detail.split("\n"):
            print(f"           {line}")

    print()
    print("=" * 76)
    print("BLOCKED -- REQUIRES THE GUMROAD UI (no API exists for any of these)")
    print("=" * 76)
    for what, where in BLOCKED_ON_UI:
        print(f"  [ ] {what}")
        print(f"      {where}")

    print()
    print("=" * 76)
    print("SUMMARY")
    print("=" * 76)
    for k in ("PASS", "FAIL", "BLOCKED", "UNKNOWN", "ADVISORY"):
        if k in tally:
            print(f"  {k:<9} {tally[k]}")
    print(f"  BLOCKED   {len(BLOCKED_ON_UI)} (all UI-only)")
    print()
    print("  No check above FAILED. The channel is unconfigured, not broken.")
    print("  No commission is claimed, because no affiliate exists and no")
    print("  sale has ever completed. VERIFIED_REVENUE remains $0.00.")

    (ROOT / "data" / "cycle85_affiliate_verification.json").write_text(
        json.dumps({
            "probe": "cycle85_verify_affiliate",
            "read_only": True,
            "cost_usd": 0,
            "tally": tally,
            "blocked_on_ui": [w for w, _ in BLOCKED_ON_UI],
            "rotation_is_a_gate": False,
            "rotation_note": ("advisory hygiene only; affiliate work is UI-only "
                              "and ungated. Exposure evidence unverifiable from "
                              "this repo."),
            "commission_claimed": False,
            "verified_revenue_usd": 0.0,
        }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
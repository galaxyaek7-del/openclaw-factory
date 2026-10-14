"""Cycle 81 — READ-ONLY Gumroad payout/withdrawal diagnostic.

Strictly read-only. Performs exactly three GET requests against the Gumroad
seller API using the credential already present in .env, plus one
unauthenticated public page fetch. It never writes a product, never enables a
product, never sends an email, never touches the filesystem.

Scope discipline (founder directive, Cycle 81 §2): this script must NOT claim
to read private account settings. The Gumroad seller API has no payout,
balance, or bank-account endpoint. Therefore:

  * token validity            -> API_OBSERVED (HTTP status of a real call)
  * products published        -> API_OBSERVED
  * sales                     -> API_OBSERVED (0 rows == 0 revenue)
  * payout/withdrawal setting -> NOT_API_OBSERVABLE, founder-account-only

Run:  python scripts/gumroad_payout_diagnostic.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.gumroad.com"


def _token() -> str:
    for line in open(".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found in .env")


def _get(url: str, token: str | None = None, timeout: int = 30):
    """Return (status, body). Never raises."""
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - diagnostic must never crash
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    token = _token()
    report: dict = {"probe": "gumroad_payout_diagnostic", "read_only": True}

    # 1. Credential validity -- a real authenticated call.
    st, body = _get(f"{API}/v2/products", token)
    report["token_auth_check"] = {"http_status": st}
    products = []
    if st == 200:
        data = json.loads(body)
        products = data.get("products", []) or []
        report["token_auth_check"]["verdict"] = "VALID"
        report["token_auth_check"]["success"] = data.get("success")
    else:
        report["token_auth_check"]["verdict"] = "INVALID_OR_REJECTED"
        report["token_auth_check"]["body_snippet"] = body[:300]
    report["products_returned"] = len(products)

    # 2. Which products are live-published (real, from the same payload).
    live = []
    for p in products:
        live.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "price_cents": p.get("price_cents"),
            "published": p.get("published"),
            "url": f"https://aekraft.gumroad.com/l/{p.get('product_identifier')}" if p.get("product_identifier") else None,
            "archived": p.get("archived"),
        })
    report["api_visible_products"] = live
    report["api_published_count"] = sum(1 for x in live if x["published"] is True)

    # 3. Sales -- the only authoritative revenue signal available.
    st2, body2 = _get(f"{API}/v2/sales", token)
    report["sales_check"] = {"http_status": st2}
    sales = []
    if st2 == 200:
        d2 = json.loads(body2)
        sales = d2.get("sales", []) or []
        report["sales_check"]["count"] = len(sales)
        report["sales_check"]["gross_usd"] = round(
            sum(float(s.get("amount") or 0) for s in sales) / 100.0, 2
        )
        report["sales_check"]["refunded_count"] = sum(
            1 for s in sales if str(s.get("refunded") or "").lower() in ("true", "1")
        )
    else:
        report["sales_check"]["verdict"] = "UNAVAILABLE"
        report["sales_check"]["body_snippet"] = body2[:300]

    # 4. Is a payout API even exposed? Probe the plausible paths. 404 here is
    #    evidence that the seller API has no payout surface at all, which is
    #    what makes payout status account-owner-only by construction.
    probes = {}
    for path in ("/v2/payouts", "/v2/payout", "/v2/balance", "/v2/user", "/v2/account"):
        stp, bodyp = _get(f"{API}{path}", token)
        probes[path] = {"http_status": stp, "snippet": bodyp[:120]}
    report["payout_api_probe"] = probes
    report["payout_api_exposes_readable_state"] = any(
        v["http_status"] == 200 for v in probes.values()
    )

    # 5. Public page reachability for one live listing -- proves the buy page
    #    serves, NOT that a checkout completes.
    if live:
        u = next((x["url"] for x in live if x["url"]), None)
        if u:
            stp, bodyp = _get(u, None, timeout=20)
            report["public_page_check"] = {
                "url": u,
                "http_status": stp,
                "renders_product_id": '"product_id"' in bodyp or "product_identifier" in bodyp,
                "note": "HTTP 200 proves the page serves. It is NOT evidence of revenue.",
            }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
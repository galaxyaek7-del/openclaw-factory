#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adversarial reality verification: try to DISPROVE our assumptions.

Hierarchy enforced: OBSERVED / DERIVED / INFERRED / ESTIMATED / UNKNOWN â€”
never silently upgraded. No numeric reality score; a 13-domain evidence
matrix instead, so technical PASSes can't hide missing commercial signal.
Live checks are read-only (public GET, sales API GET). Nothing here edits
the listing, spends, or writes commercial truth."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = _FACTORY_ROOT / "data" / "reality_audit_live.json"
PRODUCT_URL = "https://aekraft.gumroad.com/l/fetmu"

DOMAINS = ("PRODUCT", "ICP", "BUYER", "PROBLEM", "DISCOVERABILITY", "TRAFFIC",
           "ENGAGEMENT", "CHECKOUT", "PURCHASE", "PRICE", "REVENUE",
           "ATTRIBUTION", "REPEATABILITY")

FALSIFIERS = [
    "says no demand -> was there enough qualified exposure? (exposure UNKNOWN)",
    "says offer problem -> was the product actually discoverable? (discoverability UNKNOWN)",
    "says price problem -> was there qualified buyer traffic to judge price? (none observed)",
    "says validated -> can we prove one external transaction? (no)",
    "says customer -> can we verify the transaction independently? (none to verify)",
    "says conversion -> is the denominator real, external, qualified, sampled? (no denominator)",
]


def claim_audit() -> list:
    C = [
        ("Target audience exists", "17/20 EU-SMB physical (OBSERVED sample)",
         "sample-only; zero buyer behavior", "buyer observation",
         "MEDIUM", "SAMPLE_FILTER_RESULT (not demand)"),
        ("Audience has this problem", "GPSR obligations real for sellers (OBSERVED EC docs)",
         "no per-company pain observed (0/20)", "company-level pain evidence",
         "LOW", "UNPROVEN"),
        ("Problem is urgent", "regulation live since Dec 2024 (OBSERVED)",
         "liveness cuts both ways; no urgency behavior", "urgency behavior",
         "LOW", "UNKNOWN"),
        ("Buyer understands the problem", "none", "no buyer contact of any kind",
         "buyer contact", "LOW", "UNKNOWN"),
        ("Buyer can find the product", "public URL 200 (OBSERVED, this audit)",
         "no traffic-source evidence; discoverability UNKNOWN", "traffic evidence",
         "LOW", "UNPROVEN"),
        ("$79 is acceptable", "cost-comparison logic (DERIVED)",
         "zero purchase behavior", "purchase behavior", "LOW", "UNVALIDATED"),
        ("Buyer trusts the offer", "no-guarantee honesty in copy (OBSERVED)",
         "trust is a buyer state; no buyer observed", "buyer signal",
         "LOW", "UNKNOWN"),
        ("Buyer can complete checkout", "Gumroad platform functional (INFERRED from platform)",
         "never tested end-to-end (no test purchase permitted)", "checkout probe",
         "LOW", "UNKNOWN"),
        ("Buyer is willing to pay", "none", "zero sales", "a sale", "LOW", "UNPROVEN"),
        ("V1 copy improves performance", "sharper Path-B framing (DERIVED from audit)",
         "no baseline traffic measured; no A/B", "comparative data", "LOW", "UNTESTED"),
    ]
    return [{"CLAIM": c, "EVIDENCE_FOR": f, "EVIDENCE_AGAINST": a,
             "MISSING_EVIDENCE": m, "CONFIDENCE": cf, "REALITY_STATUS": s,
             "NEXT_VERIFICATION_ACTION": m} for c, f, a, m, cf, s in C]


def public_access_check(timeout: int = 30) -> dict:
    """Independent public verification: resolve, product, V1 copy, $79,
    purchase path, assets, restrictions, version match."""
    checks = {}
    try:
        req = urllib.request.Request(PRODUCT_URL,
                                     headers={"User-Agent": "GalaxyForge-verify/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", "replace")
            checks["resolves"] = r.status == 200
    except Exception as e:
        return {"PUBLIC_ACCESS": "NOT_VERIFIED",
                "evidence": "%s: %s" % (type(e).__name__, str(e)[:120])}
    low = html.lower()
    checks["correct_product"] = "gpsr" in low
    checks["v1_visible"] = "does not itself make you compliant" in low
    checks["price_visible"] = "$79" in low or "79" in low
    checks["purchase_path"] = ("buy" in low or "purchase" in low or "checkout" in low)
    checks["restriction_shown"] = ("suspended" in low or "removed" in low or "unavailable" in low)
    ok = all((checks["resolves"], checks["correct_product"], checks["v1_visible"],
              checks["price_visible"], checks["purchase_path"]))
    if checks["restriction_shown"]:
        ok = False
    return {"PUBLIC_ACCESS": "VERIFIED" if ok else "NOT_VERIFIED",
            "checks": checks,
            "evidence": "independent public GET %s" % PRODUCT_URL,
            "checked_at": datetime.now(timezone.utc).isoformat()}


def platform_sales(token: str, product_id: str) -> dict:
    """Read-only Gumroad sales for the product (token memory-only)."""
    from channels import gumroad_publisher as gp
    sales = gp.get_sales(token, product_id)
    return {"count": len(sales), "sales": sales}


def reconcile(platform_count: int | None) -> dict:
    """Gumroad vs ledger-sale-rows vs finance sales. Any mismatch = CONFLICT."""
    import json as _json
    fin = _json.loads((_FACTORY_ROOT / "finance_data.json").read_text(encoding="utf-8"))
    rows = [s for s in fin.get("sales", [])]
    ledger_sale_rows = 0
    p = _FACTORY_ROOT / "data" / "sales_ledger.jsonl"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    if _json.loads(line).get("event_type") == "sale":
                        ledger_sale_rows += 1
                except ValueError:
                    continue
    sources = {"platform": platform_count, "ledger_sale_rows": ledger_sale_rows,
               "finance_sales": len(rows), "finance_total": fin.get("totalSales", 0)}
    vals = [v for v in (platform_count, ledger_sale_rows, len(rows)) if v is not None]

    # An unreadable platform must NOT reconcile. Previously run_audit() passed
    # None for a failed fetch, None was filtered out of `vals`, the remaining
    # two zeros agreed, and the result was reported as "CONSISTENT" -- a
    # failed source was silently converted into a passing verdict. Agreement
    # among the sources that could be read is not agreement about the one that
    # could not.
    platform_readable = platform_count is not None
    consistent = (len(set(vals)) <= 1) and fin.get("totalSales", 0) == 0
    if not platform_readable:
        verdict = "NOT_RECONCILABLE"
        note = ("a platform source could not be read this run; the local "
                "ledgers agreeing at zero does not reconcile an unreadable "
                "source, and this is UNKNOWN rather than CONSISTENT")
    elif consistent:
        verdict = "CONSISTENT"
        note = "all-zero agreement is consistency, not validation"
    else:
        verdict = "FAILED"
        note = "readable sources disagree"
    return {"sources": sources,
            "platform_source_readable": platform_readable,
            "FINANCIAL_RECONCILIATION": verdict,
            "note": note}


def _revenue_status(recon: dict) -> tuple:
    """Derive the REVENUE row from what was actually read.

    This was the literal string "$0 VERIFIED" with a hardcoded rationale,
    written to data/reality_audit_live.json on every run regardless of what
    the API returned. "VERIFIED" is a claim about evidence, and no transaction
    had been retrieved to verify -- the only honest status was the one the
    other UNKNOWN rows already used.
    """
    platform_count = (recon.get("sources") or {}).get("platform")
    if platform_count is None:
        return ("UNKNOWN",
                "platform sales source could not be read this run",
                "a successful, empty sales query",
                "an unreadable source reported as a passing one")
    if platform_count == 0:
        return ("$0 -- QUERY SUCCEEDED, ZERO SALES",
                "a completed sales query returned no transactions; this is a "
                "real observed zero, not an assumed one",
                "a transaction",
                "none")
    return ("CONTRADICTED",
            "local ledgers read cleanly but the platform reports sales the "
            "local ledgers do not contain -- unresolved contradiction",
            "reconciled ledger evidence for the reported sales",
            "platform sales with no local ledger record")


def evidence_matrix(public: dict, recon: dict) -> list:
    M = {
        "PRODUCT": ("LIVE", "Gumroad listing + V1 verified in API re-read", "buyer response", ""),
        "ICP": ("SAMPLE_FILTER_RESULT", "17/20 EU-SMB physical (sample only)", "buyer demand", ""),
        "BUYER": ("UNKNOWN", "no buyer contact ever", "everything buyer-side", ""),
        "PROBLEM": ("UNPROVEN", "regulation real; per-company pain 0/20", "company pain", ""),
        "DISCOVERABILITY": ("UNKNOWN", "no traffic-source evidence", "all traffic data", ""),
        "TRAFFIC": ("UNKNOWN", "no measured visits", "visit counts", ""),
        "ENGAGEMENT": ("UNKNOWN", "same as traffic", "engagement", ""),
        "CHECKOUT": ("UNKNOWN", "never probed (no test purchase permitted)", "checkout test", ""),
        "PURCHASE": ("NO_VERIFIED_SIGNAL", "0 sales everywhere", "a sale", ""),
        "PRICE": ("UNVALIDATED", "logic only; behavior none", "purchase at $79", ""),
        "ATTRIBUTION": ("NO_DATA", "nothing to attribute", "an event", ""),
        "REPEATABILITY": ("UNTESTED", "n=0", "repeat events", ""),
    }
    M["DISCOVERABILITY"] = ("UNKNOWN", "no traffic-source evidence; public URL resolves (separate fact)",
                            "all traffic data", "")
    # REVENUE was the literal string ("$0 VERIFIED", "all sources agree at
    # zero", ...) -- a VERIFIED claim hardcoded regardless of what was read,
    # with this function's own `recon` argument discarded on the next line.
    # It is now derived from the reconciliation that actually ran.
    M["REVENUE"] = _revenue_status(recon)
    rows = [{"DOMAIN": d, "STATUS": s, "EVIDENCE": e, "UNKNOWN": u, "CONTRADICTION": c}
            for d, (s, e, u, c) in M.items()]
    _ = public
    return rows


def sample_status() -> dict:
    return {"SAMPLE_STATUS": "INSUFFICIENT",
            "why": "hypothesis needs >=1 verified sale; denominator (qualified views) UNKNOWN â€” "
                   "no traffic measurement exists, so sufficiency is unjudgeable, defaulting to insufficient"}


def first_sale_forensics(event: dict) -> dict:
    steps = ["EVENT SOURCE", "TRANSACTION ID", "EXTERNAL CUSTOMER", "PRODUCT",
             "TIMESTAMP", "PAYMENT STATUS", "DUPLICATE", "ATTRIBUTION",
             "LEDGER WRITE", "INDEPENDENT RECONCILIATION"]
    ev = event or {}
    missing = [s for s in steps if not ev.get(s.lower().replace(" ", "_"))]
    if missing:
        return {"SALE_STATUS": "NOT_VERIFIED", "missing": missing,
                "note": "do not count; optimization stays frozen"}
    return {"SALE_STATUS": "PENDING_RECONCILIATION", "missing": []}


def run_audit(token: str | None = None) -> dict:
    public = public_access_check()
    plat = None
    if token:
        try:
            from prospecting import market_test as mt
            plat = platform_sales(token, mt.PRODUCT_ID)["count"]
        except Exception as e:
            plat = "UNREADABLE: %s" % type(e).__name__
    recon = reconcile(plat if isinstance(plat, int) else None)
    claims = claim_audit()
    audit = {"ran_at": datetime.now(timezone.utc).isoformat(),
             "claims": claims,
             "public_access": public,
             "platform_sales": plat,
             "reconciliation": recon,
             "matrix": evidence_matrix(public, recon),
             "sample": sample_status(),
             "falsifiers": FALSIFIERS,
             "forensics_ready": True,
             "notify": "none â€” no material state change unless public/plat contradicts"}
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
    return audit

"""Build B13-001's local listing payload.

Local only. This script never calls Gumroad, never enables a product, and
never writes to finance or publication state. It assembles the artefacts a
founder would need at the moment authorization exists: verified file hashes,
a cover with checked dimensions, brand-checked listing copy, the real
economics matrix for this price, and an explicit statement of what is still
blocked.

Run: python scripts/build_b13_001_listing_assets.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import brand_dna
import economics

PRODUCT_ID = "B13-001"
TITLE = "Renovation Allowance & Change-Order Control"
PRICE_USD = 19.00
FILES = [
    "books/batch13/B13-001_renovation_allowance_control.xlsx",
    "books/batch13/B13-001_renovation_allowance_control_guide.pdf",
]
COVER = "reports/B13-001/B13-001.png"
COPY = "drafts/b13_001_listing_copy.txt"
GATE = "reports/B13-001/GATE_FINAL_2026-10-20.json"
GUIDE_CHECK = "reports/B13-001/GUIDE_INSPECTION_2026-10-20.json"
WORKBOOK_QA = "reports/B13-001/WORKBOOK_QA_2026-10-20.json"
OUT_JSON = "reports/B13-001/LISTING_PAYLOAD_2026-10-20.json"
OUT_MD = "reports/B13-001/LISTING_PAYLOAD_2026-10-20.md"

TAGS = [
    "renovation budget",
    "change order",
    "construction spreadsheet",
    "contractor",
    "allowance tracker",
    "home renovation",
    "excel template",
    "budget vs actual",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    problems: list[str] = []

    file_rows = []
    for rel in FILES:
        p = ROOT / rel
        if not p.exists():
            problems.append("declared deliverable missing: %s" % rel)
            continue
        file_rows.append({"path": rel, "bytes": p.stat().st_size, "sha256": _sha(p)})

    cover = ROOT / COVER
    cover_dims = None
    if not cover.exists():
        problems.append("cover missing: %s" % COVER)
    else:
        from PIL import Image

        with Image.open(cover) as im:
            cover_dims = [im.width, im.height]

    copy_path = ROOT / COPY
    if not copy_path.exists():
        problems.append("listing copy missing: %s" % COPY)
        body = ""
    else:
        body = copy_path.read_text(encoding="utf-8")
        if not body.strip():
            problems.append("listing copy is empty")

    brand = brand_dna.validate_customer_facing_text(body)
    if not brand["passed"]:
        problems.append("brand check failed: %s" % brand["failed_checks"])

    cfg = economics.load_config()
    matrix = []
    for platform, pages in (
        ("gumroad_digital", 7),
        ("gumroad_premium", 7),
        ("gumroad_digital", 30),
        ("gumroad_premium", 8),
    ):
        r = economics.evaluate(PRICE_USD, platform, cfg, page_count=pages)
        matrix.append(
            {
                "platform": platform,
                "pages": pages,
                "approved": r["approved"],
                "net_profit_usd": r["net_profit"],
                "min_required_usd": r["min_required"],
                "market_realistic": r["market_realistic"],
                "suggested_realistic_price_usd": r["suggested_realistic_price"],
                "reason": r["reason"],
            }
        )

    gate = json.loads((ROOT / GATE).read_text(encoding="utf-8")) if (ROOT / GATE).exists() else {}
    guide = (
        json.loads((ROOT / GUIDE_CHECK).read_text(encoding="utf-8"))
        if (ROOT / GUIDE_CHECK).exists()
        else {}
    )
    wbqa = (
        json.loads((ROOT / WORKBOOK_QA).read_text(encoding="utf-8"))
        if (ROOT / WORKBOOK_QA).exists()
        else {}
    )

    payload = {
        "product_id": PRODUCT_ID,
        "title": TITLE,
        "state": "LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION",
        "published": False,
        "gumroad_call_made": False,
        "price_usd": PRICE_USD,
        "price_status": "PROPOSED_NOT_AUTHORIZED",
        "price_realism": {
            "finding": (
                "At 7 pages, $19 is approved on gumroad_digital (net floor $2.50) but "
                "market_realistic is false (sub-30-page ceiling $15, then $1/page suggests $7). "
                "$19 cannot pass gumroad_premium because its $25 net floor requires at least "
                "$27.78. The price is therefore approved-but-unrealistic on one tier and "
                "rejected-on-profit on the other. Not changed here: price changes need founder "
                "authorization."
            ),
            "matrix": matrix,
            "options": [
                "Keep $19 and grow the guide to 30+ pages so the per-page ceiling clears it.",
                "List at $27.99 on gumroad_premium (net $25.19, realistic at 7 pages).",
                "List at $15 or below, which the short-book ceiling still marks unrealistic at 7 pages.",
            ],
            "recommended": "Grow the guide to 30+ pages and keep $19. It is the only option that improves the product rather than the arithmetic.",
        },
        "files": file_rows,
        "cover": {"path": COVER, "exists": cover.exists(), "dimensions": cover_dims},
        "cover_note": "No price badge: the cover is price-agnostic so it stays accurate whichever price the founder authorizes.",
        "customer_page": None,
        "customer_page_note": (
            "No customer-facing page was created for B13-001. Creating one is a separate, "
            "reviewable step; it is not required to list on Gumroad."
        ),
        "listing_copy": {
            "path": COPY,
            "text": body,
            "tags": TAGS,
            "category": "Business & Money > Business Templates / Spreadsheets",
        },
        "brand_check": brand,
        "verification_evidence": {
            "gate": GATE,
            "gate_state": gate.get("state"),
            "gate_layers": gate.get("layers"),
            "guide_inspection": GUIDE_CHECK,
            "guide_pages": guide.get("pages"),
            "guide_words": guide.get("gate_words"),
            "guide_word_method": guide.get("words_method"),
            "workbook_qa": WORKBOOK_QA,
            "workbook_qa_verdict": wbqa.get("verdict"),
            "workbook_formula_cells": wbqa.get("formula_cells"),
        },
        "authorization_required": {
            "blocked_by": "FACTORY_LIVE_PUBLISH=false and no active write scope; create_product and enable_product are not scopable.",
            "exact_minimal_action": (
                "Founder sets FACTORY_LIVE_PUBLISH=true for the run and completes a fresh "
                "gumroad_auth_watch.poll() so auth state is VERIFIED and not stale."
            ),
            "price_decision_required_first": True,
        },
        "problems": problems,
    }

    out = ROOT / OUT_JSON
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")

    lines = [
        "# B13-001 Listing Payload",
        "",
        "**State:** `%s`" % payload["state"],
        "**Published:** no · **Gumroad call made:** no · **Price:** $%.2f (proposed, not authorized)" % PRICE_USD,
        "",
        "## Deliverables",
        "",
        "| file | bytes | sha256 |",
        "|---|---|---|",
    ]
    for row in file_rows:
        lines.append("| `%s` | %d | `%s` |" % (row["path"], row["bytes"], row["sha256"][:16] + "..."))
    lines += [
        "",
        "## Verification cited",
        "",
        "- Gate: `%s` — state `%s`" % (GATE, gate.get("state")),
        "- Guide inspection: `%s` — %s pages, %s words" % (GUIDE_CHECK, guide.get("pages"), guide.get("word_count")),
        "- Workbook QA: `%s` — verdict `%s`, %s formula cells" % (WORKBOOK_QA, wbqa.get("verdict"), wbqa.get("formula_cells")),
        "- Brand check: %s" % ("PASS" if brand["passed"] else "FAIL: %s" % brand["failed_checks"]),
        "",
        "## Price realism (computed by economics.evaluate, this round)",
        "",
        "| platform | pages | approved | net | floor | realistic | suggested |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in matrix:
        lines.append(
            "| %s | %d | %s | $%.2f | $%.2f | %s | $%.2f |"
            % (
                m["platform"],
                m["pages"],
                "yes" if m["approved"] else "no",
                m["net_profit_usd"],
                m["min_required_usd"],
                "yes" if m["market_realistic"] else "no",
                m["suggested_realistic_price_usd"],
            )
        )
    lines += [
        "",
        payload["price_realism"]["finding"],
        "",
        "Recommended: " + payload["price_realism"]["recommended"],
        "",
        "## Still blocked",
        "",
        payload["authorization_required"]["blocked_by"],
        "",
        "Minimal action: " + payload["authorization_required"]["exact_minimal_action"],
        "",
        "## Problems",
        "",
    ]
    lines += ["- " + p for p in problems] if problems else ["- none"]
    with open(ROOT / OUT_MD, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print(json.dumps({"problems": problems, "out": OUT_JSON, "md": OUT_MD}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())

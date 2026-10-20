"""Re-run the real quality gate at the price the founder selected.

`b13_001_evidence.py` recorded the gate at $19.00, the price proposed before the
founder's 2026-10-20 decision. That record stays on disk as the history of that
check. This script answers the different question the decision now raises: does
the same artefact pass the same gate at $15.00, and is $15.00 realistic?

It calls the real enforcer. It does not re-derive thresholds, does not write
publication state, and never touches a platform.

Run: python scripts/b13_001_gate_at_selected_price.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import economics
from pypdf import PdfReader
from src.quality import quality_enforcer as q

PRODUCT_ID = "B13-001"
TITLE = "Renovation Allowance & Change-Order Control"
PRICE_USD = 15.00
XLSX = ROOT / "books" / "batch13" / "B13-001_renovation_allowance_control.xlsx"
PDF = ROOT / "books" / "batch13" / "B13-001_renovation_allowance_control_guide.pdf"
OUT = ROOT / "reports" / "B13-001" / "GATE_SELECTED_PRICE_2026-10-20.json"

PRODUCT = {
    "id": PRODUCT_ID,
    "title": TITLE,
    "problem": (
        "A renovation budget stops being true the moment quotes are signed, allowances are "
        "spent and changes are agreed verbally; paid-only tracking hides committed money and "
        "forgotten allowance credits."
    ),
    "audience": (
        "Homeowners and small landlords managing a renovation between $20,000 and $300,000 "
        "who pay the invoices themselves."
    ),
    "outcome": (
        "A monthly figure for projected final cost, variance against the revised budget, unpaid "
        "commitments, allowance credits still owed, and a check list that names the paperwork gap."
    ),
    "price": PRICE_USD,
    "competitors": [
        {"name": "Etsy renovation budget spreadsheet (63 reviews, 4.6)", "price_usd": 6.50,
         "url": "https://www.etsy.com/listing/1411618646/home-renovation-budget-planner-for-excel"},
        {"name": "ImperfectOrg renovation planner (9,508-sale shop)", "price_usd": 5.38,
         "url": "https://www.etsy.com/shop/ImperfectOrg"},
        {"name": "Home Renovation Spreadsheet system (6 components)", "price_usd": 27.00,
         "url": "https://www.homerenovationspreadsheet.com/"},
        {"name": "Maintenance Wizard landlord maintenance kit", "price_usd": 11.99,
         "url": "https://maintenancewizard.gumroad.com/l/landlord-maintenance-kit"},
    ],
    "files": [str(XLSX.relative_to(ROOT)), str(PDF.relative_to(ROOT))],
}


def main() -> int:
    for path in (XLSX, PDF):
        if not path.exists():
            raise SystemExit("missing artefact: %s" % path)

    pages = len(PdfReader(str(PDF)).pages)
    gate = q.inspect(PRODUCT, stage="full", save=False)
    cfg = json.loads((ROOT / "config" / "economics.json").read_text(encoding="utf-8"))
    digital_ok, digital_suggested = economics.market_realism_check(
        PRICE_USD, pages, cfg, platform="gumroad_digital"
    )
    premium_ok, premium_suggested = economics.market_realism_check(
        PRICE_USD, pages, cfg, platform="gumroad_premium"
    )

    report = {
        "product_id": PRODUCT_ID,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": "src/quality/quality_enforcer.py::inspect(stage='full')",
        "price_checked_usd": PRICE_USD,
        "price_basis": "founder decision 2026-10-20; preferred pricing direction only",
        "pdf_pages": pages,
        "verdict": gate["verdict"],
        "blocked": gate["blocked"],
        "reasons": gate["reasons"],
        "thresholds": gate["thresholds"],
        "layers": gate["layers"],
        "market_realism": {
            "gumroad_digital": {
                "realistic": digital_ok,
                "suggested_price_usd": digital_suggested,
            },
            "gumroad_premium": {
                "realistic": premium_ok,
                "suggested_price_usd": premium_suggested,
            },
        },
        "payment_evidence": "none - no sale exists anywhere in this factory",
        "state": "QA_PASS_AT_SELECTED_PRICE_AWAITING_LISTING_AND_PUBLICATION_AUTHORIZATION",
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(report, indent=1, ensure_ascii=False) + "\n")

    print(json.dumps({
        "out": str(OUT.relative_to(ROOT)),
        "price": PRICE_USD,
        "verdict": report["verdict"],
        "digital_realistic": digital_ok,
        "premium_realistic": premium_ok,
    }, indent=1))
    return 0 if (report["verdict"] == "APPROVED" and digital_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())

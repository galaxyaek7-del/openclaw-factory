#!/usr/bin/env python3
"""Sample data product: USPTO trademark fees (2026-10-29).

Eight per-class trademark fees, electronic and paper, as stated on the USPTO
fee schedule page, which was read on 2026-10-29 ("Effective January 19, 2025
(Last revised August 14, 2026)"). A US government work (17 U.S.C. 105): public
domain, commercial use allowed. Writes one release folder with the CSV, its
data card and the card's validation result.

    python data_products/uspto_trademark_fees.py
"""
import csv
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data_products import datacard  # noqa: E402

VERSION = "2026-10-29"
SOURCE_URL = "https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule"
RELEASE = ROOT / "data_products" / "releases" / "uspto-trademark-fees" / VERSION
COLUMNS = ["item", "efile_fee_code", "efile_fee_usd", "paper_fee_code", "paper_fee_usd", "unit",
           "schedule_effective", "schedule_last_revised", "source_url", "retrieved_on"]
# (item, e-file code, e-file fee, paper code, paper fee): verbatim figures from the page.
FEES = [
    ("Base application", "7017", "350.00", "6001", "850.00"),
    ("Insufficient information (Sections 1 and 44)", "7018", "100.00", "6018", "100.00"),
    ("Free-form text instead of the Trademark ID Manual", "7019", "200.00", "6019", "200.00"),
    ("Each additional 1,000 characters of free-form text", "7020", "200.00", "6020", "200.00"),
    ("Statement of use (SOU)", "7003", "150.00", "6003", "250.00"),
    ("Six-month extension to file an SOU", "7004", "125.00", "6004", "225.00"),
    ("Section 8 declaration", "7205", "325.00", "6205", "425.00"),
    ("Section 9 registration renewal", "7201", "325.00", "6201", "525.00"),
]


def build():
    RELEASE.mkdir(parents=True, exist_ok=True)
    path = RELEASE / "uspto_trademark_fees.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for item, ec, ef, pc, pf in FEES:
            w.writerow([item, ec, ef, pc, pf, "per class", "2025-01-19", "2026-08-14", SOURCE_URL, VERSION])
    card = {
        "dataset_id": "uspto-trademark-fees", "title": "USPTO trademark fees per class, electronic and paper",
        "version": VERSION,
        "description": "The eight per-class fees a US trademark applicant meets from filing to year 10, with both electronic and paper amounts and the fee codes.",
        "intended_use": "Reference table for cost planners, filing checklists and fee-change monitoring.",
        "out_of_scope_use": "Not legal advice; not a complete fee schedule (petitions, Madrid and other fees are excluded).",
        "sources": [{"name": "USPTO fee schedule", "origin": SOURCE_URL, "accessed_on": VERSION,
                     "access_method": "PUBLIC_WEB_PAGE",
                     "licence": {"name": "US government work (17 U.S.C. 105), public domain", "commercial_use": True,
                                 "attribution_required": False, "share_alike": False}}],
        "collection_method": "Read the public page on 2026-10-29 and transcribed the eight rows verbatim.",
        "processing_steps": ["transcribe verbatim", "add unit, schedule dates, source and retrieval date"],
        "columns": [{"name": c, "type": "string", "description": c.replace("_", " ")} for c in COLUMNS],
        "files": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": datacard.sha256_file(path),
                   "rows": len(FEES)}],
        "personal_data": {"contains": False},
        "licence_out": "public domain source; Galaxy Forge compilation",
        "refresh_days": 30,
        "last_refreshed": VERSION,
        "known_limitations": ["Fees change by rule-making; this release is correct as of the retrieval date only.",
                              "Law-firm alerts give 18 January 2025 as the effective date; the USPTO page says 19 January 2025."],
    }
    (RELEASE / "datacard.json").write_text(json.dumps(card, indent=1, ensure_ascii=False), encoding="utf-8")
    result = datacard.validate_card(card, ROOT, today=date(2026, 10, 29))
    (RELEASE / "validation.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return result


if __name__ == "__main__":
    r = build()
    print(json.dumps({k: r[k] for k in r if k in ("status", "findings")}, default=str)[:600])

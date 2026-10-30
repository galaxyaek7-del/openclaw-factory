#!/usr/bin/env python3
"""Sample data product: European Accessibility Act penalty register (2026-10-29).

The EAA (Directive (EU) 2019/882, applicable since 28 June 2025) leaves
penalties to each member state. Published comparisons disagree: for Germany a
widely cited vendor table gives up to EUR 500,000, while the German
implementing act (BFSG s. 37(2)) sets EUR 100,000 and EUR 10,000. This
register keeps each figure next to its source and a verification status:

  VERIFIED_OFFICIAL_TEXT  read in the national legal text on the release date
  SECONDARY_UNVERIFIED    taken from a secondary source, not yet checked
                          against the statute (shown so the gap is visible)

Sample scope: two countries verified (DE, IE), four carried as secondary
claims (FR, NL, AT, ES). Only facts (amounts, section numbers, authority
names) are recorded; no legal text is reproduced. Not legal advice.

    python data_products/eaa_penalty_register.py
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data_products import datacard  # noqa: E402

VERSION = "2026-10-29"
RELEASE = ROOT / "data_products" / "releases" / "eaa-penalty-register" / VERSION
BFSG = "https://www.gesetze-im-internet.de/bfsg/__37.html"
IE_SI = "https://www.irishstatutebook.ie/eli/2023/si/636/made/en/print"
DEQUE = "https://www.deque.com/european-accessibility-act-eaa-compliance/country-compliance-data/"
COLUMNS = ["country", "instrument", "provision", "offence_scope", "max_fine_eur", "imprisonment",
           "enforcing_bodies", "status", "source_url", "retrieved_on", "note"]
ROWS = [
    ("DE", "Barrierefreiheitsstaerkungsgesetz (BFSG)", "s. 37(2)",
     "s. 37(1) Nos 1, 7, 8, 9, 10: incl. offering or providing a non-compliant service (No 8)",
     "100000", "none in this provision", "UNKNOWN (not read for this release)", "VERIFIED_OFFICIAL_TEXT", BFSG,
     VERSION, "Secondary table gives EUR 500,000 for DE and cites BFSG plus the Medienstaatsvertrag; "
              "which provision yields 500,000 is UNKNOWN"),
    ("DE", "Barrierefreiheitsstaerkungsgesetz (BFSG)", "s. 37(2)", "s. 37(1) Nos 2-6: information, marking, "
     "documentation duties", "10000", "none in this provision", "UNKNOWN (not read for this release)",
     "VERIFIED_OFFICIAL_TEXT", BFSG, VERSION, ""),
    ("IE", "S.I. No. 636/2023", "Reg. 32", "offences under the Regulations, conviction on indictment", "60000",
     "up to 18 months", "CCPC (market surveillance, products); ComReg, Central Bank, Coimisiun na Mean and others "
     "prosecute offences within their functions (Reg. 35)", "VERIFIED_OFFICIAL_TEXT", IE_SI, VERSION,
     "Summary conviction: class A fine or up to 6 months (class A amount not re-read for this release)"),
    ("FR", "(several; per secondary source)", "", "", "300000", "", "DGCCRF, ARCOM, AFM, Banque de France, ARCEP",
     "SECONDARY_UNVERIFIED", DEQUE, VERSION, "another secondary source gives 50,000-75,000"),
    ("NL", "(several; per secondary source)", "", "", "103000", "", "AFM, ACM, ILT", "SECONDARY_UNVERIFIED",
     DEQUE, VERSION, ""),
    ("AT", "Barrierefreiheitsgesetz (BaFG), per secondary source", "", "", "80000", "",
     "Federal Office for Social Affairs and Disability", "SECONDARY_UNVERIFIED", DEQUE, VERSION, ""),
    ("ES", "Law 11/2023 and others, per secondary source", "", "", "1000000", "",
     "Autonomous communities, Ceuta, Melilla", "SECONDARY_UNVERIFIED", DEQUE, VERSION, ""),
]


def build():
    RELEASE.mkdir(parents=True, exist_ok=True)
    path = RELEASE / "eaa_penalty_register.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(ROWS)
    facts = {"name": "Facts only (amounts, section numbers, authority names); no text reproduced",
             "commercial_use": True, "attribution_required": False, "share_alike": False}
    card = {
        "dataset_id": "eaa-penalty-register", "title": "European Accessibility Act penalties by member state, with verification status",
        "version": VERSION,
        "description": "Maximum fines and imprisonment terms under national EAA transpositions, each figure tagged "
                       "as read in the official text or carried from a secondary source.",
        "intended_use": "Exposure briefings for online sellers serving EU consumers; checking vendor claims.",
        "out_of_scope_use": "Not legal advice; not a complete list of member states; not a statement of what a "
                            "regulator would actually impose.",
        "sources": [
            {"name": "BFSG s. 37 (gesetze-im-internet.de)", "origin": BFSG, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE",
             "licence": {"name": "German official work (s. 5 UrhG), public domain", "commercial_use": True,
                         "attribution_required": False, "share_alike": False}},
            {"name": "S.I. No. 636/2023 (irishstatutebook.ie)", "origin": IE_SI, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Deque EAA country-by-country table (secondary)", "origin": DEQUE, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
        ],
        "attribution": "Secondary figures: Deque Systems, EAA country-by-country compliance data (read 2026-10-29).",
        "collection_method": "Read the German and Irish legal texts on 2026-10-29 and recorded the penalty "
                             "provisions; carried four other countries from a secondary table, marked unverified.",
        "processing_steps": ["record amounts and section numbers", "tag verification status", "note conflicts"],
        "columns": [{"name": c, "type": "string", "description": c.replace("_", " ")} for c in COLUMNS],
        "files": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": datacard.sha256_file(path),
                   "rows": len(ROWS)}],
        "personal_data": {"contains": False},
        "licence_out": "Galaxy Forge compilation of facts",
        "refresh_days": 90,
        "last_refreshed": VERSION,
        "known_limitations": [
            "Only DE and IE are verified against the legal text; FR, NL, AT, ES are secondary claims.",
            "The source of the EUR 500,000 German figure in secondary tables is UNKNOWN.",
            "Maximum statutory penalties say nothing about enforcement practice.",
        ],
    }
    (RELEASE / "datacard.json").write_text(json.dumps(card, indent=1, ensure_ascii=False), encoding="utf-8")
    result = datacard.validate_card(card, ROOT, today=date(2026, 10, 29))
    (RELEASE / "validation.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return result


if __name__ == "__main__":
    r = build()
    print(json.dumps({k: r[k] for k in r if k in ("status", "findings")}, default=str)[:600])

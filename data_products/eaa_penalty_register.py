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

VERSION = "2026-10-30"  # 2026-10-29: DE, IE; 2026-10-30: AT verified, NL instrument identified
RELEASE = ROOT / "data_products" / "releases" / "eaa-penalty-register" / VERSION
READ_1029 = "2026-10-29"  # DE, IE and the secondary table were read on this date
BFSG = "https://www.gesetze-im-internet.de/bfsg/__37.html"
IE_SI = "https://www.irishstatutebook.ie/eli/2023/si/636/made/en/print"
AT_BAFG = "https://ris.bka.gv.at/eli/bgbl/i/2023/76/P36/NOR40254396"
NL_ACT = "https://wetten.overheid.nl/BWBR0049571/2025-06-28/0"
NL_STB = "https://zoek.officielebekendmakingen.nl/stb-2024-87.html"
FR_R4514 = "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000048180406/"
ES_L11 = "https://www.boe.es/buscar/act.php?id=BOE-A-2023-11022"
ES_RDL1 = "https://www.boe.es/buscar/act.php?id=BOE-A-2013-12632"
DEQUE = "https://www.deque.com/european-accessibility-act-eaa-compliance/country-compliance-data/"
COLUMNS = ["country", "instrument", "provision", "offence_scope", "max_fine_eur", "imprisonment",
           "enforcing_bodies", "status", "source_url", "retrieved_on", "note"]
ROWS = [
    ("DE", "Barrierefreiheitsstaerkungsgesetz (BFSG)", "s. 37(2)",
     "s. 37(1) Nos 1, 7, 8, 9, 10: incl. offering or providing a non-compliant service (No 8)",
     "100000", "none in this provision", "UNKNOWN (not read for this release)", "VERIFIED_OFFICIAL_TEXT", BFSG,
     READ_1029, "Secondary table gives EUR 500,000 for DE and cites BFSG plus the Medienstaatsvertrag; "
              "which provision yields 500,000 is UNKNOWN"),
    ("DE", "Barrierefreiheitsstaerkungsgesetz (BFSG)", "s. 37(2)", "s. 37(1) Nos 2-6: information, marking, "
     "documentation duties", "10000", "none in this provision", "UNKNOWN (not read for this release)",
     "VERIFIED_OFFICIAL_TEXT", BFSG, READ_1029, ""),
    ("IE", "S.I. No. 636/2023", "Reg. 32", "offences under the Regulations, conviction on indictment", "60000",
     "up to 18 months", "CCPC (market surveillance, products); ComReg, Central Bank, Coimisiun na Mean and others "
     "prosecute offences within their functions (Reg. 35)", "VERIFIED_OFFICIAL_TEXT", IE_SI, READ_1029,
     "Summary conviction: class A fine or up to 6 months (class A amount not re-read for this release)"),
    ("FR", "Code de la consommation (Decret 2023-931)", "art. R.451-4 I", "listed product breaches: CE marking, "
     "conformity assessment, manufacturer, importer and distributor duties", "", "none (contravention fine)",
     "DGCCRF with ARCOM, ARCEP, Banque de France, ACPR, AMF (services)", "VERIFIED_OFFICIAL_TEXT", FR_R4514, VERSION,
     "fine of a 5th-class contravention, amount set by the Code penal (not re-read); whether service breaches "
     "fall under this article is UNKNOWN; secondary tables give EUR 300,000 and EUR 50,000-75,000"),
    ("NL", "Implementatiewet toegankelijkheidsvoorschriften (Stb. 2024, 87)", "Warenwet (products); Whc art. 8a "
     "(services)", "accessibility breaches by product makers/sellers and by service providers", "",
     "none (administrative fine)", "RDI (products); ACM and others for services", "VERIFIED_OFFICIAL_TEXT", NL_STB,
     VERSION, "maximum is the 5th fine category of Criminal Code art. 23; its euro value is indexed and was not "
              "re-read (the secondary table's EUR 103,000 is that category's value in an earlier year)"),
    ("AT", "Barrierefreiheitsgesetz (BaFG)", "s. 36(1)", "s. 36(1) offences, incl. placing a non-compliant "
     "product on the market (Nos 1-2)", "80000", "none (administrative fine)",
     "Sozialministeriumservice (penalty authority and market surveillance)", "VERIFIED_OFFICIAL_TEXT", AT_BAFG,
     VERSION, "micro, small and medium enterprises: up to EUR 50,000; matches the secondary table's EUR 80,000"),
    ("AT", "Barrierefreiheitsgesetz (BaFG)", "s. 36(2)", "s. 36(2) offences, incl. not preparing the required "
     "information about services (s. 14(2) with Annex 3)", "40000", "none (administrative fine)",
     "Sozialministeriumservice", "VERIFIED_OFFICIAL_TEXT", AT_BAFG, VERSION,
     "micro, small and medium enterprises: up to EUR 25,000"),
    ("AT", "Barrierefreiheitsgesetz (BaFG)", "s. 36(3)", "s. 36(3) offences", "16000", "none (administrative fine)",
     "Sozialministeriumservice", "VERIFIED_OFFICIAL_TEXT", AT_BAFG, VERSION,
     "the reduced amount for SMEs under s. 36(3), if any, was not read"),
    ("ES", "Ley 11/2023", "art. 30", "breaches of Title I (accessibility of products and services)", "",
     "", "per sectoral legislation", "VERIFIED_OFFICIAL_TEXT", ES_L11, VERSION,
     "sanctions follow the sectoral legislation; where it is silent, Title III of RDL 1/2013 applies (next row)"),
    ("ES", "Real Decreto Legislativo 1/2013 (fallback)", "art. 83", "fallback regime for accessibility breaches",
     "1000000", "none (administrative fine)", "State or autonomous-community authorities (art. 105 for the State)",
     "VERIFIED_OFFICIAL_TEXT", ES_RDL1, VERSION,
     "minor up to EUR 30,000, serious up to EUR 90,000, very serious up to EUR 1,000,000 (minimum EUR 301); "
     "matches the secondary EUR 1,000,000 only as the fallback ceiling"),
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
            {"name": "BFSG s. 37 (gesetze-im-internet.de)", "origin": BFSG, "accessed_on": READ_1029,
             "access_method": "PUBLIC_WEB_PAGE",
             "licence": {"name": "German official work (s. 5 UrhG), public domain", "commercial_use": True,
                         "attribution_required": False, "share_alike": False}},
            {"name": "S.I. No. 636/2023 (irishstatutebook.ie)", "origin": IE_SI, "accessed_on": READ_1029,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "BaFG s. 36 (ris.bka.gv.at)", "origin": AT_BAFG, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Code de la consommation art. R.451-4 (legifrance.gouv.fr)", "origin": FR_R4514,
             "accessed_on": VERSION, "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Ley 11/2023 and RDL 1/2013 (boe.es)", "origin": ES_L11, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Staatsblad 2024, 87 (officielebekendmakingen.nl)", "origin": NL_STB, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Deque EAA country-by-country table (secondary)", "origin": DEQUE, "accessed_on": READ_1029,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
        ],
        "attribution": "Secondary figures: Deque Systems, EAA country-by-country compliance data (read 2026-10-29).",
        "collection_method": "Read the German and Irish legal texts on 2026-10-29 and the Austrian on 2026-10-30, "
                             "recorded the penalty provisions; and the French and Spanish on 2026-10-30; the Dutch on 2026-10-30.",
        "processing_steps": ["record amounts and section numbers", "tag verification status", "note conflicts"],
        "columns": [{"name": c, "type": "string", "description": c.replace("_", " ")} for c in COLUMNS],
        "files": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": datacard.sha256_file(path),
                   "rows": len(ROWS)}],
        "personal_data": {"contains": False},
        "licence_out": "Galaxy Forge compilation of facts",
        "refresh_days": 90,
        "last_refreshed": VERSION,
        "known_limitations": [
            "All six countries are tied to the legal text; FR (contravention amount, service scope) and NL (indexed euro value of the 5th fine category) are partly verified.",
            "The source of the EUR 500,000 German figure in secondary tables is UNKNOWN.",
            "Maximum statutory penalties say nothing about enforcement practice.",
        ],
    }
    (RELEASE / "datacard.json").write_text(json.dumps(card, indent=1, ensure_ascii=False), encoding="utf-8")
    result = datacard.validate_card(card, ROOT, today=date(2026, 10, 30))
    (RELEASE / "validation.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return result


if __name__ == "__main__":
    r = build()
    print(json.dumps({k: r[k] for k in r if k in ("status", "findings")}, default=str)[:600])

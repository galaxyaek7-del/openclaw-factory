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

Scope (release 2026-10-31): ten countries, each tied to its own legal text
(DE, IE, FR, NL, IT, SE, PL, AT, ES, DK). Earlier releases are kept unchanged.
Only facts (amounts, section numbers, authority names) are recorded; no legal
text is reproduced. Not legal advice.

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

VERSION = "2026-10-31"  # 2026-10-29: DE, IE; 2026-10-30: AT..PL; 2026-10-31: FR/NL amounts, DK
RELEASE = ROOT / "data_products" / "releases" / "eaa-penalty-register" / VERSION
READ_1029 = "2026-10-29"  # DE, IE and the secondary table were read on this date
READ_1030 = "2026-10-30"  # AT, FR R.451-4, NL instrument, IT, SE, PL, ES
BFSG = "https://www.gesetze-im-internet.de/bfsg/__37.html"
IE_SI = "https://www.irishstatutebook.ie/eli/2023/si/636/made/en/print"
AT_BAFG = "https://ris.bka.gv.at/eli/bgbl/i/2023/76/P36/NOR40254396"
NL_ACT = "https://wetten.overheid.nl/BWBR0049571/2025-06-28/0"
NL_STB = "https://zoek.officielebekendmakingen.nl/stb-2024-87.html"
IT_GU = "https://www.gazzettaufficiale.it/eli/id/2022/07/01/22G00089/SG"
IT_AGID = "https://accessibilita.agid.gov.it/domande-frequenti/"
SE_SFS = "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2023254-om-vissa-produkters-och-tjansters_sfs-2023-254"
PL_DU = "https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20240000731"
FR_R4514 = "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000048180406/"
FR_CP13113 = "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006417258"
FR_CP13141 = "https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006070719/LEGISCTA000006181735/"
NL_STB2025 = "https://zoek.officielebekendmakingen.nl/stb-2025-401.html"
NL_SR23 = "https://wetten.overheid.nl/BWBR0001854/2026-01-01/0/BoekEerste/TiteldeelII/Artikel23"
DK_LOV = "https://www.retsinformation.dk/eli/lta/2022/801"
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
     "DGCCRF with ARCOM, ARCEP, Banque de France, ACPR, AMF (services)", "VERIFIED_OFFICIAL_TEXT", FR_R4514, READ_1030,
     "fine of a 5th-class contravention (next two rows for the amount); whether service breaches "
     "fall under this article is UNKNOWN; secondary tables give EUR 300,000 and EUR 50,000-75,000"),
    ("FR", "Code penal", "art. 131-13 5", "amount of a 5th-class contravention (natural persons)", "1500",
     "none", "", "VERIFIED_OFFICIAL_TEXT", FR_CP13113, VERSION,
     "up to EUR 3,000 for a repeat offence where the regulation provides for it (not established for R.451-4)"),
    ("FR", "Code penal", "art. 131-41", "legal persons: five times the natural-person maximum for a contravention",
     "7500", "none", "", "VERIFIED_OFFICIAL_TEXT", FR_CP13141, VERSION,
     "EUR 1,500 x 5; EUR 15,000 only where a repeat-offence increase applies"),
    ("NL", "Implementatiewet toegankelijkheidsvoorschriften (Stb. 2024, 87)", "Warenwet (products); Whc art. 8a "
     "(services)", "accessibility breaches by product makers/sellers and by service providers", "",
     "none (administrative fine)", "RDI (products); ACM and others for services", "VERIFIED_OFFICIAL_TEXT", NL_STB,
     READ_1030, "maximum is the 5th fine category of Criminal Code art. 23 (next row for its 2026 amount)"),
    ("NL", "Wetboek van Strafrecht art. 23(4), amended by Stb. 2025, 401", "5th fine category",
     "euro value of the 5th category from 1 January 2026", "110000", "none (administrative fine)", "",
     "VERIFIED_OFFICIAL_TEXT", NL_STB2025, VERSION,
     "EUR 103,000 until 31 December 2025 (the secondary tables' figure); art. 23(7), next-higher category for legal "
     "persons, is a criminal-law rule and is not applied to this administrative fine; read in " + NL_SR23),
    ("IT", "D.Lgs. 82/2022", "art. 24(1)", "breach of the accessibility requirements and economic operators' duties "
     "(arts 3, 6, 8, 9, 10, 12)", "40000", "none (administrative fine)", "AgID (services); MIMIT (products)",
     "VERIFIED_OFFICIAL_TEXT", IT_GU, READ_1030,
     "minimum EUR 5,000; providers with average turnover above EUR 500 million: up to 5% of turnover "
     "(L. 4/2004 art. 9(1-bis), confirmed by AgID: " + IT_AGID + ")"),
    ("IT", "D.Lgs. 82/2022", "art. 24(2)-(3)", "not complying with the authority's measures, or not cooperating",
     "30000", "none (administrative fine)", "AgID (services); MIMIT (products)", "VERIFIED_OFFICIAL_TEXT", IT_GU,
     READ_1030, "minimum EUR 2,500"),
    ("SE", "Lag (2023:254)", "s. 37 and 39", "breaches of the listed duties (ss. 6, 8, 11-13, 15-17, 19-26)", "",
     "none (sanction fee)", "market surveillance or supervisory authority named by the government (s. 30)",
     "VERIFIED_OFFICIAL_TEXT", SE_SFS, READ_1030,
     "sanction fee SEK 10,000 to SEK 10,000,000 (statute amount in kronor, not converted); may be reduced"),
    ("PL", "Ustawa z 26 kwietnia 2024 r. (Dz. U. 2024 poz. 731)", "penalty article (number not read)",
     "non-compliant products or services and unmet duties found in a decision under art. 56(1) or 65(1)", "",
     "none (administrative penalty)", "President of PFRON or the competent market surveillance authority",
     "VERIFIED_OFFICIAL_TEXT", PL_DU, READ_1030,
     "up to 10 times the previous year's average monthly salary in the national economy, capped at 10% of the "
     "previous year's turnover"),
    ("AT", "Barrierefreiheitsgesetz (BaFG)", "s. 36(1)", "s. 36(1) offences, incl. placing a non-compliant "
     "product on the market (Nos 1-2)", "80000", "none (administrative fine)",
     "Sozialministeriumservice (penalty authority and market surveillance)", "VERIFIED_OFFICIAL_TEXT", AT_BAFG,
     READ_1030, "micro, small and medium enterprises: up to EUR 50,000; matches the secondary table's EUR 80,000"),
    ("AT", "Barrierefreiheitsgesetz (BaFG)", "s. 36(2)", "s. 36(2) offences, incl. not preparing the required "
     "information about services (s. 14(2) with Annex 3)", "40000", "none (administrative fine)",
     "Sozialministeriumservice", "VERIFIED_OFFICIAL_TEXT", AT_BAFG, READ_1030,
     "micro, small and medium enterprises: up to EUR 25,000"),
    ("AT", "Barrierefreiheitsgesetz (BaFG)", "s. 36(3)", "s. 36(3) offences", "16000", "none (administrative fine)",
     "Sozialministeriumservice", "VERIFIED_OFFICIAL_TEXT", AT_BAFG, READ_1030,
     "the reduced amount for SMEs under s. 36(3), if any, was not read"),
    ("ES", "Ley 11/2023", "art. 30", "breaches of Title I (accessibility of products and services)", "",
     "", "per sectoral legislation", "VERIFIED_OFFICIAL_TEXT", ES_L11, READ_1030,
     "sanctions follow the sectoral legislation; where it is silent, Title III of RDL 1/2013 applies (next row)"),
    ("ES", "Real Decreto Legislativo 1/2013 (fallback)", "art. 83", "fallback regime for accessibility breaches",
     "1000000", "none (administrative fine)", "State or autonomous-community authorities (art. 105 for the State)",
     "VERIFIED_OFFICIAL_TEXT", ES_RDL1, READ_1030,
     "minor up to EUR 30,000, serious up to EUR 90,000, very serious up to EUR 1,000,000 (minimum EUR 301); "
     "matches the secondary EUR 1,000,000 only as the fallback ceiling"),
    ("DK", "Lov nr. 801 af 7. juni 2022 (tilgaengelighedskrav for produkter og tjenester)", "s. 57",
     "breaches of the accessibility requirements and operators' duties (s. 57(1) Nos 1-7)", "",
     "none stated (fine only)", "Sikkerhedsstyrelsen and other control authorities", "VERIFIED_OFFICIAL_TEXT",
     DK_LOV, VERSION, "fine (boede) with no statutory maximum: the court sets the amount; companies are liable under "
     "Straffeloven chapter 5 (s. 57(3)); read in the 2022 text as published, a 2024 amendment (Lov nr. 637) was not "
     "read"),
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
        "version": READ_1030,
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
            {"name": "BaFG s. 36 (ris.bka.gv.at)", "origin": AT_BAFG, "accessed_on": READ_1030,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Code de la consommation art. R.451-4 (legifrance.gouv.fr)", "origin": FR_R4514,
             "accessed_on": READ_1030, "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Ley 11/2023 and RDL 1/2013 (boe.es)", "origin": ES_L11, "accessed_on": READ_1030,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Staatsblad 2024, 87 (officielebekendmakingen.nl)", "origin": NL_STB, "accessed_on": READ_1030,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "D.Lgs. 82/2022 (gazzettaufficiale.it) and AgID FAQ", "origin": IT_GU, "accessed_on": READ_1030,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "SFS 2023:254 (riksdagen.se)", "origin": SE_SFS, "accessed_on": READ_1030,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Dz. U. 2024 poz. 731 (isap.sejm.gov.pl)", "origin": PL_DU, "accessed_on": READ_1030,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Code penal arts 131-13 and 131-41 (legifrance.gouv.fr)", "origin": FR_CP13113, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Staatsblad 2025, 401 and Wetboek van Strafrecht art. 23", "origin": NL_STB2025, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Lov nr. 801 af 7. juni 2022 (retsinformation.dk)", "origin": DK_LOV, "accessed_on": VERSION,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
            {"name": "Deque EAA country-by-country table (secondary)", "origin": DEQUE, "accessed_on": READ_1029,
             "access_method": "PUBLIC_WEB_PAGE", "licence": facts},
        ],
        "attribution": "Secondary figures: Deque Systems, EAA country-by-country compliance data (read 2026-10-29).",
        "collection_method": "Read the German and Irish legal texts on 2026-10-29 and the Austrian on 2026-10-30, "
                             "recorded the penalty provisions; and the French and Spanish on 2026-10-30; the Dutch, Italian, Swedish and Polish on 2026-10-30; the French contravention amounts, the 2026 Dutch fine category and Denmark on 2026-10-31. SE and PL amounts are not in euro; DK sets no maximum.",
        "processing_steps": ["record amounts and section numbers", "tag verification status", "note conflicts"],
        "columns": [{"name": c, "type": "string", "description": c.replace("_", " ")} for c in COLUMNS],
        "files": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": datacard.sha256_file(path),
                   "rows": len(ROWS)}],
        "personal_data": {"contains": False},
        "licence_out": "Galaxy Forge compilation of facts",
        "refresh_days": 90,
        "last_refreshed": VERSION,
        "known_limitations": [
            "All ten countries are tied to the legal text; open points: FR service scope of R.451-4, DK 2024 amendment not read, PL article number not read.",
            "Finland was searched on 2026-10-31 but its services sanctions (Act 306/2019) could not be read; not included.",
            "The source of the EUR 500,000 German figure in secondary tables is UNKNOWN.",
            "Maximum statutory penalties say nothing about enforcement practice.",
        ],
    }
    (RELEASE / "datacard.json").write_text(json.dumps(card, indent=1, ensure_ascii=False), encoding="utf-8")
    result = datacard.validate_card(card, ROOT, today=date.fromisoformat(VERSION))
    (RELEASE / "validation.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return result


if __name__ == "__main__":
    r = build()
    print(json.dumps({k: r[k] for k in r if k in ("status", "findings")}, default=str)[:600])

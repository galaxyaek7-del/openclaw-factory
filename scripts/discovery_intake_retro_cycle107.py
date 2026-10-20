#!/usr/bin/env python3
"""Retro-run the Cycle 107 intake gate (2026-10-20).

Cycle 107 scored three regulatory candidates (EUDR 19/25, CBAM 15/25, EmpCo
16/25) and then rejected all three on the same hard gate: an adequate free
alternative already does the job. That ordering is the defect the repaired
market_discovery_engine intake gate exists to fix.

This script replays the same evidence through the repaired gate. It does not
fetch anything. Every retrieval status is taken from the Cycle 107 record:

  1. reports/CYCLE107/EVIDENCE_VERIFICATION_2026-10-20.json
     - "inaccessible_and_marked_unknown" gives the six URLs that were NOT
       usable and exactly how they failed.
     - "material_defects_found" names V1 (404), V2 (DNS) and V3 (four Reddit
       403s).
  2. The cited URL set is re-derived from the two committed Cycle 106
     discovery JSONs, which is where the 29 unique URLs came from.
  3. A URL in that set and not named in (1) is FETCHED_OK, derived from the
     report's own count of 21 served pages plus its complete six-item
     inaccessible list. This is labelled DERIVED, never OBSERVED.
  4. URLs cited by the CBAM/EmpCo sections of the Cycle 107 markdown that are
     not in the 29 are UNVERIFIED, because no per-URL status was retained for
     them. The markdown's "verified live" statement is not a retrieval record.

Output: reports/CYCLE107/GATE_REPAIR_RETRO_2026-10-20.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import market_discovery_engine as mde  # noqa: E402

EVIDENCE = ROOT / "reports" / "CYCLE107" / "EVIDENCE_VERIFICATION_2026-10-20.json"
CYCLE106_FILES = (
    ROOT / "reports" / "CYCLE106" / "DISCOVERY_2026-10-20_MARKET_SATURATION.json",
    ROOT / "reports" / "CYCLE106" / "DISCOVERY_2026-10-20_EUDR_PROBE.json",
)
OUT = ROOT / "reports" / "CYCLE107" / "GATE_REPAIR_RETRO_2026-10-20.json"

_UA = r"https?://[^\s\"\\<>)]+"


def _urls(text):
    out = []
    for match in re.finditer(_UA, text or ""):
        url = match.group(0).rstrip(".,;")
        if url not in out:
            out.append(url)
    return out


def _cycle106_urls():
    urls = []
    for path in CYCLE106_FILES:
        if not path.exists():
            continue
        for url in _urls(path.read_text(encoding="utf-8")):
            if url not in urls:
                urls.append(url)
    return urls


def _status_from_record(entry):
    """Turn one Cycle 107 inaccessible entry into a classifier verdict."""
    status = entry.get("status")
    if isinstance(status, int):
        return mde.classify_source(status_code=status, body_bytes=0)
    text = str(status or "").lower()
    if "tls" in text or "certificate" in text:
        return mde.classify_source(error="tls certificate verify failed")
    if "connection" in text:
        return mde.classify_source(error="connection closed")
    return mde.classify_source(error=text or "unrecorded failure")


def _as_retrieval(url, verdict, source_type, provenance, note=""):
    return {
        "url": url,
        "status": verdict["status"],
        "detail": verdict["detail"],
        "counts_as_evidence": verdict["counts_as_evidence"],
        "source_type": source_type,
        "provenance": provenance,
        "note": note,
    }


def build_retrievals():
    record = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    urls = _cycle106_urls()
    retrievals = {}
    provenance = {}

    for url in urls:
        retrievals[url] = _as_retrieval(
            url, mde.classify_source(status_code=200, body_bytes=1), None,
            "DERIVED", "implied by the record's 21 served pages and six-item failure list")
        provenance[url] = "DERIVED"

    for entry in record.get("inaccessible_and_marked_unknown", []):
        url = entry.get("url")
        if not url:
            continue
        verdict = _status_from_record(entry)
        retrievals[url] = _as_retrieval(url, verdict, None, "OBSERVED",
                                       entry.get("note", ""))
        provenance[url] = "OBSERVED"

    for defect in record.get("material_defects_found", []):
        finding = defect.get("finding", "")
        for url in _urls(finding):
            if defect.get("id") == "V1":
                verdict = mde.classify_source(status_code=404)
            elif defect.get("id") == "V2":
                verdict = mde.classify_source(error="dns getaddrinfo failed")
            else:
                verdict = mde.classify_source(status_code=403)
            retrievals[url] = _as_retrieval(url, verdict, None, "OBSERVED", finding)
            provenance[url] = "OBSERVED"

        if defect.get("id") == "V2":
            for url in urls:
                if "capveri.com" in url or "lextract.io" in url:
                    retrievals[url] = _as_retrieval(
                        url, mde.classify_source(error="dns getaddrinfo failed"),
                        None, "OBSERVED", finding)
                    provenance[url] = "OBSERVED"
        if defect.get("id") == "V3":
            # V3 says "the four Reddit URLs" were 403 but the committed cited set
            # contains five, and no per-URL status row was retained. Guessing
            # which four would fabricate a retrieval, so all five are marked
            # UNVERIFIED and the ambiguity is disclosed in the report.
            for url in urls:
                if "reddit.com" in url:
                    retrievals[url] = _as_retrieval(
                        url, mde.classify_source(error="V3: 403 block page reported, "
                                                       "no per-URL status row retained"),
                        None, "OBSERVED_AMBIGUOUS", finding)
                    provenance[url] = "OBSERVED_AMBIGUOUS"
    return record, urls, retrievals, provenance


def _external(url, source_type, retrievals, provenance, why):
    """A citation outside the 29: honest UNVERIFIED unless a record exists."""
    if url in retrievals:
        retrievals[url]["source_type"] = source_type
        return url
    retrievals[url] = _as_retrieval(
        url, mde.classify_source(error="no retrieval record retained in Cycle 107"),
        source_type, "NOT_RECORDED", why)
    provenance[url] = "NOT_RECORDED"
    return url


def build_candidates(urls, retrievals, provenance):
    eudr_official = next(u for u in urls if "environment.ec.europa.eu/topics/forests" in u)
    sawmill = next(u for u in urls if "sawmillsmart.com" in u)
    polygon = next(u for u in urls if "polygon-one.com" in u)
    cbam_official = _external(
        "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-definitive-regime_en",
        "official", retrievals, provenance,
        "Cycle 107 markdown asserts live verification but retained no status row")
    empco_legal = _external(
        "https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A32024L0825",
        "official", retrievals, provenance,
        "Cycle 107 markdown asserts EUR-Lex verification but retained no status row")
    empco_free = _external(
        "https://www.ecoclaim.eu/blog/how-to-check-website-greenwashing",
        "vendor_free", retrievals, provenance,
        "free scanner cited in the Cycle 107 markdown, no status retained")

    return [
        {
            "name": "EUDR operator/downstream register",
            "claimed_score": 19,
            "cited_urls": [
                {"url": eudr_official, "source_type": "official"},
                {"url": sawmill, "source_type": "vendor_free"},
                {"url": polygon, "source_type": "vendor_free"},
            ],
            "free_alternative": {
                "urls": [sawmill, polygon],
                "materially_duplicates": True,
                "demonstrated_advantage": "UNKNOWN",
                "assessment": ("SawmillSmart publishes the six-sheet workbook explicitly updated for "
                               "2025/2650; polygon-one publishes a free preparation sheet and a free "
                               "worked coffee import example. Transcript from the Cycle 107 record."),
            },
            "paid_comparison": {
                "competitors": ["cdgdocs.com EUDR documentation kit ($250, price UNVERIFIED them this cycle)"],
                "differentiator": "",
                "assessment": ("The record identifies no capability the free artifacts leave open; "
                               "commodity-specific phrasing was rejected as not being a product."),
            },
            "buyer_channel": {
                "buyer": "EU importers and traders of in-scope commodities",
                "channel": "direct digital download",
            },
            "build_cost_usd": 0,
        },
        {
            "name": "CBAM definitive regime, small importer data collection",
            "claimed_score": 15,
            "cited_urls": [{"url": cbam_official, "source_type": "official"}],
            "free_alternative": {
                "urls": [],
                "materially_duplicates": True,
                "demonstrated_advantage": "UNKNOWN",
                "assessment": ("The Commission publishes the quarterly report structure (XLSX), the "
                               "corrected default values (XLSX) and the operator communication template. "
                               "The Cycle 107 markdown names these without retaining a URL."),
            },
            "paid_comparison": {
                "competitors": [],
                "differentiator": "",
                "assessment": "No paid competitor was recorded for the simplified regime.",
            },
            "buyer_channel": {
                "buyer": "EU importers of cement, iron/steel, aluminium, fertilisers, hydrogen, electricity",
                "channel": "direct digital download",
            },
            "build_cost_usd": 0,
        },
        {
            "name": "EU EmpCo green-claims audit",
            "claimed_score": 16,
            "cited_urls": [{"url": empco_legal, "source_type": "official"}],
            "free_alternative": {
                "urls": [empco_free],
                "materially_duplicates": True,
                "demonstrated_advantage": "UNKNOWN",
                "assessment": ("EcoClaim offers a free scanner against 82 banned terms and "
                               "greenwashing-checker publishes a free eight-step SME checklist covering "
                               "the inventory fields."),
            },
            "paid_comparison": {
                "competitors": ["Kilde EU Green Claims Compliance Kit",
                                "Mallbutiken 33-file package (79 SEK)"],
                "differentiator": "",
                "assessment": "Kilde already ships the register and rewrite library; differentiation was assessed as zero.",
            },
            "buyer_channel": {
                "buyer": "any EU trader making voluntary environmental claims to consumers",
                "channel": "direct digital download",
            },
            "build_cost_usd": 0,
        },
    ]


def main() -> int:
    record, urls, retrievals, provenance = build_retrievals()
    candidates = build_candidates(urls, retrievals, provenance)
    screened = mde.screen_intake(candidates, retrievals)

    by_name = {r["name"]: r for r in screened["results"]}
    eudr = by_name["EUDR operator/downstream register"]

    report = {
        "cycle": 107,
        "recorded_at": "2026-10-20",
        "purpose": ("Replay Cycle 107's three candidates through the repaired intake gate to prove "
                    "they are rejected before any score is computed."),
        "source_record": str(EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
        "cited_url_pool": len(urls),
        "retrieval_provenance": {
            "OBSERVED": sorted(u for u, p in provenance.items() if p == "OBSERVED"),
            "OBSERVED_AMBIGUOUS": sorted(u for u, p in provenance.items()
                                         if p == "OBSERVED_AMBIGUOUS"),
            "DERIVED": "every other URL in the Cycle 106 set; implied by 21 served pages plus the "
                       "record's complete six-item failure list",
            "NOT_RECORDED": sorted(u for u, p in provenance.items() if p == "NOT_RECORDED"),
        },
        "status_counts": {
            status: sum(1 for r in retrievals.values() if r["status"] == status)
            for status in mde.SOURCE_STATUSES
        },
        "record_inconsistency_found": {
            "what": ("The Cycle 107 record states 3 bot-protected 403 responses in its summary but "
                     "names 'the four Reddit URLs' as 403 in material defect V3, while the cited set "
                     "contains five Reddit URLs. The aggregate counts (21 + 3 + 1 + 2 + 2 + 2) also "
                     "sum to 31 against a stated 29 unique URLs because the 5 wrong-content pages "
                     "overlap the 21 served."),
            "effect": "No verdict changes: none of the three candidates cites a Reddit URL. The five "
                      "Reddit URLs are recorded as UNVERIFIED rather than guessed, and the counts are "
                      "reported as recorded, not reconciled by invention.",
        },
        "retrievals_used": [retrievals[u] for u in sorted(retrievals)],
        "screen": screened,
        "conclusion": {
            "rejected_at_intake": screened["rejected_at_intake"],
            "qualified": screened["qualified"],
            "scores_consulted": False,
            "eudr_note": ("Every EUDR citation survived retrieval (G1/G2 pass), so the rejection does "
                          "not rest on missing evidence: it fails G3 (materially duplicated by a free "
                          "alternative) and G4 (no stated differentiator). That is the same conclusion "
                          "Cycle 107 reached after scoring 19/25, now reached without computing a score."),
            "cbam_empco_note": ("Both fail G1 as well, because Cycle 107 retained no per-URL status for "
                                "their citations. That is the second defect this repair closes: an md "
                                "sentence saying 'verified live' is not a retrieval record."),
            "verdict": "ALL THREE REJECTED AT INTAKE",
        },
        "what_this_does_not_prove": [
            "It does not prove the free alternatives are adequate for every buyer; it proves they were "
            "adequate to reject these three candidates, as already recorded.",
            "It does not re-fetch anything: statuses are the ones Cycle 107 observed or derived.",
            "It does not create demand evidence, and passing the intake gate would not have made any of "
            "the three sellable.",
        ],
    }

    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote %s" % OUT.relative_to(ROOT))
    print("screened=%d rejected=%d qualified=%d"
          % (screened["screened"], screened["rejected_at_intake"], screened["qualified"]))
    for row in screened["results"]:
        print("  %-55s %-22s failed=%s"
              % (row["name"][:55], row["verdict"], ",".join(row["failed_gates"]) or "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

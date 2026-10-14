"""Cycle 86c -- LEGAL REVIEW INVENTORY.

WHAT THIS FOUND (the reason it exists)
--------------------------------------
Two real gaps, found by tracing every call site rather than assuming:

  GAP 1 -- legal_review_required() is DEAD CODE. It is defined in both
  product_content_integrity.py and source_grounding.py, and called by NOTHING
  in production. Both docstrings claim it exists "so callers cannot
  accidentally present a mechanical pass as clearance" -- there are no such
  callers. It is a promise in a docstring, not a control.

  GAP 2 -- SOURCE_REGISTRY covers exactly one topic. get_sources() returns []
  for GDPR, CCPA, SOC 2, FTC, GPSR, HIPAA and PCI. A regulatory product in
  any of those areas therefore receives an EMPTY grounding instruction, and
  check_generated() verifies it only against EU-AI-Act-specific forbidden
  framings, which are meaningless there. The product looks checked and is not.

This script builds the inventory that neither gap can substitute for: which
shipped files actually make legal claims, in which jurisdiction, on what date,
and which of those claims are confirmed versus unresolved.

IT DELIBERATELY GIVES NO LEGAL OPINION AND GRANTS NO CLEARANCE.
It is an inventory of what needs review, not a review itself.

Read-only. Costs $0. No network.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

import source_grounding as sg

# Jurisdiction signals, deliberately explicit rather than clever.
JURISDICTIONS = {
    "EU": [r"\bEU\b", r"European Union", r"\bGDPR\b", r"AI Act", r"\bEUDPR\b"],
    "UK": [r"\bUK\b", r"United Kingdom", r"\bUK GDPR\b", r"Consumer Protection"],
    "US-Federal": [r"\bCCPA\b", r"\bFTC\b", r"\bHIPAA\b", r"\bPCI DSS\b",
                   r"\bSOC 2\b", r"\bGLBA\b", r"CFPB"],
    "US-State": [r"California", r"\bCPPA\b", r"state law"],
    "INTL": [r"\bISO 42001\b", r"\bISO 27001\b"],
}

LEGAL_TOPIC_TERMS = [
    "compliance", "regulation", "regulatory", "directive", "statute",
    "GDPR", "AI Act", "CCPA", "SOC 2", "FTC", "GPSR", "HIPAA", "PCI",
    "penalt", "enforcement", "liable", "liability", "must comply",
    "obligations under", "not legal advice", "lawful basis",
]


@dataclass
class ReviewItem:
    file: str
    size_bytes: int
    pages: int = 0
    words: int = 0
    jurisdictions: list[str] = field(default_factory=list)
    legal_topics: list[str] = field(default_factory=list)
    has_disclaimer: bool = False
    grounded_sources: list[str] = field(default_factory=list)
    verified_dates: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    status: str = "HOLD"          # HOLD | REVIEW | NOT_APPLICABLE
    reason: str = ""


def _text_of(p: Path) -> str:
    try:
        r = PdfReader(str(p))
        return "\n".join((pg.extract_text() or "") for pg in r.pages)
    except Exception:  # noqa: BLE001
        return ""


def inspect_file(p: Path) -> ReviewItem | None:
    txt = _text_of(p)
    if not txt.strip():
        return None
    try:
        pages = len(PdfReader(str(p)).pages)
    except Exception:  # noqa: BLE001
        pages = 0

    low = txt.lower()
    juris = [name for name, pats in JURISDICTIONS.items()
             if any(re.search(p, txt, re.I) for p in pats)]
    topics = sorted({t for t in LEGAL_TOPIC_TERMS if t.lower() in low})
    disclaimer = bool(re.search(r"not legal advice|does not constitute legal",
                                txt, re.I))
    verified = sorted(set(re.findall(r"verified\s+(\d{4}-\d{2}-\d{2})", txt, re.I)))

    # Normalise separators before classification. Passing the raw stem
    # ("eu_ai_act_transparency_literacy_checklist") meant the "ai act"
    # marker never matched the underscored form, so that file reported NO
    # grounded source and understated the inventory. A false negative in a
    # legal-claims inventory is the dangerous direction.
    normalized = p.stem.replace("_", " ").replace("-", " ")
    is_reg, _ = sg.classify_regulatory(normalized, txt[:2000])
    srcs = sg.get_sources(normalized) if is_reg else []
    grounded = [s.get("url", "") for s in srcs]

    unresolved: list[str] = []
    if not disclaimer:
        unresolved.append("no 'not legal advice' disclaimer found")
    if not verified:
        unresolved.append("no verification date found")
    if is_reg and not srcs:
        unresolved.append(
            "regulatory topic with NO grounded primary source in SOURCE_REGISTRY")
    if juris and not grounded:
        unresolved.append("jurisdictional claims rest on no primary source")

    status = "NOT_APPLICABLE" if not topics and not juris else "HOLD"
    reason = ""
    if status == "HOLD":
        reason = ("legal claims present; requires qualified human legal review. "
                  "No automated result clears this.")
    if juris and not grounded:
        status = "REVIEW"

    return ReviewItem(
        file=str(p), size_bytes=p.stat().st_size, pages=pages,
        words=len(txt.split()), jurisdictions=sorted(juris), legal_topics=topics,
        has_disclaimer=disclaimer, grounded_sources=grounded,
        verified_dates=verified, unresolved=unresolved,
        status=status, reason=reason)


def build_inventory(targets: list[Path]) -> dict:
    items = [i for i in (inspect_file(p) for p in targets if p.exists()) if i]
    reg = [i for i in items if i.legal_topics or i.jurisdictions]
    return {
        "probe": "cycle86c_legal_review_inventory",
        "read_only": True,
        "cost_usd": 0,
        "grants_clearance": False,
        "gives_legal_opinion": False,
        "scanned_files": len(items),
        "files_with_legal_claims": len(reg),
        "summary": {
            "HOLD": sum(1 for i in reg if i.status == "HOLD"),
            "REVIEW": sum(1 for i in reg if i.status == "REVIEW"),
            "NOT_APPLICABLE": sum(1 for i in reg if i.status == "NOT_APPLICABLE"),
        },
        "gaps": [
            "legal_review_required() is defined twice and called by NO production "
            "caller -- it is documentation, not an enforced control.",
            "SOURCE_REGISTRY covers only eu_ai_act; get_sources() returns [] for "
            "GDPR/CCPA/SOC2/FTC/GPSR/HIPAA, so those topics get an empty grounding "
            "block and are verified against AI-Act-specific patterns only.",
        ],
        "items": [asdict(i) for i in reg],
    }


def main() -> int:
    targets = [
        Path("books/eu_ai_act_compliance_toolkit_v2.pdf"),
        Path("books/eu_ai_act_compliance_toolkit_preview.pdf"),
        Path("books/eu_ai_act_audit_logging_kit.pdf"),
        Path("books/eu_ai_act_compliance_quickstart_checklist.pdf"),
        Path("books/eu_ai_act_transparency_literacy_checklist.pdf"),
        Path("books/ccpa_compliance_action_kit.pdf"),
        Path("books/soc2_compliance_automation_kit.pdf"),
        Path("books/ftc_review_rule_compliance_kit.pdf"),
        Path("books/gpsr_eu_seller_action_kit.pdf"),
        Path("books/ai_compliance_automation_for_accounting_firms_v2.pdf"),
    ]

    inv = build_inventory(targets)

    print("=" * 78)
    print("CYCLE 86c -- LEGAL REVIEW INVENTORY")
    print("=" * 78)
    print(f"files scanned            : {inv['scanned_files']}")
    print(f"files with legal claims  : {inv['files_with_legal_claims']}")
    print(f"  HOLD {inv['summary']['HOLD']}  "
          f"REVIEW {inv['summary']['REVIEW']}  "
          f"NOT_APPLICABLE {inv['summary']['NOT_APPLICABLE']}")
    print()
    print("GAPS FOUND")
    for g in inv["gaps"]:
        print(f"  - {g}")
    print()
    print("=" * 78)
    print("ITEMS REQUIRING QUALIFIED HUMAN LEGAL REVIEW")
    print("=" * 78)
    for it in inv["items"]:
        print(f"\n[{it['status']}] {Path(it['file']).name}")
        print(f"    {it['pages']}pp / {it['words']} words")
        print(f"    jurisdiction : {', '.join(it['jurisdictions']) or 'unstated'}")
        print(f"    legal topics : {', '.join(it['legal_topics'][:6]) or '-'}")
        print(f"    disclaimer   : {'YES' if it['has_disclaimer'] else 'NO'}")
        print(f"    verified on  : {', '.join(it['verified_dates']) or 'NONE'}")
        print(f"    grounded src : {', '.join(it['grounded_sources']) or 'NONE'}")
        for u in it["unresolved"]:
            print(f"    UNRESOLVED   : {u}")

    print()
    print("=" * 78)
    print("THIS IS AN INVENTORY, NOT A REVIEW")
    print("=" * 78)
    print("No file below is cleared. No legal opinion is offered. HOLD stands")
    print("until a qualified reviewer examines it. Grounding prevents unsourced")
    print("claims; it does not establish that a document is lawful or accurate.")

    Path("data/cycle86c_legal_review_inventory.json").write_text(
        json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote data/cycle86c_legal_review_inventory.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
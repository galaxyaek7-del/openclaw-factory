"""Cycle 86b -- are the three sibling EU AI Act listings affected by the same
fabricated-Annex-III defect, or is the flagship an isolated case?

This is the cheap next obstacle. If the same pipeline produced the same
invented categories in the $29 / $19 / $9 listings, the problem is systemic,
not a one-off, and the fix has to be upstream in the generator rather than a
patch to one PDF.

Read-only. Costs $0.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

import product_content_integrity as pci

CANDIDATES = [
    ("EU AI Act Audit Logging Kit", "books/eu_ai_act_audit_logging_kit.pdf"),
    ("EU AI Act Compliance Quickstart Checklist", "books/eu_ai_act_compliance_quickstart_checklist.pdf"),
    ("EU AI Act Transparency & AI Literacy Quickstart Checklist", "books/eu_ai_act_transparency_literacy_checklist.pdf"),
]

TODAY = "2026-10-14"
print("=" * 78)
print("CYCLE 86b -- SIBLING EU AI ACT LISTINGS")
print("=" * 78)

any_bad = False
for name, path in CANDIDATES:
    p = Path(path)
    print(f"\n--- {name}")
    if not p.exists():
        print(f"    {path} NOT PRESENT LOCALLY")
        continue
    try:
        r = PdfReader(str(p))
        text = "\n".join((pg.extract_text() or "") for pg in r.pages)
    except Exception as exc:  # noqa: BLE001
        print(f"    unreadable: {type(exc).__name__}")
        continue

    words = len(text.split())
    print(f"    {p.name}  pages={len(r.pages)}  words={words}")

    res = pci.check_product(name, text, TODAY)
    crit = [f for f in res.findings if f.severity == "CRITICAL"]
    rules = sorted({f.rule for f in res.findings})
    print(f"    verdict={res.verdict}  critical={len(crit)}  rules={rules or 'none'}")

    for f in crit[:3]:
        print(f"      CRITICAL {f.rule}: {f.evidence[:110]}")
    if not crit:
        print("      no critical finding -- but note: a short file may simply")
        print("      not contain enough text to trigger any rule. That is NOT")
        print("      a pass. Absence of a finding is not evidence of accuracy.")
    if crit:
        any_bad = True

print()
print("=" * 78)
print("SYSTEMIC OR ISOLATED?")
print("=" * 78)
if any_bad:
    print("  AT LEAST ONE SIBLING CARRIES THE SAME CRITICAL DEFECT.")
    print("  This is a pipeline problem, not a single bad PDF.")
    print("  The fix belongs in the generator, not in one file.")
else:
    print("  No sibling showed a critical finding. Two readings are possible:")
    print("    (a) the flagship's defect was isolated, or")
    print("    (b) the siblings are too short to trip any rule.")
    print("  Only (a) is reassuring, and this probe cannot distinguish them.")
    print("  Human legal review is the only real resolution.")
print()
print("NONE of this constitutes clearance. See legal_review_required().")
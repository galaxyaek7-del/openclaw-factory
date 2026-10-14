"""Run the Cycle 86 content-integrity gate against the REAL shipped product
and write an evidence-backed scorecard.

Read-only. Costs $0. Writes only its own result JSON.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import product_content_integrity as pci

TODAY = "2026-10-14"
PRODUCT = "EU AI Act Compliance Toolkit"
TEXT = Path("data/cycle86_toolkit_text.txt")

res = pci.check_product(PRODUCT, TEXT.read_text(encoding="utf-8"), TODAY)

print("=" * 76)
print(f"CYCLE 86 -- CONTENT INTEGRITY GATE: {PRODUCT}")
print("=" * 76)
print(f"verdict          : {res.verdict}")
print(f"critical findings: {res.critical_count}")
print(f"total findings   : {len(res.findings)}")
print()

by_rule: dict[str, list] = {}
for f in res.findings:
    by_rule.setdefault(f.rule, []).append(f)

for rule, items in by_rule.items():
    print(f"--- {rule}  ({len(items)}) [{items[0].severity}] ---")
    for f in items[:4]:
        print(f"  where  : {f.where}")
        print(f"  why    : {f.evidence[:150]}")
    if len(items) > 4:
        print(f"  ... and {len(items) - 4} more")
    print()

print("=" * 76)
print("SCORECARD (100 pts)")
print("=" * 76)

critical = res.critical_count
critical_rules = {f.rule for f in res.findings if f.severity == "CRITICAL"}
minor = sum(1 for f in res.findings if f.severity == "MINOR")
major = sum(1 for f in res.findings if f.severity == "MAJOR")

# Content/sources (25) -- fabricated legal citations is disqualifying.
if "FABRICATED_CITATION" in critical_rules or "INVENTED_STRUCTURE" in critical_rules:
    correctness = 2
    corr_why = "2/25 - fabricated Annex III categories cited as literal regulation text"
elif "FALSE_PROHIBITION" in critical_rules:
    correctness = 6
    corr_why = "6/25 - a stated prohibition is not in the regulation"
else:
    correctness = 20
    corr_why = "20/25 - no fabricated citation detected, but no primary-source check done"

# File completeness (25) -- verified real by cycle 81 byte audit.
files_score = 25
files_why = "25/25 - both PDFs fetched, sha256'd, parsed, size-matched (data/delivery_integrity.json)"

# Practical value (20) -- padding detected.
if "CONTENT_PADDING" in {f.rule for f in res.findings}:
    value = 7
    val_why = "7/20 - most of 25 chapters are 5-bullet generic lists (~45 words each)"
else:
    value = 16
    val_why = "16/20 - usable but unproven depth"

# Independent verification (15) -- gate exists but human legal review absent.
tests = 15 - (3 if minor else 0) - (2 if major else 0)
tests_score = max(0, tests - 5)   # minus 5: no qualified human legal review
tests_why = (f"{tests_score}/15 - automated gate now exists, but NO qualified human "
             f"legal review has ever been performed; mechanical pass is not clearance")

# Commercial presentation (15) -- markdown + truncation visible.
pres = 15 - (3 if "MARKDOWN_LEAKAGE" in by_rule else 0) - (2 if "TRUNCATED_HEADING" in by_rule else 0)
pres_why = f"{pres}/15 - literal **markdown** and mid-word TOC truncation visible to buyers"

total = correctness + files_score + value + tests_score + pres

print(f"  content correctness      {correctness:>3}/25   {corr_why}")
print(f"  file completeness        {files_score:>3}/25   {files_why}")
print(f"  practical value          {value:>3}/20   {val_why}")
print(f"  independent verification {tests_score:>3}/15   {tests_why}")
print(f"  commercial presentation  {pres:>3}/15   {pres_why}")
print(f"  {'-'*60}")
print(f"  TOTAL                    {total:>3}/100")

print()
print("=" * 76)
print("DECISION")
print("=" * 76)
if critical:
    print(f"  **HOLD** -- {critical} CRITICAL defect(s).")
    print("  The standard is explicit: any critical failure means HOLD regardless")
    print("  of total score. A 90+ score would not rescue fabricated citations.")
    print()
    print("  This product must NOT go to any marketing campaign, and the")
    print("  affiliate programme page built for it must not be published.")

payload = res.as_dict()
payload.update({
    "probe": "cycle86_content_gate",
    "today": TODAY,
    "source_pdf": "books/eu_ai_act_compliance_toolkit_v2.pdf",
    "source_sha256": "18c4158342c7f8a290a4386507e1d6bb7cfdc92420e485d76108d4102a40f6bf",
    "scorecard": {
        "content_correctness": {"score": correctness, "max": 25, "why": corr_why},
        "file_completeness": {"score": files_score, "max": 25, "why": files_why},
        "practical_value": {"score": value, "max": 20, "why": val_why},
        "independent_verification": {"score": tests_score, "max": 15, "why": tests_why},
        "commercial_presentation": {"score": pres, "max": 15, "why": pres_why},
        "total": total,
        "max": 100,
        "threshold": 90,
        "decision": "HOLD",
        "decision_reason": "critical defects open; HOLD overrides total score",
    },
    "cost_usd": 0,
})
Path("data/cycle86_content_gate.json").write_text(
    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nwrote data/cycle86_content_gate.json")
"""Cycle 82 -- run the manifest gate on the real bundle, using the REAL
sales-page text fetched from Gumroad.

Every expected size is derived from the artifact on disk. Nothing is
hand-typed. Read-only; no purchase; no write. $0.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, r"C:\openclaw-dasgboard")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import manifest_gate as mg

ARCHIVE = "books/_releases/etsy_suspension_complete_bundle_v3.zip"
SLUG = "bfhpzl"

req = urllib.request.Request(f"https://aekraft.gumroad.com/l/{SLUG}",
                             headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
html = html.replace("&quot;", '"').replace("&#39;", "'")

m = __import__("re").search(
    r"EXACTLY WHAT YOU DOWNLOAD(.{0,1200}?)which file to open first", html,
    __import__("re").S)
if not m:
    print("BLOCKED: the published manifest block was not found on the page.")
    raise SystemExit(2)
page_text = m.group(1)

print("=" * 80)
print("CYCLE 82 -- MANIFEST GATE vs THE LIVE SALES PAGE")
print("=" * 80)
print(f"archive : {ARCHIVE}")
print(f"page    : https://aekraft.gumroad.com/l/{SLUG}")
print()

res = mg.check_manifest(ARCHIVE, page_text)

print(f"VERDICT: {res.verdict}")
print(f"claims checked : {len(res.results)}")
print(f"mismatched     : {len(res.mismatched)}")
print(f"blocked        : {len(res.blocked)}")
if res.archive_problems:
    print(f"archive problems: {res.archive_problems}")
print()
print(f"{'FILE':<42}{'PAGE SAYS':>10}{'ACTUAL B':>12}  STATUS")
print("-" * 80)
for r in res.results:
    print(f"{r.claim.filename:<42}{r.claim.size_text:>10}"
          f"{(r.actual_bytes if r.actual_bytes is not None else 0):>12,}  "
          f"{r.status}")

print()
print("=" * 80)
print("EVIDENCE FOR EACH MISMATCH")
print("=" * 80)
for r in res.mismatched:
    print(f"\n  {r.claim.filename}")
    print(f"    current value on page : {r.claim.size_text}")
    print(f"    corrected value       : {r.corrected_text}")
    print(f"    actual delivered size : {r.actual_bytes:,} bytes")
    print(f"    difference            : {r.actual_bytes - int(r.claim.claimed_bytes):+,} bytes")
    print(f"    why                   : {r.evidence}")

print()
print("=" * 80)
print("PROPOSED SALES-PAGE TEXT CHANGE (PREPARED ONLY -- NOT PUBLISHED)")
print("=" * 80)
old_lines, new_lines = [], []
# FIRST DRAFT OF THIS DIFF WAS BROKEN AND WOULD HAVE CORRUPTED THE LIVE PAGE.
# It replaced the substring "6 KB" everywhere, which also struck inside
# "36 KB" and turned the two DOCX entries into "315 KB". The gate verdicts
# above were correct; only the patch text was wrong. Replacement is now
# anchored on a word boundary and applied per-entry.
for raw in page_text.splitlines():
    line = raw.rstrip()
    if not line.strip():
        continue
    new = line
    touched = False
    for r in res.mismatched:
        pat = re.escape(r.claim.size_text)
        replaced, n = re.subn(rf"(?<![0-9A-Za-z]){pat}(?![0-9A-Za-z])",
                               r.corrected_text, new)
        if n:
            new = replaced
            touched = True
    if touched:
        old_lines.append(line.strip())
        new_lines.append(new.strip())
if old_lines:
    print("\n  REPLACE:")
    for o in old_lines:
        print(f"    - {o}")
    print("  WITH:")
    for n in new_lines:
        print(f"    + {n}")
    # prove the patch cannot have damaged an unrelated entry
    joined_old, joined_new = " ".join(old_lines), " ".join(new_lines)
    for r in res.results:
        if r.status == "PASS":
            if r.claim.size_text not in joined_new:
                print(f"    !! SAFETY CHECK FAILED: passing entry "
                      f"{r.claim.filename} ({r.claim.size_text}) lost")
else:
    print("  (no exact line match -- a manual edit is required)")

print()
print("  ROLLBACK: re-apply the current lines above. No file, product or")
print("  price changes; the description is the only field touched.")
print("  STATUS: PREPARED. NOT PUBLISHED. Requires founder approval and a")
print("  live Gumroad write, which the Phase 5 gate blocks.")

Path("data/cycle82_manifest_gate.json").write_text(json.dumps({
    "probe": "cycle82_manifest_gate", "read_only": True, "cost_usd": 0,
    "purchases": 0, "writes": 0,
    "archive": ARCHIVE, "page": f"/l/{SLUG}",
    **res.as_dict(),
    "correction_prepared": [
        {"file": r.claim.filename, "current": r.claim.size_text,
         "corrected": r.corrected_text, "actual_bytes": r.actual_bytes}
        for r in res.mismatched],
    "published": False,
}, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nwrote data/cycle82_manifest_gate.json")
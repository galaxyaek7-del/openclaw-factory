"""Cycle 85: derive and validate the two-number description patch for /l/bfhpzl.

Read-only. Produces the exact new description text and proves the diff touches
nothing but the two approved numbers.

Two findings shaped this, and both are why a naive string replace is wrong here:

1. The page's KB convention had to be DERIVED, not assumed. The two "36 KB"
   claims are decisive: 36,302 B rounds to 36 under 1 KB = 1000 B but to 35
   under 1 KB = 1024 B. The page uses decimal KB.

2. A bare replace of "6 KB" is actively dangerous. The description contains
   "36 KB" twice, and "6 KB" is a substring of both -- so three separate
   matches exist and two of them belong to a DIFFERENT file's size claim. The
   first draft of this script asserted anchor uniqueness and that assert fired,
   which is exactly what it existed for. The replacement is therefore anchored
   on the filename and rewrites only the numeric token.
"""
import difflib
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ZIP = "books/_releases/etsy_suspension_complete_bundle_v3.zip"
BASE = "data/cycle83_description_baseline.json"
OUT = "data/cycle85_description_patch.json"

html = json.load(open(BASE, encoding="utf-8"))["description_html"]

# (filename, current claim, correct byte size)
TARGETS = [
    ("etsy_suspension_appeal_kit.pdf", 122, 138923),
    ("etsy_appeal_evidence_tracker.xlsx", 6, 15011),
]

zf = zipfile.ZipFile(ZIP)
sizes = {i.filename: i.file_size for i in zf.infolist()}
for name, _, size in TARGETS:
    assert sizes[name] == size, f"{name}: expected {size}, zip says {sizes[name]}"

new = html
applied = []
for name, old_kb, size in TARGETS:
    correct_kb = round(size / 1000)
    # Anchored on the filename; only the number after it is captured.
    pat = re.compile(
        r"(" + re.escape(name) + r"\s+)" + str(old_kb) + r"(\s*KB\b)")
    hits = pat.findall(new)
    assert len(hits) == 1, (
        f"{name}: expected exactly 1 match for the stale claim, found {len(hits)}")
    new, n = pat.subn(r"\g<1>" + str(correct_kb) + r"\g<2>", new, count=1)
    assert n == 1
    applied.append({
        "file": name,
        "bytes": size,
        "was_kb": old_kb,
        "now_kb": correct_kb,
        "derivation": f"{size} / 1000 = {size/1000:.3f} -> {correct_kb} KB (decimal, "
                      "the convention proven from the page's own 36 KB claims)",
    })

# Prove the diff is confined to the two numbers.
sm = difflib.SequenceMatcher(None, html, new, autojunk=False)
ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
print("Changed regions in the description (should be exactly 2):")
for tag, i1, i2, j1, j2 in ops:
    print(f"  {tag:8s} {html[i1:i2]!r} -> {new[j1:j2]!r}   "
          f"at offset {i1} | context: {' '.join(html[max(0,i1-46):i1].split())!r}")
assert len(ops) == 2, f"expected 2 changed regions, found {len(ops)}"

# Every byte outside those regions must be identical.
restored = new
for tag, i1, i2, j1, j2 in reversed(ops):
    restored = restored[:j1] + html[i1:i2] + restored[j2:]
assert restored == html, "change leaked outside the two approved numbers"
print()
print("PASS: restoring the two edits reproduces the original byte-for-byte,")
print("       so nothing outside the approved numbers can have moved.")

result = {
    "probe": "cycle85_description_patch",
    "slug": "bfhpzl",
    "product_id": "LzOV85deBGdLgNZmvpvYGw==",
    "read_only": True,
    "live_write_performed": False,
    "cost_usd": 0,
    "old_description_length": len(html),
    "new_description_length": len(new),
    "old_sha256": hashlib.sha256(html.encode()).hexdigest(),
    "new_sha256": hashlib.sha256(new.encode()).hexdigest(),
    "changes": applied,
    "out_of_scope_findings": [{
        "what": "the zip's own size claim",
        "claims": f"{173} KB",
        "actual_bytes": Path(ZIP).stat().st_size,
        "correct_kb": round(Path(ZIP).stat().st_size / 1000),
        "action": "NOT changed - the approval covers exactly two numbers. "
                  "Reported for a separate decision.",
    }],
}
json.dump(result, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print()
print(f"new description sha256: {result['new_sha256']}")
print(f"wrote {OUT}")
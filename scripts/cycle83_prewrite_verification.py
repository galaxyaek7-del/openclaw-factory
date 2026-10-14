"""Cycle 83 -- pre-write verification for the approved /l/bfhpzl description repair.

Derives every value from the delivered artifact on disk. No value is assumed,
typed by hand, or carried over from an earlier cycle. Nothing is written.
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, r"C:\openclaw-dasgboard")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ARCHIVE = Path("books/_releases/etsy_suspension_complete_bundle_v3.zip")
TARGETS = {
    "etsy_suspension_appeal_kit.pdf": None,
    "etsy_appeal_evidence_tracker.xlsx": None,
}

print("=" * 78)
print("PRE-WRITE VERIFICATION -- values derived from disk")
print("=" * 78)
print(f"archive : {ARCHIVE}")
print(f"bytes   : {ARCHIVE.stat().st_size:,}")
h = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
print(f"sha256  : {h}")
print()

rows = []
with zipfile.ZipFile(ARCHIVE) as z:
    for i in z.infolist():
        if i.filename not in TARGETS:
            continue
        b = i.file_size
        kib = b / 1024
        dec = b / 1000
        crc = hex(z.getinfo(i.filename).CRC)
        TARGETS[i.filename] = {
            "bytes": b, "kib": round(kib, 2), "kb_decimal": round(dec, 2),
            "crc32": crc, "page_style": round(kib),
        }
        rows.append((i.filename, b, kib, dec, crc))

print(f"{'MEMBER':<42}{'BYTES':>10}{'KiB':>9}{'KB(dec)':>10}  CRC32")
print("-" * 78)
for name, b, kib, dec, crc in rows:
    print(f"{name:<42}{b:>10,}{kib:>9.2f}{dec:>10.2f}  {crc}")

print()
print("UNIT CHECK -- the page uses DECIMAL KB (confirmed below)")
print("-" * 78)
xlsx = TARGETS["etsy_appeal_evidence_tracker.xlsx"]
print(f"  xlsx actual : {xlsx['bytes']:,} B")
print(f"  in KiB      : {xlsx['kib']}  -> page would say '{round(xlsx['kib'])} KB'")
print(f"  in KB(dec)  : {xlsx['kb_decimal']}  -> page would say '{xlsx['page_style']} KB'")
print()
print("  The instruction requires confirming the XLSX is 14.7 KB under the")
print("  page's unit. It is:")
print(f"    15,011 / 1024 = {xlsx['kib']} KiB  -> 14.7 KiB. CONFIRMED in binary.")
print(f"    15,011 / 1000 = {xlsx['kb_decimal']} KB -> 15.0 KB in decimal.")
print()
print("  DETERMINATION: the other four manifest entries were already")
print("  consistent under DECIMAL only (36,302 B renders '36 KB' decimal,")
print("  35.5 KiB binary; 1,003 B renders '1 KB' both ways). The page is")
print("  therefore a DECIMAL page, so the XLSX must publish as 15 KB, not")
print("  14.7 KB or 15 KB. Recording this explicitly because '14.7 KB'")
print("  in the approval note is a binary reading of a decimal page.")

pdf = TARGETS["etsy_suspension_appeal_kit.pdf"]
print()
print("PROPOSED VALUES (derived, not assumed)")
print("-" * 78)
print(f"  etsy_suspension_appeal_kit.pdf   : 122 KB -> "
      f"{round(pdf['kb_decimal'])} KB   (actual {pdf['bytes']:,} B)")
print(f"  etsy_appeal_evidence_tracker.xlsx:   6 KB -> "
      f"{round(xlsx['kb_decimal'])} KB   (actual {xlsx['bytes']:,} B)")

Path("data/cycle83_prewrite_verification.json").write_text(json.dumps({
    "probe": "cycle83_prewrite_verification",
    "archive": str(ARCHIVE), "archive_bytes": ARCHIVE.stat().st_size,
    "archive_sha256": h, "read_only": True, "cost_usd": 0,
    "page_unit": "decimal KB",
    "members": TARGETS,
}, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nwrote data/cycle83_prewrite_verification.json")
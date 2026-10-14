"""Cycle 88 -- immutable checksum manifest of every build artifact.

WHY THIS IS MANDATORY, NOT TIDYNESS
-----------------------------------
books/*.pdf and books/*.xlsx are GITIGNORED (.gitignore:40). They are not in
version control, so git cannot roll them back. During this very session 44
files under books/ were rewritten in a single minute, and the count of
black-box PDFs moved from 44 to 19 between two scans minutes apart.

That is the strongest argument for taking a checksum manifest BEFORE any
repair: the originals are the only rollback path that actually exists, and
right now there is no record of what they were.

This writes a manifest of SHA-256 for every artifact, plus a verifiable
restore source. It copies nothing and modifies nothing -- it only records.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
SPRINT = ROOT / "factory_workspace" / "sprint14"

BAD = "\u25a0\ufffd"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def boxes_in(p: Path) -> int:
    if p.suffix.lower() != ".pdf":
        return 0
    try:
        from pypdf import PdfReader
        t = "".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
        return t.count(BAD[0]) + t.count(BAD[1])
    except Exception:  # noqa: BLE001
        return -1


def main() -> int:
    entries = []
    for store in (BOOKS, SPRINT):
        if not store.exists():
            continue
        for p in sorted(store.iterdir()):
            if not p.is_file() or p.suffix.lower() not in (".pdf", ".xlsx", ".zip"):
                continue
            try:
                digest = sha256(p)
                size = p.stat().st_size
            except OSError:
                continue
            entries.append({
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "bytes": size,
                "sha256": digest,
                "mtime_utc": datetime.fromtimestamp(
                    p.stat().st_mtime, timezone.utc).isoformat(),
                "black_boxes": boxes_in(p),
            })

    with_boxes = [e for e in entries if (e["black_boxes"] or 0) > 0]
    out = {
        "manifest": "cycle88_artifact_checksums",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": ("rollback path for artifacts that are NOT in version "
                    "control -- books/*.pdf is gitignored"),
        "note": "these files are untracked by design; this manifest is the record",
        "total_artifacts": len(entries),
        "artifacts_with_black_boxes": len(with_boxes),
        "total_black_boxes": sum(e["black_boxes"] for e in with_boxes),
        "artifacts": entries,
    }
    dest = ROOT / "data" / "cycle88_artifact_checksums.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=" * 72)
    print("ARTIFACT CHECKSUM MANIFEST (rollback baseline)")
    print("=" * 72)
    print(f"  artifacts recorded      : {len(entries)}")
    print(f"  with black boxes        : {len(with_boxes)}")
    print(f"  total black boxes       : {out['total_black_boxes']}")
    print(f"  written to              : data/cycle88_artifact_checksums.json")
    print()
    print("  FILES THAT STILL CONTAIN UNRENDERABLE GLYPHS")
    print("  " + "-" * 68)
    for e in sorted(with_boxes, key=lambda x: -x["black_boxes"])[:25]:
        print(f"    {e['black_boxes']:>5}  {e['path']}")
    if len(with_boxes) > 25:
        print(f"    ... and {len(with_boxes) - 25} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge drift detector (V68). Read-only by default: compares the
working tree against HEAD and prints a categorized divergence summary.
No network, no writes, no publishing. Exit 0 = within thresholds,
exit 2 = drift above thresholds (informational, never a failure of the
commercial system). Optional --record writes a dated snapshot JSON next
to this script's stdout consumer (explicit only)."""
import json
import subprocess
import sys
from datetime import datetime, timezone

TRACKED_MODIFIED_WARN = 10
SOURCE_ADDED_WARN = 500


def _run(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def snapshot():
    head = _run(["git", "rev-parse", "HEAD"]).strip()
    status = _run(["git", "status", "--porcelain"]).splitlines()
    modified = [l[3:].strip().strip('"') for l in status if l[:2] != "??"]
    untracked = [l[3:].strip().strip('"') for l in status if l[:2] == "??"]
    numstat = []
    # V69: diff against HEAD (not index) so staged-new files are included.
    # `git diff` alone misses staged additions entirely (proved: 600-line
    # staged .py reported WITHIN_THRESHOLDS before this fix).
    for l in _run(["git", "diff", "HEAD", "--numstat"]).splitlines():
        p = l.split("\t")
        if len(p) == 3 and p[0] != "-":
            numstat.append({"file": p[2], "added": int(p[0]), "removed": int(p[1])})
    src_added = sum(r["added"] for r in numstat
                    if r["file"].endswith((".py", ".js")) and "/tests/" not in r["file"]
                    and not r["file"].startswith("tests/"))
    return {
        "at": datetime.now(timezone.utc).isoformat(),
        "head": head,
        "tracked_modified": len([m for m in modified if not m.startswith("A ")]),
        "untracked": len(untracked),
        "diff_added": sum(r["added"] for r in numstat),
        "diff_removed": sum(r["removed"] for r in numstat),
        "source_added": src_added,
        "top": sorted(numstat, key=lambda r: -r["added"])[:10],
    }


def main():
    snap = snapshot()
    over = (snap["tracked_modified"] >= TRACKED_MODIFIED_WARN
            or snap["source_added"] >= SOURCE_ADDED_WARN)
    if "--record" in sys.argv:
        path = "data/drift_detector_last.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=1)
        print("recorded to %s" % path)
    print(json.dumps(snap, indent=1)[:2000])
    print("DRIFT_STATE:", "ABOVE_THRESHOLDS" if over else "WITHIN_THRESHOLDS")
    return 2 if over else 0


if __name__ == "__main__":
    sys.exit(main())

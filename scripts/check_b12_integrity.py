#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B12 deliverable integrity + listing consistency check (Phase 7, Mission F).
Read-only: recomputes SHA-256/size of every B12 file, compares against the
baselines recorded in reports/phase7/B12_001_QUALITY_AUDIT.md (B12-001) and
the batch registry, and verifies each prep listing title/price matches.
Exit 0 = all match; exit 1 = drift detected (never modifies anything)."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINES = {
    # Re-baselined 2026-10-17 (Cycle 88): intentional repair of the percentage
    # display and RaisePlanner formulas; previous baseline 3f5ce8a6…f5109 / 8302 B,
    # original kept in books/batch12/_pre_cycle88_fix/.
    "books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx": {
        # Re-baselined again 2026-10-17 (Cycle 94): input validation and guarded
        # outputs (edge cases tested in Excel 16); previous 09410945…53e4d3 / 8359 B.
        "sha256": "aee8fc0b100345e7abc6e8a41487ddf551b5b7f235c6f4324827d1c6ab8a092d",
        "size": 8922,
    },
    "books/batch12/B12-004_meeting_cost_roi_calculator.xlsx": {
        "sha256": "733fc40ba7cb3cf224e253cbdb2f57592c395c16dcc2f0dfd6244cb5dea4a331",
        "size": 7125,
    },
    "books/batch12/B12-004_meeting_method_onepager.pdf": {
        "sha256": "bc897207efe2a199c36587451b86c0187f776365a3e5d8ef992b74a4a934e244",
        "size": 3360,
    },
    "books/batch12/B12-008_moving_budget_tracker.xlsx": {
        "sha256": "1e42132bf63d3c2b305a66ac86ff79824bdada0511b186420adaeaf5121dd1ed",
        "size": 7629,
    },
    "books/batch12/B12-008_moving_checklist.pdf": {
        "sha256": "368660003648942fbc7b14edb6f304d5b8b1aa21a606bf06e27a6e3b617526dd",
        "size": 4311,
    },
}


def main():
    problems = []
    reg = json.loads((ROOT / "data" / "product_batch_12.json").read_text(encoding="utf-8"))
    prep = json.loads((ROOT / "data" / "product_batch_12_gumroad_prep.json").read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in reg["products"]}
    for item in prep["items"]:
        rp = by_id.get(item["id"])
        if rp is None or rp["title"] != item["title"] or rp["price"] != item["proposed_price_usd"]:
            problems.append("registry/prep mismatch: " + item["id"])
        for f in rp["files"] if rp else []:
            if not (ROOT / "books" / "batch12" / f).exists():
                problems.append("missing file: " + f)
    for rel, base in BASELINES.items():
        p = ROOT / rel
        if not p.exists():
            problems.append("missing baseline file: " + rel)
            continue
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != base["sha256"]:
            problems.append("HASH DRIFT: " + rel)
        if len(data) != base["size"]:
            problems.append("SIZE DRIFT: " + rel)
    if problems:
        print("B12 integrity: DRIFT DETECTED")
        for x in problems:
            print(" -", x)
        return 1
    print("B12 integrity: OK (%d prep items, %d baselines)" % (len(prep["items"]), len(BASELINES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
        # Re-baselined 2026-10-18 (Cycle 97): rebuild to the deep-QA bar — Setup
        # sheet, guarded formulas, input validation, Dashboard KPIs (inspection:
        # reports/B12-004/). NOTE: openpyxl embeds a timestamp, so a rebuild
        # changes the bytes even when the content is identical.
        "sha256": "87ecb1cd223ebf615c46bf49a74c1feb70ea5131a1da9c14dcedff470ccac820",
        "size": 12865,
    },
    "books/batch12/B12-004_meeting_method_guide.pdf": {
        # Renamed from _onepager (it is a 4-page guide, Cycles 97). reportlab
        # embeds a timestamp, so the bytes are not stable across rebuilds.
        "sha256": "2c964edcfc8a9dcfb45d6bfcde23da85871ec6b3deacc39a10c71cf227972a46",
        "size": 9639,
    },
    "books/batch12/B12-008_moving_budget_tracker.xlsx": {
        "sha256": "1e42132bf63d3c2b305a66ac86ff79824bdada0511b186420adaeaf5121dd1ed",
        "size": 7629,
    },
    "books/batch12/B12-008_moving_checklist.pdf": {
        # Re-baselined 2026-10-18 (Cycle 97): the B12-004 guide rebuild ran the
        # shared scripts/build_batch12_pdfs.py, which regenerates every batch-12
        # PDF; B12-008's content is unchanged but reportlab's embedded timestamp
        # differs, so the bytes differ. Same 4311-byte size, new hash.
        "sha256": "d3803cd831106cfbce6875c84ada45fd008360db7fbe195d60c6a7bf73d2db14",
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
    # Native workbook QA gate (Cycle 102): a workbook with a registered QA spec
    # must carry a recorded PASS whose hash matches the file about to ship. This
    # reads the recorded evidence only -- it never runs Excel -- so the gate is
    # deterministic and fast, and fails if the workbook changes without the
    # native recalculation/format check being re-run against it.
    sys.path.insert(0, str(ROOT))
    try:
        import native_workbook_qa as wbqa
        for product_id, spec in wbqa.SPECS.items():
            report_dir = ROOT / "reports" / product_id
            evidence = sorted(report_dir.glob("WORKBOOK_QA_*.json"))
            if not evidence:
                problems.append(
                    "workbook QA evidence missing: reports/%s/WORKBOOK_QA_*.json" % product_id
                )
                continue
            record = json.loads(evidence[-1].read_text(encoding="utf-8"))
            if record.get("verdict") != "PASS":
                problems.append("workbook QA verdict is %s: %s" % (record.get("verdict"), evidence[-1].name))
            artifact = ROOT / spec["artifact"]
            if not artifact.exists():
                problems.append("workbook QA artifact missing: " + spec["artifact"])
            elif record.get("artifact_sha256") != hashlib.sha256(artifact.read_bytes()).hexdigest():
                problems.append(
                    "workbook QA evidence is stale for %s: re-run native_workbook_qa.py" % product_id
                )
    except ImportError as exc:  # pragma: no cover - import guards the gate itself
        problems.append("workbook QA module could not be imported: %s" % exc)

    if problems:
        print("B12 integrity: DRIFT DETECTED")
        for x in problems:
            print(" -", x)
        return 1
    print("B12 integrity: OK (%d prep items, %d baselines)" % (len(prep["items"]), len(BASELINES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

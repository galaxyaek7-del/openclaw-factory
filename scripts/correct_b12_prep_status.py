#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cycle 104 -- correct unsupported status claims in the B12 Gumroad prep registry.

WHY
---
`data/product_batch_12_gumroad_prep.json` is a *tracked* registry, so its
`status` values are company claims. Cycle 104's scan found four of them were
unsupported:

  B12-001  "LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION"
           -> actually live on Gumroad and verified this cycle (was stale).
  B12-004  same stale "LOCAL_READY" -> live and verified this cycle.
  B12-006..009 "LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION"
           -> no gate record exists for any of them (no reports/B12-00X/ at
              all), their artifact files are untracked, and the real
              content-quality layer fails all four. Claiming LOCAL_READY for a
              product that never passed a gate is exactly the unsupported claim
              PERMANENT_OPERATING_DOCTRINE forbids.

Every corrected entry gets a `status_basis` naming the artifact that supports
the new value, so a future reader can re-check instead of trusting this script.

This does NOT delete any product and does NOT change any price or file list.
Dry-run by default.
"""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

FACTORY = Path(__file__).resolve().parent.parent
REGISTRY = FACTORY / "data" / "product_batch_12_gumroad_prep.json"
OUT_DIR = FACTORY / "reports" / "CYCLE104"

VERIFICATION = "reports/CYCLE104/GUMROAD_LISTING_VERIFICATION.json"

CORRECTIONS = {
    "B12-001": {
        "status": "PUBLISHED_AND_VERIFIED 2026-10-19",
        "status_basis": VERIFICATION,
        "status_note": ("live GET /v2/products/:id: published=true, price 1499, "
                        "attachment byte-matches the local workbook"),
    },
    "B12-004": {
        "status": "PUBLISHED_AND_VERIFIED 2026-10-19",
        "status_basis": VERIFICATION,
        "status_note": ("live GET /v2/products/:id: published=true, price 1199, "
                        "both attachments byte-match the local artifacts"),
    },
    "B12-006": {
        "status": "QA_FAIL__NOT_LOCAL_READY",
        "status_basis": "reports/CYCLE104/PRODUCT_QA_RESULTS.json",
        "status_note": ("content-quality layer FAIL 60 (254 words vs 2900 required "
                        "at $29.00); no gate record exists"),
    },
    "B12-007": {
        "status": "QA_FAIL__NOT_LOCAL_READY",
        "status_basis": "reports/CYCLE104/PRODUCT_QA_RESULTS.json",
        "status_note": ("content-quality layer FAIL 60 (273 words vs 1900 required "
                        "at $19.00); zero-formula workbook defect repaired this "
                        "cycle, content depth still unmet; no gate record exists"),
    },
    "B12-008": {
        "status": "QA_FAIL__NOT_LOCAL_READY",
        "status_basis": "reports/CYCLE104/PRODUCT_QA_RESULTS.json",
        "status_note": ("content-quality layer FAIL 60 (273 words vs 2900 required "
                        "at $29.00); budget tracker holds a single formula; no gate record exists"),
    },
    "B12-009": {
        "status": "QA_FAIL__NOT_LOCAL_READY",
        "status_basis": "reports/CYCLE104/PRODUCT_QA_RESULTS.json",
        "status_note": ("content-quality layer FAIL 60 (233 words vs 1900 required "
                        "at $19.00); PDF only, no companion workbook; no gate record exists"),
    },
}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--write-report", action="store_true")
    a = ap.parse_args()

    doc = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    changes = []
    for item in doc.get("items") or []:
        pid = item.get("id")
        corr = CORRECTIONS.get(pid)
        if not corr:
            continue
        before = item.get("status")
        if before == corr["status"] and item.get("status_basis") == corr["status_basis"]:
            continue
        changes.append({"id": pid, "before": before, "after": corr["status"]})
        item.update(corr)

    record = {
        "registry": str(REGISTRY.relative_to(FACTORY)),
        "corrected_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "reason": ("unsupported status claims: stale published state and/or "
                   "LOCAL_READY asserted with no gate record"),
        "changes": changes,
        "applied": False,
    }

    if not a.apply:
        print(json.dumps(record, indent=1, ensure_ascii=False))
        return 0

    doc.setdefault("registry_corrections", []).append(record)
    backup = REGISTRY.with_suffix(".json.cycle104.bak")
    if not backup.exists():
        shutil.copy2(REGISTRY, backup)
    REGISTRY.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    record["applied"] = True
    record["backup"] = str(backup.relative_to(FACTORY))
    print(json.dumps(record, indent=1, ensure_ascii=False))

    if a.write_report:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "PREP_REGISTRY_CORRECTION.json").write_text(
            json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")
        print("written: %s" % (OUT_DIR / "PREP_REGISTRY_CORRECTION.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

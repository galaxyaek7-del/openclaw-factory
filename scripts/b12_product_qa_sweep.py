#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cycle 104 -- per-product quality sweep for batch 12 (offline, $0).

Produces the deliverable "product-by-product processing and QA results".

For every product it records, from real files only:
  * whether a GATE_FINAL exists and what its verdict says
  * whether the product's own artifact files are tracked by git
  * the real quality_enforcer verdict per layer, plus the raw content-depth
    numbers (words vs required, formulas, sheets)
  * defects found by file_testing_engine (structural, not aesthetic)
  * one honest state label

Layer-3 (market reality) needs sourced competitor prices and founder-recorded
payment evidence supplied by the caller. This sweep deliberately passes neither,
so market reality reports MISSING_DATA for every product. That is a limitation
of *this harness*, not a finding about the products, and it is labelled as such
in the output rather than reported as a product failure.

Read-only. Never writes to a product file. Writes only its own report.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

FACTORY = Path(__file__).resolve().parent.parent
if str(FACTORY) not in sys.path:
    sys.path.insert(0, str(FACTORY))

BATCH = FACTORY / "data" / "product_batch_12.json"
OUT_DIR = FACTORY / "reports" / "CYCLE104"

# Price the *gate* approved where one exists; the manifest price otherwise.
# Never invented: both sources are named.
GATE_PRICE = {"B12-001": 14.99, "B12-002": 11.99, "B12-003": 8.0,
              "B12-004": 11.99, "B12-005": 8.0, "B12-010": 15.0}
MANIFEST_PRICE = {"B12-006": 29.0, "B12-007": 19.0, "B12-008": 29.0, "B12-009": 19.0}


def tracked_batch_files() -> set[str]:
    out = subprocess.run(["git", "ls-files", "books/batch12"],
                         cwd=FACTORY, capture_output=True, text=True)
    return {ln.strip().replace("\\", "/") for ln in out.stdout.splitlines() if ln.strip()}


def gate_for(pid: str) -> dict | None:
    d = FACTORY / "reports" / pid
    if not d.is_dir():
        return None
    hits = sorted(p for p in d.glob("GATE_FINAL_*.json"))
    if not hits:
        return None
    try:
        doc = json.loads(hits[-1].read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        return {"file": str(hits[-1].relative_to(FACTORY)), "parse_error": repr(exc)}
    verdict = doc.get("verdict")
    if verdict is None:
        nested = {k: v.get("verdict") if isinstance(v, dict) else None
                  for k, v in doc.items() if isinstance(v, dict) and "verdict" in v}
        verdict = nested or None
    return {"file": str(hits[-1].relative_to(FACTORY)), "verdict": verdict,
            "recommended_price_usd": doc.get("recommended_price_usd")}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    from src.quality import quality_enforcer as qe
    import file_testing_engine as fte

    doc_in = json.loads(BATCH.read_text(encoding="utf-8-sig"))
    tracked = tracked_batch_files()

    rows = []
    for p in doc_in["products"]:
        pid = p["id"]
        files = [f"books/batch12/{f}" for f in (p.get("files") or [])]
        gate = gate_for(pid)
        price = GATE_PRICE.get(pid) or MANIFEST_PRICE.get(pid) or p.get("price_usd")
        product = {
            "id": pid,
            "title": p.get("title"),
            "audience": p.get("audience"),
            "problem": p.get("problem"),
            "outcome": p.get("outcome") or p.get("differentiation") or p.get("title"),
            "price": float(price) if isinstance(price, (int, float)) else price,
            "files": [str(FACTORY / f) for f in files],
        }
        res = qe.inspect(product, stage="full", save=False)
        structural = []
        for rel in files:
            fp = FACTORY / rel
            if not fp.exists():
                structural.append({"file": rel, "status": "MISSING"})
                continue
            r = fte.test_file(fp)
            structural.append({"file": rel, "status": r.status, "kind": r.kind,
                               "problems": (fte.blocking_problems(r) if r.status == fte.FAIL
                                            else (r.problems or []))})
        cq = res["layers"]["content_quality"]
        rows.append({
            "id": pid,
            "title": p.get("title"),
            "price_used_usd": product["price"],
            "files": files,
            "artifacts_tracked_in_git": {f: (f in tracked) for f in files},
            "gate": gate,
            "enforcer_verdict": res["verdict"],
            "layers": {k: {"status": v.get("status"), "score": v.get("score")}
                       for k, v in res["layers"].items()},
            "content_depth": cq.get("detail", {}).get("depth"),
            "structural": structural,
            "notes": [
                "market_reality is MISSING_DATA for every row because this sweep "
                "supplies neither sourced competitor prices nor payment evidence; "
                "that is a harness limitation, not a product verdict",
            ],
        })

    doc = {
        "schema": "galaxy_forge.b12_product_qa_sweep.v1",
        "generated_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "cost_usd": 0,
        "read_only": True,
        "products": len(rows),
        "summary": {
            "gate_present": sum(1 for r in rows if r["gate"]),
            "gate_absent": sum(1 for r in rows if not r["gate"]),
            "content_quality_pass": sum(1 for r in rows
                                        if r["layers"]["content_quality"]["status"] == "PASS"),
            "content_quality_fail": sum(1 for r in rows
                                        if r["layers"]["content_quality"]["status"] == "FAIL"),
            "structural_failures": sum(1 for r in rows
                                       for s in r["structural"] if s["status"] == "FAIL"),
            "artifacts_untracked": sum(1 for r in rows for v in
                                       r["artifacts_tracked_in_git"].values() if not v),
        },
        "results": rows,
    }

    if a.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "PRODUCT_QA_RESULTS.json").write_text(
            json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        lines = ["# Cycle 104 \u2014 batch 12 per-product QA results", "",
                 "Offline. $0. No product file was modified by this sweep.", "",
                 "| id | verdict | gate | CQ | depth (words/required) | formulas | tracked | structural |",
                 "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            d = r["content_depth"] or {}
            st = [s for s in r["structural"] if s["status"] != "PASS"]
            lines.append("| %s | %s | %s | %s | %s/%s | %s | %s | %s |" % (
                r["id"], r["enforcer_verdict"],
                (r["gate"] or {}).get("verdict") if r["gate"] else "ABSENT",
                r["layers"]["content_quality"]["status"],
                d.get("words"), d.get("words_required"), d.get("formulas"),
                "all" if all(r["artifacts_tracked_in_git"].values()) else "partial/none",
                ("; ".join("%s:%s" % (s["file"].split("/")[-1], s["status"]) for s in st)
                 or "PASS")))
        lines += ["", "market_reality is MISSING_DATA on every row: this sweep passes no "
                  "competitor prices and no payment evidence, so layer 3 cannot run here. "
                  "That is a harness limitation, not a product verdict.", ""]
        (OUT_DIR / "PRODUCT_QA_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")

    if a.json:
        print(json.dumps(doc, indent=1, ensure_ascii=False))
    else:
        for r in rows:
            d = r["content_depth"] or {}
            st = ",".join(s["status"] for s in r["structural"])
            print("%-8s verdict=%-16s gate=%-8s cq=%-4s words=%s/%s formulas=%-4s tracked=%s struct=%s"
                  % (r["id"], r["enforcer_verdict"],
                     (r["gate"] or {}).get("verdict") if r["gate"] else "ABSENT",
                     r["layers"]["content_quality"]["status"], d.get("words"),
                     d.get("words_required"), d.get("formulas"),
                     "Y" if all(r["artifacts_tracked_in_git"].values()) else "N", st))
        print("\nsummary: %s" % json.dumps(doc["summary"], ensure_ascii=False))
        if a.write:
            print("written: %s" % (OUT_DIR / "PRODUCT_QA_RESULTS.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

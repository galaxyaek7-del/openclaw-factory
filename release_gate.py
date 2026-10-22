#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge -- product release gate (2026-10-22).

WHY THIS EXISTS
---------------
The Gumroad delivery audit (scripts/gumroad_delivery_audit.py) found live,
paid listings that promise files they do not deliver (GPSR: "PDF guide + PDF
cost planner", only the guide attached), and ~20 paid products whose whole
deliverable is a 1-2 page PDF. Each piece of QA already existed --
file_testing_engine.py tests files by type, content_qa.py catches residue --
but nothing joined "what the listing promises" with "what the buyer receives"
before a product was called ready.

This module is that join. It evaluates a product's local deliverables and
listing copy through the pipeline stages up to AUTHORIZATION_CHECK and stops
there. It has no publish path: the furthest status it can assign is
READY_FOR_AUTHORIZATION. PUBLISHED_VERIFIED can only come from a platform
record, never from here.

Reuses, never re-implements: file_testing_engine (per-type file tests),
affiliate.content_qa (residue/banned phrases), scripts.gumroad_delivery_audit
(promise-vs-delivery rules).

State: data/release_gate_state.jsonl, append-only. A result is recorded once
per (product_id, fingerprint); re-running unchanged inputs records nothing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import file_testing_engine as fte
from affiliate.content_qa import qa_content
from scripts.gumroad_delivery_audit import classify as classify_listing

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "data" / "release_gate_state.jsonl"

STAGES = ("OPPORTUNITY_DISCOVERY", "DEMAND_EVIDENCE", "PRODUCT_SPECIFICATION", "PRODUCTION",
          "QUALITY_ASSURANCE", "RIGHTS_AND_POLICY_REVIEW", "PACKAGING", "LISTING_PREPARATION",
          "DISTRIBUTION_PREPARATION", "AUTHORIZATION_CHECK", "PUBLICATION_IF_AUTHORIZED",
          "MEASUREMENT", "LEARNING_AND_IMPROVEMENT")
STATUSES = ("PLANNED", "RESEARCHING", "IN_PROGRESS", "QA_FAILED", "QA_PASSED",
            "READY_FOR_AUTHORIZATION", "PUBLISHED_VERIFIED", "BLOCKED", "HOLD", "ARCHIVED")
# The only statuses this module may assign. PUBLISHED_VERIFIED is deliberately absent.
ASSIGNABLE = ("QA_FAILED", "HOLD", "READY_FOR_AUTHORIZATION")

# Substance relative to price: a paid product whose only content is a short
# PDF and that ships no working tool is held for a human pricing decision.
# Disclosed heuristic (the live thin products measured 135-618 words).
MIN_WORDS_PER_DOLLAR = 25
EXPERIMENTAL_PRICE_LABEL = "experimental"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(paths) -> list:
    out = []
    for p in map(Path, paths):
        out.append({"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p),
                    "kind": fte.detect_kind(p)})
    return out


def _pdf_words(path: Path) -> int | None:
    try:
        from pypdf import PdfReader
        return sum(len((pg.extract_text() or "").split()) for pg in PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001 -- unreadable text is UNKNOWN, not zero
        return None


def evaluate(product_id: str, deliverables, listing_text: str, price_usd: float,
             demand_evidence: str | None = None, rights_review: dict | None = None,
             price_basis: str | None = None) -> dict:
    """Pure evaluation (no writes). Returns a record with per-stage results
    and one status from ASSIGNABLE."""
    paths = [Path(p) for p in deliverables]
    stages, blocking, holds = {}, [], []

    stages["DEMAND_EVIDENCE"] = {"status": "PASS" if demand_evidence else "UNKNOWN",
                                 "evidence": demand_evidence}
    if not demand_evidence:
        holds.append("no demand evidence recorded")

    missing = [str(p) for p in paths if not p.exists()]
    if not paths or missing:
        blocking.append("deliverables missing: " + (", ".join(missing) or "none given"))
        return _result(product_id, None, stages, blocking, holds, price_usd)

    file_results = [fte.test_file(p) for p in paths]
    qa_problems = [f"{Path(r.path).name}: {x}" for r in file_results for x in fte.blocking_problems(r)]
    unknown = [Path(r.path).name for r in file_results if r.status == fte.UNKNOWN]
    stages["QUALITY_ASSURANCE"] = {"status": "FAIL" if qa_problems else ("UNKNOWN" if unknown else "PASS"),
                                   "files": [r.as_dict() for r in file_results]}
    blocking += qa_problems
    if unknown:
        blocking.append("files that could not be tested: " + ", ".join(unknown))

    manifest = build_manifest(paths)
    stages["PACKAGING"] = {"status": "PASS", "manifest": manifest}

    # Listing promise vs. what is actually in the package (same rules as the live audit).
    synthetic = {"published": True, "price": int(round(price_usd * 100)), "description": listing_text,
                 "files": [{"filetype": m["name"].rsplit(".", 1)[-1].lower(), "size": m["bytes"],
                            "name": m["name"]} for m in manifest]}
    # THIN_DELIVERABLE is the live audit's byte-size proxy; here substance is
    # judged on real word counts below, and as a HOLD (pricing call), not a failure.
    listing_issues = [i for i in classify_listing(synthetic)["issues"]
                      if i not in ("ZIP_CONTENTS_UNVERIFIED", "THIN_DELIVERABLE")]
    copy_qa = qa_content({"title": product_id, "body": listing_text, "disclosure": True, "cta_present": True})
    copy_failures = [f for f in copy_qa["failures"] if not f.startswith(("affiliate disclosure", "no CTA"))]
    stages["LISTING_PREPARATION"] = {"status": "FAIL" if (listing_issues or copy_failures) else "PASS",
                                     "promise_issues": listing_issues, "copy_failures": copy_failures}
    blocking += listing_issues + copy_failures

    # Substance vs. price: only judged when no working tool (formulas) ships.
    has_tool = any(r.kind == "xlsx" and (r.detail.get("formula_count") or 0) > 0 for r in file_results)
    words = [w for w in (_pdf_words(p) for p in paths if p.suffix.lower() == ".pdf") if w is not None]
    total_words = sum(words) if words else None
    substance = {"has_working_tool": has_tool, "pdf_words": total_words}
    if price_usd > 0 and not has_tool and total_words is not None \
            and total_words < MIN_WORDS_PER_DOLLAR * price_usd and price_basis != EXPERIMENTAL_PRICE_LABEL:
        holds.append(f"substance below price: {total_words} words for ${price_usd:g} "
                     f"(<{MIN_WORDS_PER_DOLLAR}/$) and no working tool -- expand, reprice, or label experimental")
    stages["QUALITY_ASSURANCE"]["substance"] = substance

    if rights_review and rights_review.get("reviewer") and rights_review.get("basis"):
        stages["RIGHTS_AND_POLICY_REVIEW"] = {"status": "PASS", **rights_review}
    else:
        stages["RIGHTS_AND_POLICY_REVIEW"] = {"status": "PENDING"}
        holds.append("human rights/policy review not recorded")

    return _result(product_id, manifest, stages, blocking, holds, price_usd)


def _result(product_id, manifest, stages, blocking, holds, price_usd):
    status = "QA_FAILED" if blocking else ("HOLD" if holds else "READY_FOR_AUTHORIZATION")
    stages["AUTHORIZATION_CHECK"] = {
        "status": "AWAITING_FOUNDER" if status == "READY_FOR_AUTHORIZATION" else "NOT_REACHED",
        "note": "publication requires explicit founder authorization; this module never publishes"}
    fingerprint = hashlib.sha256(json.dumps(
        {"m": [(m["name"], m["sha256"]) for m in (manifest or [])], "b": blocking, "h": holds,
         "p": price_usd}, sort_keys=True).encode()).hexdigest()[:16]
    return {"product_id": product_id, "status": status, "blocking": blocking, "holds": holds,
            "stages": stages, "fingerprint": fingerprint,
            "evaluated_at": datetime.now(timezone.utc).isoformat()}


def record(result: dict, state_path=None) -> bool:
    """Append once per (product_id, fingerprint). Returns True if written."""
    assert result["status"] in ASSIGNABLE, "release gate may not assign " + result["status"]
    path = Path(state_path) if state_path else STATE_PATH
    key = (result["product_id"], result["fingerprint"])
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if (row.get("product_id"), row.get("fingerprint")) == key:
                return False
    path.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: result[k] for k in ("product_id", "status", "blocking", "holds", "fingerprint", "evaluated_at")}
    slim["manifest"] = (result["stages"].get("PACKAGING") or {}).get("manifest")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(slim, ensure_ascii=False) + "\n")
    return True


def latest(product_id: str, state_path=None) -> dict | None:
    path = Path(state_path) if state_path else STATE_PATH
    last = None
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("product_id") == product_id:
                last = row
    return last

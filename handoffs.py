"""Internal handoff contracts (Permanent Operating Doctrine, section 3D).

Every material handoff between arms states the same seven things: who sends,
who receives, what is delivered, what acceptance means, who owns it, when it is
due (or that the target is genuinely unknown), and what evidence proves
acceptance. Without that, a blocked arm silently stalls work and the next reader
cannot tell "waiting" from "done".

`data/handoffs.jsonl` is append-only. A handoff advances by recording a new
entry with the same `handoff_id` and a new `status`, so the delay is visible in
history rather than overwritten.

Honesty rules baked in:
  * a `BLOCKED` handoff must name the blocking dependency in `delay_reason`;
  * `due` may be the string `UNKNOWN` -- the factory has no per-stage duration
    model, so inventing a date would be fabrication;
  * `ACCEPTED` requires at least one real evidence path that exists.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "data" / "handoffs.jsonl"

STATUSES = ("PENDING", "IN_PROGRESS", "ACCEPTED", "REJECTED", "BLOCKED", "CANCELLED")
TERMINAL = ("ACCEPTED", "REJECTED", "CANCELLED")
REQUIRED_FIELDS = (
    "handoff_id",
    "recorded_at",
    "sender",
    "receiver",
    "deliverable",
    "acceptance_criteria",
    "owner",
    "due",
    "evidence_required",
    "status",
    "evidence",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_path(path: Optional[Path]) -> Path:
    return Path(path) if path else DEFAULT_PATH


def load_handoffs(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = _default_path(path)
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def latest_by_id(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for record in load_handoffs(path):
        latest[record["handoff_id"]] = record
    return latest


def validate_handoff(record: Dict[str, Any], root: Path = ROOT) -> List[str]:
    problems: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            problems.append("missing field: " + field)

    if record.get("status") not in STATUSES:
        problems.append("status must be one of %s" % (STATUSES,))

    for field in ("acceptance_criteria", "evidence_required", "evidence"):
        value = record.get(field)
        if not isinstance(value, list) or not value:
            problems.append(field + " must be a non-empty list")

    for field in ("sender", "receiver", "deliverable", "owner", "due"):
        if field in record and not record[field]:
            problems.append(field + " must not be empty")

    if record.get("status") == "BLOCKED" and not record.get("delay_reason"):
        problems.append("a BLOCKED handoff must state delay_reason")

    if record.get("status") == "ACCEPTED":
        for ref in record.get("evidence") or []:
            if ref == "none":
                problems.append("ACCEPTED requires real evidence, not 'none'")
            elif not (root / ref).exists():
                problems.append("ACCEPTED evidence does not exist: " + str(ref))

    return problems


def record_handoff(record: Dict[str, Any], path: Optional[Path] = None,
                   root: Path = ROOT, dry_run: bool = False) -> Dict[str, Any]:
    path = _default_path(path)
    record = dict(record)
    record.setdefault("recorded_at", _now_iso())
    problems = validate_handoff(record, root)
    if problems:
        raise ValueError("invalid handoff: " + "; ".join(problems))

    latest = latest_by_id(path).get(record["handoff_id"])
    if latest and latest.get("status") == record.get("status") and \
            latest.get("delay_reason") == record.get("delay_reason"):
        return {"written": False, "reason": "no change", "handoff_id": record["handoff_id"]}
    if dry_run:
        return {"written": False, "reason": "dry run", "handoff_id": record["handoff_id"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {"written": True, "handoff_id": record["handoff_id"]}


def open_handoffs(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    return [r for r in latest_by_id(path).values() if r.get("status") not in TERMINAL]


def delays(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    return [r for r in open_handoffs(path)
            if r.get("status") == "BLOCKED" or r.get("delay_reason")]


# Real handoffs implied by the batch-12 evidence in data/operational_history.json.
def seed_records() -> List[Dict[str, Any]]:
    """The real handoffs implied by the batch-12 evidence, with common fields filled in."""
    common = {"owner": "factory", "due": "UNKNOWN",
              "recorded_at": "2026-10-19T00:00:00+00:00"}
    seeds = [
        {
            "handoff_id": "H-B12-010-PROD-QA", "sender": "production", "receiver": "qa",
            "deliverable": "B12-010 workbook + guide + cover at the release hashes",
            "acceptance_criteria": ["quality gate APPROVED", "native workbook QA PASS", "artifact hash matches the manifest"],
            "evidence_required": ["reports/B12-010/GATE_FINAL_2026-10-19.json", "reports/B12-010/WORKBOOK_QA_2026-10-19.json"],
            "status": "ACCEPTED",
            "evidence": ["reports/B12-010/GATE_FINAL_2026-10-19.json", "reports/B12-010/WORKBOOK_QA_2026-10-19.json"],
        },
        {
            "handoff_id": "H-B12-010-QA-COMMERCE", "sender": "qa", "receiver": "commerce",
            "deliverable": "approved B12-010 release package at $15.00",
            "acceptance_criteria": ["gate PASS", "price derived by the standing rule", "listing copy brand-validated"],
            "evidence_required": ["reports/B12-010/RELEASE_BASELINE_2026-10-19.json"],
            "status": "BLOCKED",
            "delay_reason": "no product-specific founder authorization phrase exists",
            "evidence": ["reports/B12-010/PUBLICATION_READINESS_2026-10-19.md"],
        },
        {
            "handoff_id": "H-B12-002-QA-COMMERCE", "sender": "qa", "receiver": "commerce",
            "deliverable": "approved B12-002 release package at $11.99",
            "acceptance_criteria": ["gate APPROVED at the recommended price"],
            "evidence_required": ["reports/B12-002/GATE_FINAL_2026-10-18.json"],
            "status": "PENDING",
            "delay_reason": "publication not authorized",
            "evidence": ["reports/B12-002/GATE_FINAL_2026-10-18.json"],
        },
        {
            "handoff_id": "H-B12-005-QA-COMMERCE", "sender": "qa", "receiver": "commerce",
            "deliverable": "approved B12-005 release package at $8.00",
            "acceptance_criteria": ["gate APPROVED"],
            "evidence_required": ["reports/B12-005/GATE_FINAL_2026-10-19.json"],
            "status": "BLOCKED",
            "delay_reason": "publication not authorized; readiness verified but no authorization phrase exists",
            "evidence": ["reports/B12-005/GATE_FINAL_2026-10-19.json"],
        },
        {
            "handoff_id": "H-B12-001-COMMERCE-DIST", "sender": "commerce", "receiver": "distribution",
            "deliverable": "B12-001 live listing",
            "acceptance_criteria": ["public page served", "checkout URL present", "served file hash matches"],
            "evidence_required": ["data/cycle94_live_verification.json"],
            "status": "ACCEPTED",
            "evidence": ["data/cycle94_live_verification.json"],
        },
        {
            "handoff_id": "H-B12-003-COMMERCE-DIST", "sender": "commerce", "receiver": "distribution",
            "deliverable": "B12-003 live listing at $8.00",
            "acceptance_criteria": ["public page served", "checkout URL present"],
            "evidence_required": ["data/cycle99_b12_003_live_verification.json"],
            "status": "ACCEPTED",
            "evidence": ["data/cycle99_b12_003_live_verification.json"],
        },
        {
            "handoff_id": "H-B12-004-COMMERCE-DIST", "sender": "commerce", "receiver": "distribution",
            "deliverable": "B12-004 live listing at $11.99",
            "acceptance_criteria": ["public page served", "checkout URL present"],
            "evidence_required": ["data/cycle98_b12_004_live_verification.json"],
            "status": "ACCEPTED",
            "evidence": ["data/cycle98_b12_004_live_verification.json"],
        },
    ]
    for product in ("B12-006", "B12-007", "B12-008", "B12-009"):
        seeds.append({
            "handoff_id": "H-%s-PROD-QA" % product,
            "sender": "production", "receiver": "qa",
            "deliverable": "%s artifacts turned over for a real quality gate" % product,
            "acceptance_criteria": ["a GATE_FINAL record with an explicit verdict"],
            "evidence_required": ["reports/%s/GATE_FINAL_*.json" % product],
            "status": "BLOCKED",
            "delay_reason": "no reports/%s/ gate record exists; QA has never run on these artifacts" % product,
            "evidence": ["data/operational_history.json"],
        })

    return [dict(common, **record) for record in seeds]


def seed(path: Optional[Path] = None, root: Path = ROOT) -> Dict[str, int]:
    seeds = seed_records()
    written = skipped = 0
    for record in seeds:
        result = record_handoff(record, path=path, root=root)
        if result["written"]:
            written += 1
        else:
            skipped += 1
    return {"written": written, "skipped": skipped, "total": len(seeds)}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Internal handoff contracts")
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args(argv)
    if args.seed:
        print(json.dumps(seed(), indent=1))
    if args.audit:
        latest = latest_by_id()
        problems = []
        for hid, record in latest.items():
            for problem in validate_handoff(record):
                problems.append({"handoff_id": hid, "problem": problem})
        print(json.dumps({"handoffs": len(latest), "problems": problems,
                          "ok": not problems}, ensure_ascii=False, indent=1))
        if problems:
            return 1
    if args.open:
        for record in open_handoffs():
            print("%-26s %-12s -> %-12s %s" % (
                record["handoff_id"], record["sender"], record["receiver"],
                record.get("delay_reason") or record.get("status")))
    if not any((args.seed, args.audit, args.open)):
        print(json.dumps({"handoffs": len(latest_by_id())}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

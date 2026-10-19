"""Rework and cycle-time measurement (Permanent Operating Doctrine, section 4).

The factory already produces cycle reports, but no record answered the questions
that make a cycle cheaper next time: what changed, which checks were *new* and
which were *repeated and why*, how much of the work was rework, and whether a
capability survived the cycle. Without that, "another cycle" and "progress" look
identical in a report count.

This module stores one proportional record per cycle in
`data/cycle_metrics.jsonl`. It measures only what is measurable:

  * file/insertion counts come from real git ranges when a range is given;
  * test durations come from the real pytest output when recorded;
  * wall-clock time spent thinking/working is `UNKNOWN` unless it was actually
    measured -- the doctrine forbids inventing it, and no timer is wired into
    the session, so claiming minutes would be fabrication.

`repetition_audit()` flags a cycle that produced no artifact, no repair, no
validated capability, and no decision-relevant evidence, and flags two
consecutive cycles with identical deliverables -- the two honest signatures of
avoidable repetition.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "data" / "cycle_metrics.jsonl"

TIME_BUCKETS = ("production", "testing", "investigation", "documentation", "blocked")
REQUIRED_FIELDS = (
    "cycle",
    "recorded_at",
    "commit_range",
    "changed_since_previous",
    "deliverables",
    "checks_new",
    "checks_repeated",
    "defects",
    "rework",
    "time",
    "new_capability",
    "next_action",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_path(path: Optional[Path]) -> Path:
    return Path(path) if path else DEFAULT_PATH


def load_cycles(path: Optional[Path] = None) -> List[Dict[str, Any]]:
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


def validate_cycle(record: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            problems.append("missing field: " + field)

    if not isinstance(record.get("cycle"), int) or record.get("cycle", 0) <= 0:
        problems.append("cycle must be a positive integer")

    for field in ("deliverables", "checks_new", "checks_repeated"):
        if field in record and not isinstance(record[field], list):
            problems.append(field + " must be a list")

    for entry in record.get("checks_repeated") or []:
        if not isinstance(entry, dict) or not entry.get("check") or not entry.get("reason"):
            problems.append("every repeated check needs a check name and a reason")

    if not isinstance(record.get("changed_since_previous"), dict):
        problems.append("changed_since_previous must be an object")
    else:
        changed = record["changed_since_previous"]
        if not isinstance(changed.get("files"), int):
            problems.append("changed_since_previous.files must be an integer")
        if changed.get("files", 0) and not record.get("commit_range"):
            problems.append("a non-empty change needs a commit_range")

    defects = record.get("defects")
    if not isinstance(defects, dict):
        problems.append("defects must be an object")
    else:
        for severity in ("critical", "high", "medium", "low"):
            if not isinstance(defects.get(severity, 0), int):
                problems.append("defects.%s must be an integer" % severity)

    rework = record.get("rework")
    if not isinstance(rework, dict):
        problems.append("rework must be an object")
    else:
        for field in ("new_defects", "preexisting"):
            if not isinstance(rework.get(field), int):
                problems.append("rework.%s must be an integer" % field)

    timing = record.get("time")
    if not isinstance(timing, dict):
        problems.append("time must be an object")
    else:
        if timing.get("measured") not in (True, False):
            problems.append("time.measured must be true or false")
        if timing.get("measured") is True:
            for bucket in TIME_BUCKETS:
                if not isinstance((timing.get("seconds") or {}).get(bucket), (int, float)):
                    problems.append("measured time needs a seconds value for " + bucket)
        else:
            if not timing.get("reason"):
                problems.append("unmeasured time needs a reason")

    if not record.get("new_capability") and not record.get("no_new_capability_reason"):
        problems.append("record a new capability or state why the cycle produced none")
    if not record.get("next_action"):
        problems.append("next_action is required")

    for ref in record.get("evidence") or []:
        if not (ROOT / ref).exists():
            problems.append("evidence path does not exist: " + str(ref))
    return problems


def record_cycle(record: Dict[str, Any], path: Optional[Path] = None,
                 dry_run: bool = False) -> Dict[str, Any]:
    path = _default_path(path)
    record = dict(record)
    record.setdefault("recorded_at", _now_iso())
    problems = validate_cycle(record)
    if problems:
        raise ValueError("invalid cycle record: " + "; ".join(problems))
    existing = load_cycles(path)
    if any(c.get("cycle") == record["cycle"] for c in existing):
        return {"written": False, "reason": "cycle already recorded", "cycle": record["cycle"]}
    if dry_run:
        return {"written": False, "reason": "dry run", "cycle": record["cycle"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {"written": True, "cycle": record["cycle"]}


def rework_ratio(record: Dict[str, Any]) -> Optional[float]:
    rework = record.get("rework") or {}
    new = rework.get("new_defects", 0)
    pre = rework.get("preexisting", 0)
    total = new + pre
    if total == 0:
        return None
    return round(new / total, 3)


def repetition_audit(path: Optional[Path] = None) -> Dict[str, Any]:
    cycles = sorted(load_cycles(path), key=lambda c: c.get("cycle", 0))
    findings = []
    for record in cycles:
        defects = record.get("defects") or {}
        productive = (
            (record.get("changed_since_previous") or {}).get("files", 0) > 0
            or any((record.get("defects") or {}).get(s, 0) for s in ("critical", "high", "medium", "low"))
            or record.get("new_capability")
            or record.get("decision_relevant_evidence")
        )
        if not productive:
            findings.append({
                "cycle": record.get("cycle"),
                "finding": "cycle produced no artifact, repair, capability, or decision-relevant evidence",
            })
    for previous, current in zip(cycles, cycles[1:]):
        if (previous.get("deliverables") and
                previous.get("deliverables") == current.get("deliverables")):
            findings.append({
                "cycle": current.get("cycle"),
                "finding": "identical deliverables to cycle %s" % previous.get("cycle"),
            })
    return {"cycles": len(cycles), "findings": findings, "ok": not findings}


def summary(path: Optional[Path] = None) -> Dict[str, Any]:
    cycles = load_cycles(path)
    defects = {s: sum((c.get("defects") or {}).get(s, 0) for c in cycles)
               for s in ("critical", "high", "medium", "low")}
    new_rework = sum((c.get("rework") or {}).get("new_defects", 0) for c in cycles)
    pre_rework = sum((c.get("rework") or {}).get("preexisting", 0) for c in cycles)
    measured = [c for c in cycles if (c.get("time") or {}).get("measured")]
    return {
        "cycles": len(cycles),
        "defects_total": defects,
        "rework": {"new_defects": new_rework, "preexisting": pre_rework,
                   "new_share": (round(new_rework / (new_rework + pre_rework), 3)
                                 if (new_rework + pre_rework) else None)},
        "time_measured_cycles": len(measured),
        "time_unmeasured_cycles": len(cycles) - len(measured),
    }


# Two real cycles, reconstructed from git ranges and the records each produced.
SEED_CYCLES: List[Dict[str, Any]] = [
    {
        "cycle": 101,
        "recorded_at": "2026-10-19T00:00:00+00:00",
        "commit_range": "4e6a7c8..b2e2f34",
        "changed_since_previous": {"files": 12, "insertions": 832, "deletions": 19},
        "deliverables": [
            "books/batch12/B12-010_grant_pipeline_tracker.xlsx (formats repaired)",
            "tests/test_b12_010_workbook.py (format regression test)",
            "reports/B12-010/NATIVE_RECALC_EXCEL_2026-10-19.json",
            "reports/B12-010/GATE_METHOD_2026-10-19.md",
            "reports/B12-010/RELEASE_BASELINE_2026-10-19.json",
            "reports/B12-010/TEST_EVIDENCE_2026-10-19.json",
            "reports/CYCLE101_B12-010_VERIFICATION_2026-10-19.md",
        ],
        "checks_new": ["native Excel recalculation of every Dashboard cell"],
        "checks_repeated": [
            {"check": "workbook value/formula inspection", "reason": "formats changed, so released bytes changed"},
            {"check": "bounded pytest group", "reason": "a regression test was added to the module under test"},
        ],
        "defects": {"critical": 0, "high": 7, "medium": 0, "low": 0},
        "rework": {"new_defects": 7, "preexisting": 0},
        "time": {"measured": False, "reason": "no session timer exists; only pytest durations are real (about 10.4s across the two runs)"},
        "new_capability": "native recalculation as a defect-finding technique; a permanent format regression test",
        "next_action": "make the native recalculation reusable so the next workbook cannot ship a display defect",
        "evidence": [
            "reports/CYCLE101_B12-010_VERIFICATION_2026-10-19.md",
            "reports/B12-010/TEST_EVIDENCE_2026-10-19.json",
        ],
    },
    {
        "cycle": 102,
        "recorded_at": "2026-10-19T00:00:00+00:00",
        "commit_range": "b2e2f34..9a096b0",
        "changed_since_previous": {"files": 17, "insertions": 3443, "deletions": 88},
        "deliverables": [
            "native_workbook_qa.py",
            "scripts/excel_recalc_probe.ps1",
            "tests/test_native_workbook_qa.py",
            "operational_history.py + data/operational_history.json",
            "PRODUCTION_TO_PUBLISHING_PLAYBOOK.md",
            "reports/OPERATIONAL_LEARNING_BASELINE.md",
            "reports/B12-010/PUBLICATION_READINESS_2026-10-19.md",
            "scripts/check_b12_integrity.py (workbook QA gate)",
        ],
        "checks_new": [
            "reusable native workbook QA (format vs number kind, error cells, artifact hash)",
            "evidence-based release-state invariants",
            "integrity gate for a recorded native PASS",
        ],
        "checks_repeated": [
            {"check": "native Excel recalculation", "reason": "the release evidence had to match the artifact after record edits"},
            {"check": "bounded pytest group", "reason": "new tests were added and shared modules were changed"},
            {"check": "B12 integrity check", "reason": "the gate itself changed"},
        ],
        "defects": {"critical": 0, "high": 0, "medium": 2, "low": 0},
        "rework": {"new_defects": 0, "preexisting": 2},
        "time": {"measured": False, "reason": "no session timer exists; pytest totals are real (153 passed in 6.26s; 17 passed in 1.23s)"},
        "new_capability": "native workbook QA is reusable and gated; release state is reconstructed from evidence instead of reported from prose",
        "next_action": "turn the remaining doctrine layers into checks instead of prose",
        "evidence": [
            "reports/CYCLE102_B12-010_OPERATIONAL_LEARNING_2026-10-19.md",
            "reports/B12-010/CYCLE102_FINAL_EVIDENCE_2026-10-19.json",
        ],
    },
]


def seed(path: Optional[Path] = None) -> Dict[str, int]:
    written = skipped = 0
    for record in SEED_CYCLES:
        result = record_cycle(record, path=path)
        if result["written"]:
            written += 1
        else:
            skipped += 1
    return {"written": written, "skipped": skipped, "total": len(SEED_CYCLES)}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Rework and cycle-time metrics")
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    if args.seed:
        print(json.dumps(seed(), indent=1))
    if args.audit:
        result = repetition_audit()
        print(json.dumps(result, ensure_ascii=False, indent=1))
        if not result["ok"]:
            return 1
    if args.summary:
        print(json.dumps(summary(), ensure_ascii=False, indent=1))
    if not any((args.seed, args.audit, args.summary)):
        print(json.dumps(summary(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

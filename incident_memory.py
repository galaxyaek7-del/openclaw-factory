"""Permanent incident memory (Permanent Operating Doctrine, section 3A).

`data/incidents.jsonl` already exists and is written by `resilience_monitor.py`.
It answers a narrow question -- "is this subsystem critical right now, and was
the incident opened/closed?" -- with four fields (incident_id, area, event,
detail). It is an *alert stream*, not an incident record: it has no root cause,
no detection mechanism, no corrective action, and no preventive control, so a
recurring defect can close there and immediately recur.

This module is the durable record the doctrine asks for. It is deliberately
proportional:

  * one record per *material* incident, not per failed check;
  * every record must name a real preventive control (a test, gate, rule, or
    procedure that a later reader can open) or say explicitly that none exists;
  * a verified root cause and a hypothesis are stored in different fields, so a
    guess can never read like a finding;
  * `audit()` fails a record whose preventive control path does not exist, whose
    verification is missing, or that claims a cause it did not verify.

It does not replace `data/incidents.jsonl` and does not write to it. The two
serve different purposes and the doctrine forbids merging distinct states.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "data" / "incident_memory.jsonl"

LABELS = ("OBSERVED", "DERIVED", "INFERRED", "ESTIMATED", "UNKNOWN", "BLOCKED")
SEVERITIES = ("low", "medium", "high", "critical")
VERIFICATION_STATUSES = ("PASS", "FAIL", "PARTIAL", "UNKNOWN", "BLOCKED")
CONTROL_KINDS = ("test", "gate", "rule", "procedure")

REQUIRED_FIELDS = (
    "incident_id",
    "recorded_at",
    "title",
    "severity",
    "what_failed",
    "component",
    "evidence",
    "detection_mechanism",
    "why_not_caught",
    "root_cause",
    "corrective_action",
    "preventive_control",
    "rules_left_unchanged",
    "verification",
    "remaining_uncertainty",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_incident_id(title: str, component: str) -> str:
    return "INC-" + hashlib.sha256(
        f"{title}|{component}".encode("utf-8")
    ).hexdigest()[:12]


def _default_path(path: Optional[Path]) -> Path:
    return Path(path) if path else DEFAULT_PATH


def _read(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _append(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def validate_record(record: Dict[str, Any], root: Path = ROOT) -> List[str]:
    """Return a list of problems. An empty list means the record is admissible."""
    problems: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            problems.append("missing field: " + field)

    if record.get("severity") not in SEVERITIES:
        problems.append("severity must be one of %s" % (SEVERITIES,))

    for field in ("evidence", "rules_left_unchanged"):
        if field in record and not isinstance(record[field], list):
            problems.append(field + " must be a list")

    cause = record.get("root_cause") or {}
    if not isinstance(cause, dict):
        problems.append("root_cause must be an object")
    else:
        verified = cause.get("verified") or []
        hypothesis = cause.get("hypothesis") or []
        if not verified and not hypothesis:
            problems.append("root_cause must record a verified cause or an explicit hypothesis")
        if not isinstance(verified, list) or not isinstance(hypothesis, list):
            problems.append("root_cause.verified/hypothesis must be lists")

    control = record.get("preventive_control")
    if not isinstance(control, dict):
        problems.append("preventive_control must be an object")
    else:
        kind = control.get("kind")
        if kind not in CONTROL_KINDS:
            problems.append("preventive_control.kind must be one of %s" % (CONTROL_KINDS,))
        ref = control.get("ref")
        if not ref:
            problems.append("preventive_control.ref is required (path, id, or explicit 'none')")
        elif ref != "none":
            if not (root / ref).exists():
                problems.append("preventive_control.ref does not exist: " + str(ref))
        if not control.get("description"):
            problems.append("preventive_control.description is required")

    verification = record.get("verification") or {}
    if not isinstance(verification, dict):
        problems.append("verification must be an object")
    else:
        if verification.get("status") not in VERIFICATION_STATUSES:
            problems.append("verification.status must be one of %s" % (VERIFICATION_STATUSES,))
        if not verification.get("evidence"):
            problems.append("verification.evidence is required")

    detection = record.get("detection_mechanism") or {}
    if not isinstance(detection, dict) or not detection.get("status"):
        problems.append("detection_mechanism.status is required")
    else:
        if detection["status"] not in ("EXISTED_AND_FIRED", "EXISTED_AND_MISSED", "DID_NOT_EXIST"):
            problems.append("detection_mechanism.status is not a recognised value")

    for field in ("recorded_at", "what_failed", "component", "title",
                  "corrective_action", "why_not_caught", "remaining_uncertainty"):
        if field in record and not record[field]:
            problems.append(field + " must not be empty")

    return problems


def record_incident(record: Dict[str, Any], path: Optional[Path] = None,
                    root: Path = ROOT, dry_run: bool = False) -> Dict[str, Any]:
    """Validate and append one incident. Identical ids are never duplicated."""
    path = _default_path(path)
    record = dict(record)
    record.setdefault("recorded_at", _now_iso())
    record.setdefault("incident_id", _make_incident_id(record.get("title", ""), record.get("component", "")))

    problems = validate_record(record, root)
    if problems:
        raise ValueError("invalid incident record: " + "; ".join(problems))

    existing = _read(path)
    if any(r.get("incident_id") == record["incident_id"] for r in existing):
        return {"written": False, "reason": "already recorded", "incident_id": record["incident_id"]}
    if dry_run:
        return {"written": False, "reason": "dry run", "incident_id": record["incident_id"]}
    _append(path, record)
    return {"written": True, "incident_id": record["incident_id"]}


def list_incidents(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    return _read(_default_path(path))


def search_incidents(query: str, path: Optional[Path] = None) -> List[Dict[str, Any]]:
    needle = query.lower().strip()
    if not needle:
        return []
    hits = []
    for record in _read(_default_path(path)):
        haystack = json.dumps(record, ensure_ascii=False).lower()
        if needle in haystack:
            hits.append(record)
    return hits


def _unprevented(record: Dict[str, Any]) -> bool:
    control = record.get("preventive_control") or {}
    return control.get("ref") in (None, "", "none") or not control.get("description")


def audit(path: Optional[Path] = None, root: Path = ROOT) -> Dict[str, Any]:
    """Re-validate the whole store and surface recurrence risk."""
    path = _default_path(path)
    records = _read(path)
    findings = []
    keys: Dict[str, int] = {}
    for record in records:
        iid = record.get("incident_id")
        problems = validate_record(record, root)
        for problem in problems:
            findings.append({"incident_id": iid, "problem": problem})
        key = f"{record.get('component')}|{record.get('title')}"
        keys[key] = keys.get(key, 0) + 1
        if _unprevented(record):
            findings.append({"incident_id": iid, "problem": "no preventive control: recurrence is not prevented"})

    recurring = [k for k, count in keys.items() if count > 1]
    return {
        "records": len(records),
        "findings": findings,
        "recurring_without_distinct_record": recurring,
        "ok": not findings and not recurring,
    }


# Real incidents already documented in this repository. Each one is a record of
# something that actually happened; none is reconstructed from an assumption.
SEED_INCIDENTS: List[Dict[str, Any]] = [
    {
        "incident_id": "INC-cycle101-number-formats",
        "recorded_at": "2026-10-19T00:00:00+00:00",
        "title": "Excel displayed wrong values because number formats were one row out of step",
        "severity": "high",
        "what_failed": "Seven cells in B12-010 showed a correct underlying value through the wrong display: Awarded count showed 100% for 1, Award rate showed $1 for 100%, Total requested showed 3000000% for $30,000, Awarded against requested showed 1 for 50%, Deadlines due within 14 days showed 1900-01-01 for 1, Next deadline showed 46328 for a date, and Opportunities!V showed a serial instead of a date.",
        "component": "scripts/build_batch12_xlsx.py::b12_010_grant_pipeline",
        "product": "B12-010",
        "workflow": "workbook build to release",
        "version": "pre-Cycle-101 build; fixed build sha256 df49ceca",
        "evidence": [
            "reports/B12-010/NATIVE_RECALC_EXCEL_2026-10-19.json",
            "reports/CYCLE101_B12-010_VERIFICATION_2026-10-19.md",
            "reports/B12-010/WORKBOOK_QA_2026-10-19.json",
        ],
        "reproducible_conditions": "Open the pre-fix workbook in Excel and read Dashboard!B6:B13; the values are correct in openpyxl and wrong on screen.",
        "detection_mechanism": {
            "status": "EXISTED_AND_MISSED",
            "detail": "The QA gate compared cell values, never the number format against the kind of number displayed. Every value was correct, so every check passed.",
        },
        "why_not_caught": "No check read the rendered text; a value-only comparison cannot see a format defect.",
        "root_cause": {
            "verified": [
                "the format block was assigned by a stale row order, not by label",
                "Opportunities!V lost its format because its formula was written after the sheet-level format pass",
            ],
            "hypothesis": [],
        },
        "corrective_action": "Aligned every format to its label explicitly and set the V column format inside the formula loop.",
        "preventive_control": {
            "kind": "test",
            "ref": "tests/test_native_workbook_qa.py",
            "description": "17 tests reintroduce each of the seven defects into a synthetic recalculation dump and assert the validator catches it; scripts/check_b12_integrity.py fails if the workbook changes without a recorded native PASS.",
        },
        "rules_left_unchanged": [
            "the native-recalculation requirement itself was correct and was kept",
            "no threshold was lowered and no test was weakened",
        ],
        "verification": {
            "status": "PASS",
            "evidence": "reports/B12-010/WORKBOOK_QA_2026-10-19.json (Excel 16.0 build 19127, PASS, 0 critical)",
        },
        "remaining_uncertainty": "The probe covers 148 of the workbook's 427 formulas; formats on the unscanned sheets are not verified by this control.",
    },
    {
        "incident_id": "INC-cycle100-price-misstatement",
        "recorded_at": "2026-10-19T00:00:00+00:00",
        "title": "Cycle 100 record claimed the winning price had been withdrawn",
        "severity": "high",
        "what_failed": "The Cycle 100 build report was constructed from a summary stating that $15.00 and $39.00 were both withdrawn. $15.00 was the winning price and was never withdrawn; only $39.00 was.",
        "component": "reports/CYCLE100_B12-010_BUILD_2026-10-19.md",
        "product": "B12-010",
        "workflow": "release pricing record",
        "version": "Cycle 100 report",
        "evidence": [
            "reports/B12-010/GATE_FINAL_2026-10-19.json price_history",
            "reports/CYCLE101_B12-010_VERIFICATION_2026-10-19.md section 6",
        ],
        "reproducible_conditions": "Compare the report's pricing paragraph with the gate record's price_history.",
        "detection_mechanism": {
            "status": "DID_NOT_EXIST",
            "detail": "No check compared prose release claims against the structured price history.",
        },
        "why_not_caught": "The report was written from a narrative summary and never reconciled with the gate record it described.",
        "root_cause": {
            "verified": ["the source summary was wrong and was not checked against the structured record"],
            "hypothesis": [],
        },
        "corrective_action": "Restated the correct history in the Cycle 101 report and added an inline history note to the release baseline.",
        "preventive_control": {
            "kind": "test",
            "ref": "tests/test_doctrine_layers.py",
            "description": "test_release_price_history_names_each_candidate asserts each price in the gate history carries its own status and that the release baseline agrees with the winning price.",
        },
        "rules_left_unchanged": [
            "the highest-price-passing-all-gates rule was correct and was kept",
        ],
        "verification": {
            "status": "PASS",
            "evidence": "reports/CYCLE101_B12-010_VERIFICATION_2026-10-19.md; RELEASE_BASELINE price.history_note",
        },
        "remaining_uncertainty": "Other prose reports written from the same wrong summary were not exhaustively searched.",
    },
    {
        "incident_id": "INC-task-title-identity",
        "recorded_at": "2026-10-19T00:00:00+00:00",
        "title": "A generated task title named the wrong product",
        "severity": "medium",
        "what_failed": "Each of the two product-specific task files carries three copy-pasted titles naming B12-001: data/first_sale_tasks_b12-003.json and _b12-004.json both contain tasks titled 'Validate B12-001 package (sha/size/cover)', 'Confirm B12-001 price is authorized', and 'Publish B12-001 (requires founder phrase)' -- 6 mismatched titles in total. The payloads are correct for their own product: B12-003's workbook sha256 is 7cf3e46f..., B12-004's is 87ecb1cd..., and B12-004's publish result is its own url https://aekraft.gumroad.com/l/ieashv (published true, externally verified). The generic data/first_sale_tasks.json and the cycle-94 backup are real B12-001 runs whose titles are consistent; they are not part of this defect.",
        "component": "first-sale task generation",
        "product": "B12-004",
        "workflow": "publish task generation",
        "version": "Cycle 98 artifacts",
        "evidence": ["data/first_sale_tasks_b12-004.json",
                     "data/first_sale_tasks_b12-003.json"],
        "reproducible_conditions": "Open the task file and compare its title with its result payload.",
        "detection_mechanism": {
            "status": "DID_NOT_EXIST",
            "detail": "Task titles were never validated against the product they act on.",
        },
        "why_not_caught": "The title is a string literal that was not parameterised, and nothing compared it to the result.",
        "root_cause": {
            "verified": [
                "the title template hard-codes B12-001 regardless of the product",
                "the defect is systematic across product-specific files: the same three wrong titles appear in both b12-003 and b12-004 (6 mismatched titles); the B12-001 run files are consistent and confirm the template was never parameterised",
            ],
            "hypothesis": [],
        },
        "corrective_action": "operational_history derives identity from the result payload, never from a task title.",
        "preventive_control": {
            "kind": "gate",
            "ref": "doctrine_review.py",
            "description": "audit_task_titles() flags any task file whose title names a product other than the one in its result.",
        },
        "rules_left_unchanged": [
            "externally-verified publish results remain the authority for publish state",
        ],
        "verification": {
            "status": "PASS",
            "evidence": "operational_history.json records B12-004 CHECKOUT_VERIFIED from cycle98 evidence, not from the task title; doctrine_review.audit_task_titles() reports the 6 mismatched titles (3 in each product-specific file) and tests/test_doctrine_layers.py asserts the detector fires",
        },
        "remaining_uncertainty": "The generator that produced the titles has not been corrected; the defect is detected, not yet prevented at source.",
    },
    {
        "incident_id": "INC-cycle162-audit-side-effect",
        "recorded_at": "2026-10-19T00:00:00+00:00",
        "title": "A read-only audit re-evaluated and downgraded all accepted opportunities",
        "severity": "critical",
        "what_failed": "reality_audit.py's safety gate scanned only each endpoint's shallow wrapper. Two endpoints looked read-only but called a real evaluation pipeline that appended about 630 decisions and re-evaluated all four real ACCEPTED opportunities to DEFERRED/REJECTED.",
        "component": "reality_audit.py::audit_all_endpoints",
        "product": "company portfolio",
        "workflow": "enterprise audit",
        "version": "ADR-162 original and Addendum 1/2",
        "evidence": [
            "CLAUDE.md ADR-162 Addendum 2",
            "tests/test_reality_audit.py",
        ],
        "reproducible_conditions": "Run the audit without the re-entrancy guard against endpoints that call a live evaluation pipeline.",
        "detection_mechanism": {
            "status": "EXISTED_AND_MISSED",
            "detail": "The write-indicating source scan inspected only the wrapper, not one level of called functions.",
        },
        "why_not_caught": "Indirect side effects were invisible to a shallow scan, and the incident was first characterised as harmless log growth.",
        "root_cause": {
            "verified": [
                "the safety gate did not resolve called functions",
                "the first addendum understated severity because it compared row counts, not derived decision status",
            ],
            "hypothesis": [],
        },
        "corrective_action": "The gate now resolves and scans one level of called functions, fails safe on resolution failure, and has a re-entrancy guard.",
        "preventive_control": {
            "kind": "test",
            "ref": "tests/test_reality_audit.py",
            "description": "Named regression tests cover the safety gate and the re-entrancy guard; before/after derived-status diffing is the required verification method.",
        },
        "rules_left_unchanged": [
            "the audit remains read-only by mandate; the fix strengthened that mandate rather than relaxing it",
        ],
        "verification": {
            "status": "PASS",
            "evidence": "tests/test_reality_audit.py; ADR-166 re-run changed no decision's derived status",
        },
        "remaining_uncertainty": "The lost ACCEPTED status was not reverted; a founder re-evaluation is still the correct remedy.",
    },
    {
        "incident_id": "INC-registry-drift",
        "recorded_at": "2026-10-19T00:00:00+00:00",
        "title": "The batch registry still reports live products as awaiting review",
        "severity": "medium",
        "what_failed": "data/product_batch_12.json records all ten products as READY_FOR_REVIEW, including three that are published and checkout-verified. A report that reads the registry alone is wrong.",
        "component": "data/product_batch_12.json",
        "product": "batch 12",
        "workflow": "release state reporting",
        "version": "registry as of Cycle 102",
        "evidence": [
            "data/product_batch_12.json",
            "data/operational_history.json",
        ],
        "reproducible_conditions": "Compare registry state per product with its highest verified milestone.",
        "detection_mechanism": {
            "status": "DID_NOT_EXIST",
            "detail": "No gate compared registry state with evidence-derived state.",
        },
        "why_not_caught": "The registry is written by an earlier workflow and was never reconciled after publication.",
        "root_cause": {
            "verified": ["publication does not update data/product_batch_12.json"],
            "hypothesis": [],
        },
        "corrective_action": "Release state is derived from evidence by operational_history.py; the registry is explicitly documented as not authoritative for state.",
        "preventive_control": {
            "kind": "gate",
            "ref": "doctrine_review.py",
            "description": "audit_registry_drift() flags any product whose registry state is behind its highest verified milestone.",
        },
        "rules_left_unchanged": [
            "the registry remains the file-integrity input for check_b12_integrity.py, which is a different job",
        ],
        "verification": {
            "status": "PASS",
            "evidence": "reports/OPERATIONAL_LEARNING_BASELINE.md section 6 (L3)",
        },
        "remaining_uncertainty": "The registry itself was not rewritten; the drift is detected and disclosed, not eliminated.",
    },
]


def seed(path: Optional[Path] = None, root: Path = ROOT) -> Dict[str, int]:
    """Record the known real incidents, skipping any already present."""
    written = 0
    skipped = 0
    for record in SEED_INCIDENTS:
        result = record_incident(record, path=path, root=root)
        if result["written"]:
            written += 1
        else:
            skipped += 1
    return {"written": written, "skipped": skipped, "total": len(SEED_INCIDENTS)}


def render_markdown(path: Optional[Path] = None) -> str:
    records = _read(_default_path(path))
    lines = ["# Incident Memory", "", "%d record(s)." % len(records), ""]
    for record in records:
        lines.append("## %s" % record.get("title"))
        lines.append("")
        lines.append("- id: `%s`" % record.get("incident_id"))
        lines.append("- severity: %s" % record.get("severity"))
        lines.append("- component: `%s`" % record.get("component"))
        lines.append("- detection: %s" % (record.get("detection_mechanism") or {}).get("status"))
        cause = record.get("root_cause") or {}
        for item in cause.get("verified") or []:
            lines.append("- verified cause: %s" % item)
        for item in cause.get("hypothesis") or []:
            lines.append("- hypothesis: %s" % item)
        control = record.get("preventive_control") or {}
        lines.append("- preventive control (%s): `%s`" % (control.get("kind"), control.get("ref")))
        lines.append("- verification: %s" % (record.get("verification") or {}).get("status"))
        lines.append("- remaining uncertainty: %s" % record.get("remaining_uncertainty"))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[Iterable[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Permanent incident memory")
    parser.add_argument("--seed", action="store_true", help="record the known real incidents")
    parser.add_argument("--audit", action="store_true", help="validate every record")
    parser.add_argument("--search", help="substring search")
    parser.add_argument("--markdown", action="store_true", help="render the store as markdown")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.seed:
        print(json.dumps(seed(), indent=1))
    if args.audit:
        result = audit()
        print(json.dumps(result, ensure_ascii=False, indent=1))
        if not result["ok"]:
            return 1
    if args.search:
        for record in search_incidents(args.search):
            print("%s  %s" % (record.get("incident_id"), record.get("title")))
    if args.markdown:
        print(render_markdown())
    if not any((args.seed, args.audit, args.search, args.markdown)):
        print(json.dumps({"records": len(list_incidents())}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

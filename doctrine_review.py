"""Claim-versus-reality auditing and doctrine review (Doctrine sections 3G, 3E).

Two jobs, both mechanical:

1. `audit_structured_claims()` checks material operational claims that are
   already machine-readable -- release verification rows, release-manifest
   statuses, registry states, and generated task titles -- against the evidence
   they cite. It distinguishes an unlinked claim (a warning: prose can be
   evidence) from a cited path that does not exist (critical) and from a PASS
   row whose own evidence says the check was not run (critical).

2. `build_doctrine_review()` answers the doctrine-review questions from real
   records: incident controls, rework/repetition, handoff delays, weak-signal
   reviews, arm states, and the claim audit. Where no signal exists it says
   `UNKNOWN` rather than inventing a finding.

Nothing here writes to a product, a platform, or a decision. It reads records.
"""
from __future__ import annotations

import glob
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent

MILESTONES = [
    "BUILD_COMPLETE",
    "QA_PASS",
    "READY_FOR_AUTHORIZATION",
    "UPLOAD_COMPLETED",
    "PUBLIC_LISTING_VERIFIED",
    "CHECKOUT_VERIFIED",
    "FIRST_SALE_VERIFIED",
]
MILESTONE_INDEX = {name: i for i, name in enumerate(MILESTONES)}
REGISTRY_EQUIV = {
    "BUILD_COMPLETE": 0,
    "QA_PASS": 1,
    "READY_FOR_REVIEW": 2,
    "READY_FOR_AUTHORIZATION": 2,
    "UPLOAD_COMPLETED": 3,
    "PUBLIC_LISTING_VERIFIED": 4,
    "CHECKOUT_VERIFIED": 5,
    "FIRST_SALE_VERIFIED": 6,
}

PATH_RE = re.compile(
    r"(?:reports|data|tests|scripts|books|customer_site|OpenClaw_Brain|services|kids_studio|affiliate_commerce|channels|market_intelligence_core|multi_source_intelligence)"
    r"/[A-Za-z0-9_./*\-\u0600-\u06FF]+"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default=None):
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _ref_exists(ref: str, root: Path) -> bool:
    ref = ref.rstrip(".,;:)`'\"")
    candidate = root / ref
    if "*" in ref:
        return bool(list(root.glob(ref)))
    if candidate.exists():
        return True
    # paths in evidence sometimes name a directory pattern or omit a suffix
    return bool(list((root / ref).parent.glob((root / ref).name))) if (root / ref).parent.exists() else False


def _evidence_refs(text: str) -> List[str]:
    return [m.group(0).rstrip(".,;:)`'\"") for m in PATH_RE.finditer(text or "")]


def audit_registry_drift(root: Path = ROOT) -> List[Dict[str, Any]]:
    registry = _read_json(root / "data" / "product_batch_12.json", {}) or {}
    snapshot = _read_json(root / "data" / "operational_history.json", {}) or {}
    by_id = {p.get("product_id"): p for p in snapshot.get("products") or []}
    findings = []
    for product in registry.get("products") or []:
        pid = product.get("id")
        record = by_id.get(pid)
        if not record:
            continue
        registry_state = product.get("status") or product.get("state")
        verified = record.get("highest_contiguous_verified")
        if registry_state not in REGISTRY_EQUIV or verified not in MILESTONE_INDEX:
            continue
        if REGISTRY_EQUIV[registry_state] < MILESTONE_INDEX[verified]:
            findings.append({
                "severity": "WARNING",
                "code": "REGISTRY_BEHIND_EVIDENCE",
                "product_id": pid,
                "claim": "registry state %s" % registry_state,
                "reality": "evidence state %s" % verified,
                "evidence": "data/product_batch_12.json vs data/operational_history.json",
            })
    return findings


def audit_task_titles(root: Path = ROOT) -> List[Dict[str, Any]]:
    findings = []
    for path in sorted(glob.glob(str(root / "data" / "first_sale_tasks*.json"))):
        match = re.search(r"(b12-\d{3})", Path(path).name.lower().replace("_", "-"))
        file_id = match.group(1).upper() if match else None
        if not file_id:
            continue
        data = _read_json(Path(path), {}) or {}
        tasks = data.get("tasks") or {}
        if isinstance(tasks, dict):
            tasks = list(tasks.values())
        for task in tasks:
            title = (task or {}).get("title") or ""
            named = set(re.findall(r"B12-\d{3}", title))
            if named and file_id not in named:
                findings.append({
                    "severity": "WARNING",
                    "code": "TASK_TITLE_MISMATCH",
                    "file": str(Path(path).relative_to(root)).replace("\\", "/"),
                    "task_id": (task or {}).get("id"),
                    "claim": title,
                    "reality": "file and payload belong to %s" % file_id,
                    "evidence": "title text vs filename",
                })
    return findings


def audit_release_records(root: Path = ROOT) -> Dict[str, Any]:
    findings = []
    claims = 0
    snapshot = _read_json(root / "data" / "operational_history.json", {}) or {}
    by_id = {p.get("product_id"): p for p in snapshot.get("products") or []}

    for path in sorted(glob.glob(str(root / "reports" / "B12-*" / "MANIFEST_*.json"))):
        data = _read_json(Path(path), {}) or {}
        pid = data.get("product_id")
        claim = data.get("status")
        if not pid or not claim:
            continue
        claims += 1
        record = by_id.get(pid)
        if record and claim != record.get("highest_contiguous_verified"):
            findings.append({
                "severity": "CRITICAL",
                "code": "MANIFEST_STATUS_CONTRADICTS_STATE",
                "file": str(Path(path).relative_to(root)).replace("\\", "/"),
                "claim": claim,
                "reality": record.get("highest_contiguous_verified"),
                "evidence": "data/operational_history.json",
            })

    for path in sorted(glob.glob(str(root / "reports" / "B12-*" / "RELEASE_BASELINE_*.json"))):
        data = _read_json(Path(path), {}) or {}
        pid = (data.get("product_id") or Path(path).parent.name).upper()
        record = by_id.get(pid)
        release_state = data.get("release_state")
        if release_state and record:
            claims += 1
            if release_state != record.get("highest_contiguous_verified"):
                findings.append({
                    "severity": "CRITICAL",
                    "code": "BASELINE_STATE_CONTRADICTS_EVIDENCE",
                    "file": str(Path(path).relative_to(root)).replace("\\", "/"),
                    "claim": release_state,
                    "reality": record.get("highest_contiguous_verified"),
                    "evidence": "data/operational_history.json",
                })

        for row in data.get("verification") or []:
            if row.get("status") != "PASS":
                continue
            claims += 1
            text = row.get("evidence") or ""
            refs = _evidence_refs(text)
            lowered = text.lower()
            if any(marker in lowered for marker in ("not run", "not tested", "unknown")):
                findings.append({
                    "severity": "CRITICAL",
                    "code": "PASS_CONTRADICTED_BY_ITS_OWN_EVIDENCE",
                    "file": str(Path(path).relative_to(root)).replace("\\", "/"),
                    "claim": row.get("check"),
                    "reality": "evidence text disclaims the check",
                    "evidence": text,
                })
                continue
            if not refs:
                findings.append({
                    "severity": "WARNING",
                    "code": "PASS_WITHOUT_LINKED_EVIDENCE",
                    "file": str(Path(path).relative_to(root)).replace("\\", "/"),
                    "claim": row.get("check"),
                    "reality": "no file reference in the evidence text",
                    "evidence": text,
                })
                continue
            if not any(_ref_exists(ref, root) for ref in refs):
                findings.append({
                    "severity": "CRITICAL",
                    "code": "EVIDENCE_PATH_MISSING",
                    "file": str(Path(path).relative_to(root)).replace("\\", "/"),
                    "claim": row.get("check"),
                    "reality": "none of the cited paths exist",
                    "evidence": ", ".join(refs),
                })
    return {"claims_checked": claims, "findings": findings}


def audit_structured_claims(root: Path = ROOT) -> Dict[str, Any]:
    registry = audit_registry_drift(root)
    titles = audit_task_titles(root)
    release = audit_release_records(root)
    findings = registry + titles + release["findings"]
    critical = sum(1 for f in findings if f["severity"] == "CRITICAL")
    warning = sum(1 for f in findings if f["severity"] == "WARNING")
    claims = release["claims_checked"]
    return {
        "claims_checked": claims,
        "critical": critical,
        "warning": warning,
        "unsupported_rate": round(critical / claims, 4) if claims else None,
        "findings": findings,
        "basis": "release verification rows, release-manifest statuses, release baselines, batch registry, generated task titles",
        "target": "zero critical unsupported material claims",
    }


LAYERS = {
    "incident_memory": {
        "requirement": "durable incident records with root cause, detection, prevention, verification",
        "modules": ["incident_memory.py"],
        "tests": ["tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 3A",
    },
    "claim_vs_reality": {
        "requirement": "material claims traceable to evidence, with an unsupported-claim rate",
        "modules": ["operational_history.py", "product_claim_integrity.py", "doctrine_review.py"],
        "tests": ["tests/test_native_workbook_qa.py", "tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 3G",
    },
    "unknown_protocol": {
        "requirement": "explicit OBSERVED/DERIVED/INFERRED/ESTIMATED/UNKNOWN/BLOCKED labels",
        "modules": ["truth_first.py", "operational_history.py"],
        "tests": ["tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 3C",
    },
    "rework_cycle_time": {
        "requirement": "per-cycle change, repeated-check reasons, rework split, honest timing",
        "modules": ["cycle_metrics.py"],
        "tests": ["tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 4",
    },
    "handoffs": {
        "requirement": "seven-field contracts with visible delays",
        "modules": ["handoffs.py"],
        "tests": ["tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 3D",
    },
    "risk_budget": {
        "requirement": "zero-spend and protected-action gates remain enforced",
        "modules": ["safe_mode.py", "channels/publish_protection.py"],
        "tests": ["tests/test_resilience.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 3B/8",
    },
    "weak_signals": {
        "requirement": "small observations with source/date/independence; no single-signal verdicts",
        "modules": ["weak_signals.py"],
        "tests": ["tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 3F",
    },
    "doctrine_review": {
        "requirement": "periodic review of the rules themselves, from evidence",
        "modules": ["doctrine_review.py",
                    "OpenClaw_Brain/00_Governance/PERMANENT_OPERATING_DOCTRINE.md"],
        "tests": ["tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 3E",
    },
    "business_arms": {
        "requirement": "five-state arm registry that cannot claim READY without evidence",
        "modules": ["business_arms.py"],
        "tests": ["tests/test_doctrine_layers.py"],
        "doc": "PERMANENT_OPERATING_DOCTRINE.md section 5",
    },
}


def layer_matrix(root: Path = ROOT) -> Dict[str, Any]:
    layers = {}
    for key, cfg in LAYERS.items():
        modules = [m for m in cfg["modules"] if (root / m).exists()]
        missing_modules = [m for m in cfg["modules"] if not (root / m).exists()]
        tests = [t for t in cfg["tests"] if (root / t).exists()]
        if missing_modules:
            status = "MISSING"
        elif tests:
            status = "EXISTS"
        else:
            status = "PARTIAL"
        layers[key] = {
            "status": status,
            "requirement": cfg["requirement"],
            "modules_present": modules,
            "modules_missing": missing_modules,
            "tests_present": tests,
            "doc": cfg["doc"],
        }
    return {"layers": layers, "counts": {
        s: sum(1 for v in layers.values() if v["status"] == s)
        for s in ("EXISTS", "PARTIAL", "MISSING")
    }}


def _incident_section(root: Path = ROOT) -> Dict[str, Any]:
    import incident_memory
    audit = incident_memory.audit(root=root)
    records = incident_memory.list_incidents()
    return {
        "records": len(records),
        "ok": audit["ok"],
        "findings": audit["findings"],
        "with_preventive_control": sum(
            1 for r in records
            if (r.get("preventive_control") or {}).get("ref") not in (None, "", "none")
        ),
        "with_verified_control": sum(
            1 for r in records
            if (r.get("preventive_control") or {}).get("ref") not in (None, "", "none")
            and (r.get("verification") or {}).get("status") == "PASS"
        ),
        "detection_existed_and_missed": sum(
            1 for r in records
            if (r.get("detection_mechanism") or {}).get("status") == "EXISTED_AND_MISSED"
        ),
        "rules_kept": sum(1 for r in records if r.get("rules_left_unchanged")),
    }


def build_doctrine_review(root: Path = ROOT) -> Dict[str, Any]:
    import business_arms
    import cycle_metrics
    import handoffs
    import weak_signals

    claims = audit_structured_claims(root)
    incidents = _incident_section(root)
    cycles = cycle_metrics.summary()
    repetition = cycle_metrics.repetition_audit()
    open_handoffs = handoffs.open_handoffs()
    blocked = [h for h in open_handoffs if h.get("status") == "BLOCKED"]
    signals = weak_signals.review_triggers()
    arms = business_arms.arm_status()
    layers = layer_matrix(root)

    questions = [
        {
            "question": "Which rules demonstrably improved quality, cycle time, reliability, or commercial outcomes?",
            "status": "OBSERVED" if incidents["with_verified_control"] else "UNKNOWN",
            "answer": "%d incident(s) carry a real preventive control whose verification passed; those controls are the rules with evidence of effect." % incidents["with_verified_control"],
            "basis": "incident_memory audit",
        },
        {
            "question": "Which rules are redundant or unnecessarily expensive?",
            "status": "UNKNOWN",
            "answer": "No doctrine-cost telemetry exists. Rework that is attributable to a specific rule is not recorded, so no rule can be called redundant from evidence.",
            "basis": "cycle_metrics records rework, not rule-level cost",
        },
        {
            "question": "Which rules repeatedly fail in practice?",
            "status": "OBSERVED" if incidents["detection_existed_and_missed"] else "UNKNOWN",
            "answer": "%d incident(s) had a check that existed and still missed the failure; those checks are the ones to strengthen, not the policies they enforce." % incidents["detection_existed_and_missed"],
            "basis": "incident_memory detection_mechanism.status",
        },
        {
            "question": "Which failures indicate poor implementation rather than a defective rule?",
            "status": "DERIVED" if incidents["records"] else "UNKNOWN",
            "answer": "%d incident(s) explicitly kept their rule unchanged and fixed the implementation instead." % incidents["rules_kept"],
            "basis": "incident_memory rules_left_unchanged",
        },
        {
            "question": "Which new risks or business requirements require a change?",
            "status": "OBSERVED" if signals["triggered"] else "NOT_ENOUGH_EVIDENCE",
            "answer": ("Triggered topics: " + ", ".join(signals["triggered"])) if signals["triggered"]
                      else "No topic has the required number of independent signals yet; this is not evidence that no risk exists.",
            "basis": "weak_signals.review_triggers",
        },
        {
            "question": "Which safeguards must remain regardless of frequency of use?",
            "status": "OBSERVED",
            "answer": "The four founder-protected gates remain: evolution execute, capital reallocation, business retirement, and first/elevated-risk publishing. Rare use is never a reason to remove a safeguard.",
            "basis": "safe_mode.py, channels/publish_protection.py, evidence_engine REJECT_IF_FAIL",
        },
    ]

    return {
        "generated_at": _now_iso(),
        "layers": layers,
        "claims": claims,
        "incidents": incidents,
        "cycles": cycles,
        "repetition": repetition,
        "handoffs": {
            "open": len(open_handoffs),
            "blocked": len(blocked),
            "blocked_reasons": [
                {"handoff_id": h["handoff_id"], "reason": h.get("delay_reason")} for h in blocked
            ],
        },
        "weak_signals": signals,
        "arms": arms,
        "questions": questions,
        "status": {
            "claim_audit": "PASS" if claims["critical"] == 0 else "HOLD",
            "incident_memory": "PASS" if incidents["ok"] else "HOLD",
            "repetition": "PASS" if repetition["ok"] else "REVIEW",
            "layers": "PASS" if layers["counts"]["MISSING"] == 0 else "HOLD",
        },
    }


def render_markdown(review: Dict[str, Any]) -> str:
    lines = ["# Doctrine Review", "", "Generated: %s" % review["generated_at"], ""]
    lines.append("## Layer matrix")
    lines.append("")
    lines.append("| Layer | Status | Requirement | Proof |")
    lines.append("|---|---|---|---|")
    for key, layer in review["layers"]["layers"].items():
        proof = ", ".join(layer["tests_present"]) or "none"
        lines.append("| %s | %s | %s | %s |" % (key, layer["status"], layer["requirement"], proof))
    lines.append("")
    claims = review["claims"]
    lines.append("## Claims")
    lines.append("")
    lines.append("- material claims checked: %s" % claims["claims_checked"])
    lines.append("- critical unsupported: %s" % claims["critical"])
    lines.append("- warnings: %s" % claims["warning"])
    lines.append("- unsupported rate: %s" % claims["unsupported_rate"])
    lines.append("")
    lines.append("## Incidents, rework, handoffs")
    lines.append("")
    lines.append("- incidents: %s (controls: %s, verified: %s)"
                 % (review["incidents"]["records"],
                    review["incidents"]["with_preventive_control"],
                    review["incidents"]["with_verified_control"]))
    defects = review["cycles"]["defects_total"]
    defects_text = ", ".join("%s %s" % (k, v) for k, v in defects.items() if v) or "none"
    lines.append("- cycles: %s; defects: %s" % (review["cycles"]["cycles"], defects_text))
    lines.append("- rework: %(new_defects)s new / %(preexisting)s pre-existing" % review["cycles"]["rework"])
    lines.append("- repetition findings: %s" % len(review["repetition"]["findings"]))
    lines.append("- open handoffs: %(open)s (%(blocked)s blocked)" % review["handoffs"])
    lines.append("")
    lines.append("## Arms")
    lines.append("")
    for key, arm in review["arms"]["arms"].items():
        lines.append("- **%s** — %s%s" % (arm["name"], arm["status"],
                                          (": " + arm["blocker"]) if arm.get("blocker") else ""))
    lines.append("")
    lines.append("## Doctrine questions")
    lines.append("")
    for item in review["questions"]:
        lines.append("**%s**" % item["question"])
        lines.append("")
        lines.append("- %s — %s" % (item["status"], item["answer"]))
        lines.append("")
    lines.append("## Status")
    lines.append("")
    for key, value in review["status"].items():
        lines.append("- %s: %s" % (key, value))
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Claim audit and doctrine review")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--claims", action="store_true")
    args = parser.parse_args(argv)

    if args.claims:
        result = audit_structured_claims()
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 1 if result["critical"] else 0

    review = build_doctrine_review()
    if args.write:
        reports = ROOT / "reports"
        reports.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        json_path = reports / ("DOCTRINE_REVIEW_%s.json" % stamp)
        md_path = reports / ("DOCTRINE_REVIEW_%s.md" % stamp)
        json_path.write_text(json.dumps(review, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        md_path.write_text(render_markdown(review), encoding="utf-8", newline="\n")
        print("wrote", json_path.relative_to(ROOT), md_path.relative_to(ROOT))
    if args.json or not args.write:
        print(json.dumps(review, ensure_ascii=False, indent=1))

    hold = any(v in ("HOLD",) for v in review["status"].values())
    return 1 if hold else 0


if __name__ == "__main__":
    raise SystemExit(main())

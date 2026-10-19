#!/usr/bin/env python
"""Single doctrine gate.

Runs every doctrine-layer check that has a real signal and fails the build when
one of them is HOLD. It is read-only: it never publishes, spends, mutates a
product record, or writes a ledger.

Exit codes:
    0  every layer is within its rule
    1  at least one layer is not
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import business_arms  # noqa: E402
import cycle_metrics  # noqa: E402
import doctrine_review  # noqa: E402
import handoffs  # noqa: E402
import incident_memory  # noqa: E402
import weak_signals  # noqa: E402


def _pytest(path: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    tail = (result.stdout or "").strip().splitlines()
    return {
        "name": path,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "summary": tail[-1] if tail else "",
    }


def run() -> dict:
    claims = doctrine_review.audit_structured_claims()
    incidents = incident_memory.audit()
    cycles = cycle_metrics.repetition_audit()
    hands = handoffs.latest_by_id()
    invalid_handoffs = [h for h in hands.values() if handoffs.validate_handoff(h)]
    signals = weak_signals.review_triggers()
    arms = business_arms.arm_status()
    matrix = doctrine_review.layer_matrix()

    checks = [
        {
            "name": "claim_vs_reality",
            "ok": claims["critical"] == 0,
            "detail": "%s material claims, %s critical, %s warning"
                      % (claims["claims_checked"], claims["critical"], claims["warning"]),
        },
        {
            "name": "incident_memory",
            "ok": incidents["ok"],
            "detail": "%s records, %s findings" % (incidents["records"], len(incidents["findings"])),
        },
        {
            "name": "handoff_contracts",
            "ok": not invalid_handoffs,
            "detail": "%s handoffs, %s invalid" % (len(hands), len(invalid_handoffs)),
        },
        {
            "name": "cycle_rework",
            "ok": cycles["ok"],
            "detail": "%s cycles, %s repetition findings"
                      % (cycles["cycles"], len(cycles["findings"])),
        },
        {
            "name": "weak_signals",
            "ok": True,
            "detail": "%s topics, %s triggered review"
                      % (len(signals["topics"]), len(signals["triggered"])),
        },
        {
            "name": "business_arms",
            "ok": not business_arms.validate_arm_states(arms),
            "detail": "%s arms, %s revenue-verified, %s ready"
                      % (len(arms["arms"]), arms["counts"]["REVENUE_VERIFIED"],
                         arms["counts"]["READY"]),
        },
        {
            "name": "doctrine_layers",
            "ok": matrix["counts"]["MISSING"] == 0 and matrix["counts"]["PARTIAL"] == 0,
            "detail": "%s exists, %s partial, %s missing"
                      % (matrix["counts"]["EXISTS"], matrix["counts"]["PARTIAL"],
                         matrix["counts"]["MISSING"]),
        },
        _pytest("tests/test_doctrine_layers.py"),
    ]
    checks[-1]["name"] = "doctrine_tests"

    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def main() -> int:
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=1))
    for check in result["checks"]:
        if not check["ok"]:
            print("HOLD: %s -- %s" % (check["name"], check.get("detail") or check.get("summary")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

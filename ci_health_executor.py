"""Goal 2 -- EXECUTE and VERIFY, the bounded technical CI action layer.

SCOPE, deliberately narrow
    EXECUTE acts ONLY on CI state. It reads evidence, decides a verdict, and
    when the verdict is HOLD or BLOCKED it persists one evidence-bearing action
    record to data/ci_health_state.jsonl. It never publishes, never charges,
    never contacts anyone, never spends, and never reaches a commercial system.
    It is not, and must not grow into, an autonomous commercial engine.

WHY THE ACTION SET IS THIS SMALL
    The CI incident that motivated Goal 2 was never a missing capability; it was
    absence of evidence being read as health. So the only useful first action is
    to make the evidence durable and unambiguous. Anything more would be
    scope creep against a system that has no verified blocker to act on.

THE FOUR-STATE MODEL IS PRESERVED EXACTLY
    PASS    -> NO action. Emitting an action on a green run is itself a defect:
              it manufactures work and pollutes the ledger.
    HOLD    -> record "await_completion", then VERIFY by re-reading the run.
    BLOCKED -> record the confirmed failure(s) as the technical action.
    UNKNOWN -> NO action, ever. Acting on insufficient evidence is how a system
              does something irreversible it cannot justify. UNKNOWN is
              recorded as an observation only, with no action.

IDEMPOTENCY
    The action key is (commit_sha, run ids, verdict). Re-polling an unchanged
    state produces no new row. Verified by re-reading the ledger, not by
    trusting the write call's return value -- VERIFY never believes EXECUTE.

SECURITY
    No token is read, required, stored or logged. There is no code path that
    could emit a credential, and a test asserts both facts.
"""
from __future__ import annotations

import json
import os
import time

from ci_health_detector import (  # noqa: F401
    BLOCKED, HOLD, PASS, UNKNOWN, VERDICTS, collect, decide, detect,
)

DEFAULT_LEDGER = os.path.join("data", "ci_health_state.jsonl")

# The complete, closed set of technical actions. Nothing outside this mapping
# can ever be produced, which is what keeps EXECUTE bounded.
ACTION_AWAIT = "await_completion"
ACTION_REPORT = "report_confirmed_failure"
ACTION_NONE = "none"


def decide_action(verdict, evidence):
    """Map a verdict to its bounded technical action.

    PASS and UNKNOWN deliberately map to no action at all.
    """
    if verdict == BLOCKED:
        detail = evidence.get("detail") or {}
        names = (detail.get("failed_jobs") or detail.get("not_successful")
                 or detail.get("runs_not_ok") or [])
        return ACTION_REPORT, names
    if verdict == HOLD:
        return ACTION_AWAIT, []
    return ACTION_NONE, []


def _action_key(verdict, evidence):
    ev = evidence.get("evidence", evidence) if isinstance(evidence, dict) else {}
    runs = ev.get("runs") if isinstance(ev, dict) else []
    run_ids = "|".join(sorted(str(r.get("id")) for r in (runs or [])
                              if isinstance(r, dict)))
    sha = (ev.get("commit_sha") if isinstance(ev, dict) else None) or "unknown"
    return [sha, run_ids, verdict]


def _read_ledger(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:                          # noqa: BLE001
                continue
    return rows


def execute(verdict, reason, evidence, ledger_path=DEFAULT_LEDGER):
    """Persist one action record, or deliberately do nothing.

    Returns a dict describing what happened. Callers must not treat this return
    value as proof -- VERIFY exists precisely because a successful write is not
    evidence of a correct outcome.
    """
    if verdict not in VERDICTS:
        raise ValueError("refusing to execute an unknown verdict: %r" % verdict)

    action, targets = decide_action(verdict, evidence)
    key = _action_key(verdict, evidence)

    if action == ACTION_NONE:
        # PASS and UNKNOWN are recorded as observations with no action. Writing
        # an "action" for either would be inventing work.
        return {"acted": False, "action": ACTION_NONE, "verdict": verdict,
                "reason": reason, "targets": [],
                "why": ("PASS needs no action; UNKNOWN must never trigger one "
                        "because acting on insufficient evidence is exactly the "
                        "failure this whole system exists to prevent")}

    for row in _read_ledger(ledger_path):
        if [str(x) for x in row.get("action_key", [])] == [str(x) for x in key]:
            return {"acted": False, "action": action, "verdict": verdict,
                    "reason": reason, "targets": targets,
                    "why": "identical action already recorded (idempotent)"}

    ev = evidence.get("evidence", evidence) if isinstance(evidence, dict) else {}
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit_sha": (ev.get("commit_sha") if isinstance(ev, dict) else None),
        "run_ids": [r.get("id") for r in (ev.get("runs") or []) if isinstance(r, dict)],
        "check_ids": [j.get("run_id") for j in (ev.get("jobs") or [])
                      if isinstance(j, dict)],
        "state": verdict,
        "decision_reason": reason,
        "action": action,
        "action_targets": targets,
        "action_key": key,
    }
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"acted": True, "action": action, "verdict": verdict, "reason": reason,
            "targets": targets, "record": record}


def verify(key, ledger_path=DEFAULT_LEDGER, expected_count=1):
    """VERIFY by re-reading the ledger from disk.

    Deliberately does not accept, or consult, the return value of execute().
    The only acceptable proof that an action was recorded correctly is that the
    persisted state independently says so, exactly the requested number of times.
    """
    matches = []
    for row in _read_ledger(ledger_path):
        if [str(x) for x in row.get("action_key", [])] == [str(x) for x in key]:
            matches.append(row)
    return {"verified": len(matches) == expected_count,
            "count": len(matches), "expected": expected_count,
            "records": matches}


def run_once(sha, ledger_path=DEFAULT_LEDGER, repo=None, api=None):
    """Full DETECT -> DECIDE -> EXECUTE -> VERIFY for one commit."""
    if repo or api:
        verdict, reason, evidence = detect(sha, **({"repo": repo} if repo else {}),
                                          **({"api": api} if api else {}))
    else:
        verdict, reason, evidence = detect(sha)
    outcome = execute(verdict, reason, evidence, ledger_path)
    proof = verify(outcome.get("record", {}).get("action_key")
                   or _action_key(verdict, evidence), ledger_path)
    return {"verdict": verdict, "reason": reason, "execute": outcome,
            "verify": proof}


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    print(json.dumps(run_once(target), indent=2, default=str))
"""OpenClaw Factory — Safe Startup Detection (Unified Recovery System §2).

check_startup_safety() is the single real decision point: was the
previous instance's shutdown unclean, and if so, is it safe to resume
automatically or does it need the founder's explicit confirmation?

Reuses, never re-derives:
  - the stale-lock evidence factory_loop.js's acquireLock() already
    computes (passed in as `was_stale_lock`, never recomputed here)
  - orchestrator/timeline.py's has_succeeded() for the one real case
    where "did the external side effect already happen" can be checked
    (an orchestrator-routed production/publishing stage)
  - factory_state.py's existing load_state()/save_state() (no new file,
    no new schema)

CLI mirrors mission_control_api.py's own stdin/stdout-JSON convention so
scripts/factory_startup_check.js (factory_loop.js's caller) and server.js
can both shell out to the same one real implementation:

    echo '{"was_stale_lock": true}' | python -m recovery.startup_check
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import factory_state
from orchestrator import timeline as orch_timeline
from orchestrator.types import DUPLICATE_SENSITIVE_STAGES

# factory_loop.js's own tick steps (Phase A's markStep()) all share
# current_task.name == "golden_hunter_tick" — the risky ones (a real
# book_generator.py/distribute call can fire) are these two specific
# steps. Unlike an orchestrator-routed stage, there is no idempotency_key
# to check has_succeeded() against here, so this factory conservatively
# always requires confirmation rather than guessing "probably fine."
_RISKY_GOLDEN_HUNTER_TICK_STEPS = {"hunt", "golden_hunter_bridge"}


def check_startup_safety(was_stale_lock, state_path=None, timeline_path=None):
    """Returns {"classification": "HEALTHY"|"RECOVERING"|"NEEDS_CONFIRMATION",
    "reason": str, "current_task": dict|None}. Never raises — a startup
    check that itself crashes would be worse than the problem it exists
    to catch, so any unexpected shape degrades to NEEDS_CONFIRMATION
    (fail closed, same discipline as the rest of this factory's recovery
    tooling)."""
    if not was_stale_lock:
        return {"classification": "HEALTHY", "reason": "clean start", "current_task": None}

    try:
        state = factory_state.load_state(state_path)
        current_task = state.get("current_task")
    except Exception as e:
        return {"classification": "NEEDS_CONFIRMATION", "reason": f"could not read factory_state.json: {e}", "current_task": None}

    if current_task is None:
        classification, reason = "RECOVERING", "previous instance died uncleanly, but nothing was in flight"
    else:
        name = current_task.get("name")
        step = current_task.get("step")
        idem_key = current_task.get("idempotency_key")

        if name in DUPLICATE_SENSITIVE_STAGES:
            if idem_key and orch_timeline.has_succeeded(idem_key, path=timeline_path):
                classification, reason = "RECOVERING", f"previous instance died mid-{name}, but it had already succeeded before dying"
            else:
                classification, reason = "NEEDS_CONFIRMATION", (
                    f"previous instance died mid-{name} with no confirmed success record — "
                    f"the real external side effect may or may not have completed"
                )
        elif name == "golden_hunter_tick" and step in _RISKY_GOLDEN_HUNTER_TICK_STEPS:
            classification, reason = "NEEDS_CONFIRMATION", (
                f"previous instance died mid-{step} — this step can spawn a real "
                f"generation/distribution call with no idempotency key to verify against"
            )
        else:
            classification, reason = "RECOVERING", f"previous instance died mid-{name or 'unknown'} ({step or 'no step'}), safe to auto-resume"

    _record_recovery_info(classification, reason, current_task, state_path)
    return {"classification": classification, "reason": reason, "current_task": current_task}


def _record_recovery_info(classification, reason, current_task, path):
    try:
        state = factory_state.load_state(path)
        state["recovery_info"] = {
            "interrupted": classification != "HEALTHY",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "evidence": f"stale lock reclaimed; current_task={current_task!r}",
            "reason": reason,
        }
        factory_state.save_state(state, path)
    except Exception as e:
        print(f"[recovery.startup_check] failed to record recovery_info: {e}")


def resolve_recovery(path=None):
    """Marks a previously-interrupted state as resolved — called once the
    formerly in-flight task actually finishes (auto-resumed and
    succeeded, or the founder confirmed confirm-safe-to-resume and it
    then completed). This is what flips recovery_info.interrupted back
    to False and is the trigger for the recovery_completed Telegram
    event."""
    try:
        state = factory_state.load_state(path)
        state["recovery_info"] = {"interrupted": False, "detected_at": None, "evidence": None, "reason": None}
        factory_state.save_state(state, path)
        return True
    except Exception as e:
        print(f"[recovery.startup_check] failed to resolve recovery_info: {e}")
        return False


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    try:
        raw = sys.stdin.read().strip()
        job = json.loads(raw) if raw else {}
        result = check_startup_safety(bool(job.get("was_stale_lock")))
        print(json.dumps({"success": True, **result}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

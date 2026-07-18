"""OpenClaw Factory — Factory State Manager, Python side (Operational
Resilience Architecture, Phase A, 2026-07-18).

The single authoritative "what's happening right now" view: data/
factory_state.json. Same atomic tmp-file-then-rename write server.js's
saveFin()/channels/ledger.py's reconcile_ledger_to_finance() already use,
so a crash mid-write never corrupts it — worst case, the rename never
happened and the previous valid state is still on disk. A corrupt/missing
file is never treated as fatal: every read falls back to a safe default,
matching this factory's existing quarantine-then-recover discipline
(server.js's loadFin()).

Phase A scope only: this module is read/write plumbing. Nothing yet acts
on recovery_info/pending_retries (that's Phase B/C of the Operational
Resilience Architecture) — wiring this in changes no existing behavior,
it only adds a new, accurate, disk-persisted view alongside it.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "factory_state.json"


def _default_state():
    return {
        "current_task": None,
        "active_workflow": None,
        "queue": None,
        "last_successful_checkpoint": None,
        "recovery_info": {"interrupted": False, "detected_at": None, "evidence": None, "reason": None},
        "pending_retries": [],
        "updated_at": None,
    }


def load_state(path=None):
    """Never raises. A missing or corrupt file reads as the safe default —
    the caller must be able to trust this always returns a well-shaped
    dict."""
    p = Path(path) if path else DEFAULT_STATE_PATH
    if not p.exists():
        return _default_state()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_state()
    if not isinstance(data, dict):
        return _default_state()

    state = _default_state()
    state.update({k: data.get(k, state[k]) for k in state})
    return state


def save_state(state, path=None):
    """Atomic write — a crash mid-write leaves the previous valid file
    intact, never a half-written one."""
    p = Path(path) if path else DEFAULT_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp_path = p.parent / f"{p.name}.tmp-{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, p)
    return state


# Every mutator below must never raise back into its caller — this is new
# instrumentation layered onto already-working code (orchestrator stages,
# factory_loop.js's tick via subprocess calls into this module where
# applicable); a disk error writing factory_state.json must never break
# the real work it's merely observing. Same discipline as this factory's
# other best-effort loggers (logFinanceError, appendLoopLog).


def set_current_task(name, step=None, idempotency_key=None, path=None):
    """Marks a long-running task as in-flight. Called at the START of any
    stage — if the process dies before clear_current_task() runs, this is
    exactly the "in-flight, not yet resolved" evidence startup recovery
    needs (Operational Resilience Architecture §5) that the append-only
    timeline alone can't give (timeline only records finished attempts)."""
    try:
        state = load_state(path)
        state["current_task"] = {
            "name": name, "step": step, "idempotency_key": idempotency_key,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        state["active_workflow"] = name
        return save_state(state, path)
    except OSError as e:
        print(f"[factory_state] set_current_task failed: {e}")
        return None


def clear_current_task(path=None):
    """Marks the current task resolved — success or failure, either way
    it's no longer "in flight." Called at the end of a stage, regardless
    of outcome."""
    try:
        state = load_state(path)
        state["current_task"] = None
        return save_state(state, path)
    except OSError as e:
        print(f"[factory_state] clear_current_task failed: {e}")
        return None


def record_checkpoint(stage, idempotency_key, path=None):
    """Records the last real success — a summary pointer into
    orchestrator/timeline.py's own real checkpoint records, never a
    second, competing checkpoint store."""
    try:
        state = load_state(path)
        state["last_successful_checkpoint"] = {
            "stage": stage, "idempotency_key": idempotency_key,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        return save_state(state, path)
    except OSError as e:
        print(f"[factory_state] record_checkpoint failed: {e}")
        return None


def enqueue_retry(task, error, path=None):
    """Appends a pending retry — the Offline Mode queue (§6): a real
    network failure (Groq/arm publish/n8n notify) is remembered here
    instead of just being lost, so a later reconnect can replay it."""
    try:
        state = load_state(path)
        state["pending_retries"].append({
            "task": task, "last_error": str(error),
            "queued_at": datetime.now(timezone.utc).isoformat(),
        })
        return save_state(state, path)
    except OSError as e:
        print(f"[factory_state] enqueue_retry failed: {e}")
        return None


def due_retries(path=None):
    """Every currently-queued retry — Phase A has no backoff scheduling
    yet (every queued retry is "due"); a later phase may add next_retry_at
    filtering without changing this function's contract."""
    return load_state(path)["pending_retries"]


def clear_retry(task, path=None):
    """Removes every queued retry for `task` (by name) — called once a
    replay succeeds."""
    try:
        state = load_state(path)
        state["pending_retries"] = [r for r in state["pending_retries"] if r.get("task") != task]
        return save_state(state, path)
    except OSError as e:
        print(f"[factory_state] clear_retry failed: {e}")
        return None

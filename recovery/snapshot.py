"""OpenClaw Factory — Backup snapshot helper (Unified Recovery System §7,
2026-07-18).

Generalizes the existing quarantine-then-recover pattern (server.js's
loadFin(): fs.copyFileSync(FINANCE_FILE, f"{FINANCE_FILE}.corrupt-{ts}.bak")
on a corrupt read) into a small, reusable "snapshot before a real,
critical operation" helper — not a blanket full-repo snapshot (git
already does that, and better; see DISASTER_RECOVERY_PLAN.md).

Snapshots a fixed, small set of critical state files
(data/factory_state.json, data/production_control.json,
data/decisions.jsonl) immediately before an operation this factory
already treats as duplicate-sensitive (a real Paddle publish, an
orchestrator production/publishing stage) — so a corrupted write mid-
operation always has a clean, recent copy to restore from
(scripts/restore_file_from_git.js covers the git-tracked history; this
covers the moment just before a specific real risk).
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SNAPSHOT_TARGETS = (
    _FACTORY_ROOT / "data" / "factory_state.json",
    _FACTORY_ROOT / "data" / "production_control.json",
    _FACTORY_ROOT / "data" / "decisions.jsonl",
    # Full Factory Integrity Audit (2026-07-22): these 4 files didn't exist
    # when this list was last written and carry the same duplicate-write/
    # corruption risk this snapshot system exists to protect against.
    _FACTORY_ROOT / "data" / "market_evidence.jsonl",
    _FACTORY_ROOT / "data" / "board_meetings.jsonl",
    _FACTORY_ROOT / "data" / "paddle_products.json",
    _FACTORY_ROOT / "data" / "paddle_checkout_notifications.json",
)


def snapshot_before(reason, paths=None):
    """Best-effort: copies each existing target file to
    "{path}.snapshot-{timestamp}.bak". A missing target is skipped, not
    an error (e.g. production_control.json may not exist yet on a fresh
    factory). Never raises — a snapshot failure must never block the
    real operation it's protecting.

    Returns a list of {"path": str, "snapshot": str|None, "error": str|None}."""
    targets = paths if paths is not None else DEFAULT_SNAPSHOT_TARGETS
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    results = []
    for p in targets:
        p = Path(p)
        if not p.exists():
            results.append({"path": str(p), "snapshot": None, "error": None})
            continue
        snapshot_path = p.parent / f"{p.name}.snapshot-{ts}.bak"
        try:
            shutil.copyfile(p, snapshot_path)
            results.append({"path": str(p), "snapshot": str(snapshot_path), "error": None})
        except OSError as e:
            print(f"[recovery.snapshot] snapshot_before failed for {p}: {e}")
            results.append({"path": str(p), "snapshot": None, "error": str(e)})
    _ = reason  # kept for the caller's own audit trail / future logging, not used internally yet
    return results

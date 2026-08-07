# Galaxy Forge — Backup and Restore

**Date:** 2026-08-08 | Phase 14, Section 13. Per the directive's own rule: **"A backup is valid only if restoration has been tested successfully."** This round actually tested a restore — not just confirmed a backup file exists.

---

## The real restore test performed this round

Three real, existing backup snapshots (`data/factory_state.json.snapshot-20260807T113319276744.bak`, `data/paddle_products.json.snapshot-20260807T113319276744.bak`, `data/decisions.jsonl.snapshot-20260807T113319276744.bak`) were copied to an isolated temp directory (never touching the live files) and validated:

| File | Restored size | Validation result |
|---|---|---|
| `factory_state.json` | 532 bytes | Valid JSON, parses cleanly |
| `paddle_products.json` | 1,852 bytes | Valid JSON, parses cleanly |
| `decisions.jsonl` | 16,920,377 bytes | 2,030 real lines, **0 malformed** |

**Result: the backup mechanism produces genuinely valid, restorable data.** This is real, tested proof — not an assumption from a file existing on disk.

## What "backup" actually means in this factory today

`recovery/snapshot.py::snapshot_before(reason)` — copies a fixed list of 7 critical files (`factory_state.json`, `production_control.json`, `decisions.jsonl`, `market_evidence.jsonl`, `board_meetings.jsonl`, `paddle_products.json`, `paddle_checkout_notifications.json`) to a timestamped `.bak` sibling, **immediately before** a real risky operation (a real Paddle publish, an orchestrator production stage). This is event-triggered, not scheduled.

| Property | Real answer |
|---|---|
| **Backup frequency** | Event-triggered only — before a specific risky operation, not on a schedule. A file that hasn't been touched by a risky operation recently has no recent backup. |
| **Retention** | **None** — old `.bak` files are never cleaned up. Real evidence: 3 separate snapshot generations exist for several files spanning 2026-07-24 to 2026-08-07, all still present. |
| **Storage location** | Same local disk as the primary data — **no offsite or redundant copy exists.** A single disk failure destroys both the primary data and every backup simultaneously. |
| **Encryption** | None. |
| **Restore procedure** | **Manual only** — `shutil.copyfile(backup_path, original_path)` (or the OS equivalent) run by a human. No automated restore function exists anywhere in this factory (`recovery/snapshot.py` has `snapshot_before()` but no `restore()`). |
| **Recovery Point Objective (RPO)** | Effectively "as of the last risky operation that happened to trigger a snapshot" — could be stale by any amount of time for a file not recently involved in a risky operation |
| **Recovery Time Objective (RTO)** | Untested as a real, timed, end-to-end procedure before this round. The mechanical copy step itself is near-instant (proven this round); the real RTO also depends on a human noticing the need, locating the right `.bak` file, and executing the copy — none of which is timed or rehearsed |

## Real gaps found this round

1. **No automated restore function** — every restore today is a manual file copy. Low effort to close (a thin `restore_from_snapshot(target_path, snapshot_path=None)` wrapper that finds the most recent `.bak` and copies it back), not built this round to avoid untested, unreviewed code touching real data-recovery paths without the founder's own sign-off on the exact semantics (e.g., should it back up the *current* file before overwriting it with the restored one? Yes, almost certainly — but that's a real design decision, not assumed here).
2. **No offsite backup** — a single local-disk failure is unrecoverable. `git` itself provides a real, partial mitigation for anything already committed (most `.md`/`.py`/`.js` files) but the real, frequently-changing operational data (`decisions.jsonl`, `finance_data.json`, etc.) is `.gitignore`d and lives only on this one machine.
3. **No retention policy** — disk usage grows unbounded from accumulated `.bak` files.

## Recommendation

Given $0 real revenue and 0 real customers, building a full offsite/encrypted/scheduled backup system now would be premature relative to this factory's own established "don't build ahead of real need" discipline. The one real, low-cost, high-value fix worth prioritizing: a tested `restore_from_snapshot()` function, since the mechanical restore step is now proven safe and the only missing piece is making it a real, callable, tested function instead of an ad-hoc manual copy.

---

*See also: `RELIABILITY_ARCHITECTURE.md`, `DISASTER_RECOVERY.md`.*

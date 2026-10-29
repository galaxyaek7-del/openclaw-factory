# Continuous operations plan (2026-10-29)

Goal: the factory keeps working without a person restarting it, and when it cannot,
someone is told the same hour. Every line below is OBSERVED on 2026-10-29 unless marked.

## 1. What stopped or nearly stopped the factory

| # | Failure | How long, unnoticed | Root cause | Status |
|---|---|---|---|---|
| F1 | n8n not running | 2026-10-25 07:00 -> 2026-10-29 07:44 (zero executions of the sales poll and sensing workflows) | n8n window closed (task result 0xC000013A); `healN8n` only logged "warning" every tick; no restart path | **Fixed:** restarted; `factory_loop.js` n8n watchdog restarts it via its logon task after 3 down ticks, max once/hour (`tests/test_n8n_watchdog.js`) |
| F2 | Disk C: 3.4 GB free of 255 GB (1.3%) | daily `critical` health check, never alerted | `C:\Users\Dell\.local\share\opencode\opencode.db` = 126.7 GB, +10.5 MB/min measured while active (est. ~5 h to full at that rate) | **Alert fixed:** critical checks now reach `NEEDS_ATTENTION.md` + desktop notice. **Space: founder decision (below)** |
| F3 | No alert channel | every alert since at least 2026-10-28 `not_delivered` | `TELEGRAM_BOT_TOKEN` / `OPENCLAW_TELEGRAM_CHAT_ID` not configured (B12) | Founder: set both in `.env` |
| F4 | No restart after reboot/log-off | server + loop started by hand 2026-10-17 | no logon task for the supervisors; `start_factory.bat` started unsupervised duplicates | **Ready:** `scripts/start_factory_supervised.ps1` (duplicate-guarded, tested); `start_factory.bat` now delegates to it. Founder runs once: `powershell -File scripts\install_factory_autostart.ps1` (registering a logon task was refused to the agent) |
| F5 | Site auto-publish stalled | since 3 non-site commits were made today | `auto_publish_site.py` pushes only site-only ranges; `git push` was refused to the agent | Founder: `git push origin main` |
| F6 | Tests wrote live ledgers | months (493 test rows found) | default paths in tests; a JS test restored the real `CLAUDE.md` | **Fixed:** write guard (Python), restore test isolated, rows quarantined with backups |

## 2. Decision needed now: opencode.db (F2)

Owner rule: no cleaning of `opencode.db` without a backup and the owner's approval. A full
backup needs ~127 GB that C: does not have. Options, safest first:

1. **Move it** to another drive with >130 GB free (external disk), then point OpenCode at it
   (or symlink). Nothing is deleted. Needs OpenCode closed during the copy.
2. **Use OpenCode's own session cleanup** to delete old sessions inside the tool (its data,
   its supported path), then let SQLite reclaim space (VACUUM needs temporary free space).
3. **Stop the growth first:** close OpenCode sessions that are idle; growth was measured only
   while it was active.

Until then the factory itself keeps running; the disk check is critical and visible.

## 3. Operating model (what runs, what watches it)

| Layer | Runs | Watched by | Restart |
|---|---|---|---|
| server.js | supervisor (`logs/server_supervised.log`) | factory_loop `diagnose()` each tick | supervisor on crash; logon task (F4) after reboot |
| factory_loop.js | supervisor (`SUPERVISOR_TARGET=factory_loop.js`) | supervisor | same |
| n8n | logon task `GalaxyForge-N8N-Autostart` | loop watchdog (port 5678) + `scripts/n8n_workflow_health.py` (did workflows actually run) | watchdog -> same logon task |
| Alerts | `NEEDS_ATTENTION.md`, desktop notice; Telegram when configured | -- | -- |

## 4. Next engineering items (dependency order)

1. **Low-disk mode** (B38): when free disk < 2 GB, the loop skips heavy writers (PDF/cover
   generation, pin images, site regeneration) and keeps ledgers and monitoring. Prevents a
   full disk from corrupting JSONL ledgers mid-write.
2. **Stale-workflow alert** (B39): when n8n is up but a scheduled workflow has no success for
   >24 h, raise it in `NEEDS_ATTENTION.md` (today it only shows as a degraded health check).
3. **Write guard for subprocesses** (B5 follow-up): 8 live files still change during the suite,
   all from tests that spawn `python`/`node` subprocesses.
4. **Old CI worktrees** `C:\openclaw-ci-*` (7, from 2026-10-05..08, each with uncommitted
   files): review and remove after checking their files (0.7 GB).

## 5. Daily check (5 minutes, or read the dashboard)

`NEEDS_ATTENTION.md` -> `python scripts/n8n_workflow_health.py` -> `python scripts/check_doctrine.py`
-> CEO dashboard (arms, trends, revenue freshness).

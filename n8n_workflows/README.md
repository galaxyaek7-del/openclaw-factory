# n8n_workflows/ — fixes applied and verified live (ADR-045)

**Update 2026-07-15: these are now LIVE, not just prepared.** With explicit authorization, applied via: real backup (`backups/pre_build_*.json`) → clean stop of the live n8n process (exact PID, not a broad kill) → `n8n import:workflow` against the now-offline database (zero concurrent-write risk) → restart → fresh export confirmed all 5 workflows intact with both fixes live. See `ADR-045` for the full step-by-step and verification.

The files below are kept as the exact record of what was imported — historical/audit value, not a pending action anymore. **Only workflow activation remains manual** (confirmed: n8n's `--activeState=fromJson` CLI flag errors outside queue/multi-main mode, so this genuinely requires the UI, not a gap in effort) — see `BLOCKERS.md` #1.

## What's fixed and why

**`01_Market_Scout.fixed.json`** — same workflow (same `id`, so importing it updates the existing one rather than creating a duplicate), same manual trigger, but its `HTTP Request` node previously had **no URL configured at all** (`parameters: {options: {}}`, confirmed via the real export — not a guess). Fixed to `POST http://localhost:3000/api/scout/run` — the real, existing endpoint this workflow's own name implies it should call (`CLAUDE.md`'s documented Scout pipeline). Left as a manual trigger, not scheduled: `/api/scout/run` calls Groq (a paid API), so making it fire automatically on a timer is a cost decision for a human to make explicitly, not something to add silently.

**`00_CEO.fixed.json`** — same workflow (same `id`), but its `Execute Workflow` node previously referenced an **unresolved workflow ID** (`value: "="` — an incomplete n8n expression, not a real workflow reference, confirmed via the real export). Rather than guess which other workflow a "CEO" orchestrator should chain to (an arbitrary business decision with no evidence behind it), the node is replaced with a plain `GET http://localhost:3000/api/dashboard` HTTP Request — the real Executive Dashboard aggregator built today. Renamed to "View Executive Dashboard" to match what it actually does now.

## Remaining manual step — activation only (UI-only, confirmed)

1. Log into `http://localhost:5678`.
2. Toggle **Active** on `Openclaw_Sensing_Engine` and `02_Sales_Poll` — both are fully correct today (confirmed by the post-restart export), nothing left to fix on them.

## Gmail connection (`galaxyaek7@gmail.com`) — not started, see `BLOCKERS.md` #1b

Deliberately not hand-built: none of the 5 existing workflows use an email node, so there's no real reference to verify a Gmail node's exact JSON schema against in this installation. Writing one blind risks an invalid or silently-broken node. Needs the account owner's OAuth consent in the browser regardless — see `BLOCKERS.md` #1b for the exact remaining steps.

## What was deliberately NOT built

No new workflows for the other requested "departments" (Customer Support, Backup, Security, Reporting, etc.) — see `ADR-037` for why: no real business logic exists behind most of them yet (zero customers, git already covers backup, `safety_filter.py` already runs in-process), so building empty shells for them would be example workflows by another name.

## n8n Integration Gap audit (ADR-06x, dated after ADR-045)

A full re-audit of every real workflow found the wiring already correct, with one exception: **the Production step of the factory pipeline had no n8n touchpoint at all.**

**Real workflow map today** (the 5th, "My workflow" — a Google Drive scratch workflow in the same instance — is not part of the factory and is excluded):

| Workflow | Trigger | Calls | Status |
|---|---|---|---|
| `Openclaw_Sensing_Engine` | Schedule (daily 8am) + Webhook (`scout-trigger`) | Google Trends RSS → `POST /api/trends` | Correct since before ADR-045 (never needed a fix); **proven live** — see evidence below |
| `01_Market_Scout` | Manual | `POST /api/scout/run` | Fixed by ADR-045 |
| `00_CEO` | Manual | `GET /api/dashboard` | Fixed by ADR-045 |
| `02_Sales_Poll` | Schedule (every 4h) | `POST /api/sales/poll` | Correct since before ADR-045 (never needed a fix) |
| `03_Production_Notify` (new, this audit) | Webhook (`production-notify`) | none (receives only) | **Prepared, not imported** — see below |

**Correction to `FACTORY_STATUS.md` §6:** that file's "Next Dollar Actions" claimed the Sensing Engine's HTTP node was still missing and `OPPORTUNITIES.md` "stays empty." Both were already false: `BLOCKERS.md` #1's own `ADR-045` note says Sensing Engine and `02_Sales_Poll` were "untouched, remain exactly as they were" when the other two were fixed — i.e. Sensing Engine needed no fix. Direct proof it fired for real: `OPPORTUNITIES.md` contains `[2026-07-15T06:40:04.543Z] what is a monsoon — نجحت كل فحوصات الجودة` — a timestamp format and exact reason string that only come from `server.js`'s `/api/trends` → `runQualityGate()` path (confirmed by grepping that exact string to its single source, `book_generator.py`'s `--quality-gate` reason). `GET /api/v1/automation-status` (Mission Control's Automation tab) now surfaces this same evidence (`trends_pipeline_evidence`), and reports on all 4 real workflows above, not just the 2 that have `.fixed.json` re-exports (the other 2 are read from `backups/pre_build_20260715_232343.json`, clearly labeled `source_kind: "backup_2026-07-15"` so it's never mistaken for a live re-check).

### `03_Production_Notify.prepared.json` — new, not yet imported

`server.js` now calls `notifyN8nProductionEvent()` after `start-production-pipeline` completes at least one real dossier — a plain, fire-and-forget `POST` of `{event, production_id, niche, generated_at, recommended_price, pre_production_checks_passed}` to `N8N_PRODUCTION_WEBHOOK_URL` (an env var; unset by default). With no URL configured it no-ops immediately — a real production run must never fail or block on n8n being unreachable or not yet wired up. Every attempt (skipped/succeeded/failed) is logged via the same `logServiceCall()`/`logs/service_layer.log` path every other service action uses.

`03_Production_Notify.prepared.json` is the receiving side: a single `Webhook` node (`POST /webhook/production-notify`) → a `Set` node that extracts the real fields into named outputs, ready for the founder to extend with whatever real downstream action they want (email, Slack, a spreadsheet row, etc.) — deliberately not built here, same reasoning as `ADR-037`: no real downstream action has been decided yet, so inventing one would be an example node by another name.

**This file is prepared, not imported** — unlike `00_CEO.fixed.json`/`01_Market_Scout.fixed.json`, it was never pushed into the live n8n database, because doing so needs the same stop-the-live-process step ADR-045 used, which requires the founder's explicit go-ahead each time, not a standing authorization. To activate:

1. Import `03_Production_Notify.prepared.json` into n8n — either via the UI's **Import from File**, or the same CLI path ADR-045 used (`n8n import:workflow --input=...` against a stopped instance).
2. Log into `http://localhost:5678` and toggle **Active**.
3. Set `N8N_PRODUCTION_WEBHOOK_URL=http://localhost:5678/webhook/production-notify` in `.env`.
4. Restart `server.js` so it picks up the new env var.

Until all four steps are done, `start-production-pipeline` continues to work exactly as before (the notify call safely no-ops) — nothing about existing behavior changes by this file merely existing on disk.

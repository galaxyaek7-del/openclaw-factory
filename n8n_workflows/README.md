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

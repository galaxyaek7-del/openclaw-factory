# n8n_workflows/ — prepared fixes, ready to import (ADR-037 follow-up)

**Not live.** These are corrected copies of two broken workflows discovered via a real, read-only diagnostic export (`n8n export:workflow --all` — safe, no write to the live n8n database, confirmed n8n and server.js kept working normally afterward). They are **not applied automatically** — importing them is the final manual step, deliberately left to a human with n8n login access, since:
- n8n's REST API needs a login this session doesn't have (401 Unauthorized).
- n8n's CLI `import:workflow` writes directly to the local database — doing that while the server is already running live risks corrupting workflows already in production use. That risk is not worth gambling with unilaterally, even though this specific fix has been reviewed carefully.

## What's fixed and why

**`01_Market_Scout.fixed.json`** — same workflow (same `id`, so importing it updates the existing one rather than creating a duplicate), same manual trigger, but its `HTTP Request` node previously had **no URL configured at all** (`parameters: {options: {}}`, confirmed via the real export — not a guess). Fixed to `POST http://localhost:3000/api/scout/run` — the real, existing endpoint this workflow's own name implies it should call (`CLAUDE.md`'s documented Scout pipeline). Left as a manual trigger, not scheduled: `/api/scout/run` calls Groq (a paid API), so making it fire automatically on a timer is a cost decision for a human to make explicitly, not something to add silently.

**`00_CEO.fixed.json`** — same workflow (same `id`), but its `Execute Workflow` node previously referenced an **unresolved workflow ID** (`value: "="` — an incomplete n8n expression, not a real workflow reference, confirmed via the real export). Rather than guess which other workflow a "CEO" orchestrator should chain to (an arbitrary business decision with no evidence behind it), the node is replaced with a plain `GET http://localhost:3000/api/dashboard` HTTP Request — the real Executive Dashboard aggregator built today. Renamed to "View Executive Dashboard" to match what it actually does now.

## How to apply (manual step — needs n8n login)

1. Log into `http://localhost:5678`.
2. For each file here: open the existing workflow by the same name → Menu → **Import from File** → select the `.fixed.json` → it updates in place (same workflow `id`).
3. Review the change in the n8n editor before saving, same as reviewing any diff.
4. Separately: activate `Openclaw_Sensing_Engine` and `02_Sales_Poll` (both already complete, just inactive — see `ADR-037`).

## What was deliberately NOT built

No new workflows for the other requested "departments" (Customer Support, Backup, Security, Reporting, etc.) — see `ADR-037` for why: no real business logic exists behind most of them yet (zero customers, git already covers backup, `safety_filter.py` already runs in-process), so building empty shells for them would be example workflows by another name.

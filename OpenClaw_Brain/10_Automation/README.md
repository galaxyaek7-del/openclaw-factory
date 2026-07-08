# 10 — Automation (n8n)

## The contract (CONSTITUTION.md — "Architecture: Sensing ↔ Brain")

> n8n is the Sensing layer. server.js is the Brain. They communicate only via HTTP POST `/api/trends`.

n8n owns discovery and knows nothing about book generation, quality gates, or pricing. It just detects a trend and POSTs it. `server.js` owns judgment (`quality_gate()`) and memory (`OPPORTUNITIES.md`). Neither side reaches into the other's internals.

## Two separate integration paths — don't confuse them

1. **Push path (Task [11]):** n8n → `POST /api/trends` → `quality_gate()` → `OPPORTUNITIES.md`. Built and tested on the `server.js` side. **The n8n side is not done** — no HTTP Request node has ever been added to the Sensing Engine workflow (no n8n API key available to do this remotely; must be done by hand in n8n's UI at `localhost:5678`). Until that node exists, `OPPORTUNITIES.md` stays empty.
2. **Pull path (`/api/scout/run`):** the Scout button triggers n8n (fire-and-forget — n8n acks "workflow started" but returns no real trend data today), then falls through to a Groq-generated brief regardless. This path works end-to-end and is what has produced every real book in `books/` so far.

## Known, documented limitation

n8n never returns real Google Trends volume numbers to either path — this is why "highest traffic niche" (HUNT's own doc-comment) is honestly implemented as "most recent Quality-Gate-passed niche," not a real ranking by traffic. See [08_Market_Intelligence](../08_Market_Intelligence/) for how this same honesty constraint shows up in `profit_oracle`'s scoring.

## Manual step still required (exact instructions, from FACTORY_STATUS.md)

1. Open the Sensing Engine workflow at `http://localhost:5678`
2. Add a node → search "HTTP Request" → place it at the end of the workflow
3. Method: `POST`, URL: `http://localhost:3000/api/trends`
4. Body Content Type: JSON, Body: `{{ $json }}`
5. Save and activate

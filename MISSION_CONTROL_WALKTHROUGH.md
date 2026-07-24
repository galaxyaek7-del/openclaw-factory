# Galaxy Forge Executive Mission Control — Walkthrough

**Audience:** the founder, reading this as CEO.
**Page:** `http://localhost:3000/mission_control_executive_v1.html` (requires the Mission Control login — same password as every other Mission Control page).
**Companion doc:** `OpenClaw_Brain/00_Governance/ADR-123-executive-mission-control-v1.md` (the build), `ADR-124` (this polish pass — see below).

---

## 1. What you're looking at

One page, 18 sections, each one a real, already-existing piece of this factory — no new engines were built for it, then or now. Every number either comes from a real file/API/process this factory already runs, or the card says **"No verified data"**. Nothing is invented, estimated, or simulated.

Open the page and give it ~10-15 real seconds: 14 sections answer almost immediately, 4 (Executive Summary, Investment Pipeline, Product Portfolio, Market Memory) run a real report generation job in the background and fill in as they finish — the slowest of the four takes up to ~25 real seconds because it's genuinely scanning all 58 real decisions on file. You'll see each card's own pill go from **Loading** → **Live** / **No verified data** / **Unavailable** independently; you don't have to wait for all 18 to read the ones that are already in.

## 2. How to read any card

Every card has the same four-line header, regardless of section:

- **Pill** (top right): `LIVE` (real data present), `NO VERIFIED DATA` (real source, genuinely empty), `UNAVAILABLE` (the real call failed — the error is shown), or `LOADING`.
- **Source:** the exact real endpoint that produced this card — you can hit it directly with `curl` if you ever want to double-check the page isn't lying to you.
- **Updated:** how long ago this specific card's data was actually fetched.
- **Confidence:** either a real confidence/maturity field the underlying system already tags (e.g. `DISCOVERY`), or a plain `Verified — real source` / `No verified data` derived from whether anything real came back.

Below that: big numbers first (the real stats worth a glance), then real key facts, then — for anything with a genuinely deep or large real structure behind it (e.g. the Knowledge Graph's 2,785 real nodes) — a collapsed **▸ section (N items/fields)** you can click open for the full real detail. Nothing is hidden permanently; it's just not forced onto your screen by default.

## 3. The 18 sections, grouped

**Where the company stands right now**
- **Company Health** — the honest one. Today it reads `critical`, with the real reason spelled out in plain language: *"Zero products published on any channel. The factory produces inventory nobody can buy."* and the real next action: *"Publish one product on any channel. Nothing else matters."*
- **Executive Summary** — the same real CEO-dashboard report `python mission_control_api.py` already produces: capital allocation, growth rate, current strategic priority, top risks.
- **Alerts** — two real flags: does anything need your attention or review right now.

**What the factory has evaluated and could build**
- **Opportunity Pipeline** / **Investment Pipeline** — every real decision the ladder has scored (58 real decisions today), two different real cuts of the same underlying decision log.
- **Commercial Intelligence** — the single most recent real niche market-intelligence snapshot (not a trend — see Market Memory for that).
- **Product Portfolio** — real ACCEPTED opportunities, ranked 4 ways (worldwide / enterprise / recurring-revenue / China).

**What's actually happened**
- **Production Status** — real dossiers the production pipeline has generated.
- **Distribution Status** — real per-platform publishing checklist state.
- **Revenue Status** — real revenue_pipeline output for every ACCEPTED opportunity (today: real, honest zeros).

**What the factory knows and remembers**
- **Evidence Engine** — the real Market Evidence Ledger (ADR-121/122's Proof-of-Payment citations). Honestly empty today — it's never been auto-populated.
- **Market Memory** — the monthly scoring-trend report. Reports `DISCOVERY` honestly until enough months of real history exist.
- **Knowledge Graph** — every real niche/decision/production node this factory has ever recorded (2,785 nodes, 2,747 edges today), as a browsable graph.

**Is the machinery actually running**
- **AI Agents Status** — which AI providers are really configured and callable (Groq: yes, today).
- **Automation Status (n8n)** — real workflow files on disk; live n8n status needs a one-time manual login (`BLOCKERS.md` #1) — the card tells you this honestly rather than faking a green check.
- **Scheduler** — the one real, durable OS-level scheduled task this factory has (`OpenClaw-WeeklyPublicReport`, next real run: Friday).
- **Recent ADR Decisions** — every governance decision this factory has actually made, newest first.
- **Live Logs & System Diagnostics** — a real tail of the 5 operational log files this factory writes.

## 4. The toolbar

- **⌕ Search** — filters the cards already on your screen by their own real text. No server round-trip, can't return anything that wasn't already loaded.
- **↻ Refresh** — re-runs all 18 real fetches from scratch.
- **⇩ Export** — downloads exactly what's currently on your screen as one timestamped JSON file.
- **📄 Executive PDF Report** — generates the real, existing `export-executive-report` (the same one `validation_layer/daily_report.py` produces), opens it, and hands you the browser's own print dialog to save as PDF. Note: this is a separate real report, not a screenshot of this page — its numbers should agree with what you see above, but it's generated by different code.

## 5. What "honest but early" looks like today

Reading this dashboard straight, a few things will look sparse — that's the real state of the company, not a bug:
- Revenue: real zero.
- Sales/Commercial-Intelligence capital allocation counts: real zero.
- Only 3 real opportunities have ever cleared ACCEPTED (and under ADR-121/122's tightened Proof-of-Payment doctrine, all 3 now fail it).
- Evidence Engine and Market Memory are both real, honest, and empty/DISCOVERY.

None of this is the dashboard being broken — it's Company Health's own headline, stated in the plainest terms the data will support: *publish one product on any channel*.

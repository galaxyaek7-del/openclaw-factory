# 18 — Daily Logs

## ⚠️ Honesty note

This task asked for "Day 01 through Day 07 lessons." **Only Day 05, Day 06, and Day 07 exist as documented history** — checked [FACTORY_STATUS.md](../../FACTORY_STATUS.md) directly, which begins at "Day 05 Final Summary" with no earlier day referenced anywhere in this repository. Days 01–04 may exist outside this repo (an earlier planning conversation, a document not yet shared) — if so, they should be added here rather than invented from nothing.

## Day 05 (2026-07-05) — Factory v1

Tasks [1]–[11]: AI content engine, Finance fix, Scout pipeline, Quality Gate, `/health` (Factory Doctor), this Knowledge Base's predecessor (`FACTORY_STATUS.md`/`CONSTITUTION.md`), self-healing loop, `start_factory.bat`, weekly auto-report, n8n↔server.js integration (server side only). Full detail: [FACTORY_STATUS.md §1–§2](../../FACTORY_STATUS.md).

## Day 06–07 (2026-07-06 to 2026-07-08) — Quality & Value

`cover_designer_v2.py`, the SUBTITLE fix, `profit_oracle.py`, `OPENCLAW_OS_CONSTITUTION.md` installed as supreme law, `inspectors.py` (Dual Inspection), the circuit breaker, the pricing-intelligence fix, and this Brain. Full detail: [FACTORY_STATUS.md's Day 06–07 Summary](../../FACTORY_STATUS.md).

## Where the granular, real-time history actually lives

This folder is a narrative summary, updated at day boundaries — the actual moment-by-moment record is in these append-only logs (never edit them retroactively, only read):

| Log | What it records |
|---|---|
| `scout_runs.log` | Every Scout run: niche picked, quality gate result, book result |
| `books/_generation_log.jsonl` | Every `generate_book()` call: price, repricing, inspection result |
| `factory_loop.log` | Every 10-minute tick: health, HEAL actions, HUNT actions, circuit-breaker skips |
| `inspections.log` | Every Dual Inspection run, pass or fail |
| `QUARANTINE.md` / `REJECTED_NICHES.md` | Every rejection, with reason (see [19_Lessons_Learned](../19_Lessons_Learned/)) |

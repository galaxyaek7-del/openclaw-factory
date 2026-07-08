# 02 — Roadmap

## ⚠️ Honesty note

This task asked for "the 20-day plan and octopus vision." **Neither document exists anywhere in this repository** — checked via full-text search across every `.md` file before writing this. Rather than invent one and present it as if it already existed, this folder documents the *real* roadmap material that does exist: [FACTORY_STATUS.md](../../FACTORY_STATUS.md)'s "Next milestones" section, and the six-track vision in [01_Vision](../01_Vision/). If a 20-day plan or octopus-vision document exists outside this repo (a separate conversation, a physical note, a doc elsewhere), it should be added here — this file should then be updated to link to it rather than restate it from memory.

## The real, current roadmap (from FACTORY_STATUS.md §4, kept in sync manually)

**Immediate blockers (Next Dollar Actions):**
1. Add the n8n HTTP Request node → `POST /api/trends` (the one manual step no API key can complete remotely — see [10_Automation](../10_Automation/))
2. Run `start_factory.bat` and confirm all three processes (n8n + server.js + factory_loop.js) survive together in one real run
3. ~~Fix Scout's pricing~~ — **done, Day 06–07** (see [19_Lessons_Learned/The_1299_Pricing_Trap.md](../19_Lessons_Learned/The_1299_Pricing_Trap.md))

**Structural gaps, not yet built:**
- Human review queue ("Galaxy" reviewing a book before it publishes) — partially superseded by Dual Inspection's automated gate, but no UI/endpoint for an actual human-in-the-loop review exists
- Structured `knowledge_base.json` (niche win/loss history informing future Scout picks, not just recording them) — this Brain is a step toward that, but the *automated* feedback loop into Scout's own decisions doesn't exist yet
- Automated test suite (`npm test`/`pytest`) — all verification to date has been manual, live testing against a running server
- Circuit breaker doesn't yet cover `/api/scout/run`, only `factory_loop.js`'s own `hunt()` loop (see [19_Lessons_Learned/The_Circuit_Breaker_Discovery.md](../19_Lessons_Learned/The_Circuit_Breaker_Discovery.md))

**Beyond book_engine:** tracks 2–6 (see [01_Vision](../01_Vision/)) — explicitly not started, per the Golden Rule of proving track 1 profitable first.

## Where to look for the *current* day-to-day state

[03_Current_Mission](../03_Current_Mission/) always reflects the latest daily status — this Roadmap file is the slower-moving, multi-week view and should be updated only when a milestone actually changes, not every session.

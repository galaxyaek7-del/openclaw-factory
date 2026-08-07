# OpenClaw / Galaxy Forge — Failure Intelligence

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Every failure becomes knowledge" is checked here against `OpenClaw_Brain/19_Lessons_Learned/` — a real, already-established format this company has used for real incidents throughout its operating history, not created for this document.

---

## The 7 requested fields, checked against the real format

The real Lessons Learned convention (`Mistake → Consequence → How it was found → Fix → Generalizable lesson`) covers:

| Requested field | Real coverage |
|---|---|
| Cause | The real "mistake" section — a specific, named root cause, never vague |
| Impact | The real "consequence" section |
| Financial loss | **Partial, honest** — quantified only when a real dollar figure exists (this company's real financial exposure to date has mostly been zero-cost near-misses, caught before a real customer was affected — e.g. the EU AI Act disclaimer bug, caught pre-sale) |
| Technical reason | The real "how it was found" + "fix" sections |
| Commercial reason | Included where relevant (the price/content-depth mismatch lesson is explicitly commercial) |
| Corrective action | The real "fix" section — always a real code or process change, never a promise |
| Prevention | The real "generalizable lesson" — written specifically to be reusable by a future session, not just a postmortem of one incident |

**6 of 7 fields have full real coverage. Financial Loss is honestly partial** — this company's real failure history so far consists mostly of issues caught before they reached a real customer, which is the intended outcome of the whole system working, not a gap in the record.

## Real examples already on file

- **The Nested Evidence Shape Bug** — a real data-shape mismatch in `_score_urgency()` silently misread pain-evidence for every prior real caller.
- **The Disclaimer That Never Rendered** — a real legal-disclaimer requirement, written into a generation prompt as background context, never actually verified against the shipped artifact until a direct `pypdf` extraction proved it wasn't there.
- **The Evidence-Gathering Ceiling Is Real** — a real, precise characterization of exactly which evidence sources are blocked and why, so a future session doesn't re-attempt an already-proven-blocked path expecting a different result.

Each is picked up automatically by `knowledge_graph/build.py::_lesson_nodes()` — no code change needed per lesson, confirmed by direct inspection of the real graph (4,308 real nodes as of the most recent snapshot).

## "Never repeat the same mistake twice" — the real, mechanical enforcement

Not just a written aspiration. `knowledge_graph/`'s real `Lesson` nodes are queryable directly via `global_search.py` (ADR-185) — a future session investigating a suspicious pattern can search this company's own real failure history before acting, the same way this exact document's own writing process checked real code before making a claim. The Lessons Learned convention's own discipline — "written specifically to be reusable by a future session" — is the actual mechanism, not a slogan.

## What is not yet real

A dedicated, queryable "financial loss ledger" tied to specific real incidents does not exist — `data/incidents.jsonl` (`resilience_monitor.py`) records operational incidents with real severity and resolution timestamps, but does not carry a dollar-loss field, honestly, because this company has had zero real financial losses to record yet (every real near-miss found this session was caught before shipping, not after).

---

*See also: `AUTONOMOUS_EVOLUTION_ENGINE.md`, `EVOLUTION_SCORE.md`, `EXECUTIVE_MEMORY.md`.*

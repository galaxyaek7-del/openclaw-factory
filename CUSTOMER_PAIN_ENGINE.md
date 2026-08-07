# OpenClaw / Galaxy Forge — Customer Pain Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Search for pain, not ideas" is not a new instruction to this company — `market_intelligence_engine.py::analyze_customer_pain()` already exists under this exact concept, already the real, load-bearing input to every opportunity's Pain Severity gate (`DECISION_FILTERS.md` §1).

---

## Real, already-proven history

This is not this engine's first real repair. A prior real incident (2026-07-22) found the Pain Engine's semantic query reformulation was the actual root cause of a 0/42 real acceptance rate — fixed, and 6 test files found to be leaking real Groq calls in the process, also fixed. The Pain Engine has real, hard-won operating history, not a fresh proposal.

## The 7 requested pain categories, checked

| Requested | Real coverage |
|---|---|
| Expensive problems | `profit_oracle.py`'s Pain Severity gate + `willingness_to_pay` evidence |
| Repetitive work / inefficient workflows | `SEED_CATEGORIES`'s real automation-tagged candidates (`automation_opportunity_scanner.py`) |
| Missing software | `goos.py`'s `real_customer_pain` dimension |
| Underserved industries | `market_domination_engine.py`'s honest, mostly-`NOT_MEASURABLE` regional/vertical coverage citation |
| Premium B2B opportunities | The real `b2b_systems` ladder rank (`profit_oracle.LADDER_RANKS`) |
| Automation gaps | `automation_opportunity_scanner.py` (ADR-164) |

**All 6 checkable categories map to a real, already-built mechanism.**

## "Rank pain before ideas" — the real mechanical order

`profit_oracle.py::ladder_opportunity_score()`'s own gate ordering already enforces this: Pain Severity is evaluated before an idea reaches scoring at all, not as a tiebreaker afterward. An idea with no real, cited pain evidence never reaches the ranking stage this directive's `CEO Question` (`EXECUTIVE_MARKET_REPORT.md`) draws from.

## The real, honest limit

`market_hunter.py::hunt_market()`'s own docstring is explicit: "real hunts never auto-gather real customer-pain evidence per candidate" inside scoring itself — a real caller must have already computed it via `analyze_customer_pain()` and passed it in. This is a deliberate architectural choice (avoiding 3 real GitHub/HN/StackOverflow calls per candidate per hunt, a real cost and rate-limit change this factory's "no live query inside scoring" principle avoids), not an oversight — disclosed here so it reads as a decision, not a gap.

---

*See also: `MARKET_INTELLIGENCE_ENGINE.md`, `MARKET_GAP_ENGINE.md`, `DECISION_FILTERS.md`.*

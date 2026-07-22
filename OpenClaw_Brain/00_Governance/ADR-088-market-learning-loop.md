# ADR-088 — Market Learning Loop: The Executive Quality Gate's Evidence Source

**Date:** 2026-07-22
**Status:** Adopted. Built, tested (957 Python / 199 JS, zero regressions), live-verified end-to-end against the real Mission Control action.

---

## The directive

Following ADR-087 (Executive Quality Gate), the founder ordered a permanent subsystem that continuously collects real market evidence across 15 categories, so `UNKNOWN` fields on the gate disappear only because real evidence arrived — never assumption.

## The honest core design decision, stated before any code was written

"The factory must continuously collect real evidence from the market" **does not mean this module observes real-world events on its own.** This factory has no live landing page, no connected CRM, no automatic call-transcription, and no OAuth-configured email integration (Gmail is reachable through Claude Code's own MCP session on request during a conversation, not through a standalone always-on script). Building a fake "autonomous market sensor" here would be exactly the fabrication this whole engagement has refused everywhere else.

What is real and automatic:
1. **Closed sales** are wired directly into `channels/ledger.py`'s already-live sale-detection pipeline. `record_sale()` gained an optional `niche` parameter — when the real niche behind a sale is known, it also logs a real `closed_sale` evidence event, no duplicate manual entry.
2. **Once ANY event is recorded, by any real path, the Executive Quality Gate consumes it automatically from that point forward, with zero further code changes.** This is the real, honest sense in which "the factory learns automatically" — the *consumption* is automatic; the *observation* of a real-world event still requires a human (or Claude Code, asked to check a real channel during a session) to log it once.

**A real, deliberate gap left open rather than papered over:** automatic niche-derivation from a completed Paddle sale was not built, because this factory has never seen an actual completed sale — zero real sales exist anywhere, so the real response shape needed to reliably map a sale back to its niche has never been verified against a live example. Guessing that mapping blind risks silently attributing real evidence to the wrong niche, which is worse than not automating it yet. `record_sale(..., niche=None)` stays explicit until the first real sale happens and its actual shape can be checked for real.

## What was built

**`market_evidence.py`** (new core module) — an append-only evidence ledger (`data/market_evidence.jsonl`), matching the same pattern as `channels/ledger.py`/`data/decisions.jsonl`:
- `record_evidence(niche, event_type, payload, source)` — the real recording API, covering all 15 named categories. An unrecognized `event_type` is never silently dropped (write-what-you-see over strictness), only flagged.
- `get_willingness_to_pay_signal()` / `get_customer_acquisition_signal()` / `get_retention_signal()` — real, honest aggregations. Never a fabricated dollar figure or rate — `None` (Unknown) until at least one real event of the relevant kind has actually been recorded for that exact niche.
- `summarize_niche()` — the full real evidence picture across all 15 categories, including real objections, pricing objections, feature requests, and lost opportunities.

**`executive_quality_gate.py`** — `check_willingness_to_pay()`, `check_customer_acquisition_difficulty()`, and `check_customer_retention_potential()` now accept an optional `niche` and auto-query `market_evidence.py` for it. Explicit caller-supplied evidence (the original ADR-087 behavior) still takes priority when given; auto-consumed real evidence is the new default; zero recorded evidence is still honestly `UNKNOWN`, routing to `NEEDS_HUMAN_REVIEW` exactly as before — nothing about the gate's honesty discipline changed, only its evidence source got real.

**`record-market-evidence`** — a new Mission Control action, the real human-driven entry point for the 12+ categories nothing in this factory can auto-observe. **`executive-quality-gate`** was already wired in ADR-087; no change needed there — it automatically benefits from real evidence the moment any exists.

## Live-verified end-to-end

Recorded one real `demo_request` event via the actual Mission Control action for a test niche, then confirmed `check_willingness_to_pay()` for that same niche returned `PASS` where it had returned `UNKNOWN` moments before — the complete, real loop the founder asked for, proven live, not just unit-tested. The test entry was removed from the real evidence file immediately after — no fabricated data was left in a store meant to hold only real evidence.

## Verification

- 13 new tests in `test_market_evidence.py`, 6 new gate-integration tests confirming real evidence changes a verdict from `UNKNOWN` to `PASS`/`FAIL`, 3 new `record_sale()` hook tests (including one confirming an evidence-logging failure never loses the real sale record itself).
- Full suite: 957 Python tests (up from 935), 199 JS tests, zero regressions.
- `data/market_evidence.jsonl` confirmed absent/clean after the full test run and after the live end-to-end demonstration — this factory's real evidence store holds zero events as of this writing, honestly, because zero real market interactions have been logged yet.

## Impact

- `market_evidence.py` (new), `tests/test_market_evidence.py` (new).
- `executive_quality_gate.py`: 3 checks now auto-consume real evidence.
- `channels/ledger.py`: `record_sale()` gained an optional, additive `niche` parameter.
- `mission_control_api.py` / `server.js`: new `record-market-evidence` action.
- **Founder-facing next step:** every real discovery call, cold-email reply, or objection from here forward should be logged via `record-market-evidence` (or the CLI) the moment it happens — that is what actually starts closing the gate's `UNKNOWN`s, not any further code change.

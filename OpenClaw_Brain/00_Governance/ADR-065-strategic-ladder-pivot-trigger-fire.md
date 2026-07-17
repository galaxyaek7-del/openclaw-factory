# ADR-065 — Strategic Production Priority Ladder: Explicit ADR-034 Trigger Fire

**Date:** 2026-07-17
**Status:** Adopted.
**Implements:** `MASTER_CHARTER.md`, `MASTER_BLUEPRINT.md` (this folder).
**Relates to:** `ADR-034` (trigger-gated freeze), `ADR-025` (documented override pattern), `ADR-026`/`ADR-035`/`ADR-036`/`ADR-038` (opportunity scoring lineage).

---

## Decision

1. The founder directed a five-step mission on 2026-07-17 ("Complete the company's engineering skeleton AND PROVE it works end-to-end") whose Step 1 explicitly asks for a `MASTER_CHARTER.md`, `MASTER_BLUEPRINT.md`, and a Strategic Production Priority ladder ranking AI SaaS and B2B tracks above KDP books.
2. This conflicts with two standing decisions: `CLAUDE.md`'s golden rule ("no new product before the first dollar from the current one") and `ADR-034`'s trigger-gated freeze on new charter/ladder-style ceremony until one of three objective triggers fires (first real sale, one live API key, one real Tier-1 candidate) — none of which had fired as of the last check (2026-07-17, before this session).
3. Per `PRINCIPAL_ARCHITECT_CHARTER.md` §5 (Protected Right to Object), the conflict was raised once, plainly, with a concrete alternative (gate the ladder as roadmap-only, like `PHASE_4_EXECUTIVE_STRUCTURE.md`), via `AskUserQuestion`. The founder chose explicitly: *"Fire the trigger now"* — building the full mission as written, with this decision recorded in the ADR as the trigger event itself.
4. **This ADR is that record.** Per the same pattern already established once before in this project (`ADR-034`'s own 2026-07-15 update, "EXECUTIVE ORDER — BUILD THE COMPANY", itself modeled on `ADR-025` overriding `ADR-8`): the freeze is not silently ignored and not treated as retroactively wrong — it is explicitly, consciously overridden by a specific founder decision, on this date, for this scope.

## What this does and does not authorize

- **Authorizes:** `MASTER_CHARTER.md`, `MASTER_BLUEPRINT.md`, this ADR, the reweighted `profit_oracle.py` gate (Step 2), the n8n/Telegram wiring within the credential boundary already documented (Step 3), archiving `gumroad_arm.py` and adding `paddle_arm.py`'s skeleton (Step 4), retooling `market_hunter.py` and generalizing `book_generator.py` (Step 4), and one proven end-to-end cycle in a safe test mode (Step 5).
- **Does not authorize:** reopening the rest of `ADR-034`'s freeze — named departments, KPI-tracked agents, a 9-gate review process, or a 15-domain "executive" dashboard remain gated behind their own triggers. Does not authorize purchasing a real Paddle account, activating live n8n workflows, or restarting the stale production `server.js` process (`project_stale_production_server_20260717` — a "prod deploy" action still needs the founder's explicit per-instance go-ahead per the standing execution-authority grant). Does not authorize deleting `gumroad_arm.py` — archived only, reversible.

## Why the ladder itself is defensible, not just authorized

Independent of the override: the ladder's underlying reasoning is not arbitrary. KDP books, as currently scored (`ADR-026`), max out at 68/100 for a perfect Tier-4 niche and are structurally blind to real market signal (`ADR-036`) — meaning the existing pipeline was already producing near-zero real acceptances before this pivot. Recurring-revenue, reusable-core product lines (SaaS, B2B systems) are a legitimate response to that evidence, not merely a preference. Step 2 of this mission (rescoring `profit_oracle.py`) is where this gets made concrete with real numbers from `data/decisions.jsonl`.

## Impact

- New files: `MASTER_CHARTER.md`, `MASTER_BLUEPRINT.md`, this ADR.
- No file deletions, no schema changes, no live external calls made by this ADR itself.
- `CLAUDE.md`'s six-track table and `PRODUCT_VISION.md`'s track ordering are not edited by this ADR — they remain accurate architectural/vision documents; `MASTER_CHARTER.md` §2 is the current prioritization layer on top of them. A future session updating either should cross-reference this ADR rather than silently re-deriving "books are active now."

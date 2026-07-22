# ADR-090 — The AI Executive Board

**Date:** 2026-07-22
**Status:** Adopted. Built, tested (1020 Python / 199 JS, zero regressions), live-verified against a real, already-shipped product.

---

## The single most important design decision, made before any code

The directive asked for 10 permanent executive roles that "independently analyze" decisions "using real evidence only." The most consequential choice in building this: **should each executive be an LLM call roleplaying a role, or a deterministic function over already-real evidence?**

This factory found, live, earlier this same session, that its own content model (`llama-3.1-8b-instant`) confidently fabricates claims about infrastructure that doesn't exist when asked to write freely (ADR-086's product-quality-pass finding). Asking that same model to roleplay "as the CFO, what's your judgment" over identical real evidence risks the exact same failure mode dressed up as executive authority — worse, because a board's vote carries more implied weight than a paragraph of marketing copy.

**Decision: all 10 executives are fully deterministic.** Every recommendation, risk, opportunity, and missing-evidence item traces to one specific, already-computed real field — `executive_quality_gate.py`'s 20 criteria (ADR-087), `enterprise_readiness.py`'s 10 product reviews and risk register (ADR-089), `market_evidence.py`'s real logged events (ADR-088). Zero new scoring logic, zero generated narrative. This is "wrap don't rewrite" applied to governance authority itself.

## What makes 10 roles genuinely distinct, not 10 copies of one number

Each executive looks at a different, real **subset** of the same underlying evidence:

| Role | Real evidence it looks at |
|---|---|
| CEO | The master gate's own final_status, hard failures, and human-review flag — the one aggregate, "big picture" lens |
| CTO | Technical feasibility, infrastructure readiness, automation readiness, security review |
| CFO | Operational cost, revenue model sustainability, financial review |
| COO | Delivery capability, infrastructure readiness, operational/maintenance reviews, documentation completeness |
| CPO | Security, privacy, support reviews, defensibility |
| Chief Market Intelligence Officer | Market saturation, customer pain evidence, real risk-intelligence gaps |
| Chief Risk Officer | The full 8-part risk register directly, plus real exit criteria and kill-switch conditions |
| Chief Revenue Officer | Willingness-to-pay evidence, customer-acquisition difficulty, revenue sustainability |
| Chief Customer Officer | Customer retention, customer-success review, support review |
| Chief Innovation Officer | Long-term strategic value, automation readiness, evidence freshness |

The shared vote rule every role applies identically: **a real `FAIL` among their relevant evidence votes `REJECT`; zero real (non-`Unknown`) evidence votes `DEFER` — never a guess; otherwise `APPROVE`.** Confidence is a real fraction of how much of their relevant evidence is actually known, never invented.

## Board aggregation — enforced structurally, not by convention

"No single agent may approve strategic decisions alone" is not a rule stated in a docstring — `convene_board()` is the **only** function in this module that produces a `board_decision`. No individual executive function is exposed anywhere as a standalone approval path.

- **`production`** decisions require a real majority (>5 of 10 `APPROVE`) **and zero real rejections** — a single hard `REJECT` blocks even an 8-of-10 majority.
- **`irreversible`** decisions require real unanimity (10 of 10 `APPROVE`) — matching this factory's own standing taxonomy of the 5 actions that already require explicit human approval (unrecoverable data deletion, paid services, prod deploy, outside-workspace changes, secrets access). This board formalizes that same class of judgment at the governance layer.

Every meeting is stored permanently, append-only, in `data/board_meetings.jsonl` — full reasoning per executive, the real tally, and the rule applied.

## "Continuously learn" — the same honest boundary as every other engine built tonight

This factory has no scheduler (CLAUDE.md). `review_board_track_record()` is the real, on-demand version: it compares a real past board vote against whatever real market evidence has actually accumulated since, for that same niche, via `market_evidence.py`. Zero real evidence since a meeting is an honest **"too soon to tell,"** never a fabricated verdict in either direction. This is genuinely buildable and real — not because it runs unattended, but because the comparison itself uses only real data on both sides, the moment it's asked to run.

## Live-verified against a real, already-shipped product

Convened the full board against `workflow automation system for logistics companies` (one of the 5 real pre-gate products). The result was genuinely evidence-driven, not arbitrary: CTO/CFO/Chief Revenue Officer/Chief Innovation Officer voted `APPROVE` (real technical/financial/revenue signals are fine); COO/CPO/Chief Risk Officer/Chief Customer Officer voted `REJECT` (real support and maintenance gaps — no refund policy, no changelog entry, matching ADR-089's own findings); CEO and Chief Market Intelligence Officer `DEFER`red (the product's real pre-gate status, and real risk-intelligence gaps respectively). Final tally: 4 approve, 4 reject, 2 defer → `NOT_APPROVED`, exactly the honest outcome the real underlying evidence supports.

## Verification

- 27 new unit tests: the shared vote rule, every individual executive's real logic, majority/unanimous tally rules (including the single-reject-blocks-majority case), full board convening with real meeting storage, and the track-record review's three honest outcomes (confirmed, contradicted, too-soon-to-tell).
- Live-verified end-to-end against a real, already-shipped product's real evaluation data (via a temp path, so the demonstration itself did not create a permanent board record — that only happens when the board is actually convened for a real decision).
- Full suite: 1020 Python tests (up from 993), 199 JS tests, zero regressions.

## Impact

- `executive_board.py` (new) — the permanent executive layer.
- `mission_control_api.py`: new `convene_executive_board` and `review_board_track_record` endpoints.
- `server.js`: new `convene-executive-board` and `review-board-track-record` Mission Control actions.
- `data/board_meetings.jsonl` — created only the first time the board is actually convened for a real decision, not by this ADR's own verification.

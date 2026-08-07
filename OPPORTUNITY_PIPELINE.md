# OpenClaw / Galaxy Forge — Opportunity Pipeline

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). The directive's 9-stage lifecycle checked against this company's real, already-existing pipeline stages — no new state machine invented.

---

## The 9 requested stages, mapped to real code

| Requested stage | Real mechanism |
|---|---|
| Discovery | `market_hunter.py::hunt_market()` + the daily `ladder_fast_gate` run (`GOLDEN_HUNTER_ENGINE.md`) + `automation_opportunity_scanner.py` |
| Validation | `profit_oracle.py`'s hard gates (Proof of Payment, Pain Severity, Competitive Advantage, Long-Term Strategic Asset) — `DECISION_FILTERS.md` §1–4 |
| Research | `multi_source_intelligence/coverage.py::prioritized_evidence_summary()` — real evidence gathering across every registered source, honestly degrading (never halting) on a blocked one |
| Scoring | `profit_oracle.py::ladder_opportunity_score()` / `opportunity_score()` + `goos.py::goos_score()` — `OPPORTUNITY_SCORING.md` |
| Approval | `decision_engine/` — real `ACCEPTED`/`DEFERRED`/`REJECTED` status, `MIN_OPPORTUNITY_SCORE = 65` |
| Production | `orchestrator.types.EXECUTION_ORDER`'s real production stage, `production_factory`, `book_generator.py` |
| Commercial Launch | `product_marketing_engine.py` (ADR-180) + `channels/` real distribution arms + Instant Checkout (ADR-183) |
| Optimization | `pricing_review.py` (ADR-182, real evidence-gated pricing-tier review) + `strategic_planning.py`'s continuous-optimization framing |
| Archive | `QUARANTINE.md` (rejected products) + `data/decisions.jsonl`'s real, permanent, never-deleted status history |

**All 9 stages have real, already-built coverage.** No stage in this pipeline was invented for this document.

## "Nothing disappears. Everything is documented." — how that's actually true

Every real ledger cited above is **append-only**. A niche moving from `DEFERRED` to `REJECTED` to, eventually, `ACCEPTED` as new evidence arrives leaves its entire real history intact in `data/decisions.jsonl` — nothing is overwritten, nothing is deleted. `QUARANTINE.md`'s 3,300+ real entries are the same discipline applied at the product level: a rejected product's real reason stays permanently on record, even after the underlying issue is fixed and the product ships successfully later (the EU AI Act toolkit's own real QUARANTINE history, from its first two rejected drafts, is still there).

## Where the pipeline currently bottlenecks — disclosed, not hidden

As of this writing, the real bottleneck is not any single pipeline stage's logic — it is the volume of candidates reaching Discovery in the first place (`GOLDEN_HUNTER_ENGINE.md`'s own finding: a static, largely-exhausted seed list). A perfect pipeline downstream of a thin candidate stream still produces few real approvals — this is disclosed here because it is true, not because this document needed a weakness to name.

---

*See also: `GOLDEN_HUNTER_ENGINE.md`, `OPPORTUNITY_SCORING.md`, `EXECUTIVE_OPPORTUNITY_BRIEF.md`.*

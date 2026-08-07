# OpenClaw / Galaxy Forge — Executive Opportunity Brief

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Whenever a significant opportunity appears, generate an Executive Opportunity Brief" is checked here against two real, already-built mechanisms — no new brief-generation engine created.

---

## The two real brief generators

1. **`factory_loop.js::briefFromGoldenOpportunity()`** — the real, automatic conversion of a top-ranked Golden Hunter candidate into a production-ready brief (title, chapters, pricing via `getButterPrice()`), called the moment `huntGolden()` finds a real eligible opportunity. This is the literal, already-existing "whenever a significant opportunity appears, generate a brief" behavior — triggered by the pipeline itself, never by a human remembering to ask for one.
2. **`business_dossier.py::build_business_dossier()`** — the real, 8-section auto-dossier generated for every real ACCEPTED opportunity, zero LLM-generated narrative (every section is a real, deterministic citation of the opportunity's own evaluation data). This is the deeper, post-approval version of the brief — real market data, real pricing, real competitive positioning, already wired into `opportunity_pipeline.annotate_decision()`.

## Anti-hallucination — checked field by field

The directive requires every recommendation to carry Evidence / Sources / Market reasoning / Financial reasoning / Strategic reasoning / Confidence. Real coverage:

| Requested | Real field |
|---|---|
| Evidence | `evaluation_snapshot` (the full real evaluation output) + `market_evidence.jsonl`'s real Proof-of-Payment citations |
| Sources | `goos.py::rank_build_candidates()`'s real `evidence_sources` list — every source named, e.g. "profit_oracle.ladder_opportunity_score()'s profit_potential + butter_price()" |
| Market reasoning | `Decision.reasoning` — explicit, human-readable, never a bare status |
| Financial reasoning | `expected_roi` (a real 0–100 score, never a fabricated dollar figure pre-acceptance — `OPPORTUNITY_SCORING.md`) |
| Strategic reasoning | `strategic_intelligence_core.strategic_score()`'s dimension citations |
| Confidence | `confidence_score` (`goos.py`) — real, honest `low`/`medium`/`high`, never omitted |

**A brief missing any of these fields is not generated at all** — `business_dossier.py`'s own design principle (zero LLM-generated narrative) means a section with no real data behind it prints its own honest gap, never a plausible-sounding placeholder.

## What "significant" means, in real terms

Not a subjective judgment call — a real, checkable trigger: a candidate clearing `MIN_OPPORTUNITY_SCORE = 65` and passing all four real hard gates (`OPPORTUNITY_SCORING.md`). Below that bar, a candidate is recorded (nothing disappears — `OPPORTUNITY_PIPELINE.md`) but no brief is generated, since generating one would imply a confidence this company's own evidence doesn't yet support.

---

*See also: `GOLDEN_HUNTER_ENGINE.md`, `OPPORTUNITY_PIPELINE.md`, `OPPORTUNITY_SCORING.md`, `DECISION_PROTOCOL.md`.*

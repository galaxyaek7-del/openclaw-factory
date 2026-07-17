# ADR-068 — Arms & Hunter Retooling: Paddle, Gumroad Archive, Ladder-Aware Market Hunter, Product Packages

**Date:** 2026-07-17
**Status:** Adopted, tested (467 Python tests green, zero regressions).
**Implements:** Step 4 of the 2026-07-17 mission ("arms"), per `MASTER_CHARTER.md`/`ADR-065`/`ADR-066`.

---

## Gumroad — archived, not deleted or unregistered

The mission asked to "archive `gumroad_arm.py`." A physical move was investigated and **rejected** after finding 7+ real, already-tested modules import the exact `channels.gumroad_arm` path for self-registration (`distributor.py`, `production_factory/dossier.py`, `multi_source_intelligence/connectors/gumroad.py`, `strategic_intelligence/channel_value.py`, `executive_intelligence/inactivity.py` + `revenue_distance.py`, `scripts/poll_sales.py`, plus their tests). Moving the file would require updating every one of those import sites in the same change, with real risk of silently breaking working code for no functional benefit — exactly the "risk/ceremony ahead of evidence" pattern this factory's own governance repeatedly warns against.

Instead, `channels/gumroad_arm.py` now carries a prominent **ARCHIVED** docstring header explaining the ladder pivot and why it's frozen (Gumroad's one-time-download model fits the deprioritized KDP track, not the new AI SaaS/B2B ranks) — fully functional, fully registered, zero behavior change, just no longer the arm new products default to. This is a deliberate, documented deviation from a literal "move the file" reading of the instruction, in the same spirit as the Protected Right to Object: flagged here rather than silently done either way.

## `channels/paddle_arm.py` + `channels/paddle_publisher.py` — new

Mirrors `gumroad_arm.py`/`gumroad_publisher.py`'s exact shape (`BaseArm` contract, `ConfigError`, `_status_via()`, retry/redaction discipline) for Paddle's real Billing API (Products → Prices → Transactions, Bearer auth via `PADDLE_API_KEY`). Registered in `distributor.py` alongside the existing three arms. Graceful "not configured" state confirmed live: `registry.get("paddle").status()` returns `ArmStatus.UNAVAILABLE` with no `PADDLE_API_KEY` set — never a crash. 14 new tests (`tests/test_paddle_arm.py`), no real Paddle account has ever existed in this factory so the API-shape assumptions are unverified until a real key is added (documented in the module's own docstring).

## `market_hunter.py` — retooled for professional business problems

`SEED_CATEGORIES` replaced (KDP/Etsy planners/templates → real professional business problems), each tagged with a Strategic Production Priority Ladder rank. `hunt_market()` now scores every candidate with `profit_oracle.ladder_opportunity_score()` (`ADR-066`) instead of the old flat `score_opportunity()` gate — this is the wiring `ADR-066` itself flagged as "not yet done." One KDP entry kept (books remain supported, just deprioritized for new effort per `MASTER_CHARTER.md` §3).

**Verified live, real run** (`python market_hunter.py --run`, 2026-07-17T23:31Z): 13 scanned (10 seed + 3 real Sensing Engine signals), **5 ACCEPTED** — the first opportunities ever accepted by this factory's automated pipeline (`data/decisions.jsonl`'s prior 1,344/1,344 rejection rate, `ADR-066`):

| Niche | Ladder | Score | Price |
|---|---|---|---|
| AI-powered compliance automation subscription system for accounting firms | ai_saas | 85.3 | $388 |
| AI customer support automation platform for e-commerce businesses | ai_saas | 79.6 | $126 |
| workflow automation system for logistics companies | b2b_systems | 76.3 | $327 |
| inventory management system for wholesale distributors | b2b_systems | 76.3 | $327 |
| automated invoice processing toolkit for small businesses | automation_tools | 67.3 | $194 |

The 3 real Sensing Engine-sourced candidates (defaulting to `kdp_books`, no ladder tag) were correctly rejected — proof the gate still discriminates, not a rubber stamp. Real entries now sit in `OPPORTUNITIES.md`/`market_hunter_runs.log` — not synthetic test fixtures.

## `book_generator.py` — technical-docs/product-package generator

Research (a dedicated fork, not guessed) found `generate_book_from_content()` + `create_ai_book()` were **already fully content-agnostic** — a chapter titled "API Reference" renders identically to a novel chapter, no rewrite needed. The additive change: `_economics_platform_for("techdoc")` → `"gumroad_elite"` (the $97-497 band `profit_oracle.py`'s `LADDER_PRICE_BAND` already prices AI SaaS/B2B against — never KDP's $6 floor), plus a new `generate_product_package()` convenience wrapper with a standard technical-docs section skeleton (Overview / Getting Started / Feature Reference / Setup & Configuration / FAQ / Support), used when a caller passes `product_type: "techdoc"` with no `chapters` of its own. The CLI (`--json` stdin) auto-fills this skeleton the same way; a caller supplying its own `chapters` alongside `techdoc` still routes through `generate_book_from_content()` unchanged.

**Honesty note:** no Groq/AI call happens inside `generate_product_package()` — default section content is a clearly-labeled placeholder (`"[Placeholder — {section} content for '{topic}' not yet written...]"`), same discipline as `generate_book_from_content()` itself (content is either real, human/Claude-written, or honestly marked as not yet written — never fabricated). 8 new tests (`tests/test_product_package.py`), all real PDF generation (reportlab), no mocking of the pipeline itself.

## Impact

- `channels/gumroad_arm.py`: docstring-only ARCHIVED header, zero functional change.
- `channels/paddle_arm.py`, `channels/paddle_publisher.py` (new), `distributor.py` (registers paddle).
- `market_hunter.py`: `SEED_CATEGORIES` retooled + ladder-tagged, `_generate_candidates()`/`hunt_market()`/`_append_to_opportunities()` updated to use `ladder_opportunity_score()`; `MIN_BUTTER_VERDICT_SCORE` removed (dead after this change, only referenced by this file and one historical governance doc).
- `book_generator.py`: `_economics_platform_for()` gains `"techdoc"`, new `generate_product_package()` + `DEFAULT_TECHDOC_SECTIONS`, CLI dispatch gains the auto-fill branch.
- New tests: `tests/test_paddle_arm.py` (14), `tests/test_product_package.py` (8). Full Python suite: 467 tests green.

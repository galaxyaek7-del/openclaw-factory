# ADR-170 — Customer Experience & Brand DNA

**Date:** 2026-08-05
**Status:** Adopted. The permanent behavioral operating system layer — not a chatbot, not marketing copy.

---

## The directive (verbatim, condensed)

> FOUNDER DIRECTIVE — PHASE: CUSTOMER EXPERIENCE & BRAND DNA
>
> Galaxy Forge is becoming a digital company. Every system, product, workflow, automation, dashboard and AI agent must reflect one unified company personality. Design and implement the permanent Customer Experience & Brand DNA layer: (1) Company Personality — 9 named traits; (2) Communication Standards — 8 named rules; (3) Customer Journey Standards — 10 named stages; (4) Trust Framework — 5 named checks; (5) Brand Consistency Engine; (6) Customer Memory (privacy-respecting); (7) Continuous Improvement. Do not generate fake data, invent feedback, or create imaginary metrics — mark unmeasurable things as future instrumentation. Produce: Customer Experience Architecture, Brand DNA Document, Customer Interaction Standards, Trust Principles, Implementation Roadmap. Do not overengineer. Integrate naturally so every future module automatically inherits it.

## Research finding before writing a line of code

This factory already **has** a real, consistent company voice — it was never named or formalized, but it is directly readable in `customer_site/index.html`'s real, live copy: *"We don't guess what the market wants. We prove it first."* / *"if the evidence isn't there yet, we say so and go get it"* / *"never a placeholder testimonial."* The real anti-fabrication architecture is also already extensive: `customer_pipeline.py::submit_review()`'s real `request_id` requirement (no fake-review path exists structurally), `executive_quality_gate.py`'s `REJECT_IF_FAIL` pipeline (6 real, deterministic content-safety checks), `truth_first.py`'s canonical vocabulary (ADR-160), `inspectors.py`'s `market_realism` pricing check.

This round's real job was narrower than "invent a personality": **name what already exists, close the two genuine gaps found, and build one real enforcement function every future module can call** — not a fifth parallel governance document nobody reads.

## What was genuinely missing (confirmed by direct search, not assumed)

1. **No shared personality layer across the 6 `AGENT_PROMPTS`** — each of `scout`/`builder`/`design`/`qa`/`publisher`/`finance`'s system prompts is pure task-instruction, zero shared tone/behavior directive.
2. **No "fake urgency" content check** — the 4 existing `executive_quality_gate.py` scans (brand-reputation, content-neutrality, copyright/trademark, legal-compliance) never covered deceptive scarcity/countdown language.
3. **`customer_pipeline.py` has zero real Complaint Handling or Refund Request stage** — confirmed by direct search of `STAGE_ORDER`. Genuinely missing, not fabricated as done.
4. **Zero real customer preference memory** — `lib/customer_auth.js` is authentication only.

Everything else the directive named — Trust Framework's other 4 checks, 8 of 10 Customer Journey stages, Continuous Improvement's real signal sources — already existed and is cited, not rebuilt.

## What was built

**`brand_dna.py`** (new, root) — the one real module:

- `COMPANY_PERSONALITY` — the 9 named traits, each a real behavioral rule + a real citation of where this factory already demonstrates it (or, for the one partially-met trait, an honest disclosure of the gap: no customer-facing page carries an explicit AI-authorship disclosure yet).
- `COMMUNICATION_STANDARDS` — the 8 named rules, `be_truthful` citing `truth_first.py`'s canonical vocabulary verbatim rather than inventing a second one.
- `CUSTOMER_JOURNEY_STANDARDS` — all 10 named stages, honestly **8/10 REAL** against `customer_pipeline.py`'s real `STAGE_ORDER`; `complaint_handling` and `refund_requests` are `FUTURE_INSTRUMENTATION`, disclosed, not fabricated.
- `TRUST_PRINCIPLES` — all 5 named checks, **5/5 REAL**: 4 delegate verbatim to already-real `executive_quality_gate.py` checks + `inspectors.py`'s `market_realism`; the 5th (`no_fake_urgency`) cites the one new function this round added.
- `validate_customer_facing_text(text)` — **the real Brand Consistency Engine.** Runs the 4 relevant Trust Framework content checks against arbitrary text. This is the actual "every future module automatically inherits it" mechanism — a callable function, not a document.
- `CUSTOMER_MEMORY_ARCHITECTURE` — **honestly `FUTURE_INSTRUMENTATION`.** A real, disclosed 5-principle privacy-first design (opt-in only, commerce-relevant facts only, no cross-session guest tracking, real deletion path required in the same change that ever builds it, reuses `customer_auth.js`'s existing `account_id`) — never built, because zero real customer preference data exists to store yet. Building storage/UI for data that doesn't exist would be exactly the overengineering this directive explicitly forbids.
- `continuous_improvement_sources()` — pure citation of `evolution_queue.py`'s real Observe-stage signals (`funnel_conversion_summary()`, `delivery_delay_summary()`, `channels/ledger.py::revenue_trend()`) — no second, competing learning loop.
- `brand_dna_report()` — the one real aggregator.

**`executive_quality_gate.py`** gained `check_fake_urgency_risk()` (+ `FAKE_URGENCY_RISK_PHRASES`), registered in `REJECT_IF_FAIL` and `_run_all_checks()` — the exact same real, deterministic, non-exhaustive phrase-scan discipline as `check_brand_reputation_risk()`/`check_content_neutrality_risk()`/`check_copyright_trademark_risk()`. Deliberately distinct from `profit_oracle.py::_score_urgency()`, which scores *real customer-pain-evidence* urgency (a market-research signal) — this checks the opposite direction: fabricated urgency in outbound copy.

**`server.js`** — `COMPANY_PERSONALITY_PREAMBLE`, a real Arabic constant sourced from `brand_dna.py::COMPANY_PERSONALITY`, injected at **all 3 real call sites** an `AGENT_PROMPTS` system prompt passes through (found by direct search, not assumed to be one): the `/api/agent/:name` route, `generatePublisherSEO()`'s reuse of `AGENT_PROMPTS.publisher.system`, and the real Scout pipeline's reuse of `AGENT_PROMPTS.scout.system`. A future 7th agent or call site inherits the personality automatically the moment it references `AGENT_PROMPTS`, without a checklist to remember.

## Customer Experience Architecture

The real, current customer journey, end to end, per `customer_pipeline.py::STAGE_ORDER`:

`NEW → QUALIFIED → PROPOSED → APPROVED → AWAITING_PAYMENT → PAID → PRODUCTION → QUALITY_INSPECTION → PACKAGING → DELIVERED → FOLLOWED_UP`

Every stage reuses an already-real engine (the same evidence gate every internal opportunity goes through, the same Dual Inspection every internal product passes) — never a separate "customer track." Two real gaps sit outside this flow entirely: Complaint Handling and Refund Requests have no real stage at all today.

## Brand DNA Document

= `brand_dna.py::COMPANY_PERSONALITY` + `COMMUNICATION_STANDARDS` (above) — the real, callable definition, not a static prose file that drifts from the code.

## Customer Interaction Standards

= `brand_dna.py::CUSTOMER_JOURNEY_STANDARDS` (above) — 8/10 real, 2 disclosed gaps.

## Trust Principles

= `brand_dna.py::TRUST_PRINCIPLES` (above) — 5/5 real, enforced via `validate_customer_facing_text()` and `executive_quality_gate.py`'s `REJECT_IF_FAIL` pipeline.

## Implementation Roadmap

1. **Done this round:** shared personality preamble live at all 3 real agent call sites; `check_fake_urgency_risk()` live and REJECT_IF_FAIL-gated; `validate_customer_facing_text()` callable by any future module.
2. **Next, when real customer volume justifies it (not before):** a real Complaint Handling stage in `customer_pipeline.py`'s `STAGE_ORDER`, modeled on the existing stage-transition pattern.
3. **Next, same trigger:** a real Refund Request stage, likely reusing `invoice_generator.py`'s existing real invoice records as the join key.
4. **When the first real customer preference exists to store:** build `CUSTOMER_MEMORY_ARCHITECTURE`'s 5 disclosed design principles into real code — not before, per this directive's own "do not overengineer" rule.
5. **Open, disclosed gap, not yet scheduled:** an explicit AI-authorship disclosure on customer-facing pages (the one partially-met personality trait) — a real product/legal decision, not purely an engineering one.

## Rules honored literally

No fake data, no invented feedback, no imaginary metrics — every field in `brand_dna.py` either cites a real signal or is explicitly tagged `FUTURE_INSTRUMENTATION`. Customer Memory is architecture only, disclosed as unbuilt, exactly per the directive's own instruction. No overengineering — one module, one new check function, one preamble constant, zero new parallel systems.

## Validation

`python -m unittest tests.test_brand_dna -v` — 14/14 passing. `python -m unittest tests.test_executive_quality_gate -v` — 52/52 passing (including the new `TestFakeUrgencyRisk`). `node tests/test_brand_dna_preamble_consistency.js` — 3/3 passing, a real drift guard cross-checking server.js's hand-authored Arabic preamble against brand_dna.py's actual trait keys via a real (offline, one-time) Python subprocess call, not a live runtime dependency. Live-verified: `GET /api/v1/brand-dna-report` end-to-end via a disposable server; `POST /api/agent/scout` confirmed the preamble-injected prompt still produces a real, successful Groq response (HTTP 200) with no runtime error across the 3 real call sites (only one hit live to avoid unnecessary real API spend, given all 3 use the identical concatenation pattern in the same module).

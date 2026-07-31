# Truth First Constitution

**Date:** 2026-07-31
**Status:** Adopted — the company's highest law (see `OPENCLAW_OS_CONSTITUTION.md`'s new "TRUTH FIRST" section, immediately after Supreme Law).

---

## The founder's directive (verbatim)

> FOUNDER DIRECTIVE — TRUTH FIRST CONSTITUTION
>
> This is now the highest law of the company.
>
> The company is forbidden from: inventing data, inventing metrics, inventing customers, inventing revenue, inventing conversions, inventing suppliers, inventing APIs, inventing integrations, inventing products, inventing market validation, inventing research, inventing architecture, inventing completion percentages, inventing confidence values, inventing progress.
>
> If information does not exist, the system must explicitly say: NOT BUILT, NOT IMPLEMENTED, NOT CONNECTED, NOT MEASURED, UNKNOWN, WAITING FOR REAL DATA, SIMULATION, REFERENCE IMPLEMENTATION, PLANNED.
>
> Never replace missing facts with optimistic assumptions. Never hide weaknesses. Never manipulate dashboards. Never fake green status. Never claim success before verification.
>
> Every number displayed anywhere must have a traceable source. Every recommendation must reference its evidence. Every KPI must expose: source, timestamp, confidence, verification state. Every business decision must be reproducible. Every architectural decision must be documented.
>
> Every simulation must always be clearly labeled SIMULATION. Simulation data must never mix with production data. Production data must never be modified by simulations.
>
> Every public output must pass a Legal Safety Review. Before publishing anything externally the system must verify: no false claims, no misleading statistics, no fabricated testimonials, no fake reviews, no fake partnerships, no copyright violation, no trademark misuse, no privacy violation.
>
> When uncertainty exists: say "I don't know." When evidence is missing: say "Not verified." When implementation does not exist: say "Not implemented."
>
> The company's reputation is worth more than short-term revenue. Trust is treated as a permanent company asset.
>
> Every subsystem must continuously audit itself for: mistakes, inconsistencies, duplicated logic, technical debt, legal risks, security risks, customer risks.
>
> Every improvement must make the company more honest, more transparent, more maintainable, more secure, more explainable, more reliable.
>
> The company is not optimized for looking impressive. The company is optimized for surviving decades.

## Why this is a governance-ratification round, not a feature build

Unlike every other directive this session, this one carries no "Build the Enterprise X System" framing and no numbered Objectives — it is a declaration of permanent law. Research before writing any code confirmed something worth recording honestly: **this factory has already been practicing this discipline in substance, all session, under a different name.** Every ADR since at least ADR-052 has followed "never fabricate a missing fact, disclose the gap honestly instead" — `NOT_ARCHITECTED`, `WAITING_FOR_REAL_SOURCE`, `NOT ENOUGH EVIDENCE`, `DISCOVERY`, `Unknown` are all real, load-bearing instances of exactly this principle, just under inconsistent vocabulary. This round's real, honest job is threefold: (1) ratify the principle as this company's highest law, in the correct place in the governance hierarchy; (2) canonicalize the vocabulary going forward; (3) close the small number of genuinely new, genuinely missing pieces — never retrofit hundreds of already-truthful existing call sites for a purely cosmetic rename.

## Real audit: vocabulary already in use

A repo-wide mechanical census (`truth_first.py::vocabulary_census()`, callable and re-runnable, not just a one-time grep) found **350 real instances** of an honest-disclosure string across 9 different variants, live as of this ADR:

| Existing variant | Count (live, `vocabulary_census()`) | Canonical replacement, going forward |
|---|---:|---|
| `"DISCOVERY"` | 190 | `PLANNED` or `NOT CONNECTED` depending on context (structural/data-source absence vs. a named future capability) |
| `NOT ENOUGH EVIDENCE` | 53 | `WAITING FOR REAL DATA` |
| `NOT_ARCHITECTED` | 46 | `NOT BUILT` |
| `NOT YET BUILT` | 24 | `NOT BUILT` |
| `NOT_ENOUGH_DATA` | 13 | `WAITING FOR REAL DATA` |
| `WAITING_FOR_REAL_SOURCE` | 11 | `WAITING FOR REAL DATA` |
| `no_real_source` | 6 | `NOT CONNECTED` |
| `not_computed` | 4 | `NOT MEASURED` |
| `WAITING FOR REAL SOURCE` | 3 | `WAITING FOR REAL DATA` |

These counts are a live snapshot (350 total, 354 `*.py` files scanned) — re-run `truth_first.vocabulary_census()` for the current real number; this table will drift as the codebase grows and is not re-synced automatically.

**This is a real, disclosed finding, not a criticism to silently fix**: every one of these 350 instances is already honest — none of them fabricates a fact. Rewriting all 350 call sites across dozens of files spanning ADR-052 through ADR-159 for a purely cosmetic vocabulary change would be a large, high-blast-radius change with zero functional benefit, directly contradicting this factory's own standing "reuse, don't duplicate, don't rewrite what already works" discipline. **Decision: the canonical 9-term vocabulary (`truth_first.CANONICAL_VOCABULARY`) governs all new code from this ADR forward; existing call sites are grandfathered, not rewritten.**

`SIMULATION` and `REFERENCE IMPLEMENTATION` are the two canonical terms with no direct prior variant — `SIMULATION` is already real and consistently applied via `simulation_mode.py`'s `SIMULATION_TAG` (ADR-153); `REFERENCE IMPLEMENTATION` has no prior real usage anywhere in this factory and is reserved for a future case where a real, working example exists but isn't wired into the live pipeline (e.g., `seed_english_book.py`'s own documented "standalone, safe to run/delete" status — a real precedent for the *concept*, just never labeled with this exact word before).

## Real audit: KPI provenance (source / timestamp / confidence / verification state)

Most of this session's real functions already return a `{answer, source, reason}`-shaped dict — `source` and an implicit verification-state signal (present vs. `NOT_ARCHITECTED`) are already near-universal. `timestamp` is real and present at the aggregator level (`generated_at` on nearly every dashboard function) but not per-field. `confidence` as a distinct, separate field is genuinely inconsistent — some functions have it (`opportunity_pipeline.py`'s real recorded `confidence`, `strategic_intelligence_core.py`'s `components_basis` real/estimated tagging), most do not. **This is a real, disclosed gap** — not retrofitted this round (same proportionality reasoning as the vocabulary census above); new functions built from this ADR forward should include all 4 fields where a real confidence/verification signal exists, honestly omitting `confidence` (never fabricating a number) where none does.

## Real audit: Legal Safety Review

`executive_quality_gate.py::REJECT_IF_FAIL` = `customer_pain_evidence`, `legal_compliance_risk`, `brand_reputation_risk`, `market_saturation_competitor_quality`, `content_neutrality_risk` — a real, already-enforced hard-reject pipeline every real opportunity/product passes through. Coverage against this directive's 8 named checks, audited honestly:

- **No false claims / no misleading statistics** — partially covered by `check_brand_reputation_risk()` (fabricated-infrastructure claims, a real 2026-07-22 incident) and `check_data_confidence_score()`; not a general statistical-accuracy checker (none exists, none is claimed to exist).
- **No fabricated testimonials / no fake reviews** — **already satisfied architecturally, not by a content scan**: `customer_pipeline.py::submit_review()` requires a real `request_id` tied to a real customer request — there is no code path anywhere in this factory that can generate a review without one. Adding a phrase-list scan for "fake testimonial" text would be redundant duplicated logic layered on top of an already-effective real control — not built, disclosed as already-satisfied-differently.
- **No fake partnerships** — no real control exists specifically for this; genuinely open, disclosed here rather than silently assumed covered.
- **No copyright violation / no trademark misuse** — **the one genuine, previously-undisclosed gap**, confirmed by direct search: no check anywhere scans for claimed affiliation with a real named brand or reuse of a registered product name. Closed this round: `check_copyright_trademark_risk()` (new, `executive_quality_gate.py`), same real, deterministic, non-exhaustive phrase-list-scan discipline as `check_content_neutrality_risk()`/`check_brand_reputation_risk()` — honestly `UNKNOWN` when no content is supplied, never a false `PASS`.
- **No privacy violation** — covered by `check_content_neutrality_risk()`'s existing privacy-violation phrase category (ADR-135).

## Real mechanism

`truth_first.py` (new): `CANONICAL_VOCABULARY` (the 9 terms + precise definitions), `vocabulary_census()` (the real, re-runnable scan behind the table above), `truth_first_compliance_report()` (the one real aggregator — census + `simulation_mode.py`'s real separation guarantee + `REJECT_IF_FAIL`'s real coverage list + this ADR's 3 existing self-audit-subsystem citations, `resilience_monitor.py`/`ai_doctor.py`/`self_awareness.js`). Read-only and informational — it is a meta-report about the existing hard-reject pipeline's own coverage, never a second gate layered on top of it. Mission Control: `truth-first-compliance` (`SERVICE_REGISTRY`, no-input, cheap — a local file scan, no full-portfolio computation).

## What this principle does not claim

`vocabulary_census()` is a string census, not a semantic auditor — it cannot detect a fabrication that doesn't use one of the known honest-disclosure strings, the same honest limitation every phrase-list check in `executive_quality_gate.py` already discloses about itself. `check_copyright_trademark_risk()` is non-exhaustive and not a substitute for real legal review, same as its 3 siblings. `truth_first_compliance_report()` does not retroactively verify every one of this factory's ~350 existing honest-disclosure instances individually — it counts them by known variant and cites where the underlying discipline is enforced; a genuinely fabricated claim using novel wording would not be caught by this audit today.

# ADR-160 — Truth First Constitution

**Date:** 2026-07-31
**Status:** Adopted. The company's highest law — ratified into `OPENCLAW_OS_CONSTITUTION.md`, fully detailed in `OpenClaw_Brain/00_Governance/TRUTH_FIRST_CONSTITUTION.md`. A governance-ratification round: one new module (`truth_first.py`), one new Legal Safety Review check, zero retrofit of existing honest-disclosure code.

---

## The directive (verbatim)

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

## Why this round is governance, not a feature build

Unlike every other directive this session, this one carries no "Build the Enterprise X System" framing and no numbered Objectives — it is a declaration of permanent law. See `OpenClaw_Brain/00_Governance/TRUTH_FIRST_CONSTITUTION.md` for the full research, but the headline finding: **this factory has already been practicing this exact discipline in substance, all session, under inconsistent vocabulary.** A real, mechanical, re-runnable census (`truth_first.py::vocabulary_census()`) found ~350 real honest-disclosure instances across 9 pre-existing variants (`DISCOVERY`, `NOT ENOUGH EVIDENCE`, `NOT_ARCHITECTED`, `NOT YET BUILT`, `NOT_ENOUGH_DATA`, `WAITING_FOR_REAL_SOURCE`, `no_real_source`, `not_computed`, `WAITING FOR REAL SOURCE`) — every one of them already honest, none fabricating a fact. Retrofitting all of them for a purely cosmetic vocabulary rename would be large, high-blast-radius, and of zero functional benefit — directly against this session's own standing "reuse, don't rewrite what already works" discipline. **Decision: `truth_first.CANONICAL_VOCABULARY`'s 9 named terms govern all new code from this ADR forward; existing call sites are grandfathered.**

## What was built

- **`OPENCLAW_OS_CONSTITUTION.md`** (supreme law, amended): new "TRUTH FIRST" section immediately after "SUPREME LAW" — the founder's own "highest law" framing placed correctly in the existing governance hierarchy rather than a second, competing supreme document. Gained an amendment-history table (it had none before).
- **`OpenClaw_Brain/00_Governance/TRUTH_FIRST_CONSTITUTION.md`** (new, matches `EXECUTIVE_SAFETY_PRINCIPLES.md`'s exact precedent format): the full directive, the vocabulary-census finding + canonical-term mapping table, a real audit of KPI provenance (source/timestamp near-universal already; `confidence` as a distinct field is a real, disclosed, not-retrofitted gap), and a real, honest, per-item audit of Legal Safety Review coverage against all 8 named checks — some real (privacy via `check_content_neutrality_risk()`), some already satisfied architecturally rather than by a content scan (fake reviews/testimonials: `customer_pipeline.py::submit_review()`'s real `request_id` requirement — no fabrication path exists, confirmed, matching this factory's own prior Global Trust & Resilience Layer finding), one genuine gap found and closed (copyright/trademark).
- **`truth_first.py`** (new, root): `CANONICAL_VOCABULARY` (9 terms + definitions), `vocabulary_census(root_dir=None)` (the real, callable, re-runnable scan behind the finding above — a string census, not a semantic auditor, same disclosed limitation as every phrase-list check in `executive_quality_gate.py`), `truth_first_compliance_report(census=None)` (the one real aggregator — census + real citations of `simulation_mode.py`'s production/simulation separation, `executive_quality_gate.py::REJECT_IF_FAIL`'s real coverage, and the 3 existing self-audit subsystems; never a fabricated numeric compliance score).
- **`executive_quality_gate.py`** (extended): `check_copyright_trademark_risk()` (new, added to `REJECT_IF_FAIL` — the one genuine Legal Safety Review gap direct search found: no prior check scanned for claimed affiliation with a real named brand or reuse of a registered product name). Deliberately did **not** add a fake-testimonial/fake-review phrase scan — the real, effective control is architectural (`submit_review()`'s real `request_id` requirement), and a second phrase-list check on top of it would be duplicated logic for zero real benefit.
- **Mission Control**: `truth-first-compliance` (`SERVICE_REGISTRY`, no-input, cheap — a local file scan, no full-portfolio computation) + one panel in the existing Executive Overview group.
- **`CONSTITUTION.md`**: amendment-history line noting this round's addition to the supreme document above it, per its own stated hierarchy.

## What is explicitly NOT done this round

No retrofit of the ~350 already-honest existing disclosure strings across dozens of files spanning ADR-052 through ADR-159. No new fake-testimonial/fake-review phrase scan (the real control is architectural, already exists). No KPI-provenance retrofit across every existing function (a real, disclosed gap — new functions built from this ADR forward should adopt the full source/timestamp/confidence/verification-state shape where a real signal exists for each). No second self-audit dashboard — `truth_first_compliance_report()` cites the 3 existing subsystems rather than duplicating them.

## Validation

`python -m unittest tests.test_truth_first -v` — 13/13 passing: the canonical vocabulary has all 9 named terms with real definitions; the census finds real non-zero counts for the 3 most common known variants (regression-proofing this ADR's own finding) and correctly scopes to zero on an isolated empty fixture; the compliance report cites real sources for every field and never emits a fabricated numeric score; `check_copyright_trademark_risk()` follows the exact same honest `_unknown`/`_real` shape as its siblings and is confirmed registered in `REJECT_IF_FAIL`. `tests.test_executive_quality_gate` (47 tests, pre-existing) re-run clean — the new check is additive, no existing test hardcoded `REJECT_IF_FAIL`'s length. Live-verified: `truth_first.vocabulary_census()` against the real repository returned 350 real instances across 354 real `*.py` files scanned — the governance documents were corrected to cite this live, traceable number rather than an earlier informal estimate, itself a small real demonstration of this ADR's own "every number must have a traceable source" requirement.

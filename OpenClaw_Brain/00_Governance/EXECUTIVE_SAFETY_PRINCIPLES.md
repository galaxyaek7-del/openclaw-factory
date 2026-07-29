# Executive Safety Principles

**Date:** 2026-07-29
**Status:** Adopted — permanent policy, not a phase-specific rule.

---

## The founder's directive (verbatim)

From "GALAXY FORGE — EXECUTIVE DIRECTIVE — Phase: Global Commercial Hardening" (2026-07-29), Priority 3:

> Galaxy Forge must never evolve toward:
>
> - Political activity
> - Religious discussions
> - Ethnic classification
> - Sensitive personal profiling
> - Illegal content
> - Hate content
> - Manipulation
> - Privacy violations
> - Government interference
>
> The company must remain globally neutral. Its mission is solving customer problems professionally.

## Why this is a permanent record, not just a code comment

Every other hard-reject criterion in `executive_quality_gate.py::REJECT_IF_FAIL` traces back to a real incident or an explicit founder directive with its own citable record (`check_brand_reputation_risk()` → the 2026-07-22 fabricated-hosted-software bug; `check_legal_compliance_risk()` → `QUARANTINE.md`/`REJECTED_NICHES.md`). This principle is the same kind of standing constraint — a permanent boundary on what this company will ever become, independent of any single product or opportunity — and deserves the same permanent, citable home rather than living only inside one function's docstring.

## Real mechanism

`executive_quality_gate.py::check_content_neutrality_risk()` — added to `REJECT_IF_FAIL`, so a real match hard-rejects an opportunity outright, exactly like `check_brand_reputation_risk()`/`check_legal_compliance_risk()`. Same honest discipline as every other check in that module:

- A real, deterministic phrase-list scan (`CONTENT_NEUTRALITY_RISK_PHRASES`) over `product_chapters` content — not exhaustive, not a substitute for human judgment, but a real, cheap, automatable first pass.
- Honestly `UNKNOWN` (never a silent `PASS`) when no content is supplied to check.
- Covers all nine named categories with representative real phrase markers: political activity, religious discussions/proselytizing, ethnic classification, sensitive personal profiling, illegal content, hate content, manipulation, privacy violations, and government interference.

This is not a new gate system — it is one more named criterion inside the same `executive_quality_gate.py`/`enterprise_readiness.py` hard-reject pipeline every real opportunity and product already passes through, following this factory's own standing "wrap, don't rewrite" discipline.

## What this principle does not claim

A phrase-list scan cannot catch every real violation, and does not replace human judgment on genuinely ambiguous content. It exists to catch the clear, unambiguous cases automatically and cheaply — the same honest limitation `check_brand_reputation_risk()` already discloses about itself. If this factory's product surface ever expands to something where this check's coverage meaningfully matters more (e.g. user-generated or highly variable AI content at scale), the phrase list should be revisited then, grounded in real content actually seen — never expanded speculatively ahead of real evidence.

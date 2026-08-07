# Galaxy Forge — Company Standards

**Status:** Permanent, part of the Company DNA. Where the first three Phase 11 documents govern how the company *decides*, this one governs what the company *ships and says* — the customer- and product-facing standards the 14 Operating Principles translate into. Every standard below cites the real, callable check that enforces it; where none exists, the gap is named rather than smoothed over (Principle 1, applied to this document itself).

## Product Standards (Principles 3, 4)

- **A product ships only after Dual Inspection passes.** `inspectors.py::inspect_technical()`/`audit_commercial()`, real per-product checks, not a formality — `QUARANTINE.md`'s 3,337+ real historical rejections are this standard actually being enforced, not a theoretical gate.
- **A product's price must be justified by its real content depth**, not an arbitrary anchor. `economics.py::market_realism_check()` — the real check that once correctly repriced the EU AI Act Compliance Toolkit from $349 to $310 based on actual page count, before any customer ever saw it.
- **A product's readiness is a real, disclosed number**, never a vibe. `product_readiness_score.py::compute_product_readiness_score()` — averages only the dimensions with a real computed value that call (Technical/Commercial/Strategic); never force-averages in a missing signal as a stand-in.
- **The company would buy its own product.** `trust_audit.py`'s literal citation of this standard against real evidence, not self-assessment.

## Customer-Facing Standards (Principles 1, 2)

- **No fabricated reviews, ever — architecturally, not by policy.** `customer_pipeline.py::submit_review()` requires a real `request_id` tied to a real transaction; there is no code path that can produce a review with no underlying purchase.
- **No fake urgency or manipulative scarcity.** `brand_dna.py::check_fake_urgency_risk()`, `REJECT_IF_FAIL`-gated in `executive_quality_gate.py` — a real, deterministic phrase-scan, not a style guideline.
- **No misleading pricing, no deceptive wording, promises match reality.** `brand_dna.py::TRUST_PRINCIPLES` (5 named checks), `validate_customer_facing_text()` — the real, callable Brand Consistency Engine every generated customer-facing text is run through, not a document anyone has to remember to consult.
- **Hidden limitations must be disclosed, not buried.** The real, disclosed regulatory-currency catch on the EU AI Act toolkit (2026-08-07) — a material 16-month deferral in the product's core premise, found and corrected before the product was ever offered for sale — is this standard's own working proof, not a hypothetical.

## Commercial Standards (Principles 3, 7, 10, 11)

- **No niche is accepted without real, human-cited Proof of Payment evidence.** `profit_oracle.py::ladder_opportunity_score()`'s hard gate (ADR-121) — the reason 0 of 91 real evaluated niches were accepted as of the most recent Gap Analysis, an honest outcome of a real standard, not a broken pipeline.
- **A product is never tied to one platform's survival.** `channels/base_arm.py`'s `BaseArm` contract — real arms exist for Gumroad/Etsy/Payhip/Paddle today; a platform closing stops only its own channel (Principle 10, `channels/registry.py`).
- **Commercial monitoring never stops for one platform's failure.** `channels/publish_protection.py`'s per-arm circuit breaker + `safe_mode.py`'s per-subsystem independent flags (Principle 11).

## Evidence & Traceability Standards (Principles 5, 6, 12)

- **Every real product, decision, and publish attempt is traceable to a real ledger entry.** `evidence_engine.py`'s 10 named types (ADR-163); the one disclosed gap (`CUSTOMER` has no dedicated append-only ledger yet) is named in `EXECUTABLE_PRINCIPLES.md`, not hidden here.
- **A mistake, once made and understood, is written down permanently.** `OpenClaw_Brain/19_Lessons_Learned/` — real, dated files (`The_Nested_Evidence_Shape_Bug.md`, `The_Disclaimer_That_Never_Rendered.md`, etc.), mechanically picked up by `knowledge_graph/build.py::_lesson_nodes()`, never re-typed from memory.

## Standards this document deliberately does not invent

No numeric SLA (e.g. "99.9% uptime," "24-hour response time") appears above — this factory has no real historical data to justify one yet (the same honest-gap discipline `growth_stages.py`'s cash-reserve/revenue thresholds already established as `NOT_ARCHITECTED`). A standard is listed here only when a real, callable check already enforces it.

---

*See also: `OPERATING_PRINCIPLES.md`, `EXECUTABLE_PRINCIPLES.md`, `DECISION_LAWS.md`, `AUTONOMOUS_RULEBOOK.md`, `brand_dna.py` (the fuller Brand DNA source these standards summarize).*

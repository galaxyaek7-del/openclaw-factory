# OpenClaw Factory — Engineering Constitution

> Treat OpenClaw as an enterprise-grade digital factory, not a collection of scripts.

**Supreme law:** this document operates under, and must never contradict, [`OPENCLAW_OS_CONSTITUTION.md`](./OPENCLAW_OS_CONSTITUTION.md) — the company's foundational mission, DNA, Councils, and Supreme Law ("System Before Individuals"). Where the two ever appear to conflict, `OPENCLAW_OS_CONSTITUTION.md` wins. This document is the *engineering-specific* implementation standard: it translates that supreme law into concrete code-level principles for this repository. Any task, fix, or feature must be evaluated against both — the 17 principles below, and the supreme law above them.

---

## 1. Stability First
- Never break existing working features.
- Every new feature must be isolated.
- Preserve backward compatibility.

## 2. Modular Architecture
- Every module has one responsibility.
- Loose coupling.
- High cohesion.
- No circular dependencies.

## 3. Fault Tolerance
- Every external service (Groq, OpenAI, APIs...) must have:
  - timeout
  - retry
  - fallback
  - graceful degradation
- The factory never crashes because one provider fails.

## 4. Security
- No secrets in source code.
- Secrets only in `.env`.
- Validate every input.
- Sanitize filenames.
- Prevent path traversal.
- Escape dangerous characters.
- Use least-privilege permissions.

## 5. Factory Memory
- Every production generates metadata.
- Log every error.
- Log every successful publication.
- Build reusable knowledge instead of repeating work.

## 6. Production Pipeline
```
Idea
  ↓
Research
  ↓
Generate
  ↓
Quality Check
  ↓
Review
  ↓
Package
  ↓
Publish
  ↓
Analytics
```
No stage may bypass quality validation.

## 7. Self-Healing
If one module fails:
- continue production where possible
- report the failure
- never terminate the whole factory

## 8. Plugin Architecture
Every production line must be installable/removable independently.

Examples: KDP, Etsy, Printables, Wall Art, Courses, Templates, Prompt Packs.

## 9. Reusable Assets
Never regenerate assets that already exist. Cache everything reusable.

## 10. Configuration Driven
Business rules belong in configuration files. Avoid hard-coded values.

## 11. Scalability
The architecture must support 1 product/day, 10 products/day, and 1000 products/day — without redesign.

## 12. Testing
Every module must include:
- unit tests
- integration tests
- regression tests

## 13. Observability
Every important action must be logged. Every failure must include a useful error message.

## 14. AI Independence
AI providers are interchangeable. The factory should support multiple providers through one unified interface.

## 15. Human Override
The Executive Director can override any automated decision.

## 16. The Butter Principle (Profit-First)
No product is built on hope. Before any product is made, its profit potential must be scored — demand, competition, margin, execution fit — never skipped, never assumed. A digital product priced at $30 or more, at near-zero production cost, is "butter": high margin, low risk, worth making. A score of 80+ ("GOLDEN") still requires the Executive Director's ("Galaxy's") approval before production — profit-first does not mean approval-free. Implemented in `profit_oracle.py`.

## 17. Dual Inspection
No product ships without both guardians' approval. Every generated product passes through two independent inspectors before it may publish: a **Technical Inspector** (cover, PDF integrity, Arabic rendering, no placeholder leftovers) and a **Commercial Auditor** (profit score, Butter-principle price, no duplicates, no previously-rejected niches). Either failing blocks publication and logs the reason to `QUARANTINE.md`; a critical technical failure alerts the Executive Director immediately. One bad product across KDP/Etsy/Gumroad is a disaster, not a minor bug — zero tolerance. Implemented in `inspectors.py`, called automatically at the end of every `generate_book()`.

**Quality Council.** This *is* this repository's concrete instantiation of `OPENCLAW_OS_CONSTITUTION.md`'s **Quality** Council and its mandate — *"Nothing reaches production without passing all quality gates."* The Technical Inspector and Commercial Auditor are that Council's two standing gates for the book_engine product line; any future product line (template_engine, art_engine, ...) must stand up its own equivalent pair before it may publish, per the same supreme law.

**Anti-Fragility.** Per `OPENCLAW_OS_CONSTITUTION.md`'s Anti-Fragility principle — *"every failure becomes knowledge"* — a rejected product is never just discarded. `QUARANTINE.md` and `inspections.log` are that knowledge made durable: every blocked niche, every failure reason, and every critical alert stays on record so the same mistake is recognizable (`audit_commercial`'s "niche not previously rejected" check reads this history back in) instead of being repeated blindly.

---

## Architecture: Sensing ↔ Brain

n8n is the Sensing layer. server.js is the Brain. They communicate only via HTTP POST `/api/trends`.

n8n owns discovery (Google Trends, future data sources) and knows nothing about book generation, quality gates, or opportunity tracking — it just detects a trend and POSTs it. server.js owns judgment (`quality_gate()`) and memory (`OPPORTUNITIES.md`) — it never reaches into n8n's workflow internals. Neither side depends on the other's implementation details, only on this one HTTP contract (Constitution §2: loose coupling).

---

## Cover Design: The 70/20/10 Rule

Every generated book cover follows a fixed visual hierarchy, top to bottom:

- **70% — Title.** The single dominant element. Largest text on the cover, placed at the top, bold enough to stay readable at a 100px thumbnail.
- **20% — Visual/graphic element.** A supporting accent (image, icon, pattern) in the middle — present, but never competing with the title for attention.
- **10% — Author name.** Smallest text on the cover, placed at the bottom. Must always render smaller than the title — a cover generator that lets the author name rival the title has inverted its own hierarchy and should refuse to save.

One dominant color per niche/genre; high contrast between text and background. Implemented in `cover_designer_v2.py`.

---

## Mission

Build the most reliable, scalable, secure and self-improving digital product factory possible. Optimize for long-term maintainability, resilience and automation rather than short-term speed.

---

## Amendment history

| Date | Change |
|---|---|
| 2026-07-05 | Constitution established and adopted as the governing standard for all work in this repository. |
| 2026-07-05 | Added "Architecture: Sensing ↔ Brain" — codifies the n8n ↔ server.js contract established by `/api/trends` (Task [11]). |
| 2026-07-06 | Added "Cover Design: The 70/20/10 Rule" — this rule was referenced as already being in this document by the task that built `cover_designer_v2.py` but did not actually exist here yet; added now so that reference is accurate going forward. |
| 2026-07-06 | Added "16. The Butter Principle (Profit-First)" — same situation: referenced by the task that built `profit_oracle.py` as an existing numbered principle, but this document only had 15 before now. |
| 2026-07-06 | Added "17. Dual Inspection" — the task that built `inspectors.py` asked for it as "Principle 23", but this document only had 16 principles at the time (17 through 22 don't exist), so it was added as the actual next number, 17, instead of leaving an unexplained gap. |
| 2026-07-08 | Installed `OPENCLAW_OS_CONSTITUTION.md` as the supreme governing law above this document; added explicit Quality Council + Anti-Fragility references to "17. Dual Inspection", tying `inspectors.py`/`QUARANTINE.md`/`inspections.log` to their source principles in the supreme constitution. |

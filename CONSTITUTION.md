# OpenClaw Factory — Engineering Constitution

> Treat OpenClaw as an enterprise-grade digital factory, not a collection of scripts.

This document is the highest-authority engineering standard for this repository. Any task, fix, or feature must be evaluated against these 15 principles before and after implementation.

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

---

## Architecture: Sensing ↔ Brain

n8n is the Sensing layer. server.js is the Brain. They communicate only via HTTP POST `/api/trends`.

n8n owns discovery (Google Trends, future data sources) and knows nothing about book generation, quality gates, or opportunity tracking — it just detects a trend and POSTs it. server.js owns judgment (`quality_gate()`) and memory (`OPPORTUNITIES.md`) — it never reaches into n8n's workflow internals. Neither side depends on the other's implementation details, only on this one HTTP contract (Constitution §2: loose coupling).

---

## Mission

Build the most reliable, scalable, secure and self-improving digital product factory possible. Optimize for long-term maintainability, resilience and automation rather than short-term speed.

---

## Amendment history

| Date | Change |
|---|---|
| 2026-07-05 | Constitution established and adopted as the governing standard for all work in this repository. |
| 2026-07-05 | Added "Architecture: Sensing ↔ Brain" — codifies the n8n ↔ server.js contract established by `/api/trends` (Task [11]). |

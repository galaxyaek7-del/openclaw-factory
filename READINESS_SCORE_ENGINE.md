# OpenClaw / Galaxy Forge — Readiness Score Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Every product receives Strategic/Technical/Commercial/Customer/Automation/Security/Overall Readiness" checked against `launch_readiness.py` — a real system already named almost exactly this (ADR-153, "Launch Readiness Score") — with one precise, named granularity mismatch disclosed rather than glossed over.

---

## The real granularity mismatch

`launch_readiness.py` scores real **business divisions** (Affiliate Commerce, Digital Products, SaaS, AI Services, Licensing) on 8 real dimensions (architecture/automation/testing/compliance/monitoring/documentation/integration/operational readiness) — each a real, mechanical, disclosed-heuristic check (file existence, real test counts, real text-marker presence). This directive asks for a score **per product**, not per division. Both are real and valuable; neither substitutes for the other.

## The 6 requested scores, mapped

| Requested | Real coverage |
|---|---|
| Strategic Score | `strategic_intelligence_core.strategic_score()` — real, per-niche |
| Technical Score | `reality_audit.py`'s real REAL% (98.8% as of the most recent live audit) + `inspectors.py::inspect_technical()`, per-product |
| Commercial Score | `commercial_readiness.py` (ADR-181, company-wide) + `inspectors.py::audit_commercial()`, per-product |
| Customer Score | **Real, disclosed gap** — no per-product customer-readiness score exists; `trust_audit.py`'s customer-risk section is company-wide, not product-specific |
| Automation Score | `launch_readiness.py`'s real `automation` dimension — division-level only |
| Security Score | `resilience_monitor.py`'s real findings, company-wide; no per-product security score exists |
| Overall Readiness | **Not computed anywhere as one number today** — the 6 sub-scores above live in at least 4 different real modules, at 2 different granularities, never synthesized |

**3 of 6 have real, product-level coverage. 3 are real but company-wide or division-level only, not per-product.**

## Why "Overall Readiness" isn't fabricated here

Averaging scores from different granularities (a per-niche strategic score, a company-wide security finding, a per-division automation score) into one number would produce something that looks precise and means very little — the exact failure mode `commercial_readiness.py`'s own design already avoids by excluding uncomputed dimensions rather than treating them as zero. This document names the real gap instead: a genuine per-product Overall Readiness score is real, buildable future work (thread the 3 already-per-product scores through, honestly exclude the 3 that aren't), not something to compute today by force-averaging incompatible real numbers.

## What a real per-product readiness score would look like right now

For the one real product that exists — the EU AI Act Compliance Toolkit — the 3 real, per-product-computable scores: Technical (real, passed Dual Inspection), Commercial (real, `$155` cleared the market-realism floor after correction), Strategic (real, `strategic_intelligence_core.strategic_score()` citable). Customer, Automation, and Security stay honestly at the company-wide/division level for this product specifically, same as every other product would today.

---

*See also: `GLOBAL_LAUNCH_PROTOCOL.md`, `LAUNCH_CHECKLIST.md`, `EVOLUTION_SCORE.md` (the same historical-trend gap discipline applied here).*

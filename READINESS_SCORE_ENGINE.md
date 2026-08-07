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

## Why "Overall Readiness" wasn't fabricated when this document was first written

Averaging scores from different granularities (a per-niche strategic score, a company-wide security finding, a per-division automation score) into one number would produce something that looks precise and means very little — the exact failure mode `commercial_readiness.py`'s own design already avoids by excluding uncomputed dimensions rather than treating them as zero.

## Built (ADR-199, same session): `product_readiness_score.py`

The gap above is now closed for the real, per-product-computable dimensions. `product_readiness_score.py::compute_product_readiness_score()` threads `inspectors.py::inspect_technical()`/`audit_commercial()` and `strategic_intelligence_core.strategic_score()` through exactly once, averaging only the dimensions with a real numeric value that call — never force-averaging in Customer/Automation/Security, which stay honestly excluded (`not_scored`, with the same reasons named above). Mission Control: `eu-ai-act-readiness-score`.

**Live for the one real product:** Technical 100/100 (9/9 real checks), Commercial 66/100 (the real `profit_score`, reported separately from 2 procedural re-run artifacts — `not_duplicate`/`not_previously_rejected` correctly fire on any re-check of an already-shipped product, and are not a live commercial defect), Strategic honestly `None` (0 of 11 real dimensions have a value — `strategic_score()` only produces real numbers for a niche with a real ACCEPTED decision, and this niche doesn't have one). **Overall Readiness: 83.0/100**, the real average of the 2 dimensions that did compute.

---

*See also: `GLOBAL_LAUNCH_PROTOCOL.md`, `LAUNCH_CHECKLIST.md`, `EVOLUTION_SCORE.md` (the same historical-trend gap discipline applied here).*

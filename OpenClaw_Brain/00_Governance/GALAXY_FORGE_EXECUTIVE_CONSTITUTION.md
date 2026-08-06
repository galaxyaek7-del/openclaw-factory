# Galaxy Forge Executive Constitution

**ADR-177, 2026-08-06.** The permanent operating constitution governing every department, AI agent, workflow, and product in Galaxy Forge.

---

## Why this document exists, and what it is not

Three founder directives arrived in immediate succession, each asking for a "permanent" governance layer from a different angle: **Global Executive Standards** (8 areas: Product Excellence, Customer Trust, Security, Operational Discipline, Financial Discipline, Continuous Innovation, Company Knowledge, Long-Term Value), **Global Dominance Directive** (a company moat framework + a per-project Strategic Impact Score), and **Executive Operating System** (15 named governance domains: Executive Council through Long-Term Company Evolution). All three explicitly instructed: *do not duplicate existing architecture, integrate cleanly.*

Research confirmed this instruction was necessary and correct: every one of the ~23 named sub-areas across the three directives already maps to a real, already-built module or an existing governance document (`CONSTITUTION.md`, `OPENCLAW_OS_CONSTITUTION.md`, `TRUTH_FIRST_CONSTITUTION.md`, `EXECUTIVE_SAFETY_PRINCIPLES.md`, `IDENTITY_ARCHITECTURE.md`). This document does not restate those — it is the **one navigable index** the three directives asked for, organized around the Executive Operating System's 15 domains (the most complete structure of the three), citing the real enforcement mechanism for each. Three genuinely new, narrow pieces were built to close real gaps found during this consolidation: a quarterly Architecture Review cadence, an annual Strategic Review cadence, and a Strategic Impact Score.

This document supersedes no prior constitution — `CONSTITUTION.md` and `TRUTH_FIRST_CONSTITUTION.md` remain the supreme law; this is the operational index beneath them.

---

## The 15 Governance Domains

Each domain: **Responsibilities** · **Decision Authority** · **Required Evidence** · **Mandatory Reports** · **Measurable KPIs** · **Escalation Rules** — every field cites a real, already-existing mechanism, or is honestly disclosed as not yet built.

### 1. Executive Council

- **Responsibilities:** Multiple independent viewpoints on every major decision before implementation.
- **Decision Authority:** Advisory only — never auto-executes.
- **Required Evidence:** Real per-domain citations (Strategic/Market/Production/Customer/Financial/Security/Resilience/Innovation).
- **Mandatory Reports:** `galaxy_council.py::convene_council(niche)` (ADR-138), `council_learning_summary()`.
- **Measurable KPIs:** Real 3-way join (Recommendation → Decision → Outcome), `NOT ENOUGH EVIDENCE` until real triples accumulate — honestly disclosed, never backfilled.
- **Escalation Rules:** Honest disagreement is never forced into a fabricated consensus — `disagreement_detected` reports `SPLIT`.

### 2. Decision Hierarchy

- **Responsibilities:** The single real accept/reject/defer authority for every opportunity.
- **Decision Authority:** `decision_engine/` — the one real gate; nothing enters production without a real ACCEPTED status.
- **Required Evidence:** `evaluation_snapshot` (real per-niche pain/competition/automation/risk/confidence scores).
- **Mandatory Reports:** `executive_decision_memory.py` (ADR-145) — real duplicate detection, conflict detection, `explain_decision()`.
- **Measurable KPIs:** `data/decisions.jsonl` — currently 0 real ACCEPTED, 49 DEFERRED, 17 REJECTED (live, honest).
- **Escalation Rules:** A real, still-open founder decision exists today — whether to re-evaluate the 4 niches the ADR-162 incident downgraded.

### 3. Risk Management

- **Responsibilities:** Real, continuous risk detection across security/financial/operational/legal.
- **Decision Authority:** Detection only — `resilience_monitor.py` never auto-executes a fix.
- **Required Evidence:** `assess_resilience()`'s real 4-tier severity vocabulary (informational/warning/critical/emergency).
- **Mandatory Reports:** `data/incidents.jsonl` — real, deduped incident ledger.
- **Measurable KPIs:** `resilience_score` (real, disclosed heuristic, currently 93/100).
- **Escalation Rules:** Critical/emergency findings fire a real Telegram notification (`newIncidentTelegramReasons()`); every tick, not daily-gated.

### 4. Strategic Planning Cycle

- **Responsibilities:** Rolling roadmap across Today/Week/Month/Quarter/Year.
- **Decision Authority:** Advisory — `strategic_planning.py::rolling_roadmap()` (ADR-159), never a committed date.
- **Required Evidence:** `scheduler.py`'s real 5 buckets + Growth Stage requirements.
- **Mandatory Reports:** Weekly (`export_executive_report`, Sunday-gated), Monthly (`Galaxy Evolution Report`, ADR-173), **Quarterly (Architecture Review, new — see below)**, **Annual (Strategic Review, new — see below)**.
- **Measurable KPIs:** `growth_stages.py`'s real current stage — honestly Stage 0/Bootstrap as of this document.
- **Escalation Rules:** Stage 4/5 permanently blocked by standing founder policy (country diversification, the 4 protected gates) — not a data threshold.

### 5. Product Approval Pipeline

- **Responsibilities:** No product enters production without real evaluation.
- **Decision Authority:** `goos.py` (ADR-171) — advisory citation of the real gate; the real gate remains `decision_engine`'s ACCEPTED status + `profit_oracle.py`'s real 65/100 weighted floor.
- **Required Evidence:** GOOS's real 20-dimension evaluation (10 named by this directive, 10 more from ADR-171's own scope).
- **Mandatory Reports:** `build_opportunity_intelligence_report(niche)` — the real 15-section report.
- **Measurable KPIs:** `goos_score()` — advisory 0-100, `meets_advisory_85_threshold` (informational, never gates).
- **Escalation Rules:** Elevated-risk/new-channel publishing requires real founder approval (`channels/publish_protection.py`, ADR-135) — one of the 4 protected gates.

### 6. Market Intelligence Workflow

- **Responsibilities:** Continuous, honest opportunity discovery.
- **Decision Authority:** `market_domination_engine.py` (ADR-175) — passive discovery only, never triggers new evaluation.
- **Required Evidence:** 8 of 11 real, query-capable global sources (Amazon/Etsy/Gumroad/GitHub/HN/arXiv/public search/Stack Overflow).
- **Mandatory Reports:** `market-domination-dashboard` (Mission Control).
- **Measurable KPIs:** `REGIONAL_COVERAGE` — honestly `NOT_MEASURABLE` for 6 of 8 named regions (standing founder deferral, 2026-07-23).
- **Escalation Rules:** No new real regional data connector may be built before (a) the first real dollar, or (b) a real connector becoming available — reconfirmed 4x this session.

### 7. Capital Allocation Workflow

- **Responsibilities:** Decide where every hour/dollar/API call/engineer/AI model is invested.
- **Decision Authority:** `enterprise_capital_allocation.py` (ADR-165/176) — the engine recommends, the founder decides; capital reallocation is one of the 4 protected gates.
- **Required Evidence:** Real 20-dimension Investment Score citation; forward-revenue projections honestly `NOT_MEASURABLE` (the real `expected_revenue` field is retrospective, never a forecast).
- **Mandatory Reports:** `capital-decisions-report` — real `INVEST NOW`/`BUILD LATER`/`EXPERIMENT`/`REJECT` per niche, with written reasoning.
- **Measurable KPIs:** `portfolio_balance()` — real recurring-vs-one-time split by ladder character.
- **Escalation Rules:** `projects_overfunded()`/`opportunity_cost()` surface real misallocation signals for founder review, never auto-corrected.

### 8. Innovation Workflow

- **Responsibilities:** Weekly self-improvement.
- **Decision Authority:** `evolution_queue.py` (ADR-133/143) — Execute is human-gated always, one of the 4 protected gates, "must not be loosened without asking again."
- **Required Evidence:** Real bottleneck/technical-debt/capability-gap detection (`evolution_engine.py`).
- **Mandatory Reports:** Daily evolution report; **Monthly `Galaxy Evolution Report`** (ADR-173).
- **Measurable KPIs:** `measure_outcome()` — real IMPROVED/DEGRADED/NO_CHANGE, no sooner than 7 real elapsed days.
- **Escalation Rules:** A proposal reaches `AWAITING_FOUNDER_APPROVAL` and stops — no code path approves itself.

### 9. Knowledge Governance

- **Responsibilities:** Nothing important stays only inside AI memory; everything strategic becomes permanent, re-derivable documentation.
- **Decision Authority:** `knowledge_graph/` — real, mechanical, non-semantic parsing, never inferential.
- **Required Evidence:** Real node types (Decision, Outcome, Proposal, ADR, AffiliateEvent, CouncilRecommendation, ExecutiveDirective).
- **Mandatory Reports:** `gfos.py::enterprise_timeline()` — real chronological merge of 6+ real ledgers, "nothing is lost."
- **Measurable KPIs:** Real node/edge counts, honestly sparse where real data is sparse.
- **Escalation Rules:** N/A — read-only, no execution path.

### 10. Security Governance

- **Responsibilities:** Internal/external security, secrets management, access control, audit trails, disaster recovery.
- **Decision Authority:** `executive_quality_gate.py`'s real 7-check `REJECT_IF_FAIL` pipeline (customer-pain evidence, legal, brand-reputation, market-saturation, content-neutrality, copyright/trademark, **fake-urgency** — ADR-170); `safe_mode.py`'s per-subsystem circuit breakers.
- **Required Evidence:** Real, deterministic phrase-scans — never semantic/AI judgment.
- **Mandatory Reports:** `resilience-status`, `resilience-incidents` (Mission Control).
- **Measurable KPIs:** Zero real fabrication path exists for reviews (`submit_review()`'s real `request_id` requirement).
- **Escalation Rules:** **Honestly disclosed, standing gap:** no independent external security audit or penetration test has ever been run against this factory. `IDENTITY_ARCHITECTURE.md` documents the real, conscious single-Google-account risk — not accidental, reviewed before any account-separation proposal.

### 11. Quality Governance

- **Responsibilities:** Every product solves a real expensive problem with measurable customer value and passes strict quality gates.
- **Decision Authority:** `inspectors.py`'s Dual Inspection — the real, load-bearing gate every generated product passes.
- **Required Evidence:** Real technical (PDF integrity, cover 70/20/10) + commercial (profit score, market realism, duplicate/rejection checks) inspection.
- **Mandatory Reports:** `truth_first.py::truth_first_compliance_report()` (ADR-160).
- **Measurable KPIs:** Real vocabulary census (371 grandfathered gap-disclosure instances, 9 canonical terms governing all new code).
- **Escalation Rules:** A product failing Dual Inspection is quarantined (`QUARANTINE.md`), never silently published.

### 12. Revenue Governance

- **Responsibilities:** Real, honest revenue tracking — never fabricated.
- **Decision Authority:** `channels/ledger.py::revenue_trend()` — the one real revenue source of truth.
- **Required Evidence:** `config/reality.json` — the factory's own unfakeable ledger (`published_books`, currently `[]`).
- **Mandatory Reports:** Real per-sale events in `data/sales_ledger.jsonl` — never a publish-attempt miscounted as a sale.
- **Measurable KPIs:** $0 real revenue to date — stated plainly, not softened.
- **Escalation Rules:** MRR/ARR/Cash/Runway tiles remain honest, disclosed gaps (ADR-146) until real revenue exists to populate them — building them earlier was explicitly rejected as premature (ADR-174's Phase 3 sequencing).

### 13. Automation Governance

- **Responsibilities:** Real, bounded, human-started automation — never an unattended daemon.
- **Decision Authority:** `factory_loop.js` — no scheduler exists; a human must start each real run.
- **Required Evidence:** `autonomous_operations_status.py` — real per-activity automatic/human-gated/ambiguous classification.
- **Mandatory Reports:** `engine-registry` (ADR-172) — the real 9-engine map.
- **Measurable KPIs:** `automation_level_pct` (57.1%, real, company-wide) — distinct from automation *utilization*, which is honestly `WAITING FOR REAL SOURCE`.
- **Escalation Rules:** The always-on-daemon question has been asked and declined **7 times** (ADR-107/110/115/142/147/157/168-era) — the most-reconfirmed standing policy in this factory.

### 14. Crisis Management

- **Responsibilities:** Detect, notify, and record — never auto-remediate.
- **Decision Authority:** `resilience_monitor.py::record_incident()` — real, deduped, severity-gated.
- **Required Evidence:** Root cause, prevention rule, detection rule — cited only when real evidence supports each field.
- **Mandatory Reports:** Real Telegram notification for critical/emergency findings.
- **Measurable KPIs:** Real incident open/resolved counts, `data/incidents.jsonl`.
- **Escalation Rules:** `channels/publish_protection.py`'s global emergency stop — founder-only to trigger or clear.

### 15. Long-Term Company Evolution

- **Responsibilities:** The company must become stronger every real cycle, never optimizing only for today's task.
- **Decision Authority:** `evolution_engine.py::build_galaxy_evolution_report()` (ADR-173) — real monthly synthesis.
- **Required Evidence:** Real strengths (Truth Registry), weaknesses (technical debt), risks (resilience), opportunities (capital allocation opportunity cost).
- **Mandatory Reports:** Monthly Galaxy Evolution Report; this document's own Quarterly/Annual reviews (new, below).
- **Measurable KPIs:** ROI-ranked priority actions (`capital_allocation_engine.py`'s real `top_roi_initiatives`).
- **Escalation Rules:** "What prevents world-class status" is answered honestly every cycle from the most recent real audit — never softened for the founder's comfort.

---

## What was genuinely new (built for this round)

1. **Quarterly Architecture Review** — `factory_loop.js::maybeGenerateQuarterlyArchitectureReview()`, this factory's first once-per-calendar-quarter gate, reusing `enterprise_validation.py`'s already-real `build_enterprise_validation_report()` (ADR-166) verbatim. Writes `reports/ARCHITECTURE_REVIEW_<year>-Q<quarter>.md`.
2. **Annual Strategic Review** — `factory_loop.js::maybeGenerateAnnualStrategicReview()`, this factory's first once-per-calendar-year gate, reusing `strategic_planning.py`'s already-real `build_strategic_planning_dashboard()` (ADR-159) verbatim. Writes `reports/ANNUAL_STRATEGIC_REVIEW_<year>.md`.
3. **Strategic Impact Score** — `goos.py::strategic_impact_score(niche)`, the Global Dominance Directive's own named per-project score. A disclosed average of 2 already-real scores (GOOS's advisory score, ADR-171; Capital Allocation's extended Investment Score, ADR-165/176) — never a 3rd, independent computation. Honestly reports whichever real component is unavailable rather than silently substituting.

## The Global Dominance moat framework — answered by citation, not new architecture

- **What makes Galaxy Forge impossible to copy:** `market_defensibility`/`difficulty_of_copying` dimensions (GOOS, ADR-171) — a real, per-niche citation, never a company-wide slogan.
- **Why customers choose us instead of competitors:** `customer_site/index.html`'s own real, demonstrated voice ("We don't guess what the market wants. We prove it first.") — the evidence-gate discipline itself, cited in `brand_dna.py` (ADR-170).
- **Which activities should never consume engineering time** (a real, evidence-based list from this session's own standing deferrals, not invented): building real per-country/regional market data connectors before the first real dollar or a real connector becoming available (reconfirmed 4x); building UI/dashboard tiles for data that doesn't exist yet (MRR/ARR before real revenue); building a second, parallel version of any "unify the company" governance layer once one already exists (reconfirmed 6x this session alone); loosening any of the 4 founder-protected gates.

## The 4 standing founder-protected gates (unchanged by this document)

Evolution execution (`evolution_queue.py`), capital reallocation (`capital_allocation_engine.py`), business retirement (no real system exists, by design), elevated-risk/new-channel publishing (`channels/publish_protection.py`). This constitution cites all four; it does not, and structurally cannot, loosen any of them.

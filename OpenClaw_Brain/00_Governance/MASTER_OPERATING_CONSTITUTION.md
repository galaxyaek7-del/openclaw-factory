# Galaxy Forge Master Operating Constitution

**2026-09-29.** The permanent operating constitution of Galaxy Forge as an
autonomous global digital company — one navigable index binding the Founder's
central goal to the real mechanisms that enforce it.

---

## The Central Goal (verbatim, Founder directive 2026-09-29)

> بناء شركة رقمية عالمية متعددة الأنشطة، ذات عقل تشغيلي مستقل، قادرة على اكتشاف
> الفرص، وبناء الحلول، وإدارة الأصول، والوصول إلى الأسواق، واكتساب العملاء،
> وتوليد إيرادات حقيقية، والتعلم المستمر، والتوسع المنضبط، مع حماية مصالح
> المؤسس وتقليل اعتماده على التدخل التقني اليومي.

> Build a global multi-activity digital company with an independent operating
> mind — discovering opportunities, building solutions, managing assets,
> reaching markets, acquiring customers, generating real revenue, learning
> continuously, and expanding with discipline — while protecting the Founder's
> interests and reducing dependence on daily technical intervention.

---

## What this document is, and is not

This is a **consolidation index, not a new governance layer**. Every article
below cites the real module, ledger, or document that already enforces it —
verified against live code before writing, never restated from memory. Where
no real mechanism exists, the gap is disclosed honestly as a gap, never filled
with invented content.

This document **supersedes nothing**:

- Supreme law remains `CONSTITUTION.md` and
  `OpenClaw_Brain/00_Governance/TRUTH_FIRST_CONSTITUTION.md`.
- The operational index remains
  `OpenClaw_Brain/00_Governance/GALAXY_FORGE_EXECUTIVE_CONSTITUTION.md`
  (ADR-177).
- Safety constraints remain
  `OpenClaw_Brain/00_Governance/EXECUTIVE_SAFETY_PRINCIPLES.md`.
- Identity constraints remain
  `OpenClaw_Brain/00_Governance/IDENTITY_ARCHITECTURE.md` (single personal
  Google account by conscious decision, ADR-014).
- The Founder interface remains the V5.4 Founder Command Center
  (`founder_command_center.py` + `founder_command_center.html`): the Founder
  governs the company, the Factory operates it.

**Amendment rule:** this constitution grows by citation, never by duplication.
A new capability is added here only when its real enforcement mechanism
already exists and is referenced by module path. A conflict between this
document and any standing human-gated protection is resolved by asking the
Founder — never by silent override.

---

## The 10 Articles

Each article: **Mandate** (what the goal demands) · **Enforcement** (the real
mechanism, verified) · **Current Truth** (the honest live state).

### Article 1 — Independent Operating Mind

- **Mandate:** The company runs continuously without daily technical operation
  by the Founder.
- **Enforcement:** `factory_loop.js` — the autonomous tick (daily/weekly/
  monthly/quarterly/annual gated steps: reports, snapshots, outcome
  measurement, blueprint/kit generation, Paddle readiness notification,
  resilience monitoring every tick). Runs supervised via
  `SUPERVISOR_TARGET=factory_loop.js node scripts/supervisor.js` with
  crash-loop guard and Telegram alerts. `autonomous_operations_status.py`
  maps every activity to automatic / human-gated / untouched.
- **Standing boundary (declined 5+ times, ADR-107→110→115→142→147→157):**
  no always-on daemon with autonomous real-world action. Autonomy ends where
  irreversible external effects begin — those stay behind Founder gates.
- **Current Truth:** The tick is real and running; every irreversible lever
  remains Founder-gated by explicit Founder decision.

### Article 2 — Opportunity Discovery

- **Mandate:** The company finds opportunities itself; the Founder never hunts
  manually.
- **Enforcement:** `market_hunter.py` (live scans incl. Hacker News),
  `golden_hunter/` (evaluation trigger, deliberately never auto-called —
  proven by `test_never_calls_run_hunt`), `automation_opportunity_scanner.py`
  (static seeds + recorded decisions only), `goos.py::rank_build_candidates()`
  (the one real cross-niche ranking), `market_domination_engine.py` (all 6
  real ladders), Real Evidence Provider abstraction
  (`multi_source_intelligence/`, 10-tier priority, graceful degradation —
  a blocked source lowers confidence, never halts evaluation).
- **Gate:** `profit_oracle.py::ladder_opportunity_score()` — Proof of Payment
  doctrine (ADR-121): a niche is rejected as `UNPROVEN` unless real,
  human-cited evidence exists that someone already pays to solve that exact
  problem. Floor `MIN_OPPORTUNITY_SCORE = 65`. Unfakeable by automation.
- **Current Truth:** ~66 real candidate niches evaluated; 0 real ACCEPTED
  today — every one fails the same universal gate. That is the gate working,
  not the pipeline broken.

### Article 3 — Solution Building

- **Mandate:** Approved opportunities become real, quality-gated products —
  never demos presented as products.
- **Enforcement:** `book_generator.py` (real PDF pipeline; deterministic
  safety-critical content via `generate_book_from_content()`, never left to
  LLM chance), `commercial_execution/` pipeline, Dual Inspection
  (`inspectors.py`), `executive_quality_gate.py::REJECT_IF_FAIL` (7 real
  checks incl. copyright/trademark, fake-urgency, content neutrality),
  `QUARANTINE.md` (3,337+ real historical rejections — the safety system
  working, disclosed not hidden). `brand_dna.py::validate_customer_facing_text()`
  enforces the Trust Framework on every generated kit.
- **Current Truth:** One real shipped product (EU AI Act Compliance Toolkit,
  31 pages, honest $310 price after market-realism audit); its regulatory
  premise was caught and corrected pre-sale by continuous monitoring.

### Article 4 — Asset Management

- **Mandate:** Every company asset is inventoried, evidenced, and reviewed —
  nothing silently rots.
- **Enforcement:** `product_master_catalog.py` (revenue/checkout detail),
  `data/market_funnel_state.json` (per-offer market truth — 51 offers, zero
  with a market signal), `truth_registry.py` (246-module mechanical
  inventory; 134 READY / 112 UNKNOWN disclosed), `reality_audit.py`
  (147→162 endpoints, 98.6%+ REAL, re-entrancy guarded),
  `enterprise_validation.py::detect_unused_services()`.
- **Current Truth:** Full inventory exists; product count is inventory, never
  a success metric (V5.4 Sec 17).

### Article 5 — Market Access

- **Mandate:** Products reach markets through protected, rate-guarded
  channels — never spam, never account-threatening bursts.
- **Enforcement:** `distributor.py` + `channels/` arms (Gumroad/Etsy/Payhip/
  Paddle real; KDP/Shopify/AliExpress greenfield, honestly labeled),
  `channels/publish_protection.py` (per-arm caps, cooldowns, spacing, global
  emergency stop — checked before every real publish, dry runs exempt),
  Founder Protection layer (new arm's first publish and elevated-risk
  publishes need explicit Founder approval), `seo_distribution.py` (the one
  READY zero-cost channel).
- **Current Truth:** Publishing code paths are real and callable; no live
  Gumroad credential and incomplete Paddle onboarding block real publishing —
  Founder actions, not code gaps.

### Article 6 — Customer Acquisition

- **Mandate:** The company earns customers through real channels with honest
  evidence at every funnel stage.
- **Enforcement:** `customer_site/` (public platform: intake → qualification/
  pricing on real engines → contract e-signature → Paddle checkout → payment
  verification → fulfillment → reviews), `customer_pipeline.py`
  (fabrication-proof reviews via real `request_id` requirement),
  `commercial_experiment_automation.py` (controlled experiments with
  observation windows — no failure declared before the window closes),
  Instant Checkout for catalog products with real Paddle `price_id`
  (tested fallback while onboarding gate holds).
- **Current Truth:** 0 verified customers, 0 verified sales. Exposure is live
  on real offer pages; evidence stops at exposure — displayed plainly, never
  softened.

### Article 7 — Real Revenue Generation

- **Mandate:** Only verified money counts. Activity is never presented as
  income.
- **Enforcement:** `finance_data.json` (sales array, `DELETE-ME` test records
  filtered), `channels/ledger.py` (append-only; `reality.py` excludes every
  `dry_run` event from ground truth), `config/reality.json`
  (`published_books: []` — deliberately unfakeable), `simulation_mode.py`
  (simulated economics tagged `{"simulation": true}`, physically separated
  ledgers, `RuntimeError` if simulated paths run under production mode).
- **Display law:** `VERIFIED REVENUE: $0` — prominent, unsoftened (V5.4 Sec 5).
  Page views, clicks, downloads, commits, published products, QA passes, and
  generated assets never count as revenue.
- **Current Truth:** $0 verified revenue. The first-dollar blockers are two
  Founder-only actions (payment onboarding, customer outreach).

### Article 8 — Continuous Learning

- **Mandate:** Every action teaches the company; lessons are retained and
  measured — never lost, never assumed.
- **Enforcement:** `evolution_queue.py` (Observe→Think→Simulate→Decide→
  Execute→Learn→Protect; **Execute human-gated always** — every proposal stops
  at `AWAITING_FOUNDER_APPROVAL`), `measure_outcome()` (7-day-minimum
  IMPROVED/DEGRADED/NO_CHANGE vs. real baselines; honestly `NO_REAL_SIGNAL`
  where no signal exists), `knowledge_graph/build.py` (Decision/Outcome/
  Proposal/Lesson/ADR/CouncilRecommendation/ExecutiveDirective nodes),
  `decision_engine/feedback.py::sync_outcomes()`,
  `OpenClaw_Brain/19_Lessons_Learned/` (real mistake→fix records, auto-graphed),
  `galaxy_council.py` + `executive_board.py` track records
  (`matched`/`diverged`/`pending`, never backfilled).
- **Current Truth:** Learning machinery is real; outcome verdicts are mostly
  `NOT_ENOUGH_DATA` — disclosed, not hidden.

### Article 9 — Disciplined Expansion

- **Mandate:** No new product, division, or market before the current one
  proves itself. Ambition without discipline is fabrication with extra steps.
- **Enforcement:** The Golden Rule (no expansion before the first real dollar
  — invoked to defer GCID/ADR-148, country intelligence/2026-07-23,
  Global Affiliate Commerce Engine/ADR-152 with zero code authorized),
  `launch_readiness.py` (8-dimension per-division scorecard; unarchitected
  divisions honestly report `not_architected`), `growth_stages.py`
  (Stage 1 Validation today; Stage 5 blocked by standing Founder policy, not
  data), `capital_allocation_engine.py` + `enterprise_capital_allocation.py`
  (the engine recommends, the Founder decides — sunk-cost-proof by
  architecture: no cumulative-spend parameter exists in any scoring
  signature).
- **Current Truth:** Discipline is holding: zero premature divisions built.

### Article 10 — Founder Protection & Freedom from Technical Toil

- **Mandate:** The Founder's interests are structurally protected, and the
  Founder governs the company — never operates the machine.
- **The 4 protected human gates** (reconfirmed unchanged across ADR-133/134/
  139/142/144/147/157 — loosen none without asking again): evolution
  **Execute**, capital **reallocation**, business **retirement**, new-channel /
  elevated-risk **publishing**.
- **Enforcement:** `data/founder_gates.jsonl` (append-only, deduped by
  GATE_ID, ACKNOWLEDGED/SUPERSEDED lifecycle), `founder_next_action.py` (one
  prioritized next action, not twenty tasks), `safe_mode.py` (stop only the
  affected subsystem, never cascade), V5.4 Founder Command Center
  (`founder_command_center.html`, Mission-Control-auth-gated, mobile-first):
  COMPANY / MONEY / CUSTOMERS / OPPORTUNITIES / OPERATIONS / FACTORY /
  MY ACTIONS / SECURITY — business language by default, technical details
  hidden, UNKNOWN always visible as unknown.
- **Operating principle:** FROM founder-operates-factory TO founder-governs-
  company WHILE factory-operates-company.

---

## Standing Constraints (supreme law, restated as citations)

1. **Truth First** (`TRUTH_FIRST_CONSTITUTION.md`): 9 canonical gap terms for
   all new work; ~350 pre-existing honest variants grandfathered, never
   cosmetically renamed. No fake urgency, no fake reviews, no fake scarcity,
   no manipulated copy — enforced by `brand_dna.py` + `executive_quality_gate.py`.
2. **Single Source of Truth** (V5.4 Sec 30): the interface reads authoritative
   state only. Two disagreeing sources display `REALITY MISMATCH` — never a
   silent pick of the flattering number.
3. **Privacy** (V5.4 Sec 29, `IDENTITY_ARCHITECTURE.md`): no secrets, tokens,
   credentials, internal paths, or private data through any Founder or public
   surface. Configuration NAMES only, never values.
4. **Evidence over adjectives** (V5.4 Sec 25): every commercial claim carries
   measurable evidence or is labeled unverified.
5. **No false simplicity** (V5.4 Sec 32): complex issues display as complex,
   explained simply — uncertainty is never hidden to keep the interface clean.

---

## Honest Gap Register (disclosed, not built)

These are real missing capabilities, recorded here so no future work pretends
they exist:

- **Retention:** no repeat-purchase / follow-up / referral machinery — system
  reports `READY / WAITING FOR FIRST VERIFIED CUSTOMER` (V5.4 Sec 7).
- **Recurring revenue:** no subscription/billing infrastructure; revenue is
  one-time-only by architecture today.
- **Forward-looking revenue forecasts:** `expected_revenue` is retrospective;
  multiplying it into projections would be fabrication (ADR-165/176).
- **Per-niche TAM/SAM/SOM and market maturity:** zero real data source
  (GOOS/ADR-171, capital allocation/ADR-165).
- **Country-level market intelligence:** deferred by standing Founder decision
  (2026-07-23) until the first real dollar or a real local connector.
- **Customer notification (email/SMS):** 0% built; pull-based status pages are
  the real substitute; the Founder is still notified via Telegram.

---

## Ratification

This constitution is ratified as the master operating index of Galaxy Forge. It
creates no new authority, removes no existing protection, and authorizes no new
automation. The Factory continues to operate the company behind the Founder
Command Center; the Founder continues to govern through it.

*What is happening · Why it matters · What the evidence says · What the
Factory has done · What the Founder must decide · What happens next.*

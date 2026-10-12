# Product Class Registry

**Created:** Cycle 78, 2026-10-11. **Purpose:** a prioritization/triage tool only — see the warning at the bottom. This registry does not exempt any product from Gate-2 (founder sign-off), ADR-121 (Proof of Payment doctrine), `profit_oracle.py`'s `profit_score`/`ladder_opportunity_score()` gates, or any other existing quality/commercial gate in this factory. Every claim below is cited to real, checked code or explicitly marked UNKNOWN/DISCOVERY — never invented.

Machine-readable sibling: `docs/product_classes.json` (same schema style as `config/capability_registry.json`'s REAL/ESTIMATED/DISCOVERY convention).

**Ground truth check before reading further:** `config/reality.json` → `published_books: []`. `finance_data.json` → `sales: 0`. Zero verified revenue exists for any class below, regardless of its readiness label.

---

## Active single-focus narrowing (Cycle 82, "From Builder to Seller") — supersedes the registry below until 10 verified sales

**ADR-247** (`OpenClaw_Brain/00_Governance/ADR-247-arabic-hvac-refrigeration-focus.md`) froze all new business-arm/infrastructure work and converged the factory on exactly one audience and one product line until the first 10 real, independently-verified sales exist: **Arabic-speaking HVAC/refrigeration technicians (Algeria, Maghreb, Gulf)**, buying **Arabic-language digital technical reference guides** (refrigerant P-T charts, fault-diagnosis guides, AC wiring/electrical diagrams, maintenance checklists).

### E1. `arabic_hvac_pt_chart_guide` — Arabic refrigerant pressure-temperature chart + diagnostic primer
1. **Maturity:** DRAFT, unpublished. First concrete artifact: `docs/PRODUCT_REVIEW_HVAC_PT_CHART_AR.md` (Cycle 82) — a full Arabic review file with a complete R-22/R-410A pressure-temperature table transcribed verbatim (zero recomputation) from a single dated, cited manufacturer-adjacent reference (ADVANTAGE Engineering FYI #289, 2009/updated 2012), plus an ASHRAE 34 A1 safety-classification citation and mandatory electrical/refrigerant-handling warnings.
2. **Automated QA:** not yet routed through `inspectors.py` Dual Inspection — this is a hand-authored review draft, not a `book_generator.py` pipeline run, specifically because every number needed a disclosed, checkable source rather than LLM generation (see the review file's own §0 for why this deviates from the research fork's #1-ranked pick, an AC wiring guide, which was judged too source-risky for a first attempt).
3. **Price range:** $9–$19 (directive-set, not yet market-tested).
4. **Human review required (mandatory, blocking):** the founder (a refrigeration engineer) must personally verify every number in the review file before any publish — explicitly **not published this cycle**, per the directive's own rule.
5. **Demand evidence:** no `ladder_opportunity_score()`/ADR-121 payment-evidence entry exists for this niche yet — this class was founder-selected for this cycle, not surfaced by the existing 500-candidate discovery dataset. See `docs/CYCLE_82_FINAL_REPORT.md` §2 for the real competing-product evidence found (Amazon/Etsy/Udemy listings, no confirmable sales/rating counts) and §2's ADR-121 decision-proposal on whether that kind of secondhand evidence can ever qualify.
6. **Platforms:** Gumroad (existing channel) — **current credential is `UNVERIFIED_COMPROMISED` (see `gumroad_auth_watch.py`), no write/publish may use it this cycle regardless of this product's own readiness.**
7. **Confidence:** MEDIUM on sourcing discipline (every number cited); LOW/UNKNOWN on demand (no ADR-121 evidence recorded for this specific niche yet).

---

## A. Potentially High-Readiness Classes (standing registry — paused per the freeze above, not deleted)

### A1. `templates_xlsx_docx_sop` — Professional templates/checklists/SOPs (XLSX/DOCX/PDF bundles)
1. **Maturity:** REAL, shipped. `cohort_GF_BATCH11_2026_09/dist/GF-B11-01/` and `GF-B11-02/` (tracked in git) contain real, built `.xlsx`/`.docx`/`.pdf` bundles (EUDR due-diligence kit, EMPCO green-claims kit) with real `manifest.json` per bundle.
2. **Automated QA:** `product_families/families/professional_templates.py` + `digital_toolkits.py` (both tracked, both report `REAL` from `production_factory.dossier._product_type_capability()`, live-checked this cycle) — routed through the shared Dual Inspection gate (`inspectors.py`).
3. **Price range (estimate, not proven):** $25–$97, per `config/economics.json`'s `gumroad_premium`/`gumroad_elite` tiers (min net $25/$70 respectively) — a cost-floor-derived band, not a market-tested price.
4. **Build/run/host/support cost:** Groq generation cost only (`data/ai_cost_log.jsonl`), $0 hosting (static files via Gumroad/Etsy), no ongoing support infra exists.
5. **Platforms:** Gumroad, Etsy (per `supported_marketplaces` in the family manifests) — both currently blocked for new writes (Gumroad: compromised credential; see Factory Automation Audit §C).
6. **Human review needed:** spot-check content accuracy before first sale of any new topic (no legal/financial claim verification pipeline exists for this class specifically).
7. **Time to first revenue:** UNKNOWN/unestimable with evidence — zero sales ever recorded for this class; `87 days` of real production history exists with $0 revenue (not treated as proof of non-demand, per Cycle 78's own rule — see Automation Audit §F).
8. **Risks:** low technical risk (proven pipeline); commercial risk unproven (zero real sales).
9. **Demand evidence:** NONE direct to this class; `data/market_intelligence_analyses.jsonl` carries general niche-pain signals, not SOP-template-specific demand.
10. **Accept/reject before building more:** accept only niches that already cleared `ladder_opportunity_score()`'s Proof-of-Payment gate (ADR-121) — this registry does not relax that gate.
11. **Confidence:** MEDIUM on buildability (proven), LOW on sellability (no sale ever confirmed).

### A2. `market_competitor_reports` — Evidence-cited market/competitor reports
1. **Maturity:** REAL, internal-only. `competitor_discovery.py` + `market_intelligence_core/` (tracked, 51/51 related tests passing per this cycle's audit) produce real `source_url`/evidence-cited competitor and demand signals.
2. **Automated QA:** `inspectors.py::market_realism` check (existing).
3. **Price range (estimate):** $47–$150 if packaged as a sold report (unprecedented — no prior sale of this shape exists; estimate only, modeled on comparable premium-tier guides).
4. **Cost:** Groq + live HN/GitHub query cost only, $0 hosting.
5. **Platforms:** Gumroad (digital report), same blocker as A1.
6. **Human review:** required — verify every `source_url` actually resolves and supports the claim before sale (no automated link-liveness check exists today for a report sold externally).
7. **Time to first revenue:** UNKNOWN — never packaged as a standalone sold product before; the underlying data is currently internal decision-support only (confirmed by Cycle 78's 8-arm audit, arm 5).
8. **Risks:** a stale/dead `source_url` at the moment of sale would misrepresent evidence currency — real risk, no automated mitigation yet.
9. **Demand evidence:** NONE direct (no customer has ever asked for or bought this).
10. **Accept/reject:** build only after a specific niche's report clears the same ADR-121 evidence bar as any other product; packaging-only effort (data already exists).
11. **Confidence:** MEDIUM on technical buildability; UNKNOWN on demand (never tested).

### A3. `small_scripts_cli_tools` — Small tested scripts/CLI utilities as a sellable product
1. **Maturity:** SCAFFOLD_ONLY as a *product line* — this factory's own codebase proves scripts/CLI tools are technically easy to build and test (hundreds exist internally), but **zero evidence** any script has ever been packaged and sold as an external product.
2. **Automated QA:** generic — would reuse `scripts/scan_for_secrets.py`-style static checks + real `pytest`/`node --test` execution before shipping a tool externally (not currently wired to any sale path).
3. **Price range (estimate):** $9–$47 (one-time, low-effort digital tool norm) — unproven.
4. **Cost:** near-$0 to build (reuses existing patterns); packaging/docs for an external, non-technical buyer is the real unbuilt cost.
5. **Platforms:** Gumroad, GitHub (free listing) — both viable in principle.
6. **Human review:** required — a buyer-facing CLI tool needs real documentation and a support channel this factory doesn't have.
7. **Time to first revenue:** UNKNOWN, never attempted.
8. **Risks:** support burden if buyers hit environment/install issues with no support infra.
9. **Demand evidence:** NONE found.
10. **Accept/reject:** needs a real demand signal (e.g., a recurring real pain-point query from Pioneer/HN data) before investing packaging effort.
11. **Confidence:** LOW overall (buildable, but zero market validation of any kind).

### A4. `arabic_prompt_packs` — Arabic-language profession-specific prompt packs
1. **Maturity:** **UNCOMMITTED, near-complete scaffold** — `product_families/families/prompt_libraries.py` exists on disk (30 lines, a real `ProductManifest` wired to `register_manifest_driven_family()`, price_hint $29, targets Gumroad+Etsy) **but `git status` shows it as `??` (untracked)** — it has never been committed, and `production_factory.dossier._product_type_capability()` (live-checked this cycle) reports `prompt_libraries: NOT YET BUILT` precisely because this unregistered file was never imported into the real system. **This is the single most "almost there" class in the entire registry** — but it is part of the same ~168-file uncommitted branch flagged as a standing decision item (see Automation Audit §I).
2. **Automated QA:** would inherit the shared Dual Inspection gate once wired in — not active today.
3. **Price range:** manifest's own `price_hint: $29` (its author's estimate, not market-tested).
4. **Cost:** $0 additional (reuses the existing `groq_techdoc`/`techdoc_package` pipeline).
5. **Platforms:** Gumroad, Etsy per the manifest.
6. **Human review:** required for any Arabic-specific cultural/professional accuracy claim — no Arabic-content review pipeline exists.
7. **Time to first revenue:** UNKNOWN.
8. **Risks:** none new beyond the existing pipeline's risks; the real decision is whether to commit+register this file at all (see §I).
9. **Demand evidence:** NONE found for Arabic prompt packs specifically.
10. **Accept/reject:** a founder decision on the uncommitted branch (§I), not a technical one.
11. **Confidence:** HIGH on "this would work if committed" (it reuses a proven pipeline byte-for-byte); ZERO on demand.

### A5. `n8n_importable_packages` — n8n workflow bundles sold as a product
**Maturity: DOES NOT EXIST.** Verified directly: `product_families/families/automation_systems.py` (the real, registered family closest to this name) generates a **PDF/document describing** a business-automation system — not an actual importable `.json` n8n workflow file. This factory's only real `.json` n8n workflow files (`n8n_workflows/*.fixed.json`) are **internal operational workflows for Galaxy Forge itself** (Market Scout, Sensing Engine, Sales Poll), never packaged or offered for sale. There is no code path anywhere that turns a workflow into a customer-deliverable import file. This is a **Category D** item in practice (new, feasibility-only), despite the founder's directive listing it under "high readiness" — the registry records the real finding, not the assumption.

---

## B. Classes Requiring Human Review Before Sale

### B1. `pdf_guides_marketing_copy` — PDF guides, email sequences, marketing copy, mini-courses
1. **Maturity:** REAL, one real shipped example exists: `books/eu_ai_act_compliance_toolkit.pdf` (31 pages, tracked, real technical+commercial inspection passed per repo history) + `books/eu_ai_act_compliance_toolkit_launch_kit.md` (real marketing copy, source-cited).
2. **Automated QA:** `inspectors.py` Dual Inspection (technical+commercial), already proven on this exact artifact.
3. **Price:** $310 (real, already-set price for the one shipped example, per `config/economics.json`'s `gumroad_elite` tier) — **still a listed, not a confirmed-sold, price.**
4. **Human review required (mandatory, not optional):** this factory's own history records a real defect — a "not legal advice" disclaimer specified in the generation prompt never rendered into the actual shipped PDF, found only by a direct post-hoc audit. Automated generation alone is **not sufficient** for this class.
5. **Risk:** legal/financial exposure from an unreviewed claim — the exact failure mode already caught once.
6. **Demand evidence:** none beyond the one shipped example; $0 sales recorded.
7. **Confidence:** MEDIUM (pipeline proven, human-review step proven necessary and now documented).

### B2. `legal_compliance_kits` — Regulatory compliance kits (EU AI Act, GPSR done; **PDPL Saudi Arabia: NOT STARTED**)
1. **Maturity:** PARTIAL. Real shipped examples exist for EU AI Act and GPSR (`customer_site/gpsr-landing.html`, `books/eu_ai_act_*`). **Saudi PDPL: zero files found anywhere in the tracked repo** (`git ls-files | grep -i pdpl` → no results) — this is a from-scratch build, not an existing-but-unpolished asset.
2. **Mandatory human review:** a licensed/qualified reviewer (or at minimum a clear "not legal advice" disclaimer, proven to actually render — see B1's lesson) before any sale, for every jurisdiction.
3. **Risk:** highest in this registry — wrong regulatory guidance has real financial/legal consequences for a buyer. This factory already found and corrected one real regulatory-currency error in the EU AI Act kit (a 16-month enforcement-date deferral it had gotten wrong) — proof this risk is live, not theoretical.
4. **Price:** $150–$350 (estimate, based on the EU AI Act precedent).
5. **Demand evidence:** none specific to PDPL.
6. **Accept/reject:** do not build PDPL content without (a) real evidence of demand and (b) a named human reviewer path — this is explicitly NOT an auto-build class.
7. **Confidence:** LOW (new jurisdiction, no reviewer pipeline, no demand evidence).

---

## C. Lower-Readiness Classes (visual/creative-quality-dependent)

Covers, design assets, video, novels, games. **No real evidence of any shipped product in this category.** `cover_designer_v2.py` exists and is used internally for book covers (real, tracked), but that is production tooling for class A/B products, not a standalone sellable design-asset product. No video/novel/game pipeline exists anywhere in the tracked repo. Confidence: LOW across the board; building here requires creative review capacity this factory does not currently have.

---

## D. New Classes — Feasibility Study Only (explicitly NOT auto-build)

Per the founder's own instruction, these are assessed for feasibility only. None should be built this cycle.

| Class | Real code today | Feasibility note | Confidence |
|---|---|---|---|
| `saas_micro_tools` (single-function converter/generator/checker/calculator) | NONE found | **Hosting/ToS/DB/payment research not completed this cycle — out of the 15-min-per-item budget; marked UNKNOWN, not estimated.** Any SaaS requires a live DB, security posture, and ongoing support this factory has never operated. Do not build before a measurable demand signal and a named, real, currently-documented free-tier hosting option are both confirmed. | UNKNOWN |
| `telegram_whatsapp_bots_as_product` | Telegram Bot API integration exists (internal notifications only, `TELEGRAM_BOT_TOKEN` present) | Selling a bot *as a product/service* to a third party is a different undertaking (hosting their bot instance, their token, their support) — zero code exists for this. WhatsApp: no integration of any kind found. | LOW |
| `google_sheets_excel_addons` | NONE found (Apps Script, Sheets API) | No existing code touches Google Sheets/Apps Script at all. | UNKNOWN |
| `cli_python_node_tools` | See A3 above (same real gap: buildable, never sold) | | LOW |
| `structured_datasets` | Real raw data exists internally (`data/*.jsonl` ledgers) but none are cleaned/documented/licensed for external resale | Would require a real data-cleaning + licensing-terms pass before any sale; not started. | UNKNOWN |
| `subscription_newsletters_reports` | NONE found — no recurring-billing code path exists anywhere (confirmed: only one-time Gumroad/Paddle one-off purchases are wired) | Recurring billing is a materially different commercial/legal/tax surface than this factory has ever operated. | UNKNOWN |
| `ai_agent_deployment_as_service` | NONE found (see Factory Automation Audit, arm 4 — "Done-for-You AI Agent Deployment" has zero real mapping in code) | Would require human-labor delivery component this factory has no process for. | UNKNOWN |
| `browser_extensions` | NONE found | Chrome/Firefox store fees, review process, and permissions audit not researched this cycle. | UNKNOWN |

**SaaS-specific findings (per the directive's explicit checklist), live-verified this cycle by a research fork:** no dedicated payment-gateway integration exists for a hosted SaaS (Stripe/Shopify are absent from this factory's real `channels/registry.py`); no database layer exists anywhere in this factory by design (flat JSON/JSONL only, per `CLAUDE.md`'s own architecture note); geographic payout eligibility is a REAL, already-encountered constraint elsewhere in this factory (PayPal does not support Algeria, per code citations in `commission_engine.py`) and would apply equally to any new SaaS payment path. **None of this clears a single SaaS micro-tool for building this cycle** — the explicit directive's own instruction ("ابدأ بدراسة الجدوى... لا بالبناء") is honored: no SaaS code was written.

---

## Important

This registry is a **prioritization and triage tool only**. No entry here — regardless of its "maturity" or "confidence" label — exempts a product from:
- Gate-2 (founder sign-off ledger)
- ADR-121 (Proof of Payment doctrine — real evidence of willingness-to-pay required before production)
- `profit_oracle.py`'s `profit_score` / `ladder_opportunity_score()` gates
- Dual Inspection (`inspectors.py`) technical + commercial checks
- Any other existing quality or commercial gate in this factory

A class marked "high readiness" above means **the pipeline to build it is proven** — it says nothing about whether any specific candidate niche in that class has cleared the real evidence gates, which remain the single authoritative acceptance criterion.

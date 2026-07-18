# Universal Production Engine (UPE)

**Status:** Roadmap Step 2 shipped, 2026-07-18. `automation_systems` is the first product family built end-to-end on the new architecture and is now the reference template every future family follows.

This file is the engineering record of what's actually built. The original architecture plan (System Architecture / Module Interfaces / Data Flow / Product Lifecycle / Folder Structure / Roadmap) was approved and implemented in two steps:

- **Step 1** (interfaces, zero new families): `content_generation/`, `asset_generation/`, `dossier_bundle/` — formalized the swappable Content/Asset Generation interfaces and the mandatory per-product artifact bundle, wrapping the 4 already-shipped families (`kdp_books`, `professional_templates`, `digital_toolkits`, `knowledge_bases`) with zero behavior change.
- **Step 2** (this step): `automation_systems` — the first family that actually routes through those new registries instead of calling `book_generator.py` directly, plus everything Step 1 left as future work: `product_packaging/`, and `dossier_bundle`'s version/build-manifest/QA-report/recovery-metadata fields.

## What's real vs. what's still a template for later

| Piece | Status |
|---|---|
| `content_generation/` registry + `groq_book`/`groq_techdoc` generators | Real (Step 1), now with real recovery-queue integration (Step 2) |
| `asset_generation/` registry + `ai_book`/`techdoc_package` builders | Real (Step 1) |
| `product_packaging/` registry + `single_file` packager | Real (Step 2) |
| `dossier_bundle` (documentation/metadata/marketing/support/changelog) | Real (Step 1) |
| `dossier_bundle`'s version/build_manifest/qa_report/recovery_metadata | Real (Step 2) |
| `automation_systems` family adapter | Real (Step 2) — the reference implementation |
| `ai_saas`, `notion_workspaces`, `spreadsheet_systems`, `prompt_libraries`, `api_products`, `micro_saas` | Not built — see "Adding a new family" below |

## Folder structure (as actually shipped — one deliberate deviation from the original plan)

```
content_generation/
  registry.py
  generators/groq_generator.py        (groq_book, groq_techdoc — both now
                                        enqueue a real recovery-queue retry
                                        on Groq failure, threading
                                        production_id through for traceability)

asset_generation/
  registry.py
  builders/pdf_builder.py              (ai_book, techdoc_package)

product_packaging/                     (NOT "packaging/" — the original plan
  registry.py                          named this folder "packaging/", but
  bundle.py                            that shadows the installed pip
                                        `packaging` library (version parsing,
                                        used by pip/setuptools) since this
                                        factory's root is on sys.path. Caught
                                        before it shipped; renamed. Any future
                                        reference to the plan's "packaging/"
                                        folder means this one.)

dossier_bundle/
  build_bundle.py                      (build_product_dossier_bundle())

product_families/
  families/automation_systems.py       (the reference UPE family adapter)
  mapping.py                           ("automation_packs" renamed to
                                        "automation_systems" here, the moment
                                        a real adapter was built under that
                                        name — the plan had already adopted
                                        the new wording, this is where it
                                        actually landed in code)
```

## The reference family: `automation_systems`

`product_families/families/automation_systems.py`'s `generate(spec)` is the concrete answer to "how does a family actually use the UPE registries":

```
1. Content Generation  — content_generation.registry.get("groq_techdoc").generate(...)
                          (skipped per-section for any component already
                          carrying real, verbatim content)
2. Asset Generation    — asset_generation.registry.get("techdoc_package").build(...)
                          (never re-generates content the step above already
                          produced — components_to_sections() treats a
                          {"title","content"} dict as verbatim either way)
3. Packaging           — product_packaging.registry.get("single_file").package(...)
                          (today's families all produce exactly one PDF; a
                          future multi-file family registers a real zip
                          packager here without this file changing)
4. Dossier Bundle      — dossier_bundle.build_bundle.build_product_dossier_bundle(...)
                          (documentation, metadata, marketing, support,
                          changelog, version, build manifest, QA report,
                          recovery metadata — see below)
```

Its own section skeleton (`DEFAULT_AUTOMATION_SECTIONS`) is real and distinct from the generic techdoc default: *System Overview, Workflow Architecture, Setup & Integration Guide, Automation Triggers & Logic, Maintenance & Troubleshooting, ROI & Time Savings*.

## Per-product artifacts (every product, not just this family)

`build_product_dossier_bundle()` now returns:

| Field | What it actually is |
|---|---|
| `production_id` | Unchanged formula, `PROD-{decision_id}` (ADR-077/050) — never a second ID scheme |
| `version` | Derived from real changelog history: first build of a `production_id` is `1.0.0`; each real regeneration bumps the minor number. Never fabricated. |
| `documentation` | A plain README assembled from the spec's already-generated components — no new generation |
| `metadata` | Reuses `production_factory/dossier.py`'s full real assembly when a `Decision` is supplied; a smaller, honest subset otherwise |
| `marketing` / `support` | Real Groq-backed copy (headline/description/keywords, FAQ), same honest-fallback discipline as every other AI content path in this factory |
| `build_manifest` | Files produced, which registry implementations built them (`content_generator`/`asset_builder`/`packager`), a spec hash, and when |
| `qa_report` | `inspectors.py`'s real Dual Inspection result, surfaced verbatim — never recomputed |
| `recovery_metadata` | A real, filtered lookup of this exact `production_id`'s pending retries in `factory_state.json` — never a fabricated "no issues" claim, and never a per-product history invented from `data/recovery_actions.jsonl` (whose real records are factory-wide operator actions with no `production_id` field to filter by) |

## Integration — verified, not assumed

| System | How `automation_systems` actually integrates | Evidence |
|---|---|---|
| Decision Engine | `product_families.mapping.DEFAULT_FAMILY_BY_LADDER["b2b_systems"/"automation_tools"]` now resolves to `"automation_systems"` | `tests/test_automation_systems_e2e.py`'s full pipeline runs a real `profit_oracle.ladder_opportunity_score()` → `decision_engine.engine.record_ladder_decision()` → the resolved `Decision.product_family` |
| Orchestrator / Production Queue | `orchestrator/engines/production.py`'s existing family-adapter dispatch (`product_families.registry.get(product_family).generate(spec)`) needed zero changes | Same E2E test calls `orchestrator.engines.production.run()` directly, not the adapter |
| Mission Control | `production-families` service (Step 1) is data-driven off the registry — automatically reports `automation_systems` as REAL the moment the adapter self-registers | `mission_control_api._production_families()`, asserted in the E2E test |
| Factory State / Recovery Queue | `content_generation`'s Groq generators now call `factory_state.enqueue_retry()` on failure, threading `production_id` through `context` | E2E test's interruption simulation: a mocked Groq failure produces a real, traceable `pending_retries` entry |
| Revenue Tracking | Unchanged — `channels/ledger.py`'s reconciliation is family-agnostic | Not re-tested here; already proven generic in ADR-077 |
| Knowledge Base | Transitive, not direct: this family runs through `orchestrator`'s `production` stage same as any other, which `mission_control_api._full_cycle()`'s `knowledge_base_update` step logs after (`data/full_cycle_runs.jsonl`) — no new per-family code needed | Existing `_full_cycle()` mechanism, unchanged |

## Marketplace compatibility

`automation_systems` produces a `product_type="techdoc"` PDF — the exact same shape `digital_toolkits`/`professional_templates` already produce. `schemas/product.py`'s `Product.from_jsonl_record()` already prices `"techdoc"` against the `gumroad_elite` band with zero family-specific code, and both `channels/paddle_arm.py` and `channels/gumroad_arm.py` implement the same generic `BaseArm` contract (`title`/`description`/`price_usd`/`file_path`).

**Verified** (`tests/test_automation_systems_e2e.py::test_round_trips_through_the_generic_product_schema_and_dry_run_publish`): a real generation result round-trips through `Product.from_jsonl_record()` and a dry-run `publish()` on both arms with zero special-casing.

**Shopify**: future, not built. `BaseArm`'s contract needs no schema change to add a `ShopifyArm` later — same reasoning the original plan already gave — but no such arm exists today; this is a documented gap, not an aspirational claim.

## Adding the next family: configuration, not a rewrite

A future family (`prompt_libraries`, `spreadsheet_systems`, etc.) needs:

1. A `product_families/families/<name>.py` module shaped exactly like `automation_systems.py`: its own `DEFAULT_*_SECTIONS` (or an equivalent real content shape), then Content Generation → Asset Generation → Packaging → Dossier Bundle, each via the registries.
2. If the existing `groq_techdoc`/`techdoc_package`/`single_file` implementations fit (true for anything that's fundamentally "a PDF built from generated sections" — most of the remaining 6 families), **zero new registry code is needed** — only step 1 above.
3. If the family needs a genuinely different asset shape (a spreadsheet workbook, a Notion export), a new `asset_generation/builders/*.py` module registers under a new name — `product_families/families/<name>.py` is the only file that changes to use it.
4. `product_families/mapping.py`'s `DEFAULT_FAMILY_BY_LADDER` gets one new entry once the founder confirms which ladder rank(s) the family maps from.
5. Mission Control's `production-families` service picks it up automatically — no change needed there.

`api_products`/`micro_saas` remain the one real exception: they need actual `Customer Delivery` provisioning (API key issuance, environment setup) that no marketplace does automatically, deferred until the founder confirms what real provisioning means for this factory (unchanged from the original plan's own Roadmap §5).

## Tests

- `tests/test_content_generation.py`, `tests/test_asset_generation.py`, `tests/test_dossier_bundle.py` — unit tests per module (Step 1, extended Step 2).
- `tests/test_product_families.py`'s `TestAutomationSystemsAdapter` — the family adapter in isolation.
- `tests/test_automation_systems_e2e.py` — the full pipeline, real Decision Engine + real orchestrator dispatch, a real interruption simulation, and the marketplace round-trip proof.

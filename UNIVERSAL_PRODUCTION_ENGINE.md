# Universal Production Engine (UPE)

**Status:** Roadmap Step 3 shipped, 2026-07-19. A Product Definition Registry now replaces family-specific routing: 3 families (`automation_systems`, `professional_templates`, `digital_toolkits`) are pure configuration — `ProductManifest` objects, zero bespoke Python — and a brand-new family needs only one to work.

This file is the engineering record of what's actually built. The original architecture plan (System Architecture / Module Interfaces / Data Flow / Product Lifecycle / Folder Structure / Roadmap) was approved and has been implemented in three steps:

- **Step 1** (interfaces, zero new families): `content_generation/`, `asset_generation/`, `dossier_bundle/` — formalized the swappable Content/Asset Generation interfaces and the mandatory per-product artifact bundle, wrapping the 4 already-shipped families (`kdp_books`, `professional_templates`, `digital_toolkits`, `knowledge_bases`) with zero behavior change.
- **Step 2**: `automation_systems` — the first family that actually routed through those new registries instead of calling `book_generator.py` directly, plus everything Step 1 left as future work: `product_packaging/`, and `dossier_bundle`'s version/build-manifest/QA-report/recovery-metadata fields.
- **Step 3** (this step): the Product Definition Registry (`product_families/manifest.py` + `generic_adapter.py`) — `automation_systems`'s Step 2 hand-written adapter class is now itself just configuration, and 2 more families (`professional_templates`, `digital_toolkits`) converted alongside it.

### Step 3's scope decision — "lighter path," not the full literal spec

The founder's Step 3 request asked for a manifest **file** format with **dynamic loading** (discover families from disk — manifest + templates + prompts + assets, zero Python) and a formal **DI container** for 7 roles. Before building that, the real cost/benefit was raised directly: this factory has exactly **one** proven family (`automation_systems`, Step 2) and zero real revenue yet — building a file-based loader and DI framework now would be exactly the premature architecture generalization `MASTER_CHARTER.md` and `CLAUDE.md`'s own "don't expand before the first dollar" principle warn against, before anything has proven the *current* registry pattern insufficient.

**Decision (founder-confirmed): the lighter path.** A real, validated `ProductManifest` **Python object** (not a file on disk) replaces per-family routing; the existing registries (`content_generation`, `asset_generation`, `product_packaging`) already *are* the dependency injection — a manifest just names which registered implementation to use. No new loader, no new DI framework, no new failure surface. This satisfies the actual goal (a family = configuration, not code) with a small fraction of the engineering investment, and is easy to grow into the full file-based version later *if* a real second data point (a 4th, 5th family) ever shows the Python-object manifest is genuinely insufficient.

## What's real vs. what's still a template for later

| Piece | Status |
|---|---|
| `content_generation/` registry + `groq_book`/`groq_techdoc` generators | Real (Step 1), with real recovery-queue integration (Step 2) |
| `asset_generation/` registry + `ai_book`/`techdoc_package` builders | Real (Step 1) |
| `product_packaging/` registry + `single_file` packager | Real (Step 2) |
| `dossier_bundle` (documentation/metadata/marketing/support/changelog/version/build_manifest/qa_report/recovery_metadata) | Real (Step 1 + Step 2) |
| `product_families/manifest.py` (`ProductManifest`, the Product Definition Registry) | Real (Step 3) |
| `product_families/generic_adapter.py` (`ManifestDrivenFamily`, `register_manifest_driven_family()`) | Real (Step 3) |
| `automation_systems`, `professional_templates`, `digital_toolkits` | Real (Step 3) — pure `ProductManifest` configuration, zero bespoke adapter code |
| `kdp_books`, `knowledge_bases` | Real, deliberately bespoke Python — see "Why 2 families stay bespoke" below |
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
  manifest.py                          (ProductManifest + its registry — the
                                        Product Definition Registry itself)
  generic_adapter.py                   (ManifestDrivenFamily — the ONE
                                        generic dispatcher every manifest-
                                        driven family shares; and
                                        register_manifest_driven_family(),
                                        the one call a config-only family
                                        needs)
  families/automation_systems.py       (now just a ProductManifest + one
                                        registration call — no adapter class)
  families/professional_templates.py   (same — converted alongside it)
  families/digital_toolkits.py         (same — converted alongside it)
  families/kdp_books.py                (still bespoke Python — real
                                        distinct logic, see below)
  families/knowledge_bases.py          (still bespoke Python — real
                                        distinct logic, see below)
  mapping.py                           ("automation_packs" renamed to
                                        "automation_systems" here, the moment
                                        a real adapter was built under that
                                        name — the plan had already adopted
                                        the new wording, this is where it
                                        actually landed in code)
```

## The Product Definition Registry

`product_families/manifest.py`'s `ProductManifest` is the "configuration, not code" unit Step 3 introduces:

```python
ProductManifest(
    product_id, family, category,          # identity
    content_generator, asset_builder, packager,   # which registered implementation builds this
    default_sections=[...],                # real per-family content skeleton
    qa_profile={...}, publishing_profile={...},   # documentation of the one real, shared QA/publish behavior
    pricing_strategy={...},                # LIVE: price_hint feeds the spec as a default
    supported_marketplaces=[...],          # real, computed via compatible_arms() against channels.registry
    recovery_policy={...}, version="1.0",
)
```

`product_families/generic_adapter.py`'s `ManifestDrivenFamily` is the **one** class every manifest-driven family shares — its `generate(spec)` runs the exact 4-stage pipeline `automation_systems.py`'s Step 2 hand-written class established, but every registry lookup name and default content skeleton comes from the manifest instead of being hardcoded per family:

```
1. Content Generation  — content_generation.registry.get(manifest.content_generator).generate(...)
                          (skipped per-section for any component already
                          carrying real, verbatim content)
2. Asset Generation    — asset_generation.registry.get(manifest.asset_builder).build(...)
                          (never re-generates content the step above already
                          produced — components_to_sections() treats a
                          {"title","content"} dict as verbatim either way;
                          manifest.pricing_strategy["price_hint"] fills in
                          as the spec's price_hint default)
3. Packaging           — product_packaging.registry.get(manifest.packager).package(...)
4. Dossier Bundle      — dossier_bundle.build_bundle.build_product_dossier_bundle(...),
                          crediting the manifest's registry names in the
                          real build manifest
```

**Adding a family that reuses existing generators/builders/packagers now means exactly this** (`tests/test_product_manifest.py::TestConfigOnlyFamilyAddition` proves it with a throwaway demo family):

```python
register_manifest_driven_family(ProductManifest(
    product_id="my_new_family", family="my_new_family", category="...",
    content_generator="groq_techdoc", asset_builder="techdoc_package", packager="single_file",
    default_sections=["Section A", "Section B"],
))
```

Zero new adapter class. Zero orchestrator change. Zero registry code. `automation_systems.py`'s own file (see Folder Structure above) is now this short — it's the manifest itself, not a demo of one.

### Why `kdp_books`/`knowledge_bases` stay bespoke Python

Not every family fits the generic shape, and forcing them to would be a real behavior change for zero benefit: `kdp_books` calls `generate_book()` (a different underlying function from `generate_product_package()`, different economics band, `kdp_ebook` not `gumroad_elite`); `knowledge_bases` enforces verbatim-only content (raises `ValueError` on a component with no real content — no AI-generation path by design). A manifest can only declare *which* registered implementation to use, not *different validation rules* — that's genuinely code, not configuration, so these two stay hand-written. This is itself the honest answer to "when does a family need engineering, not just configuration": when its real behavior — not just its content skeleton or pricing — actually differs.

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

| System | How a manifest-driven family actually integrates | Evidence |
|---|---|---|
| Decision Engine | `product_families.mapping.DEFAULT_FAMILY_BY_LADDER["b2b_systems"/"automation_tools"]` resolves to `"automation_systems"` | `tests/test_automation_systems_e2e.py`'s full pipeline runs a real `profit_oracle.ladder_opportunity_score()` → `decision_engine.engine.record_ladder_decision()` → the resolved `Decision.product_family` |
| Orchestrator / Production Queue | `orchestrator/engines/production.py`'s existing family-adapter dispatch (`product_families.registry.get(product_family).generate(spec)`) needed zero changes — `ManifestDrivenFamily` registers into the exact same registry a hand-written adapter would | Same E2E test calls `orchestrator.engines.production.run()` directly, not the adapter |
| Mission Control | `production-families` service reports REAL/NOT YET BUILT off the registry (Step 1) **and** now surfaces each family's real `ProductManifest` (category, generators, pricing, marketplaces) under a new `manifests` key (Step 3) | `tests/test_mission_control_api.py::test_production_families_surfaces_real_manifests_for_manifest_driven_families` |
| Factory State / Recovery Queue | `content_generation`'s Groq generators call `factory_state.enqueue_retry()` on failure, threading `production_id` through `context` — a property of the generator, not any one family | `tests/test_product_manifest.py::TestManifestDrivenRecovery` proves this against a throwaway demo manifest, not just `automation_systems` |
| Revenue Tracking | Unchanged — `channels/ledger.py`'s reconciliation is family-agnostic | Already proven generic in ADR-077 |
| Knowledge Base | Transitive, not direct: every family runs through `orchestrator`'s `production` stage same as any other, which `mission_control_api._full_cycle()`'s `knowledge_base_update` step logs after (`data/full_cycle_runs.jsonl`) — no per-family code needed | Existing `_full_cycle()` mechanism, unchanged |

## Marketplace compatibility

Every manifest-driven family produces a `product_type="techdoc"` PDF. `schemas/product.py`'s `Product.from_jsonl_record()` already prices `"techdoc"` against the `gumroad_elite` band with zero family-specific code, and both `channels/paddle_arm.py` and `channels/gumroad_arm.py` implement the same generic `BaseArm` contract (`title`/`description`/`price_usd`/`file_path`). A manifest's `supported_marketplaces` declares which platforms a family is meant for; `product_families.manifest.compatible_arms(manifest)` computes the real, live answer by intersecting that list against whichever arms are actually registered right now — never trusting the manifest's own list blindly.

**Verified** (`tests/test_automation_systems_e2e.py::test_round_trips_through_the_generic_product_schema_and_dry_run_publish`): a real generation result round-trips through `Product.from_jsonl_record()` and a dry-run `publish()` on both arms with zero special-casing.

**KDP**: legacy-only, via `kdp_books`'s bespoke adapter (not manifest-driven — see above). **Shopify**: future, not built. `BaseArm`'s contract needs no schema change to add a `ShopifyArm` later — same reasoning the original plan already gave — but no such arm exists today, so `compatible_arms()` would correctly report it absent even if a manifest declared it. **API products**: future, not built — see below.

## Adding the next family: configuration, not a rewrite

**If the family reuses existing generators/builders/packagers** (true for anything that's fundamentally "a PDF built from generated sections" — most of the remaining 6 families):

1. Register one `ProductManifest` via `register_manifest_driven_family()` — see the Product Definition Registry section above. That's the whole family definition.
2. `product_families/mapping.py`'s `DEFAULT_FAMILY_BY_LADDER` gets one new entry once the founder confirms which ladder rank(s) the family maps from.
3. Mission Control's `production-families` service picks it up automatically, manifest fields included — no change needed there.

**If the family needs a genuinely different asset shape** (a spreadsheet workbook, a Notion export) or genuinely different validation rules (like `knowledge_bases`'s verbatim-only enforcement): a new `asset_generation/builders/*.py` module (or, rarely, a bespoke `product_families/families/<name>.py` class like `kdp_books`/`knowledge_bases`) — the manifest still names which one to use for everything else.

`api_products`/`micro_saas` remain the one real exception: they need actual `Customer Delivery` provisioning (API key issuance, environment setup) that no marketplace does automatically, deferred until the founder confirms what real provisioning means for this factory (unchanged from the original plan's own Roadmap §5).

## Tests

- `tests/test_content_generation.py`, `tests/test_asset_generation.py`, `tests/test_dossier_bundle.py` — unit tests per module (Step 1, extended Step 2).
- `tests/test_product_manifest.py` — the Product Definition Registry itself: `ProductManifest`/registry, `compatible_arms()`, and the two rigorous Step 3 proofs — `TestConfigOnlyFamilyAddition` (a brand-new family needs only a manifest) and `TestManifestDrivenRecovery` (interruption-recovery holds for any manifest-driven family, not just `automation_systems`).
- `tests/test_product_families.py` — `TestAutomationSystemsAdapter`/`TestProfessionalTemplatesAdapter`/`TestDigitalToolkitsAdapter` — each real, manifest-driven family in isolation.
- `tests/test_automation_systems_e2e.py` — the full pipeline, real Decision Engine + real orchestrator dispatch, a real interruption simulation, and the marketplace round-trip proof.
- `tests/test_mission_control_api.py::test_production_families_surfaces_real_manifests_for_manifest_driven_families` — Mission Control's manifest reporting.

## Recovery verification (requirement #7)

The Product Definition Registry adds no new recovery mechanism — it reuses the Unified Recovery System (`DISASTER_RECOVERY_PLAN.md`) unchanged, which already covers every family generically because `orchestrator/orchestrator.py`'s `_run_stage()` and `factory_state.py` don't know or care which family is running:

| Scenario | Mechanism | Verified for manifest-driven families by |
|---|---|---|
| Power interruption / process crash | `factory_state.json`'s checkpoint + `recovery/startup_check.py`'s safe-startup classification | Inherited unchanged — orchestrator-level, not family-level; already proven in the Unified Recovery System's own interruption simulations |
| Internet outage (Groq unreachable) | `content_generation`'s generators enqueue a real, traceable retry (`factory_state.enqueue_retry`) instead of losing the failure | `tests/test_product_manifest.py::TestManifestDrivenRecovery` — proven against a throwaway demo manifest, so it's a property of the generic adapter, not just `automation_systems` |
| Duplicate execution / partial publishing | `channels/paddle_arm.py`'s idempotent publish (searches by `production_id` in `custom_data` before creating) + `recovery/snapshot.py`'s pre-publish snapshot | Inherited unchanged — every manifest-driven family produces the same `production_id`-tagged `Product` the existing idempotent-publish path already handles |

## A hard-won lesson from this step: test isolation for real, paid side effects

Converting `professional_templates`/`digital_toolkits` to route through `dossier_bundle` means every real generation now also makes 2 real Groq calls (marketing/support copy). An early version of their tests didn't mock `book_generator.groq_chat()` and made real, paid API calls during routine test runs (~$0.0003 total, caught and fixed same session — see `data/ai_cost_log.jsonl`'s real entries for the exact cost). **Any test that exercises a manifest-driven family's real `generate()` must mock `bg.groq_chat` in addition to whichever content-generation function it already mocks** — this is now true for every family that reaches `dossier_bundle`, not just the ones this file names.

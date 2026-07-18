# Commercial Execution Layer

**Status:** Universal Production Engine Roadmap Step 4 shipped, 2026-07-19. A unified Publish Pipeline now turns an already-generated, already-QA'd product into a real (or dry-run) marketplace listing, respecting each family's Product Manifest, with one explicit, auditable record per publish.

## What's genuinely new vs. what already existed

Most of the Commercial Execution Layer's requirements were **already real** before this step — `channels/registry.py` already is the Marketplace Registry, `distributor.py` already fans out to every arm and writes the audit ledger, `channels/ledger.py` already registers revenue, `factory_state.py` already retries real failures. This step is deliberately a **unification and one integration fix**, not a rebuild — consistent with `MASTER_CHARTER.md`'s "wrap, don't rewrite" principle.

| Piece | Status |
|---|---|
| Marketplace Registry (`channels/registry.py` + `BaseArm`) | Already real — Paddle, Gumroad, Etsy, Payhip, all one shared `status()`/`publish()`/`get_sales()` contract |
| Fan-out publishing + audit ledger (`distributor.py`, `channels/ledger.py`) | Already real — unchanged by this step |
| Real-failure retry queue (`factory_state.enqueue_retry`) | Already real — unchanged by this step |
| Revenue reconciliation (`channels/ledger.reconcile_ledger_to_finance()`) | Already real — unchanged by this step |
| **Arm selection respects a family's manifest** (`commercial_execution/pipeline.py::resolve_target_arms`) | **New this step** — the one real integration gap: publishing used to fan out to every registered arm regardless of what a product's family actually declared it supports |
| **Unified PublishRecord** (`commercial_execution/pipeline.py::build_publish_record`) | **New this step** — one explicit, auditable structure combining what used to be scattered across `PublishResult`/ledger events/`factory_state` |
| **Founder approval gates** (`commercial_execution/approval_gates.py`) | **New this step** — a real, computed answer to "what needs founder action right now," off every arm's own live `status()` |
| KDP | Still manual/file-based (no public self-publish API to automate against) — unchanged, out of scope |
| Shopify, API products | Future, not built — `BaseArm`'s contract needs no change to add a `ShopifyArm` later |

## The unified Publish Pipeline

```
Discovery → Generation → QA → Packaging          (Roadmap Steps 1-3, upstream, unchanged)
                                   │
                                   ▼
                     commercial_execution.pipeline.run_publish_pipeline(product, product_family, dry_run)
                                   │
                     ┌─────────────┼──────────────────────────┐
                     ▼             ▼                          ▼
              resolve_target_arms   distributor.distribute()   build_publish_record()
              (manifest-aware,       (fan-out publish +          (Product ID, Marketplace ID,
               Step 3 integration)    ledger + retry-enqueue,      Version, Publish Status,
                                      all unchanged)                Revenue Status, Recovery
                                                                     Token, Audit Trail)
                                   │
                                   ▼
                        Knowledge Update (existing _full_cycle()/decision_engine.learning — unchanged)
```

`orchestrator/engines/publishing.py`'s `run(context)` calls this directly, threading `context["decision_result"]["product_family"]` and the real `dossier_bundle` version through — the only change to the orchestrator itself.

## The PublishRecord (requirement #3)

`build_publish_record()` returns, per publish:

| Field | What it actually is |
|---|---|
| `product_id` | The real `Product.source_id` (`PROD-{decision_id}`, unchanged formula) |
| `version` | Passed through from `dossier_bundle`'s real per-build version, when known — honestly `None` otherwise |
| `marketplaces[].marketplace` / `marketplace_id` | The arm's own name / the platform's real returned product ID (`PublishResult.product_id`) |
| `marketplaces[].publish_status` | `"ok"` / `"not_ready"` (missing credentials — distinguished from a real failure, same convention `distributor.py` already uses to decide whether to even retry) / `"failed"` / `"not_attempted"` (skipped, with `skip_reason`) |
| `marketplaces[].recovery_token` | The **exact** task-name string `distributor.py`'s own `factory_state.enqueue_retry()` call already uses (`f"arm_publish:{arm}:{product_id}"`) — never a second, parallel ID scheme |
| `marketplaces[].has_pending_retry` | A real, live lookup of that exact token in `factory_state.json`'s `pending_retries` |
| `revenue_status.listed_on` | Real, computed from `channels/ledger.py`'s own `publish_attempt` events — which platforms this exact product successfully published to |
| `revenue_status.sale_attribution` | Honestly `"platform_wide_not_yet_per_product"` — real platform sale payloads (Paddle transactions, Gumroad sales) don't reliably echo back our internal `production_id`, so per-product sale attribution is a documented gap, not faked |
| `audit_trail` | Every real `publish_attempt` ledger event for this `product_id`, in order |

## Founder approval gates (requirement #6)

`commercial_execution.approval_gates.check_approval_gates()` splits every registered arm into `autonomous` (real `status() == READY`) and `gated` (real `status()` is `UNAVAILABLE`/`COOLDOWN`, with a generic, current-state-driven reason — never a hardcoded claim about one platform's business status, since that changes over time and a fixed comment would just go stale). Payoneer is deliberately absent: it's the founder's own payout/withdrawal rail configured inside Paddle/Gumroad's own settings, not a distribution channel this factory publishes to (`IDENTITY_ARCHITECTURE.md`/`ADR-014`) — there is no arm to gate.

## Integration — verified, not assumed

| System | How it integrates | Evidence |
|---|---|---|
| Decision Engine | `context["decision_result"]["product_family"]` flows into `resolve_target_arms()` | `tests/test_orchestrator.py::TestPublishingEngineUsesTheUnifiedPipeline` |
| Product Definition Registry (Step 3) | `resolve_target_arms()` reads `product_families.manifest`'s `compatible_arms()` | `tests/test_commercial_execution.py::TestResolveTargetArms` |
| Mission Control | New `commercial-execution` service: real approval gates + recent real publish attempts | `tests/test_mission_control_api.py::test_commercial_execution_reports_real_approval_gates_and_ledger_history` |
| Factory Queue / Recovery System | Unchanged — `distributor.py`'s existing retry-enqueue on real failure, now surfaced explicitly via `recovery_token`/`has_pending_retry` | `tests/test_commercial_execution.py::TestApiTimeoutRetry` |
| Revenue Engine | Unchanged — `channels/ledger.py`'s reconciliation | Already proven generic in ADR-077 |
| Knowledge Base | Unchanged — transitive via `_full_cycle()`'s `knowledge_base_update` step | Existing mechanism |

## Recovery verification (requirement #7 — dry-run then production-ready)

| Scenario | Mechanism | Verified by |
|---|---|---|
| Dry-run mode | `run_publish_pipeline(dry_run=True)` — every arm's shared `BaseArm._dry_run_result()` short-circuits before any live API call | `tests/test_commercial_execution.py::TestRunPublishPipelineDryRun` |
| Production-ready mode | The exact same function, `dry_run=False` — proven with a real, mocked arm reaching the ledger | `tests/test_commercial_execution.py::TestRunPublishPipelineRealMode` |
| Internet outage / API timeout | `distributor.py`'s existing real-failure retry-enqueue, reflected honestly in the record's own `recovery_token`/`has_pending_retry` | `tests/test_commercial_execution.py::TestApiTimeoutRetry` |
| Power interruption / process crash | `factory_state.json`'s checkpoint mechanism — orchestrator-level, unchanged, already covered by the Unified Recovery System | Inherited, not re-tested here |
| Duplicate publish request | Each real attempt is its own honest, append-only `audit_trail` entry — never corrupts the ledger. Per-platform de-duplication (never a second real Paddle product for the same `production_id`) is `PaddleArm`'s own concern, already proven in `tests/test_paddle_arm.py` | `tests/test_commercial_execution.py::test_duplicate_publish_request_is_safely_recorded_not_corrupted` |

## Tests

- `tests/test_commercial_execution.py` — `resolve_target_arms`, `build_publish_record`, `check_approval_gates`, dry-run vs. real-mode pipeline runs, duplicate-publish safety, API-timeout retry tracing.
- `tests/test_orchestrator.py::TestPublishingEngineUsesTheUnifiedPipeline` — the orchestrator wiring.
- `tests/test_mission_control_api.py::test_commercial_execution_reports_real_approval_gates_and_ledger_history` — Mission Control's reporting.

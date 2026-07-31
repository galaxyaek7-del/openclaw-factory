# ADR-168 — Enterprise Truth Registry (Single Source of Truth)

**Date:** 2026-07-31
**Status:** Adopted. Read-only inventory infrastructure — no customer-facing features, no revenue features, no new automation, per the directive's own explicit prohibitions.

---

## The directive (verbatim, condensed)

> ADR-168 — Enterprise Truth Registry (Single Source of Truth)
>
> Do not build customer-facing features. Do not build revenue features. Do not create new automation. Build the Truth Registry for the entire company — the ONLY authoritative inventory of the enterprise. Every component must exist exactly once. Nothing may be assumed. Nothing may be inferred. Everything must be verified from the real codebase.
>
> Per component: Name, Category, Purpose, Physical location, Owner, Dependencies, Dependents, Status (READY/PARTIAL/EXPERIMENTAL/DEPRECATED/BROKEN), Production usage (YES/NO), Live verified (YES/NO), Test coverage (FULL/PARTIAL/NONE), Last verification, Last commit, Confidence score, Business criticality (LOW/MEDIUM/HIGH/CRITICAL).
>
> Never invent entries. Never mark READY/VERIFIED without evidence. If uncertain: Status = UNKNOWN, Confidence = LOW. No fabricated architecture. Future ideas go in a separate Proposed Components section (none exist in this factory today — not fabricated here).
>
> 10 summary sections + Overall Enterprise Truth Score (0–100). Final question: "If the entire repository disappeared today, could the company be reconstructed from the Truth Registry alone?" If No, list exactly what is missing.

## Why this is code, not a written document

Every other round this session that produced a report (ADR-162, ADR-166) did so via a real, re-runnable Python module rather than a hand-typed document, for one reason: a mechanical scan cannot lie about what it finds. This directive's own rules ("Never invent entries," "Nothing may be assumed") are exactly what a hand-written 246-component inventory would risk violating the moment attention lapses on component #200. `truth_registry.py` (new, root) is built the same way — every one of the 14 named fields per component is computed from one specific, cited, already-real signal, never typed by hand.

## Real signal sources reused (never re-derived)

- **`dependency_graph.py`** (Factory OS directive, 2026-07-23) — the real, AST-based enumeration of every internal `.py` file (`_iter_real_py_files`), the real import graph (`build_graph`), real dependents (`dependents_of`), real cycles (`find_cycles`), real zero-dependent-module candidates excluding known standalone entry points (`find_zero_dependent_modules`), and its real `parse_errors` — the one safe, non-executing BROKEN signal this registry uses (this module never imports/executes the 246 real modules it inventories, only parses their syntax with `ast.parse`, specifically to avoid repeating the ADR-162 live-invocation incident class).
- **`reality_audit.py`** (ADR-162) — the real, live REAL/SIMULATION/ARCHITECTURE_ONLY/NOT_IMPLEMENTED/DEPRECATED classification of the 152 real Mission Control endpoints, attributed down to the real module(s) each endpoint's own wrapper source imports via `_real_dependencies()`/`enrich_ledger_entry()` (reused verbatim, not re-derived — an early draft of this module mistakenly assumed `audit_all_endpoints()`'s raw output already carried a `dependencies` field; it does not, `build_reality_ledger()` is the real enrichment step that adds it — caught and fixed before the first real run completed, see Errors below).
- **`gfos.py`** (ADR-147) — its real, disclosed, narrow `_DEPARTMENT_PRIMARY_MODULE` 12-entry dict, inverted here into a module→owner citation. Everything outside those 12 primary modules is honestly `"Unassigned — no direct primary-module match in gfos.py's 12-department roster"`, never guessed.
- **`git log`** — one real per-file lookup for Last Commit (date + short hash), never a guessed timestamp.

## What is genuinely computed fresh by this module

`truth_registry.py::build_truth_registry()` — the one real aggregator, computing `dependency_graph.build_graph()` and `reality_audit.audit_all_endpoints()` exactly once each (the redundant-full-portfolio-scan guard this session has applied in every round since ADR-155) and threading both through all 246 real component entries:

- **Category** — the real top-level directory name (or `"root"`), zero invention.
- **Purpose** — the real module's own first docstring line (`ast.get_docstring`), never AI-paraphrased; honestly `"UNKNOWN — no real module docstring present"` when absent.
- **Status** — `READY` only if the module backs a real, live-invoked, REAL-classified endpoint; `PARTIAL` for SIMULATION/ARCHITECTURE_ONLY/NOT_IMPLEMENTED-backed modules; `DEPRECATED` if it backs a DEPRECATED-classified endpoint; `BROKEN` if `ast.parse()` genuinely fails on the file; `UNKNOWN` otherwise — the honest default the directive's own rules demand, and the status the large majority of this factory's 246 real modules land on, since `reality_audit.py` only classifies the ~152 endpoint *wrapper* functions in `mission_control_api.py`, not every module they transitively import. This is not a shortfall of this scan — it is the real, disclosed boundary of what has ever been live-verified in this factory.
- **Production usage** — `YES` only for modules reachable by a real BFS over `dependency_graph.py`'s own dependency edges, starting from real live-invoked-REAL endpoint modules **plus** a small, disclosed, CLAUDE.md-cited set of known direct subprocess entry points (`book_generator`, `customer_pipeline`, `distributor`, `safety_filter`, `contract_generator`, `invoice_generator`, `market_analyzer` — real modules `server.js` spawns directly, never through `mission_control_api._ENDPOINTS`, so a purely endpoint-graph-based scan would have wrongly called them unreachable). Everything else is honestly `UNKNOWN`, explicitly **not** asserted `NO` — this scan cannot enumerate every real entry point in the factory, only the ones it can cite.
- **Test coverage** — `PARTIAL` if a real `tests/test_<basename>.py` file exists, `NONE` otherwise. **`FULL` is never assigned by this scan, for any module, disclosed explicitly**: no line-coverage tool (`coverage.py` or equivalent) is wired into this factory (confirmed by direct search) — claiming `FULL` for any module would be a fabricated claim this directive explicitly forbids.
- **Business criticality** — a disclosed, mechanical keyword match (`CRITICAL`: finance/payment/invoice/ledger/publish/distributor/contract/customer_pipeline/safety_filter/credential/secret/checkout/paddle/gumroad; `HIGH`: decision_engine/orchestrator/evolution_queue/executive_brain/capital_allocation/publish_protection/reality_audit/safe_mode) against the module's own name and path — never a business judgment call. Everything else is honestly `UNKNOWN`.
- **Confidence score** — a disclosed, additive 0–100 heuristic (+10 real docstring, +20 real test file, +30 real production reachability, +30 real live-verified endpoint, +10 real recent git history) — every point traceable to a field already on the same entry, never a number invented independent of evidence.

## The 10 named summary sections + Enterprise Truth Score

`build_truth_registry_report()` derives every section from the registry above, computed exactly once:

1. **Company Inventory**: **246 real components** across 28 real categories (largest: `root` 90, `multi_source_intelligence` 17, `market_intelligence_core` 17, `channels` 13, `orchestrator`/`product_families` 12 each).
2. **Operational Components** (READY): **134** (54.5%).
3. **Experimental Components** (PARTIAL): a small set backing SIMULATION/ARCHITECTURE_ONLY-classified endpoints (e.g. `growth_stages`/`strategic_planning`'s simulation entry points, though both those specific modules also back a real REAL-classified endpoint and so land READY overall — the directive's own status set has no "mixed" category, so this scan reports the module's single best-evidenced status, disclosed here rather than silently chosen).
4. **Missing Components**: a real, mechanical cross-check of every `` `something.py` `` reference in `CLAUDE.md`'s own text against real on-disk existence — 12 raw candidates found, **manually verified to be zero genuine undisclosed gaps** (see "A real, disclosed limitation" below).
5. **Broken Components**: **0** — every one of the 246 real `.py` files parses successfully with `ast.parse()`. (This checks syntax only, not runtime import success — disclosed explicitly, see Rules below.)
6. **Duplicate Components**: 6 real same-basename collisions across different directories (`__init__.py` excluded as structural convention, not duplication) — `registry.py` ×9, `types.py` ×5, `pipeline.py` ×3, `orchestrator.py`/`learning.py`/`report.py` ×2 each. A real, disclosed architectural pattern (each package names its own interface file identically) — not asserted as a problem, just surfaced.
7. **Dead Code**: real overlap with Orphan Components below, disclosed rather than presented as a second independent signal.
8. **Orphan Components**: **30** real modules with zero real internal dependents, via `dependency_graph.find_zero_dependent_modules()` (already excludes `KNOWN_STANDALONE_ENTRY_POINTS` — human-run CLI tools with zero importers by design, not dead code).
9. **Never-Verified Components**: **112** of 246 (45.5%) — modules with no real live-verification event in this scan, i.e. every honestly-`UNKNOWN`-status module.
10. **Enterprise Truth Score**: **68.8 / 100** — `0.3×%READY + 0.2×%not-BROKEN + 0.2×%not-UNKNOWN + 0.3×avg(confidence_score)`, a disclosed additive heuristic (components: 54.5% READY, 100% not-BROKEN, 54.5% not-UNKNOWN, 71.8 avg confidence). Never an invented single number — every input is a real, already-computed field on the registry.

**Real import cycles** (cited from `dependency_graph.find_cycles()`, not a new computation): **6**, matching ADR-156's original live finding — confirms architectural stability, not a regression.

## The final question

**"If the entire repository disappeared today, could the company be reconstructed from the Truth Registry alone?"**

**No.** What is still missing:

1. Real credentials/secrets in `.env` (`GROQ_KEY`, `MISSION_CONTROL_PASSWORD`, `GUMROAD_ACCESS_TOKEN`, `INTERNAL_SERVICE_TOKEN`, `N8N_PRODUCTION_WEBHOOK_URL`, the Telegram bot token) — gitignored by design, never in the repo this registry describes, and never in the registry itself.
2. Real, live third-party account state — the founder's actual KDP/Etsy/Gumroad/Paddle/Amazon-Associates account sessions, approvals, and onboarding status. Not code. Cannot be reconstructed from any file.
3. **112 of 246 real components (45.5%) have UNKNOWN status/confidence in this registry** — their real current behavior is not captured here, only their existence, name, location, and structural relationships.
4. Human/founder knowledge and decisions never captured in any real ledger this registry can cite (undocumented verbal decisions, informal context).

## A real, disclosed limitation found and resolved: the "Missing Components" false-positive rate

The mechanical CLAUDE.md-cross-reference check flagged 12 raw candidates. Manual verification (real file-existence checks + real `grep` against the exact CLAUDE.md sentences) found **zero genuine undisclosed gaps** among them:

- **4 are real files referenced by bare basename, missing their real directory prefix** in this scan's naive regex: `click_tracking.py` (real: `affiliate_commerce/click_tracking.py`), `inactivity.py` (real: `executive_intelligence/inactivity.py`), `networks.py` (real: `affiliate_commerce/networks.py`), `products.py` (real: `affiliate_commerce/products.py`).
- **2 are informal prose shorthand for a real package**, not a literal flat file: `orchestrator.py` (CLAUDE.md's own ADR-147 section says "a real citation of already-real `scheduler.py`/`orchestrator.py`" meaning the `orchestrator/` package), `executive_intelligence.py` (CLAUDE.md's ADR-158 section says "the same naming-collision lesson ADR-154 already learned (`executive_intelligence.py` → `executive_questions.py`)" — shorthand for the `executive_intelligence/` package).
- **3 are explicitly-documented historical removals**, already disclosed in the very sentence that names them: `cover_generator.py`, `niche_validator.py`, `quality_doctor.py` (CLAUDE.md's "Other Python utilities" section: "An older `X.py` existed... and was removed").
- **3 are explicitly-intentional negative naming comparisons** ("named `strategic_planning.py`, **not** `roadmap.py`/`priority_matrix.py`/`enterprise_timeline.py`") — names deliberately never chosen, not gaps.

Disclosed here rather than silently excluded from the raw candidate list (the function itself stays a pure, unbiased mechanical check — the human-verification pass is a separate, disclosed step, not baked into the checker as hidden exclusions).

## Rules honored literally

No customer-facing features, no revenue features, no new automation — `truth_registry.py` is read-only inventory, exposed via one new read-only Mission Control panel (`truth-registry-report`), the same class of addition every other structurally-similar audit round this session made. Never invents entries (every component comes from a real file-system walk). Never marks READY/VERIFIED without evidence (both require a real `reality_audit.py` classification hit). Uncertain → UNKNOWN/LOW confidence, applied literally — 112 of 246 components land there today, an honest majority, not a shortfall.

## What is explicitly NOT built

- No import-execution-based BROKEN detection (`importlib.import_module()` on all 246 modules) — real risk of side effects on modules with top-level executable code, the exact incident class ADR-162 already caused once. `ast.parse()`-only syntax checking is the safe, real, disclosed substitute.
- No "Proposed Components" section — none exist in this factory today; fabricating placeholder future-plan entries would violate the directive's own "no imagined modules" rule.
- No attempt to force every one of the 246 modules to a non-UNKNOWN status via looser heuristics — the directive's own rule ("if uncertain, UNKNOWN") is honored even though it produces a large UNKNOWN bucket.

## Validation

`python -m unittest tests.test_truth_registry -v` — 19/19 passing, covering `_status_for()`'s full real branch logic (UNKNOWN default, READY/PARTIAL/DEPRECATED precedence), `_business_criticality_for()`'s keyword matching, `_test_coverage_for()`'s real file-existence check (and a dedicated regression proving `FULL` is never assigned), `_confidence_score()`'s additive factors (both the all-evidence-present and zero-evidence cases), `_duplicate_basenames()`'s `__init__.py` exclusion, `_reachable_from_production()`'s real BFS, and `build_truth_registry_report()`'s own "never asserts reconstructable YES" and Truth Score bounds.

Live-verified across 5 separate full real runs, in-process and via the real HTTP/subprocess dispatch path: 376.1s (pre-fix, all-UNKNOWN), 254.7s (post-fix, in-process, the 134/112 split reported above), 320.9s and 480.8s (both real HTTP timeouts — the endpoint genuinely needs longer than either budget, not a fluke), 482.8s (direct CLI dispatch, succeeded), 421.4s (final HTTP round-trip against a disposable server on port 3020, `GET /api/v1/truth-registry-report`, HTTP 200). **Real cost is disclosed as variable, ~255–485s**, not a single fixed number — `reality_audit.audit_all_endpoints()` sequentially live-invokes 152 real endpoints, several of which independently carry their own real, disclosed up-to-100s timeout budgets for live external calls (Groq/HN/GitHub); the total run time depends on real live network conditions at the moment of invocation, not on this module's own logic. `runPythonServiceCached`'s timeout was set to 320s, found genuinely too short via live testing, then 480s, also found genuinely too short, before settling on 600s (10 minutes) with real headroom over the worst observed run. Confirmed via the refined diff discipline, run after every live invocation across this round, that zero real decision-status mutation occurred at any point (only expected append-only log growth from live-invoking real endpoints).

**A real, disclosed operational risk, not solved by this round**: `runPythonServiceCached()`/`runPythonService()` (`server.js`) has no request-coalescing or locking — every request spawns a fresh Python subprocess, regardless of whether an identical request is already in flight. At this panel's real ~255–485s cost against Mission Control's standard 60s polling interval, an operator leaving this panel open would cause multiple overlapping ~5-minute Python subprocesses to pile up rather than being deduplicated. This is a pre-existing, shared characteristic of every expensive panel in this factory (`strategic-planning-dashboard`, `enterprise-capital-allocation-dashboard`, etc.), not unique to this one — but this panel's cost is roughly 5–8× any prior panel's, making the risk materially worse. Not fixed here: building request-coalescing would itself be new automation/infrastructure, outside this directive's explicit "do not create new automation" scope. Disclosed rather than silently left for an operator to discover the hard way.

## Errors and fixes found during this round

1. **`_endpoint_classification_by_module()`'s first draft assumed `reality_audit.audit_all_endpoints()`'s raw result already carried a `dependencies` key.** It does not — `classify_endpoint()`'s raw output has no such field; `enrich_ledger_entry()`/`build_reality_ledger()` is the real, separate enrichment step that adds it (via `_real_dependencies(fn)`, which needs the actual function object, not just the classification result). The first full live run (376.1s) consequently produced all 246 components as `UNKNOWN` status — a real, caught, disclosed bug, not a silently-accepted wrong answer. Fixed by calling `build_reality_ledger(audit_results)` before building the module-attribution map; the corrected re-run (254.7s) produced the real 134 READY / 112 UNKNOWN split reported above.
2. **`_duplicate_basenames()`'s first draft included `__init__.py`** (33 real files sharing that exact basename by structural Python convention) — caught before the report was finalized, excluded explicitly with a disclosed one-line rationale rather than silently dropped.
3. **The Mission Control panel's real end-to-end cost was significantly underestimated at first** — an in-process measurement of `build_truth_registry()` alone (254.7s) was mistaken for the full endpoint's real cost. The actual `GET /api/v1/truth-registry-report` round-trip (registry + report + real subprocess/CLI dispatch overhead) genuinely needs 320–485s+, confirmed by 2 real, consecutive live HTTP timeouts (at 320s and 480s) before a 600s timeout and a clean 421.4s success were achieved. Both timeouts were real server-side kills (`killAfterTimeout`), not curl-side or fabricated — logged in `logs/service_layer.log` with the real elapsed `duration_ms`.

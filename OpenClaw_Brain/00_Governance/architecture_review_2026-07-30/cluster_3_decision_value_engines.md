# Architecture Stability Review — Cluster 3: Decision, Value & Financial Engines

**Scope:** value_engine.py, profit_oracle.py, opportunity_pipeline.py, economics.py, portfolio_engine.py, investment_pipeline.py, capital_allocation_engine.py, growth_engine.py, decision_reopen.py, scheduler.py, strategic_intelligence_core.py, commercial_intelligence.py, decision_engine/ (6 files), strategic_intelligence/ (6 files), revenue_pipeline/ (2 files). Method: docstring + `grep "^def \|^class "` structure read for every file (not full-text reads of large files), real import-edge grep, and repo-wide caller grep before calling anything dead. Evidence cited inline.

**Cluster summary:** This is a deliberately *layered composition* architecture, not a duplicated one. `decision_engine/store.py::append_decision()` is verified the single real write path into `data/decisions.jsonl` (only caller chain: `decision_engine/engine.py` → `store.append_decision()`; every other file matching "decisions_path" in a repo-wide grep is either a read-only consumer passing the path through, or a test). Each higher-layer module (`opportunity_pipeline` → `investment_pipeline`/`value_engine`/`growth_engine`/`commercial_intelligence` → `portfolio_engine`/`capital_allocation_engine`/`strategic_intelligence_core`) explicitly documents, in its own docstring, exactly which fields it reuses verbatim vs. computes new — and in the two cases I independently verified in code (not just docstring claim), the reuse is real: `capital_allocation_engine.py:104` literally calls `strategic_intelligence_core.strategic_score()`; `portfolio_engine.py:182` literally calls `investment_pipeline.build_investment_pipeline_entry()`. The real risk in this cluster is not duplicate computation — it's **surface proliferation**: 9+ distinct Mission Control panels all answering some flavor of "what should we prioritize," which is a genuine cognitive-load/maintainability finding even though none of them recompute the same number twice.

---

### Decision Ledger Core
- **Files:** `decision_engine/store.py`, `decision_engine/engine.py`, `decision_engine/types.py`, `decision_engine/ranking.py`
- **Purpose:** The single real source of truth for every ACCEPTED/REJECTED/DEFERRED decision (ADR-076) and the one real append path into `data/decisions.jsonl`.
- **Inputs:** A decision record (niche, verdict, score components) from `market_hunter.py`/`opportunity_pipeline.py`/other decision-producing callers.
- **Outputs:** `data/decisions.jsonl` (append-only), `latest_decision_per_niche()`, `rank_all()`.
- **Dependencies:** Imported by nearly every other module in this cluster (verified: `opportunity_pipeline`, `value_engine`, `investment_pipeline`, `portfolio_engine` via `investment_pipeline`, `capital_allocation_engine` via `strategic_intelligence_core`, `growth_engine`, `scheduler` callers, `decision_reopen`). Zero real intra-repo imports of its own beyond stdlib.
- **Current maturity:** REAL/production — verified the ONLY real writer via repo-wide grep for `append_decision(`; all other matches are the 3 real call sites in `decision_engine/engine.py` or tests.
- **Business value:** Every downstream scoring/prioritization surface in this factory ultimately reads from here — this is the load-bearing foundation of the whole opportunity-evaluation pipeline.
- **Technical debt:** None found at this layer — small files (53-254 lines), single responsibility, no duplication.
- **Risk level:** LOW. Only real scalability note: `latest_decision_per_niche()`/`rank_all()` do a full linear scan of `decisions.jsonl` per call (confirmed via `read_events`-style pattern) — fine at current real volume (dozens of decisions), a real future risk only once this grows into the thousands with no index.
- **Recommendation:** **KEEP.** This is the cleanest, most disciplined module in the cluster — no changes needed.

### Commercial Scoring Foundation
- **Files:** `profit_oracle.py`, `economics.py`
- **Purpose:** `profit_oracle.py` — pre-build profit-potential scoring (0-100) across 4 weighted signal groups, the Constitution's Butter Principle gate. `economics.py` — single source of truth for unit economics (replaces a hardcoded price floor with config-driven math).
- **Inputs:** Niche/product parameters; `config/economics.json`.
- **Outputs:** Opportunity scores, price floors/margins consumed by nearly every other module in this cluster.
- **Dependencies:** `economics.py` is confirmed standalone (its own docstring: "zero imports from the rest of the factory") — verified true (only stdlib `sys`/`json` imports) — but has 5 REAL callers (`inspectors.py`, `market_memory.py`, `profit_oracle.py`, `revenue_pipeline/plan.py`, `schemas/product.py`), so "standalone" means clean dependency direction (a leaf/foundation module), not orphaned. `profit_oracle.py` has no intra-repo imports either (checked its import block) but is the single most-depended-upon module in the cluster.
- **Current maturity:** REAL/production, but `profit_oracle.py`'s own docstring is unusually explicit that several signals it's asked for (live Google Trends, real search volume, live competitor counts) have **no connected live data source** — it honestly falls back to (a) real saved `niche_reports/` data or (b) a disclosed, labeled heuristic, never a fabricated live call. This is a maturity/honesty strength, not a hidden gap.
- **Business value:** The literal gate that decides whether any product gets built at all (Constitution §16).
- **Technical debt:** `profit_oracle.py` is the largest file in this cluster — 1832 lines, 35 top-level functions. It has internal grouping (4 weighted signal groups per its own docstring) but a file this size is worth a maintainability flag even though I found no duplicate logic inside it via structural grep.
- **Risk level:** MEDIUM for `profit_oracle.py` on maintainability grounds alone (file size/function count — a change here has a large blast radius since almost everything else depends on it, directly or transitively). LOW for `economics.py` (small, isolated, config-driven).
- **Recommendation:** `profit_oracle.py`: **REFACTOR** (split its 4 signal groups into 4 cohesive sub-modules or at minimum clearly-delimited sections — not urgent, no bug evidence, purely a future-maintainability move given its central, high-blast-radius role). `economics.py`: **KEEP** as-is.

### Opportunity Ranking & Aggregation Layer
- **Files:** `opportunity_pipeline.py`, `investment_pipeline.py`, `commercial_intelligence.py`
- **Purpose:** Three real, non-competing views over the same ACCEPTED-decision substrate: `opportunity_pipeline.py` is the base ranked view (reuses `decision_engine.ranking.rank_all()`, `profit_oracle`, `market_intelligence_engine` — zero live network calls, its own docstring says "safe to run over the full real history in milliseconds"); `investment_pipeline.py` reuses 9 of its own 10 named ranking dimensions verbatim from `opportunity_pipeline.annotate_decision()`, adding exactly one genuinely new signal (`urgency`, a disclosed proxy from `market_alerts.py` severity — never a fabricated general urgency score); `commercial_intelligence.py` is pure aggregation (demand/WTP/competition/price/buying-behavior/opportunities), citing `opportunity_pipeline`, `market_evidence`, `profit_oracle`, `market_memory`, `growth_engine` — confirmed a real, small (116-line, 2-function) report-only module.
- **Inputs:** `data/decisions.jsonl` (via `decision_engine.ranking`), `market_alerts.py`, `market_evidence.py`.
- **Outputs:** Ranked opportunity lists, investment-pipeline entries, a commercial intelligence report.
- **Dependencies:** `opportunity_pipeline.py` imports `decision_engine.ranking`, `profit_oracle`, `business_dossier`, `executive_board`, `market_alerts`, `decision_reopen`. `investment_pipeline.py`/`commercial_intelligence.py` both build on `opportunity_pipeline.annotate_decision()`.
- **Current maturity:** REAL/production. `opportunity_pipeline.py`'s own docstring is explicit that "Time to MVP" has no real data source and reports it honestly as Unknown rather than guessing — same honesty discipline as `profit_oracle.py`.
- **Business value:** The real ranked backlog the founder actually reviews.
- **Technical debt:** None found beyond the surface-proliferation issue noted at cluster level (3 overlapping "ranked view" outputs, even though each is internally non-duplicative).
- **Risk level:** LOW individually. The real risk is at the aggregate cluster level (see Cross-cutting findings).
- **Recommendation:** **KEEP** all three — verified genuinely non-duplicative in computation, each serves a distinct real question (base ranking vs. investment framing vs. commercial-report framing). If anything is merged cluster-wide, `commercial_intelligence.py` (116 lines, pure aggregation, no unique computation of its own) is the best MERGE candidate — it could become a view/section inside `opportunity_pipeline.py`'s own report rather than a separate top-level module.

### Portfolio & Capital Allocation Layer
- **Files:** `portfolio_engine.py`, `capital_allocation_engine.py`
- **Purpose:** `portfolio_engine.py` classifies every ACCEPTED opportunity into 13 founder-named portfolio classes + 4 execution buckets, reusing `investment_pipeline.py`'s entry (verified real call at line 182) and `scheduler.decide_next_actions()` (verified real call at line 244). `capital_allocation_engine.py` computes a 14-dimension Investment Score, delegating 7 dimensions verbatim to `strategic_intelligence_core.strategic_score()` (verified real call at line 104) and adding 7 genuinely new ones sourced from `value_engine.compute_value_profile()`.
- **Inputs:** ACCEPTED decisions, `investment_pipeline` entries, `strategic_score()` output, `value_engine` dimensions.
- **Outputs:** Portfolio classification + NOW/NEXT/LATER/REJECT buckets; 14-dim Investment Score + opportunity-cost pairings.
- **Dependencies:** Both real, verified (not just docstring-claimed) consumers of upstream cluster modules — no evidence of a second, competing scoring pass in either.
- **Current maturity:** REAL/production. `portfolio_engine.py`'s own docstring honestly discloses 6 of its 13 founder-named classes have no distinct real product family in this factory today (never silently folded into an adjacent class). `capital_allocation_engine.py`'s sunk-cost protection is documented as structural (neither `profit_oracle.opportunity_score()` nor `value_engine.compute_value_profile()` accepts a cumulative-past-spend parameter) — verified this is an architectural property, not a runtime check that could be bypassed.
- **Business value:** Real resource-allocation guidance for the founder.
- **Technical debt:** None found — both are recent (2026-07-24, 2026-07-29), small (298/327 lines), and explicitly built via research-audit-first discipline.
- **Risk level:** LOW.
- **Recommendation:** **KEEP** both. They're the newest, most disciplined modules in the cluster and the reuse chains are verified real.

### Growth, Decision-Reopen & Scheduling
- **Files:** `growth_engine.py`, `decision_reopen.py`, `scheduler.py`
- **Purpose:** `growth_engine.py` — product multiplication/channel expansion/compounding candidates for validated winners, distinguishing market-validated (real closed sale) vs. intelligence-validated (ladder score only) — never presented as equally proven. `decision_reopen.py` — deterministic re-open trigger for the Executive Board, fired only by real Critical/2+High market alerts, never on a schedule (none exists) or speculation. `scheduler.py` — on-demand classification of ACCEPTED opportunities into 5 buckets (run_now/wait/accelerate/stop/cancel); explicitly never self-schedules (confirmed via `AskUserQuestion` per its own docstring, matching this factory's standing "no scheduler exists" architecture).
- **Inputs:** ACCEPTED decisions, `market_alerts.py`, `value_engine`, `product_families.registry`.
- **Outputs:** Growth candidates, reopen events, 5-bucket execution recommendations.
- **Dependencies:** `scheduler.decide_next_actions()` has 8 real, verified callers across the cluster and beyond (`capital_allocation_engine.py`, `ceo_decision_center.py`, `execution_status.py`, `master_loop.py`, `mission_control_api.py`, `portfolio_engine.py`) — genuinely load-bearing, not dead.
- **Current maturity:** REAL/production.
- **Business value:** Growth/expansion recommendations and the real "what to work on next" bucket classifier several other modules build on.
- **Technical debt:** `growth_engine.py` independently re-reads `decisions.jsonl` directly rather than exclusively going through `decision_engine.store`/`ranking` (confirmed via grep — it's one of only 2 modules in the whole cluster that opens the file itself, the other being `decision_engine/store.py` itself). Minor: a second real read-path exists, though not a second *write* path, so this is a low-severity duplication, not a data-integrity risk.
- **Risk level:** LOW-MEDIUM. **A real, previously-undocumented naming collision found**: `server.js`'s `scheduler-status` Mission Control panel (line 1124) refers to an entirely different concept — the Windows Scheduled Task `OpenClaw-WeeklyPublicReport` (ADR-119), queried live via `Get-ScheduledTask` — NOT `scheduler.py`'s opportunity-bucketing logic. A repo-wide grep for "scheduler" returns 33 hits in `server.js`/`mission_control_api.py` alone, and a new engineer cannot tell which "scheduler" is meant without opening the file. This is a real, confirmed maintainability risk (evidence: `server.js:1125`'s own description text is about a Windows Task, while `scheduler.py`'s docstring is about opportunity bucketing — two unrelated systems sharing one name).
- **Recommendation:** `growth_engine.py`/`decision_reopen.py`: **KEEP**. `scheduler.py`: **KEEP the logic, REFACTOR the name** — rename either `scheduler.py` (e.g. to `execution_bucketing.py` or `next_actions.py`) or the Mission Control `scheduler-status` panel (e.g. `weekly-report-task-status`) to remove the collision. Low effort, real clarity win, zero behavior change.

### Strategic Intelligence Core & Sub-package
- **Files:** `strategic_intelligence_core.py`, `strategic_intelligence/` (`bottleneck_effort.py`, `channel_value.py`, `decision_patterns.py`, `rejection_patterns.py`, `report.py`, `technical_debt.py`)
- **Purpose:** `strategic_intelligence_core.py` is the "Executive Brain" citation layer (11-dim Strategic Score, Executive Brief, multi-year horizons) — its own docstring states a field-by-field audit found most of its ask already answered by `ceo_decision_center.py`, `value_engine.py`, `scheduler.py`. The `strategic_intelligence/` package (all small, 31-89 lines each, single-function-per-file) provides narrow, real analytical primitives (bottleneck effort, channel value, decision patterns, rejection patterns, technical debt) that `strategic_intelligence_core.py` and others cite.
- **Inputs:** `decisions.jsonl`, `ceo_decision_center`, `value_engine`, `scheduler`.
- **Outputs:** Strategic Score (11 dims), Executive Brief, multi-year horizon report.
- **Dependencies:** Confirmed thin, well-factored sub-package — each file does one thing, no internal duplication found.
- **Current maturity:** REAL for the sub-package primitives; `strategic_intelligence_core.py` itself is explicitly a citation/synthesis layer over other real modules, honestly reporting horizons as "NOT ENOUGH EVIDENCE" rather than projecting (per its own docstring, consistent with this factory's stated no-fabrication discipline).
- **Business value:** The "top-level decision layer" the founder's own directive asked for, built via reuse rather than a competing scoring engine.
- **Technical debt:** None found — this is a model example of the "citation layer, not a second judgment engine" pattern this whole cluster mostly follows well.
- **Risk level:** LOW.
- **Recommendation:** **KEEP** as-is. The `strategic_intelligence/` sub-package is exactly the right granularity — small, single-purpose files, no reason to merge or split further.

### Revenue Pipeline
- **Files:** `revenue_pipeline/pipeline.py`, `revenue_pipeline/plan.py`
- **Purpose:** Real cost/ROI/ladder-comparison functions cited directly by `value_engine.py` (confirmed in `value_engine.py`'s own docstring: "reuses... `revenue_pipeline/plan.py`'s real cost/ROI/ladder-comparison functions").
- **Inputs:** Decision/ladder data.
- **Outputs:** Cost/ROI comparisons consumed by `value_engine.py`.
- **Dependencies:** `revenue_pipeline/plan.py` imports `economics.py` (confirmed in economics.py's own caller list).
- **Current maturity:** REAL — small (175-250 lines), genuinely load-bearing (cited by `value_engine.py`, the cluster's top synthesis layer).
- **Business value:** Feeds the Priority Score/Expected ROI fields the Executive Board actually sees.
- **Technical debt:** None found.
- **Risk level:** LOW.
- **Recommendation:** **KEEP.**

---

## Cross-cutting findings

**Duplicate responsibilities:** None found at the computation level — every layered module I checked either has zero intra-repo imports (foundation layer: `economics.py`, `profit_oracle.py`) or verifiably delegates to a real upstream function rather than recomputing (spot-checked `capital_allocation_engine.py`→`strategic_score()` and `portfolio_engine.py`→`investment_pipeline`, both real in code, not just docstring claims). The apparent duplication is at the **view/surface level**, not the computation level — see "Unnecessary complexity" below.

**Overlapping logic:** `growth_engine.py` independently re-reads `decisions.jsonl` rather than going exclusively through `decision_engine.store`/`ranking` — a second real read-path (not write-path) into the same file. Low severity, but inconsistent with the rest of the cluster's discipline.

**Dead code:** None found in this cluster. Every module I checked has real, repo-wide-grep-verified callers (`scheduler.py`: 8 real callers across `capital_allocation_engine.py`/`ceo_decision_center.py`/`execution_status.py`/`master_loop.py`/`mission_control_api.py`/`portfolio_engine.py`; `economics.py`: 5 real callers despite "standalone" framing referring only to its own import direction).

**Obsolete modules:** None found — every file in this cluster carries a 2026-07-2x date and an explicit "checked against real existing intelligence before writing" audit note in its own docstring; none read as legacy/superseded.

**Architectural bottlenecks:** `decision_engine/store.py`'s `latest_decision_per_niche()`/`rank_all()` do a full linear scan of `decisions.jsonl` per call — fine today, a real future scaling concern once decision volume grows into the thousands (currently dozens).

**Scalability risks:** Same as above — no indexing/caching layer over `decisions.jsonl`/`sales_ledger.jsonl` reads; every cluster module that needs decision data re-triggers a fresh full-file parse rather than sharing one cached pass per request. Not urgent at current real data volume.

**Maintainability risks:** (1) `profit_oracle.py` at 1832 lines/35 functions is the highest-blast-radius file in the cluster — almost everything downstream depends on it, directly or transitively. (2) The "scheduler" naming collision documented above (`scheduler.py` vs. `server.js`'s Windows-Task `scheduler-status` panel) is a real, confirmed source of confusion for anyone grepping the codebase. (3) **Surface proliferation**: 9+ distinct Mission Control panels answer overlapping "what matters most" questions (`opportunity-queue`, `unified-priorities`, `opportunity-pipeline`, `executive-score`, `global-opportunity-exchange`, `investment-score`, `get-investment-pipeline(-entry)`, `get-portfolio-entry`/`get-portfolio-report`, `get-company-reality-score`) — each is internally non-duplicative (verified), but a founder or new engineer has no single obvious place to look for "priority," and onboarding cost scales with panel count regardless of whether the underlying math is DRY.

**Security risks:** None found specific to this cluster — no user input reaches a filesystem path, shell command, or SQL/query string anywhere in these modules (all inputs are internal niche/decision identifiers already validated upstream). `profit_oracle.py`'s explicit refusal to fabricate live data when a real source is missing (honestly labels heuristics in its `reasoning` field) is a positive integrity control worth naming, not a risk.

**Unnecessary complexity / simplification opportunities:** The single highest-leverage simplification in this cluster is consolidating the "prioritization surface" list above into fewer Mission Control panels — not by deleting computation (all of it is real and distinct), but by presenting `opportunity_pipeline`/`investment_pipeline`/`portfolio_engine`/`capital_allocation_engine`/`strategic_intelligence_core`'s outputs as sections of 2-3 panels instead of 9+. `commercial_intelligence.py` (116 lines, pure aggregation, zero unique computation) is the clearest literal-MERGE candidate — folding it into `opportunity_pipeline.py`'s own report would remove one full file/import-surface for zero loss of real functionality.

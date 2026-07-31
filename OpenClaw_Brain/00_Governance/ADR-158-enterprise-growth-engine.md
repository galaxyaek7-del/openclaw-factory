# ADR-158 — Enterprise Growth Engine

**Date:** 2026-07-31
**Status:** Adopted. Real, additive, citation-heavy company-wide Growth Stage classification + Executive Growth Dashboard + Simulation Mode integration built.

---

## The directive (verbatim)

> Founder Directive — Enterprise Growth Engine
>
> The Autonomous Runtime now exists.
>
> The next objective is NOT another business division.
>
> Build the Enterprise Growth Engine.
>
> This becomes the company's strategic evolution layer.
>
> Objectives:
>
> 1. Define measurable Growth Stages (Stage 0 — Bootstrap, Stage 1 — Validation, Stage 2 — Stable Revenue, Stage 3 — Expansion, Stage 4 — Multi-market, Stage 5 — Autonomous Enterprise).
>
> 2. Every stage must have REAL entry conditions (minimum recurring revenue, minimum cash reserve, production stability, quality score, infrastructure readiness, automation coverage, affiliate network readiness, digital products maturity).
>
> 3. Every stage also has exit conditions — if health deteriorates, the company automatically falls back.
>
> 4. Every division receives stage-specific objectives (Affiliate Commerce, Digital Products, Publishing, Research, Infrastructure, Operations, Executive).
>
> 5. Build Executive Growth Dashboard (current stage, reason, remaining requirements, estimated readiness, blocking factors).
>
> 6. Every recommendation must be explainable — no black-box decisions.
>
> 7. Simulation Mode must simulate stage progression without affecting production.
>
> 8. Mission Control becomes capable of answering: Why are we still in Stage X? What blocks Stage Y? What is the highest ROI action to reach the next stage?
>
> Rules: Reuse existing systems. No duplicated logic. No fabricated readiness metrics. Everything derived from real company state. ADR + tests + documentation required.

## Research before writing any code

- **Naming collision avoided.** A real, unrelated `growth_engine.py` already exists in this factory (2026-07-24) — per-niche Product Multiplication, Channel Expansion, `portfolio_growth_summary()`, `growth_forecast()`. This directive's concept — a company-wide maturity stage — is a genuinely different thing. The new module is named `growth_stages.py`, exactly the same collision-avoidance lesson ADR-154 already learned the hard way (`executive_intelligence.py` → renamed `executive_questions.py`).
- **No pre-existing "growth stage"/"company maturity stage" concept anywhere** (confirmed via repo-wide grep). Genuinely new organizing structure — but nearly every signal it needs to cite already exists: `channels/ledger.py::revenue_trend()` (recurring revenue, real, currently $0), `resilience_monitor.assess_resilience()` (production stability), `executive_score.py::_production_quality()` (quality score), `autonomous_operations_status.py` (automation coverage), `launch_readiness.py::launch_readiness_score()` (affiliate/digital-products readiness, ADR-153), `capital_allocation_engine.py`/`enterprise_executive_brain.py::enterprise_scheduler()` (highest-ROI action, ADR-139/156), `global_opportunity_exchange.py::revenue_distribution()`/`country_dependency_note()` (multi-market signals, ADR-140), `config/reality.json` (the real ground-truth `published_books` gate).
- **Cash reserve: confirmed zero real signal anywhere** in this factory (grepped `cash_reserve|runway|treasury` — zero hits, same disclosed-gap class as ADR-146's MRR/ARR/Runway tiles). Honestly `NOT_ARCHITECTED`, never invented.
- **7 named divisions map onto real modules** (confirmed via `department_events.VALID_DEPARTMENTS` + `gfos._DEPARTMENT_PRIMARY_MODULE`, ADR-147): Affiliate Commerce→`affiliate_commerce/`, Digital Products→`book_generator.py`/production, Publishing→`distributor.py`, Research→`research_department`, Infrastructure→`infrastructure_bridge`, Operations→`enterprise_operations.py` (ADR-155), Executive→`executive_brain.py`/`executive_questions.py`.

## The policy question, resolved without a fresh AskUserQuestion

Objective 3 — "if health deteriorates, the company automatically falls back" — reads, on first pass, like it could conflict with the standing principle `company_runtime.py::company_state()` (ADR-157, built hours earlier the same day) established: a status label must be read-only/informational, recomputed fresh every call, and never itself trigger a behavior change anywhere else in this factory.

This was resolved by direct application of that same-day precedent rather than re-litigating it via a fresh `AskUserQuestion`: **"automatic fallback" is implemented as non-caching, non-sticky recomputation.** `growth_stages.current_growth_stage()` stores nothing and reads nothing back — it is a pure function of (real current signals, optional Simulation Mode overrides). A degraded real signal (e.g. an incident opens, revenue drops to zero) simply produces a lower stage on the *next* call. This literally satisfies "automatically falls back" without any triggered action, side effect, or new automation path — the exact same resolution `company_state()` already used for its own "state machine" framing.

## Stage 5 is a policy citation, not a data threshold

Reaching Stage 5 (Autonomous Enterprise) would require lifting one or more of the 4 standing founder-protected gates this factory has reconfirmed unchanged in every relevant round today: `evolution_queue.py`'s Execute step (ADR-133), `capital_allocation_engine.py`'s capital reallocation (ADR-139), business retirement (no real system exists, by design), and `channels/publish_protection.py`'s new-channel/elevated-risk publish gate (ADR-135) — reconfirmed as-is in ADR-142/144/147/157. `growth_stages.py`'s Stage 5 condition (`founder_protected_gates_lifted`) always reports `met: False`, always citing all 4 gates by name, and this module never attempts to lift any of them itself. A real, correct citation of standing policy — never a fabricated numeric gate standing in for a founder decision.

## What was built

**`growth_stages.py`** (new, root):

- `STAGES` (6 named stages) / `DIVISIONS` (7 named divisions, mapped to real modules) / `PROTECTED_GATES` (the 4 standing gates, cited verbatim).
- `_real_signals(overrides=None)` — fetches every real signal this module's conditions need, each exactly once, honoring any Simulation Mode override per-key so an overridden key never triggers its real (possibly expensive) lookup.
- `_stage_conditions(stage, signals)` — per-stage, per-condition real evaluation. Booleans are used only where a natural real threshold exists (≥1 real ACCEPTED decision, ≥1 real production run, zero open critical incidents, ≥1 fully launch-ready division, ≥2 platforms with real revenue). Where no real founder-set policy threshold exists anywhere (minimum revenue dollar figure, minimum cash reserve, minimum automation %, minimum quality %), the condition is honestly `met: None` / `NOT_ARCHITECTED` — the current real value is still shown for transparency, but never silently treated as a pass or a fail.
- `current_growth_stage(overrides=None)` — the core, stateless, non-cached classifier. Computes and discloses **every** stage's conditions regardless of where advancement stops (Objective 6's "no black-box decisions" — you can always see exactly why Stage 4/5 would also fail, not just the first blocker), while `reached` itself stops at the first stage with a genuinely `met: False` condition.
- `remaining_requirements_for_next_stage()` / `blocking_factors()` — derived from the same condition list, split into real blockers (`met: False`) vs. undetermined ones (`met: None`, no policy threshold set).
- `division_stage_objectives(division=None, stage=None)` — a static, disclosed guidance template (same convention as `growth_engine.py::_PREMIUM_CATEGORY_FAMILY` / `execution_status.py::_OWNER_BY_STAGE`) — one real, short, founder-legible line per (division × stage), explicitly labeled "founder-authored strategic guidance template, not AI-generated per-cycle." Executive's own Stage 5 line is the one division objective that is real today: keep the 4 protected gates exactly as they are unless the founder explicitly says otherwise.
- `highest_roi_action_to_advance(scheduler_result=None)` — pure citation of `enterprise_executive_brain.py::enterprise_scheduler()`'s real `ranked_by_roi` (itself a pure citation of `capital_allocation_engine.py`, ADR-139/156) — never a second, competing ranking algorithm.
- `build_growth_dashboard(overrides=None)` — the one real aggregator (Objective 5): current stage + reason, remaining requirements, blocking factors, estimated readiness % (gradable conditions only — `NOT_ARCHITECTED` conditions are excluded from the denominator and disclosed separately, never silently counted as failing), per-division objectives, highest-ROI action. Computes each expensive real sub-scan exactly once — same redundant-computation discipline `company_pulse()` (ADR-155) and `enterprise_scheduler()` (ADR-156) already established.
- `answer_growth_questions(dashboard=None)` (Objective 8) — literally answers the directive's 3 named Mission Control questions by citing the dashboard's own fields, same convention as `executive_questions.py::answer_strategic_questions()` (ADR-154).
- `simulate_stage_progression(**hypothetical)` (Objective 7) — the Simulation Mode hook: recomputes the dashboard against hypothetical overrides, tags the result with `simulation_mode.SIMULATION_TAG` via `simulation_mode.tag_simulated()` (ADR-153's existing framework, reused verbatim). Writes nothing to disk — a stateless what-if, lighter than `affiliate_commerce/simulation.py`'s event ledger since there is no transaction sequence to replay later. Unknown override keys are rejected explicitly rather than silently ignored.

**Mission Control**: `growth-stage-status` (`SERVICE_REGISTRY`, no-input, 60s timeout — measured live ~30s, same cost class as `enterprise-scheduler`) dispatches the dashboard + answered questions; `simulate-growth-stage-progression` (`ACTION_REGISTRY`, async, accepts any subset of the 8 known override keys) dispatches the simulation. One new panel in `mission_control_executive_v1.html`'s existing Executive Overview group, next to `company-state` — no new top-level group, per this session's own established "don't proliferate panels" finding (ADR-146/147).

## Real, disclosed current finding

Verified live against real factory data: `current_growth_stage()` returns **Stage 1 — Validation** today (3 real ACCEPTED decisions, 4,402 real production runs in `books/_generation_log.jsonl` — both Stage 1 conditions met; Stage 2 blocked by `positive_recurring_revenue` being `False`, since `channels/ledger.py::revenue_trend()` reports $0 real revenue). A real, honest finding — not a failure of this module, the correct reflection of this factory's real current commercial state. Stage 4's `country_diversification` condition is permanently `met: False` by design (the founder's own 2026-07-23 deferral, cited structurally, never re-litigated here) — meaning Stage 4/5 are currently unreachable regardless of revenue, which is itself an honest, correct disclosure rather than a bug.

## What is explicitly NOT built

No growth-stage persistence/history table — the stage is a pure function of current real state, never a stored/tracked value, same precedent as `company_state()`. No automatic action triggered by a stage change (no auto-pause, no auto-reallocation, no auto-anything) — Stage 5's 4 gates stay exactly as founder-only as every prior round left them. No fabricated dollar thresholds for the revenue/cash-reserve/automation-%/quality-% conditions that have no real founder-set policy value yet — each is honestly `NOT_ARCHITECTED`, current value still shown for transparency.

## Validation

`python -m unittest tests.test_growth_stages -v` — 17/17 passing, including: real current state never fabricates a high stage; `current_growth_stage()` is proven non-cached (two calls, two different override sets, two different stages); Stage 5 always cites all 4 protected gates; every condition either has a real `met` bool + source or is honestly `NOT_ARCHITECTED`, never a silently-invented threshold; `division_stage_objectives()` covers all 7 named divisions × 6 stages; `simulate_stage_progression()` proven to write nothing to `data/` (before/after mtime + file-list diff); `highest_roi_action_to_advance()` proven to match `enterprise_scheduler()`'s real ranked list exactly, no second ranking algorithm. Live CLI-verified against real production data. Full test suite re-run.

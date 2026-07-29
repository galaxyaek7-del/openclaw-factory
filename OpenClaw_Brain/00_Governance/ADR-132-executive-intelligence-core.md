# ADR-132 — Executive Intelligence Core (CEO Brain)

**Date:** 2026-07-29
**Status:** Adopted.

---

## The directive

The founder issued "PHASE NEXT — EXECUTIVE INTELLIGENCE CORE (CEO BRAIN)": a permanent Executive Intelligence Layer that evaluates every action before execution (business value, customer value, risk, financial/reputation/security impact, legal/ethical compliance, long-term strategic value), asks 8 named "executive questions" before every major operation, runs a Self Evolution Engine analyzing 10 real signals to generate improvement proposals, builds institutional Company Memory, and produces an Executive Score plus 10 named sub-scores — all in Mission Control, with an explicit "no fake automation" rule.

## What was found before building anything

Three parallel research agents audited the existing codebase against every piece of this directive, reading real source files end to end (not doc summaries). Verdict: the pre-action evaluation gate the directive describes was **already ~100% real**, built and ADR-documented between 2026-07-13 and 2026-07-25 — `executive_quality_gate.py` (20 real criteria), `decision_engine.evaluate_and_decide()`, ADR-121/122/126 (Proof of Payment, Strategic Doctrine v2's 4 conditions, the Product Strategy's 10 conditions), ADR-127/128 (Evidence Completeness Engine, Evidence Network), `enterprise_readiness.py` (legal/security/privacy hard-reject checks), and `ai_capability/registry.py` (security/maintainability/customer_value/business_impact metrics for AI tooling choices). Building a second, parallel gate would have recreated the exact anti-pattern this codebase has explicitly and repeatedly refused (competing decision gates, fabricated composite scores — `SERVICE_LAYER_API.md`'s own standing rule: real signals "never merged into one fabricated composite score").

## The 8 executive questions → real mechanism

| # | Executive question | Real mechanism (file:function) |
|---|---|---|
| 1 | Good for the customer? | `executive_quality_gate.py: check_customer_pain_evidence, check_willingness_to_pay, check_customer_retention_potential`; `executive_board.py: analyze_as_cco()` |
| 2 | Damages reputation? | `executive_quality_gate.py: check_brand_reputation_risk()` — hard `REJECT_IF_FAIL` |
| 3 | Long-term value increase? | `value_engine.py: compute_value_profile()`; ADR-122's condition 4 / ADR-126's condition 7, both hard gates in `profit_oracle.ladder_opportunity_score()`; `executive_quality_gate.py: check_long_term_strategic_value()` |
| 4 | Can it damage trust? | `executive_board.py: build_strategic_brief()`'s `customer_trust_impact` lens; `enterprise_readiness.py: compute_trust_score()` |
| 5 | Creates technical debt? | `strategic_intelligence/technical_debt.py: components_at_risk_of_technical_debt()`, folded into `evolution_engine.py` |
| 6 | Creates security debt? | `executive_quality_gate.py`/`enterprise_readiness.py: review_security()` (real deterministic insecure-practice scan, disclosed as a proxy, not a real security review); `ai_capability/registry.py`'s `security` metric |
| 7 | Becomes hard to maintain? | `enterprise_readiness.py: review_maintenance()`; `executive_quality_gate.py: check_delivery_capability/check_infrastructure_readiness`; `ai_capability/registry.py`'s `maintainability` metric |
| 8 | Can it be improved? | `evolution_engine.py: build_evolution_report()` — bottlenecks, technical debt, high-ROI opportunities, capability gaps, tool proposals in one report |

No new code was needed for this half of the directive — only this permanent record of the mapping, so it's citable going forward instead of only existing in one session's research.

## What was actually built (the real, confirmed gaps)

**Round 1 — Complete the daily-report set.** `evolution_report` and `self_awareness`/`GROWTH_LOG.md` were already wired into `factory_loop.js`'s real tick, running automatically once per calendar day (a direct code read found this, correcting an initial research pass that missed it). `ai_doctor.py` and `department_health.py` had the identical real shape (`render_markdown()` + a `mission_control_api.py` dispatch command) but were never wired the same way — two new functions (`maybeGenerateDailyAiDoctorReport`, `maybeGenerateDailyDepartmentHealthReport`) copy the existing `maybeGenerateDailyEvolutionReport` template exactly, now also running daily.

**Round 2 — Dynamic proposal generation.** `tool_intelligence/proposals.py::list_proposals()` used to return only 3 hand-written entries, unchanged since 2026-07-19 — real and evidence-cited when written, but static. It now also computes fresh proposals at call time from the same real bottleneck/technical-debt/capability-gap signals `evolution_engine.py` already assembles, honestly returning zero dynamic proposals when nothing real is detected — never padded.

**Round 3 — Pattern aggregators.** `data/support_tickets.jsonl` was write-only (zero reader anywhere) — `lib/dashboard_data.js::readSupportTicketSummary()` closes that, honestly empty today (zero real customer traffic). `readFailedJobsSummary()` gained real `by_step` grouping on top of its existing raw tally.

**Round 4 — Weak-department ranking.** `department_health.py::rank_department_weakness()` — three honest buckets (`no_data`, `below_threshold`, `healthy`), reusing the exact real failure-rate threshold `executive_intelligence.bottlenecks` already uses. Deliberately never a single blended department score (the module's own pre-existing docstring already establishes why: no common unit across department fields).

**Round 5 — Company memory linking.** Company memory was 4 disconnected real systems (`knowledge_brain.js` grep-retrieval, `knowledge_graph/build.py` structured decisions/production/sales, `data/decisions.jsonl` reasoning text, hand-written `19_Lessons_Learned/`+ADRs). `knowledge_graph/build.py` gained real `Lesson`/`ADR` node types, mechanically parsed from real filenames + first markdown heading — no semantic linking attempted (disclosed non-goal, needs embeddings infrastructure this factory doesn't have).

**Round 6 — Executive Score.** `executive_score.py` (new): Trust, Production Quality, Technical Debt, Security Health, Delivery Quality, Automation, Growth, Architecture Health — each a real number from an existing real function, or an honest `"Unknown"` with the real reason stated (Architecture Health is always Unknown — `ai_doctor.py` already declined to build real drift detection). `server.js`'s `executiveScoreService()` merges in the two JS-native sub-scores (Operational Stability from the same `computeHealthStatus()` every other health surface trusts; Customer Happiness from real review data) and computes `overall` as a transparent average of only the real (non-Unknown) sub-scores, with the Unknown count always disclosed alongside it. **Never wired into any accept/reject/production gate** — a new informational-only Mission Control panel, reusing the existing generic panel rendering.

**Housekeeping (Round 7).** `quality_doctor.py` — confirmed fake (`health_score = 100 - len(issues)*15`, no real check behind any `_check_*()`), already disclosed via a `warning` field, zero real callers — removed, directly following this same directive's own "no fake metrics" rule.

## Validation

New/updated tests: `tests/test_tool_intelligence.py` (+4, dynamic proposal generation), `tests/test_dashboard_data.js` (+4, support tickets + failure grouping), `tests/test_department_health.py` (+5, weakness ranking), `tests/test_knowledge_graph.py` (+5, Lesson/ADR nodes, +1 existing test fixed), `tests/test_executive_score.py` (new, 20 tests), `tests/test_factory_loop_daily_ai_doctor_report.js` / `tests/test_factory_loop_daily_department_health_report.js` (new, 3 each). Every new Python test mocks/injects the underlying real functions it composes — no live network/subprocess calls. Full regression (`tests/test_api_contract.js`, `tests/test_mission_control_api.py`, `tests/test_evolution_engine.py`, `tests/test_ai_doctor.py`) re-run clean after every round, zero regressions.

Live E2E: every new daily-report function, the dynamic proposal generator, and the Executive Score panel were run directly against real factory data (not just unit tests) — real dated report files written to `reports/`, a real live Executive Score computed and served through the authenticated `/api/v1/executive-score` endpoint.

## What's still honestly Unknown

Architecture Health has no real signal today and is not expected to gain one soon — `ai_doctor.py`'s own prior reasoning (no architecture baseline exists to diff against, and building one now risks exactly the fabrication `quality_doctor.py` was the cautionary tale for) still applies. Growth stays Unknown until at least 2 real, comparable sales windows exist (`growth_engine.py`'s own pre-existing gate — zero real sales exist today). Customer Happiness stays Unknown until a real review exists. None of these are treated as 0 in the Executive Score's overall average — they're excluded from it, with the exclusion count always shown.

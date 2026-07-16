# n8n Integration Gap — Verification Report

**Date:** 2026-07-16
**Directive:** "Executive Directive — Fix the n8n integration gap."
**Full governance record:** `OpenClaw_Brain/00_Governance/ADR-061-n8n-integration-gap-audit.md`

## 1. Audit findings

A full re-audit of every real n8n touchpoint (not an assumption from stale docs) found:

- **`FACTORY_STATUS.md` §6 was wrong.** It claimed the Sensing Engine workflow's HTTP Request node was still missing and `OPPORTUNITIES.md` "stays empty." Both were false: `BLOCKERS.md` #1's own `ADR-045` note already says `Openclaw_Sensing_Engine`/`02_Sales_Poll` were "untouched, remain exactly as they were" — i.e. never needed a fix — and `OPPORTUNITIES.md` contains a real entry (`[2026-07-15T06:40:04.543Z] what is a monsoon — نجحت كل فحوصات الجودة`) whose exact reason string and timestamp format are only produced by `server.js`'s `/api/trends` → `runQualityGate()` path. **Fixed** (`FACTORY_STATUS.md`, this commit).
- **Mission Control's automation view only showed 2 of 4 real workflows** — `00_CEO` and `01_Market_Scout` (the two re-exported after their fixes); `Openclaw_Sensing_Engine` and `02_Sales_Poll` were invisible to it, despite being just as real. **Fixed** (`mission_control_api.py`'s `_automation()`).
- **Zero n8n touchpoint existed for the Production step.** Confirmed by grep: no reference to n8n/port 5678 anywhere in `production_factory/`, `revenue_pipeline/`, `decision_engine/`, or `orchestrator/`. The chain `Market Intelligence → Decision Engine → Production → n8n → Status Reporting` had a real, structural gap at exactly one link. **Fixed** (`lib/n8n_notify.js` + wiring in `server.js`'s `start-production-pipeline` action).
- **Workflow activation remains genuinely blocked** — confirmed again, unchanged from `ADR-045`: n8n's `--activeState=fromJson` CLI flag errors outside queue/multi-main mode, and the REST API still returns `401 Unauthorized` (re-confirmed via direct request this session). This is a real platform limitation requiring the founder's browser login at `http://localhost:5678`, not a code gap.

## 2. What was built

| Component | File | Purpose |
|---|---|---|
| `notifyN8nProductionEvent()` | `lib/n8n_notify.js` (new) | Safe, opt-in, fire-and-forget POST to `N8N_PRODUCTION_WEBHOOK_URL` after a real production dossier completes. No-ops with no URL configured; never throws; every attempt logged. |
| `buildProductionNotifyPayload()` | `lib/n8n_notify.js` (new) | Pure field projection from a real `production_factory` dossier to the notify payload — no new business logic. |
| Wiring | `server.js`'s `startProductionPipelineAction()` | Calls the above for every dossier once `run_production_factory()` completes, fire-and-forget. |
| `03_Production_Notify.prepared.json` | `n8n_workflows/` (new) | Receiving-side workflow (Webhook → Set node extracting fields). **Prepared, not imported** — importing requires the same stop-the-live-process step `ADR-045` used, which needs explicit per-operation authorization, not a standing one. |
| Richer `_automation()` | `mission_control_api.py` | Now reports all 4 real workflows (2 from current `.fixed.json` exports, 2 from the dated backup, each labeled with `source_kind` so the distinction is never blurred) plus `trends_pipeline_evidence` (the real proof described above). |

## 3. Regression tests

- `tests/test_n8n_notify.js` (new, 8 tests): no-URL no-op, successful POST, non-2xx response, network error, timeout, payload fidelity, and `buildProductionNotifyPayload` field projection (including missing-field degradation) — all via a mocked `global.fetch`, no real network calls.
- `tests/test_mission_control_api.py` (+5 tests): all 4 real workflows reported, `source_kind` correctly distinguishes current vs. backup, real trends-pipeline evidence surfaced, and `_find_trends_pipeline_evidence()` correctly ignores `market_hunter.py`-sourced entries and handles a missing file honestly.

**Full suite result:** 405/405 Python tests, 45/45 JS unit tests (`test_metrics.js` + `test_dashboard_data.js` + `test_n8n_notify.js`), 44/44 `test_factory_loop_golden.js`.

## 4. Live end-to-end verification

Performed against a throwaway server instance (port 3099) — the real server (port 3000) and the real, already-running background processes (including the actual n8n instance, port 5678) were never touched or restarted.

1. **`GET /api/v1/automation-status`** — confirmed live: returns all 4 real workflows with correct `source_kind` labels and the real `trends_pipeline_evidence` (count 3, most recent = the 2026-07-15 entry).
2. **Safe no-op with real data**: with `N8N_PRODUCTION_WEBHOOK_URL` pointed at a local mock listener, triggered `start-production-pipeline` against today's real decision queue (0 ACCEPTED opportunities). Result: `processed: 0`, and — correctly — the mock listener received nothing. Proves the pipeline never wastes a call when there is nothing to report.
3. **Full wiring proof with a synthetic fixture**: since fabricating a real ACCEPTED opportunity to force a live dossier would mean inventing business data (not acceptable), the exact shared module server.js's action calls (`lib/n8n_notify.js`) was exercised directly with a clearly-labeled synthetic dossier (`niche: "[SYNTHETIC TEST FIXTURE — not a real opportunity]"`). Result: the mock listener received the exact expected JSON payload, and the call was logged as `succeeded` with a real status code and duration. This proves the payload-building → HTTP-delivery chain is correct without touching any real business record.
4. Confirmed n8n's real, live instance (port 5678) was unaffected throughout — a `GET /` check returned 200 both before and after this work, and the 4 real background node processes present at the start of this session were confirmed still running, unmodified, at the end.

## 5. What remains genuinely blocked (not part of this deliverable)

- Importing `03_Production_Notify.prepared.json` into the live n8n database, and activating any of the 4 real workflows — both require the founder's browser login at `http://localhost:5678` (`BLOCKERS.md` #1), unchanged by this work.
- A live, real (not synthetic) end-to-end firing of Production → n8n additionally requires at least one real ACCEPTED opportunity — today's real decision queue has zero (see the earlier "Run more real evaluation cycles" exchange this session). This is a business-data state, not a code gap, and is explicitly out of scope for this directive.

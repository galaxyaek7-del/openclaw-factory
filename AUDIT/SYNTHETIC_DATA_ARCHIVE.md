# Galaxy Forge — Synthetic Data Archive

**Date:** 2026-08-08 | ADR-222, Phase 30.5.1 (Post-Audit Cleanup — Remove Synthetic Commercial Contamination).

---

## Record removed from `finance_data.json`

| Field | Value |
|---|---|
| Original identifier | `id: 1784854757424` |
| Platform | Paddle |
| Amount | $150 |
| Product | `contract-test-ladder-DELETE-ME` |
| Date | 2026-07-24 |
| Ladder | ai_saas |

## Why it existed

Created 2026-07-24 as a real smoke test of the `/finance/add` → Paddle ladder-rank rollup pipeline (ADR-065 Step 3(c), the "4-layer" finance view fix) — its own product name was deliberately chosen to self-flag as a test artifact pending deletion (`-DELETE-ME` suffix), a pattern this factory has used before for disposable verification records.

## Why it was removed from production analytics

The Phase 30.5 forensic audit (ADR-221, 2026-08-08) found this record was the sole contributor to `finance_data.json`'s `totalSales`/`totalPaddle` figures ($150), and confirmed via live testing that the real `/finance` endpoint served this figure with no in-UI disclosure that it was a smoke test rather than real revenue — a genuine risk of a founder misreading $150 as real commercial activity. Per the audit's own `CEO_VERDICT.md` recommendation and the founder's explicit Phase 30.5.1 cleanup directive, it has been removed from `finance_data.json`.

## How it was removed

Via the real, pre-existing, authenticated `DELETE /finance/delete/:id` endpoint (`server.js`) — not a manual JSON edit. This exercises the same code path (`loadFin()` → filter → `recomputeFinTotals()` → `saveFin()`) any real deletion would use, and was live-verified before and after: `GET /finance` before removal showed `totalSales: 150`; after, `totalSales: 0`, `sales: []`, `byLadder` all zero.

## Where the archived test evidence is stored

`AUDIT/archive/finance_synthetic_records.jsonl` — the complete original record, tagged:

```json
{"SIMULATION_ONLY": true, "SOURCE": "SMOKE_TEST", "NOT_REAL_REVENUE": true, "ORIGINAL_RECORD": {...}}
```

## Confirmation

This record was never a real sale. It represents $0 in real revenue, 0 real orders, 0 real customers, and 0 real payouts. Its removal changes `finance_data.json`'s totals from a misleading $150 to an accurate $0 — it does not remove any real commercial activity, because none existed in this record.

---

*See also: `AUDIT/COMMERCIAL_REALITY.md`, `AUDIT/CEO_VERDICT.md`, `AUDIT/DATA_LINEAGE.md`.*

# Affiliate simulation results (2026-10-23)

Raw results: `simulation_baseline_2026-10-23.json` (before repair) and `simulation_after_repair_2026-10-23.json`.

| Run | Checks | Pass | Fail |
|---|---|---|---|
| Baseline (existing code) | 35 | 28 | 7 |
| After repair | 46 | 46 | 0 |

Baseline failures (each a finding about the factory): no approval path; no destination validation; no status-change path (PENDING could never become CONFIRMED); reversal impossible (DuplicateCommissionError); EUR added to the USD total (75 instead of 60); per-currency totals absent; four commissions sharing one id.

All results are SIMULATION. Nothing here is a real click, conversion, commission or payout.

# Affiliate simulation plan

Command: `python scripts/affiliate_e2e_simulation.py` (or `--json`). Regression: `python -m pytest tests/test_affiliate_e2e_simulation.py`.

Isolation: a temporary directory per run; every record uses `SIM-` ids and environment SIMULATION or TEST (REAL only inside temp files, to test REAL-only guards); production files under `data/` are never written (asserted by the regression test); switches are set only inside a patched environment.

| Scenario | What runs (existing code) | Expected |
|---|---|---|
| A healthy route | registry, eligibility matrix, approval record, link registry, destination validation, content QA, write gate, click tracking, commission ledger PENDING -> CONFIRMED -> PAID, firewall | every stage works; simulated money never counts as real |
| B approval blocked | registry with unverified program, no approval | not QUALIFIED/APPROVED; NOT_APPLIED |
| C payout incompatible | eligibility matrix with an unavailable rail | eligibility found, payout BLOCKED, next action "hold" |
| D invalid links | tokenized/malformed domains; 8 destination URLs | rejected with reason |
| E missing tracking | REAL without evidence, PAID without tx id, unknown status | refused |
| F duplicate conversion | same tx id twice | second refused; ids unique |
| G reversal | PENDING -> CONFIRMED -> REVERSED, then PAID | revenue 50 then 0; PAID after REVERSED refused |
| H unauthorized publication | write gate with switches off; search-ping switch only | all refused |
| I partial failure | truncated ledger line; missing file | valid records kept; empty read |
| J reconciliation | pending/confirmed/paid USD + confirmed EUR | USD 60 (independent calculation), paid 40, per-currency map, unique ids |

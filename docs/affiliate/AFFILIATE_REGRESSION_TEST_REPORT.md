# Affiliate regression test report (2026-10-23)

| Run | Result |
|---|---|
| Existing affiliate/commission tests before changes (20 files) | 433 passed |
| New: `tests/test_affiliate_e2e_simulation.py` | 12 passed |
| Simulation harness | 46/46 checks |
| All tests importing the ledger, registry or links, plus affiliate/commission tests (CI=true) | 1,085 passed, 1 skipped, 9 failed |

The 9 failures are all in untracked test files of the parallel session (`test_performance_commission_validator.py` x6 expects the live click file to hold 21 rows, it holds 30; `test_prospecting.py`; `test_alert_path.py`; `test_ledger_firewall.py`), confirmed absent from HEAD; none of the tracked tests fails.

Not run: anything needing live network or credentials (network postbacks, real link checks). The simulation is not an end-to-end test against a real affiliate network.

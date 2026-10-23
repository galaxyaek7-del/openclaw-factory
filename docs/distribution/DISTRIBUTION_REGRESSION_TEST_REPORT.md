# Distribution: regression test report (2026-10-23)

| Suite | Runner | Result |
|---|---|---|
| `tests/test_social_distribution.py` (33) | `scripts/run_python_group.py` with `CI=true` | 33 passed |
| `tests/test_repurposing_engine.py` (19, unchanged) | same | OK |
| `tests/test_product_launch_kit.py` | same | OK after R13 (failed 2 before) |
| `tests/test_affiliate_launch_batch.py` | same | OK |
| `tests/test_attribution_os.py` | same | OK |
| `tests/test_autonomous_commerce_ops.py` | same | OK |
| `tests/test_commercial_operations.py` | same | OK |
| `tests/test_distribution_os.py` | same | OK |
| `tests/test_revenue_os.py` | same | OK |
| JSONL-read duplication check | `node scripts/check_jsonl_duplication.js` | no new duplication |
| Syntax | `python -m compileall` on new and changed modules | OK |
| Secrets | `python scripts/scan_for_secrets.py` | none found |

Mutation checks: disabling the write gate, the QA, the residue check or the retry bound makes the matching tests fail (4/4); removing the listing-text exemption makes its three tests fail (3/3).

Previous task, for the record: the full CI-equivalent run on 12da063 had 42 steps with 1 failure (R16); after the fix, groups i-p (1,632 tests) and q-z (936) passed on df64a04, and GitHub CI passed for df64a04 (36 of 36 jobs) with the Pages deployment.

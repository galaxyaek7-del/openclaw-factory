# Complete CI Pipeline

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10C: Operations Automation & CI/CD Pipeline," objective 1 (deliverable 1)
**Implementation:** `.github/workflows/ci.yml`

---

## What runs, and why each job exists

Real CI on GitHub's own runners — no merge to `main` should be considered safe unless every job below passes.

| Job step | What it verifies | Real, not simulated |
|---|---|---|
| Syntax check `server.js` | Architecture integrity | `node -c` |
| Syntax check every Python module | Architecture integrity | `python -m compileall` |
| Syntax check Mission Control's inline JS | Architecture integrity | Extracts and parses the `<script>` block the same way this session verified every `mission_control.html` change |
| `.env` never tracked | Security check | `git ls-files` — the exact incident this guards against is trivial to reintroduce by accident |
| Python tests | Business logic correctness | `python -m unittest discover` — 410 real tests |
| JS unit tests | Business logic correctness (incl. Dashboard tests) | `test_metrics.js`, `test_dashboard_data.js`, `test_n8n_notify.js` — 45 real tests |
| Factory Loop tests | Business logic correctness | `test_factory_loop_golden.js` — 44 real tests, now fully deterministic (Phase 10A's frozen-fixture fix) |
| API contract tests (new) | API compatibility | `test_api_contract.js` — boots a real `server.js` in the CI runner and checks the Unified Service Layer's actual shape: all services documented, every data/health endpoint responds correctly, the confirmation gate and 401/404 contracts hold |
| Performance smoke check | Performance regression | Runs `scripts/perf_measure.js latency` against a freshly-booted instance; fails only on a gross error (a hang or non-numeric latency), not a strict per-millisecond gate — CI runner performance isn't comparable to any specific real-hardware baseline |

## Why booting a real server in CI is safe here (and wasn't done elsewhere this session)

Every other verification this session deliberately used a throwaway local port specifically to never interfere with the real, already-running production instance. CI has no such instance — every run starts from a fresh checkout with nothing else running. This is the one place in this entire pipeline where booting a real `server.js` process carries no risk at all.

## What this pipeline does not do

It does not deploy anywhere. It does not touch the real, single local production instance. See `DEPLOYMENT_PIPELINE.md` for what happens after CI passes.

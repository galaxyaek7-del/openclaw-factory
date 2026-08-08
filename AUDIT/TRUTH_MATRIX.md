# Galaxy Forge — Truth Matrix

**Date:** 2026-08-08 | ADR-221, Phase 30.5 forensic audit. Zero-trust: every row below was independently re-tested this round, not carried forward from prior documentation claims.

Evidence levels: E0=claim only, E1=documentation, E2=code exists, E3=local test passed, E4=real integration test passed, E5=real commercial event verified.

| Capability | Expected Behavior | Location | Test Performed | Result | Evidence | Classification | Confidence |
|---|---|---|---|---|---|---|---|
| Real revenue ledger | Reflects real completed sales | `finance_data.json` | Read file directly | 1 record, product name literally `contract-test-ladder-DELETE-ME` — a smoke test, not a sale | E4 (real file read) | **SIMULATED** (mislabeled as revenue but is test data) | HIGH |
| Published books ground truth | Reflects real KDP/marketplace publications | `config/reality.json` | Read file directly | `published_books: []` | E4 | **VERIFIED_LOCAL** (0, honestly) | HIGH |
| Paddle credential | Real API key configured | `.env` (name only, not value), `channels/paddle_arm.py::status()` | Live call | `PADDLE_API_KEY` present; `status()` returns `ready` | E4 | VERIFIED_LIVE (credential valid) | HIGH |
| Paddle checkout readiness | Real customers can pay | `scripts/check_paddle_checkout_status.py::check_and_notify_all()` | Live call against real Paddle account | `checkout_ready: false` for all 6 real products — onboarding incomplete | E4 | **BLOCKED_EXTERNAL** | HIGH |
| Paddle product catalog | Real products exist on the real platform | `channels/paddle_arm.py::list_products()` | Live API call | 6 real active products returned, including EU AI Act Compliance Toolkit | E4 | VERIFIED_LIVE | HIGH |
| Gumroad/Etsy/Payhip credentials | Real API access configured | `.env`, each arm's `status()` | Live call | No credential present for any; `status()` returns `unavailable` for all 3 | E4 | **NOT_CONNECTED** | HIGH |
| Amazon Associates affiliate | Real clicks tracked, real tag configured | `affiliate_commerce/` | Prior-session code inspection (this round: re-confirmed `.env` lacks `AMAZON_ASSOCIATE_TAG`) | Code real; 0 real clicks, tag unset | E2/E3 (code+tests real, no live signal) | PARTIALLY_IMPLEMENTED | HIGH |
| Golden Hunter scoring/evidence | Real market signal → structured, evidence-cited opportunity | `profit_oracle.py`, `market_hunter.py::hunt_market()` | Code read + live file-timestamp check | Real, working scoring logic; feeds `decisions.jsonl` daily | E3 | VERIFIED_LOCAL | HIGH |
| Golden Hunter ranked feed (`golden_opportunities.json`) | Refreshed regularly for Mission Control | `profit_oracle.py::run_oracle()`, called from `market_hunter.py::hunt_market()` only `if golden_catch` | Live file-timestamp check + factory_loop.js log tail | File is 411 hours (17 days) stale; refresh only fires on a new GOLDEN-tier catch, none in 17 days (exhausted static seed list) | E4 | **PARTIALLY_IMPLEMENTED** (real, but effectively stalled) | HIGH |
| Golden Hunter self-detection of staleness | System should know when its own feed is stale | `factory_loop.js` lines ~902-935, 1157-1161 | Live event-log tail | Correctly detects and logs `skipped: stale` every tick, never fabricates fresh data | E4 | VERIFIED_LIVE | HIGH |
| Customer data (requests/reviews/pipeline state) | Real customer records | `data/customer_requests.jsonl`, `data/customer_pipeline_state.json`, `data/customer_reviews.jsonl` | File-existence check | None of the 3 files exist on disk | E4 | **VERIFIED_LOCAL** (0, honestly — genuinely no customers) | HIGH |
| Phase 26-30 module code | Functions execute without error against real data | 5 new modules, 180 tests | Independently re-ran full suites fresh this round | 180/180 pass | E3 | VERIFIED_LOCAL | HIGH |
| Phase 26-30 commercial data flow | Real $ figures flow end-to-end | `global_commercial_operations_engine.py` spot calls | Live calls (`price_intelligence`, `commercial_commission_engine`, `payout_reconciliation`) | All honestly report $0/0-click real state, no fabrication | E4 | VERIFIED_LIVE (architecture real, business activity $0) | HIGH |
| Phase 30 enterprise sales pipeline | Real accounts move through 13 stages | `enterprise_sales_engine.py` | Live call against real `business_development.py` state | 2 real tracked platform relationships (Paddle, Amazon), neither a real enterprise account | E4 | VERIFIED_LIVE (mechanism real, 0 real enterprise deals) | HIGH |
| `delivery_profitability()` negative-revenue handling | Never silently produces an impossible margin | `enterprise_sales_engine.py` | 5 real test cases this round | **Defect found**: -$5,000 revenue produced `margin_pct: 1.2` | E3 | **BROKEN → FIXED THIS ROUND** | HIGH |
| API contract / auth gating | Every commercial endpoint requires auth | `tests/test_api_contract.js` | Live re-run against the running supervised server | 31/31 pass, including the 2 new Phase 30 endpoints | E4 | VERIFIED_LIVE | HIGH |
| Committed secrets | No API keys/tokens/passwords in source control | `git grep`, `.env` gitignore check | Live grep across tracked `.py`/`.js`/`.json` | 0 matches; `.env` confirmed gitignored | E4 | VERIFIED_LOCAL (clean) | HIGH |
| Secrets in logs | No key material printed to log files | `logs/*.log` | Live grep for key-shaped patterns | 0 matches | E4 | VERIFIED_LOCAL (clean) | HIGH |
| AI cost vs. revenue | Real cumulative Groq spend | `data/ai_cost_log.jsonl` | Live parse | $0.0198 real cumulative spend across 230 events | E4 | VERIFIED_LOCAL (immaterial risk) | HIGH |
| Daily automation ticks | `factory_loop.js` runs its ~20 named daily/weekly/monthly functions | Marker files under `data/.*_daily_marker` | Live `ls -la` timestamp check | 10 checked markers all dated today (2026-08-08) | E4 | VERIFIED_LIVE | HIGH |
| `factory_state.json` stickiness bug (ADR-157) | `active_workflow` clears when idle | `factory_state.json` | Live read | `current_task: null, active_workflow: null` — correctly idle | E4 | VERIFIED_LIVE (prior fix holds) | HIGH |
| Webhook receivers (any platform) | Real inbound webhook handling | repo-wide grep | Grep for webhook route registration | None found for any of the 4 registered arms | E2 | **NOT_IMPLEMENTED** | HIGH |
| Order deduplication | Prevents double-charging on a duplicate order | repo-wide grep | Grep + code read | No real dedup logic found; 0 real orders exist to have required it yet | E2 | **NOT_IMPLEMENTED** (real gap, currently low-impact) | MEDIUM |

---

*See also: `PHASE_26_AUDIT.md` through `PHASE_30_AUDIT.md` for per-phase detail, `COMMERCIAL_REALITY.md` for the consolidated revenue-truth statement.*

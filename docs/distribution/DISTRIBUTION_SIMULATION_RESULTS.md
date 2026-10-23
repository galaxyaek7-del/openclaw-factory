# Distribution: offline simulation results

All scenarios use synthetic offers, a fake transport that records calls, temporary ledgers and `FACTORY_LIVE_PUBLISH=false` unless a test opens it inside the test. Source: `tests/test_social_distribution.py::TestScenarios`.

| # | Scenario | Expected | Result |
|---|---|---|---|
| 1 | Valid product, complete campaign | approved -> published -> read-back public -> PUBLISHED_VERIFIED | PASS |
| 2 | Unpublished product | NOT_ELIGIBLE, draft fails QA, not planned | PASS |
| 3 | Invalid destination URL | missing/http/ftp refused; link to another host flagged | PASS |
| 4 | Missing or contradictory claims | no description -> not eligible; template amount not equal to price flagged | PASS |
| 5 | Unsupported media format | Instagram without JPEGs, TikTok without video, guide on Instagram all flagged | PASS |
| 6 | Missing credentials | BLOCKED, zero transport calls | PASS |
| 7 | Insufficient permissions | BLOCKED, never retried | PASS |
| 8 | Rate limiting | RATE_LIMITED, refused before retry_at, succeeds after | PASS |
| 9 | Timeouts / transient errors | retried, stops at 3 attempts as FAILED | PASS |
| 10 | Duplicate publishing | same job id; second publish is a no-op; one transport call | PASS |
| 11 | Partial multi-platform failure | LinkedIn BLOCKED, X PUBLISHED_VERIFIED | PASS |
| 12 | Missing tracking parameters | all four reported; link removed from text flagged | PASS |
| 13 | Wrong product-to-campaign mapping | campaign of another offer flagged | PASS |
| 14 | Unauthorized publication | refused without approval, with weak evidence, and with the switch off; zero calls | PASS |
| 15 | Incorrect or unavailable analytics | REAL without evidence refused; UNKNOWN with a value refused; simulation into the real ledger refused; dashboard shows "NO REAL METRICS RECORDED" | PASS |
| 16 | Price or destination changed | STALE, zero calls | PASS |
| 17 | Rights or policy failure | added "guaranteed"/"trusted by" flagged, listing's own disclaimer allowed, "UNKNOWN" residue flagged, video rights UNRESOLVED flagged | PASS |
| 18 | Interrupted campaign | PUBLISHING without result -> NEEDS_RECONCILIATION, zero calls | PASS |

Additional safety tests: default adapters never reach a network (hand-off instead); X blocked for spend; no HTTP client in the package source; secrets redacted.

Mutation check: with the write gate forced open, QA forced to pass, the residue check removed, or retries unbounded, the matching tests fail (4 of 4).

Live check: `platforms.readiness()` on this machine reports X `BLOCKED_SPEND` (from the recorded 402) and the other three `NOT_CONNECTED`. No simulated post is counted anywhere: the real job ledger holds only drafts.

# Galaxy Forge — Security Test Report

**Date:** 2026-08-07 | Test Scenario 17, executed via real repository scans and one real, safe, live failure-injection call (an intentionally invalid Paddle API key against the live account — no real account access, no money at risk).

---

| Check | Verdict | Evidence |
|---|---|---|
| Secrets not hardcoded in source | **PASS** | Full-repo scan for real Paddle/Stripe key patterns (`pdl_live_`, `sk_live_`, etc.) found zero matches outside `.env` and one code comment describing the key *format* for redaction purposes, not a real key |
| API keys not logged | **PASS** | Full-repo scan for key-logging patterns (`console.log`/`print` including `api_key`) found zero matches |
| Real error messages never leak the key | **PASS (live-verified)** | A real, live call to Paddle with a deliberately invalid key produced `"403 Client Error: Forbidden for url: https://api.paddle.com/products"` — no key fragment present (Paddle auth is a Bearer header, never a URL parameter) |
| Customer data protected | **PASS (architecturally)** | No real customer PII exists yet (0 real customer requests, confirmed in `DATA_RECONCILIATION_REPORT.md`) — the real code path (`customer_pipeline.py`) stores request data locally, never transmits it to a third party beyond the real Paddle checkout itself |
| Authentication failures handled | **PASS (live-verified)** | Every arm's `status()` returns `UNAVAILABLE` on a missing/bad credential, never raises; confirmed live for Paddle with a real invalid key this round |
| Webhook signatures validated where supported | **NOT APPLICABLE** | This factory has **no webhook receiver at all** — every payment/refund state is discovered by polling (`check_payment_status()`), never by an inbound webhook. There is nothing to validate a signature on. This is a real architectural fact, not a vulnerability, but see `FAILURE_REGISTER.md` F7 for its real, secondary consequence (delayed real-time event detection) |
| Sensitive information excluded from normal logs | **PASS** | `paddle_publisher.py::_safe_err()`/`gumroad_publisher.py::_safe_err()` — real, existing, dedicated key-redaction helpers, confirmed by their own passing test suite (`tests/test_paddle_arm.py::TestKeyNeverLeaksInErrors`) |

## Real, live failure-injection evidence (Test Scenario 10, security-relevant subset)

```
Invalid API key -> real Paddle 403, correctly caught as RuntimeError, no key leaked
Timeout         -> correctly wrapped, real error message, no crash
Malformed JSON  -> caught at the real caller-facing boundary (PaddleArm), returns {"status":"ERROR"}
```

## What this report does NOT cover

- **Penetration testing of `server.js`'s HTTP surface** (SQL injection, XSS, CSRF) — out of scope for this round; this factory's own prior security-review skill runs (referenced in this session's history) already cover new-route review on every commit.
- **A real webhook signature check** — cannot be tested because no webhook receiver exists to test (NOT APPLICABLE, not UNKNOWN).

---

*See also: `FAILURE_REGISTER.md`, `END_TO_END_TEST_REPORT.md`.*

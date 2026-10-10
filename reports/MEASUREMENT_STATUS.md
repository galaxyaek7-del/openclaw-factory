# MEASUREMENT_STATUS — what is observable, what is not (Night mission, 2026-10-10)

| Metric | Status | Source / window |
|---|---|---|
| Telegraph page views (per-page) | OBSERVED | getPage API; 35 pages ~113 total; attribution UNKNOWN |
| Site page visits | UNKNOWN | Pages static, no backend (405 proven); server localhost-only, no tunnel |
| Outbound clicks | UNKNOWN | ref/UTM tagged 100% (attribution on purchase only) |
| Nostr replies/claims | OBSERVED (0) | Relay REQ checks, both relays, multiple cycles |
| Lead form submissions | OBSERVED (0 real) | support_tickets ledger (5 records, all test/synthetic) |
| Checkout starts | UNKNOWN | No instrumentation; Gumroad dashboard founder-only |
| Completed purchases | OBSERVED (0) | Gumroad /v2/sales + product sales_count, live API |
| Refunds/fees | OBSERVED (0) | Same APIs; nothing to reconcile |
| Verified revenue | $0 OBSERVED | No qualifying transaction exists |
| Spend | $0 OBSERVED | No purchase made by factory |

**How the next experiment is evaluated:** Telegraph counter increments above own fetches; relay claims; ticket ledger non-test entries; sales API non-zero. First change in any = signal.
**No new analytics layer** (would need accounts/backend); current design (UTM + sales poll + counters) is the maximum free-observable setup.

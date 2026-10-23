# Distribution: campaign pipeline

Mandate stages mapped to code:

| Stage | Where | Automatic? |
|---|---|---|
| PRODUCT_DISCOVERY | `offers.build()` over registry, Gumroad, site, affiliate, video | yes |
| PRODUCT_VERIFICATION | eligibility with reasons; listing state from `product_registry`; site pages from origin/main | yes |
| AUDIENCE_SELECTION | listing tags; UNKNOWN when none (never invented) | yes |
| CAMPAIGN_PLANNING | `prioritize.plan()` (score, per-arm cap, 30-day rotation, needs one QA-passing draft) | yes |
| CONTENT_CREATION | `content.draft()` per platform | yes |
| ASSET_PRODUCTION | video from `video_studio` when rendered; images NOT BUILT | partial |
| QUALITY_REVIEW | `content.qa()` | yes |
| APPROVAL | `Jobs.approve(job, approver, evidence)` | person only |
| SCHEDULING_OR_QUEUEING | `Jobs.queue()`: API queue, or hand-off file in `data/social_handoff/` | yes after approval |
| AUTHORIZED_PUBLICATION | `Jobs.publish()` behind write gate, credentials, spend and transport checks; or a person posts the hand-off | gated |
| PUBLICATION_VERIFICATION | `Jobs.verify()` read-back must show public; hand posts stay unverified | gated |
| TRAFFIC_MEASUREMENT | `tracking.record_metric()` (REAL needs source and evidence) | when data exists |
| CONVERSION_ANALYSIS | `tracking.attribute_purchases()` | when sales exist |
| LEARNING / NEXT_CAMPAIGN | rotation penalty, historical-performance factor, next cycle | yes |

## Job states

`CONTENT_CREATED -> QA_PASSED | QA_FAILED -> APPROVED -> HANDOFF_READY | QUEUED -> PUBLISHING -> PUBLISHED_UNVERIFIED -> PUBLISHED_VERIFIED`, plus `MANUAL_POSTED_UNVERIFIED`, `STALE`, `BLOCKED`, `RATE_LIMITED`, `FAILED_RETRYABLE`, `FAILED`, `NEEDS_RECONCILIATION`.

## Guarantees (each tested)

- Idempotent: job id = hash of offer, platform and content; the same draft is one job and is never published twice.
- Bounded retries: 3 attempts, backoff 60 s / 300 s / 1,800 s recorded as `retry_at`; nothing sleeps.
- Rate limits respected (`retry_at` from the platform's wait).
- Permission and credential errors are not retried.
- A crash during publishing becomes `NEEDS_RECONCILIATION`; no automatic retry.
- An offer whose price or destination changed after drafting makes the job `STALE`.
- A failed platform never changes another platform's jobs.
- A successful API answer is not success: only a public read-back is.
- Secrets in error text are redacted before they reach the ledger.

## Running it

`python scripts/distribution_cycle.py --n 8 --per-arm 2 [--include <offer ids>]` builds offers, plans, drafts and the dashboard. Approval, queueing and recording a hand post are done by a person (Python calls on `social_distribution.campaigns.Jobs`).

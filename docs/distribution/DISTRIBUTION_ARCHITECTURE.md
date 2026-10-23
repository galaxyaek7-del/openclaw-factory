# Distribution engine: architecture

```
data/product_registry.json --+
Gumroad GET /v2/products ----+--> social_distribution/offers.py -----> data/distribution_offers.json
customer_site on origin/main +    (173 offers, 5 arms, eligibility with reasons)
affiliate.registry ----------+
video_studio/projects -------+
                                       |
                    social_distribution/prioritize.py  (transparent score, per-arm cap, rotation, usable-draft check)
                                       |
content_generation/repurposing_engine.py --> social_distribution/content.py  (draft per platform + QA)
social_distribution/tracking.py  (UTM link per draft; metrics ledger; attribution)
                                       |
                    social_distribution/campaigns.py  (job ledger data/social_campaign_jobs.jsonl)
                         approve (person) -> queue -> API adapter  OR  hand-off file data/social_handoff/
                         adapters check: channels/write_gate.py, credentials, spend, transport
                                       |
                    social_distribution/dashboard.py -> data/distribution_dashboard.json, DISTRIBUTION_DASHBOARD.md
scripts/distribution_cycle.py runs offers -> plan -> drafts -> ledger -> dashboard; never approves or publishes.
```

## Design decisions

- **One source of truth per fact.** Product ids and listing states come from `product_registry.py`; copy comes from the repurposing engine; the live-write switch is `channels/write_gate.py`; secret redaction reuses `video_studio.youtube_upload.redact`. The offer registry is a derived view, rebuilt each cycle.
- **Separate package name.** `social_distribution/` avoids the parallel session's untracked `distribution_engine.py` files.
- **Platforms are independent.** Each has its own adapter and readiness; one platform's failure changes only its own jobs (tested).
- **No transport is built.** Every adapter refuses to publish until a transport is injected. Approved jobs become hand-off files a person posts by hand.
- **Approval is a person.** `Jobs.approve()` needs an approver and an evidence reference; the cycle script never calls it.
- **A post counts only after a read-back** shows it public. A hand-posted job stays `MANUAL_POSTED_UNVERIFIED`.

## Loop

The cycle is safe to run repeatedly (same drafts, same job ids). It is not yet wired into `factory_loop.js`: the parallel session has uncommitted edits in that file, and a daily cycle adds drafts faster than a person can review them while every platform is manual. A weekly step is recommended once the founder confirms a review cadence.

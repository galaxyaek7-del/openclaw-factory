# Engineering backlog (ranked, 2026-10-23)

Each item: why, acceptance criteria, verification. Status: TODO, DOING, DONE, BLOCKED (with owner).

| # | Task | Why (risk) | Acceptance | Verify | Status |
|---|---|---|---|---|---|
| B1 | Remove paid product files from the public tree | R2 | 168 files untracked and ignored; dependent tests skip on CI when files absent and still run locally; CI green | CI-equivalent suite on a clean checkout; raw URL 404 after push | DOING |
| B2 | Product identity registry + drift check | R3 | every live Gumroad listing and every manifest has exactly one internal id; registry rebuild is idempotent (same input -> same ids); drift report lists live-not-registered, registered-not-live, price/title mismatches | unit tests with fixtures; run against the live account | TODO (next) |
| B3 | Drift check in the loop, daily | R3 | `factory_loop.js` step records counts; failure reported, never thrown | loop log shows the step | TODO |
| B4 | One publication gate for direct publishers | R4 | `scripts/publish_batch14.py` and future publishers call the central Quality Gate; a product without gate evidence is refused unless the founder's authorization record names it | negative tests (refuse without evidence) and positive tests | TODO (coordinate with parallel session's uncommitted test) |
| B5 | Tests must not write tracked files | R9 | full suite on a clean checkout leaves `git status` clean | run suite, check status | TODO |
| B6 | Per-product traffic measurement | R1 | page views attributed to product pages by internal id; weekly per-product report | page-view ledger + registry join | TODO |
| B7 | Search-intent pages for the 12 reviewed (KEEP) products | R1 | one page per product with buyer problem, real contents, price, link; sitemap + IndexNow | pages live (200), IndexNow receipts | TODO |
| B8 | Thin-PDF repairs and unpublish/delete set | R5 | founder authorization for the 14/2/1 actions in `drafts/release_packages/REPAIR_MANIFEST.json` | platform re-read after each action | BLOCKED (founder) |
| B9 | Move cohort generators behind the manifest contract | R8 | cohort build produces the same manifest shape and runs adapter QA | regenerated manifest + QA report | TODO |
| B10 | Retire unused Mission Control services | R7 | services with no caller listed and removed in reviewed batches | `enterprise_validation.detect_unused_services()` before/after | TODO |
| B11 | Mark superseded root documents as historical | R6 | index lists authoritative docs; others carry a one-line historical header | spot check | TODO |
| B12 | Paddle key permissions, Telegram chat id | R10 | verifier shows Paddle and Telegram VERIFIED | `connection_verifier.py` | BLOCKED (founder) |

Done this session (2026-10-23), for context: agent runtime + telemetry, six-agent daily chain, Sensing commercial classifier with retry, demand sensing, site auto-publish (site-only), IndexNow with keyLocation, 20 service timeouts, evaluator extensions and Excel ROUND, batch 14 (10 products) built, verified and published.

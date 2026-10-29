# Factory reconstruction and build pass, 2026-10-29

Mission: GF-FACTORY-WIDE-RECONSTRUCTION-AND-BUILD-v1. Base: `main` at `070cc24`, working tree
with ~1,790 uncommitted paths from a parallel session (not touched except where listed below).
Nothing in this pass was committed, pushed, published, scheduled, priced or paid.
Spend: $0. `FACTORY_LIVE_PUBLISH` unchanged (false).

Evidence labels: OBSERVED (read from a file, process or live read this session), DERIVED
(computed from observed data), INFERRED, UNKNOWN.

## 1. State of the factory (OBSERVED unless marked)

| Area | State | Evidence |
|---|---|---|
| Digital products | 102 listings live on Gumroad, 3 uploaded not published, 0 sales | `data/product_registry.json` (rebuilt 2026-10-29 00:07Z from a read-only Gumroad GET) |
| Batch 15 | all 10 published 2026-10-27 12:41Z; site pages committed | `data/batch15_publish_results.json`, `git ls-files customer_site` |
| Revenue | $0 gross, 0 sales; Gumroad confirmed by a poll at 00:07Z; Paddle not checked (403 backoff) | `revenue_truth.read_revenue_state()`, `data/sales_poll_last_check.json` |
| Fees, refunds, net, balances, withdrawals | UNKNOWN: no source records them | dashboard shows UNKNOWN |
| Factory loop / server | both running under `scripts/supervisor.js`; loop ticks every ~10 min | Win32_Process, `factory_loop.log` |
| Distribution | Pinterest and TikTok connected via Metricool; X BLOCKED_SPEND; LinkedIn, Instagram NOT_CONNECTED; Pinterest queue 86 blocked on missing board + 13 images not public | `data/distribution_dashboard.json`, `data/pinterest_queue.json` |
| Affiliate | no associate tag; commission ledger 1 TEST row; 38 click records with no source/bot classification | `data/commission_ledger.jsonl`, `data/affiliate_clicks.jsonl` |
| Children's studio | episode 1 animatic verified (14 shots, 158 s, 16 Arabic cues); no finished film; blocked on voices and font decisions | `kids_studio/production_manifest.json` |
| Doctrine gate | `python scripts/check_doctrine.py` exit 0 | run this session |

Arm statuses (DERIVED by `business_arms.py`, 00:2xZ): PARTIAL 5, PLANNED 2, BLOCKED 1, READY 0,
REVENUE_VERIFIED 0. Mapping of the ten activities: `docs/factory/ARM_TAXONOMY.md`.

## 2. Defects found and fixed (root cause -> change -> proof)

1. **Revenue reported STALE although polled every cycle.** `finance_data.json` is rewritten only
   when a sale arrives; `revenue_truth` judged freshness by that file's age alone.
   -> `scripts/poll_sales.py` records per-arm successful reads (`data/sales_poll_last_check.json`);
   `revenue_truth.read_revenue_state()` accepts that as confirmation for the arms read without
   error inside 24 h and names the arms not checked. The amount is never changed by it.
   Proof: `tests/test_revenue_freshness.py`; a real loop poll at 00:07Z produced PASS with
   "not checked: paddle".
2. **Digital Products arm stuck at BLOCKED for a reason that stopped being true.** Fixed text
   from 2026-10-19. -> status/gap derived from the product registry; Digital Products can reach
   REVENUE_VERIFIED only with a registry sale *and* a reconciled finance record.
   Proof: `tests/test_arm_portfolio.py`.
3. **Guide generator** printed internal "UNKNOWN -- ..." markers on 13 public pages and removed
   og/canonical tags from all 17 guides each time it regenerated them (the tags had been added
   once by `scripts/add_share_cards.py`). This corrects the 2026-10-24 report that blamed the
   parallel session. -> `seo_distribution._known()` and `_share_block()`.
   Proof: `tests/test_seo_guide_quality.py`; regenerated 17 guides, 0 residue, 17/17 with one
   canonical tag, 0 guides that lose a tag against HEAD.
4. **Test side effect introduced and removed in this pass**: wiring the arm writer into
   `registry_daily.run_once` made an existing test write the live
   `data/business_arms_state.json`. -> the writer runs by default only on the real rebuild.
   Proof: `RegistryDailyWritesArms` tests.

## 3. Capabilities added

- `business_arms.PORTFOLIO_ACTIVITIES`, `portfolio_view()`, `CONTROL_CAPABILITIES`,
  `control_status()`, `write_state()`, `python business_arms.py --write`.
- Daily: `scripts/registry_daily.py` restates the arm file after each registry rebuild.
- CEO dashboard (`dashboard.html`, `lib/ceo_command_center.js::businessArms`): section
  "الأذرع والقدرات" — ten activities, eight arms, two controls, freshness (STALE after 36 h),
  validation problems. Behind Mission Control login (401 without). Live server restarted
  by exact PID under the supervisor and checked over HTTP.
- Backlog rows B13-B26 in `docs/factory/FACTORY_ENGINEERING_BACKLOG.md`, machine-readable
  in `data/factory_backlog.json`.

## 3a. Tests actually run

| Command | Result |
|---|---|
| `pytest tests/test_doctrine_layers.py tests/test_seo_distribution.py` (baseline, before changes) | 61 passed |
| `node --test tests/test_ceo_command_center.js` (baseline) | 25 passed |
| `pytest tests/test_revenue_freshness.py` (new) | 8 passed |
| `pytest` on the 6 files importing `revenue_truth`/`poll_sales` | 133 passed |
| `pytest tests/test_arm_portfolio.py tests/test_doctrine_layers.py` | 65 passed (arm file now 15 tests) |
| `pytest tests/test_arm_portfolio.py tests/test_product_registry.py` | 29 passed |
| `pytest tests/test_seo_guide_quality.py tests/test_seo_distribution.py` | 15 passed |
| `node --test tests/test_ceo_command_center.js` (after) | 27 passed |
| `python scripts/check_doctrine.py` | exit 0 |
| full `pytest tests` | **incomplete**: stopped by the system for low memory at 39% (3,094 passed, 47 failed, names not printed). Failures are UNATTRIBUTED; not re-run. It also appended fixture rows to live ledgers (backlog B27). |

## 4. Not done, and why

- No commit or push: the mission requires founder authorization. Consequence: the guide fixes
  and 13 new pin images are local only; the auto-publisher pushes only existing commits.
- RaaS, Data Products, Productized AI Services, AI Operations: no evidence of demand or of a
  delivery engine for a recurring service; specs are backlog B19-B21, not built speculatively.
- Per-arm attribution beyond Digital Products (B22) and click classification (B24): TODO.

## 5. Next executable steps

1. Founder: authorize a commit of this pass (file list in the session report) and, separately,
   a site-only commit for the regenerated guides and pin images.
2. Founder: create the Pinterest board "Small Business Finance Tools"; reissue the Paddle key.
3. Engineering: B24 (click classification), then B22 (affiliate attribution), then B19-B21 specs.

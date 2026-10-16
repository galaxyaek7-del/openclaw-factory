# EXP-C81-001 — Diagnosis (Phase 1) and Proposed Fix (Phase 2)

Date: 2026-10-15. Mode: read-only. No Gumroad write, no publish, no message, no gate touched.
Labels: **OBSERVED** (seen in this session, with the command/time), **DERIVED** (inferred from observed facts), **UNVERIFIED** (claimed somewhere, not confirmed).

## 1. Evidence

### 1.1 What EXP-C81-001 is
It is not a product. It is a 30-day, $0 acquisition **experiment** over the free Etsy-guide cluster, pointing to the Gumroad listing `/l/bfhpzl` ("Etsy Suspension: Triage + Appeal Bundle", $79).

| Location | Content |
|---|---|
| `scripts/cycle81_product_evaluation.py:46-66` (tracked, commit `1256531`) | `EXPERIMENT = {"id": "EXP-C81-001", ..., "stopping_rule": "stop and report if, after 30 days, Gumroad Analytics shows zero impressions for the cluster AND zero clicks on the tagged links ...", "measurement_status": "BLOCKED - the tagged links exist, but no analytics endpoint can be read without the founder, so the experiment cannot currently be judged either way"}` |
| `data/cycle81_product_evaluation.json:41-52` (untracked; written by the script above, 2026-10-15 11:12) | The same dict, copied verbatim. This is the only stored "block record". |
| `reports/FOUNDER_ACTION_AR_gumroad_analytics.md:55` | Asks the founder to export Gumroad Analytics to measure EXP-C81-001. |
| `tests/test_exp_c81_utm_regression.py` (untracked, written by a parallel tool) | UTM regression tests for the experiment links: 18/18 pass (OBSERVED). |

### 1.2 The "could not analyze" block is a hard-coded string, not a runtime failure (OBSERVED)
- `measurement_status` is a literal string in the `EXPERIMENT` dict. No function computes it, no API call precedes it, and nothing ever re-evaluates it.
- There is no state machine, SQLite row or retry loop for this experiment.
- No quality gate is involved: `publish_protection.py`, `quality_gate_policy.py`, `profit_oracle.py`, `write_gate.py` and `distributor.py` contain no reference to `EXP-C81` or `bfhpzl` (grep: 0 files).

### 1.3 The claimed Gumroad analytics probe has no recorded evidence
- The 404 table ("`/v2/analytics` 404, `/v2/visits` 404, `/v2/products/analytics` 200 'product not found', per-product 404") appears in:
  - `scripts/cycle85_buyer_path.py`, docstring and a string literal.
  - `data/cycle85_buyer_path.json`.
  - `reports/CYCLE85_COMMERCIAL_IGNITION.md`.
  - `reports/FOUNDER_ACTION_AR_gumroad_analytics.md`.
- `cycle85_buyer_path.py` does **not** call those endpoints. It only fetches public product pages.
- **Last 3 attempts:** none are recorded. No log, ledger or evidence file in the repository contains a request to those endpoints with a status code or timestamp.
- **Transcripts on this machine:**
  - Claude Code: only this session's own search commands match.
  - OpenCode's local database: read-only, time-bounded queries over 2026-10-10 → 2026-10-15. The first occurrence of the table is OpenCode **writing it into the script** at 2026-10-14T21:45:34Z. Before that, from 12:28Z, only prose such as "Gumroad exposes no analytics API" appears. No actual request was found in the windows searched.
- **Conclusion:** "Gumroad has no analytics API" is **UNVERIFIED** in this repository. It is probably true (DERIVED: the integration's own client implements only products/sales/user calls), but no recorded call proves it. A fetch of Gumroad's public API docs and source failed (JS-only page; GitHub raw timed out).

### 1.4 The factory's own visit tracking cannot record a single visit (OBSERVED) — the decisive finding
- **The pages carry the tracker.** All 8 experiment pages load `assets/gf-pageview.js` (`<script src="assets/gf-pageview.js" defer>`, e.g. `guide-etsy-suspension-appeal.html:190`).
- **The tracker's target is relative.** It posts to `/api/page-view` unless the page sets `<meta name="gf-pageview-endpoint">` or `window.GF_PAGEVIEW_ENDPOINT`. **0 of 8 pages set an override.**
- **The pages are served from GitHub Pages:** `https://galaxyaek7-del.github.io/openclaw-factory/customer_site/...` (285 references in the site).
- **The live page loads, the receiver does not exist:**
  - `GET .../customer_site/guide-etsy-suspension-appeal.html` → **200**, 2026-10-15T22:23:43Z.
  - `/api/page-view` begins with `/`, so it resolves to the **domain root**. `GET https://galaxyaek7-del.github.io/api/page-view` → **404**, 2026-10-15T22:24:09Z.
- **The real receiver is local only.** It lives in `server.js` (public event-ingestion routes, line ~6764), which binds `BIND_HOST = '127.0.0.1'` (line 8264). It is unreachable from the internet.
- **The ledger shows only internal probes.** `data/affiliate_page_views.jsonl` holds 30 events: `solutions` 18, `market-validation` 3, `c89-ua-probe` 3, `mindfulness-test` 2, … **None comes from an experiment page.**
- The script's own header documents this exact failure mode (Cycle 89: "served as a static GitHub Pages tree there is no /api/page-view handler at all, the POST 404s").

### 1.5 Credentials and the product (OBSERVED)
- **`.env`:** `GUMROAD_ACCESS_TOKEN` is SET (value not printed). `FACTORY_LIVE_PUBLISH` is `'false'`.
- **Auth state:** `data/gumroad_auth_state.json` = VERIFIED, recorded 2026-10-14T18:57Z (27 h old). Stale for the write gate, but irrelevant to reads.
- **Read-only GET** via the existing `gumroad_publisher.get_product()` (2026-10-15T22:15:03Z, `GET /v2/products/LzOV85deBGdLgNZmvpvYGw==`):
  - id `LzOV85deBGdLgNZmvpvYGw==`, slug `bfhpzl`, price 7900 cents.
  - `published: True`, `deleted: False`.
  - `sales_count: 0`, `sales_usd_cents: 0.0`.
- **It matches the local inventory** (`data/commercial_inventory.json`).

## 2. Root cause

**Category h (Other): measurement architecture gap. Contributing: category f (a defect in the factory's own instrumentation).** Confidence: **High** for the first and third points below, **Medium** for the second.

The experiment cannot be judged because **none of the three data sources its stopping rule needs is readable by the factory**:
1. **Visits / impressions on the guide pages.** The factory's own tracker is deployed to a static host with no receiver; it 404s on every page view (OBSERVED). GitHub Pages itself gives the owner no visitor analytics, and Google Search Console (the source of search "impressions") was never connected (DERIVED from the repo; no verification file found).
2. **Clicks on the tagged links / views of the Gumroad listing.** These exist only in the Gumroad dashboard. No API path is implemented, and the "no analytics API" claim is UNVERIFIED (see 1.3).
3. **Purchases.** This one **is** measurable today through the existing read-only API: `sales_count = 0` (OBSERVED). It is not wired into the experiment.

The block message blames Gumroad. The decisive defect is the factory's own: its first-party tracker has never been able to reach a receiver from the public pages.

## 3. What is NOT the cause (with evidence)
| Category | Not the cause because |
|---|---|
| a. Credentials | Token SET. A live read-only GET succeeded at 22:15:03Z. |
| b. ID/slug mismatch | Gumroad returned the same id, slug and price as local state. |
| c. Missing metadata | Product published, priced, not deleted. The experiment needs no product metadata change. |
| d. File upload/format | No upload is involved in measurement. |
| e. API change / rate limit | No analytics call was ever made, so nothing was rate-limited. The product GET returned normally. |
| g. Stale state needing reconciliation | The status text is static but **accurate in substance**. Reconciling the record would not unblock anything. |
| Quality gate | No gate references this experiment (grep: 0). The block is a hand-written measurement status, not a gate decision. |

## 4. Proposed fix (Phase 2 — nothing applied)

**Honest scope:** no code change can make the stopping rule judgeable on its own, because the missing data lives behind accounts only the founder controls. Code can do two things: make the status computed and evidence-cited instead of hard-coded, and wire in the one source that is already readable (sales). Real unblocking requires **one founder choice** (step 1).

1. **Founder decision (no code): pick a measurement source.**
   - **A. Google Search Console** for `galaxyaek7-del.github.io`. Free. Gives search impressions and clicks per page, which matches the stopping rule's "impressions". The founder verifies ownership; the verification token file would then be added to the site (a separate approved change).
   - **B. Gumroad dashboard export** (the existing `FOUNDER_ACTION_AR_gumroad_analytics.md`). Gives listing views and referrers.
   - **C. A public receiver for `gf-pageview.js`**, e.g. a free serverless endpoint or exposing `server.js`. This is new infrastructure and a security surface; I don't recommend it now.
   - Risk: none to the factory; it is a decision.
2. **`scripts/cycle81_product_evaluation.py`.** Replace the literal `measurement_status` string with a structured, evidence-cited `measurement` block:
   - `impressions_source: NOT CONNECTED` (tracker receiver 404, URL + timestamp).
   - `listing_views_source: NOT CONNECTED` (Gumroad dashboard only; API claim UNVERIFIED).
   - `purchases_source: CONNECTED` (`get_sales` read-only), `status: BLOCKED` until both sources 1 and 2 are connected.
   - Risk: **Low**. Reporting data only; no gate, no channel, no write path.
3. **New `scripts/exp_c81_measurement_check.py`.** A read-only checker that:
   - GETs the live guide page and the tracker target, and records the status codes.
   - Calls the existing `gumroad_publisher.get_sales(token, product_id)` (GET) and records the count.
   - Writes only `data/exp_c81_measurement_status.json`.
   - Never calls a write function (asserted by a test).
   - Risk: **Low–Medium**: network reads that use the token read-only.
4. **New `tests/test_exp_c81_measurement.py`** (offline, mocked HTTP). Asserts that:
   - status stays BLOCKED whenever impressions or views are NOT CONNECTED;
   - zero observed visits are never reported as zero traffic;
   - the checker imports no Gumroad write function and never calls one.
   - Existing coverage kept as-is: `tests/test_exp_c81_utm_regression.py` (18 pass), `tests/test_gf_pageview.js`. Risk: **Low**.
5. **Not touched:** `publish_protection.py`, `quality_gate_policy.py`, profit logic, `write_gate.py`, Gate-2, `FACTORY_LIVE_PUBLISH`, any Gumroad write, `gf-pageview.js` behaviour, and all existing tests.

### Verification without publishing
- Run the checker. Expect: page 200, receiver 404, `sales_count` 0, overall status BLOCKED, with the reason naming the missing sources.
- Run the new and related tests (`test_exp_c81_*`, `test_gf_pageview.js`), then the full Python suite (by CI groups).
- Diff `data/*.jsonl` before and after: only `data/exp_c81_measurement_status.json` and `data/cycle81_product_evaluation.json` may change.

### Rollback
- Delete `scripts/exp_c81_measurement_check.py`, `tests/test_exp_c81_measurement.py` and `data/exp_c81_measurement_status.json`.
- `git checkout -- scripts/cycle81_product_evaluation.py`.
- Restore `data/cycle81_product_evaluation.json` from the copy taken before the change (it is untracked).

## Phase 3 status — PARTIAL (approved items a, b, c only), 2026-10-15

**(a) One read-only GET** to `/v2/sales?product_id=LzOV85deBGdLgNZmvpvYGw==`, no retry needed:
- HTTP **200**, `success: true`, **0 records**, no next page.
- Received 2026-10-15T22:32:32Z (server `Date: Thu, 15 Oct 2026 22:32:37 GMT`).
- Saved to `reports/EXP-C81-001_api_probe.json`, with no token.

**(c) Computed status in `scripts/cycle81_product_evaluation.py`.** The literal is replaced by `compute_measurement()`:

| Metric | Value | Evidence |
|---|---|---|
| `purchases` | **connected** | `reports/EXP-C81-001_api_probe.json` |
| `page_views` | **not connected** | 0 of 8 pages configure a receiver; 0 events recorded from them |
| `listing_views_and_tagged_clicks` | **not connected** | no export; no API path; API availability unverified |

- Overall: **BLOCKED**, because the stopping-rule data is not connected.
- The old literal is kept as `LEGACY_MEASUREMENT_STATUS` and written to the output as `measurement_status_legacy_hardcoded`.

**(b) New test** `tests/test_exp_c81_measurement_status.py`: 2 tests, both pass.
- A deliberate mutation (treating 200 as success without `success=true`) made it fail, as intended.
- Related tests: `test_exp_c81_utm_regression.py` 18/18 pass; `test_gf_pageview.js` 1/1 pass.
- CI group e (working tree): 659 tests, 1 failure, in the untracked `test_e2e_simulation.py::test_02`. It fails identically with the original HEAD script, so it is unrelated to this change. Its cause is the untracked evidence gate `affiliate/opportunities.evidence_gate_check()`, which is out of scope and was not touched.

**Not touched:** `server.js`, any port, `publish_protection.py`, `quality_gate_policy.py`, profit logic, gates, Gumroad writes, the site, `FACTORY_LIVE_PUBLISH`, `PRODUCTION_AUTHORIZED`.

## Phase 3 — Close (2026-10-16, founder directive)

The founder lifted the BLOCK on closing Phase 3 and accepted the known limits. This is a governance decision. The computed metrics are unchanged, because the data they describe still does not exist.

```json
{
  "experiment_id": "EXP-C81-001",
  "phase": 3,
  "status": "COMPLETE_WITH_KNOWN_LIMITS",
  "measurement_status": "LEGACY_HARDCODED",
  "measurement_status_note": "Founder label for this cycle. The computed status in data/cycle81_product_evaluation.json remains BLOCKED (purchases: connected; page_views: not connected; listing_views_and_tagged_clicks: not connected), and the legacy hard-coded string is kept for audit.",
  "measurement_status_reason": "No Gumroad analytics API path exists in the factory; whether Gumroad offers one is UNVERIFIED (no recorded call; the earlier 404 table has no recorded request behind it). Page-visit receiver not configured (tracker target https://galaxyaek7-del.github.io/api/page-view observed 404, 2026-10-15T22:24:09Z). Both deferred to Phase 4.",
  "tests": {
    "test_exp_c81_measurement_status": "see Final verification below",
    "test_exp_c81_utm_regression": "see Final verification below",
    "test_gf_pageview": "see Final verification below",
    "test_e2e_simulation_test_02": "FAIL_ISOLATED",
    "e2e_failure_cause": "evidence gate in affiliate/opportunities.py rejects placeholder values; fails identically without the C81 change; deferred (BKL-003)"
  },
  "files_changed": [
    "scripts/cycle81_product_evaluation.py",
    "tests/test_exp_c81_measurement_status.py",
    "reports/EXP-C81-001_api_probe.json",
    "reports/EXP-C81-001_diagnosis.md",
    "reports/backlog/BACKLOG-2026-10-16.json"
  ],
  "files_regenerated_untracked": ["data/cycle81_product_evaluation.json"],
  "files_not_touched": [
    "server.js",
    "publish_protection.py",
    "quality_gate_policy.py",
    "profit_oracle.py",
    "FACTORY_LIVE_PUBLISH",
    "PRODUCTION_AUTHORIZED"
  ],
  "founder_decisions": {
    "analytics_source": "MANUAL_EXPORT_DEFERRED",
    "page_visit_metric": "UNRESOLVABLE_NOW",
    "e2e_failure": "ISOLATED_SEPARATE_SPRINT"
  },
  "phase_4_requirements": [
    "Connect Google Search Console",
    "Configure page-visit receiver",
    "Fix affiliate evidence gate for e2e tests",
    "Gumroad CSV export integration"
  ],
  "backlog": "reports/backlog/BACKLOG-2026-10-16.json (BKL-001..BKL-004)",
  "verdict": "UNBLOCK_APPROVED_BY_FOUNDER"
}
```

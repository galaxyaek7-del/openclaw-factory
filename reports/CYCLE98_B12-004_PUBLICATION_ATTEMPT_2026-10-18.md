# Cycle 98 — B12-004 Publication Attempt (2026-10-18)

**Status: BLOCKED (founder decision required).** All other Cycle-98 work is complete and verified.

## Founder directive (Cycle 98)
1. Approve the proposed B12-004 price of **USD 11.99**, subject to confirming the final listing and
   checkout both display exactly that price and currency.
2. Issue **`APPROVE B12-004 PUBLISH`** (scope: B12-004 only).
3. Execute the sanctioned publication workflow, verify live independently, then continue to the next product.

## What was done

### 1. Price reconciled to the founder-approved $11.99
Updated every B12-004 price reference from the gate-rejected `$19.00` to **`$11.99`** (USD):

| File | Change |
|---|---|
| `data/product_batch_12.json` | B12-004 `price` 19 → **11.99**; added `price_basis: FOUNDER_APPROVED_BELOW_COMPARABLE_2026-10-18` |
| `data/product_batch_12_gumroad_prep.json` | B12-004 `proposed_price_usd` 19 → **11.99**; `price_status: FOUNDER_APPROVED 2026-10-18 (USD 11.99)` |
| `customer_site/b12-meeting-cost-calculator.html` | title/og/twitter + body $19 → **$11.99**; banner + price line now "approved … not yet for sale" |
| `scripts/build_batch12_pages_qa.py` | B12-004 `price=19` → **`price=11.99`** (only that entry; `main()` never run) |
| `drafts/b12_004_listing_copy.txt` | price line → **$11.99 USD (FOUNDER-APPROVED 2026-10-18)** |
| `reports/phase8/B12_004_GUMROAD_LISTING_PACKAGE.md` | Price section → **$11.99 USD, FOUNDER-APPROVED** |
| `reports/B12-004/DEMAND_EVIDENCE_2026-10-18.json` | added `approved_price_usd: 11.99`, `approved_by`, `requires_founder_confirmation: false` |
| `data/product_pipeline.json` | `price_usd: 11.99`, `price_status: FOUNDER_APPROVED`, updated prerequisite/next_action |

All four touched JSON files re-parse; `scripts/build_batch12_pages_qa.py` re-compiles. B12-001 was **not** touched.

### 2. Deliverables re-verified (unchanged)
| File | Size | sha256 | Result |
|---|---|---|---|
| `books/batch12/B12-004_meeting_cost_roi_calculator.xlsx` | 12,865 | `87ecb1cd…c820` | MATCH |
| `books/batch12/B12-004_meeting_method_guide.pdf` | 9,639 | `2c964edc…2a46` | MATCH |
| `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx` | 8,922 | `aee8fc0b…092d` | MATCH (untouched) |

`scripts/check_b12_integrity.py` → **`B12 integrity: OK (10 prep items, 5 baselines)`**.

### 3. Publication attempt → BLOCKED
Attempted the sanctioned, documented path. **No sanctioned mechanism can publish B12-004:**

- **`scripts/first_sale_orchestrator.py` (the phrase-gated mechanism) is hardcoded to B12-001.**
  `PUBLISH_PHRASE = "APPROVE B12-001 PUBLISH"` (L265); the whole task graph, `build_spec()`,
  `_real_verify_draft()` (asserts price 1499), and `data/first_sale_draft_evidence.json` are B12-001-specific.
  There is **no product parameter**. `--status --json` confirms it: 10/10 tasks COMPLETED/EXTERNALLY_VERIFIED,
  `next_action = DONE`, and **zero B12-004 tasks**.
- **B12-004 has no Gumroad product and no draft** (never created).
- **Automated draft creation is blocked by design:** `scripts/gumroad_draft_orchestrator.py --capability --json`
  → `DRAFT_CREATION_CAPABILITY_UNKNOWN`, `authorization: BLOCKED`, `live_verified: false`
  (our `create_product()` omits the `published` field; a real live create defaulted to `published:true`;
  creation is non-idempotent).
- **`--audit --json` (read-only)** found only 2 create-then-publish files, both **parallel-owned**:
  `affiliate/publish_queue.py` (does not check `FACTORY_LIVE_PUBLISH`) and `src/publish/auto_publisher.py`
  (checks it, but its founder authorization is unconfirmed and it has no per-product gate). Neither is the
  per-product phrase-gated founder mechanism.
- **Using `channels/gumroad_publisher.py --create` would bypass the founder-authorization layer** and would
  create a **live** product with **no cover** — the directive explicitly forbids bypassing gates.

Evidence: `reports/B12-004/PUBLICATION_MECHANISM_AUDIT_2026-10-18.json` (contains the three raw read-only audits).

## Verified results
- **Verified revenue: $0** — `VERIFIED_EXTERNAL_TRANSACTIONS=0`. No new sale.
- B12-004 remains **READY_FOR_AUTHORIZATION**; listing/copy/price all consistent and approved.

## Founder decision required (one of)
- **A. Parameterize the hosted mechanism for B12-004** — extend `scripts/first_sale_orchestrator.py` to take a
  per-product spec/phrase (e.g. `--product B12-004` + its own draft evidence), then run it. (A real code change
  to a safety-critical gate; needs explicit go-ahead.)
- **B. Founder-created manual draft** — create the B12-004 draft at gumroad.com, record its product id + price in
  `data/first_sale_draft_evidence.json`, then the existing enable/verify/rollback path can run.
- (The `$11.99` price itself is approved; the **checkout-display confirmation** the founder attached is
  impossible today because no listing exists.)

## Next
Per the queue's move-on rule, the next eligible product is **B12-002 — Client Project Handoff Pack**
(BUILDING: needs real demand/competitor evidence, a rebuild to the deep-QA bar, then QA).

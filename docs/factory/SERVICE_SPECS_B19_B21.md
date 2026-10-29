# Service specifications: RaaS, Productized AI Service, AI Operations (B19, B21; 2026-10-29)

Specifications only. No offer is activated, no intake channel opened, no price set,
no customer contacted. Each spec is built on an engine that already exists and is
tested here; what that engine does not yet do is listed as a gap, not assumed.

Common rules for all three:

- **Founder gates:** opening intake, setting a price, contacting a customer and every
  delivery go through the founder (same gate as `services/spreadsheet_normalization/offer.md`:
  "HUMAN REVIEW: founder final QA on every delivery").
- **Promotion from spec to offer** requires all of: (1) the acceptance tests below pass
  on fixtures in CI; (2) at least 3 recorded customer-problem signals for the buyer
  group, from at least 2 independent sources (`trend_to_product.records.record_signal`,
  type CUSTOMER_PROBLEM); (3) founder approval of the intake channel and price. Until
  then the arm stays PLANNED/PARTIAL in `business_arms.py`.
- **No outcome guarantees** beyond the documented report; no financial, tax or legal advice.

---

## B19 — RaaS: monthly marketplace-export clean-up (arm: `micro_b2b`)

**Engine:** `services/spreadsheet_normalization/engine.py::normalize` (headers, dates to
ISO, US/EU currency to numeric, SKU clean-up, duplicate flagging, missing-value report,
secret scan). Tests: `tests/test_spreadsheet_engine.py` (8),
`tests/test_spreadsheet_family_xlsx.py`. One-off offer already written
(`services/spreadsheet_normalization/offer.md`); this spec is its recurring form.

| Item | Specification |
|---|---|
| Buyer | small online sellers who reconcile monthly order/fee exports by hand |
| Recurring outcome | each month: a clean export plus a month-over-month change report |
| Input | the month's CSV/XLSX export (orders, fees or payouts), max 50k rows; column roles confirmed once and reused |
| Output | cleaned file; QA report (rows in = rows out + duplicates, columns mapped, missing values); change report vs last month (row count, new/removed SKUs, total per currency) |
| Cadence | monthly, on upload; no scheduled pull from the buyer's accounts |
| Data handling | files deleted after delivery (engine README: "No PII retention after delivery"); `scan_secrets` flags credential-like headers and values (first 200 rows) but is not called inside `normalize`: the delivery workflow must call it and refuse a flagged file |
| Excluded | bookkeeping judgement, tax advice, credentialed access to the buyer's store |

**Acceptance per delivery:** row reconciliation holds; every dropped row counted; currency
spot-check passes on US and EU formats; the change report totals equal the sums of the two
cleaned files; founder QA sign-off recorded.

**Gap (code):** the engine has no month-over-month comparison and no stored column-role
profile per buyer, and the secret scan is not enforced inside the pipeline. All three are
needed before promotion (backlog B34).

**Outcome pricing rule (proposed, not set):** charged only for a delivery that passed its
acceptance checks; a failed delivery is re-run or not charged.

---

## B21a — Productized AI Service: listing claim audit (arm: `productized_ai_services`)

**Engine:** `product_claim_integrity.py::check_claim_integrity` (does the delivered file
actually contain what the listing promises: data claims vs payload, enumerated contents,
depth vs price), plus `executive_quality_gate.check_fake_urgency_risk` and
`check_copyright_trademark_risk` for the listing text. Tests: `tests/test_cycle81.py` (26).
It found a real defect in our own catalog on 2026-10-14 (a $99 "lead list" whose file was
a one-page description).

| Item | Specification |
|---|---|
| Buyer | digital-product sellers (Gumroad/Etsy) before launch or after a refund complaint |
| Outcome | a report per listing: each promise in the text, whether the delivered file backs it, and wording that reads as fake urgency or claimed brand affiliation |
| Input | listing title and description as published + the delivered files (PDF/XLSX/CSV/ZIP) |
| Output | per-listing verdict (PASS / mismatch list / UNKNOWN when a file cannot be inspected) and plain-language fixes |
| Turnaround | per batch; no access to the seller's account (files supplied by the seller) |
| Excluded | legal opinion on trademark or consumer law; rewriting the product |

**Acceptance:** on the fixture set from `tests/test_cycle81.py` the verdicts match; an
uninspectable file yields UNKNOWN, never PASS; every mismatch quotes the promise and names
the file that fails it.

**Gap:** the phrase lists are English-only and non-exhaustive (stated in
`executive_quality_gate.py`); DOCX payloads are not inspected. Report wording must say the
audit is a screen, not legal review.

---

## B21b — AI Operations: automation health audit (arm: `ai_operations`)

**Engine:** `scripts/n8n_workflow_health.py::assess` — per workflow, five separate facts
(service answers, workflow active, last execution status, freshness against its schedule,
business operation succeeded). It caught our own failure on 2026-10-22: n8n answered on
its port while every company workflow had failed since 2026-10-10. Tests:
`tests/test_n8n_workflow_health.py` (10).

| Item | Specification |
|---|---|
| Buyer | small teams running self-hosted n8n who check "is it up" but not "did it work" |
| Outcome | a dated report: which workflows actually ran and succeeded, which are stale or failing, and the first failing node, with secrets redacted (`redact`) |
| Input | **a copy of the buyer's n8n database file** (the engine reads a SQLite snapshot; it does not use the n8n API) or an export of executions |
| Output | per-workflow five-fact table, overall verdict, list of failing workflows with redacted error text |
| Cadence | one-off audit; recurring only after the API path exists |
| Excluded | changing the buyer's workflows; holding the buyer's credentials |

**Acceptance:** on fixture databases (healthy, failing, stale, inactive, port-up-but-failing)
the five facts and the verdict match; no secret value appears in the report.

**Gap and risk:** the engine reads a database snapshot, which contains the buyer's
credentials table. Receiving that file is a security decision for the founder; the
preferred path is an executions-API reader that never touches credentials (not built,
backlog B35). Until then this spec stays PLANNED.

---

## Summary

| Spec | Engine exists and tested | Code gap before promotion | Blocking decision |
|---|---|---|---|
| B19 RaaS monthly clean-up | yes (`services/spreadsheet_normalization`) | month-over-month report, buyer column profile (B34) | founder: intake channel, price |
| B21a Listing claim audit | yes (`product_claim_integrity.py`) | DOCX inspection; report wording | founder: intake channel, price |
| B21b Automation health audit | yes (`scripts/n8n_workflow_health.py`) | executions-API reader without credentials (B35) | founder: whether to accept buyer data at all |

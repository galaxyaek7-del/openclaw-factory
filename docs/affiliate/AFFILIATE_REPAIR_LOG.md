# Affiliate repair log (2026-10-23, commit `f1eb108`)

| Defect | Before | After | Regression test |
|---|---|---|---|
| A1 ids | `COM-{partner}-{opp}-{timestamp}` collided within a second | `...-{8 hex}` suffix | `test_ids_unique_within_one_second`, simulation F/J |
| A2 currency | `*_usd` summed every currency | USD only + `real_confirmed_or_paid_by_currency`, `real_paid_by_currency` | `test_revenue_uses_latest_state_and_separates_currencies` |
| A3 status | no follow-up path; reversed commissions kept counting | `record_status_change()` with `ALLOWED_TRANSITIONS`; events in `<ledger>.status.jsonl`; summaries and `first_real_dollar_status()` use `transaction_states()` (latest state) | `test_status_changes_live_beside_the_ledger...`, `test_a_reversed_only_ledger_has_no_first_dollar`, simulation G |
| A4 bypass | PENDING without tx id -> CONFIRMED via status change | refused (AntiFabricationError) | `test_pending_without_transaction_id_cannot_be_confirmed_by_a_status_change` |
| A5 links | no destination check | `links.validate_destination()` | `TestDestinations`, simulation D |
| A6 approvals | APPROVED unreachable | `registry.record_approval()` / `latest_approvals()`; evidence required | `TestApprovals`, simulation A |

Compatibility: `load_ledger()` returns exactly the commission records it returned before (status changes are in a separate file), so the seven modules that read the raw ledger see no new record shape. No ledger, approval or link file in `data/` was modified.

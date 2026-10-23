# Affiliate route and gap register (2026-10-23)

## Route status

| Route / subsystem | Implementation status | Evidence |
|---|---|---|
| Program registry read model | IMPLEMENTED_AND_TESTED | simulation A/B; existing tests |
| Eligibility vs payout separation | IMPLEMENTED_AND_TESTED | simulation C |
| Program approval record | IMPLEMENTED_AND_TESTED (new) | simulation A; `tests/test_affiliate_e2e_simulation.py` |
| Link registry (domain) | IMPLEMENTED_AND_TESTED | simulation D |
| Destination URL validation | IMPLEMENTED_AND_TESTED (new) | simulation D (8 cases) |
| Content QA (disclosure, dated claims) | IMPLEMENTED_AND_TESTED | simulation A |
| Publication gate | IMPLEMENTED_AND_TESTED | simulation H |
| Click tracking (local server) | IMPLEMENTED_AND_TESTED | simulation A |
| Click tracking (public site) | BLOCKED | no receiver on GitHub Pages |
| Commission recording + anti-fabrication | IMPLEMENTED_AND_TESTED | simulation E/F |
| Commission status changes, reversals | IMPLEMENTED_AND_TESTED (new) | simulation A/G |
| Latest-state, per-currency revenue | IMPLEMENTED_AND_TESTED (new) | simulation J |
| Network report / postback import | MISSING | no code |
| Payout receipt reconciliation | MISSING | no code |
| Amazon Associates earnings | BLOCKED | tag not configured; account not created |
| Real program approval | BLOCKED | founder applications |

## Defects

| # | Component | Observed | Expected | Severity | Fix | Result |
|---|---|---|---|---|---|---|
| A1 | `commission_ledger` ids | 4 commissions in one second shared one id | unique | High (commercial_operations dedups by id) | random suffix | FIXED, tested |
| A2 | `real_commission_summary` currency | 60 USD + 15 EUR reported as 75 "usd" | USD only; per-currency map | High (wrong financial report) | per-currency totals | FIXED, tested |
| A3 | status changes | no API; a reversal raised DuplicateCommissionError; reversed money kept counting | allowed transitions, latest state counts | High | `record_status_change`, `transaction_states` | FIXED, tested |
| A4 | status change bypass (found in own fix) | a REAL PENDING without tx id could become CONFIRMED | same tx-id bar as record_commission | High | guard in `record_status_change` | FIXED, tested |
| A5 | link destinations | no validation of the URL a link sends to | https, program domain, no credentials, no off-domain redirect | Medium | `links.validate_destination` | FIXED, tested |
| A6 | approvals | no way to record an approval; APPROVED unreachable | evidence-backed record | Medium | `registry.record_approval` | FIXED, tested |
| A7 | registry classification | 3 sales channels counted as affiliate programs | separate category | Low | none yet | OPEN |
| A8 | two portfolio sources | tracked registry 17 vs untracked portfolio.py 32 | one source | Medium | coordinate with parallel session | OPEN |
| A9 | `commission_engine` own sums | naive sum (any currency, ignores status changes) compared with the authoritative summary | reuse `real_commission_summary` | Medium (false alarm when diverging) | file has parallel edits; not touched | OPEN |
| A10 | `networks.build_amazon_url` | tag appended unencoded from env | encode / validate | Low | none yet | OPEN |

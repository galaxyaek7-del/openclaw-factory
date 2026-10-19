# Cycle 103 — Permanent Operating Doctrine Integration

**Date:** 2026-10-19
**Scope:** integrate the operating doctrine into the repository as enforced
layers with tests and one gate. No product was published, no money was spent, no
product record was mutated.
**Prior release:** Cycle 102 at `9a096b0` (verified).

---

## 1. Objective

Turn the doctrine from prose into artifacts: each rule has a module that
enforces it, a test that proves it, and a single gate that fails when a layer is
outside its rule — plus a real gap matrix showing what exists, what is partial,
and what is unknown.

## 2. Deliverables

| Artifact | Purpose | Verification |
|---|---|---|
| `incident_memory.py` | durable incident records with 15 fields; a control whose reference does not exist on disk is rejected | `data/incident_memory.jsonl` (5 records), `audit()` ok |
| `cycle_metrics.py` | files changed, repeated checks and why, defect split, honest timing | `data/cycle_metrics.jsonl` (2 cycles), `repetition_audit()` ok |
| `handoffs.py` | 7-field contracts; `BLOCKED` needs a delay reason; `ACCEPTED` needs existing evidence | `data/handoffs.jsonl` (11 handoffs, 0 invalid) |
| `weak_signals.py` | no verdict from one observation: 3 signals, 2 independent groups | `data/weak_signals.jsonl` (3 signals, 0 triggered) |
| `business_arms.py` | 8 arms, 5 states, computed from path existence; `REVENUE_VERIFIED` unreachable without attribution | 8 arms, 0 ready, 0 revenue-verified |
| `doctrine_review.py` | claim-vs-reality audit + the 6 doctrine-review questions | 14 material claims, 0 critical, 10 warning |
| `scripts/check_doctrine.py` | single gate, read-only, exit 1 on any HOLD | exit 0 (8 checks) |
| `tests/test_doctrine_layers.py` | proves each layer's rule and the real repository invariants | 53 tests, all passing |
| `OpenClaw_Brain/00_Governance/PERMANENT_OPERATING_DOCTRINE.md` | the doctrine itself, cross-referenced from the constitution | layer matrix EXISTS ×9 |
| `reports/DOCTRINE_REVIEW_2026-10-19.{md,json}` | generated review of the rules from evidence | regenerated this cycle |
| `operational_history.py` | UNKNOWN protocol vocabulary extended with `ESTIMATED`/`BLOCKED` | snapshot rewritten; 0 transitions appended |

## 3. Gap matrix

| Layer | Before | After | Enforcement / test |
|---|---|---|---|
| Incident memory | MISSING | EXISTS | `incident_memory.py` + `audit()` |
| Claim vs. reality | PARTIAL (states existed, no rate) | EXISTS | `doctrine_review.audit_structured_claims()` |
| UNKNOWN protocol | PARTIAL (4 labels) | EXISTS | `operational_history.LABELS` (6 labels) |
| Rework / cycle time | MISSING | EXISTS | `cycle_metrics.py` |
| Handoff contracts | MISSING | EXISTS | `handoffs.py` |
| Risk budget | EXISTS | EXISTS | `safe_mode.py`, `publish_protection.py` |
| Weak signals | MISSING | EXISTS | `weak_signals.py` |
| Doctrine review | MISSING | EXISTS | `doctrine_review.py` |
| Business arms | MISSING | EXISTS | `business_arms.py` |

`UNKNOWN` remains for two things the doctrine names but nothing measures:
doctrine-cost telemetry, and per-cycle wall-clock time.

## 4. Real findings from the claim audit

The audit found exactly three classes of real, current discrepancy — none of
which was fabricated as a "clean" result:

1. **Registry drift (3 products).** `data/product_batch_12.json` says
   `READY_FOR_REVIEW` for B12-001, B12-003, and B12-004, while
   `data/operational_history.json` records them `CHECKOUT_VERIFIED`. Classified
   `WARNING`: the registry is behind, not ahead. The evidence ledger remains the
   state source.
2. **Task-title identity (6 titles).** Both product-specific task files
   (`data/first_sale_tasks_b12-003.json`, `_b12-004.json`) carry three tasks
   each, all titled for B12-001. Classified `WARNING`. Payloads are correct for
   their own product.
3. **One release-baseline `PASS` row with no file reference.** B12-010's
   "deadline states and post-award cadence match the documented rule" cites prose
   only ("recalculated by Excel and re-derived independently in Python").
   Classified `WARNING`. The verification is real; the record does not name the
   artifact, which is the correct thing for the audit to surface.

Critical unsupported claims: **0**. Warnings: 10. Unsupported rate: **0.0**.

## 5. Corrections made during this cycle

Both are recorded because they are the doctrine's own mechanism working:

- **My first reading of the task-title defect was wrong.** An ad-hoc scan
  suggested 12 mismatched titles across all four `first_sale_tasks*` files. The
  audit module, which derives identity from the file's own product id, showed the
  generic `first_sale_tasks.json` and the cycle-94 backup are real B12-001 runs
  whose titles are consistent. The true scope is **6 titles in 2 files**. The
  incident record, the operational-learning baseline, and the doctrine were
  corrected to match. This is exactly the claim-vs-reality discipline applied to
  this cycle's own claims.
- **`operational_history.LABELS` was missing `ESTIMATED` and `BLOCKED`**, so the
  snapshot could not have expressed either. Extended; the snapshot was
  regenerated (the only changes were the label list and the timestamp; 0
  transitions appended).

## 6. Business arms (computed, not asserted)

`python business_arms.py` — 0 `REVENUE_VERIFIED`, 0 `READY`, 4 `PARTIAL`,
2 `BLOCKED`, 2 `PLANNED`. `READY` is refused while any gap or external dependency
is named; `REVENUE_VERIFIED` is refused without per-arm attribution, which does
not exist anywhere in this factory.

Blocked arms: Digital Products (founder listing authorization and a live Gumroad
write credential) and Affiliate Intelligence (a real Amazon Associates account).

## 7. Verification run this cycle

```
python incident_memory.py --seed --audit          -> 5 written, audit ok
python cycle_metrics.py --seed --audit --summary  -> 2 cycles, no repetition
python handoffs.py --seed --audit --open          -> 11 written, 0 invalid, 7 open
python weak_signals.py --seed --reviews           -> 3 written, 0 triggered
python business_arms.py                           -> 8 arms, validate []
python doctrine_review.py --claims                -> 0 critical, 10 warning
python scripts/check_doctrine.py                  -> exit 0
python operational_history.py --write --check     -> OK, 0 transitions
pytest tests/test_doctrine_layers.py              -> 53 passed
```

## 8. Limitations and disclosures

- **The task-title generator is not corrected.** The defect is detected, not
  prevented at source; the incident's `remaining_uncertainty` says so.
- **The title detector only inspects files named with a product id.** The
  generic and backup files are skipped by construction; they happen to be
  consistent, so nothing is missed today, but a future generic file carrying a
  wrong title would not be flagged.
- **One warning cannot be eliminated by code**: a `PASS` row that cites prose
  instead of a path is legitimate and is reported, not failed.
- **Doctrine-cost telemetry does not exist**, so "which rules are redundant" is
  `UNKNOWN`, not "none".
- **Cycle timing is unmeasured** (no timer); recorded as `measured: false` with a
  reason.
- **The full repository test suite is not run** (over 50 minutes, known
  pre-existing failures elsewhere); bounded groups only.
- **B12-010 remains unpublished** — no founder authorization phrase exists and no
  live Gumroad write credential is present. `FACTORY_LIVE_PUBLISH=false`.
- **Revenue is $0.00.** No product is `FIRST_SALE_VERIFIED`; nothing here changes
  that, and no artifact claims otherwise.

## 9. What did not change

No product artifact, hash, price, listing, or platform state. No spend. No new
execute-capable path: `check_doctrine.py` is read-only, and every layer module
either appends to its own new ledger or reads.

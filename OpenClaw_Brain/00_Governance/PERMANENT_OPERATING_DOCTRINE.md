# Permanent Operating Doctrine

**Status:** ratified 2026-10-19. Applies to every cycle from Cycle 103 onward.
**Relationship to existing governance:** this file is the *operating* doctrine —
how a cycle is run and what proves it. `MASTER_OPERATING_CONSTITUTION.md` remains
the constitution and ADR index; it is not replaced or superseded. Where a rule
here is also a constitutional rule, the constitution wins and this file only
restates the operational consequence. No competing constitution is created.

---

## 1. Purpose

Galaxy Forge is run as a living factory: it observes, builds, verifies, records,
and learns, and it does so without pretending. The doctrine exists to make three
failure modes structurally difficult:

1. **Claim drift** — a record saying something is done when only part of it is.
2. **Repeat failure** — the same class of defect arriving twice because nothing
   durable remembered the first one.
3. **Silent stall** — work sitting between two roles with nobody able to see it.

Every rule below names the artifact that enforces it. A rule with no artifact is
listed as `NOT IMPLEMENTED` in section 12 rather than assumed to hold.

---

## 2. Evidence vocabulary

Six labels, used in every record and never collapsed into "done":

| Label | Means |
|---|---|
| `OBSERVED` | read directly from a system of record in this session |
| `DERIVED` | computed from observed values by a stated rule |
| `INFERRED` | concluded from other evidence, stated as a conclusion |
| `ESTIMATED` | a modelled value with a stated basis; never presented as measured |
| `UNKNOWN` | no supporting signal exists |
| `BLOCKED` | a named dependency prevents progress right now |

`UNKNOWN` is a real answer. `BLOCKED` always names the dependency. Enforced in
`operational_history.py` (`LABELS`), `incident_memory.py` (`LABELS`),
`weak_signals.py` (`CONFIDENCE_LABELS`), and `truth_first.py`
(`CANONICAL_VOCABULARY`).

---

## 3. Layers and their enforcement

| Layer | Rule | Artifact | Verification |
|---|---|---|---|
| 3A Incident memory | a failure is not "handled" until a control prevents recurrence | `incident_memory.py` | `audit()` fails a record with no control or a repeated signature |
| 3B Risk budget | $0 spend; at most three active experiments; protected actions gated | `safe_mode.py`, `channels/publish_protection.py` | `tests/test_resilience.py` |
| 3C UNKNOWN protocol | every material statement carries one of the six labels | `operational_history.py`, `truth_first.py` | `tests/test_doctrine_layers.py` |
| 3D Handoff contracts | work crosses a boundary only with seven named fields | `handoffs.py` | `validate_handoff()`; `ACCEPTED` requires existing evidence |
| 3E Doctrine review | the rules themselves are reviewed from evidence, not opinion | `doctrine_review.py` (section 3E questions) | `build_doctrine_review()` |
| 3F Weak signals | no verdict from one observation; three signals, two independent groups | `weak_signals.py` | `review_triggers()` |
| 3G Claim vs. reality | a material claim must trace to evidence, with a measured rate | `doctrine_review.audit_structured_claims()` | critical count must be zero |

### 3A — Incident memory

Fifteen fields per record, including `detection_mechanism.status`
(`DID_NOT_EXIST` / `EXISTED_AND_MISSED` / `EXISTED_AND_FIRED` / `NOT_APPLICABLE`),
`why_not_caught`, `root_cause.verified` vs `root_cause.hypothesis`,
`preventive_control` (kind + a real artifact reference), `rules_left_unchanged`,
`verification`, and `remaining_uncertainty`. A root cause that is only a
hypothesis is recorded as a hypothesis. A control whose reference does not exist
on disk is rejected at record time.

The store is append-only and deduplicated by id. The audit fails the build when a
record has no preventive control or when the same `component|title` pair appears
twice.

### 3B — Risk budget

- Spend on external tools and ads stays **$0.00** until a verified sale exists.
- At most **three** active experiments at once.
- Publishing, spending, and account creation remain founder-gated
  (`simulation_mode.py`, `channels/publish_protection.py`): `FACTORY_LIVE_PUBLISH`
  stays `false` and the production path raises rather than acting when it is off.

### 3C — UNKNOWN protocol

A statement is admissible only if its label is one of the six in section 2. The
protocol exists because the two expensive mistakes are opposite: stating a
`DERIVED` value as `OBSERVED`, and leaving a genuine gap blank so that a reader
assumes it is fine. `BLOCKED` requires the dependency to be named, not implied.

### 3D — Handoff contracts

Seven fields: `deliverable`, `acceptance_criteria`, `owner`, `due`,
`evidence_required`, `status`, `evidence`. A handoff in `BLOCKED` must state
`delay_reason`; a handoff in `ACCEPTED` must cite evidence that exists. Open
handoffs are visible by design — `open_handoffs()` and `delays()` exist so a
stalled handoff is a recorded state, not a discovery made months later.

### 3E — Doctrine review

Six standing questions, answered from records rather than memory, each with a
label: which rules demonstrably improved an outcome; which are redundant or
expensive; which repeatedly fail in practice; which failures were implementation
rather than policy; which new risks require a change; which safeguards must
remain regardless of use frequency. See section 11 for the command.

### 3F — Weak signals

A signal carries `source`, `source_date`, `independent_group`, `topic`,
`summary`, `relevance`, `confidence`. A topic triggers review only at three
signals from at least two independent groups. One striking observation is
recorded and produces no verdict.

### 3G — Claim vs. reality

Eight distinct states exist for a product, and they are never collapsed (section
10). The audit separates three cases that look alike and are not:

- **critical** — a cited evidence path does not exist, a status contradicts the
  evidence ledger, or a `PASS` row's own evidence says the check was not run.
- **warning** — a `PASS` claim whose evidence is prose with no file reference.
- **clean** — every material claim names evidence that exists.

---

## 4. Rework and cycle time

Every cycle records files changed, deliverables, checks repeated *and why*,
defects by severity, and the split between new defects and pre-existing ones.
`rework_ratio()` reports the new-defect share. A cycle is flagged when it
produced no artifact, repair, capability, or decision-relevant evidence, and when
its deliverables are identical to the previous cycle. Time is recorded as
`measured: false` with a reason unless a real timer exists — an unmeasured cycle
is never reported as fast.

---

## 5. Business arms

Eight specialized arms share one operating layer (this doctrine, the ledgers, the
gates). Five states, and an arm is never `READY` because code or plans exist:

| State | Means |
|---|---|
| `READY` | every acceptance criterion met and a commercial path exists |
| `PARTIAL` | implementation evidence exists, named gaps remain |
| `PLANNED` | no implementation evidence for the arm itself |
| `BLOCKED` | implementation exists but a named dependency stops progress |
| `REVENUE_VERIFIED` | real external revenue attributable to this arm |

`REVENUE_VERIFIED` is unreachable today: revenue is recorded company-wide and no
per-arm attribution exists anywhere in this factory. That is a real structural
gap, not an oversight, and `business_arms.validate_arm_states()` refuses the
state without attribution. Current real state, as of Cycle 103:
**0 `REVENUE_VERIFIED`, 0 `READY`, 4 `PARTIAL`, 2 `BLOCKED`, 2 `PLANNED`.**
Re-derive with `python business_arms.py`; the numbers are a snapshot, not a rule.

---

## 6. Proving ground

Gumroad is the proving ground because it is the only live rail: Paddle returns
403 and the X publishing arm is blocked by depleted credits. The rule is
sequence, not preference — reach a real first sale on one rail before widening.
Preparation, authorization, and platform access remain three separate things
(section 10); a prepared product is not an authorized one, and an authorized one
is not necessarily reachable in this environment.

---

## 7. Commercial priority

Order of work when capacity is limited: (1) anything blocking a verified sale,
(2) verification of what already claims to be done, (3) closing a defect class
that has recurred, (4) new capability. Governance artifacts are not exempt — they
are subject to the same rule, which is why this doctrine ships with tests and a
gate rather than prose alone.

---

## 8. Safety

- Publication, spending, account creation, and destructive actions stay
  founder-gated. No cycle performs them unattended.
- Four protections remain regardless of how rarely they are exercised: evolution
  execute, capital reallocation, business retirement, and first / elevated-risk
  publishing.
- Simulation and production stay separated: simulated outcomes are labelled and
  kept out of real ledgers (`simulation_mode.py`, `revenue_truth.py`).

---

## 9. Phases

**Phase 1 — structure.** Record the layers, their artifacts, and the gaps. This
document plus the modules referenced above.

**Phase 2 — operate.** Run cycles under the doctrine: incident records for every
real failure, handoffs between roles, weak signals recorded rather than acted on,
the claim audit at zero critical.

**Phase 3 — commercial.** Convert the prepared work into a verified sale, which
is the only thing that moves `REVENUE_VERIFIED` off zero.

---

## 10. Definition of success

Seven states per product, never collapsed:

| State | Proves |
|---|---|
| `BUILD_COMPLETE` | artifacts exist |
| `QA_PASS` | a real quality gate approved them |
| `READY_FOR_AUTHORIZATION` | prepared to be authorized |
| `UPLOAD_COMPLETED` | a write reached the platform |
| `PUBLIC_LISTING_VERIFIED` | a public page serves the product |
| `CHECKOUT_VERIFIED` | a checkout path is live |
| `FIRST_SALE_VERIFIED` | a real external transaction occurred |

Success is the last row and nothing else. `CHECKOUT_VERIFIED` is not a sale;
`UPLOAD_COMPLETED` is not a public listing. Real current position: three products
at `CHECKOUT_VERIFIED`, three at `READY_FOR_AUTHORIZATION`, four at
`BUILD_COMPLETE`, **zero at `FIRST_SALE_VERIFIED`**, company revenue **$0.00**.

---

## 11. Running the checks

```powershell
python incident_memory.py --seed --audit
python cycle_metrics.py --seed --audit --summary
python handoffs.py --seed --audit --open
python weak_signals.py --seed --reviews
python business_arms.py
python doctrine_review.py --claims
python doctrine_review.py --write
python scripts/check_doctrine.py
```

`scripts/check_doctrine.py` exits non-zero if any layer is outside its rule. It
does not publish, spend, or write a ledger.

---

## 12. Open gaps

Recorded as `UNKNOWN` or `NOT IMPLEMENTED` rather than assumed:

- Per-arm revenue attribution (`REVENUE_VERIFIED` unreachable).
- Doctrine-cost telemetry — no rework is attributable to a specific rule, so no
  rule can be called redundant from evidence.
- Per-cycle wall-clock timing — no timer is running; timing is unmeasured.
- `customer_site` DRAFT banners on two pages, disclosed and out of scope here.
- The full repository test suite (over 50 minutes, known pre-existing failures)
  is not run by the doctrine gate.

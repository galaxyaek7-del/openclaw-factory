# Galaxy Forge — Commercial Flight Control & First-Real-Dollar Execution: Final Report

**Date:** 2026-08-09 | Directive: "Commercial Flight Control & First-Real-Dollar Execution" (Phase 39, ADR-236)

Role held throughout: Chief Commercial Engineer + Reliability Engineer. Per the directive's own closing instruction: **be brutally honest, optimize for becoming genuinely ready, not for appearing ready.**

---

## A. What already existed

The entire commercial production chain from Phase 33 through Phase 38b/Resilience Hardening: a 13-real-opportunity portfolio (`commission_engine.py`, evidence-cited via `business_development.py`); a 13-dimension scoring function; a ranked shortlist (`rank_commission_shortlist()`); an opportunity lifecycle state machine (`opportunity_rotation_engine.py`, PURSUE/WATCH/ABANDON/ROTATE); real lead discovery over 3 legitimate sources (`lead_discovery.py`); an outreach adapter with an 11-field exact-scope CEO approval gate and a real expiration check (`outreach_adapter.py`); a real, anti-fabrication-guarded commission ledger (`commission_ledger.py`, `AntiFabricationError`); a formal `FIRST_REAL_DOLLAR` gate; and — from the immediately preceding Resilience & Stress Hardening round — real atomic writes, a real backup/restore cycle, and 4 real 10x sequential-retry idempotency proofs. `AUDIT/RESILIENCE_CERTIFICATION.md` classified the whole system **B — operationally strong but not ready** the day before this round began.

## B. What was genuinely missing

1. **One authoritative flight-control gate.** Two separate, real selection functions (`rank_commission_shortlist()`, `select_first_launch_opportunity()`) existed with no single function reconciling them into one verdict.
2. **A real vocabulary reconciliation** between this factory's two ledger-state naming schemes and the directive's own third naming scheme — never done before.
3. **Proof of duplicate-protection under genuine concurrency**, not just sequential retries — the existing 10x retry-storm test only ever ran attempts one after another in the same thread.
4. **A consolidated 12-field commercial control view** — the data existed across several functions but never in one shape.
5. **An explicit verification of the commission-side Golden Hunter** against a named checklist — the function existed and worked, but had never been formally audited against these 7 properties in one place.
6. **A real architecture fact nobody had stated plainly**: this factory's entire outreach-approval machinery assumes one commercial mechanism (referral outreach); Amazon Associates uses a structurally different one (self-service affiliate links). Nothing enforced that distinction before this round — a caller could have silently applied outreach-shaped checks to a link-publish opportunity, or vice versa.

## C. What was built

- `commission_engine.py::commercial_flight_control_status()` — the Section 1 gate. Returns exactly one of `LAUNCH_READY`/`FIRST_CONTROLLED_ACTION_READY`/`CEO_APPROVAL_REQUIRED`/`BLOCKED`, parameterized by `action_type` (`OUTREACH_REFERRAL` vs `AFFILIATE_LINK_PUBLISH`), checking each opportunity against its own real mechanism.
- `commission_engine.py::directive_ledger_state_mapping()` — reconciles the directive's 8 named ledger states against the two real pre-existing vocabularies (2 exact matches, 5 nearest-analog, 1 genuinely missing).
- `commission_engine.py::commercial_failure_recovery_status()` — a real citation matrix over the directive's 13 named failure cases (11 real, 2 disclosed open gaps).
- `commission_engine.py::commercial_control_panel()` — the Section 10 12-field view.
- `commission_engine.py::golden_hunter_commission_verification()` — the Section 11 audit (8 checks, all passing against live data).
- `commission_ledger.py::_LedgerLock` — a real, cross-process (msvcrt/fcntl) + intra-process (`threading.Lock`) advisory lock closing a genuine duplicate-write race found while stress-testing (see Section E).
- 5 new Mission Control panels wired end-to-end (`mission_control_api.py` + `server.js` `SERVICE_REGISTRY`): `commercial-flight-control-status`, `commercial-control-panel`, `golden-hunter-commission-verification`, plus the underlying dispatch entries.
- `select_first_launch_opportunity()` fixed to respect `opportunity_rotation_engine.py`'s real WATCH/ABANDON lifecycle state (it previously didn't know that ledger existed).

## D. What was tested

34 new regression tests across `tests/test_commission_engine.py` and `tests/test_commission_ledger.py`: the 4 named gate verdicts; action-type/opportunity mismatch handling; WATCH-state exclusion; expired/mismatched-scope approval refusal; the ledger-state mapping's honesty about the one genuinely missing state; the failure-recovery matrix's honest REAL/OPEN_GAP split; the 12-field control panel's exact field set; the Golden Hunter verification's 8 checks plus a fabricated-entry detection test; a structural mock-based proof that the read-only functions never call `record_commission`; and — the most consequential new tests — real 10x and 25x genuine `ThreadPoolExecutor` concurrency races proving the duplicate-commission guard now holds under true concurrency, not just sequential retries.

A full repo-wide regression was run: **3371 tests, 4439.6s (~74 min), 4 failures — all 4 the same single pre-existing test** (see Section E).

## E. What failed

1. **The real concurrency race** (Section 9's own realistic stress check): 10 genuinely concurrent threads recording the identical `external_transaction_id` produced 3 separate REAL commission records instead of 1, before the fix. This directly contradicted Section 7's own requirement and was not previously caught because the existing idempotency test only exercised sequential retries.
2. **A real Windows-specific locking bug found while fixing #1**: `msvcrt.locking(LK_LOCK)` raised `OSError: [Errno 36] Resource deadlock avoided` under 25-thread same-process contention — a genuine platform quirk (Windows same-process byte-range lock detection), not a hypothetical.
3. **A pre-existing, unrelated failure** surfaced by the full regression run: `tests/test_publish_protection.py::test_hitting_daily_cap_blocks_further_publishes` fails when run near a real UTC midnight rollover (`channels/publish_protection.py`'s daily-cap `day_bucket` logic mis-buckets publishes spaced across a real day boundary). Reproduced and diagnosed in isolation — confirmed unrelated to any Phase 39 change (no Phase 39 commit touches `channels/publish_protection.py`).

## F. What was fixed

\#1 and \#2 above were fixed this round (`commission_ledger.py::_LedgerLock`, combining a `threading.Lock` with the real cross-process file lock). \#3 was **not** fixed — it is a real, pre-existing bug in an unrelated subsystem, outside Phase 39's explicit scope ("do NOT redesign the factory"). It is disclosed here for the founder's own future action, not silently left undocumented.

## G. What remains blocked

- **Track A (Outreach Referral)**: no `OUTREACH_SMTP_*` credential configured; no real qualified lead on file (the one real live discovery run, Phase 37B, found 0/6 qualified); no CEO approval object has ever been created.
- **Track B (Affiliate Link Publish, Amazon)**: `AMAZON_ASSOCIATE_TAG` unset; no real Amazon Associates account exists; zero real clicks ever recorded.
- **2 disclosed, unfixed operational gaps** carried forward from the Resilience round: no disk-full handling anywhere; nothing restarts `scripts/supervisor.js` if it dies.
- **1 pre-existing, unrelated bug**: the `channels/publish_protection.py` day-boundary test failure (Section E.3).

## H. What requires CEO/human action

Configuring a real outreach-sending credential; running (or re-running) a real lead-discovery pass and manually reviewing candidates; creating and approving a real Amazon Associates account, or explicitly deciding not to pursue that track; issuing a real, exact-scope, time-bounded approval object for any specific outreach send; deciding whether/how to address the 3 disclosed open gaps (disk-full handling, supervisor meta-restart, the publish-protection day-boundary bug) in a future, separately-scoped round.

## I. Shortest path to the first controlled commercial action

**Track A**: configure `OUTREACH_SMTP_*` → run a real lead-discovery pass and get ≥1 real `QUALIFIED` lead → prepare a scoped draft → founder issues a real, exact-scope, time-bounded approval → `commercial_flight_control_status()` returns `FIRST_CONTROLLED_ACTION_READY` → the one real, `MAX_REAL_SENDS=1`-capped send occurs.
**Track B**: founder creates a real Amazon Associates account and sets `AMAZON_ASSOCIATE_TAG` → `commercial_flight_control_status(opportunity_id="CO-amazon-affiliate")` returns `FIRST_CONTROLLED_ACTION_READY` → a real tagged link is published somewhere with real traffic (the controlled action itself, for this mechanism, is publication + traffic, not a single atomic send).

## J. Shortest path to the first REAL commission dollar

Beyond I, both tracks then require a genuine external event this system cannot manufacture or accelerate: a real prospect converts (Track A) or a real visitor clicks and buys within the cookie window (Track B). Neither path has a code blocker beyond the human actions in Section H — both are now honestly blocked on real-world commercial activity, not on missing software.

## K. What must NEVER be automated

Configuring any outreach-sending credential. Configuring `AMAZON_ASSOCIATE_TAG` or creating any real external account. Issuing a CEO exact-scope approval object (a generic `approved=true` is structurally insufficient and always will be — `verify_exact_scope_approval()` enforces this). Sending any real outreach message. Recording a REAL/CONFIRMED-or-PAID commission without real, human-supplied evidence and a real external transaction id (`AntiFabricationError` is the permanent, structural enforcement of this). Lifting any of the 4 standing founder-protected gates (evolution execution, capital reallocation, business retirement, new-channel/elevated-risk publishing) — untouched by this round, exactly as every prior round this session reconfirmed.

## L. Current launch readiness verdict

**BLOCKED**, honestly and correctly, on both tracks — via `commercial_flight_control_status()`'s own live computation, not a documentation claim. This is not a regression from the Resilience round's **B** classification; it is a more precise, mechanism-aware statement of the same real state that classification already described. The gate itself, the duplicate-protection guarantee, and the Golden Hunter's honesty are now real, tested, and — after this round's fix — provably correct under genuine concurrency, which they were not before.

---

## Required verbatim answers

### WHAT IS THE SINGLE SHORTEST SAFE PATH FROM THE CURRENT FACTORY STATE TO THE FIRST REAL COMMISSION DOLLAR?

There is no single shortest path — this factory's own two real selection functions genuinely disagree (Amazon vs. Adobe/n8n), and neither disagreement was artificially resolved this round. The honest answer is two parallel, comparably-short real paths (Runbook Tracks A and B), each blocked on exactly one class of human action (a credential + a qualified lead + an approval, or an external account + real traffic) followed by one genuinely unpredictable external event (a real prospect or customer converting). Whichever the founder chooses to pursue, the shortest *safe* path is: clear the real human blockers in Section H for that track, let `commercial_flight_control_status()` confirm `FIRST_CONTROLLED_ACTION_READY` live, take the one real controlled action, and let `first_real_dollar_status()` report the outcome honestly — never accelerated, never assumed.

### WHAT EXACT HUMAN ACTION IS REQUIRED BEFORE THE FACTORY MAY TAKE THAT CONTROLLED COMMERCIAL ACTION?

For Track A: the founder must (1) configure a real `OUTREACH_SMTP_*` credential, (2) obtain at least one real `QUALIFIED` lead (via a real lead-discovery run, manually reviewed), and (3) issue a real, exact-scope, time-bounded CEO approval object matching a specific prepared draft exactly. For Track B: the founder must create a real Amazon Associates account (this system cannot do so — a standing, unconditional prohibition) and set the real `AMAZON_ASSOCIATE_TAG`. No code path in this factory can substitute for either.

---

## Hard Stop

Per the directive: full regression run (3371 tests, 4 failures — all pre-existing and unrelated, see Section E.3, none in Phase 39's own new code). Git status inspected: 102 commits ahead of `origin/main`, not pushed. No outreach sent (`REAL_OUTREACH_SENT=0`, confirmed via `first_real_dollar_status()` before and after this round). No credential configured. No external commercial action executed. No Phase 40 initiated. Waiting for founder review.

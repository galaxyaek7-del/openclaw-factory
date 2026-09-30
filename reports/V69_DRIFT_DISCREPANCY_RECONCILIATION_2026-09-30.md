# V69 CTO DISCREPANCY REPORT — 17K vs 2,099 reconciled (2026-09-30)

## 1. ORIGINAL DRIFT CLAIM — exact source and methodology

Source: `reports/V68_CTO_DRIFT_FORENSIC_RECONCILIATION_2026-09-30.md` §2/§17
+ `data/factory_baseline_manifest.json` (`counting_methodology` field).

- Baseline: `main @ 5fd3c56` (2026-09-30 08:58 +0200).
- Command: `git diff --numstat` — **unstaged tracked modifications only**.
- Result: **+17,328 / −2,219 across 80 files**.
- Census: 82 modified tracked, 1,457 untracked, 0 staged, 0 deleted.
- Whitespace control: `-w` changed totals <0.2% (no line-ending artifact).
- Excluded by construction: staged changes, untracked files (counted by
  file-count + bytes only), ignored files (`.env`, nostr key, node_modules).
- No renames/copies/deletes in the population (0 deleted; renames not detected).

**V69 reproduction** @ `HEAD 98922af` (the V68 commit itself):
`git diff --numstat` → **+17,329 / −2,219, 81 text files + 2 binary zips**
(`cohort_GF_BATCH11_2026_09/dist/*.zip`, line counts N/A).
Delta vs V68 (+1 line, +1 file) is live-ledger growth between runs, not a
methodology difference. **The 17K figure reproduces. It was never wrong —
it was unparsed.**

## 2. CURRENT 2,099-LINE CLAIM — exact source and population

Source: V68 §3/§6 (same numstat output, filtered).

- Population: tracked `*.py` / `*.js` **excluding** `tests/` — additions only.
- Result: **+2,099 / −60 across 13 files**:
  server.js +919 · factory_loop.js +442 · production_os.py +286 ·
  mission_control_api.py +135 · lib/telegram_commands.js +86 ·
  distributor.py +80 · channels/gumroad_publisher.py +73 ·
  channels/gumroad_arm.py +43 · profit_oracle.py +18 ·
  affiliate_commerce/click_tracking.py +10 · affiliate_discovery.py +5 ·
  channels/publish_protection.py +1 · lib/publisher_seo.js +1.
- Security scan over exactly these lines: 0 secrets, 0 key blocks,
  0 external fetches (V68 §6; staged-file extension in §7 below).
- 2,099-LINE POPULATION → 13 files above → SOURCE only → baseline HEAD →
  measured 2026-09-30 (V68 cycle; re-verified byte-identical V69).

## 3. MATHEMATICAL RECONCILIATION

17,329 (unstaged text) − 2,099 (source) = **15,230**, accounted line-for-line:

| CATEGORY | LINES +/− | IN 17K? | IN 2,099? | EXECUTABLE? | ACTION |
|---|---|---|---|---|---|
| SOURCE (unstaged) | +2,099/−60, 13 files | YES | YES | YES | owner review/commit |
| SOURCE (staged-new) | +1,372/−0, 4 files | **NO** | **NO** | YES | see §3b |
| LEDGER jsonl | +6,622/−10, 22 files | YES | NO | NO | keep unversioned |
| DOCS md | +6,567/−537, 7 files | YES | NO | NO | keep unversioned |
| SNAPSHOT rewrite | ±1,170, golden_opportunities.json | YES | NO | NO | net-zero rewrite |
| TESTS | +551/−314, 8 files | YES | NO | test-only | companion to stream |
| DATA snapshots | +264/−25, 10 files | YES | NO | NO | keep unversioned |
| HTML | +2/−102, 18 files, net −100 | YES | NO | NO | uninspected, note |
| MISC | +54/−1, 2 files | YES | NO | NO | note |
| GENERATED binary | 2 zip bundles, N/A | YES (as `- -`) | NO | NO | artifacts, not code |

Added check: 6622+6567+2099+1170+551+264+2+54 = **17,329** ✓.
Removed check: 10+537+60+1170+314+25+102+1 = **2,219** ✓.
`-w` control V69: +17,310/−2,200 (delta 19/19, <0.2%) — no artifact ✓.

### 3b. The lines in NEITHER figure (+1,372 staged)

4 staged-new (indexed, uncommitted) files, absent from HEAD
(`git cat-file -e HEAD:lib/factory_lock.js` → "exists on disk, but not in HEAD"):

- `arms/affiliate/affiliate_engine.js` +209
- `lib/factory_lock.js` +115
- `lib/qa_engine.js` +538
- `src/attribution/attribution_os.js` +510

**True HEAD-vs-worktree divergence: +18,701 / −2,219 across 85 files**
(`git diff HEAD --numstat` = staged + unstaged). Both prior figures used
bare `git diff --numstat` and were blind to staged content.

## 4. ACTUAL RUNNING CODE

Entry points (per CLAUDE.md): `node scripts/supervisor.js` → `server.js`;
`SUPERVISOR_TARGET=factory_loop.js` → `factory_loop.js`. The supervisor
executes **working-tree files, not the HEAD commit** — running = HEAD + drift
by construction (V68 manifest; still true).

- Drifted `server.js` (working tree) requires all 4 staged files at top level
  (lines 17/19/21/22 — all 4 `require` lines are themselves ADDED drift lines;
  `HEAD:server.js` contains none of them). Verified: all 4 modules load clean
  (`STAGED-REQUIRES-OK`); HEAD is self-consistent without them.
- Classification: CANONICAL (HEAD) = consistent baseline; NON-CANONICAL =
  13-file source drift + 4-file staged chain (the actual delta in behavior);
  GENERATED = 2 zip bundles + PDFs/covers on disk; UNTRACKED = 1,453 files
  (reports, scratch scripts, companion tests, runtime logs — not executed by
  the entry points); UNKNOWN = none material (stray 15-byte `-w` file, 2026-09-21,
  `{"status":"ok"}` — redirect accident, non-executable, harmless).
- Live-system note: the tree grew ~4 lines between two detector runs minutes
  apart — the factory appends while being measured. Forensic numbers are
  point-in-time by nature here.

## 5. CANONICAL BASELINE

- CANONICAL_BASELINE_SHA: `98922af` (V68; self-consistent — no HEAD module
  requires uncommitted files).
- RUNTIME_BASELINE: working tree = `98922af` + 18,701 added / 2,219 removed
  (85 files + 2 binary). Legitimately different from canonical: the supervisor
  runs the tree, never the commit.
- DEPLOYMENT_BASELINE: same working tree (no containers, no CI, no remote
  deploy). `origin/main` is 13 commits behind (V5.8→V68 local-only, unpushed).
- REPRODUCIBILITY: HEAD alone = REPRODUCIBLE; working-tree runtime from HEAD
  alone = NOT (needs the 85-file drift incl. staged chain).
  Overall: **PARTIALLY_REPRODUCIBLE** — same label as V68, new precise reason.

## 6. DRIFT DETECTOR — test results

Old code used `git diff --numstat` (misses staged). **Proved in isolation:**
a 600-line staged-new `.py` reported WITHIN_THRESHOLDS (exit 0) — the exact
mechanism that hid the 1,372 staged lines from every prior number.

Safe one-line fix applied (V69, internal/reversible, no side effects):
`git diff --numstat` → `git diff HEAD --numstat` in `scripts/drift_detector.py`.
Temp-repo suite (fresh `git init` outside the factory): A PASS · B PASS
(staged now trips ABOVE, exit 2) · B2 PASS · C LIMITATION (docs/ledger mass
never trips source thresholds — by design; `diff_added` still shows it) ·
D LIMITATION (untracked `.py` counted but never thresholded) · E PASS.
Live V69: ABOVE_THRESHOLDS, `source_added` 2,099 → **3,471** (staged now
visible in top-10: qa_engine +538, attribution_os +510). Full matrix:
`data/factory_drift_detector_test.json`.

## 7. SECURITY — material findings only

- Staged 1,372 lines scanned (the population V68's 2,099-line scan never saw):
  **0 secrets, 0 external URLs, 0 telegram/finance/child_process references**
  across all 4 files. Same clean profile as the 2,099.
- `lib/` secret grep: 1 hit — a `GROQ_KEY-missing` error string (reads env,
  embeds nothing). Clean.
- Ignored secrets verified: `.env` ignored; `data/nostr_key` does not exist.
- No new attack surface beyond V68's reviewed 12 public routes (trial/*
  isolated, interest intake rate-limited + honeypot, execFile-by-argv no shell).

## 8. COMMERCIAL IMPACT

- Verified transactions: **0**. Verified revenue: **$0.00**
  (`finance_data.json`: sales [], all platform totals 0; `config/reality.json`:
  `published_books` 0 items — ground truth unchanged).
- Qualified intent: **0** (sales_ledger 94 rows; last 70 all `publish_attempt`, 0 sale-like).
- Exposure: ~50 real Gumroad listings published 09-20→09-28 (per V68 row parse,
  uncontested) + 2/2 nostr relay acceptances (protocol-level, EXP-SUB-001).
- Unknowns: EXP-SUB-001 window outcome (closes 2026-10-02T03:00Z), audience, WTP.

## 9. EXP-SUB-001 — integrity

**Untouched and uncontaminated.** Zero network calls this cycle (no
webfetch/websearch; only local git/python/node reads). Zero writes to
experiment/observation/hypothesis/selection records — the sole repo write is
`scripts/drift_detector.py` (forensic tooling). Checksums pinned for
`nostr_sub_observation/exposure.json`, `market_test_state.json`,
`hypothesis_register.jsonl`, `experiment_registry.json`, `v64_selection.json`,
`decision_record_001.json` (see validation). Window open to 2026-10-02T03:00Z;
no probe, repost, re-poll, or publish path touched. No historical evidence repaired.

## 10. REPRODUCIBILITY

**PARTIALLY_REPRODUCIBLE** — HEAD (`98922af`) is self-consistent and boots
without the drift; the running tree (HEAD + 18,701/−2,219) cannot be rebuilt
from HEAD alone. Minimum repair: commit the 17-file executable stream
(13 unstaged + 4 staged) as one reviewed unit.

## 11. A/B/C VALIDITY — factual consequences

The forensic facts ARE now established, so A/B/C are decidable — but V68
framed them around "~2.1k lines". Corrected scope: **3,471 source lines
across 17 files** (13 unstaged + 4 staged-new), plus test companions.

- **A — owner reviews + commits the stream.** Commits 17 executable files
  (+3,471/−60) + 8 test files as one unit. Resolves drift fully for source;
  ledgers/docs stay unversioned by design. Reversible via revert. Founder
  workload: review time. Running system: unchanged (tree already runs this).
  EXP-SUB-001: unaffected. Solves drift: YES for source.
- **B — CTO merges after full validation.** Same file set, fastest. CTO
  assumes behavior risk without author context (includes the previously
  unscanned 1,372 staged lines — now scanned clean V69). Reversible via
  revert. Solves drift: YES, with assumed risk.
- **C — park stream to side branch, restore HEAD-clean.** Baseline becomes
  pristine; running behavior REGRESSES (loses click-tracking, trial/interest
  routes, locks, QA engine, attribution OS — the drifted server.js requires
  files that HEAD lacks, so HEAD-clean runs the OLD server.js). Re-landing
  cost later. Solves drift: YES, at behavior cost. EXP-SUB-001: unaffected
  either way (no publish path in the stream touches the experiment).

## 12. FOUNDER DECISION

Facts sufficient: the discrepancy is resolved mathematically (§3) with one
scope correction (staged 1,372). **The Founder may choose A/B/C on the
corrected 17-file / 3,471-line scope.** No ranking offered; consequences above.

## 13. AUTONOMOUS REPAIRS (actual only)

1. `scripts/drift_detector.py` one-line fix (staged-inclusive numstat) — tested (§6).
2. `data/factory_drift_reconciliation.json` + `data/factory_drift_detector_test.json`
   (new, machine-readable evidence). 3. This report.
   NOT done (deliberately): committing the 17-file stream (another stream's
   authorship), moving the 4 staged files, touching ledgers/history/secrets.

## 14. CTO SELF-CRITIQUE

The discrepancy existed because two different populations were given one
name: an unparsed `git diff` aggregate ("17K") was read as code drift, while
a source-only filter ("2,099") was read as the whole divergence — and the
measurement command itself (`git diff` without `HEAD`) was blind to staged
content, hiding 1,372 runtime-required lines from BOTH numbers. Previous
controls failed because no baseline was pinned (audits narrated HEAD while
the supervisor ran the tree) and no detector existed until V68 — and V68's
detector inherited the same staged-blindness it was built to prevent, caught
only because V69 tested rather than trusted it. Fix discipline going forward:
always `git diff HEAD`, always decompose source/ledger/docs/data, always
test the tool against a known-planted change before citing it.

## 15. SINGLE HIGHEST-VALUE NEXT ACTION

Owner-review and commit the 17-file executable stream (Options A/B/C §11) —
every downstream improvement compounds on a trustworthy baseline; without it
they float. (Unchanged from V68; scope corrected 13→17 files.)

## 16. COST

$0.00. No services, purchases, network calls, or secret operations.

## 17. VALIDATION (exact tests)

- `git diff --numstat` + `git diff HEAD --numstat` + `git status --porcelain`
  census; category reconciliation adds to 17,329/2,219 exactly (§3).
- `-w` control: 17,310/2,200 (no line-ending artifact).
- Detector temp-repo A–E suite (4 PASS, 2 documented LIMITATIONS) + 2 live
  runs (pre-fix 2,099 / post-fix 3,471, ABOVE_THRESHOLDS both).
- `pytest tests/test_market_evidence.py tests/test_production_os.py` → **36/36 passed**.
- Staged 1,372-line secret/URL scan (0 findings) + `node -e` require-load check.
- Experiment checksums pinned (re-verified §9); finance/sales/reality re-reads.

## 18. GIT

New commit (V69): detector fix + reconciliation JSONs + detector-test JSON +
this report. The 4 staged stream files and all unstaged stream work left
exactly as found — no merge, no reset, no destructive move.

# Cycle 94 — Evidence and commercial status (2026-10-17)

## 1. Executive decision: **HOLD**
- **Local work:** complete, and CI-equivalent tests are green.
- **Remote:** the publishing bypass fix (`34c1ea5`) is **not on GitHub**. `origin/main` (`f55f660`) still carries the auto-publisher that can post live without the switch. This is the reason for HOLD.
- **B12-001:** waits on one founder action (a manual, unpublished draft).
- **Revenue:** none verified.

## 2. Evidence classes used
| Class | Meaning in this report |
|---|---|
| OBSERVED | Read directly: Gumroad API (read-only), files opened, Excel 16 recalculation, page metadata |
| DERIVED | Computed from observed data: content verdicts, similarity, hashes |
| INFERRED | Reasoned, not tested (e.g. the workbook in LibreOffice or Google Sheets) |
| UNKNOWN | Not measurable here: demand for B12-001, Gumroad support-reply routing, the Etsy competitor's price |

## 3. Committed baseline vs working tree
**The four previously failing tracked tests** (exp_c81_utm_regression, final_rehearsal, product_quality_repairs, universal_fabric_stage01):

| Tree | Result |
|---|---|
| Committed (`git archive` of `34c1ea5`) | 70 run, OK (1 skipped: gitignored PDF fixture), exit 0 |
| Working tree | 70 run, **2 failures**, exit 1 |

**The two working-tree failures come from uncommitted parallel-session changes:**
- **`test_exp_c81_utm_regression`** is locally modified to expect a *mandatory* publish gate (the change the founder rejected).
- **`test_final_rehearsal`** finds the untracked `affiliate/publish_queue.py`, which contains `enable_product(`.

**Final committed HEAD (`5fd5637`, clean archive):**
- 298 related tests OK (1 skipped);
- 5,215 tests collected, 0 unimportable;
- requirements audit: 0 undeclared hard imports.

## 4. `34c1ea5` safety assessment
- **It is the fix, not a bypass.** It removes the auto-publisher's direct Gumroad POST. Live publishing now goes through `distributor → gumroad_arm → gumroad_publisher.create_product`.
- **Tests:** the fail-closed boundary tests are 15/15. They cover:
  - the switch being off;
  - a missing or unreadable file, a missing price, the wrong file identity;
  - a duplicate title, an unreadable catalog;
  - an invalid, mismatched, reused, **malformed** or **wrong-operation** approval;
  - the daily cap.

  They are mutation-checked. Existing tests already cover stale and expired approvals.
- **The bypass exists in `f55f660` = `origin/main` (GitHub).** Exposure today is nil in practice: nothing calls it, and no product carries the labels its price gate needs. But it is reachable code.
- **Least disruptive correction:** push the local commits (`34c1ea5` onward), a fast-forward with no history rewrite. **Not pushed:** this needs founder authorization.

**Other publishing paths found:**
- **`affiliate/publish_queue.py`** (untracked, 2026-09-23): calls create → enable → update. Tested live with the switch off: **all 3 items blocked by the write gate, no network call, no state change.**
- **`autonomous_commerce_ops.py`:** mentions `enable_product()` only in text.
- **Factory loop:** `tests/test_factory_loop_publish_safety.js` passes 4/4 (missing or non-"true" switch means dry-run).

**Automation authority (Phase 8):**
- `.env` has `AUTO_PUBLISH_MODE=DISABLED`, `AUTO_PUBLISH_AUTHORIZED_BY=Founder`, `AUTO_PUBLISH_DATE=2026-10-17`. **No code reads them.**
- None of the four permissions is in effect: automation is off; external draft creation and live publication are not authorized; `FACTORY_LIVE_PUBLISH=false`.
- The "Founder" value is an unverified claim written by another session.

## 5. B12-001: quality and pricing evidence
- **Workbook:** 8,922 B, sha256 `aee8fc0b…ab8a092d`, committed in `669f9ce`.
  - **Arithmetic (OBSERVED, Excel 16):** $104.60/hr minimum, $120.29/hr with margin.
  - **Edge cases (OBSERVED):**

    | Input | Before | Now |
    |---|---|---|
    | 30 instead of 30% | $2.82/hr, silently | A message saying what to fix |
    | Tax ≥ 100%, negative pay | A negative rate | A message |
    | 0 weeks, 0 hours, text | `#DIV/0!` / `#VALUE!` | A message |

    Excel enforces the input validation.
- **Cover:** 1280×720 RGB, viewed. Clean and legible; a generic motif rather than a sheet preview.
- **Competitors (OBSERVED 20:20 UTC from page metadata):**

  | Competitor | Price | Relevance |
  |---|---|---|
  | Freelance Pricing & Proposal Kit | $19.00 | Direct |
  | Earnwise Freelance Business Toolkit | €28 (≈$31.46) | Direct |
  | Complete Freelancer Business Toolkit | $4.99 | Weak (bundle) |
  | Etsy listing | 403 | **Not evidence** |

- **Price:** **$14.99, PROPOSED.** It is below both direct comparables, but demand is UNKNOWN (0 sales).
- **Draft:** an API create is not a safe draft (observed published and public on 2026-09-17; no delete endpoint). Draft creation stays **manual**.
- **Approval packet:** `reports/B12-001/APPROVAL_PACKET_CYCLE94.md`.

## 6. The 13 replacement files (`reports/quality/REUPLOAD_MANIFEST_2026-10-17.json`)
Each of the 13 passes every check:
- valid PDF;
- hash matches the manifest;
- file tester PASS;
- same page count as the delivered file;
- text 0.98–1.00 similar to it (same product).

| Group | Files |
|---|---|
| Title printed over subtitle | ADA, FTC, Restaurant (repaired with `fix_pdf_title_overlap.py`) |
| Black boxes instead of hyphens, fixed local builds already existed | EU AI Act Audit Logging, Severance, Security Deposit, Mechanics Lien, Stripe Chargeback, CCPA, Mindfulness |
| Black boxes, repaired now from the delivered bytes with `pdf_glyph_repair.py` | Legal Case Research, SOC 2, AI Agent Blueprint |

- **Location:** **local only.** 10 are under gitignored `books/*.pdf`; 3 are untracked in `books/_reupload_2026-10-17/`.
- **Rollback:** the currently delivered originals are saved in `backups/gumroad_delivered_2026-10-17/`, with hashes recorded in the manifest.
- **Not uploaded.**

## 7. Duplicate-listing findings
These two are **not duplicates of each other.**
- **`owtmpe`:** "[Unavailable] AI Workflow QA". Published at $0; description "WITHDRAWN"; delivers nothing (no file, no content, no link); 0 sales.
- **`vhofn`:** a duplicate *title* of `akxaae` ("The 5-Minute Context Reset Playbook", $15). It delivers a cover plus near-identical habit-tracker pages. `akxaae` is the real 9-page, 1,612-word product. Both have 0 sales.
- **Recommendation:** unpublish `owtmpe` and `vhofn`, and keep `akxaae`. **Not done** (founder action).

## 8. The 15 thin products (`reports/quality/THIN_PRODUCTS_INVENTORY_2026-10-17.json`)
**All 15 have 0 sales, and no sourced price evidence for any of them.**

| Product | Price | Delivered | Action | Confidence |
|---|---|---|---|---|
| Etsy Ads ROI Playbook + Calculator | $39 | PDF 1 p | EXPAND (no calculator exists), or RENAME | high |
| Amazon FBA Reconciliation Workbook | $49 | PDF 1 p | RENAME (it isn't a workbook) + REPRICE, or EXPAND | high |
| SaaS Churn Email Pack | $39 | PDF 1 p, 268 words | EXPAND, or REPRICE | medium |
| Freelancer Scope-Creep Contract Kit | $29 | PDF 1 p | EXPAND, or REPRICE | medium |
| EU Cosmetics Responsible Person Guide | $69 | PDF 2 p, 426 words | REPRICE, or EXPAND | medium |
| EU Late Payment Recovery Kit | $59 | PDF 1 p | REPRICE, or EXPAND | medium |
| Food-Contact Materials Starter | $39 | PDF 1 p | REPRICE | medium |
| Suspended Seller First-Appeal POA System | $39 | PDF 2 p | REPRICE | medium |
| Digital-Product Refund Policy Pack | $29 | PDF 1 p | REPRICE | low |
| Toy Safety File Starter | $29 | PDF 1 p | REPRICE | low |
| Gulf Job-Landing ATS CV System | $29 | PDF 2 p | REPRICE | low |
| Battery & WEEE Mini-Guide | $29 | PDF 1 p | KEEP (honest title) | low |
| UK Deposit Recovery Action Pack | $29 | ZIP + spreadsheet (11 formulas) | KEEP | medium |
| EU AI Act Compliance Quickstart Checklist | $19 | PDF 2 p (dates already corrected) | KEEP | medium |
| EU AI Act Transparency Quickstart Checklist | $9 | PDF 2 p (dates already corrected) | KEEP | high |

## 9. Prompt-pack comparables and pricing (`data/evidence/prompt_pack_comparables.json`)
**Each candidate was verified from its page's price metadata and title:**

| Comparable | Price | Relevance |
|---|---|---|
| Marketing Masterminds Prompts (EN+AR) | $4.99 | **Direct** |
| 25 AI Prompts to Grow Your Etsy Shop (English) | $9.00 | **Direct** |
| Ultimate AI Prompt Kit for Copywriters (200+, EN+AR) | $9.00 | Weak |
| English e-commerce packs | $3.99–$6, £5, CA$5–6, and $19.99 for 250 prompts | Weak |
| 125-prompt Arabic guide; 50 English Etsy prompts | Free | Free anchors |
| One page | HTTP 404 | **Not evidence** |

**Decision: PROVISIONAL, $4.99–$7.99, leaning to the lower half.**
- **Why not final:** there have been 0 live ChatGPT tests, and there is no demand evidence.
- **Quality:**
  - Structural tests pass: teacher pack 20/20 (was 7/20), e-commerce 25/25 (was 7/25).
  - The honest-marketing guards are verified.

## 10. Local changes, commits, tests, remote status
**Local commits** (none on `origin/main`; `HEAD` = `5fd5637`, 5 ahead, 0 behind):

| Commit | Content |
|---|---|
| `34c1ea5` | Publishing security fix (Cycle 91) |
| `669f9ce` | B12-001 workbook repair, generator, integrity check, approval packet |
| `8cb62f7` | Prompt packs: tests, repairs, comparables |
| `5297e23` | Content audit, re-upload manifest, thin-product inventory |
| `5fd5637` | Approval tests; overlap test keeps its real defect sample |

**Test commands (exit 0 unless stated):**
- `python scripts/run_python_group.py <20 related modules>` in `git archive HEAD`: 298 OK, 1 skipped (PDF fixture gitignored).
- `unittest discover` import guard: 5,215 collected, 0 unimportable.
- `python scripts/audit_requirements.py`: 0 HARD.
- `node tests/test_factory_loop_publish_safety.js`: 4 passed.
- `python scripts/check_b12_integrity.py`: OK.

**Not committed (parallel-session work):**
- `distributor.py` (stays at HEAD; the rejected change is backed up), the local `tests/test_distributor.py`;
- `affiliate/publish_queue.py`, `tests/test_canva_*.py`;
- `.env` changes, and about 3,200 other untracked files.

## 11. External actions not performed, and why
| Action | Why not |
|---|---|
| Push to GitHub | Not authorized this cycle |
| Create the B12-001 draft | API creates can go live; manual is safe, so it is a founder action |
| Publish anything | `FACTORY_LIVE_PUBLISH=false`; not authorized |
| Unpublish `owtmpe` / `vhofn` | Founder action |
| Re-upload the 13 files | Founder action; Gumroad's API cannot replace files |
| Reprice, rename or expand thin products | Founder decision |

## 12. Verified revenue
**$0.00, 0 orders.**
- **Source:** Gumroad API sales read, 2026-10-17; every listing reports `sales_count` 0.
- **Not claimed:** no external transaction exists.

## 13. The single highest-value founder action
**Create the B12-001 draft (unpublished) by hand in the Gumroad dashboard:**
1. **Name:** Freelancer Rate & Raise Calculator.
2. **Price:** $14.99. Keep the product **unpublished**.
3. **Description:** paste it from `reports/B12-001/APPROVAL_PACKET_CYCLE94.md`.
4. **Files:** upload `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx` (check it's 8,922 bytes) and the cover `reports/B12-001/cover.png`.
5. **Tags:** freelancing, pricing, rate calculator, consultant, spreadsheet, raise, excel template, solo consultant.
6. **Review:** send the draft link back for review. Publishing is a separate approval afterwards.

**Before that, or at the same time:** authorize the push of the 5 local commits, which closes the publishing bypass that is on GitHub.

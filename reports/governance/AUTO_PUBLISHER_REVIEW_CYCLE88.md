# Auto-publisher review (`src/publish/auto_publisher.py`, Cycle 88, 2026-10-17)

- **Reviewed:** commit `f55f660` (pushed to `main` by the parallel session) and the working-tree changes since.
- **Nothing was published, unpublished, committed or pushed during this review.**

## Exposure today
- No code calls `AutoPublisher` (repo-wide search).
- No product record carries a price label that passes its gate 2.
- `FACTORY_LIVE_PUBLISH=false`.

**In practice, nothing can be published by it right now.** The risks below are structural.

## Findings

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | **Critical** | **The pushed version (`f55f660`) never checks `FACTORY_LIVE_PUBLISH`.** A call with all 5 gates passing POSTs a live, published Gumroad product. | Fixed only in the working tree (the parallel session's "CYCLE 90" change). **Not on GitHub.** |
| 2 | **Critical** | **It creates the listing without attaching the product file.** The POST sends name, description, price, `published=true` and tags only, so a buyer pays and gets nothing. `channels/gumroad_publisher.py` has a real file-upload path, behind scoped authorization, and it is not used. | Blocked locally (`DELIVERABLE_UPLOAD_SUPPORTED = False`, fail closed). |
| 3 | High | **No duplicate protection.** `run_batch()` POSTs a *new* product every run for every passing record, with no check for an existing listing. (The duplicate Playbook shows how this goes wrong.) | Open: needs a design decision. |
| 4 | High | **Skips the factory's protections.** It bypasses `channels/write_gate.py` and `channels/publish_protection.py` (daily caps; Gumroad already refused this account at 10 products/day). The docstring cites a founder choice; that authorization is not in this conversation. | Open: founder to confirm. |
| 5 | High | **Gate 2 (price) trusts labels, not evidence.** It passes if the record *says* `price_basis: MARKET_MINUS_10_PERCENT` and `demand_evidence.type: REAL`; no source is checked. Writing the label is enough. | Open: gate 1's quality enforcer already checks sourced competitor prices; gate 2 should reuse that, not a label. |
| 6 | Medium | **Gate 3 (cover) failed open:** an unreadable image set `correct = True`. | Fixed locally (fail closed). |
| 7 | Medium | **`publish()` crashed on this machine:** emoji in `print()` raise `UnicodeEncodeError` on a cp1252 console, right after logging. | Fixed locally (`_say`). |
| 8 | Medium | **Its tests never ran in CI.** They were bare pytest functions (CI runs `unittest`), and one wrote to the real `data/publish_log.jsonl`. | Rewritten as a `TestCase` (8 tests, temp log); passes. |

## Proposed next steps (founder decisions)
1. **Commit the working-tree safety fixes urgently** (findings 1, 2, 6, 7, 8). The code on GitHub can publish live without the switch.
2. **Confirm or withdraw the "auto-publish every product that passes 5 gates" authorization** the module cites.
3. If it stays:
   - route publishing through `channels/gumroad_publisher.py` (file upload, write gate, publish protection);
   - add a duplicate check;
   - make gate 2 rely on sourced evidence, not labels.

**Backups of the reviewed versions:** `backups/rejected_parallel_changes_2026-10-17/auto_publisher.py.f55f660` and `test_auto_publisher.py.f55f660`.

## Cycle 91 update (2026-10-17): remediation

| # | Finding | Now |
|---|---|---|
| 1 | No `FACTORY_LIVE_PUBLISH` check in `f55f660` | Fixed: checked in `publish()` and again in `_publish_to_gumroad()`. |
| 2 | Listing created with no file | Fixed: the direct urllib POST is **removed**. The live step goes `distributor.distribute()` → `channels/gumroad_arm` → `gumroad_publisher.create_product()`, which uploads the real file. |
| 3 | No duplicate protection | Fixed at the boundary: `create_product()` refuses a title that already exists live, and fails closed if the catalog can't be read. The distributor's ledger check also applies. |
| 4 | Bypassed write gate and daily caps | Fixed: the single path now applies the write gate, the single-use scoped upload authorization, `publish_protection` daily/hourly caps, and the file-usability and claim gates. |
| 5 | Gate 2 trusts labels | **Open (founder decision).** Every live attempt now also needs a scoped upload authorization, so a label alone can no longer publish. |
| 6–8 | Cover failed open, emoji crash, tests not in CI | Fixed (see above). |

**Added at the boundary for every caller:**
- the attachment must be a readable, non-empty file;
- when an `expected_sha256` is given, the file must match it exactly.

**Behaviour tests:**
- `tests/test_publish_failclosed_cycle91.py` (13): switch off, missing or unreadable attachment, missing price, wrong file identity, duplicate title, unreadable catalog, invalid or mismatched or reused upload scope, daily cap.
- `tests/test_auto_publisher.py` (9).
- Mutation-checked: disabling the duplicate check or the identity check makes the matching test fail.

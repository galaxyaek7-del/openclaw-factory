# Fixed PDFs to re-upload on Gumroad

Founder action. Gumroad's API cannot replace a product file, and the factory makes no Gumroad writes.

## The defect
On page 1 of three live kits, the title wrapped to a second line and that line was printed over the subtitle.
- **How it was found:** `file_testing_engine` flagged it, and rendering page 1 confirmed it.
- **What the repair changes:** the title now sits on one line (20pt), followed by a separator line and the subtitle (9pt), with a clear gap above the notice box.
- **What it leaves alone:** pages 2 onward and all page graphics. The text layer stays exact, so copy and search still work.
- **Repair tool:** `scripts/fix_pdf_title_overlap.py`. It verifies its own output: same page count, other pages unchanged, title and subtitle present, file test PASS.

| Listing | Re-upload this file | Original (kept) |
|---|---|---|
| ADA Demand-Letter Response & Triage Kit, https://aekraft.gumroad.com/l/palmdr | `books/ada_demand_response_kit.pdf` | `books/_pre_title_fix_2026-10-17/ada_demand_response_kit.pdf` |
| FTC Consumer Review Rule Compliance Kit, https://aekraft.gumroad.com/l/ekhza | `books/ftc_review_rule_compliance_kit.pdf` | `books/_pre_title_fix_2026-10-17/ftc_review_rule_compliance_kit.pdf` |
| Restaurant Health Inspection Readiness Kit, https://aekraft.gumroad.com/l/dvfvm | `books/restaurant_inspection_readiness_kit.pdf` | `books/_pre_title_fix_2026-10-17/restaurant_inspection_readiness_kit.pdf` |

## Why these are the delivered files
Page counts match what Gumroad records (3, 5 and 4 pages), and the original file sizes match to within about 1% (Gumroad's records in `data/cycle88_catalog_reconciliation.json`).

The repaired files are larger (30–54 KB, up from 10–13 KB) because the redrawn text embeds its font.

## Not in git
`books/*.pdf` is gitignored, so these files exist only on this machine.

## After re-uploading
Download one file from the Gumroad page and check that page 1 looks right.

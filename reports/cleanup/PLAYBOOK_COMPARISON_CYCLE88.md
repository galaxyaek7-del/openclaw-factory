# "The 5-Minute Context Reset Playbook": akxaae vs vhofn (Cycle 88)

- **Source:** Gumroad API `list_products`, one read-only GET on 2026-10-17. Raw copy saved locally, not committed.
- **Delivered files:** matched to local PDFs by exact page count and size, then read with pypdf.
- **Nothing was unpublished or edited.**

## Verdict: variants, not duplicates. `vhofn` does not deliver what it describes.

| | **akxaae** (keep, provisional preferred) | **vhofn** (proposed: unpublish) |
|---|---|---|
| Id | `rMOopS7Q7LHxwaPTY462uw==` | `9Zq9SGkALI0tjd7A97Pc_A==` |
| URL | https://aekraft.gumroad.com/l/akxaae | https://aekraft.gumroad.com/l/vhofn |
| Title / price / status | same title, $15, published, 0 sales | same title, $15, published, 0 sales |
| Delivered file (Gumroad `file_info`) | 117 KB, 9 pages | 168 KB, 10 pages |
| Matching local file | `books/five_minute_context_reset_playbook.pdf` (9 pp, 117 KB) | `books/the_5_minute_context_reset_playbook.pdf` (10 pp, 168 KB) |
| What the file contains | **1,612 words**: table of contents and chapters on the cost of context switching, a 5-step reset, a 30-second switch gate | **501 words**: a cover page, then **9 identical generic habit-tracker pages** ("Wake up early, Exercise, Read…"). Nothing on context resets. |
| Description | Specific: the 5-step reset, the 30-second gate, one measured claim, "PDF, 9 pages" | Generic template copy: "Step-by-step process… Checklists and prompts…", none of which is in the file |
| Description / file match | Matches | **Does not match.** A buyer gets a habit tracker. |
| Category | Other (taxonomy 266) | Business & Money › Entrepreneurship › Resources (taxonomy 174) |
| Tags | 5 | 4 |
| Custom summary | yes | none |

## The "80 vs 65" scores
- **Source:** `scripts/gumroad_seo_audit.py`, a listing-metadata score. It does **not** look at the delivered file.
- **akxaae, 80:** 100 − 20 (no cover). Its title, description length (854 chars), 5 tags and category all pass.
- **vhofn, 65:** 100 − 20 (no cover) − 15 (only 4 tags).
- **What the score misses:** it cannot see that `vhofn`'s file doesn't match its description. The file evidence above is the stronger reason, and it points the same way as the score.

## Proposed action (needs founder approval; not done)
1. **Unpublish `vhofn`** (https://aekraft.gumroad.com/l/vhofn): it sells a habit tracker under a context-reset title and description.
2. Keep `akxaae`.
   - Optional live edit: move it from "Other" to Business & Money (better Discover placement).
3. If `vhofn` is unpublished, also remove its card from `customer_site/products.html` (line 122, per `data/playbook_listing_conflict.json`).

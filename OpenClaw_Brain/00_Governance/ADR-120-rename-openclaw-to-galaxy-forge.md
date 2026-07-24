# ADR-120 — Company Rename: OpenClaw → Galaxy Forge

**Date:** 2026-07-24
**Status:** Adopted.

---

## The decision

Founder decision: rename the company from "OpenClaw" to "Galaxy Forge." Reason: an existing open-source project already uses the name "OpenClaw," and the company needs a distinct commercial identity that doesn't collide with it.

New public repository: `github.com/galaxyaek7-del/galaxy-forge` (superseding `github.com/galaxyaek7-del/openclaw` as the public-facing repo going forward — see "What's deliberately not done" below for the old repo's disposition).

## Scope of this rename, and why it's bounded

A repo-wide, unscoped find-and-replace of "OpenClaw" was rejected as too risky: this factory's own governance discipline is that ADRs and other dated documents are historical records of decisions made at a specific point in time, and retroactively editing what they say would misrepresent what was actually decided when. The founder's own instruction anticipated this ("keep historical accuracy where an ADR describes a past event under the old name"), so the executed scope is:

**Renamed (current/forward-facing identity):**
- Living governance docs: `MASTER_CHARTER.md`, `MASTER_BLUEPRINT.md` (`OpenClaw_Brain/00_Governance/`), `PROJECT.md`, `CLAUDE.md`.
- All real source code (147 files: every `.py`/`.js`/`.html`/`.json` file with a brand mention) — docstrings, comments, log banners, HTTP User-Agent strings (e.g. `Mozilla/5.0 (OpenClaw-Factory-SeedAuditor)` → `Mozilla/5.0 (Galaxy-Forge-SeedAuditor)`), the default KDP book author fallback (`product_families/families/kdp_books.py`/`knowledge_bases.py`: `"OpenClaw Press"` → `"Galaxy Forge Press"` — this is genuinely customer-facing, appearing on real published books).
- Telegram message templates: `channels/telegram_direct.py`, `lib/telegram_direct.js`, `n8n_workflows/04_Telegram_Notify.prepared.json`'s fallback message text, `build_in_public.py`'s Arabic notification strings.
- `public_site/` content in full (README, index.html, the 3 published posts).
- All 7 `trust/*.html` legal/policy pages (Trust Center, Security, Privacy, Terms, Refund, Responsible AI, Incident Disclosure).
- `config/economics.json`'s comment.

**Deliberately NOT renamed (historical record, or a stable internal identifier):**
- **Every `ADR-*.md` file** (111 files, 40 mentioning the old name) — each is a dated record of what was actually decided at that time under that name. Only this new ADR and any future ADR use "Galaxy Forge."
- **All other dated report/audit/strategy docs** at the repo root and in `OpenClaw_Brain/00_Governance/` not explicitly named by the founder (e.g. `FACTORY_STATUS.md`, every `*_REPORT.md`/`*_AUDIT.md`, `OPENCLAW_PRODUCTION_READINESS_CERTIFICATION.md`, `ARCHITECTURE_REVIEW_2026-07-16.md`, etc.) — same historical-snapshot reasoning as ADRs. **This is a scope interpretation, not a certainty**: the founder's instruction named exactly 3 governance docs; if "all governance docs" was meant to reach further than that literal list, say so and this can be extended.
- **`OPENCLAW_OS_CONSTITUTION.md`** — a foundational constitution document referenced by path from ~25+ other files. Not explicitly named by the founder, and renaming its filename would cascade into every cross-reference. Left untouched, filename and body both, as a deliberate deferral.
- **`OpenClaw_Brain/` directory name** — the internal knowledge-base directory itself. Renaming it would break every path cross-reference inside the (deliberately preserved) historical ADRs that mention it by path. Treated as a stable internal path, same reasoning as the local folder.
- **`backups/`, `n8n_workflows/backups/`, `data/`, `drafts/`, `pending_review/`, `reports/`, `recovery/`, `tier1_intake/`, `diagnostics/day09_health_report.json`** — dated snapshots and generated artifacts, not living docs.
- **Internal env var / test-flag names**: `OPENCLAW_TELEGRAM_CHAT_ID`, `OPENCLAW_TEST_FORCE_CRASH__`, `OPENCLAW_TEST_EMIT_SHUTDOWN_SIGNAL__`. Nobody outside this codebase ever sees these strings; renaming them requires a coordinated `.env` key change for zero brand benefit. Deferred — flagged as a cheap future cleanup if wanted, not done here.
- **The real Telegram bot handle** `@OpenClaw_Abdelkader_bot` — per the founder's explicit instruction (item 5), left untouched everywhere it's quoted (ADR-072, `n8n_workflows/README.md`). Renaming a live Telegram bot's username is a founder-side BotFather action (see the Arabic checklist delivered alongside this ADR).
- **The local folder path** (`C:\openclaw-dasgboard`) and the **private GitHub repo name** (`galaxyaek7-del/openclaw-factory`) — per the founder's explicit instruction (item 5) and because renaming either is a real, disruptive filesystem/remote operation, not a text edit. `package.json`/`package-lock.json`'s `"name": "openclaw-dasgboard"` field mirrors the folder name and was left untouched for the same reason.
- **Paddle product records** — per the founder's explicit instruction (item 5); `data/paddle_products.json` and the live Paddle dashboard were not touched. (Checked: no product title/description in the local catalog metadata mentioned "OpenClaw" in the first place, so there was nothing to change there even in the code layer.)

## Verification method

Rather than trust the rename script's own tally, every one of the 165 in-scope files was independently re-scanned afterward for any remaining "OpenClaw"/"openclaw"/"OPENCLAW" substring; the only survivors found were the explicitly protected strings listed above (confirmed line-by-line, not just by count). One real inconsistency was caught and fixed during this process: the first script pass silently failed to persist the change to `CLAUDE.md` on disk; a targeted re-run and re-verification confirmed it now matches every other renamed file.

## What's deliberately not done

- The old public repo `github.com/galaxyaek7-del/openclaw` (pushed earlier today, before this rename) is left as-is — not deleted, not archived. Founder's call on whether to archive it with a pointer to `galaxy-forge`, or leave it live.
- No attempt was made to rename `OpenClaw_Brain/`, `OPENCLAW_OS_CONSTITUTION.md`, or any historical ADR/report body text — see "Deliberately NOT renamed" above.
- Local folder path, Telegram bot handle, and Paddle products were not touched, per explicit founder instruction — a separate Arabic founder-side checklist covers exactly what to do for each, manually.

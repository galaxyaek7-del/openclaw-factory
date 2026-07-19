# ADR-078 — Nervous System v2: Fixed a Real Message-Garbling Bug, Added 2 New Events, Deployed Live

**Date:** 2026-07-19
**Status:** Adopted. Deployed live to the running n8n instance with the founder's explicit go-ahead, verified end-to-end via a real notification through the actual `factory_loop.js` code path (not just a raw webhook probe).

---

## What was found (audit, before any code)

`04_Telegram_Notify`'s "Build Telegram Message" node hardcoded exactly ONE message template — the golden-hunter-accepted one — regardless of the real `event` field in the payload. But `lib/n8n_notify.js`'s generic `notifyN8nProductionEvent()` sender is shared by **six** real event types, all posted to the same webhook (`N8N_TELEGRAM_WEBHOOK_URL`): `golden_opportunity_accepted`, `factory_stopped_unexpectedly`, `factory_recovered`, `recovery_completed`, `retry_queue_status`, and (as of this ADR) two new ones. Every one of the five non-golden-hunter events was silently rendering as `"🏆 الصياد الذهبي قبل فرصة جديدة\n\nالمجال: undefined\nالنقاط: undefined/100"` — a real, live bug, confirmed directly (see below), not assumed from reading the code alone.

Separately: `checkPendingReview()`'s 0→N transition already fired a desktop toast but never a Telegram message, and `pollSales()` detecting a real new sale (`total_new_sales > 0`) fired no notification of any kind. Both are real gaps the founder explicitly asked to close: "منتج جاهز للمراجعة" and "بيع جديد 💰".

**Confirmed live, not assumed**: a direct probe to the real, active webhook with a synthetic payload triggered the real workflow and produced a garbled message — this is an honest admission that the probe itself sent one confusing test message to the founder's real Telegram before the fix was ready. Noted directly to him, not hidden.

## What was built

1. **`lib/n8n_notify.js`**: two new pure payload builders, same pattern as every existing one — `buildPendingReviewNeededPayload(count)` and `buildNewSaleDetectedPayload(outcomes, totalNewSales)` (the latter projects only the arms with a real `new_sales > 0`, never the full raw outcome array).
2. **`factory_loop.js`**: `checkPendingReview()`'s existing 0→N transition now also fires `notifyFactoryRecoveryEvent(buildPendingReviewNeededPayload(...))`, fire-and-forget, same discipline as every other n8n notify call (a Telegram hiccup must never affect the real underlying state). `pollSales()` now fires `buildNewSaleDetectedPayload(...)` when `total_new_sales > 0`.
3. **`n8n_workflows/04_Telegram_Notify.prepared.json`**: the "Build Telegram Message" node's single hardcoded expression replaced with a nested-ternary expression branching on `$json.body.event`, with a correct Arabic template for all seven event types (six real + a `"📩 إشعار من OpenClaw: <event>"` fallback for anything unrecognized, so a future new event type degrades honestly instead of silently repeating the golden-hunter text). Verified by extracting the exact JSON-embedded expression string and executing it as real JS against all 7 real cases before touching the live instance.

## Deployed live (founder's explicit go-ahead, twice — see below)

Same safe pattern as `ADR-045`/`ADR-072`: real backup → stop the exact live PID → `n8n import:workflow` (offline) → restart → verify. Two founder confirmations were needed mid-flight because the deploy required two separate stop/restart cycles (import deactivates the workflow as a side effect; the DB-level `--active=true` write needs its own restart to take effect) and the safety classifier correctly treated the second `Stop-Process` call as a fresh action needing its own confirmation, not an extension of the first.

**Correction to `ADR-072`'s platform-limitation note**: this n8n version (2.25.7) does *not* reject `n8n update:workflow --id=<id> --active=true` (deprecated in favor of `publish:workflow`, but functional) the way the older `--activeState=fromJson` flag did. It writes the flag immediately but needs a restart to load — so activation is no longer strictly UI-only, though it still needs the same stop/restart cycle as any other change, which is why this stays a founder-go-ahead action, not a standing one.

**A process slip, honestly recorded**: the first backup was taken with `--backup` (`--all --pretty --separate`, one file per workflow in a new directory) rather than this repo's established single-combined-file convention (`--all --pretty --output=<file>.json`, per `ADR-045`). It was deleted and redone in the correct format — but by then the fix was already live and verified working, so what's kept (`n8n_workflows/backups/post_nervous_system_v2_20260719_171500.json`) is an honestly-labeled **post**-deployment confirmation snapshot, not a pre-change one. No functional risk resulted (the deploy succeeded and was verified correct before the backup was redone), but the true "before" snapshot of the live DB no longer exists as a separate file — only as this repo's own prior `04_Telegram_Notify.prepared.json` git history.

**Verified end-to-end**: `node -e "require('./factory_loop.js').notifyFactoryRecoveryEvent(buildPendingReviewNeededPayload(1))"` — the real production code path, not a raw webhook POST — returned `{"attempted":true,"success":true,"status":200}` against the live, active, freshly-imported workflow.

## What did NOT change

- `03_Production_Notify` (server.js's `N8N_PRODUCTION_WEBHOOK_URL` chain, `production_dossier_completed`) — untouched, still `active: false`/unimported, still gated on `N8N_PRODUCTION_WEBHOOK_URL` (unset in `.env`), per `CLAUDE.md`'s existing documentation. Not in scope for this ask.
- `notifyGoldenHunterAccepted()`'s payload/message — byte-identical output to the pre-fix hardcoded template, confirmed via the same extracted-expression test.

## Tests

- `tests/test_n8n_notify.js`: 4 new tests for the two new payload builders (carries real fields, degrades honestly on missing/undefined input, never throws). Full file: 27/27 passing.
- Full JS suite: all test files green, zero regressions from the `pollSales()`/`checkPendingReview()` call-site changes.
- Full Python suite: unaffected by this change (no Python files touched); re-run anyway as part of the same-session discipline.

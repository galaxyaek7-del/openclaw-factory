# ADR-073 — Telegram Notifications in Arabic, With Key Numbers

**Date:** 2026-07-18
**Status:** Adopted, tested, **verified live through the full production chain**.
**Implements:** founder directive — "the founder reads Arabic, not English."

---

## The change

`factory_loop.js`'s Golden Hunter Bridge → n8n → Telegram message is now Arabic:

> 🏆 الصياد الذهبي قبل فرصة جديدة
> المجال: {niche}
> النقاط: {opportunity_score}/100
> السعر المقترح: ${price}   *(only shown when the gate that produced the result computed a real price — the ladder-aware gate does, the older tier-based one doesn't; omitted cleanly rather than showing "undefined")*

**Key numbers threaded through, not just score:** `getLadderOpportunityScore()` (`factory_loop.js`) and `buildGoldenHunterNotifyPayload()` (`lib/n8n_notify.js`) now also carry `price` — previously dropped between `profit_oracle.ladder_opportunity_score()`'s real output and the notification payload. 5 new/updated tests confirm this (`tests/test_n8n_notify.js`, `tests/test_factory_loop_golden.js`).

## Standing principle recorded

**Every Telegram notification this factory sends — opportunity accepted, product ready, sale made, errors — must be in clear Arabic with the key numbers.** Only "opportunity accepted" is a real, live Telegram send today (this ADR). The other three are not yet wired to Telegram at all:
- **Product ready**: `server.js`'s `notifyN8nProductionEvent()`/`buildProductionNotifyPayload()` already fire a real event when a production dossier completes, but `03_Production_Notify`'s workflow only logs fields today — no Telegram send exists there yet, and `N8N_PRODUCTION_WEBHOOK_URL` isn't even configured.
- **Sale made**: no notification hook exists anywhere in the sales-polling path (`scripts/poll_sales.py` / `02_Sales_Poll`) today.
- **Errors**: `checkNeedsAttention()`/`NEEDS_ATTENTION.md`/`sendDesktopNotification()` exist for attention-needed conditions, but none of that reaches Telegram.

Building those three out is real, separate work (new payload builders, new/extended n8n workflows) — not done in this ADR, which was scoped to "make existing Telegram messages Arabic and prove it." Recorded here so a future session doesn't have to rediscover that only one of the four categories is live, and so whichever gets built next starts in Arabic from its first line, not English-then-translated.

## Verified live, twice, with a real lesson learned

First live attempt after the Arabic update showed the OLD English text still being sent, despite the database confirming the Arabic content had imported correctly. Root cause, found and disclosed rather than silently retried: **the founder's n8n browser tab had the workflow's pre-edit state cached; toggling Active in that stale tab re-saved the old English content over the CLI-imported Arabic update.** Reported to the founder plainly, re-imported, asked for a hard refresh before the next click — the second attempt held.

Final confirmed real execution (n8n execution id 43, `status: "success"`): the real Telegram API response shows `message_id: 143` for the exact text:

> 🏆 الصياد الذهبي قبل فرصة جديدة
>
> المجال: AI-powered compliance automation subscription system for accounting firms
> النقاط: 85.3/100
> السعر المقترح: $388

## Impact

- `factory_loop.js`: `getLadderOpportunityScore()` now returns `price`.
- `lib/n8n_notify.js`: `buildGoldenHunterNotifyPayload()` now carries `price` (undefined-safe).
- `n8n_workflows/04_Telegram_Notify.prepared.json`: Arabic message template with conditional price line; re-imported live (with two fresh backups in `n8n_workflows/backups/`).
- New/updated tests: 5 across `tests/test_n8n_notify.js` and `tests/test_factory_loop_golden.js`. Full suite: 470 Python + 54/12 in the two touched JS suites, zero regressions.
- **Lesson for future sessions editing a live n8n workflow via CLI while the founder may have an editor tab open**: warn them explicitly to hard-refresh before their next click, or a stale tab silently reverts the CLI-imported change the moment they save/toggle anything.

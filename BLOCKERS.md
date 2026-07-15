# BLOCKERS.md — what only the founder can unblock

Maintained automatically. Each entry: why it exists, the exact manual action needed, and what's already been prepared so the manual step is as short as possible. Nothing here should ever require more than a short authorization action from Abdelkader — everything automatable has already been done up to that point.

---

## 1. n8n login credentials

**Why it exists:** n8n's REST API returns `401 Unauthorized` (confirmed via direct request). Only Abdelkader has the login for `http://localhost:5678`.

**Update (`ADR-045`): the two broken workflows are now actually fixed in the live database, not just prepared as files.** With explicit authorization, a real backup was taken (`n8n_workflows/backups/pre_build_*.json`), the live n8n process was stopped cleanly (by exact PID, not a broad kill), `01_Market_Scout` and `00_CEO`'s fixes were imported via `n8n import:workflow` (CLI, offline database — no concurrent-write risk since the server was stopped first), n8n was restarted, and a fresh export confirmed all 5 workflows intact with the fixes live: `01_Market_Scout` now correctly calls `/api/scout/run`, `00_CEO` now correctly calls `/api/dashboard`. `Openclaw_Sensing_Engine` and `02_Sales_Poll` were untouched and remain exactly as they were.

**What's still genuinely blocked (confirmed, not assumed):** workflow **activation** cannot be done via CLI in this deployment — `n8n import:workflow --activeState=fromJson` errors with "only supported in queue or multi-main mode," which this instance doesn't run. Activation is a real, UI-only action.

**Manual action required (~1 minute):**
1. Log into `localhost:5678`.
2. Toggle **Active** on `Openclaw_Sensing_Engine` and `02_Sales_Poll` (both are fully correct now, confirmed by the fresh export — nothing else to fix).

## 1b. Gmail connection for `galaxyaek7@gmail.com`

**Why it exists:** connecting n8n to a real Gmail account requires either an OAuth2 consent flow completed by the account owner in a browser, or an app-password generated from Google Account settings and handed over — both are actions only Abdelkader can perform. No CLI or API path exists around this by design (Google's own security model), and it isn't something "full authority" changes.

**What's already prepared:** nothing hand-built yet — deliberately. None of the 5 existing workflows use an email/Gmail node, so there's no real reference in this installation to verify the exact node JSON schema against before writing one blind. Hand-crafting an unverified Gmail node and importing it risks an invalid or silently-broken node that looks configured but isn't — worse than being honest that this step hasn't started.

**Manual action required:**
1. Log into `localhost:5678`.
2. Add a Gmail (or Send Email) node to whichever workflow should notify you — e.g. `00_CEO` after an AI CEO `BUILD`/`PIVOT` decision, or a new notification workflow watching `NEEDS_ATTENTION.md`.
3. Connect the Gmail credential (OAuth consent screen — only you can click Allow) and set the recipient to `galaxyaek7@gmail.com`.
4. Once one real Gmail-connected node exists in the system, its exact JSON can be exported and used as a verified template for any additional notification nodes — at that point this becomes buildable end-to-end without guessing.

## 2. Live platform API key (Gumroad, Payhip, or Etsy)

**Why it exists:** `channels/{gumroad,payhip,etsy}_arm.py` all report `status() -> UNAVAILABLE` because no real token exists in `.env` — confirmed: `.env` has only `GROQ_KEY`.

**What's already prepared:** All three arms are fully coded, tested (35 tests across `test_base_arm.py`/`test_payhip_etsy_arms.py`/`test_gumroad_publisher.py`), and wired end-to-end into `distributor.py` and `book_generator.py`'s Dual Inspection pipeline. Gumroad is the most complete (ADR-030) — retry logic for transient failures, circuit breaker, real sales polling (`GET /sales`) all built and tested. **Nothing left to build here — this is purely a credential, not an engineering gap.**

**Manual action required:** Obtain a Gumroad access token (or Payhip/Etsy) and add it to `.env`. No code change needed to start using it.

## 3. First real sale

**Why it exists:** Depends entirely on #2 (a live API key) plus an actual product being published and marketed somewhere a buyer can find it. This is a business outcome, not a software gap.

**What's already prepared:** 4 real products have gone through the full factory pipeline (Dual Inspection passed) and sit ready in `books/`, waiting on #2 to actually publish.

**Manual action required:** Resolve #2, then publish (or confirm publishing) at least one product live.

## 4. Tier-1/2 Golden Hunter scoring (not a credential blocker — a design gap, partially closed)

**Why it exists:** Different category from #1-3 — not blocked on access, blocked on unfinished engineering. `ADR-035`/`ADR-036`: `profit_oracle.score_opportunity()`'s demand/competition/margin heuristic was blind to real market signal (HN points, GitHub stars) — confirmed empirically across 8 real research candidates, all clustering into the same 2-4 discrete scores regardless of real evidence strength.

**Update (`ADR-038`):** the `demand` component is fixed — now accepts real HN/GitHub signal and meaningfully differentiates (proven: the same 8 candidates now range 80.3-84.6 instead of a flat 81.6, tracking real evidence strength). Backward compatible, zero effect on live tier4 behavior (proven algebraically + by test). **`competition` and `profit_potential` still need the same treatment** before any real candidate could plausibly clear the tier1 floor — same word-count/keyword estimates as before.

**Manual action required:** None — still a "next design session" item, not a founder-authorization item. Narrower now than before.

---

*Nothing else in the current build is blocked. Everything not listed here either already works or has been explicitly built already this session.*

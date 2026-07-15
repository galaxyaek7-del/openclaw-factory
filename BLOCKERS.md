# BLOCKERS.md — what only the founder can unblock

Maintained automatically. Each entry: why it exists, the exact manual action needed, and what's already been prepared so the manual step is as short as possible. Nothing here should ever require more than a short authorization action from Abdelkader — everything automatable has already been done up to that point.

---

## 1. n8n login credentials

**Why it exists:** n8n's REST API returns `401 Unauthorized` (confirmed via direct request). Only Abdelkader has the login for `http://localhost:5678`.

**What's already prepared:** A full read-only diagnosis (`ADR-037`) via `n8n export:workflow --all` (safe — no write, confirmed n8n and server.js kept working normally after). Found 5 real workflows, 2 of them complete and correctly wired (`Openclaw_Sensing_Engine`, `02_Sales_Poll`) but inactive, 2 genuinely broken (`01_Market_Scout` had no URL set; `00_CEO` referenced an unresolved workflow). Corrected, ready-to-import files are saved at `n8n_workflows/01_Market_Scout.fixed.json` and `n8n_workflows/00_CEO.fixed.json` (see `n8n_workflows/README.md`).

**Manual action required (~2 minutes):**
1. Log into `localhost:5678`.
2. Activate `Openclaw_Sensing_Engine` and `02_Sales_Poll`.
3. Import the two `.fixed.json` files (Import from File, per workflow).

## 2. Live platform API key (Gumroad, Payhip, or Etsy)

**Why it exists:** `channels/{gumroad,payhip,etsy}_arm.py` all report `status() -> UNAVAILABLE` because no real token exists in `.env` — confirmed: `.env` has only `GROQ_KEY`.

**What's already prepared:** All three arms are fully coded, tested (35 tests across `test_base_arm.py`/`test_payhip_etsy_arms.py`/`test_gumroad_publisher.py`), and wired end-to-end into `distributor.py` and `book_generator.py`'s Dual Inspection pipeline. Gumroad is the most complete (ADR-030) — retry logic for transient failures, circuit breaker, real sales polling (`GET /sales`) all built and tested. **Nothing left to build here — this is purely a credential, not an engineering gap.**

**Manual action required:** Obtain a Gumroad access token (or Payhip/Etsy) and add it to `.env`. No code change needed to start using it.

## 3. First real sale

**Why it exists:** Depends entirely on #2 (a live API key) plus an actual product being published and marketed somewhere a buyer can find it. This is a business outcome, not a software gap.

**What's already prepared:** 4 real products have gone through the full factory pipeline (Dual Inspection passed) and sit ready in `books/`, waiting on #2 to actually publish.

**Manual action required:** Resolve #2, then publish (or confirm publishing) at least one product live.

## 4. Tier-1/2 Golden Hunter scoring (not a credential blocker — a design gap)

**Why it exists:** Different category from #1-3 — not blocked on access, blocked on unfinished engineering. `ADR-035`/`ADR-036`: `profit_oracle.score_opportunity()`'s demand/competition/margin heuristic is blind to real market signal (HN points, GitHub stars) — confirmed empirically across 8 real research candidates, all clustering into the same 2-4 discrete scores regardless of real evidence strength. Needs a genuine scoring redesign (e.g. feeding real engagement signal into the demand component directly), which is a standalone design project, not a quick fix.

**Manual action required:** None — this is a "when there's time for a dedicated design session" item, not a founder-authorization item. Listed here for visibility, not because it's blocking on him.

---

*Nothing else in the current build is blocked. Everything not listed here either already works or has been explicitly built already this session.*

# ADR-118 — Build in Public: Marketing Arm

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

Founder decision: adopt "Build in Public" as OpenClaw's official marketing strategy — directly closing the "Marketing readiness: NOT READY" finding from the same day's Production Readiness Certification. Three deliverables: (1) auto-generate weekly public progress reports from real factory data, English, honest numbers, no hype; (2) turn each ADR into a publishable post draft; (3) prepare a public GitHub repo structure + landing page with the real product catalog. Queue drafts for founder approval via Telegram in Arabic. Also: restore the Gumroad arm as the quick-win second channel per the certification.

## What was built

`build_in_public.py` (new), reusing every relevant already-built module rather than a second implementation of anything:

- **`build_weekly_progress_report()`** — pure real-data aggregation over `decision_engine.ranking.rank_all()` (real, timestamped decisions) and `channels/ledger.py` (real sale events). Zero AI cost, zero fabrication risk. Explicitly reports `0` when nothing real happened in the window rather than padding language — a dedicated test (`test_report_never_uses_hype_language`) asserts no hype adjective appears anywhere in the output.
- **`draft_adr_post()`** — reuses `ai_capability.orchestrator.generate()` (ADR-104's real multi-model dispatch, task type `marketing_copy`, already a real registered category on Groq) to turn one real ADR file into a public-facing draft. Never writes or publishes anything itself — returns the real draft text only.
- **`queue_draft_for_approval()`** — reuses `channels/telegram_direct.py::send_telegram_message()` verbatim (the same real, live Telegram integration wired 2026-07-18) — never a second Telegram integration. Writes the real draft to `drafts/pending_review/` and sends an Arabic approval notification. A Telegram send failure never blocks the real file being written (same fail-safe discipline as every other real notification path in this factory).
- **`build_public_site_structure()`** — real local scaffolding under `public_site/` (`README.md`, `index.html`, `products.json`), reusing `data/paddle_products.json`'s real 5-product catalog verbatim. Deliberately does **not** create or push an actual public GitHub repository — that is a real, hard-to-reverse, publicly-visible action requiring the founder's own explicit action, never taken by this module. A dedicated test (`test_never_creates_or_pushes_a_real_github_repo`) inspects the function's own source to confirm it never shells out to git/gh and never makes a network call.

Wired into Mission Control: `get-weekly-progress-report`, `draft-adr-post`, `queue-draft-for-approval` — every draft-producing action still requires the same `confirmed: true` contract every Mission Control action already enforces, and none of them publish anything; they only write a real pending-review file and notify.

## The real, live demonstration run — including one honest finding

Rather than only build and unit-test this in isolation, the pipeline was run for real, end-to-end, against this factory's actual current data:

1. `public_site/` was generated for real, with the real 5-product catalog.
2. The real weekly progress report was generated (33 opportunities scored this week, 3 accepted, 19 rejected, $0.00 real revenue) and queued — a real file was written and a real Arabic Telegram notification was sent successfully.
3. **ADR-to-post drafting was run for real on 3 sample ADRs** (ADR-116, ADR-106, ADR-117) rather than starting with all 109 real ADRs unprompted. The first (ADR-116, Reality Mode) succeeded and was queued the same way, with a real Telegram notification sent. **The second call hit a real Groq rate limit (HTTP 429 Too Many Requests)** — a genuine, live constraint, not a code bug. Reported honestly rather than retried aggressively or silently worked around. Bulk-converting the remaining ~106 real ADRs is a real, mechanical follow-up available on request, best run at a controlled pace (e.g. with real backoff between calls) rather than in one unthrottled batch.

## Gumroad restoration — a real, disclosed tension, and a real blocker this session cannot close alone

Investigated before touching anything: `channels/gumroad_arm.py`'s own docstring already documents a **prior, deliberate founder decision** (ADR-065/`MASTER_CHARTER.md` §2, dated 2026-07-17): Gumroad was explicitly "ARCHIVED... deprioritized and frozen... no new engineering effort defaults to it going forward" in favor of Paddle, because `GUMROAD_ACCESS_TOKEN` "was always the missing piece." This is disclosed here rather than silently overridden, since today's certification's own "quick win" framing was written without surfacing that prior decision.

Confirmed live: `GUMROAD_ACCESS_TOKEN` is genuinely **not present in `.env`** today. The arm's code itself is real, complete, and already tested (`channels/gumroad_arm.py` is a thin, working adapter over `gumroad_publisher.py`, self-registers correctly) — this is not a code gap. It is a missing real credential from the founder's own Gumroad account, which this session has no access to and cannot generate. **Restoring Gumroad requires the founder to obtain a real Gumroad API access token and add it to `.env`** — not something this session can complete unilaterally. Flagged here rather than left silent; no code change was made to "restore" it, since none was possible without the real credential.

## Verification

15 new tests (`tests/test_build_in_public.py` — 9, `tests/test_mission_control_api.py` — 6 new). Full regression: highest-risk suites first, then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- No actual public GitHub repository created or pushed — real local scaffolding only, per the directive's own "prepare" wording and this session's standing rule that publishing public content requires the founder's own explicit action.
- No bulk generation of all 109 real ADR drafts in one pass — a real Groq rate limit was hit at 2 concurrent calls; the mechanism is proven and ready, pacing is a founder-controlled follow-up.
- Gumroad was not "restored" — the code was already real and ready; the missing piece is a real credential only the founder can provide.

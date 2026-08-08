# Galaxy Forge — External Dependency Map

**Date:** 2026-08-08 | ADR-221, Phase 30.5, Section 26. Verified live this round via `.env` variable-name scan (values never read/exposed) and live status/health checks.

---

| Service | Purpose | Account | Credential | API | Status | Failure Mode | Manual Fallback | Business Impact |
|---|---|---|---|---|---|---|---|---|
| Groq | LLM generation (all AI text/content) | Real, active | `GROQ_KEY` present | Live-capable | **REAL** | Real exponential backoff + `Retry-After` handling (fixed 2026-08-06) | None needed — real retry logic | HIGH if down: blocks all content generation |
| Paddle | Payment processing + checkout | Real account, onboarding incomplete | `PADDLE_API_KEY` present | Live, confirmed working (real product list retrieved this round) | **CONFIGURED, BLOCKED_EXTERNAL** | `check_publish_allowed()` cooldown; checkout re-check script | Founder must complete `vendors.paddle.com` onboarding | **CRITICAL — the single blocker to any real revenue today** |
| Gumroad | Alternate marketplace | No real account credential found | `GUMROAD_ACCESS_TOKEN` absent from `.env` | Arm returns `unavailable`, never raises | **NOT_CONNECTED** | Skips safely, logs `arm not ready` | Founder must configure token | MEDIUM — alternate channel, not currently load-bearing |
| Etsy | Alternate marketplace | No real credential | Absent | `unavailable` | **NOT_CONNECTED** | Same as Gumroad | Founder must configure | LOW-MEDIUM |
| Payhip | Alternate marketplace | No real credential | Absent | `unavailable` | **NOT_CONNECTED** | Same as Gumroad | Founder must configure | LOW |
| Amazon Associates | Affiliate revenue | No real account confirmed created | `AMAZON_ASSOCIATE_TAG` absent | Real click-tracking code exists, 0 real clicks | **CONFIGURED (code) / NOT_CONNECTED (account)** | Honestly omits the tag rather than fabricating one | Founder must create & approve real Associates account | MEDIUM — a real, disclosed 2nd revenue lane, currently dormant |
| Telegram | Founder notifications | Real, active | `TELEGRAM_BOT_TOKEN`, `OPENCLAW_TELEGRAM_CHAT_ID` present | Real, used for real alerts (Paddle checkout-ready check, resilience incidents) | **REAL** | Best-effort send, never blocks the caller on failure | None needed | LOW if down — notification-only, no business logic depends on it |
| Mission Control auth | Founder dashboard access | N/A (local password) | `MISSION_CONTROL_PASSWORD` present | N/A | **REAL** | Session-cookie based | Founder resets password directly | LOW |
| Internal service token | factory_loop.js ↔ server.js internal auth | N/A | `INTERNAL_SERVICE_TOKEN` present | N/A | **REAL** | Requests without it are rejected | N/A | LOW — internal only |
| n8n | Optional automation webhook | Not configured | `N8N_PRODUCTION_WEBHOOK_URL` unset (documented as optional, off by default) | N/A | **NOT_CONNECTED (by design)** | Fire-and-forget, never blocks real production | N/A | NONE — genuinely optional |

## Summary

**1 of 6 real commercial/payment services is credentialed and API-reachable (Paddle).** It is blocked by a real external onboarding gate, not a code defect. **0 of 6 have live, working checkout.** This single fact is the real, current ceiling on this factory's ability to generate real revenue, independent of how much Phase 26-30 code exists.

---

*See also: `TRUTH_MATRIX.md`, `COMMERCIAL_REALITY.md`.*

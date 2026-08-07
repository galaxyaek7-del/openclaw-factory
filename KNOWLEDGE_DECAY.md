# Galaxy Forge — Knowledge Decay

**Date:** 2026-08-08 | Phase 18, Section 16. Document companion to `knowledge_decay.py` — live output captured this round.

---

## Real, live staleness check (this round)

**7 real, dated facts checked. 0 stale today** — every one was verified within the last 1-2 days (this session's own work), well inside its real, disclosed per-category threshold (30-90 days).

| Subject | Category | Last verified | Threshold | Status |
|---|---|---|---|---|
| Payhip public API product-creation capability | platform_api | 2026-08-07 | 60 days | FRESH |
| Amazon Associates commission rate | commission_rates | 2026-08-07 | 60 days | FRESH |
| 19-platform PLATFORM_REGISTRY | commission_rates | 2026-08-07 | 60 days | FRESH |
| EU AI Act enforcement timeline | regulations | 2026-08-06 | 90 days | FRESH |
| EU AI Act Toolkit Paddle price | pricing | 2026-08-07 | 30 days | FRESH |
| Groq real usage stats | ai_model_capabilities | 2026-08-07 | 30 days | FRESH (continuously self-updating) |
| governancedocs.com/riskprofs.com pricing citations | competitor_pricing | 2026-08-06 | 30 days | FRESH |

## The real, disclosed limitation

`KNOWLEDGE_DECAY.md`'s own registry (`KNOWN_STALENESS_CHECKS`) is **manually maintained** — it tracks only facts someone has explicitly added, with their real, already-documented verification date. It does not automatically discover new facts to track, and does not automatically re-verify a stale fact. This is disclosed in the module's own return value (`note` field), not hidden.

**What happens when something goes stale**: nothing automatic yet — `assess_all_known_knowledge()` is a real, callable check, not (yet) wired into a daily tick or alert. Given every tracked fact is fresh today, this is not urgent; the correct trigger to wire it into `factory_loop.js`'s daily cycle is the first time a real check actually goes stale.

---

*See also: `knowledge_decay.py`, `KNOWLEDGE_LIFECYCLE.md`.*

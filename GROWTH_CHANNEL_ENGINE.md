# Galaxy Forge — Growth Channel Engine

**Date:** 2026-08-08 | ADR-218, Phase 28, Section 11. `global_growth_engine.growth_channel_score()` — genuinely new this round.

---

## Real, deterministic classifier

Reuses `business_development.py`'s real per-platform score (the closest real per-channel signal this factory has). 6 named tiers (`CORE`/`GROWTH`/`EXPERIMENTAL`/`SECONDARY`/`UNPROFITABLE`/`EXIT`): real `ACTIVE` stage + score ≥4 → `CORE`; `ACTIVE` → `GROWTH`; score 0 → `UNPROFITABLE`; score 1-2 → `SECONDARY`; else → `EXPERIMENTAL`.

## Never defaults an unregistered channel to CORE

Verified by a dedicated regression test — an unrecognized channel always resolves to `EXPERIMENTAL`, never a fabricated high-confidence tier.

---

*See also: `PLATFORM_FIT_ENGINE.md` (Phase 26), `GROWTH_RISK_ENGINE.md`.*

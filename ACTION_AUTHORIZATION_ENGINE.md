# Galaxy Forge — Action Authorization Engine

**Date:** 2026-08-08 | ADR-209, Phase 19, Section 3. `autonomous_operations.authorize_action()`.

---

## The rule: never infer authorization

For every action category, `authorize_action(category, context)` returns:

```json
{
  "category": "...",
  "required_level": 0-6,
  "required_level_name": "...",
  "real_enforcement_citation": "the exact real function that already gates this",
  "decision": "ALLOW" | "REFUSE",
  "reasoning": "..."
}
```

- An **unrecognized category always refuses** — the registry (`ACTION_CATEGORY_AUTONOMY`, 12 real entries) is the only source of truth; nothing is guessed.
- **Levels 0-4 ALLOW by design** — their real enforcement already happens inside the cited function itself (e.g. `check_publish_allowed()`'s live caps/cooldown check); this engine's classification doesn't grant new authority, it documents existing authority.
- **Level 5 requires an explicit `context = {"founder_approved": True, "approval_reference": "<real reference>"}`** — both fields, not just the flag. Missing either → REFUSE.
- **Level 6 refuses unconditionally** — no `context` value can change this, verified by a dedicated regression test that forces every field to `True` and confirms `REFUSE` anyway.

## What this engine does NOT do

It does not call `evolution_queue.approve_proposal()`, `channels/publish_protection.approve_first_publish()`, or any other real mutating function. It is a pure, deterministic classifier — the real gate functions remain the only things that can actually authorize an action; this module only tells a caller (human or automated) what level is required and whether the `context` it was given would satisfy that level.

## Real fields per proposed action (Section 3's 12 named fields)

Directly available from `authorize_action()`'s own output (`category`, `required_level`, `decision`) plus the caller's own real context (Department/Agent/Risk/Financial Impact/Customer Impact/Reversibility/Security Impact/Legal Impact are supplied by the calling system, not fabricated here — e.g. `evolution_queue.py`'s own real `affected_modules`/`rollback_complexity`/`sensitive_areas_touched` fields for evolution proposals, `channels/publish_protection.py`'s own real `risk_score` for publish actions). This module deliberately does not duplicate those real per-domain risk computations into a second, competing risk model.

---

*See also: `AUTONOMY_LEVELS.md`, `AUTONOMOUS_TASK_QUEUE.md`.*

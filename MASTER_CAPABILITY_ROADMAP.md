# OpenClaw Master Capability Roadmap

**Date:** 2026-07-17
**Directive:** "Executive Mission 002 — OpenClaw Operating System"
**Rule going forward, per this directive:** every future implementation should originate from an item below, not from ad hoc technical interest. Items are grouped by the same Critical/Important/Optional/Future tiers as `CAPABILITY_MAP.md`, cross-referenced to it and to `EXECUTIVE_BACKLOG.md` (the tactical, day-to-day queue this roadmap sits above).

---

## Critical — nothing else matters until these are resolved

1. **Decide what counts as real market validation for this product category** (`CAPABILITY_MAP.md` M1). Founder decision. The current gate has a 0% real acceptance rate across 121 checks — not from lack of automation, but from evidence sourced for the wrong industry (developer tools, not consumer digital products). Candidate directions to evaluate: Etsy/Amazon real search-volume or listing-count signals, Pinterest trend data, Reddit communities relevant to journals/planners/self-improvement, or a deliberate, documented decision to loosen the tier4 floor given the evidence-source constraint is structural, not temporary.
2. **Obtain a real distribution credential** (`CAPABILITY_MAP.md` M2). Founder-only (external account). Gumroad recommended first (code already tested, no OAuth friction).

## Important — real value, doesn't block the first dollar directly

3. **Resolve the C2/C2b automation-path inconsistency** (M3). Founder + engineering: decide whether `factory_loop.js`'s simple gate or `decision_engine`'s richer one is the long-term source of truth, then retire or properly wire the other — currently both exist, only one runs, and that's an accident of history, not a decision.
4. **Proactive founder notification** (M4). Pure engineering, low risk, no design ambiguity — a real gap between "the system correctly detects a problem" and "a human finds out." Recommended next engineering pick once Critical items are moving.
5. **Get CI running on GitHub's real infrastructure** (M5). Mechanical — the workflow already exists and is locally verified; it has simply never fired for real, since every commit this session was made and pushed by the same local process rather than through a PR flow that would trigger it.

## Optional — real but not urgent

6. Additional distribution channels (Etsy, Payhip) — code exists, credentials don't. Sequence after the first Gumroad sale, not before.
7. Extend log rotation further (already covers the 3 highest-volume logs).
8. Migrate the remaining ~9 JSONL-read call sites to the shared primitive (`EXECUTIVE_BACKLOG.md`).
9. Split `server.js`/`factory_loop.js` into smaller modules (`EXECUTIVE_BACKLOG.md` — needs its own design pass first).

## Future — explicitly not now, by design

10. The other 5 planned business paths (templates, art, apps, services, trading) — `CLAUDE.md`'s own golden rule blocks this until the first real dollar from the current product.
11. Multi-machine/redundant infrastructure — `CLAUDE.md`/`IDENTITY_ARCHITECTURE.md`/`ADR-014` already cover this as a conscious, deliberate non-goal for this stage. Do not propose revisiting without reading those first.

---

## What this roadmap deliberately does not contain

Any item that would require guessing a founder's business judgment (which evidence source to build, how strict the acceptance bar should be, which channel to prioritize second) is recorded as a **decision required**, not a task to execute. This roadmap's job is to make sure engineering effort always has a real, current, evidence-based reason to exist — not to make business calls on the founder's behalf.

## How this roadmap stays current

Update this file whenever: a Critical item is resolved (promote the next tier), a new capability gap is found (add it with the same Purpose/Owner/Dependencies/Risk shape as `CAPABILITY_MAP.md`), or evidence shows a prior entry was wrong (correct it visibly, don't silently delete — matches this session's own standing convention for `EXECUTIVE_BACKLOG.md`).

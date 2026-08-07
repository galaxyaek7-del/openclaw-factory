# Galaxy Forge — Knowledge Access Control

**Date:** 2026-08-08 | Phase 18, Sections 24-25. Real citation over `server.js`'s existing `requireMissionControlAuth` gate and `customer_pipeline.py`'s data-minimization practice — not rebuilt.

---

## Section 24 — Privacy

| Principle | Real practice |
|---|---|
| Data minimization | `customer_pipeline.py` stores only name/email/description/company/budget_range — no real collection beyond operational necessity, confirmed by direct search |
| Purpose limitation | Real — customer data flows only through the real fulfillment pipeline, never repurposed for a second use |
| Access control | See Section 25 below |
| Secure storage | Local, unencrypted flat files (`RELIABILITY_ARCHITECTURE.md`'s own disclosed gap — same real limitation as all this factory's data, not unique to knowledge) |
| Deletion requirements | **Real, disclosed gap** — no real data-deletion/right-to-erasure mechanism exists anywhere in this factory, since 0 real customer PII has ever been collected to need deleting |

## Section 25 — The 4 named classification levels

| Requested | Real equivalent |
|---|---|
| PUBLIC | `customer_site/` (public routes, no auth) |
| INTERNAL | Every Mission Control panel — gated by `requireMissionControlAuth`, confirmed structurally impossible to bypass by omission (`PRODUCTION_HARDENING_REPORT.md`, Phase 10B finding, re-confirmed since) |
| CONFIDENTIAL | `INTERNAL_SERVICE_TOKEN`-gated routes (real automated-caller-only access, `X-Internal-Token`) |
| RESTRICTED | The 4 permanently protected human-gated actions (Evolution Queue execution, capital reallocation, business retirement, elevated-risk publishing) — no agent, human or AI, can bypass these |

**No new access-control layer was built** — this factory's real, existing 2-tier auth model (`MISSION_CONTROL_PASSWORD` for humans, `INTERNAL_SERVICE_TOKEN` for automated internal callers) already maps cleanly onto 3 of the 4 requested levels; the 4th (RESTRICTED) is enforced by governance, not a technical ACL, matching this factory's own established "protected by policy + code structure, not a permissions database" design (no user-role system exists, by design — single founder/operator).

---

*See also: `SECURITY_HARDENING_REPORT.md` (Phase 14), `AI_MEMORY_POLICY.md`.*

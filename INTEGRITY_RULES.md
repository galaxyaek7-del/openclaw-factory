# OpenClaw / Galaxy Forge — Integrity Rules

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). This document names the real, already-built enforcement chain that checks every AI-generated recommendation and every customer-facing artifact against the rest of the Company DNA before it executes. It documents what exists; it does not invent a new gate on top of what's already real.

---

## 1. The real enforcement chain

Every recommendation this company's AI systems produce passes through one or more of these real, checkable gates before it can affect a real customer, a real dollar, or a real publish:

| Stage | Real gate | What it checks |
|---|---|---|
| Idea → opportunity | `profit_oracle.py`'s hard gates (ADR-121/122/126) | Proof of Payment, Pain Severity, Competitive Advantage, Long-Term Strategic Asset — see `DECISION_FILTERS.md` |
| Opportunity → decision | `decision_engine/` (ADR-050/076) | Real evaluation snapshot, `decision_id`, reasoning, alternatives rejected, expected outcome |
| Decision → product | `inspectors.py`'s Dual Inspection | Real technical checks (file integrity, page count, dimensions) + real commercial checks (`market_realism`, `not_duplicate`, `not_previously_rejected`) |
| Product → publish | `executive_quality_gate.py`'s `REJECT_IF_FAIL` (7 real checks) | Legal compliance, brand reputation, market saturation, content neutrality, copyright/trademark, fake urgency, customer-pain evidence |
| Customer-facing text | `brand_dna.py::validate_customer_facing_text()` | The real, callable Brand Consistency Engine — runs the Trust Framework checks against any text before it reaches a customer |
| Every real endpoint | `reality_audit.py` | Structural REAL/SIMULATION/ARCHITECTURE_ONLY/NOT_IMPLEMENTED classification, live-verified, re-run repeatedly this session at 98–99% REAL |
| Weekly, standing | `trust_audit.py` (ADR-189) | Misleading claims, product weaknesses, customer/reputation/security/ethical risks — pure citation over the gates above |

**A recommendation that has not passed the gate relevant to its own stage does not execute.** This is not a policy statement — it is the literal, load-bearing behavior of the code named above, confirmed by direct testing throughout this company's real operating history (`QUARANTINE.md`'s 3,300+ real rejections are this system working, not failing).

## 2. Advisory vs. binding

Not every real system in this company is a gate. Some are explicitly, deliberately advisory-only — named here so the distinction is never assumed away:

- **GOOS** (`goos.py`, ADR-171) is advisory. Its own score never replaces or tightens the real production floor (`profit_oracle.MIN_OPPORTUNITY_SCORE = 65`).
- **The Enterprise Digital Twin** (`digital_twin.py`, ADR-161) is advisory-only by explicit founder decision — it never calls a real approve/reject/publish/reallocate function, verified by a real regression test that asserts this.
- **The EOS Decision Feed** (`eos_decision_feed.py`, ADR-186) and **CEO Home** (`ceo_home.py`, ADR-184) are read-only citations — they recommend, they do not execute.

## 3. The four permanently human-gated actions

Regardless of how sophisticated this company's AI systems become, these four actions have been explicitly, repeatedly reconfirmed as human-gated — first decided in ADR-133, reconfirmed in ADR-142, 144, 147, and 157, never loosened once:

1. **Capital reallocation** — `capital_allocation_engine.py` recommends; the founder decides.
2. **Business retirement** — no automated system may retire a business line.
3. **Evolution Queue execution** — `evolution_queue.py`'s Execute step requires explicit founder approval, every time, with no exception.
4. **Elevated-risk or new-channel publishing** — `channels/publish_protection.py` blocks a genuinely new arm's first publish, or any publish crossing a real high-risk threshold, until the founder clears it.

**This document does not change that list. Extending or loosening it requires the founder to say so explicitly, again, the same way it has been reconfirmed every time it's come up.**

## 4. What happens when a recommendation fails a gate

It is recorded, not hidden. `QUARANTINE.md` (products), `data/decisions.jsonl` (opportunities), `data/incidents.jsonl` (resilience findings), and `data/executive_directives.jsonl` (executive-level calls) are the real, permanent record of every real rejection and every real risk finding this company has ever produced — the actual Company Memory this document's own DNA calls for, not a separate ledger invented for this document.

## 5. Self-check

This document itself is subject to the rules it describes: it makes no claim above that isn't traceable to a real file, a real ADR, or a real, checkable fact about this company's own history as of 2026-08-07. Where something named in the founder's own directive doesn't yet exist as real code (a formal legal-entity structure, a real employee-facing culture), it says so plainly rather than filling the gap with confident-sounding prose.

---

*See also: `COMPANY_DNA.md` (the principles), `DECISION_FILTERS.md` (the six approval questions), `COMPANY_PERSONALITY.md` (the behavioral rules `validate_customer_facing_text()` enforces).*
